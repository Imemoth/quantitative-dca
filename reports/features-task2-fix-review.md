# Features Task 2 correction round 1 re-review

Reviewed the two findings in `reports/features-task2-review.md`, the appended correction report, the Task 2 brief, and the supplied correction diff against commit `557a84e`. Review was limited to the announced-action chronology fix, the missing-volume price-feature view, and regressions introduced by those changes.

**Verdict: PASS. Spec compliance: PASS. Code quality: PASS.** No new material findings.

## Finding status

- **P1 — ADDRESSED.** Action vintages are filtered by security and `available_at <= cutoff` before selection or payload validation. Each selected action with an explicit `announced_at` now fails closed when `available_at < announced_at`. Therefore an accepted action's announcement cannot be later than its availability or the prediction cutoff, and the existing maximum input-availability clock cannot precede that announcement. `announced_at=None` remains unchanged and is not synthesized. The regression covers contradictory selected evidence, an absent announcement clock, and a genuinely future-unavailable contradictory record.
- **P2 — ADDRESSED.** `build_price_features` explicitly requests `allow_missing_volume=True`; the opt-in exempts only absent/`None` volume from the missing-volume quarantine reason. It does not alter the input row or supply a replacement volume. Present nonfinite/negative volume, OHLC constraints, provenance, calendar/session clocks, and coherent-panel discontinuity screening remain active. Independently evidenced original-share units can produce turnover, while absent evidence leaves both liquidity outputs missing and preserves price-only outputs. Default `validate_ohlcv` behavior remains strict (`False`) and the regression confirms all missing-volume rows are still quarantined under canonical admission.

## Verification

Accepted the reported **22 focused / 118 covering / 437 full passing tests** as instructed; no suite was rerun and no additional probe was needed. Static inspection confirmed the supplied diff contains the complete four-file correction commit changes; its larger hunk context accounts for formatting differences from default `git show`. No market/network/data/holdout work was performed.
