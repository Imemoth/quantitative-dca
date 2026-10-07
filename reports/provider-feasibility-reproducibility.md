# Provider-feasibility reproducibility

Branch: research/provider-feasibility-admission-closure.
Durable starting SHA: 2717926687378696e8b02a9ed7e3f4d4a4d8e1fe.
Original recovered SHA: 52e56a4b5671995db251efeeadfa49774faca384 (CASE A).
No reconstruction or history rewrite was performed. c976a35 records recovery;
its proposed C0–C5 expansion was subsequently stopped by the user.
The final commit is the commit containing this report and final verification;
resolve with `git log -1 --format=%H -- reports/provider-feasibility-verification.json`.
The external fallback manifest, if needed, records the exact packaged final SHA.

Use Python 3.12 and the dependencies declared by pyproject.toml. Verification used
Python 3.12.14 and the versions recorded in readiness-manifest.json. Commands:

```bash
python -m pip install -e '.[test]'
python -m pytest -q
python -m pytest -q tests/admission tests/recession_risk/test_readiness.py
python -m compileall -q src tests
git diff --check
```

Two legacy ingestion tests require the owner's existing private fixture at
`data/raw/provider_probes/FRED_CPIAUCSL_2023_sample.raw` (568 bytes), SHA256:
61dbdd00a87dcb438928819d117258237ccbd6bcaa092ea31d8069a35bdd48f2.
It remains ignored and outside public Git/archive. Restore it from the already
retained private evidence archive, not by fetching latest FRED observations.
A public source-only checkout cannot reproduce those two tests without that
private prerequisite. Do not skip/delete/weaken the tests to mask its absence.

The final verification JSON contains log hashes and frozen-contract hashes.
Feature/regime YAML, 94-slot dictionary, 20-target dictionary and source modules
remain unchanged from 2717926. No actual panel hash exists: admitted rows and
securities are zero. Existing raw-source hashes remain in their safe inventories;
raw provider files are excluded from public history and any fallback archive.

A successful normal branch push is the durable checkpoint. If push authentication
fails, one complete Git bundle plus one source-only ZIP preserve the final history.
No merge or production handoff is part of this closure. STOP for human review.
