"""Real Foundation producer/consumer regressions for whole-review F1–F6."""
from dataclasses import asdict, replace
from datetime import date, datetime, timedelta, timezone
import runpy
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import pytest

from quant_dca.calendars.service import eligible_session_open, eligible_session_close, nth_subsequent_open
from quant_dca.canonical.validate import validate_ohlcv
from quant_dca.corporate_actions.economics import economic_acquisition_cost, split_adjusted_feature_prices
from quant_dca.lineage import FeatureLineage, lookup_lineage
from quant_dca.point_in_time.asof import latest_known
from quant_dca.storage.snapshots import write_snapshot, read_snapshot_metadata, snapshot_hash
from quant_dca.types import CorporateAction, OHLCV, Observation, QualityTier, Region, Security

UTC = timezone.utc

def ts(day, hour=22):
    return datetime(2020, 1, day, hour, tzinfo=UTC)


def bar(day='2020-01-02', price=100., exchange='XNYS', **changes):
    opened = eligible_session_open(exchange, date.fromisoformat(day))
    closed = eligible_session_close(exchange, date.fromisoformat(day))
    values = dict(security_id='S', session_date=day, open=price, high=price, low=price,
                  close=price, volume=100., currency='HUF', region=Region.US if exchange=='XNYS' else Region.EU,
                  exchange=exchange, session_open_at=opened, session_close_at=closed,
                  available_at=closed+timedelta(minutes=1), source='prices', revision_id='p1', quality=QualityTier.A)
    return OHLCV(**(values | changes))


def action(**changes):
    return CorporateAction(**(dict(security_id='S', action_id='A', action_type='split',
        ex_date='2020-01-06', currency='HUF', region=Region.US, exchange='XNYS',
        split_ratio=2., available_at=ts(3), revised_at=ts(3), source='actions', revision_id='a1', quality=QualityTier.A) | changes))


class NoFX:
    def resolve(self, *args):
        raise AssertionError('HUF must require no FX')


def obs(**changes):
    return Observation(**(dict(series='CPI', entity_id='US', observation_date='2019-12-01',
        value=1., available_at=ts(10), revised_at=ts(2), source='macro', revision_id='z-old', quality=QualityTier.A) | changes))


def test_f1_delayed_original_and_revision_never_supersede_newer_known_revision():
    old, new = obs(), obs(value=2., available_at=ts(4), revised_at=ts(3), revision_id='a-new')
    assert latest_known([old, new], ts(5)) is new
    assert latest_known([new, old], ts(11)) is new
    original = replace(old, revised_at=None, published_at=ts(1))
    assert latest_known([original, new], ts(11)) is new
    with pytest.raises(ValueError, match='PIT_AMBIGUOUS_VINTAGE'):
        latest_known([new, replace(new, value=3., available_at=ts(9))], ts(11))


def test_f1_date_vintages_order_without_inventing_timestamp():
    old = obs(revised_at=None, vintage_start='2020-01-02', vintage_end='2020-01-02')
    new = obs(value=2., revised_at=None, vintage_start='2020-01-03', vintage_end='2020-12-31', available_at=ts(4), revision_id='new')
    assert latest_known([new, old], ts(11)) is new
    assert new.published_at is None and new.revised_at is None
    with pytest.raises(ValueError, match='PIT_AMBIGUOUS_VINTAGE'):
        latest_known([old, replace(new, vintage_start=None)], ts(11))


def test_f1_fred_normalized_intervals_are_date_evidence_and_conflicts_fail_closed(tmp_path):
    from quant_dca.providers.fred import FREDProvider
    from quant_dca.providers.base import RawStore
    provider = FREDProvider(series_id='CPI', vintage_start='2020-01-01',
        vintage_end='2020-12-31', transport=None, raw_store=RawStore(tmp_path),
        availability_quality_policy=lambda row: (ts(10) if row['value']=='1' else ts(4), QualityTier.A))
    rows = list(provider.normalize('us_macro_vintages', [
        dict(date='2019-12-01',value='1',realtime_start='2020-01-02',realtime_end='2020-01-02'),
        dict(date='2019-12-01',value='2',realtime_start='2020-01-03',realtime_end='2020-12-31')]))
    assert latest_known(rows,ts(5)).value == 2.
    assert latest_known(rows,ts(11)).value == 2.
    assert all(row.published_at is None and row.revised_at is None for row in rows)
    with pytest.raises(ValueError, match='PIT_AMBIGUOUS_VINTAGE'):
        latest_known([replace(rows[0],vintage_end='2020-01-05'),rows[1]],ts(11))


