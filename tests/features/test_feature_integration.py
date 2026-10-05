from dataclasses import replace
from datetime import timedelta
import json
import pandas as pd
import pytest

from test_market_structural import configured
from quant_dca.features.history import build_price_features
from quant_dca.features.fundamentals import build_fundamental_features
from quant_dca.features.valuation import build_valuation_features
from quant_dca.features.relative import build_relative_features
from quant_dca.features.macro import build_macro_features, MacroSeriesMap
from quant_dca.features.events import build_event_features
from quant_dca.features.registry import FeatureRegistry
from quant_dca.types import Observation, QualityTier, Region, UniverseMembership
from quant_dca.universe.membership import UniverseIndex, EligibilityThresholds, TradingSession, LiquidityMetric, FundamentalReport
from quant_dca.storage.snapshots import write_snapshot, read_snapshot_metadata


def api():
    try:
        from quant_dca.features.snapshots import build_feature_snapshot, ProducerBundle
        from quant_dca.snapshot_contracts import UniverseEvidence, evidence_frame
    except ImportError:
        pytest.fail('immutable integration missing')
    return build_feature_snapshot, ProducerBundle, UniverseEvidence, evidence_frame


def fixture(tmp_path, financial=False):
    builder, bundle, universe_type, frame = api()
    missing, args = configured()
    at, sec = args['as_of'], args['security']
    label = 'Financials' if financial else 'Technology'
    args['classifications'] = tuple(replace(r,sector_id=label) for r in args['classifications'])
    args['config'] = replace(args['config'],sector_codes=((label,0),))
    args['binding'] = replace(args['binding'],sector_label=label)
    report = replace(args['reports'][0],sector_id=label,values={
        'diluted_shares':1e8, 'prior_year_diluted_shares':9e7, 'revenue':2e9,'prior_year_revenue':1e9,
        'diluted_eps':2.,'prior_year_diluted_eps':1.,'free_cash_flow':2e8,'prior_year_free_cash_flow':1e8,
        'gross_profit':8e8,'operating_income':4e8,'nopat':3e8,'invested_capital':15e8,
        'net_income':2.4e8,'average_equity':12e8,'net_debt':5e8,'ebitda':2.5e8,'ebit':3e8,'interest_expense':.5e8})
    args['reports'] = (report,)
    raw = args['stock'].raw_bars
    universe = universe_type(securities=(sec,),memberships=(UniverseMembership(universe_id='fixture',security_id=sec.security_id,
        active_from=sec.active_from,region=sec.region,exchange=sec.exchange,currency=sec.currency,
        available_at=sec.available_at,quality=QualityTier.A,source='fixture',revision_id='v1'),),
        trading_sessions=tuple(TradingSession(security_id=sec.security_id,exchange=sec.exchange,session_date=r.session_date,available_at=r.available_at) for r in raw),
        liquidity_metrics=(LiquidityMetric(security_id=sec.security_id,measured_at=at,available_at=at,value=1e8),),
        fundamental_reports=(FundamentalReport(security_id=sec.security_id,published_at=report.published_at,available_at=report.available_at),),
        thresholds=EligibilityThresholds(120,1.,True))
    index = universe.index()
    stock = args['stock']
    returns = {h:next(r for r in stock.features if r.feature==f'return_{h}d_raw') for h in (20,60,120)}
    sector_returns = {h:replace(r,entity_id=label) for h,r in returns.items()}
    relative = build_relative_features(security_id=sec.security_id,region=sec.region,as_of=at,universe_index=index,
        stock_returns=returns,cross_section_returns=tuple(returns.values()),sector_benchmark_returns=sector_returns,
        market_benchmark_returns=returns,sector_classifications=args['classifications'])
    fundamental = build_fundamental_features(security_id=sec.security_id,as_of=at,reports=(report,))
    valuation = build_valuation_features(security_id=sec.security_id,region=sec.region,as_of=at,reports=(report,),
        prices=args['valuation_prices'],universe_index=index,sector_classifications=args['classifications'])
    regional = {k:k for k in ('headline_inflation','core_inflation','unemployment_rate','high_yield_spread','investment_grade_spread','financial_conditions')}
    mapping = MacroSeriesMap(regional={Region.US:regional,Region.EU:regional},policy_rate={'US':'policy'},central_bank_liquidity={'US':'liquidity'},
        us_rates={k:k for k in ('long_10y','short_2y','short_3m')},eu_rates={k:k for k in ('sovereign_long','relevant_short')},global_risk_off='global')
    observations = tuple(Observation(series=k,entity_id=None,observation_date=at.date().isoformat(),value=3.,available_at=at,
        quality=QualityTier.A,source='fixture',revision_id='v1',region=Region.US) for k in (*regional,'policy','liquidity','long_10y','short_2y','short_3m','global'))
    sec_macro = replace(sec,monetary_jurisdiction='US')
    macro = build_macro_features(security=sec_macro,as_of=at,observations=observations,series_map=mapping)
    events = build_event_features(security=sec_macro,as_of=at,events=())
    producers = (stock,relative,fundamental,valuation,macro,events,missing(**args))
    bundles = tuple(bundle(p,write_snapshot(frame(p),'canonical',at,root=tmp_path/'sources')) for p in producers)
    uref = write_snapshot(frame(universe),'canonical',at,root=tmp_path/'sources')
    return dict(as_of=at,registry_version='features-v1',role='train',fold_id='fixture-fold',
        security_id=sec.security_id,region=sec.region,exchange=sec.exchange,bundles=bundles,
        universe=universe,universe_source=uref,root=tmp_path/'output')


