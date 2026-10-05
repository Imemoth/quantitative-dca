### Correction verdict

- **Historical observation-session cutoff — ADDRESSED.** `build_relative_features` now requires all supplied stock returns to share one ISO observation date, resolves that date through `eligible_session_close`, rejects non-session and post-prediction observations, and uses the resulting actual session close for `UniverseIndex`, cross-sectional returns, and sector classifications. The new stale-Friday/after-Monday-close regression covers both sides of the original defect: the Monday-delisted constituent remains eligible, the Monday joiner stays excluded, and the Friday-effective classification is selected.
- **Future-available direct inputs — ADDRESSED.** `_select_direct_returns` now iterates over every supplied stock, sector-benchmark, and market-benchmark mapping row and applies the canonical PIT/provenance/value checks plus both historical-cutoff clock checks before accepting the row. It no longer skips a supplied future-available row as though the operand were absent. The parameterized regression exercises all three direct mapping roles. Candidate-vintage inputs retain the intended behavior: cross-sectional returns and classifications filter future-unavailable candidates before `latest_known` selects a vintage.

### New breakage review

No new material breakage found in the correction. The calendar API returns the exact close for a real session and `None` for a non-session, so early closes and weekend/holiday rejection follow the intended contract. Missing supported direct horizons can still produce missing derived values, while supplied unsupported or mismatched rows fail closed.

### Assessment

- **Spec compliance: PASS**
- **Task quality: PASS**

The reported correction evidence is credible and directly targeted: RED `5 failed, 9 passed`; GREEN `14 passed`; full suite `451 passed`. Per review scope, these suites were not rerun.
