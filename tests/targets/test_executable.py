from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import ast
from pathlib import Path

import pytest

from quant_dca.calendars.service import eligible_session_close, next_eligible_open
from quant_dca.fx.conversion import FXService
from quant_dca.types import OHLCV, CorporateAction, FXQuote, Security, QualityTier, Region
from quant_dca.targets.executable import best_executable_improvement
from quant_dca.targets.builder import ActionCoverage, build_targets

UTC = timezone.utc
END = datetime(2023, 12, 31, 23, 59, tzinfo=UTC)


def fixture(signal=datetime(2023, 1, 3, 21, tzinfo=UTC), prices=None):
    rows = []
    instant = signal
    for i in range(61):
        instant = next_eligible_open('XNYS', instant)
        close = eligible_session_close('XNYS', instant.date())
        price = prices[i] if prices else 100.
        rows.append(OHLCV(security_id='S', session_date=instant.date().isoformat(),
            open=price, high=price, low=price, close=price, volume=1000., currency='USD',
            exchange='XNYS', region=Region.US, session_open_at=instant, session_close_at=close,
            available_at=close+timedelta(minutes=1), quality=QualityTier.A,
            source='fixture', revision_id='v1'))
    coverage = ActionCoverage('S', rows[0].session_date, rows[-1].session_date,
                              rows[-1].available_at, 'audit', 'complete-action-history')
    listing = Security(security_id='S', ticker='S', name='fixture', currency='USD',
        exchange='XNYS', region=Region.US, active_from='2010-01-01',
        available_at=datetime(2010,1,1,tzinfo=UTC), source='fixture', revision_id='v1', quality=QualityTier.A)
    quotes = [FXQuote(base_currency='USD', quote_currency='HUF', rate=300.,
        fixing_at=r.session_open_at-timedelta(minutes=1), available_at=r.session_open_at,
        quality=QualityTier.A, source='fixture', revision_id='v1') for r in rows]
    return dict(prices=rows, actions=(), security_id='S', exchange='XNYS', signal_at=signal,
                label_as_of=END, action_coverage=coverage, listing_history=(listing,),
                fx_service=FXService(quotes, max_age=timedelta(days=5)))


def event(args, kind='dividend', index=1, **kw):
    r = args['prices'][index]
    return CorporateAction(security_id='S', action_id='A', action_type=kind,
        ex_date=r.session_date, currency='USD', exchange='XNYS', region=Region.US,
        available_at=args['signal_at'], quality=QualityTier.A, source='fixture', revision_id='v1', **kw)


def test_better_entry_uses_future_opens_not_lows():
    assert best_executable_improvement(100., [101., 98., 99.]) == .02


@pytest.mark.parametrize('baseline,opens', [(0,[1]), (100,[]), (100,[float('nan')]), (True,[1])])
def test_scalar_rejects_invalid_inputs(baseline, opens):
    with pytest.raises(ValueError):
        best_executable_improvement(baseline, opens)


def test_horizon_numbering_returns_and_directions():
    prices = [100.]*61
    prices[5], prices[20], prices[60] = 105., 98., 110.
    row = build_targets(**fixture(prices=prices))
    assert row.return_5d_local == pytest.approx(.05)
    assert row.return_20d_local == pytest.approx(-.02)
    assert row.return_60d_huf == pytest.approx(.1)
    assert (row.direction_5d_local, row.direction_20d_local, row.direction_60d_huf) == (True, False, True)
    assert row.executable_min_return_5d_local == 0
    assert row.executable_min_return_20d_local == 0
    assert row.baseline_open_at == datetime(2023,1,4,14,30,tzinfo=UTC)


@pytest.mark.parametrize('low,expected5,expected20', [(98.5,True,False),(98.5001,False,False),(97.,True,True),(97.0001,True,False)])
def test_literal_thresholds(low, expected5, expected20):
    row = build_targets(**fixture(prices=[100.]+[low]*60))
    assert row.better_entry_5d_local is expected5
    assert row.better_entry_20d_huf is expected20


