# Development checkpoint recovery

This checkpoint is active development, not a completed prototype, research result, frozen configuration, retrospective-holdout authorization, or production handoff.

## Recover code and history

The checkpoint ZIP contains a readable source tree and `quant-dca-v1-history.bundle`. To recover a repository with history into a new directory:

```bash
git clone quant-dca-v1-history.bundle quant-dca-research
cd quant-dca-research
git switch research/development-v1
python -m pip install -e '.[test]' pyarrow duckdb
```

Use Python 3.12 or later. The exact observed environment is recorded in `reports/runtime-environment.json`; dependencies may disappear across scratch runtime restarts even when project files remain. Do not infer a code defect from a missing `pytest` installation.

## Find the actual next task

Read `reports/execution-ledger.md`, `reports/current-status-hu.md`, the task reports, and `git log`. A task is complete only after its recorded independent review passes. A dispatched task that has no implementation commit is unfinished; do not report it as complete. Live sub-agents may not survive a work-session interruption. Inspect the working tree before resuming, preserving draft tests and verified work.

The original spec and all four subplans remain authoritative for methodology, subject to the user's `docs/evaluation-protocol-amendment-2026-09-11.md`. Read that amendment before interpreting original lockbox wording. Foundation tests gate Subproject 2. Fixture success does not establish real-data readiness.

## Data and credential boundaries

- Only 2010–2023 development observations. Enforce end dates before each request; bound vintage/filing/publication history too. Never fetch an unbounded modern history and then filter it.
- Existing raw provider payloads are access/schema evidence unless an explicit admission report says otherwise. An absent quality tier means not admitted, not Tier C.
- FRED credentials are not in the checkpoint. Use a transient process credential supplied through the authorized session or environment; never commit it or include it in report/request logs.
- Original SEC quarter indices and accession samples are not an equity universe or normalized fundamental panel. Their large row counts must not be presented as security coverage.
- Preserve the original documentation incident. The 2024–2026 retrospective holdout is not pristine and is not authorized for evaluation here.

## Authorized stop point

Continue task commits, TDD, review gates, source audit, and the 2015–2023 nested expanding OOS development work. Stop for human review after actual development evidence and a proposed frozen V1 configuration are complete. No retrospective-holdout run or production handoff before that review and separate authorization.
