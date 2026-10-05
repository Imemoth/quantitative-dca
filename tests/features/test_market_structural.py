from dataclasses import replace
from datetime import timedelta
import pytest

from test_price_vol_liquidity import bars, build
from quant_dca.types import Observation, QualityTier, Region
from quant_dca.features.relative import SectorClassification
from quant_dca.features.fundamentals import ReportedFundamentals
from quant_dca.features.valuation import ValuationPrice


def api():
    try:
        from quant_dca.features.market_structural import build_market_structural_features, StructuralConfig, MarketBinding
    except ImportError:
        pytest.fail('market/structural producer missing')
    return build_market_structural_features, StructuralConfig, MarketBinding


def fixture():
    stock = build(bars(253))
    at = stock.features[0].as_of
    sec = stock.selected_listings[0]
    sector = SectorClassification(security_id='TEST', sector_id='Technology', active_from=sec.active_from,
        available_at=sec.available_at, quality=QualityTier.A, source='fixture', revision_id='v1')
    report = ReportedFundamentals(security_id='TEST', period_end='2020-01-01', published_at=sec.available_at,
        available_at=sec.available_at, currency='USD', per_share_basis='unadjusted', sector_id='Technology',
        valuation_period_basis='trailing_twelve_months', values={'diluted_shares': 1e8},
        quality=QualityTier.A, source='fixture', revision_id='v1', region=Region.US, exchange='XNYS')
    price = ValuationPrice(security_id='TEST', session_date=stock.sessions[-1], close=352., session_close_at=at,
        available_at=at, currency='USD', per_share_basis='unadjusted', price_basis='unadjusted',
        quality=QualityTier.A, source='fixture', revision_id='v1', region=Region.US, exchange='XNYS')
    vix = tuple(Observation(series='VIX', entity_id=None, observation_date=r.session_date,
        value=float(i*i+10), available_at=r.available_at, quality=QualityTier.A,
        source='fixture', revision_id='v1', region=Region.GLOBAL, exchange='XNYS', unit='index_points')
        for i, r in enumerate(stock.raw_bars[-43:]))
    return dict(as_of=at, role='train', security=sec, stock=stock, broad=stock, sector=stock,
        classifications=(sector,), reports=(report,), valuation_prices=(price,), vix=vix,
        fx_quotes=(), fx_max_age=timedelta(days=4))


def configured():
    builder, config, binding = api()
    args = fixture()
    args.update(config=config(sector_codes=(('Technology', 0),)),
        binding=binding(region=Region.US, broad_id='TEST', broad_exchange='XNYS',
                        sector_id='TEST', sector_exchange='XNYS', sector_label='Technology',
                        vix_series='VIX', vix_exchange='XNYS', vix_source='fixture', broad_source='fixture', sector_source='fixture'))
    return builder, args


def test_real_adjusted_producers_cover_ten_with_literal_values():
    builder, args = configured()
    out = builder(**args)
    values = {r.feature:r.value for r in out.features}
    assert len(values) == 10
    assert values['broad_market_momentum_20d_raw'] == pytest.approx(352/332-1)
    assert values['sector_momentum_60d_raw'] == pytest.approx(352/292-1)
    assert values['vix_level_raw'] == 1774.
    assert values['vix_acceleration_raw'] == 800.
    assert values['region_category'] == 0
    assert values['sector_category'] == 0
    assert values['market_cap_bucket'] == 2
    assert values['beta_bucket'] == 1
    assert out.beta == pytest.approx(1.)
    assert len(args['stock'].adjusted_close) == 253


def test_wrong_source_units_calendar_and_sector_fail_closed():
    builder, args = configured()
    for changes in ({'unit':'basis_points'}, {'exchange':'XLON'}, {'source':'unrelated'}):
        bad = tuple(replace(r, **changes) for r in args['vix'])
        with pytest.raises(ValueError):
            builder(**(args | {'vix':bad}))
    with pytest.raises(ValueError):
        builder(**(args | {'binding':replace(args['binding'], sector_label='Financials')}))


def test_future_vix_revision_not_used_missing_beta_not_padded():
    builder, args = configured()
    future = replace(args['vix'][-1], value=999999., available_at=args['as_of']+timedelta(days=1), revision_id='v2')
    out = builder(**(args | {'vix':args['vix']+(future,)}))
    assert {r.feature:r.value for r in out.features}['vix_level_raw'] == 1774.
    short = build(bars(252))
    out = builder(**(args | {'stock':replace(args['stock'], adjusted_close=short.adjusted_close, sessions=short.sessions)}))
    assert {r.feature:r.value for r in out.features}['beta_bucket'] is None


def test_request_rejected_without_consuming_lazy_inputs():
    builder, args = configured()
    class Bomb:
        def __iter__(self):
            raise AssertionError('input consumed')
    for changes in ({'role':'outer_oos'}, {'as_of':args['as_of'].replace(year=2024)}):
        with pytest.raises(ValueError):
            builder(**(args | changes | {'vix':Bomb(), 'reports':Bomb()}))


