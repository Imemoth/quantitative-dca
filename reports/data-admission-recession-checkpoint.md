# Data Admission + Recession Risk Core checkpoint

Status: SOFTWARE CHECKPOINT PASS — STOP FOR HUMAN REVIEW; DATA ADMISSION BLOCKED.
Base GitHub main: 3ad752a5be7a1141433927ed7b275d8df7261ffc.
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
| Independent reviews | Spec PASS + quality PASS; recession-risk-independent-reviews.md |
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

Verified code commit: `7212a30ace837173378b0ccc6f0adcd3ed5931fe`.
Full suite: **911 PASS** (final rerun 47.80s). Recession subsystem: **107 PASS** (3.52s).
`compileall` and `git diff --check`: exit 0. Initial baseline: 804 tests.
Independent review history and dispositions: `recession-risk-independent-reviews.md`.
Machine-readable verification: `recession-risk-verification.json`.

Python 3.12+, install `pip install -e '.[test]'` in an isolated environment.
Run `python -m pytest -q`, `python -m compileall -q src tests`, `git diff --check`.
No command above downloads market data. The full suite must have the recorded FRED
sample at data/raw/provider_probes/FRED_CPIAUCSL_2023_sample.raw; without it five
existing tests fail rather than silently skip. Its SHA256 is
61dbdd00a87dcb438928819d117258237ccbd6bcaa092ea31d8069a35bdd48f2.

The private checkpoint ZIP includes this one already-retained test dependency in
its original relative path, so extracting it preserves full-suite reproducibility.
It is not committed to Git or claimed as admitted data. Other audit raw captures
are not redistributed. The ZIP also carries a Git bundle with checkpoint history.

Dictionary generation:
`from quant_dca.recession_risk.reporting import write_dictionary`
and `write_dictionary(load_config(), 'reports/recession-risk-input-dictionary.csv')`,
with load_config from quant_dca.recession_risk.registry.

## Stop point

Both independent reviews PASS. Software checkpoint complete; stopped for human review.
Do not automatically start Models/Policy/Validation or the retrospective holdout.

## Logical commits

| Commit | Scope |
|---|---|
| da2cfbc | User mandate and execution plan |
| 4e3b712 | Phase A retained-data audit; no automatic admission |
| 2cc5043 | Diagnostic registry and admission contracts |
| 767cb0e | PIT snapshot and evidence confidence |
| c0d95cb | Deterministic rules, drivers and reporting |
| d418f02 | Architecture, readiness and deferred design notes |
| f4e863c | Full-suite collection fix and review draft |
| 7212a30 | TDD fixes for independent review findings; both re-reviews PASS |

Final documentation commit is identified by the bundled branch HEAD. No remote push
or main merge was performed. Review the ZIP/Git bundle before any integration.