def test_dividend_drop_not_better_entry_and_payable_fx():
    args = fixture(prices=[100.]+[98.]*60)
    payable = args['prices'][10].session_open_at
    args['actions'] = (event(args, cash_amount=2., payable_at=payable),)
    row = build_targets(**args)
    assert row.executable_min_return_5d_local == 0
    assert row.better_entry_5d_local is False
    assert row.return_5d_local == 0
    dividends = [f for c in row.economic_costs for f in c.cashflows if f.kind == 'foregone_dividend']
    assert dividends and all(f.cashflow_at == payable for f in dividends)
    assert all(f.fx_quote.fixing_at <= payable for f in dividends)


def test_split_invariance():
    args = fixture(prices=[100.]+[50.]*60)
    args['actions'] = (event(args, 'split', split_ratio=2.),)
    row = build_targets(**args)
    assert row.return_60d_local == 0
    assert row.executable_min_return_20d_huf == 0


def test_huf_fx_is_not_local_return():
    args = fixture()
    quotes = [FXQuote(base_currency='USD', quote_currency='HUF', rate=300. if i == 0 else 330.,
        fixing_at=r.session_open_at, available_at=r.session_open_at, source='fixture',
        revision_id='v1', quality=QualityTier.A) for i,r in enumerate(args['prices'])]
    args['fx_service'] = FXService(quotes, max_age=timedelta(days=5))
    row = build_targets(**args)
    assert row.return_5d_local == 0
    assert row.return_5d_huf == pytest.approx(.1)


def test_holiday_gap_and_missing_open_no_skipping():
    args = fixture(datetime(2023,1,13,21,tzinfo=UTC))
    assert build_targets(**args).baseline_open_at == datetime(2023,1,17,14,30,tzinfo=UTC)
    args['prices'].pop(1)
    row = build_targets(**args)
    assert row.censor_reason == 'MISSING_ELIGIBLE_OPEN'
    assert row.return_5d_local is None


def test_coverage_absence_not_verified_none():
    args = fixture()
    args['action_coverage'] = None
    assert build_targets(**args).censor_reason == 'ACTION_COVERAGE_UNAVAILABLE'


def test_delisting_and_unsupported_actions_fail_closed():
    args = fixture()
    args['listing_history'] = (replace(args['listing_history'][0], active_to=args['prices'][10].session_date),)
    assert build_targets(**args).censor_reason == 'TERMINAL_LISTING_WITHIN_WINDOW'
    args = fixture()
    args['actions'] = (event(args, 'merger'),)
    assert build_targets(**args).censor_reason == 'UNSUPPORTED_CORPORATE_ACTION'


class NoFX:
    def resolve(self, *args):
        pytest.fail('FX queried before dependency preflight')


@pytest.mark.parametrize('case', ['horizon','payable','revision','coverage'])
def test_development_bounds_before_any_fx(case):
    args = fixture(datetime(2023,12,29,21,tzinfo=UTC)) if case == 'horizon' else fixture()
    future = datetime(2024,1,2,15,tzinfo=UTC)
    if case == 'payable':
        args['actions'] = (event(args, cash_amount=2., payable_at=future),)
    if case == 'revision':
        args['prices'][5] = replace(args['prices'][5], available_at=future, revised_at=future)
    if case == 'coverage':
        args['action_coverage'] = replace(args['action_coverage'], available_at=future)
    args['fx_service'] = NoFX()
    row = build_targets(**args)
    assert row.censor_reason.startswith('DEVELOPMENT_')
    assert row.target_end_timestamp is None


def test_maturity_includes_late_raw_and_action_revisions():
    args = fixture()
    late = datetime(2023,7,3,20,tzinfo=UTC)
    args['prices'][2] = replace(args['prices'][2], available_at=late, revised_at=late)
    a = replace(event(args, cash_amount=0., payable_at=args['prices'][4].session_open_at),
                published_at=args['signal_at'])
    args['actions'] = (a, replace(a, revision_id='v2', revised_at=late, available_at=late+timedelta(days=1)))
    row = build_targets(**args)
    assert row.target_end_timestamp == late+timedelta(days=1)
    assert row.selected_actions[0].revision_id == 'v2'


@pytest.mark.parametrize('year', [2015,2022])
def test_development_years_supported(year):
    row = build_targets(**fixture(datetime(year,1,5,22,tzinfo=UTC)))
    assert row.return_60d_local == 0


