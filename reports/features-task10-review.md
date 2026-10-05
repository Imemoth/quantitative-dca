# Task 10 independent review — 2026-10-04

Scope `2d993a5..c6e8715`; reviewer `features_task10_review`.

**Spec: FAIL. Quality: NEEDS FIXES.**

## R1 — selected regime evidence may contain future availability (Important)

`src/quant_dca/regimes/integration.py:37–56` trusts interpreted.pit_validated without validating selected evidence clocks; bounded_evidence only checks the development envelope. Lines91–94 aggregate historical max_input_available_at but omit historical available_at. Unlike base producers, the path never calls assert_selected_evidence_pit.

A focused synthetic probe changed only historical interpretable evidence.available_at to2021-01-01 21:00UTC, after prediction2020-12-31 21:00UTC. Both build_regime_features and build_feature_snapshot accepted it and emitted89predictors. Hash binding did not enforce PIT.

Required fix: validate every regime evidence branch at construction and staged-snapshot admission, including historical interpretable and training evidence at their applicable cutoffs; aggregate availability across all selected dependencies; add the demonstrated regression.

## Review scope and strengths

Exact seven-producer/81-output coverage, quality floors, masks and predictor-only columns are enforced in features/snapshots.py:69–123. Actual-builder89-column fixture is present. Target store retains separate-layer economic provenance and per-horizon maturity. Reviewer read bounded diff passes, recovered truncated dictionary section, inspected unchanged Task8/9, valuation/share units and Foundation verification for focused risks. One synthetic probe only; no suite rerun, mutations, provider/data/network or research.

## Controller verification and additional R2

Controller inspected integration.py and accepts R1. Also found **R2 — hardcoded regime quality B** at integration.py:98. Both branches can consume permitted C-tier market data, yet every stored regime row is assigned B. This would promote lower-quality evidence in later A/B-only sensitivity. Derive the conservative composite tier from all actual selected branch and training dependencies; never promote a C input to B. Require regression with a permitted C dependency and preservation through snapshot serialization. This is a controller finding, not attributed to the independent reviewer.

Fix round1 covers R1 and R2. Task10 and whole-subsystem gates remain open.
