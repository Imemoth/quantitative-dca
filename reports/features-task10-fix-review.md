# Task 10 fix round 1 independent re-review — 2026-10-04

Reviewer `features_task10_fix_review`; scope `c6e8715..02a61d8`.

**R1 — future selected regime evidence: ADDRESSED.** integration.py:40–77 revalidates current/prior inputs at their EODs, training rows at each original as-of within fit bounds and prediction inputs at prediction cutoff. Canonical Task8 validation enforces PIT and exact row cutoff. Constructor preflight precedes prediction iteration; staged preflight precedes universe/source reads and repeats before regime source verification. Dependency clocks include availability, publication, revision and input clocks. Regressions: test_feature_integration.py:289–331,363–377.

**R2 — hardcoded B promotes C dependencies: ADDRESSED.** Worst validated dependency tier replaces hardcoded B. Heuristic uses current/history; unsupervised uses prediction/training. Unknown quality fails canonical validation. C retention and A/B exclusion after serialization are tested at test_feature_integration.py:334–360. Dictionary generator and CSV agree on floor C and branch policy.

**New fix breakage:** None. **Out-of-scope observations:** None.

Reviewed covering assertions and appended evidence:48focused/364subsystem/758fullPASS,compileall/diffcheck exit0. No suite rerun or additional probe needed.

**Final scoped spec: PASS. Final scoped quality: PASS.** All findings addressed, no Critical/Important fix breakage. Synthetic software evidence only, not research gate certification.