def test_adjusted_prices_not_fills():
    args = fixture()
    args['prices'][1] = replace(args['prices'][1], price_basis='adjusted')
    with pytest.raises(ValueError, match='RAW'):
        build_targets(**args)


def test_short_labels_survive_censored_60d_with_own_maturity():
    args = fixture(datetime(2023,11,1,20,tzinfo=UTC))
    args['prices'] = [r for r in args['prices'] if r.session_open_at.year == 2023]
    args['action_coverage'] = tuple(ActionCoverage('S', args['prices'][0].session_date,
        args['prices'][i].session_date, args['prices'][i].available_at, 'audit', f'coverage-{i}')
        for i in (5,20))
    row = build_targets(**args)
    assert row.return_5d_local == 0
    assert row.return_20d_local == 0
    assert row.return_60d_local is None
    assert row.horizons[0].target_end_timestamp == args['prices'][5].available_at
    assert row.horizons[1].target_end_timestamp == args['prices'][20].available_at
    assert row.horizons[2].censor_reason == 'DEVELOPMENT_WINDOW_UNAVAILABLE'
    assert row.target_end_timestamp is None


def test_features_do_not_import_target_pipeline():
    root = Path(__file__).parents[2] / 'src' / 'quant_dca' / 'features'
    for path in root.rglob('*.py'):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert not any('targets' in n.name.split('.') for n in node.names), path
            if isinstance(node, ast.ImportFrom):
                assert 'targets' not in (node.module or '').split('.'), path
                assert not any(n.name == 'targets' for n in node.names), path


def test_split_then_dividend_units_and_corrected_action_history():
    args = fixture(prices=[100.,50.]+[49.]*59)
    split = event(args, 'split', split_ratio=2.)
    dividend = replace(event(args, index=2, cash_amount=1.,
        payable_at=args['prices'][7].session_open_at), action_id='D')
    args['actions'] = (split, dividend)
    row = build_targets(**args)
    assert row.return_5d_local == 0
    assert row.better_entry_5d_local is False
    assert row.horizons[0].economic_costs[-1].foregone_distributions == 600.
    original = replace(dividend, published_at=args['signal_at'])
    late = datetime(2023,8,1,12,tzinfo=UTC)
    moved = replace(original, ex_date=args['prices'][30].session_date,
        payable_at=args['prices'][35].session_open_at, available_at=late, revised_at=late, revision_id='v2')
    args['actions'] = (split, original, moved)
    row = build_targets(**args)
    assert row.return_5d_local == pytest.approx(-.02)
    assert row.horizons[0].target_end_timestamp == late
    assert moved in row.horizons[0].selected_actions
    assert original in row.horizons[0].action_versions


def test_payable_fx_changes_huf_dividend_economics():
    args = fixture(prices=[100.]+[98.]*60)
    payable = args['prices'][10].session_open_at + timedelta(hours=2)
    args['actions'] = (event(args, cash_amount=2., payable_at=payable),)
    quotes = [FXQuote(base_currency='USD', quote_currency='HUF', rate=300.,
        fixing_at=r.session_open_at, available_at=r.session_open_at,
        quality=QualityTier.A, source='fixture', revision_id='v1') for r in args['prices']]
    quotes.append(replace(quotes[10], rate=600., fixing_at=payable, available_at=payable))
    args['fx_service'] = FXService(quotes, max_age=timedelta(days=5))
    row = build_targets(**args)
    assert row.return_5d_local == 0
    assert row.return_5d_huf == pytest.approx(.02)


def test_every_consumed_raw_revision_is_retained_and_matures_label():
    args = fixture()
    original = replace(args['prices'][2], published_at=args['prices'][2].available_at,
        available_at=datetime(2023,8,2,12,tzinfo=UTC))
    corrected = replace(original, revision_id='v2', revised_at=datetime(2023,7,1,12,tzinfo=UTC),
        available_at=datetime(2023,7,1,12,tzinfo=UTC))
    args['prices'][2] = corrected
    args['prices'].append(original)
    row = build_targets(**args)
    assert row.horizons[0].target_end_timestamp == original.available_at
    assert original in row.horizons[0].raw_versions
    assert row.horizons[0].raw_bars[2] == corrected


