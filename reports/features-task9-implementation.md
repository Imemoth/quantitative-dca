# Features / Targets / Regimes — Task 9 implementation

Status: DONE — implementation and synthetic verification complete; controller review pending.
Base: `3dc2e0054aee080c22947204a62145ebb923bd46`.
Task commit subject: `feat: add unsupervised regime candidate framework`.

## Implemented scope

- Real `hmmlearn.hmm.GaussianHMM` and `sklearn.mixture.GaussianMixture` candidates, common fit/predict/diagnostic interfaces and an exact 3–8-state grid for each family.
- Lazy canonical partition envelopes validate requested roles, 2010–2023 bounds, fold, region and explicit physical units before input iteration. Fit permits train only; prediction permits train subsets and strictly later same-fold inner validation only. Outer OOS and holdout are rejected.
- The software candidate uses three explicitly declared raw signals: broad-market momentum (fractional return), VIX (index points), HY spread (percentage points). This is not a research-selected/frozen feature set. Existing Task 8 canonical metadata/PIT validation is reused before any numeric values are consumed. Target fields, direct identity, missing or nonfinite values and unexpected schemas are rejected.
- Local train-only standard scaling (population standard deviation, constant-dimension scale 1), deterministic seeds, fixed documented numerical defaults and provenance retaining training evidence, dependency versions, schema, scale statistics, sequence boundaries and candidate digest.
- HMM historical probability outputs use log-space causal forward filtering; no smoothing, backward probabilities or Viterbi outputs. Fitted parameters use the full declared training partition, so training outputs are explicitly **not walk-forward estimates**. Validation and every prediction request explicitly reset to an independent sequence prior. Reset policy is retained in provenance/results. Missing benchmark sessions within one sequence fail; new sequence IDs are required across gaps and cannot be reused.
- Likelihoods include the train scale log-Jacobian correction and are reported in declared raw signal units. Standardized likelihood remains separately exposed. Scores do not establish financial validity or automatic comparability across different datasets.
- Descriptive occupancy and transition diagnostics exclude sequence reset edges. Temporal state stability is one minus total variation between first/second half occupancy; transition stability uses common supported rows in the two halves. Unsupported diagnostics return `None`. These are within-fitted-candidate statistics, not cross-fit state alignment.
- Inner-validation comparison reports require caller-declared cross-fit alignment/stability evidence, economic annotations for every state and downstream summaries for 5D/20D/60D. Missing evidence or convergence makes the report incomplete. External evidence is explicitly unverified. No winner policy, in-sample likelihood selection or executed financial comparison exists.

The pure `forward_filter_unvalidated` helper establishes no PIT/date/unit/fit evidence. Provider revision truth and actual source-unit admission remain upstream responsibilities; passing declared metadata checks does not establish those facts.

## TDD evidence

1. Before implementation: `/workspace/scratch/616ad772b2da/quant-dca-test-env/bin/python -m pytest tests/regimes/test_unsupervised.py -q` — **46 failed** with expected explicit failures that the unsupervised candidate / selection framework was not implemented. The tests exercised real planned APIs rather than replacing estimators.
2. First GREEN: same focused command — **46 passed in 2.04s**.
3. Self-review found comparison evidence could be converted before validating request bounds. Added `test_comparison_request_bounds_checked_before_external_numeric_evidence`; its individual RED run failed with `AssertionError: value consumed before metadata validated`. Added the shared request gate before external evidence consumption.
4. Focused regime GREEN: `python -m pytest tests/regimes -q` — **114 passed in 2.31s**, including 47 Task 9 tests.

The initial interpreter was absent and retained PyArrow files crashed on import (bus error); restoring the declared PyArrow wheel fixed the environment. Initial resolver-selected NumPy 2.5.3 produced an exchange-calendars deprecation warning. Compatible numerical dependencies were pinned to NumPy 2.2.6, SciPy 1.15.3, scikit-learn 1.7.2 and hmmlearn 0.3.3. The interruption later removed the interpreter again; the final verification uses a freshly restored environment, not stale process output.

## Final verification

Fresh restored-environment verification:

