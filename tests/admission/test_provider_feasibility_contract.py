"""Audit artifacts must preserve frozen dependencies and fail closed on gaps."""
import csv
import json
from pathlib import Path

import pytest
import yaml


def document(path):
    return json.loads(Path(path).read_text())


def rows(path):
    with Path(path).open(newline='') as stream:
        return list(csv.DictReader(stream))


def test_feature_coverage_is_exactly_the_frozen_dictionary_without_duplicates():
    actual = rows('reports/feature-data-coverage-matrix.csv')
    expected = rows('reports/feature-dictionary.csv')
    assert len(actual) == len(expected) == 94
    assert {r['name'] for r in actual} == {r['name'] for r in expected}
    assert len({r['name'] for r in actual}) == len(actual)


def test_feature_dependencies_match_registry_and_include_membership_admission():
    features = yaml.safe_load(Path('configs/features_v1.yaml').read_text())
    coverage = {r['name']: r for r in rows('reports/feature-data-coverage-matrix.csv')}
    families = document('configs/research_readiness_v1.json')['families']
    mapping = {dep: name for name, spec in families.items() for dep in spec['dependencies']}
    for feature in features['features']:
        row = coverage[feature['name']]
        assert set(row['raw_dependencies'].split(';')) == set(feature['raw_dependencies'])
        assert set(row['dependency_domains'].split(';')) == {mapping[d] for d in feature['raw_dependencies']}
        assert row['cross_cutting_required_domains'] == 'historical_universe'
        assert row['structural_missingness'] == feature['applicability']


def test_reserved_regime_slots_are_not_reported_as_fitted_or_admitted():
    coverage = rows('reports/feature-data-coverage-matrix.csv')
    regimes = [r for r in coverage if r['domain'] == 'regime']
    assert len(regimes) == 13
    for row in regimes:
        assert set(row['dependency_domains'].split(';')) == {'macro', 'market_context'}
        assert row['expected_missingness'] == 'inactive candidate slots omitted; active candidate blocked by unadmitted inputs'
        assert row['model_research_valid'] == 'false'


@pytest.mark.parametrize('family', [
    'historical_universe', 'ohlcv', 'corporate_actions', 'fx', 'fundamentals',
    'macro', 'market_context', 'event_calendars',
])
def test_mvrp_never_drops_required_regions_or_domains(family):
    frozen = document('configs/research_readiness_v1.json')['families'][family]
    mvrp = document('configs/provider_feasibility_v1.json')['mvrp'][family]
    assert mvrp['requirement'] == 'mandatory'
    assert set(mvrp['regions']) == set(frozen['regions'])
    assert set(mvrp['dependencies']) == set(frozen['dependencies'])
    assert mvrp['global_absence_allowed'] is False
    assert mvrp['proxy_activation_requires_review'] is True


def test_decisions_have_resolvable_evidence_and_explicit_limits():
    contract = document('configs/provider_feasibility_v1.json')
    evidence = {e['id']: e for e in document('reports/provider-evidence.json')['claims']}
    matrix = rows('reports/provider-decision-matrix.csv')
    assert len({r['id'] for r in matrix}) == len(matrix)
    for row in matrix:
        assert row['current_status'] in contract['feasibility_classes']
        assert row['recommended_decision'] in contract['decisions']
        assert row['quality_tier'] == ''  # none of these sources is admitted
        assert row['admission_status'] in {'RAW_ONLY', 'UNAVAILABLE', 'NOT_ADMITTED'}
        for field in contract['provider_required_columns']:
            assert row[field].strip(), (row['id'], field)
        for ref in row['evidence_ids'].split(';'):
            claim = evidence[ref]
            assert claim['claim'] and claim['caveat'] and claim['strength']
            assert claim['accessed_at'] <= '2026-10-07'
            assert claim['url'].startswith('https://') or Path(claim['url']).is_file()


