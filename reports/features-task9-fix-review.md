# Task 9 fix round 1 independent review — 2026-10-04

Reviewer `regimes_task9_fix_review`; scope `152b68d..48f03f3`.

**R1 — Mutable estimator permits stale provenance: ADDRESSED.** `src/quant_dca/regimes/unsupervised.py:246–288` fingerprints estimator configuration, fitted prediction arrays, shapes/dtypes and fit metadata. The fingerprint enters candidate identity at `:321–329`. Integrity checks reject changes before input iteration (`:372`) and before scoring (`:343`), including mutation during lazy iteration.

**New breakage in fix diff:** None.

**Out-of-scope observations:** None.

**Verification:** Report names covering mutation, refit, stable-identity and lazy-iteration regressions; records 139 focused/695 full passes plus compileall/diff-check success. Diff supports coverage claims. No tests rerun or additional probes needed.

**Fix round:** All findings addressed; no new Critical/Important breakage.

**Final spec: PASS. Final quality: PASS.**

This is software acceptance only. No financial comparison/winner selection, real data admission, OOS experiment or retrospective holdout evaluation has occurred.