def test_end_to_end_all_81_and_immutable_lineage(tmp_path):
    builder,*_ = api()
    args = fixture(tmp_path)
    result = builder(**args)
    assert result.predictors.shape == (1,81)
    assert tuple(result.predictors.columns) == FeatureRegistry.v1().names()
    assert result.predictors['return_20d_raw'].iloc[0] == pytest.approx(352/332-1)
    assert result.regime_status == 'base_only_incomplete_regime_integration'
    data = pd.read_parquet(result.reference.path)
    assert len(data)==81 and data.entity_id.unique().tolist()==['TEST']
    assert (data.available_at <= args['as_of']).all()
    assert not {'ticker','entity_id','security_id','target'} & set(result.predictors.columns)
    metadata = read_snapshot_metadata(result.reference)
    assert len({r['feature'] for r in metadata['lineage']}) == 81
    assert result.reference.sha256 == builder(**args).reference.sha256
    assert all(r['universe_snapshot']==args['universe_source'].sha256 for r in metadata['lineage'])


def test_structural_missing_masks_survive_storage(tmp_path):
    builder,*_ = api()
    result = builder(**fixture(tmp_path,financial=True))
    table = pd.read_parquet(result.reference.path).set_index('feature')
    assert pd.isna(table.loc['fcf_margin_raw','value'])
    assert table.loc['fcf_margin_raw','structural_missing']
    assert table.loc['ev_to_ebitda_raw','structural_missing']


def test_content_binding_rejects_changed_output_missing_bundle_and_ineligible(tmp_path):
    builder,bundle,*_ = api()
    args = fixture(tmp_path)
    first = args['bundles'][0]
    changed = replace(first.snapshot,features=(replace(first.snapshot.features[0],value=777.),*first.snapshot.features[1:]))
    with pytest.raises(ValueError,match='CONTENT_MISMATCH'):
        builder(**(args|{'bundles':(bundle(changed,first.source),*args['bundles'][1:])}))
    with pytest.raises(ValueError,match='COVERAGE'):
        builder(**(args|{'bundles':args['bundles'][:-1]}))
    with pytest.raises(ValueError,match='INELIGIBLE'):
        builder(**(args|{'security_id':'absent'}))


def test_invalid_request_before_lazy_bundles_or_source_reads(tmp_path):
    builder,*_ = api()
    args = fixture(tmp_path)
    class Bomb:
        def __iter__(self):
            raise AssertionError('consumed lazy input')
    for changes in ({'role':'holdout'},{'as_of':args['as_of'].replace(year=2024)}):
        with pytest.raises(ValueError):
            builder(**(args|changes|{'bundles':Bomb(),'universe_source':'nonexistent'}))