def test_fallbacks_require_evidence_and_cannot_authorize_models():
    contract = document('configs/provider_feasibility_v1.json')
    assert contract['fallback_order'] == [
        'primary', 'free_official', 'free_commercial', 'documented_proxy',
        'low_cost_paid', 'methodology_blocked',
    ]
    for family, fallback in contract['fallbacks'].items():
        assert set(fallback) == set(contract['fallback_order'])
        assert all(fallback.values())
    assert set(contract['fallbacks']) == set(contract['mvrp'])
    assert contract['positive_feasibility_is_admission'] is False
    assert contract['tiny_proof_authorizes_research'] is False
    assert contract['requires_human_model_authorization'] is True


def test_every_feature_has_a_specific_blocker_and_global_missingness_is_not_structural():
    contract = document('configs/provider_feasibility_v1.json')
    for row in rows('reports/feature-data-coverage-matrix.csv'):
        assert row['admission_feasibility'] in contract['feasibility_classes']
        assert row['expected_missingness'] and row['global_unavailability_risk']
        assert row['current_provider_candidate'] and row['blocking_evidence_ids']
        assert row['model_research_valid'] == 'false'


def test_no_false_proof_or_gate_pass_without_any_admitted_rows():
    m = document('reports/readiness-manifest.json')
    proof = document('reports/proof-panel-status.json')
    assert proof['rows'] == proof['securities'] == 0
    assert proof['dates'] is None
    assert proof['quality_gate'] == proof['leakage_gate'] == 'BLOCKED_NOT_RUN'
    assert proof['architecture_with_real_data'] == 'NOT_ESTABLISHED'
    assert all(check['status'] == 'BLOCKED_NOT_RUN' for check in proof['checks'])
    assert m['DCA_RESEARCH_GATE'] == 'BLOCKED_BY_DATA'
    assert m['financial_research_runs'] == m['financial_oos_research_runs'] == 0
    assert m['provider_feasibility']['primary_state'] == 'BLOCKED_BY_DATA'
    assert m['retrospective_holdout'] == 'NOT_RUN'


def test_phase_access_receipts_preserve_prior_exposure_instead_of_resetting_history():
    m = document('reports/readiness-manifest.json')
    phase = m['current_phase_access']
    assert phase['phase'] == 'PROVIDER_FEASIBILITY_ADMISSION_CLOSURE'
    receipt = document(phase['receipt'])
    assert phase['completed_financial_data_network_requests'] == receipt['completed_requests'] == 0
    assert phase['accessed_2024_plus_financial_observations'] is True
    old = m['previous_phase_access']['data_acquisition_admission_closure']
    assert old['completed_financial_data_network_requests'] == 4
    assert old['interrupted_request_count'] == 'UNKNOWN'
    assert old['accessed_2024_plus_financial_observations'] is True


def test_macro_inventory_covers_all_required_topics_by_region_with_revision_limits():
    macro = rows('reports/macro-series-feasibility.csv')
    required = document('configs/provider_feasibility_v1.json')['macro_required_topics']
    assert len({(r['region'], r['topic']) for r in macro}) == len(macro)
    for region, topics in required.items():
        assert {r['topic'] for r in macro if r['region'] == region} == set(topics)
    for row in macro:
        for field in ('observation_grain', 'publication', 'vintage', 'units',
                      'request_bound', 'jurisdiction', 'evidence_ids', 'remediation'):
            assert row[field]
        assert row['admission_status'] in {'RAW_ONLY', 'MISSING'}


def test_unresolved_fred_licensing_is_not_reported_as_a_legal_prohibition():
    matrix = {row['id']: row for row in rows('reports/provider-decision-matrix.csv')}
    fred = matrix['M1']
    assert fred['recommended_decision'] == 'UNRESOLVED'
    assert 'LICENSING_REQUIRES_HUMAN_REVIEW' in fred['licensing']
    assert fred['admission_status'] == 'RAW_ONLY'
    assert fred['quality_tier'] == ''
    assert fred['current_status'] == 'METHODOLOGY_BLOCKED_BY_DATA'
    fallback = document('configs/provider_feasibility_v1.json')['fallbacks']['macro']['free_commercial']
    assert 'LICENSING_REQUIRES_HUMAN_REVIEW' in fallback
    assert document('reports/readiness-manifest.json')['DCA_RESEARCH_GATE'] == 'BLOCKED_BY_DATA'
