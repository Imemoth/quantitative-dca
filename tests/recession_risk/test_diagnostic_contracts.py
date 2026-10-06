from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import pytest
import yaml

from quant_dca.recession_risk.registry import load_config, config_from_mapping
from quant_dca.recession_risk.evidence import Admission, AdmissionStatus
from quant_dca.types import QualityTier, Region

CONFIG = Path('configs/recession_risk_v1.yaml')


def test_versioned_registry_is_separate_and_complete():
    cfg = load_config()
    assert cfg.version == 'recession-core-v1'
    assert len(cfg.pillars) == 8
    assert set(p.name for p in cfg.pillars) == {'growth','labor','inflation','policy','curve','credit','conditions','stress'}
    assert all('UNKNOWN' in p.states for p in cfg.pillars)
    assert len(cfg.inputs) == 31
    assert cfg.rules == () and cfg.scenario_rules == ()
    assert cfg.context(Region.US, 'FED').exchange == 'XNYS'
    assert cfg.context(Region.EU, 'ECB').exchange == 'XETR'
    assert cfg.context(Region.EU, 'MNB') is None
    assert cfg.context(Region.US, 'ECB') is None
    assert len(cfg.sha256) == 64


def test_configuration_is_immutable_and_hash_covers_changes():
    cfg = load_config()
    with pytest.raises(FrozenInstanceError):
        cfg.version = 'mutated'
    with pytest.raises(FrozenInstanceError):
        cfg.inputs[0].unit = 'bad'
    assert replace(cfg, version='recession-core-v1.1').sha256 != cfg.sha256
    data = yaml.safe_load(CONFIG.read_text())
    parsed = config_from_mapping(data)
    data['inputs'][0]['unit'] = 'changed'
    assert parsed == cfg


@pytest.mark.parametrize('mutation', ['identity','unknown_key','duplicate','pillar','unit','age','nan_weight','bad_vocabulary','unknown_version'])
def test_invalid_registry_is_rejected(mutation):
    d = yaml.safe_load(CONFIG.read_text())
    if mutation == 'identity': d['inputs'][0]['name'] = 'ticker'
    elif mutation == 'unknown_key': d['inputs'][0]['ticker'] = 'ABC'
    elif mutation == 'duplicate': d['inputs'].append(d['inputs'][0].copy())
    elif mutation == 'pillar': d['inputs'][0]['pillar'] = 'imaginary'
    elif mutation == 'unit': d['inputs'][0]['unit'] = ''
    elif mutation == 'age': d['inputs'][0]['max_age_days'] = -1
    elif mutation == 'nan_weight': d['quality_weights']['A'] = float('nan')
    elif mutation == 'bad_vocabulary': d['pillars']['growth'].remove('UNKNOWN')
    else: d['version'] = ''
    with pytest.raises((ValueError, TypeError)):
        config_from_mapping(d)


def admission(**changes):
    values = dict(status=AdmissionStatus.ADMITTED, source='fixture', series='US_GDP_GROWTH',
                  region=Region.US, monetary_jurisdiction='FED', unit='percent_yoy', currency=None,
                  start='2010-01-01', end='2023-12-31', source_snapshot_hash='a'*64,
                  quality=QualityTier.B, evidence_refs=('synthetic-review',),
                  availability_rule='fixture timestamped release; no actual provider admission')
    values.update(changes)
    return Admission(**values)


@pytest.mark.parametrize('changes', [dict(quality=None), dict(evidence_refs=()),dict(availability_rule=''),
    dict(source_snapshot_hash='bad'),dict(end='2024-01-01'),dict(start='2023-01-01',end='2010-01-01')])
def test_admitted_requires_explicit_scoped_evidence(changes):
    with pytest.raises((ValueError,TypeError)):
        admission(**changes)


def test_unadmitted_cannot_claim_quality_and_record_is_frozen():
    with pytest.raises(ValueError):
        admission(status=AdmissionStatus.RAW_ONLY)
    raw = admission(status=AdmissionStatus.RAW_ONLY,quality=None)
    assert raw.quality is None
    with pytest.raises(FrozenInstanceError): raw.quality=QualityTier.A


@pytest.mark.parametrize('location',['context','scenario'])
def test_unknown_nested_fields_are_not_silently_dropped(location):
    d=yaml.safe_load(CONFIG.read_text())
    if location=='context':d['contexts'][0]['policy_override']=True
    else:d['scenario_rules']=[{'scenario':'RECOVERY','when':[['growth','HEALTHY']],'confidence_multiplier':2}]
    with pytest.raises((ValueError,TypeError)):config_from_mapping(d)