def regime_fixture(args,tmp_path,quality_branch=None):
    try:
        from quant_dca.regimes.integration import build_regime_features
    except ImportError:
        pytest.fail('regime snapshot integration missing')
    from quant_dca.regimes.interpretable import InterpretableRegimeModel
    from quant_dca.regimes.unsupervised import RegimePartition, RegimeSnapshot, fit_regime_candidate, SIGNAL_UNITS
    from quant_dca.features.normalize import PartitionRole
    from quant_dca.calendars.service import previous_eligible_eod
    from quant_dca.snapshot_contracts import evidence_frame
    from quant_dca.types import FeatureValue
    at=args['as_of']
    current = tuple(replace(r,entity_id=None,region=Region.GLOBAL if r.feature=='vix_level_raw' else Region.US)
        for b in args['bundles'] for r in b.snapshot.features if r.feature in SIGNAL_UNITS)
    if quality_branch=="current":
        current=tuple(replace(r,quality=QualityTier.C) if r.feature=="vix_level_raw" else r for r in current)
    prior=previous_eligible_eod('XNYS',at-timedelta(microseconds=1))
    past=tuple(replace(r,as_of=prior,available_at=prior,max_input_available_at=prior,observation_date=prior.date().isoformat()) for r in current)
    if quality_branch=="historical":
        past=tuple(replace(r,quality=QualityTier.C) if r.feature=="vix_level_raw" else r for r in past)
    interpreted=InterpretableRegimeModel.default().predict(current,historical_inputs=past,
        prediction_timestamp=at,current_eod=at,prior_eod=prior,benchmark_exchange='XNYS',region=Region.US,
        partition_role=PartitionRole.VALIDATION,feature_units=SIGNAL_UNITS)
    times=[r.session_close_at for r in args['bundles'][0].snapshot.raw_bars[:60]]
    train_rows=[]
    for i,t in enumerate(times):
        values=(.01*(i%3)+.001*(i%7),10.+5*(i%3)+.2*(i%7),2.+i%3+.1*(i%5))
        rows=tuple(FeatureValue(feature=n,entity_id=None,observation_date=t.date().isoformat(),as_of=t,value=v,
            max_input_available_at=t,available_at=t,quality=QualityTier.A,source='synthetic',revision_id='v1',
            region=Region.GLOBAL if n=='vix_level_raw' else Region.US) for n,v in zip(SIGNAL_UNITS,values))
        if quality_branch=="training":
            rows=tuple(replace(r,quality=QualityTier.C) if r.feature=="vix_level_raw" else r for r in rows)
        train_rows.append(RegimeSnapshot(eod=t,sequence_id='training',features=rows))
    train=RegimePartition(snapshots=tuple(train_rows),role=PartitionRole.TRAIN,fold_id=args['fold_id'],
        starts_at=times[0],ends_at=times[-1],region=Region.US,benchmark_exchange='XNYS',feature_units=SIGNAL_UNITS)
    model=fit_regime_candidate(train,'gmm',3,42)
    part=replace(train,snapshots=(RegimeSnapshot(eod=at,sequence_id='validation',features=current),),
        role=PartitionRole.VALIDATION,starts_at=at,ends_at=at)
    result=build_regime_features(as_of=at,role=PartitionRole.VALIDATION,fold_id=args['fold_id'],
        interpreted=interpreted,model=model,partition=part)
    ref=write_snapshot(evidence_frame(result),'canonical',at,root=tmp_path/'regime-source')
    return api()[1](result,ref),dict(as_of=at,role=PartitionRole.VALIDATION,fold_id=args['fold_id'],interpreted=interpreted,model=model,partition=part)


def test_full_89_feature_candidate_binds_fit_identity_and_no_padding(tmp_path):
    builder,*_=api()
    args=fixture(tmp_path)
    regimes,request=regime_fixture(args,tmp_path)
    result=builder(**(args|{'role':'validation','regimes':regimes}))
    assert result.predictors.shape==(1,89)
    assert result.regime_status=='complete_software_candidate_not_research_selected'
    p=result.predictors.filter(like='regime_state_')
    assert len(p.columns)==3 and p.iloc[0].sum()==pytest.approx(1.)
    table=pd.read_parquet(result.reference.path)
    regime_rows=table[table.feature.str.startswith('regime_')]
    assert set(regime_rows.fit_id)=={request['model'].provenance.candidate_id}
    assert (regime_rows.max_input_available_at<=args['as_of']).all()


