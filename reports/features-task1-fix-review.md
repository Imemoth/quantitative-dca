# Features / Targets / Regimes — Task 1 fix-round-1 review

Date: 2026-09-16. Reviewed fix commit `73c3daf` against `5d8d3fc` using the complete supplied diff, the Task 1 brief, the original three findings, the appended implementation report, the frozen design, and the Task 2–3 interfaces.

## Verdict

- **Spec compliance: PASS.** All three findings are addressed within the controller-approved Task 1 metadata/contract scope.
- **Code quality: PASS.** The schema remains strict and immutable, the added semantics are machine-validated, and the identity guard now rejects the required identifier components and synonyms without rejecting the covered economic terms.
- **Task 1 gate: PASSED.** No new material breakage was found in the fix-only diff.

## Finding disposition

### F1 — ADDRESSED

`momentum_universe_percentile` is now registered with a 121-session lookback for the 120-session return, historical membership, historical eligible-universe applicability, and point-in-time eligible-universe normalization (`configs/features_v1.yaml:445–456`). The literal regression checks the formula, normalization, applicability, and membership dependency (`tests/features/test_registry.py:96–107`). The registered count rises to 81 and the maximum planned panel to 94, still inside the frozen 80–95 range.

### F2 — ADDRESSED

Both liquidity features now use the same explicit USD-turnover contract: canonical unadjusted close × verified original-share-unit volume × local-to-USD FX for each historical EOD (`configs/features_v1.yaml:337–360`). Currency and FX are mandatory dependencies; the FX selection rule requires both fixing and availability no later than the historical EOD (`configs/features_v1.yaml:26–53`). `RawDependency` now requires and preserves `value_basis` and non-empty provenance requirements, and the loader enforces the special historical-EOD FX clock (`src/quant_dca/features/registry.py:293–324,412–424`). The regression covers both median dollar volume and the Amihud denominator (`tests/features/test_registry.py:110–146`). Under the controller ruling, numeric split/FX invariance correctly remains a Task 2 calculator responsibility; no Task 1 calculator was required.

### F3 — ADDRESSED

Identity validation now tokenizes identifier components and rejects ticker, symbol, ISIN, CUSIP, SEDOL, FIGI, compact security/entity/instrument IDs, and separated security/entity/instrument/issuer ID or identifier pairs (`src/quant_dca/features/registry.py:27–50,427–435`). It applies to feature names, base signals, transforms, formulas, normalization and applicability, while dependency names are checked during dependency parsing (`src/quant_dca/features/registry.py:323,376–388`). Parameterized regressions cover the reported bypass forms and prove representative economic terms remain accepted (`tests/features/test_registry.py:149–192`).

## Verification basis

The implementation report records **21 focused tests passed** and **415 full-suite tests passed** after the completed fix. Those results are accepted as supplied; suites were not rerun. `git diff --check` for `5d8d3fc..73c3daf` is clean. Code inspection resolved the scoped questions, so no narrow runtime probe was needed. No market network, raw data, holdout, model fit, calculator implementation, or subagent was used.