def test_quality_is_per_dependency_not_downgraded_by_unrelated_vix():
    builder,args=configured()
    out=builder(**(args|{'vix':tuple(replace(r,quality=QualityTier.C) for r in args['vix'])}))
    rows={r.feature:r for r in out.features}
    assert rows['vix_level_raw'].quality is QualityTier.C
    assert rows['market_cap_bucket'].quality is QualityTier.A


def test_last_known_vix_level_with_missing_latest_source_close():
    builder,args=configured()
    out=builder(**(args|{'vix':args['vix'][:-1]}))
    values={r.feature:r.value for r in out.features}
    assert values['vix_level_raw']==1691.
    assert values['vix_acceleration_raw'] is None


def test_declared_benchmark_source_bound_to_actual_raw_evidence():
    builder,args=configured()
    changed=replace(args['broad'],raw_bars=tuple(replace(r,source='unrelated') for r in args['broad'].raw_bars))
    with pytest.raises(ValueError,match='SOURCE'):
        builder(**(args|{'broad':changed}))


def test_usd_cap_conversion_uses_known_spot_and_equality_upper_bucket():
    from quant_dca.types import FXQuote
    builder,args=configured()
    at=args['as_of']
    euro_stock=build(bars(253,currency='EUR'))
    args.update(security=euro_stock.selected_listings[0],stock=euro_stock)
    price=replace(args['valuation_prices'][0],currency='EUR',close=10.)
    report=replace(args['reports'][0],currency='EUR')
    quote=FXQuote(base_currency='EUR',quote_currency='USD',rate=2.,fixing_at=at,available_at=at,
        quality=QualityTier.A,source='fixture',revision_id='v1')
    out=builder(**(args|{'valuation_prices':(price,),'reports':(report,),'fx_quotes':(quote,)}))
    assert {r.feature:r.value for r in out.features}['market_cap_bucket']==1
    # A future revision must not move a literal USD2bn boundary.
    future=replace(quote,rate=20.,fixing_at=at+timedelta(hours=1),available_at=at+timedelta(hours=1),revision_id='v2')
    out=builder(**(args|{'valuation_prices':(price,),'reports':(report,),'fx_quotes':(quote,future)}))
    assert {r.feature:r.value for r in out.features}['market_cap_bucket']==1


def test_beta_zero_variance_missing_session_and_controlled_sectors():
    builder,args=configured()
    flat=replace(args['broad'],adjusted_close=(100.,)*253)
    assert builder(**(args|{'broad':flat})).beta is None
    shifted=replace(args['broad'],sessions=args['broad'].sessions[:-1])
    assert builder(**(args|{'broad':shifted})).beta is None
    with pytest.raises(ValueError,match='ECONOMIC_SECTORS'):
        replace(args['config'],sector_codes=(('US0123456789',0),))
    with pytest.raises(ValueError,match='LISTED_SCOPE'):
        builder(**(args|{'security':replace(args['security'],region=Region.EU,exchange='XLON')}))


def test_price_evidence_binds_fx_staleness_policy_even_when_usd_outputs_unchanged():
    from quant_dca.features.history import build_price_features
    from quant_dca.snapshot_contracts import evidence_frame
    from quant_dca.storage.snapshots import snapshot_hash
    _,args=configured()
    stock=args['stock']
    kwargs=dict(security_id='TEST',exchange='XNYS',as_of=args['as_of'],action_coverage=stock.action_coverage,
        volume_evidence=stock.selected_volume_evidence,listing_history=stock.selected_listings)
    # deduplicate repeated historical listings from the evidence snapshot
    kwargs['listing_history']=tuple(dict.fromkeys(kwargs['listing_history']))
    one=build_price_features(stock.raw_bars,(),fx_max_age=timedelta(days=1),**kwargs)
    four=build_price_features(stock.raw_bars,(),fx_max_age=timedelta(days=4),**kwargs)
    assert one.features==four.features
    assert snapshot_hash(evidence_frame(one))!=snapshot_hash(evidence_frame(four))
    builder,_=configured()
    one_market=builder(**(args|{'fx_max_age':timedelta(days=1)}))
    four_market=builder(**(args|{'fx_max_age':timedelta(days=4)}))
    assert snapshot_hash(evidence_frame(one_market))!=snapshot_hash(evidence_frame(four_market))


def test_cap_bucket_requires_declared_unadjusted_price_dependency():
    builder,args=configured()
    price=replace(args['valuation_prices'][0],price_basis='split_adjusted_feature',per_share_basis='split_adjusted_v1')
    report=replace(args['reports'][0],per_share_basis='split_adjusted_v1')
    with pytest.raises(ValueError,match='CAP_UNADJUSTED'):
        builder(**(args|{'valuation_prices':(price,),'reports':(report,)}))