def test_f1_explicit_group_rejects_mixed_securities_and_unknown_revision_order():
    with pytest.raises(ValueError, match='PIT_MIXED_GROUP'):
        latest_known([bar(), replace(bar(),security_id='OTHER')],ts(10))
    with pytest.raises(ValueError, match='PIT_AMBIGUOUS_VINTAGE'):
        latest_known([obs(revised_at=None), obs(revised_at=None,value=2.,revision_id='r2',available_at=ts(4))],ts(11))


def test_f1_delayed_listing_and_membership_cannot_resurrect_known_delisting():
    fixture = runpy.run_path(str(Path(__file__).parents[1] / 'universe/test_membership.py'))
    cutoff = fixture['CUTOFF']
    for field, constructor in [('securities', fixture['security']), ('memberships', fixture['membership'])]:
        old = constructor(active_to=None, revised_at=datetime(2022,1,2,tzinfo=UTC), available_at=datetime(2022,1,10,tzinfo=UTC))
        new = constructor(active_to='2022-01-07', revision_id='v2', revised_at=datetime(2022,1,7,tzinfo=UTC), available_at=datetime(2022,1,8,tzinfo=UTC))
        assert not fixture['index'](**{field:[old,new]}).is_eligible('OLD', cutoff)


@pytest.mark.parametrize('duplicate', [True, False])
def test_f2_one_action_identity_is_applied_once_to_features_and_labels(duplicate):
    raw = bar()
    old = action()
    new = old if duplicate else action(split_ratio=4., revised_at=ts(7), available_at=ts(8), revision_id='a2')
    versions = [old,new]
    feature = split_adjusted_feature_prices([raw], versions, as_of=ts(10))[0]
    assert feature.open == (50. if duplicate else 25.)
    result = economic_acquisition_cost(bar('2020-01-10', 25.), raw, versions, NoFX())
    assert result.share_units == (2. if duplicate else 4.)
    assert result.selected_action_versions == (('S','A',new.revision_id),)
    assert result.label_matures_at >= new.available_at


def test_f2_corrected_date_is_selected_before_relevance_and_changes_maturity():
    old = action()
    new = action(ex_date='2020-01-13', revised_at=ts(11), available_at=ts(13), revision_id='a2')
    assert split_adjusted_feature_prices([bar()], [old,new], as_of=ts(10))[0].open == 50.
    assert split_adjusted_feature_prices([bar()], [old,new], as_of=ts(14))[0].open == 50.
    result = economic_acquisition_cost(bar('2020-01-10',100.), bar(), [old,new], NoFX())
    assert result.total == 100.
    assert result.label_matures_at == new.available_at
    assert result.selected_action_versions == (('S','A','a2'),)
    early_correction = replace(new,revised_at=ts(7),available_at=ts(8))
    feature = split_adjusted_feature_prices([bar()],[old,early_correction],as_of=ts(10))[0]
    assert feature.open == 100.
    assert feature.available_at == early_correction.available_at
    assert feature.selected_action_versions == (('S','A','a2'),)


def test_f2_corrected_dividend_amount_date_and_unknown_order():
    old = action(action_type='dividend', split_ratio=None, cash_amount=1., payable_at=ts(9))
    new = replace(old, cash_amount=3., revised_at=ts(7), available_at=ts(8), revision_id='a2')
    result = economic_acquisition_cost(bar('2020-01-10',100.), bar(), [old,new], NoFX())
    assert result.foregone_distributions == 3.
    ambiguous = replace(new, revised_at=None)
    with pytest.raises(ValueError, match='PIT_AMBIGUOUS_VINTAGE'):
        economic_acquisition_cost(bar('2020-01-10'), bar(), [replace(old,revised_at=None),ambiguous], NoFX())


