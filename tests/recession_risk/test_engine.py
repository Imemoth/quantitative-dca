from dataclasses import FrozenInstanceError,replace
from datetime import timedelta
import pytest
from quant_dca.recession_risk.engine import build_snapshot,validate_selected
from quant_dca.recession_risk.evidence import AdmissionStatus
from quant_dca.types import QualityTier,Region
from conftest import ts


def build(cfg,evidence=(),**changes):
    args=dict(as_of=ts(),region=Region.US,monetary_jurisdiction='FED',evidence=evidence,config=cfg)
    args.update(changes)
    return build_snapshot(**args)


def measure(s,name='us_gdp_growth'): return next(i for i in s.input_measures if i.name==name)


def test_no_evidence_is_unknown_and_zero_confidence(cfg):
    s=build(cfg)
    assert s.dominant_scenario=='INSUFFICIENT_EVIDENCE' and s.secondary_scenario is None
    assert s.evidence_completeness==s.data_confidence==0
    assert s.quality is None and s.max_input_available_at is None
    assert all(p.state=='UNKNOWN' and p.evidence_state=='INSUFFICIENT_EVIDENCE' for p in s.pillars)
    assert s.drivers==() and s.source_snapshot_hashes==()
    with pytest.raises(FrozenInstanceError):s.region=Region.EU


def test_one_admitted_input_is_partial_not_healthy(cfg,make_evidence):
    e=make_evidence(); s=build(cfg,[e])
    assert measure(s).value==2
    assert measure(s).status=='ADMITTED'
    assert s.evidence_completeness==1/16
    assert 0<s.data_confidence<s.evidence_completeness
    assert s.max_input_available_at==e.observation.available_at
    assert s.publication_timestamps==(e.observation.published_at,)
    assert s.source_snapshot_hashes==(e.snapshot.sha256,)
    assert s.quality is QualityTier.B
    assert all(p.state=='UNKNOWN' for p in s.pillars)


def test_vintages_replayed_without_future_rewrite(cfg,make_evidence):
    original=make_evidence(value=2)
    revision=make_evidence(value=3,available=ts('2020-06-16',12),revised=ts('2020-06-16',12))
    future=make_evidence(date='2020-07-01',available=ts('2020-07-10',12),value=999)
    past=build(cfg,[original])
    assert build(cfg,[future,revision,original])==past
    assert measure(build(cfg,[original,revision],as_of=ts('2020-06-17'))).value==3
    assert build(cfg,[original,original])==past


def test_late_revision_uses_publication_not_retrieval_order(cfg,make_evidence):
    old=make_evidence(value=1,available=ts('2020-06-12',12),published=ts('2020-06-05',12))
    new=make_evidence(value=2,available=ts('2020-06-11',12),published=ts('2020-06-05',12),revised=ts('2020-06-11',12))
    assert measure(build(cfg,[old,new])).value==2


def test_same_day_release_waits_for_eligible_eod(cfg,make_evidence):
    early=make_evidence(available=ts('2020-06-15',12))
    assert measure(build(cfg,[early],as_of=ts('2020-06-15',18))).value is None
    assert measure(build(cfg,[early])).value==2
    late=make_evidence(available=ts('2020-06-15',22))
    assert measure(build(cfg,[late])).value is None


@pytest.mark.parametrize('change,error',[
    ({'unit':'percent'},'UNIT'),({'region':Region.EU},'REGION'),
    ({'entity_id':'ABC'},'IDENTITY'),({'value':float('nan')},'NONFINITE'),
    ({'observation_date':'2020-07-01'},'FUTURE_OBSERVATION'),
    ({'published_at':ts('2020-06-16')},'CHRONOLOGY'),
    ({'revised_at':ts('2020-06-16')},'CHRONOLOGY')])
def test_bad_selected_evidence_fails_closed(cfg,make_evidence,change,error):
    e=make_evidence()
    e=replace(e,observation=replace(e.observation,**change))
    with pytest.raises(ValueError,match=error):build(cfg,[e])


def test_selected_future_input_hard_fails(cfg,make_evidence):
    e=make_evidence(available=ts('2020-06-16',12))
    definition=next(i for i in cfg.inputs if i.name=='us_gdp_growth')
    with pytest.raises(ValueError,match='PIT_LEAKAGE'): validate_selected(e,definition,ts())


@pytest.mark.parametrize('admission_change',[
    {'source':'other'},{'series':'other'},{'region':Region.EU},
    {'monetary_jurisdiction':'ECB'},{'unit':'percent'},
    {'start':'2021-01-01'},{'quality':QualityTier.A},{'source_snapshot_hash':'b'*64}])
