# Data Admission + Recession Risk Core checkpoint

Status: REVIEW PENDING — not closed. Base GitHub main: 3ad752a5be7a1141433927ed7b275d8df7261ffc.
Branch: research/data-admission-recession-core. No main merge.

## Deliverable map

| Deliverable | Artifact / status |
|---|---|
| Development admission and provider blockers | development-panel-admission.md; data-source-quality-map.csv |
| Actual retained evidence receipt | data-admission-evidence.json: 14 verified captures; zero admissions |
| Real-panel leakage | REAL_PANEL_LEAKAGE_GATE_BLOCKED_BY_DATA_ADMISSION |
| DCA research gate | BLOCKED + separate human approval required |
| Core architecture, pillar/scenario/driver/snapshot contracts | recession-risk-core-architecture.md |
| Exact diagnostic dictionary | recession-risk-input-dictionary.csv: 31 definitions |
| USA and EU/jurisdiction source map | recession-risk-input-admission.md |
| Historical smoke | HISTORICAL_DIAGNOSTIC_BLOCKED_BY_DATA_ADMISSION |
| Tests and TDD ledger | data-admission-recession-execution.md |
| Independent reviews | Pending |
| Full dashboard note | ../docs/recession-risk-dashboard-full-v1.md |
| Probability V2 note | ../docs/recession-risk-probability-v2.md |
| Macro Risk Gate note | ../docs/macro-risk-gate-experiment.md |
| Readiness | readiness-manifest.json; software/data/research/holdout separated |

Financial model research runs: **0**. Financial OOS runs: **0**.
Retrospective holdout: **NOT RUN, NOT PRISTINE**.
True forward validation: **NOT STARTED**; requires final V1 freeze.
2024+ financial observations accessed in this phase: **NO**.
Earlier access incidents remain documented; no whole-project pristine claim.
Actual admitted PIT development panel ready: **NO**. Real-panel leakage PASS: **NO**.
Models/Policy/Validation may start now: **NO** — independent human approval remains
required even if future data gates pass. No production/Codex handoff.

## Known limitations

No source has been promoted from raw evidence to an admitted panel. Default economic
pillar/scenario rules remain empty; even complete data therefore produces UNKNOWN
until rules are separately reviewed. Confidence and freshness parameters are explicit
operational heuristics, not empirically calibrated reliability. The core has no UI,
model, policy or security-level feature integration. Unsupported EU jurisdictions
have no ECB fallback. No proprietary series or paid source was purchased or assumed.

Admission review references are trusted supplied attestations; canonical content
binding checks integrity, not the authenticity or legal sufficiency of the review.
Actual source vetting stays a human/research responsibility. Historical raw audit
captures remain external to GitHub. The original full suite additionally needs the
pre-existing bounded FRED CPI replay file (see ledger), also ignored by Git.

## Reproduction

Python 3.12+, install `pip install -e '.[test]'` in an isolated environment.
Run `python -m pytest -q`, `python -m compileall -q src tests`, `git diff --check`.
No command above downloads market data. The full suite must have the recorded FRED
sample at data/raw/provider_probes/FRED_CPIAUCSL_2023_sample.raw; without it five
existing tests fail rather than silently skip. Its SHA256 is
61dbdd00a87dcb438928819d117258237ccbd6bcaa092ea31d8069a35bdd48f2.

Dictionary generation:
`from quant_dca.recession_risk.reporting import write_dictionary`
and `write_dictionary(load_config(), 'reports/recession-risk-input-dictionary.csv')`,
with load_config from quant_dca.recession_risk.registry.

## Stop point

After both independent reviews PASS and final verification, stop for human review.
Do not automatically start Models/Policy/Validation or the retrospective holdout.
