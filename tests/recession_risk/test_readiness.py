import csv,json
from pathlib import Path


def test_readiness_separates_software_data_research_and_holdout():
    m=json.loads(Path('reports/readiness-manifest.json').read_text())
    assert m['software_readiness']['feature_target_regime']=='PASS'
    assert m['data_readiness']['actual_pit_development_panel_available'] is False
    assert m['data_readiness']['real_panel_leakage_gate']=='REAL_PANEL_LEAKAGE_GATE_BLOCKED_BY_DATA_ADMISSION'
    assert m['research_readiness']['models_policy_validation_authorized'] is False
    assert m['research_readiness']['financial_model_runs']==m['research_readiness']['financial_oos_runs']==0
    assert m['holdout_status']['retrospective']=='NOT_RUN'
    assert m['holdout_status']['pristine'] is False
    # The prior sidecar phase remains zero-access evidence. The later acquisition
    # phase has its own receipt-linked assertions in tests/admission.
    assert m['previous_phase_access']['recession_core']['financial_data_network_requests']==0
    assert m['previous_phase_access']['recession_core']['accessed_2024_plus_financial_observations'] is False


def test_source_audit_retains_unknown_tiers_and_explicit_statuses():
    rows=list(csv.DictReader(Path('reports/data-source-quality-map.csv').open()))
    assert len(rows)==11
    for r in rows:
        assert r['admission_status'] in {'RAW_ONLY','MISSING','UNAVAILABLE','UNSUPPORTED_FOR_PIT','REQUIRES_MANUAL_REVIEW'}
        assert r['quality_tier']==''
        assert all(r[k] for k in ('source_units','currency_semantics','remaining_blocker','request_bound','license_usage','rate_limit'))


def test_machine_audit_is_not_admission_or_backtest():
    d=json.loads(Path('reports/data-admission-evidence.json').read_text())
    assert len(d['artifacts'])==14 and d['network_financial_requests']==0
    assert all(a['hash_verified'] and a['date_envelope_verified'] and a['quality_tier'] is None and a['admission']=='RAW_ONLY' for a in d['artifacts'])
