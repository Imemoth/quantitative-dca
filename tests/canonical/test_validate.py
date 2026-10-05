from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from quant_dca.types import OHLCV, Observation, QualityTier, Region, Security
from quant_dca.canonical.validate import DiscontinuityEvidence, validate_observations, validate_ohlcv


def stamp(day=3, hour=22):
    return datetime(2020, 1, day, hour, 30 if hour == 14 else 0, tzinfo=timezone.utc)


def bar(**changes):
    values = dict(security_id='s1', session_date='2020-01-03', open=100., high=110., low=90., close=100., volume=100., currency='USD', region=Region.US, exchange='XNYS', session_open_at=stamp(hour=14), session_close_at=stamp(hour=21), available_at=stamp(), source='fixture', revision_id='r1', quality=QualityTier.B)
    return OHLCV(**(values | changes))


def test_high_below_low_is_quarantined():
    result = validate_ohlcv([{'high': 9.0, 'low': 10.0, 'volume': 100.0}])
    assert len(result.valid_rows) == 0
    assert result.quarantined_rows[0].reason == 'HIGH_BELOW_LOW'


@pytest.mark.parametrize('change', [({'open': 111}), ({'close': 89})])
def test_price_outside_daily_range_is_quarantined(change):
    assert 'PRICE_OUTSIDE_RANGE' in validate_ohlcv([bar(**change)]).quarantined_rows[0].reasons


@pytest.mark.parametrize('field,value,reason', [('volume', -1, 'NEGATIVE_VOLUME'), ('close', 0, 'NONPOSITIVE_PRICE'), ('open', -2, 'NONPOSITIVE_PRICE'), ('high', float('inf'), 'NONFINITE_PRICE'), ('low', float('nan'), 'NONFINITE_PRICE'), ('volume', float('inf'), 'NONFINITE_VOLUME'), ('close', None, 'MISSING_PRICE')])
def test_numeric_quarantine_preserves_original(field, value, reason):
    raw = bar(**{field: value})
    result = validate_ohlcv([raw])
    assert result.quarantined_rows[0].row is raw
    assert reason in result.quarantined_rows[0].reasons
    assert result.reasons[reason] == 1
    assert not result.valid_rows


def test_conflicting_and_identical_duplicates_quarantine_every_member():
    for second in (bar(), bar(close=105)):
        result = validate_ohlcv([bar(), second])
        assert len(result.quarantined_rows) == 2
        assert all('DUPLICATE_SESSION' in q.reasons for q in result.quarantined_rows)


def jump_rows():
    return [bar(), bar(session_date='2020-01-06', session_open_at=stamp(6, 14), session_close_at=stamp(6, 21), available_at=stamp(6), open=10, high=11, low=9, close=10)]


def later_bar(day, close, **changes):
    values = dict(session_date=f'2020-01-{day:02d}', session_open_at=stamp(day, 14), session_close_at=stamp(day, 21), available_at=stamp(day), open=close, high=close * 1.1, low=close * .9, close=close)
    return bar(**(values | changes))


def test_unexplained_jump_is_uncertain_quarantine_without_clipping():
    rows = jump_rows()
    result = validate_ohlcv(rows)
    assert result.valid_rows == [rows[0]]
    assert result.quarantined_rows[0].row is rows[1]
    assert 'UNEXPLAINED_DISCONTINUITY' in result.quarantined_rows[0].reasons
    assert rows[1].close == 10


@pytest.mark.parametrize('kind', ['corporate_action', 'market_move'])
def test_verified_extreme_preserved_with_evidence(kind):
    rows = jump_rows()
    evidence = DiscontinuityEvidence(security_id='s1', prior_session='2020-01-03', session_date='2020-01-06', kind=kind, source='fixture verification', reference='evidence-123', verified_at=stamp(6))
    result = validate_ohlcv(rows, discontinuity_evidence=[evidence])
    assert result.valid_rows == rows
    assert not result.quarantined_rows
    assert result.discontinuity_evidence == [evidence]


def test_future_evidence_cannot_retroactively_validate_old_bar():
    rows = jump_rows()
    evidence = DiscontinuityEvidence(security_id='s1', prior_session='2020-01-03', session_date='2020-01-06', kind='market_move', source='fixture verification', reference='future-evidence', verified_at=stamp(7))
    result = validate_ohlcv(rows, discontinuity_evidence=[evidence])
    assert result.valid_rows == [rows[0]]
    assert result.discontinuity_evidence == []
    assert 'UNEXPLAINED_DISCONTINUITY' in result.quarantined_rows[0].reasons
    assert rows[1].available_at == stamp(6)


def test_timezone_equivalent_evidence_is_available_for_bar():
    rows = jump_rows()
    equivalent = datetime(2020, 1, 7, 0, tzinfo=timezone(timedelta(hours=2)))
    evidence = DiscontinuityEvidence(security_id='s1', prior_session='2020-01-03', session_date='2020-01-06', kind='market_move', source='fixture verification', reference='equivalent-instant', verified_at=equivalent)
    result = validate_ohlcv(rows, discontinuity_evidence=[evidence])
    assert result.valid_rows == rows
    assert result.discontinuity_evidence == [evidence]


@pytest.mark.parametrize('middle_change', [{'volume': -1}, {'source': ''}])
def test_quarantined_middle_row_never_becomes_discontinuity_anchor(middle_change):
    rows = [bar(), later_bar(6, 10, **middle_change), later_bar(7, 100)]
    result = validate_ohlcv(rows)
    assert result.valid_rows == [rows[0], rows[2]]
    assert result.quarantined_rows[0].row is rows[1]