def test_regime_rejects_other_fold_future_fit_and_unverified_heuristic(tmp_path):
    from quant_dca.regimes.integration import build_regime_features
    args=fixture(tmp_path)
    regimes,request=regime_fixture(args,tmp_path)
    with pytest.raises(ValueError,match='FOLD'):
        build_regime_features(**(request|{'fold_id':'other'}))
    with pytest.raises(ValueError,match='PIT'):
        build_regime_features(**(request|{'interpreted':replace(request['interpreted'],pit_validated=False)}))
    late=replace(request['model'],provenance=replace(request['model'].provenance,
        train_bounds=(request['model'].provenance.train_bounds[0],args['as_of']+timedelta(days=1))))
    with pytest.raises(ValueError,match='FIT_AFTER'):
        build_regime_features(**(request|{'model':late}))
    with pytest.raises(ValueError,match='FOLD'):
        api()[0](**(args|{'role':'validation','regimes':regimes,'fold_id':'other'}))


def test_selected_evidence_future_clock_cannot_hide_behind_old_feature_metadata(tmp_path):
    builder,bundle,_,frame=api()
    args=fixture(tmp_path)
    first=args['bundles'][0]
    # Content binding alone is insufficient: the supplied producer evidence must
    # also be known at the declared prediction timestamp.
    future=replace(first.snapshot.raw_bars[-1],available_at=args['as_of']+timedelta(days=1))
    altered=replace(first.snapshot,raw_bars=(*first.snapshot.raw_bars[:-1],future))
    ref=write_snapshot(frame(altered),'canonical',args['as_of'],root=tmp_path/'malformed')
    with pytest.raises(ValueError,match='EVIDENCE_AFTER'):
        builder(**(args|{'bundles':(bundle(altered,ref),*args['bundles'][1:])}))


def test_regime_changed_base_input_cannot_be_attached_to_unrelated_snapshot(tmp_path):
    builder,bundle,_,frame=api()
    args=fixture(tmp_path)
    regimes,request=regime_fixture(args,tmp_path)
    altered=replace(regimes.snapshot,evidence=tuple(replace(r,value=r.value+1) for r in regimes.snapshot.evidence))
    ref=write_snapshot(frame(altered),'canonical',args['as_of'],root=tmp_path/'bad-regime')
    with pytest.raises(ValueError,match='BASE_INPUT_MISMATCH'):
        builder(**(args|{'role':'validation','regimes':bundle(altered,ref)}))


def test_preceding_membership_and_post_prediction_revision_are_not_current_fallback(tmp_path):
    builder,bundle,_,frame=api()
    args=fixture(tmp_path)
    original=args['universe']
    ended=replace(original.memberships[0],active_to=args['as_of'].date().isoformat())
    future=replace(ended,active_to=None,available_at=args['as_of']+timedelta(days=1),revision_id='later')
    universe=replace(original,memberships=(ended,future))
    ref=write_snapshot(frame(universe),'canonical',args['as_of'],root=tmp_path/'membership')
    with pytest.raises(ValueError,match='INELIGIBLE'):
        builder(**(args|{'universe':universe,'universe_source':ref}))