- `/workspace/scratch/616ad772b2da/quant-dca-test-env/bin/python -m pytest tests/regimes -q`: **114 passed in 4.08s**, no warnings.
- `/workspace/scratch/616ad772b2da/quant-dca-test-env/bin/python -m pytest -q`: **670 passed in 15.41s**, no warnings (623 baseline + 47 Task 9 cases).
- `/workspace/scratch/616ad772b2da/quant-dca-test-env/bin/python -m compileall -q src/quant_dca tests`: exit 0.
- `git diff --check`: exit 0.
- `python -m pip check`: no broken requirements; it separately warned about leftover interrupted-install backup directories named `~umpy`, `~cipy`, `~cikit-learn`, `~yarrow`. These are environment residue, not package/test failures.

Installed versions: NumPy 2.2.6; SciPy 1.15.3; scikit-learn 1.7.2; hmmlearn 0.3.3; pandas 2.3.3; PyArrow 25.0.1; exchange-calendars 4.13.2; pytest 9.1.1.

## Files changed

- `src/quant_dca/regimes/unsupervised.py`
- `src/quant_dca/regimes/selection.py`
- `tests/regimes/test_unsupervised.py`
- `pyproject.toml` (pinned real estimator/numerical dependencies)
- `reports/features-task9-implementation.md`
- Local SDD mirror: `.superpowers/sdd/2026-09-11-quant-dca-features-targets-regimes/task-9-report.md`

## Self-review and scope limits

Reviewed canonical admission ordering, train-local normalization, the forward recursion against a hand-derived two-state example, prefix/future-mutation invariance, sequence reset behavior, diagnostic transition exclusions, evidence completeness and dependency provenance. Corrected the comparison request gate through RED/GREEN above. Parent-owned status/readiness/ledger and experiment README edits are excluded from this commit. No provider network, market-data reads, research/OOS experiment, financial comparison or holdout use occurred. Fixtures are synthetic and within 2010–2023. No independent reviewer was dispatched by the implementer; controller review remains pending.


## Review fix round 1 — R1 fitted-state integrity

Accepted finding: the live mutable estimator could change prediction probabilities while retaining the original candidate identity and fit metadata.

Implemented a fitted-state SHA-256 fingerprint stored in `FitProvenance` and included in the candidate identity digest. It binds the exact estimator family/class, full estimator configuration, feature count, convergence/iteration/history metadata and every fitted prediction array, including each array's shape and dtype. HMM coverage includes start probabilities, transition matrix, means and source diagonal covariances. GMM coverage includes mixture weights, means, covariances, precisions and precision Cholesky factors. The check runs after request admission and before prediction feature iteration, then again before numeric prediction to reject mutation during lazy input iteration. Changed or missing fitted state fails with `FITTED_STATE_INTEGRITY`; refitting the retained estimator cannot silently reuse the old identity. Unmodified repeated predictions and seeded identities remain stable. This guards ordinary mutation/refit, not arbitrary malicious Python code that forges provenance or replaces methods.

TDD and final verification (task-local interpreter):

- RED: `python -m pytest tests/regimes/test_unsupervised.py -k 'fitted or mutation_rejected' -q` — **23 failed, 47 deselected in 7.87s** before the fix. Changed arrays/configuration/refits reached the forbidden input iterator; fingerprint provenance was absent.
- Initial GREEN: `python -m pytest tests/regimes/test_unsupervised.py -q` — **70 passed in 4.95s**.
- Additional self-review RED: `python -m pytest tests/regimes/test_unsupervised.py -k mutation_during -q` — **2 failed, 70 deselected in 1.90s**, both `DID NOT RAISE ValueError` when a lazy iterator mutated means after the first integrity check. Added the pre-scoring recheck.
- Final focused GREEN: `python -m pytest tests/regimes -q` — **139 passed in 6.15s**, no warnings.
- Final full GREEN: `python -m pytest -q` — **695 passed in 18.84s**, no warnings.
- `python -m compileall -q src/quant_dca tests` — exit 0.
- `git diff --check` — exit 0.

Self-review confirmed all arrays consumed by both probability paths are covered, changes in shape/family configuration and fit metadata are detected, request admission still precedes feature access, and no estimator mutation/refit is silently certified under its earlier candidate identity. Only `unsupervised.py`, its tests and this report were changed for R1; the SDD report receives the same appended evidence. Parent files and review report are excluded from the fix commit. No data/research scope changed. Fix commit subject: `fix: bind regime predictions to fitted-state integrity`. Status: DONE; scoped independent re-review pending.