def test_discontinuity_threshold_is_configurable():
    rows = [bar(), bar(session_date='2020-01-06', session_open_at=stamp(6, 14), session_close_at=stamp(6, 21), available_at=stamp(6), open=49, high=51, low=48, close=50)]
    assert not validate_ohlcv(rows, max_price_ratio=3).quarantined_rows
    assert 'UNEXPLAINED_DISCONTINUITY' in validate_ohlcv(rows, max_price_ratio=1.5).quarantined_rows[0].reasons


@pytest.mark.parametrize('change', [{'source': ''}, {'reference': ''}, {'kind': 'rumor'}, {'verified_at': datetime(2020, 1, 6)}])
def test_discontinuity_evidence_requires_auditable_provenance(change):
    values = dict(security_id='s1', prior_session='2020-01-03', session_date='2020-01-06', kind='market_move', source='fixture verification', reference='evidence-123', verified_at=stamp(6))
    with pytest.raises(ValueError):
        DiscontinuityEvidence(**(values | change))


def test_unordered_rows_not_silently_sorted_and_compared():
    result = validate_ohlcv(list(reversed(jump_rows())))
    assert 'NONMONOTONIC_SESSION' in result.quarantined_rows[0].reasons


@pytest.mark.parametrize('change,reason', [({'currency': 'usd'}, 'INVALID_CURRENCY'), ({'source': ''}, 'MISSING_SOURCE'), ({'quality': None}, 'INVALID_QUALITY'), ({'available_at': stamp(hour=20)}, 'AVAILABILITY_BEFORE_SESSION_CLOSE'), ({'published_at': stamp(4)}, 'AVAILABILITY_BEFORE_PUBLICATION'), ({'session_open_at': stamp(hour=22)}, 'INVALID_SESSION_CHRONOLOGY'), ({'session_date': 'not-a-date'}, 'INVALID_SESSION_DATE')])
def test_canonical_metadata(change, reason):
    result = validate_ohlcv([bar(**change)])
    assert reason in result.quarantined_rows[0].reasons


def test_missing_empty_and_invalid_security_identity_is_quarantined_without_mapping():
    from dataclasses import asdict
    missing = asdict(bar())
    del missing['security_id']
    cases = [(missing, 'MISSING_SECURITY_ID'), (bar(security_id=''), 'MISSING_SECURITY_ID'), (bar(security_id='bad id'), 'INVALID_SECURITY_ID'), (bar(security_id=7), 'INVALID_SECURITY_ID')]
    for row, reason in cases:
        result = validate_ohlcv([row])
        assert result.quarantined_rows[0].row is row
        assert reason in result.quarantined_rows[0].reasons


def test_dict_timestamp_must_be_aware():
    from dataclasses import asdict
    row = asdict(bar())
    row['available_at'] = datetime(2020, 1, 3)
    assert 'INVALID_TIMESTAMP:available_at' in validate_ohlcv([row]).quarantined_rows[0].reasons


@pytest.mark.parametrize('field', ['available_at', 'session_open_at', 'session_close_at'])
def test_required_timestamps_cannot_be_omitted_from_mapping_rows(field):
    from dataclasses import asdict
    row = asdict(bar())
    del row[field]
    assert f'MISSING_TIMESTAMP:{field}' in validate_ohlcv([row]).quarantined_rows[0].reasons


def security(**changes):
    return Security(**(dict(security_id='s1', ticker='S', name='Security', currency='USD', region=Region.US, exchange='XNYS', active_from='2019-01-01', available_at=stamp(2), quality=QualityTier.B, source='fixture', revision_id='r1') | changes))


@pytest.mark.parametrize('mapping,reason', [([], 'MISSING_SECURITY_MAPPING'), ([security(currency='EUR')], 'CURRENCY_MAPPING_MISMATCH'), ([security(exchange='XNAS')], 'EXCHANGE_MAPPING_MISMATCH'), ([security(region=Region.EU)], 'REGION_MAPPING_MISMATCH'), ([security(active_from='2021-01-01')], 'MISSING_SECURITY_MAPPING'), ([security(active_to='2020-01-03')], 'MISSING_SECURITY_MAPPING'), ([security(active_to='not-a-date')], 'MISSING_SECURITY_MAPPING'), ([security(available_at=stamp(4))], 'MISSING_SECURITY_MAPPING'), ([security(), security()], 'AMBIGUOUS_SECURITY_MAPPING')])
def test_historical_security_mapping(mapping, reason):
    assert reason in validate_ohlcv([bar()], securities=mapping).quarantined_rows[0].reasons


def test_valid_historical_mapping():
    assert validate_ohlcv([bar()], securities=[security()]).valid_rows == [bar()]


def test_observation_missing_value_is_unavailable_not_tier_c():
    row = Observation(series='GDP', entity_id=None, observation_date='2020-01-02', value=None, available_at=stamp(), source='fixture', revision_id='r1', quality=QualityTier.A)
    result = validate_observations([row])
    assert result.quarantined_rows[0].reason == 'MISSING_VALUE'
    assert row.quality == QualityTier.A
    assert validate_observations([replace(row, value=-1)]).valid_rows


def test_threshold_is_validated():
    with pytest.raises(ValueError):
        validate_ohlcv([], max_price_ratio=1)
