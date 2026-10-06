from dataclasses import replace
import json
import pytest
from quant_dca.recession_risk.registry import BandRule,ScenarioRule,config_from_mapping
from quant_dca.recession_risk.engine import build_snapshot
from quant_dca.recession_risk.reporting import write_diagnostic,write_dictionary
from quant_dca.storage.snapshots import read_snapshot_metadata
from quant_dca.types import Region
from conftest import ts


def rules_config(cfg):
    return replace(cfg,rules=(BandRule('synthetic_growth','us_gdp_growth',(0.,2.),
        ('CONTRACTIONARY','COOLING','HEALTHY'),('negative','neutral','positive'),
        ('synthetic negative growth','synthetic moderate growth','synthetic strong growth')),),
        scenario_rules=(ScenarioRule('RECESSION_RISK',(('growth','CONTRACTIONARY'),)),
                        ScenarioRule('LATE_CYCLE_SLOWDOWN',(('growth','CONTRACTIONARY'),))))


def data(cfg,make_evidence,growth=2):
    return [make_evidence(i.name,date='2020-06-12',value=growth if i.name=='us_gdp_growth' else 1.) for i in cfg.inputs if i.region is Region.US]


def build(cfg,evidence):
    return build_snapshot(as_of=ts(),region=Region.US,monetary_jurisdiction='FED',config=cfg,evidence=evidence)


@pytest.mark.parametrize('value,state,polarity',[(-1,'CONTRACTIONARY','negative'),(0,'COOLING','neutral'),(1.999,'COOLING','neutral'),(2,'HEALTHY','positive')])
def test_exact_rule_bounds_and_structured_drivers(cfg,make_evidence,value,state,polarity):
    c=rules_config(cfg);s=build(c,data(c,make_evidence,value));p=next(p for p in s.pillars if p.name=='growth')
    assert p.state==state and p.evidence_state=='COMPLETE_EVIDENCE'
    assert len(s.drivers)==1
    d=s.drivers[0]
    assert d.polarity==polarity and d.value==value
    assert d.input_name=='us_gdp_growth' and d.evidence in s.evidence_references
    assert d.evidence.source_snapshot_hash in s.source_snapshot_hashes
    assert d.description.startswith('synthetic')


def test_scenario_priority_is_explicit_order_not_probability(cfg,make_evidence):
    c=rules_config(cfg);s=build(c,data(c,make_evidence,-1))
    assert s.dominant_scenario=='RECESSION_RISK'
    assert s.secondary_scenario=='LATE_CYCLE_SLOWDOWN'
    assert build(replace(c,scenario_rules=c.scenario_rules[::-1]),data(c,make_evidence,-1)).dominant_scenario=='LATE_CYCLE_SLOWDOWN'
    assert s.config_hash!=cfg.sha256


def test_partial_pillar_has_no_driver_or_healthy_state(cfg,make_evidence):
    c=rules_config(cfg);s=build(c,[make_evidence()]);p=next(p for p in s.pillars if p.name=='growth')
    assert p.state=='UNKNOWN' and p.evidence_state=='PARTIAL_EVIDENCE'
    assert s.drivers==() and s.dominant_scenario=='INSUFFICIENT_EVIDENCE'


def test_missing_critical_input_blocks_overall_even_with_growth_state(cfg,make_evidence):
    c=rules_config(cfg);rows=[e for e in data(c,make_evidence,-1) if e.observation.series!='US_HIGH_YIELD']
    s=build(c,rows)
    assert next(p for p in s.pillars if p.name=='growth').state=='CONTRACTIONARY'
    assert s.dominant_scenario=='INSUFFICIENT_EVIDENCE' and s.secondary_scenario is None


def test_fully_observed_without_rules_is_still_unknown(cfg,make_evidence):
    s=build(cfg,data(cfg,make_evidence))
    assert s.evidence_completeness==1
    assert all(p.state=='UNKNOWN' for p in s.pillars)
    assert s.drivers==() and s.dominant_scenario=='INSUFFICIENT_EVIDENCE'


def test_future_mutation_cannot_rewrite_driver_or_scenario(cfg,make_evidence):
    c=rules_config(cfg);rows=data(c,make_evidence,-1)
    future=make_evidence(date='2020-07-01',available=ts('2020-07-10'),value=100)
    assert build(c,rows)==build(c,rows+[future])
    assert build(c,rows).sha256==build(c,list(reversed(rows))).sha256


def test_immutable_diagnostic_persistence_and_dictionary(cfg,make_evidence,tmp_path):
    s=build(cfg,[make_evidence()]);a=write_diagnostic(s,root=tmp_path/'diagnostics');b=write_diagnostic(s,root=tmp_path/'diagnostics')
    assert a.sha256==b.sha256
    m=read_snapshot_metadata(a)
    assert m['layer']=='point_in_time' and m['source_hashes']==list(s.source_snapshot_hashes)
    out=tmp_path/'inputs.csv';write_dictionary(cfg,out)
    import csv
    rows=list(csv.DictReader(out.open()))
    assert len(rows)==31 and {r['name'] for r in rows}=={i.name for i in cfg.inputs}
    assert all(r['config_hash']==cfg.sha256 for r in rows)


@pytest.mark.parametrize('mutation',['bounds','state','input','duplicate_pillar','scenario_state','scenario_empty','mutable_inputs'])
def test_invalid_rule_contract_rejected(cfg,mutation):
    with pytest.raises((ValueError,TypeError)):
        r=BandRule('test','us_gdp_growth',(0.,2.),('CONTRACTIONARY','COOLING','HEALTHY'),('negative','neutral','positive'),('low','mid','high'))
        if mutation=='bounds':r=replace(r,bounds=(2.,0.))
        elif mutation=='state':r=replace(r,states=('GREAT','COOLING','HEALTHY'))
        elif mutation=='input':r=replace(r,input_name='ticker')
        elif mutation=='duplicate_pillar':replace(cfg,rules=(r,replace(r,name='other')));return
        elif mutation=='scenario_state':replace(cfg,scenario_rules=(ScenarioRule('RECESSION_RISK',(('growth','UNKNOWN'),)),));return
        elif mutation=='scenario_empty':ScenarioRule('RECESSION_RISK',());return
        elif mutation=='mutable_inputs':replace(cfg,inputs=list(cfg.inputs));return
        replace(cfg,rules=(r,))