def test_same_signal_feature_and_target_snapshots_join_only_on_metadata(tmp_path):
    from quant_dca.calendars.service import next_eligible_open,eligible_session_close
    from quant_dca.targets.store import TargetInputs,TargetRequest,build_target_store
    from quant_dca.targets.builder import ActionCoverage
    from quant_dca.types import FXQuote
    builder,_,_,frame=api()
    args=fixture(tmp_path)
    features=builder(**args)
    template=args['bundles'][0].snapshot.raw_bars[-1]
    instant=args['as_of']; prices=[]; quotes=[]
    for _ in range(61):
        instant=next_eligible_open('XNYS',instant)
        close=eligible_session_close('XNYS',instant.date())
        prices.append(replace(template,session_date=instant.date().isoformat(),session_open_at=instant,
            session_close_at=close,available_at=close,open=100.,high=100.,low=100.,close=100.))
        quotes.append(FXQuote(base_currency='USD',quote_currency='HUF',rate=300.,fixing_at=instant,
            available_at=instant,quality=QualityTier.A,source='fixture',revision_id='v1'))
    label=prices[-1].available_at
    inputs=TargetInputs(prices=tuple(prices),actions=(),listing_history=args['universe'].securities,
        action_coverage=(ActionCoverage('TEST',prices[0].session_date,prices[-1].session_date,label,'fixture','complete'),),
        fx_quotes=tuple(quotes),fx_max_age=timedelta(days=4))
    source=write_snapshot(frame(inputs),'canonical',label,root=tmp_path/'target-source')
    target=build_target_store(args['as_of'],args['as_of'],label_as_of=label,role='train',
        requests=(TargetRequest(security_id='TEST',exchange='XNYS',region=Region.US,signal_at=args['as_of'],inputs=inputs,source=source),),
        universe=args['universe'],universe_source=args['universe_source'],root=args['root'])
    feature_rows=pd.read_parquet(features.reference.path)
    target_rows=pd.read_parquet(target.path)
    assert set(target_rows.entity_id)==set(feature_rows.entity_id)=={'TEST'}
    assert (feature_rows.available_at<=args['as_of']).all()
    assert (target_rows.baseline_open_at>args['as_of']).all()
    assert set(target_rows.signal_at)==set(feature_rows.as_of)
    assert features.reference.path.parent.parent.name=='features'
    assert target.path.parent.parent.name=='targets'
    assert 'entity_id' not in features.predictors and 'target' not in features.predictors


def _change_regime_evidence(snapshot,branch,field,value):
    """Replace one evidenced clock/tier without altering any numeric value."""
    if branch=='training':
        rows=snapshot.fit.training_evidence
        return replace(snapshot,fit=replace(snapshot.fit,training_evidence=(replace(rows[0],**{field:value}),*rows[1:])))
    if branch=='prediction':
        rows=snapshot.evidence
        return replace(snapshot,evidence=(replace(rows[0],**{field:value}),*rows[1:]))
    rows=snapshot.interpreted.evidence
    at=snapshot.interpreted.prior_eod if branch=='historical' else snapshot.interpreted.current_eod
    index=next(i for i,r in enumerate(rows) if r.as_of==at)
    changed=tuple(replace(r,**{field:value}) if i==index else r for i,r in enumerate(rows))
    return replace(snapshot,interpreted=replace(snapshot.interpreted,evidence=changed))


@pytest.mark.parametrize('branch',['historical','current','training'])
@pytest.mark.parametrize('clock',['available_at','published_at','revised_at','max_input_available_at'])
def test_regime_construction_revalidates_each_branch_clock_before_lazy_prediction(tmp_path,branch,clock):
    from quant_dca.regimes.integration import build_regime_features
    args=fixture(tmp_path)
    bundle,request=regime_fixture(args,tmp_path)
    cutoff=(bundle.snapshot.fit.training_evidence[0].as_of if branch=='training' else
        bundle.snapshot.interpreted.prior_eod if branch=='historical' else args['as_of'])
    changed=_change_regime_evidence(bundle.snapshot,branch,clock,cutoff+timedelta(hours=1))
    class Unreadable:
        def __iter__(self):
            raise AssertionError('numeric prediction inputs reached before clock guard')
    with pytest.raises(ValueError,match='PIT'):
        build_regime_features(**(request|{'interpreted':changed.interpreted,
            'model':replace(request['model'],provenance=changed.fit),
            'partition':replace(request['partition'],snapshots=Unreadable())}))


@pytest.mark.parametrize('branch',['historical','current','training','prediction'])
@pytest.mark.parametrize('clock',['available_at','published_at','revised_at','max_input_available_at'])
def test_staged_regime_clocks_rechecked_before_any_source_read(tmp_path,branch,clock):
    builder,bundle_type,*_=api()
    args=fixture(tmp_path)
    bundle,_=regime_fixture(args,tmp_path)
    cutoff=(bundle.snapshot.fit.training_evidence[0].as_of if branch=='training' else
        bundle.snapshot.interpreted.prior_eod if branch=='historical' else args['as_of'])
    changed=_change_regime_evidence(bundle.snapshot,branch,clock,cutoff+timedelta(hours=1))
    with pytest.raises(ValueError,match='PIT'):
        builder(**(args|{'role':'validation','regimes':bundle_type(changed,'unreadable-regime-source'),
            'universe_source':'unreadable-universe-source'}))


