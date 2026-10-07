"""Readiness preflight must not accept global missingness or self-attested PASS."""
import json
from pathlib import Path

import pytest
import yaml


def contract():
    return json.loads(Path('configs/research_readiness_v1.json').read_text())


def test_contract_covers_every_frozen_feature_dependency_and_both_regions():
    c = contract()
    registry = yaml.safe_load(Path('configs/features_v1.yaml').read_text())
    assert {d for f in c['families'].values() for d in f['dependencies']} == set(registry['dependencies'])
    assert all(f['regions'] == ['US', 'EU'] and f['globally_required'] is True for f in c['families'].values())
    assert c['development'] == {'start': '2010-01-01', 'end': '2023-12-31'}


def test_no_evidence_blocks_every_required_family():
    from quant_dca.admission.readiness import assess_readiness
    r = assess_readiness({})
    assert r['status'] == 'BLOCKED_BY_DATA'
    assert {b['family'] for b in r['blockers'] if b['code'] == 'MISSING_FAMILY'} == set(contract()['families'])


def declarations():
    c = contract()
    return {'families': {k: {
        'admission': 'ADMITTED', 'evidence_kind': 'ACTUAL_PROVIDER_RESPONSE',
        'regions': ['US', 'EU'], 'coverage_start': '2010-01-01', 'coverage_end': '2023-12-31',
        'checks': {check: True for check in c['required_checks']},
    } for k in c['families']}, 'panel': {'rows': 100, 'securities': 2,
        'leakage': 'PASS', 'independent_review': 'PASS'}}


@pytest.mark.parametrize('field,value,code', [
    ('admission', 'RAW_ONLY', 'NOT_ADMITTED'),
    ('evidence_kind', 'SYNTHETIC', 'NOT_REAL_EVIDENCE'),
    ('regions', ['US'], 'REGION_COVERAGE'),
    ('coverage_start', '2015-01-01', 'DATE_COVERAGE'),
    ('coverage_end', '2023-12-29', 'DATE_COVERAGE'),
    ('coverage_end', '2024-01-01', 'DATE_COVERAGE'),
])
def test_claimed_coverage_does_not_hide_a_missing_requirement(field, value, code):
    from quant_dca.admission.readiness import assess_readiness
    e = declarations(); e['families']['historical_universe'][field] = value
    r = assess_readiness(e)
    assert {'family': 'historical_universe', 'code': code} in r['blockers']
    assert r['status'] == 'BLOCKED_BY_DATA'


@pytest.mark.parametrize('value', [False, None, 'PASS', 1])
def test_missing_or_non_boolean_checks_cannot_be_promoted(value):
    from quant_dca.admission.readiness import assess_readiness
    e = declarations(); e['families']['fx']['checks']['publication_and_revision'] = value
    assert {'family': 'fx', 'code': 'CHECK:publication_and_revision'} in assess_readiness(e)['blockers']


def test_all_green_caller_strings_never_open_the_real_panel_gate():
    from quant_dca.admission.readiness import assess_readiness
    r = assess_readiness(declarations())
    assert r['status'] == 'BLOCKED_BY_DATA'
    assert {'family': 'panel', 'code': 'INDEPENDENT_REAL_PANEL_EVIDENCE_REQUIRED'} in r['blockers']
    assert r['preflight_only'] is True


def test_global_missing_family_is_not_structural_security_missingness():
    from quant_dca.admission.readiness import assess_readiness
    e = declarations(); del e['families']['fundamentals']
    e['allow_missing_values'] = True
    assert {'family': 'fundamentals', 'code': 'MISSING_FAMILY'} in assess_readiness(e)['blockers']


def test_unknown_family_is_not_silently_ignored():
    from quant_dca.admission.readiness import assess_readiness
    e = declarations(); e['families']['fx_typo'] = e['families'].pop('fx')
    with pytest.raises(ValueError, match='Unknown family'):
        assess_readiness(e)
