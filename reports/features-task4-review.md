# Task 4 independent review

**Spec compliance: FAIL. Task quality: Needs fixes.** Review scope: supplied diff, base `00e4d99`, head `755b302`.

## Strengths

- `fundamentals.py:211–226` selects revisions within fiscal periods before choosing the latest period, preventing an old-period restatement from displacing a newer report.
- `valuation.py:294–313` selects report and classification evidence at each historical close; `valuation.py:115–122` requires 756 complete observations. `tests/features/test_fundamentals.py:355–382` specifically checks that a late report revision does not rewrite the earlier valuation history.
- `valuation.py:76–89` rejects total-return prices and mismatched currency/share bases. `fundamentals.py:83–123` and `valuation.py:357–374` preserve explicit financial-sector structural missingness. Feature emission is restricted to the registry names (`fundamentals.py:270–278`, `valuation.py:376–391`), with no identity feature outputs.

## Important findings

1. **Unverified report values bypass the consensus evidence boundary.** `fundamentals.py:256–260` copies every report value and only overwrites `consensus_eps` when an admissible estimate exists. Consequently, a report containing `consensus_eps` produces an earnings surprise through `fundamentals.py:114–116` even with no estimate, a late estimate, or a rejected Tier C estimate. The snapshot then says `selected_consensus=None`, and its provenance includes only the report. Remove any embedded consensus input at the evidenced boundary before inserting a selected estimate. Add a regression using an embedded consensus value with absent and rejected estimate evidence.

2. **Sector ranks silently drop historically eligible peers on other exchanges.** `valuation.py:318–329` makes a peer's values missing whenever its exchange differs from the target exchange. Thus a US sector containing both XNYS and XNAS listings is ranked using only the target's exchange despite all peers having been admitted by `UniverseIndex` at `valuation.py:268–274`. Exchange identity is not a sector or regional eligibility condition. Select each peer's latest eligible close known by the target cutoff and preserve its own calendar/availability evidence, rather than filtering by exchange equality. Test a same-sector XNAS peer whose value changes the XNYS target's percentile.

3. **Unknown fundamental sector is treated as affirmative nonfinancial applicability.** `ReportedFundamentals` accepts an empty sector (`fundamentals.py:136–163`), and the evidenced builder passes it directly to the helper (`fundamentals.py:256–260`). `_is_financial` returns false for missing/blank classification (`fundamentals.py:68–71`), so the helper marks industrial ratios applicable and computes them (`fundamentals.py:83–109`). This contradicts the claimed fail-closed treatment of unknown classification and can destroy structural missingness before downstream imputation. Require known classification for sector-dependent applicability, or reject unknown classification at the evidenced boundary; retain the pure helper's required Financials example. Add an evidenced unknown-sector regression.

## Verification and limits

- Read the supplied diff once. Tool output truncated the valuation hunk mid-function, so `valuation.py` was read separately with numbered lines to recover that missing content.
- Read the exact Task 4 brief, execution preflight, and implementation report. Focused unchanged-code checks addressed two named contract risks: `relative.py:54–91,107–129` for historical classification intervals and eligible-only percentile semantics; `types.py:131–147` for output clock/provenance fields. A focused registry search checked domain selection; it did not expand into a broader crawl.
- The implementation reports 11 focused tests and 462 full-suite passes (`reports/features-task4-implementation.md:29–34`). These runs were not repeated. Existing tests do not exercise the three counterexamples above.
- Economic period normalization remains unverified: `ReportedFundamentals` documents provider-normalized values but carries only `period_end`, while `valuation.py:96–106` consumes EPS, revenue, EBITDA, and FCF directly. The controller should confirm the upstream trailing-period normalization contract before real data admission; this review does not prescribe additional methodology or registry features.
- No network, market data, financial research, code edits, or git mutations were performed. The only write is this review report.

**Assessment:** The revision selection and causal history logic are well scoped, but the consensus bypass and incorrect peer/applicability admission require fixes before Task 4 passes its gate.
