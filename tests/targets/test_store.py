from dataclasses import replace
from datetime import date,timedelta
import pandas as pd
import pytest

from test_executable import fixture as executable_fixture
from quant_dca.calendars.service import eligible_session_close
from quant_dca.types import UniverseMembership,QualityTier,Region
from quant_dca.universe.membership import TradingSession,LiquidityMetric,FundamentalReport,EligibilityThresholds
from quant_dca.snapshot_contracts import UniverseEvidence,evidence_frame
from quant_dca.storage.snapshots import write_snapshot,read_snapshot_metadata


def api():
    try:
        from quant_dca.targets.store import build_target_store,TargetInputs,TargetRequest
    except ImportError:
        pytest.fail('target store missing')
    return build_target_store,TargetInputs,TargetRequest


def fixture(tmp_path,short=False):
    builder,inputs,request=api()
    old=executable_fixture()
    sec=old['listing_history'][0]
    at=old['signal_at']
    sessions=[]; day=date(2022,1,3)
    while len(sessions)<120:
        close=eligible_session_close('XNYS',day)
        if close:
            sessions.append(TradingSession(security_id='S',exchange='XNYS',session_date=day.isoformat(),available_at=close))
        day+=timedelta(days=1)
    universe=UniverseEvidence(securities=(sec,),memberships=(UniverseMembership(universe_id='fixture',security_id='S',active_from='2010-01-01',
        region=Region.US,exchange='XNYS',currency='USD',available_at=sec.available_at,quality=QualityTier.A,source='fixture',revision_id='v1'),),
        trading_sessions=tuple(sessions),liquidity_metrics=(LiquidityMetric(security_id='S',measured_at=at,available_at=at,value=1e8),),
        fundamental_reports=(FundamentalReport(security_id='S',published_at=at,available_at=at),),thresholds=EligibilityThresholds(120,1,True))
    rows=old['prices'][:21] if short else old['prices']
    coverage=replace(old['action_coverage'],end_session=rows[-1].session_date,available_at=rows[-1].available_at)
    # Materialized FX is the source evidence, not an opaque injected resolver.
    from quant_dca.types import FXQuote
    quotes=tuple(FXQuote(base_currency='USD',quote_currency='HUF',rate=300.,fixing_at=r.session_open_at-timedelta(minutes=1),
        available_at=r.session_open_at,quality=QualityTier.A,source='fixture',revision_id='v1') for r in rows)
    label=rows[-1].available_at if short else old['label_as_of']
    data=inputs(prices=tuple(rows),actions=(),listing_history=(sec,),action_coverage=(coverage,),
        fx_quotes=quotes,fx_max_age=timedelta(days=5),discontinuity_evidence=())
    source=write_snapshot(evidence_frame(data),'canonical',label,root=tmp_path/'sources')
    usource=write_snapshot(evidence_frame(universe),'canonical',at,root=tmp_path/'sources')
    task=request(security_id='S',exchange='XNYS',region=Region.US,signal_at=at,inputs=data,source=source)
    return dict(start=at,end=at,label_as_of=label,role='train',requests=(task,),universe=universe,universe_source=usource,root=tmp_path/'out')


def test_separate_immutable_targets_preserve_each_horizon_maturity(tmp_path):
    builder,*_=api()
    args=fixture(tmp_path,short=True)
    result=builder(**args)
    table=pd.read_parquet(result.path)
    assert len(table)==20
    assert 'feature' not in table.columns
    assert (table.baseline_open_at>table.signal_at).all()
    t=table.set_index('target')
    assert t.loc['return_5d_local','value']==0.
    assert t.loc['return_20d_huf','value']==0.
    assert pd.isna(t.loc['return_60d_huf','value'])
    assert t.loc['return_60d_huf','censor_reason']=='LABEL_WINDOW_NOT_YET_AVAILABLE'
    assert pd.notna(t.loc['return_5d_local','target_end_timestamp'])
    assert pd.notna(t.loc['return_20d_local','target_end_timestamp'])
    assert read_snapshot_metadata(result)['layer']=='targets'
    assert result.sha256==builder(**args).sha256


def test_invalid_range_role_and_signal_rejected_before_inputs(tmp_path):
    builder,*_=api()
    args=fixture(tmp_path)
    class Bomb:
        def __iter__(self):
            raise AssertionError('target data consumed')
    for changes in ({'role':'outer_oos'},{'start':args['start'].replace(year=2009)},{'label_as_of':args['label_as_of'].replace(year=2024)}):
        with pytest.raises(ValueError):
            builder(**(args|changes|{'requests':Bomb(),'universe_source':'missing'}))
    task=replace(args['requests'][0],signal_at=args['start'].replace(year=2024),inputs=Bomb())
    with pytest.raises(ValueError):
        builder(**(args|{'requests':(task,)}))


def test_target_source_binding_and_signal_membership(tmp_path):
    builder,*_=api()
    args=fixture(tmp_path)
    task=args['requests'][0]
    changed=replace(task.inputs,prices=(replace(task.inputs.prices[0],open=110.),*task.inputs.prices[1:]))
    with pytest.raises(ValueError,match='CONTENT_MISMATCH'):
        builder(**(args|{'requests':(replace(task,inputs=changed),)}))
    with pytest.raises(ValueError,match='INELIGIBLE'):
        builder(**(args|{'requests':(replace(task,security_id='unknown'),)}))
