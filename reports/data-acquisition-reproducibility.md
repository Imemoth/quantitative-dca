# Acquisition closure reproducibility

Base: `e58bf6001446c3787bf8d5b11d4b1ab94ba8a4e6`.
Branch: `research/data-acquisition-admission-closure`. The original reviewed
checkpoint tree is preserved through the external normal merge; not re-created.

Environment: Python 3.12.14; dependencies declared in pyproject.toml. Use an isolated
environment and install the project with its test extra. Verification commands:

```sh
python -m pytest -q
python -m compileall -q src tests
git diff --check
```

Public source checkout is sufficient for the new synthetic admission tests. The
pre-existing offline FRED replay tests require the separately retained three-row
2023 CPI fixture, supplied privately alongside the source in the checkpoint.
It remains ignored by Git. No new raw acquisition dataset is included in the
checkpoint. Actual research data remains external; the software report
does not imply the public repository contains a reproducible financial panel.

To reproduce the new FRED profiles without any network request, obtain the nine
exact raw blobs identified by `raw-data-quality-results.json`, verify SHA-256,
JSON-decode and call `quant_dca.admission.profile.profile_fred(document,
request_bounds=entry['request_bounds'])` for each. The request bounds come from
the retained request/audit receipts, not inferred from the response. Compare the
returned aggregate fields. Keep vintage chunks separate. Retained original audit
and manifest integrity evidence is in `data-admission-evidence.json`.

To reproduce the blocked readiness preflight, JSON-decode
`reports/research-readiness-evidence.json`, call
`quant_dca.admission.readiness.assess_readiness(evidence)`, and compare with
`reports/research-readiness-preflight.json`. This never authenticates source claims
or issues READY; real-panel verification is still absent.

New listing/action probe parameters, source hashes and manifest receipt fields are
in `observed-source-inventory.json`; no private key or credential URL is stored.
Those exact hashes, not a future redownload, identify this capture. Structural
listing counts use symbol uniqueness, assetType counts, missing names and IPO <=
delisting dates. Action counts use event-date uniqueness, positive split decimal
numerator/denominator, finite nonnegative amounts, currency, and date chronology.
They are descriptive raw checks, not economic reconciliation or rights evidence.

No model, feature, threshold, calibration or policy experiment occurred. Financial
model/OOS counters remain 0/0. No fitted artifact, random seed search or financial
result is claimed. The execution ledger records software TDD and source inspection.