@pytest.mark.parametrize('field,value', [('open',0),('volume',-1),('high',99),('source','')])
def test_invalid_raw_panel_never_becomes_fill(field, value):
    args = fixture()
    args['prices'][1] = replace(args['prices'][1], **{field:value})
    with pytest.raises(ValueError):
        build_targets(**args)


def test_intraday_signal_rejected():
    args = fixture()
    args['signal_at'] = datetime(2023,1,3,18,tzinfo=UTC)
    with pytest.raises(ValueError, match='EOD'):
        build_targets(**args)


def test_fx_after_fill_unusable():
    args = fixture()
    args['fx_service'] = FXService([FXQuote(base_currency='USD', quote_currency='HUF', rate=300.,
        fixing_at=args['prices'][0].session_open_at+timedelta(minutes=1),
        available_at=args['prices'][0].session_open_at+timedelta(minutes=1),
        source='fixture', revision_id='v1', quality=QualityTier.A)], max_age=None)
    row = build_targets(**args)
    assert row.horizons[0].censor_reason.startswith('FX_UNAVAILABLE')
    assert row.return_5d_huf is None


def test_terminal_action_on_baseline_open_is_not_silently_ignored():
    args = fixture()
    args['actions'] = (event(args, 'delisting', index=0),)
    args['fx_service'] = NoFX()
    assert build_targets(**args).horizons[0].censor_reason == 'UNSUPPORTED_CORPORATE_ACTION'


def test_terminal_after_short_window_only_censors_long_horizons():
    args = fixture()
    args['listing_history'] = (replace(args['listing_history'][0], active_to=args['prices'][10].session_date),)
    row = build_targets(**args)
    assert row.return_5d_local == 0
    assert row.return_20d_local is None
    assert row.horizons[1].censor_reason == 'TERMINAL_LISTING_WITHIN_WINDOW'


@pytest.mark.parametrize('field', ['signal_at', 'label_as_of'])
def test_2024_cutoff_not_authorized(field):
    args = fixture()
    args[field] = datetime(2024,1,1,tzinfo=UTC)
    args['fx_service'] = NoFX()
    with pytest.raises(ValueError, match='DEVELOPMENT'):
        build_targets(**args)


def test_large_split_requires_audited_discontinuity_evidence():
    from quant_dca.canonical.validate import DiscontinuityEvidence
    args = fixture(prices=[100.]+[10.]*60)
    args['actions'] = (event(args, 'split', split_ratio=10.),)
    with pytest.raises(ValueError, match='UNEXPLAINED_DISCONTINUITY'):
        build_targets(**args)
    evidence = DiscontinuityEvidence('S', args['prices'][0].session_date,
        args['prices'][1].session_date, 'corporate_action', 'audit', 'verified-split',
        args['prices'][1].available_at)
    args['discontinuity_evidence'] = (evidence,)
    row = build_targets(**args)
    assert row.return_60d_local == 0
    assert row.horizons[0].discontinuity_evidence == (evidence,)


class UnboundedHistory:
    def __iter__(self):
        pytest.fail('unbounded history was consumed')


def test_all_out_of_bound_horizons_do_not_touch_any_history():
    args = fixture(datetime(2023,12,29,21,tzinfo=UTC))
    for name in ('prices', 'actions', 'listing_history', 'action_coverage', 'discontinuity_evidence'):
        args[name] = UnboundedHistory()
    args['fx_service'] = NoFX()
    row = build_targets(**args)
    assert [h.censor_reason for h in row.horizons] == ['DEVELOPMENT_WINDOW_UNAVAILABLE'] * 3


@pytest.mark.parametrize('name', ['prices', 'actions', 'listing_history', 'action_coverage', 'discontinuity_evidence'])
def test_mixed_horizons_reject_lazy_ingress_without_consumption(name):
    args = fixture(datetime(2023,11,1,20,tzinfo=UTC))
    args[name] = UnboundedHistory()
    args['fx_service'] = NoFX()
    with pytest.raises(TypeError, match='MATERIALIZED_TARGET_HISTORY_REQUIRED'):
        build_targets(**args)