def test_review_future_historical_availability_rejected_with_valid_content_bound_source(tmp_path):
    from quant_dca.regimes.integration import build_regime_features
    builder,bundle_type,_,frame=api()
    args=fixture(tmp_path)
    bundle,request=regime_fixture(args,tmp_path)
    changed=_change_regime_evidence(bundle.snapshot,'historical','available_at',args['as_of']+timedelta(days=1))
    source=write_snapshot(frame(changed),'canonical',args['as_of'],root=tmp_path/'future-history-source')
    with pytest.raises(ValueError,match='PIT'):
        build_regime_features(**(request|{'interpreted':changed.interpreted}))
    with pytest.raises(ValueError,match='PIT'):
        builder(**(args|{'role':'validation','regimes':bundle_type(changed,source)}))


@pytest.mark.parametrize('branch,want_heuristic,want_unsupervised',[
    ('historical','C','A'),('training','A','C'),('current','C','C')])
def test_regime_composite_tier_preserves_selected_branch_quality_in_storage(tmp_path,branch,want_heuristic,want_unsupervised):
    builder,*_=api()
    args=fixture(tmp_path)
    bundle,_=regime_fixture(args,tmp_path,quality_branch=branch)
    result=builder(**(args|{'role':'validation','regimes':bundle}))
    stored=pd.read_parquet(result.reference.path)
    heuristic=stored[stored.feature.str.startswith('regime_interpretable_')]
    unsupervised=stored[stored.feature.str.startswith('regime_state_')]
    assert set(heuristic.quality)=={want_heuristic}
    assert set(unsupervised.quality)=={want_unsupervised}
    # A later A/B sensitivity predicate must exclude C, using serialized metadata.
    admissible=stored[stored.quality.isin(['A','B'])]
    for subset,wanted in ((heuristic,want_heuristic),(unsupervised,want_unsupervised)):
        assert set(subset.feature).issubset(set(admissible.feature)) == (wanted!='C')


@pytest.mark.parametrize('branch',['historical','current','training','prediction'])
def test_staged_unknown_regime_tier_rejected_before_source_reads(tmp_path,branch):
    builder,bundle_type,*_=api()
    args=fixture(tmp_path)
    bundle,_=regime_fixture(args,tmp_path)
    changed=_change_regime_evidence(bundle.snapshot,branch,'quality','unknown')
    with pytest.raises(ValueError,match='QUALITY'):
        builder(**(args|{'role':'validation','regimes':bundle_type(changed,'unreadable-regime-source'),
            'universe_source':'unreadable-universe-source'}))


def test_regime_dependency_clock_aggregation_includes_actual_availability(tmp_path):
    builder,bundle_type,_,frame=api()
    args=fixture(tmp_path)
    bundle,_=regime_fixture(args,tmp_path)
    snap=bundle.snapshot
    earlier=args['as_of']-timedelta(hours=1)
    interpreted=replace(snap.interpreted,evidence=tuple(replace(r,max_input_available_at=earlier)
        if r.as_of==args['as_of'] else r for r in snap.interpreted.evidence))
    changed=replace(snap,interpreted=interpreted,evidence=tuple(replace(r,max_input_available_at=earlier) for r in snap.evidence))
    source=write_snapshot(frame(changed),'canonical',args['as_of'],root=tmp_path/'earlier-max-input')
    result=builder(**(args|{'role':'validation','regimes':bundle_type(changed,source)}))
    stored=pd.read_parquet(result.reference.path)
    rows=stored[stored.feature.str.startswith('regime_')]
    assert (rows.max_input_available_at==args['as_of']).all()
    assert (rows.available_at==args['as_of']).all()


