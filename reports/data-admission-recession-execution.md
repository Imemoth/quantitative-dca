# Data Admission + Recession Risk Core execution ledger

Authority: user-supplied 35-section spec, explicitly instructing implementation;
continued by user on 2026-10-05. Base: GitHub main
`3ad752a5be7a1141433927ed7b275d8df7261ffc`, verified with GitHub and git ls-remote.
Branch: research/data-admission-recession-core. Separate clone; previous local
checkpoint repository and raw evidence remain intact.

Ruling: treat the supplied complete written mandate and subsequent 'folytasd' as
authorization for its bounded architecture and execution; no repeat approval gate.
The implementation plan decomposes that mandate without changing methodology.

Ruling: default pillar/scenario economic rules stay unconfigured. The requested
scaffold supports deterministic rules with synthetic tests; evidence alone never
implies HEALTHY. Cost: no usable economic state until a separately reviewed rule
definition and admitted inputs exist. This avoids undocumented threshold selection.

Preflight shared interfaces: Task 1 audit informs evidence admission, not inferred
tiers. Task 2 immutable registry/admission feeds Task 3 selection and Task 4 rules.
Task 3 selected evidence supplies driver references and confidence. Task 5 reports
actual data readiness separately from software tests. No interface conflicts.

No market data network request has been made in this phase. GitHub source retrieval
and package installation are software operations. Previous incidents remain history.

Task 1 complete: 14 retained raw captures rehashed and development dates checked;
0 sources admitted. One original SEC filing manifest absent; explicitly recorded.
Audit reports committed 4e3b712. No financial network request.

Baseline reproduction finding: fresh GitHub snapshot initially 799 PASS / 5 FAIL.
All five failures were FileNotFoundError for the same ignored historical FRED test
capture in tests/providers/test_ingestion.py. Restored the exact pre-existing bounded
sample locally (SHA256 61dbdd00a87dcb438928819d117258237ccbd6bcaa092ea31d8069a35bdd48f2),
validated its observation/realtime dates before copying; focused provider suite 27 PASS.
No production code or tests changed; no new download. Clean-clone full reproduction
requires this external test dependency. It is not committed or redistributed here.

Task 2 RED: new test_contracts collection failed because the diagnostic module did
not exist. GREEN: immutable registry/admission contracts and separate YAML implemented;
focused result recorded below. No feature/regime/target config changed.
Task 2 focused GREEN: 18 PASS.
Task 3 RED: test_engine collection failed on absent engine module. GREEN: 55 combined
contract/engine tests PASS in 2.49s. Selection delegates to canonical latest_known,
assert_pit_safe and evidence verification; calendars gate releases at regional EOD.
Future extension, revision timing, binding, missing/stale/low-quality and region cases
are tested. Confidence is evidence quality, not recession probability.
Task 4 RED: missing reporting module, then 6 behavioral failures / 11 PASS before
rule evaluation. GREEN: 78 PASS. Additional integrity probes exposed 3 failures:
future vintage_start behind an earlier availability; ignored unknown nested context
and scenario fields. Narrow fixes applied; combined subsystem 83 PASS. Conflicting
admissions and missing revision clocks also tested. Dictionary generated (31 rows).

Task 5 focused checks: 86 PASS. Full-suite collection exposed a pytest basename
collision with the existing tests/types/test_contracts.py; renamed only the new
file to test_diagnostic_contracts.py. No test assertion was removed or weakened.
Readiness test first failed on missing software_readiness, then passed after the
manifest gained separate software/data/research/holdout fields.

Independent initial spec PASS / quality FAIL at f4e863c. Three Important boundary
findings reproduced and fixed under TDD; details in recession-risk-independent-reviews.md.
21 additional boundary cases cover mutable contracts, forged persisted state,
replay evidence and defensive series matching. After fixes: full suite 911 PASS
in 50.57s; compileall and git diff --check exit 0. Re-review remains pending.