@pytest.mark.parametrize('kind', ['bar', 'action', 'listing', 'coverage', 'discontinuity', 'publication'])
def test_entire_snapshot_is_bounded_even_unrelated_records(kind):
    from quant_dca.canonical.validate import DiscontinuityEvidence
    args = fixture()
    future = datetime(2024,1,2,15,tzinfo=UTC)
    if kind == 'bar':
        args['prices'].append(replace(args['prices'][0], security_id='OTHER', session_date='2024-01-02'))
    elif kind == 'action':
        args['actions'] = (replace(event(args, 'split', split_ratio=2.), security_id='OTHER', ex_date='2024-01-02'),)
    elif kind == 'listing':
        args['listing_history'] += (replace(args['listing_history'][0], security_id='OTHER', active_to='2024-01-02'),)
    elif kind == 'coverage':
        args['action_coverage'] = (args['action_coverage'], replace(args['action_coverage'], security_id='OTHER', end_session='2024-01-02'))
    elif kind == 'discontinuity':
        args['discontinuity_evidence'] = (DiscontinuityEvidence('OTHER','2023-12-29','2024-01-02',
            'market_move','fixture','out-of-bound',future),)
    else:
        args['prices'].append(replace(args['prices'][0], security_id='OTHER', published_at=future, available_at=future))
    args['fx_service'] = NoFX()
    row = build_targets(**args)
    assert all(h.censor_reason == 'DEVELOPMENT_DEPENDENCY_UNAVAILABLE' for h in row.horizons)


def test_entire_snapshot_observations_respect_declared_knowledge_cutoff():
    args = fixture()
    args['label_as_of'] = datetime(2023,9,1,tzinfo=UTC)
    args['prices'].append(replace(args['prices'][0], security_id='OTHER', session_date='2023-10-02'))
    args['fx_service'] = NoFX()
    row = build_targets(**args)
    assert row.horizons[0].censor_reason == 'LABEL_EVIDENCE_NOT_YET_AVAILABLE'


def test_pre2010_listing_inception_with_bounded_knowledge_is_valid():
    args = fixture()
    args['listing_history'] = (replace(args['listing_history'][0], active_from='1980-12-12',
        published_at=args['signal_at'], available_at=args['signal_at']),)
    row = build_targets(**args)
    assert row.return_5d_local == 0
    assert row.return_60d_huf == 0
    assert row.horizons[0].selected_listing.active_from == '1980-12-12'


def test_pre2010_coverage_start_reference_with_bounded_audit_is_valid():
    args = fixture()
    args['action_coverage'] = replace(args['action_coverage'], start_session='2009-01-02')
    row = build_targets(**args)
    assert row.return_5d_local == 0
    assert row.return_60d_huf == 0


def test_pre2010_listing_retains_short_labels_at_development_end():
    args = fixture(datetime(2023,11,1,20,tzinfo=UTC))
    args['prices'] = [r for r in args['prices'] if r.session_open_at.year == 2023]
    args['action_coverage'] = replace(args['action_coverage'],
        end_session=args['prices'][-1].session_date, available_at=args['prices'][-1].available_at)
    args['listing_history'] = (replace(args['listing_history'][0], active_from='1980-12-12',
        published_at=args['signal_at'], available_at=args['signal_at']),)
    row = build_targets(**args)
    assert row.return_5d_local == 0
    assert row.return_20d_huf == 0
    assert row.horizons[2].censor_reason == 'DEVELOPMENT_WINDOW_UNAVAILABLE'


@pytest.mark.parametrize('kind', ['listing_publication','price_observation','action_observation'])
def test_pre2010_observations_and_knowledge_remain_out_of_bounds(kind):
    args = fixture()
    if kind == 'listing_publication':
        args['listing_history'] = (replace(args['listing_history'][0], active_from='1980-12-12',
            published_at=datetime(2009,1,1,tzinfo=UTC)),)
    elif kind == 'price_observation':
        args['prices'].append(replace(args['prices'][0], security_id='OTHER', session_date='2009-01-02'))
    else:
        args['actions'] = (event(args, 'split', split_ratio=2.),)
        args['actions'] = (replace(args['actions'][0], ex_date='2009-01-02'),)
    args['fx_service'] = NoFX()
    assert build_targets(**args).censor_reason == 'DEVELOPMENT_DEPENDENCY_UNAVAILABLE'
