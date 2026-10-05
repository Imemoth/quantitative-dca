# Task 9 independent review — 2026-10-04

Scope `3dc2e00..152b68d`; reviewer `regimes_task9_review`.

## Spec compliance: FAIL; code quality: NEEDS FIXES

One important finding, no critical/minor findings.

**R1 — Mutable estimator permits silently stale provenance**, `src/quant_dca/regimes/unsupervised.py:274–287`. The frozen RegimeCandidate retains a live mutable estimator. Predictions trust its current parameters without binding them to candidate_id, training evidence or convergence metadata. A focused synthetic probe modified `model._estimator.means_` after fitting: candidate_id stayed unchanged, maximum probability change was 1.0 and likelihood changed by -5615.7848. A private attribute is not fitted-state integrity protection. Store and verify a parameter fingerprint before prediction, or predict from a protected immutable parameter snapshot. Regression must reject mutation or create a newly identified candidate.

The remaining scoped contracts were satisfied: exact 3–8 HMM/GMM grid; request bounds/roles and chronology before snapshot iteration; all metadata before numeric conversion; training-local scaling; normalized log-space causal forward filtering and explicit resets; within-model diagnostics distinguished from caller-declared alignment evidence; missing-evidence reporting without winner selection.

## Review checks and limits

Read supplied diff once; recovered only truncated unsupervised.py lines135–290. Focused unchanged-code check of Task8 _number/_timestamp/_snapshot confirmed reused metadata admission ordering. Ran only the synthetic estimator-mutation probe. Did not rerun 114 focused/670 full tests; no git mutations, subagents, network, actual data or financial/OOS experiments. Provider revision/unit truth and financial validity remain unverified upstream obligations.

Controller checked the reported mutable reference and prediction consumption in code and accepts R1. Fix round1 assigned original implementer; Task10 waits for scoped independent re-review PASS.