def _two_member_cohort(args,tmp_path,*,missing_peer=False):
    """Recompute both cross-sectional producers on a genuine two-member index."""
    builder,bundle_type,_,frame=api()
    small=args['universe']
    fields=('securities','memberships','trading_sessions','liquidity_metrics','fundamental_reports')
    large=replace(small,**{name:(*getattr(small,name),*(replace(r,security_id='PEER') for r in getattr(small,name))) for name in fields})
    index=large.index()
    original={type(b.snapshot).__name__:b.snapshot for b in args['bundles']}
    relative=original['RelativeFeatureSnapshot']
    valuation=original['ValuationFeatureSnapshot']
    returns={h:next(r for r in relative.selected_stock_returns if r.feature==f'return_{h}d_raw') for h in (20,60,120)}
    classifications=(*relative.selected_classifications,replace(relative.selected_classifications[0],security_id='PEER'))
    peer_return=replace(returns[120],entity_id='PEER',value=0.)
    relative=build_relative_features(security_id=args['security_id'],region=args['region'],as_of=args['as_of'],
        universe_index=index,stock_returns=returns,
        cross_section_returns=tuple(returns.values())+(() if missing_peer else (peer_return,)),
        sector_benchmark_returns={h:next(r for r in relative.selected_sector_benchmark_returns if r.feature==f'return_{h}d_raw') for h in (20,60,120)},
        market_benchmark_returns={h:next(r for r in relative.selected_market_benchmark_returns if r.feature==f'return_{h}d_raw') for h in (20,60,120)},
        sector_classifications=classifications)
    peer_price=replace(valuation.selected_prices[-1],security_id='PEER',close=176.)
    valuation=build_valuation_features(security_id=args['security_id'],region=args['region'],as_of=args['as_of'],universe_index=index,
        reports=(*valuation.selected_reports,replace(valuation.selected_reports[-1],security_id='PEER')),
        prices=valuation.selected_prices+(() if missing_peer else (peer_price,)),sector_classifications=classifications)
    replacements={type(p).__name__:bundle_type(p,write_snapshot(frame(p),'canonical',args['as_of'],root=tmp_path/'cohort-sources')) for p in (relative,valuation)}
    source=write_snapshot(frame(large),'canonical',args['as_of'],root=tmp_path/'cohort-universe')
    return args|{'universe':large,'universe_source':source,
        'bundles':tuple(replacements.get(type(b.snapshot).__name__,b) for b in args['bundles'])},replacements


@pytest.mark.parametrize('producer',['RelativeFeatureSnapshot','ValuationFeatureSnapshot'])
def test_snapshot_rejects_genuine_two_member_outputs_with_one_member_universe(tmp_path,producer):
    builder,*_=api()
    small=fixture(tmp_path)
    large,replacements=_two_member_cohort(small,tmp_path)
    valid=builder(**large)
    assert valid.predictors['momentum_universe_percentile'].iloc[0]==1.
    assert valid.predictors['trailing_pe_sector_percentile'].iloc[0]==1.
    assert replacements[producer].snapshot.eligible_security_ids==('PEER','TEST')
    # Keep the genuine content-bound output unchanged; attach a different,
    # equally valid immutable historical universe that still admits TEST.
    unchanged=tuple(replacements[producer] if type(b.snapshot).__name__==producer else b for b in small['bundles'])
    with pytest.raises(ValueError,match='COHORT'):
        builder(**(small|{'bundles':unchanged}))


def test_matching_full_cohort_allows_only_subset_of_peers_with_finite_values(tmp_path):
    builder,*_=api()
    args,replacements=_two_member_cohort(fixture(tmp_path),tmp_path,missing_peer=True)
    result=builder(**args)
    assert result.predictors['momentum_universe_percentile'].iloc[0]==.5
    assert result.predictors['trailing_pe_sector_percentile'].iloc[0]==.5
    assert replacements['RelativeFeatureSnapshot'].snapshot.eligible_security_ids==('PEER','TEST')
    assert replacements['ValuationFeatureSnapshot'].snapshot.eligible_security_ids==('PEER','TEST')
    assert {r.security_id for r in replacements['ValuationFeatureSnapshot'].snapshot.selected_prices}=={'TEST'}
