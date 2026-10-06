"""Regression probes for independent review's immutable and persistence boundaries."""
from dataclasses import fields, make_dataclass, replace

import pytest

from quant_dca.recession_risk.engine import build_snapshot, validate_selected
from quant_dca.recession_risk.reporting import write_diagnostic
from quant_dca.types import Region
from conftest import ts


def build(cfg, evidence=()):
    return build_snapshot(as_of=ts(), region=Region.US,
                          monetary_jurisdiction='FED', evidence=evidence, config=cfg)


@pytest.mark.parametrize('field', ['pillars', 'input_measures', 'evidence_references',
    'drivers', 'publication_timestamps', 'source_snapshot_hashes', 'reason_codes'])
def test_output_rejects_mutable_collections(cfg, field):
    snapshot = build(cfg)
    with pytest.raises(TypeError):
        replace(snapshot, **{field: list(getattr(snapshot, field))})


@pytest.mark.parametrize('field', ['inputs', 'pillars', 'contexts'])
def test_config_rejects_mutable_nested_substitutes(cfg, field):
    original = getattr(cfg, field)[0]
    mutable_type = make_dataclass('MutableContract', [(f.name, f.type) for f in fields(original)])
    mutable = mutable_type(**{f.name: getattr(original, f.name) for f in fields(original)})
    with pytest.raises(TypeError):
        replace(cfg, **{field: (mutable,) + getattr(cfg, field)[1:]})


def test_nested_evidence_rejects_mutable_references(cfg, make_evidence):
    ref = build(cfg, (make_evidence(),)).evidence_references[0]
    with pytest.raises(TypeError):
        replace(ref, admission_evidence_refs=['mutable'])


@pytest.mark.parametrize('change', [
    {'as_of': ts('2009-01-01')},
    {'max_input_available_at': ts('2021-01-01')},
    {'data_confidence': 1.0},
    {'dominant_scenario': 'NORMAL_EXPANSION'},
    {'evidence_completeness': float('nan')},
    {'source_snapshot_hashes': ('a' * 64,)},
])
def test_forged_output_never_persists(cfg, tmp_path, change):
    snapshot = build(cfg)
    with pytest.raises((ValueError, TypeError)):
        write_diagnostic(replace(snapshot, **change), config=cfg, evidence=(), root=tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_persistence_requires_replayable_evidence(cfg, make_evidence, tmp_path):
    rows = (make_evidence(),)
    snapshot = build(cfg, rows)
    with pytest.raises(ValueError):
        write_diagnostic(snapshot, config=cfg, evidence=(), root=tmp_path/'out')
    assert not (tmp_path/'out').exists()
    result = write_diagnostic(snapshot, config=cfg, evidence=rows, root=tmp_path/'out')
    assert result.sha256


def test_selected_evidence_series_must_match_definition(cfg, make_evidence):
    item = make_evidence(observation_changes={'series': 'WRONG_SERIES'},
                         admission_changes={'series': 'US_GDP_GROWTH'})
    definition = next(i for i in cfg.inputs if i.name == 'us_gdp_growth')
    with pytest.raises(ValueError, match='SERIES_MISMATCH'):
        validate_selected(item, definition, ts())


def test_nonempty_snapshot_cannot_forge_confidence_or_config(cfg, make_evidence, tmp_path):
    rows = (make_evidence(),)
    snapshot = build(cfg, rows)
    for changes in ({'data_confidence': 0.9}, {'config_hash': 'f' * 64},
                    {'source_snapshot_hashes': ()}, {'evidence_references': ()}):
        with pytest.raises(ValueError):
            write_diagnostic(replace(snapshot, **changes), config=cfg,
                             evidence=rows, root=tmp_path/'out')
        assert not (tmp_path/'out').exists()


def test_output_rejects_mutable_nested_member(cfg):
    snapshot = build(cfg)
    original = snapshot.pillars[0]
    mutable_type = make_dataclass('MutablePillar', [(f.name, f.type) for f in fields(original)])
    mutable = mutable_type(**{f.name: getattr(original, f.name) for f in fields(original)})
    with pytest.raises(TypeError):
        replace(snapshot, pillars=(mutable,) + snapshot.pillars[1:])