@pytest.mark.parametrize('horizon,fill_day,maturity', [
    (5, '2020-01-09', datetime(2020, 1, 16, tzinfo=UTC)),
    (20, '2020-01-31', datetime(2020, 1, 31, 21, 1, tzinfo=UTC)),
    (60, '2020-03-30', datetime(2020, 3, 30, 20, 1, tzinfo=UTC)),
])
def test_r1_unrelated_full_history_preserves_economics_maturity_and_training_usability(
    horizon, fill_day, maturity,
):
    # Break caught: attaching distinct later identities to a completed target.
    assert nth_subsequent_open('XNYS', date(2020, 1, 2), horizon).date().isoformat() == fill_day
    history = []
    for year in range(2020, 2024):
        for month in (1, 4, 7, 10):
            ex_day = date(year, month, 6)
            while eligible_session_open('XNYS', ex_day) is None:
                ex_day += timedelta(days=1)
            known = datetime.combine(ex_day, datetime.min.time(), UTC) - timedelta(days=2)
            history.append(action(action_id=f'{year}-{month}', action_type='dividend',
                split_ratio=None, cash_amount=1., ex_date=ex_day.isoformat(),
                available_at=known, revised_at=known, payable_at=known+timedelta(days=12)))
    base = economic_acquisition_cost(bar(fill_day), bar(), history[:1], NoFX())
    full = economic_acquisition_cost(bar(fill_day), bar(), iter(reversed(history)), NoFX())
    assert full.total == base.total == 101.
    assert full.cashflows == base.cashflows
    assert full.label_matures_at == base.label_matures_at == maturity
    assert full.selected_action_versions == base.selected_action_versions == (('S', '2020-1', 'a1'),)
    for year in (2021, 2022, 2023):
        training_cutoff = datetime(year, 1, 1, tzinfo=UTC)
        assert full.label_matures_at <= training_cutoff


@pytest.mark.parametrize('old_date,new_date,total', [
    ('2020-01-06', '2020-01-13', 100.),
    ('2020-01-13', '2020-01-06', 200.),
    ('2020-01-06', '2020-01-02', 100.),
])
def test_r1_correction_crossing_window_keeps_evidence_without_unrelated_dependencies(old_date,new_date,total):
    # Break caught: filtering current dates loses removal evidence; filtering old
    # dates loses additions; applying raw versions double-counts split economics.
    old = action(ex_date=old_date)
    correction = replace(old, ex_date=new_date, revised_at=ts(13), available_at=ts(14), revision_id='a2')
    unrelated = action(action_id='later', ex_date='2023-10-06',
        available_at=datetime(2023,10,4,tzinfo=UTC), revised_at=datetime(2023,10,4,tzinfo=UTC))
    result = economic_acquisition_cost(bar('2020-01-10'), bar(),
        [unrelated, correction, old, correction], NoFX())
    assert result.total == total
    assert result.label_matures_at == ts(14)
    assert result.selected_action_versions == (('S','A','a2'),)


def test_f3_valid_vintages_survive_and_compose_with_mapping_and_pit():
    old = bar(revised_at=ts(2,21))
    new = replace(old, open=102.,high=102.,low=102.,close=102., revised_at=ts(3),available_at=ts(4),revision_id='p2')
    mapping = Security(security_id='S',ticker='S',name='S',currency='HUF',region=Region.US,exchange='XNYS',active_from='2019-01-01',available_at=ts(1),revised_at=ts(1),revision_id='s1',source='mapping',quality=QualityTier.A)
    corrected = replace(mapping, ticker='NEW',revised_at=ts(3),available_at=ts(3),revision_id='s2')
    result = validate_ohlcv([old,new],securities=[mapping,corrected])
    assert result.valid_rows == [old,new]
    assert latest_known(result.valid_rows,ts(2)) is old
    assert latest_known(result.valid_rows,ts(5)) is new
    assert split_adjusted_feature_prices(result.valid_rows,[],as_of=ts(5))[0].close == 102.
    assert len(split_adjusted_feature_prices(result.valid_rows,[],as_of=ts(5))) == 1
    invalid_correction = replace(corrected,active_to='invalid')
    assert not validate_ohlcv([new],securities=[mapping,invalid_correction]).valid_rows
    changed_currency = replace(corrected,currency='EUR')
    assert not validate_ohlcv([old],securities=[mapping,changed_currency],as_of=ts(5)).valid_rows


def test_f3_discontinuity_anchor_cannot_use_later_price_revision():
    old = bar(revised_at=ts(2,21))
    correction = replace(old, open=10.,high=10.,low=10.,close=10.,revised_at=ts(6),available_at=ts(6),revision_id='p2')
    next_bar = bar('2020-01-03',100.)
    result = validate_ohlcv([old,correction,next_bar])
    assert next_bar in result.valid_rows
    assert old in result.valid_rows and correction in result.valid_rows
    # Admission preserves versions, but a later selected panel must be screened
    # again: its corrected Jan 2 anchor makes Jan 3's uncorrected 100 suspicious.
    with pytest.raises(ValueError, match='UNEXPLAINED_DISCONTINUITY'):
        split_adjusted_feature_prices(result.valid_rows, [], as_of=ts(7))


