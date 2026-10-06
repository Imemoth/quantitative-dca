"""Fail-closed required-family preflight, NOT a real-panel leakage validator.

This accepts declarations to enumerate missing evidence. It deliberately never
opens the research gate, even if every caller declaration says PASS. A genuine
panel and independent, artifact-bound checks remain necessary. No such panel
exists in this phase; building a fictitious positive path would assert evidence
we do not have.
"""
import json
from pathlib import Path


CONTRACT_PATH = Path(__file__).resolve().parents[3] / 'configs/research_readiness_v1.json'


def assess_readiness(evidence: dict) -> dict:
    """Enumerate declaration shortfalls; leave actual verification explicitly open."""
    contract = json.loads(CONTRACT_PATH.read_text())
    families = evidence.get('families', {})
    if not isinstance(families, dict):
        raise ValueError('Families must be a mapping')
    if set(families) - set(contract['families']):
        raise ValueError('Unknown family in evidence')
    blockers = []

    def block(family, code):
        blockers.append({'family': family, 'code': code})

    for family, required in contract['families'].items():
        declared = families.get(family)
        if not isinstance(declared, dict) or not declared:
            block(family, 'MISSING_FAMILY')
            continue
        if declared.get('admission') != 'ADMITTED':
            block(family, 'NOT_ADMITTED')
        if declared.get('evidence_kind') != 'ACTUAL_PROVIDER_RESPONSE':
            block(family, 'NOT_REAL_EVIDENCE')
        regions = declared.get('regions')
        if not isinstance(regions, list) or not all(r in regions for r in required['regions']):
            block(family, 'REGION_COVERAGE')
        if declared.get('coverage_start') != contract['development']['start'] or declared.get('coverage_end') != contract['development']['end']:
            block(family, 'DATE_COVERAGE')
        checks = declared.get('checks', {})
        if not isinstance(checks, dict):
            checks = {}
        for check in contract['required_checks']:
            if checks.get(check) is not True:
                block(family, 'CHECK:' + check)
    block('panel', 'INDEPENDENT_REAL_PANEL_EVIDENCE_REQUIRED')
    return {'status': 'BLOCKED_BY_DATA', 'preflight_only': True, 'blockers': blockers}
