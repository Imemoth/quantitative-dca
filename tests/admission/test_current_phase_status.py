"""Public readiness must reflect actual new requests and incidental exposure."""
import json
from pathlib import Path


def test_acquisition_status_does_not_reuse_prior_zero_exposure_claim():
    m = json.loads(Path('reports/readiness-manifest.json').read_text())
    observed = json.loads(Path('reports/observed-source-inventory.json').read_text())
    phase = m['current_phase_access']
    assert phase['completed_financial_data_network_requests'] == observed['completed_requests']
    assert phase['interrupted_request_count'] == observed['interrupted_request_count']
    assert phase['accessed_2024_plus_financial_observations'] is observed['incidental_2024_plus_exposure']
    assert Path(m['latest_access_incident']).is_file()
    assert m['research_readiness']['financial_model_runs'] == 0
    assert m['research_readiness']['financial_oos_runs'] == 0
    assert m['DCA_RESEARCH_GATE'] == 'BLOCKED_BY_DATA'
    assert m['actual_admitted_panel']['rows'] == m['actual_admitted_panel']['securities'] == 0
    assert m['retrospective_holdout'] == 'NOT_RUN'