def test_f3_feature_panel_requires_and_accepts_same_pit_discontinuity_evidence():
    from quant_dca.canonical.validate import DiscontinuityEvidence
    rows = [bar(),bar('2020-01-03',10.)]
    evidence = DiscontinuityEvidence(security_id='S',prior_session='2020-01-02',session_date='2020-01-03',kind='market_move',source='verified',reference='e1',verified_at=rows[1].available_at)
    admitted = validate_ohlcv(rows,discontinuity_evidence=[evidence])
    assert admitted.valid_rows == rows
    assert split_adjusted_feature_prices(admitted.valid_rows,[],as_of=ts(5),discontinuity_evidence=admitted.discontinuity_evidence)[1].close == 10.


@pytest.mark.parametrize('exchange,day', [('XNYS','2020-01-04'),('XNYS','2020-07-03'),('XETR','2020-04-10')])
def test_f4_non_sessions_rejected_at_canonical_and_feature_and_execution(exchange,day):
    raw = replace(bar(exchange=exchange),session_date=day)
    assert not validate_ohlcv([raw]).valid_rows
    with pytest.raises(ValueError,match='SESSION'):
        split_adjusted_feature_prices([raw],[],as_of=ts(15))
    with pytest.raises(ValueError,match='SESSION'):
        economic_acquisition_cost(raw,raw,[],NoFX())


@pytest.mark.parametrize('exchange,day', [('XNYS','2020-03-09'),('XNYS','2020-11-27'),('XETR','2020-03-30'),('XLON','2020-12-24')])
def test_f4_actual_dst_and_early_close_clocks_bound_consumers(exchange,day):
    valid = bar(day,exchange=exchange)
    assert validate_ohlcv([valid]).valid_rows == [valid]
    assert split_adjusted_feature_prices([valid],[],as_of=valid.available_at)[0].close == 100.
    for field in ('session_open_at','session_close_at'):
        bad = replace(valid,**{field:getattr(valid,field)-timedelta(hours=1)})
        assert not validate_ohlcv([bad]).valid_rows
        with pytest.raises(ValueError,match='SESSION'):
            split_adjusted_feature_prices([bad],[],as_of=valid.available_at)
        with pytest.raises(ValueError,match='SESSION'):
            economic_acquisition_cost(bad,bad,[],NoFX())


@pytest.mark.parametrize('actions', [[],[action()]])
def test_f5_actual_feature_provenance_writes_and_verified_reads_deterministically(tmp_path,actions):
    feature = split_adjusted_feature_prices([bar()],actions,as_of=ts(10))[0]
    frame = pd.DataFrame([asdict(feature)],dtype=object)
    digest = 'a'*64
    lineage = FeatureLineage(feature=feature.feature,provider='fixture',source_snapshot=digest,transform='split_adjusted_feature_prices',availability_rule='as_of',source_observations=(feature.revision_id,),source_timestamps=(feature.available_at,))
    first = write_snapshot(frame,'features',ts(10),root=tmp_path,source_hashes=[digest],lineage=[lineage])
    second = write_snapshot(frame,'features',ts(10),root=tmp_path,source_hashes=[digest],lineage=[lineage])
    assert first == second
    assert read_snapshot_metadata(first)['data_sha256'] == snapshot_hash(frame)
    assert lookup_lineage(first,feature.feature) == (lineage,)
    read = pq.read_table(first.path).to_pylist()[0]
    assert tuple(read['applied_action_ids']) == feature.applied_action_ids
    assert tuple(read['input_sources']) == feature.input_sources


def test_f6_actual_feature_object_rejected_as_fill_baseline_and_readjustment():
    raw = bar('2020-01-03')
    feature = split_adjusted_feature_prices([raw],[action()],as_of=ts(10))[0]
    for fill,baseline in [(feature,bar()),(raw,feature)]:
        with pytest.raises((TypeError,ValueError),match='RAW'):
            economic_acquisition_cost(fill,baseline,[],NoFX())
    for adjusted in (feature,replace(raw,price_basis='split_adjusted_feature')):
        with pytest.raises((TypeError,ValueError),match='RAW'):
            split_adjusted_feature_prices([adjusted],[action()],as_of=ts(10))