def test_admission_binding_cannot_be_substituted(cfg,make_evidence,admission_change):
    e=make_evidence(admission_changes=admission_change)
    with pytest.raises(ValueError,match='ADMISSION'):build(cfg,[e])


def test_content_hash_cannot_be_substituted(cfg,make_evidence):
    e=make_evidence();e=replace(e,observation=replace(e.observation,value=99))
    with pytest.raises(ValueError,match='CONTENT_MISMATCH'):build(cfg,[e])


@pytest.mark.parametrize('kind',['missing','stale','raw','low_quality'])
def test_unusable_input_never_increases_confidence(cfg,make_evidence,kind):
    kw={}
    if kind=='missing':kw['value']=None
    if kind=='stale':kw['date']='2019-01-01'
    if kind=='raw':kw['status']=AdmissionStatus.RAW_ONLY
    if kind=='low_quality':kw['quality']=QualityTier.C
    s=build(cfg,[make_evidence(**kw)])
    assert s.data_confidence==s.evidence_completeness==0
    assert measure(s).value is None
    assert s.dominant_scenario=='INSUFFICIENT_EVIDENCE'


def test_publication_uncertainty_reduces_confidence(cfg,make_evidence):
    good=build(cfg,[make_evidence()]);uncertain=build(cfg,[make_evidence(published=None)])
    assert uncertain.data_confidence==good.data_confidence*0.5
    with pytest.raises(ValueError,match='TIER_A_PUBLICATION'):
        build(cfg,[make_evidence(published=None,quality=QualityTier.A)])


def test_mixed_admission_and_permutation_are_deterministic(cfg,make_evidence):
    a=make_evidence(); b=make_evidence('us_unemployment',status=AdmissionStatus.RAW_ONLY)
    assert build(cfg,[a,b])==build(cfg,[b,a])
    assert build(cfg,[a,b]).evidence_completeness==1/16


@pytest.mark.parametrize('region,jurisdiction',[(Region.EU,'MNB'),(Region.EU,'UNKNOWN'),(Region.US,'ECB')])
def test_no_implicit_jurisdiction_fallback(cfg,make_evidence,region,jurisdiction):
    s=build(cfg,[make_evidence('ea_policy_rate')],region=region,monetary_jurisdiction=jurisdiction)
    assert s.dominant_scenario=='INSUFFICIENT_EVIDENCE' and s.data_confidence==0
    assert 'UNSUPPORTED_JURISDICTION' in s.reason_codes


def test_euro_area_context_is_explicit(cfg,make_evidence):
    s=build(cfg,[make_evidence('ea_policy_rate')],region=Region.EU,monetary_jurisdiction='ECB')
    assert measure(s,'ea_policy_rate').value==2 and s.evidence_completeness==1/15


@pytest.mark.parametrize('changes',[{'role':'outer_oos'},{'role':'research'},{'as_of':ts('2024-01-01')},{'as_of':ts('2009-12-31')}])
def test_invalid_request_rejected_before_iterating(cfg,changes):
    class Trap:
        def __iter__(self):raise AssertionError('read forbidden data')
    with pytest.raises(ValueError):build(cfg,Trap(),**changes)


def test_out_of_development_dependency_is_rejected(cfg,make_evidence):
    e=make_evidence();e=replace(e,observation=replace(e.observation,available_at=ts('2024-01-01')))
    with pytest.raises(ValueError,match='DEVELOPMENT'):build(cfg,[e])


def test_future_vintage_date_cannot_masquerade_as_known(cfg,make_evidence):
    e=make_evidence(observation_changes={'vintage_start':'2020-06-16','vintage_end':'2023-12-31'})
    with pytest.raises(ValueError,match='VINTAGE'):
        build(cfg,[e])


def test_missing_revision_clock_for_repeated_period_cannot_be_sorted_by_id(cfg,make_evidence):
    a=make_evidence(value=1,published=None)
    b=make_evidence(value=2,published=None,available=ts('2020-06-11',12))
    with pytest.raises(ValueError,match='AMBIGUOUS_VINTAGE'):build(cfg,[a,b])


def test_conflicting_admissions_are_rejected(cfg,make_evidence):
    e=make_evidence()
    other=replace(e,admission=replace(e.admission,evidence_refs=('another review',)))
    with pytest.raises(ValueError,match='AMBIGUOUS_ADMISSION'):build(cfg,[e,other])
