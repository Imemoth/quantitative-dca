# Task 4 fix re-review

**Spec compliance: PASS. Task quality: PASS.** Scope: correction diff from `eb0dbab` to `e789525`, the three previously reported findings, and the explicit trailing-period declaration. No new material findings were identified in that scope.

## Finding status

| Prior finding | Status | Evidence |
| --- | --- | --- |
| Embedded consensus bypass | Addressed | `fundamentals.py:267–273` removes report-embedded `consensus_eps` before inserting only the separately selected estimate. Absent, late, and Tier C estimate regressions assert both missing surprise and no selected consensus. |
| Cross-exchange eligible sector peers excluded | Addressed | `valuation.py:318–338` selects each eligible member's latest admitted close at or before the target cutoff, selects its report at that close, removes exchange equality as a filter, and retains selected peer evidence. The XNYS/XNAS regression checks the changed percentile, retained XNAS price, and peer availability in the output clock. |
| Unknown sector grants industrial applicability | Addressed | `fundamentals.py:264–265` rejects blank and non-string selected sectors before the helper computes applicability. The blank-sector regression covers the original counterexample; the pure helper's Financials behavior is unchanged. |

## Narrow contract and regression assessment

`ReportedFundamentals.valuation_period_basis` is required and accepts only `trailing_twelve_months` (`fundamentals.py:140,152–155`). The quarterly-basis regression verifies rejection. This makes upstream normalization an explicit admission declaration; it does not calculate or independently verify TTM normalization. That limitation is consistent with the correction appendix and does not add methodology or registry features.

Focused unchanged-code inspection resolved the concrete risk that removing exchange equality could bypass peer calendar or availability admission: `ValuationPrice.__post_init__` checks the declared exchange's actual session close (`valuation.py:145–151`), and `_selected_prices` admits only prices known by their own close (`176–195`). The new target-cutoff filter therefore does not introduce later-close evidence. Peer reports are selected by the peer close, while historical sector membership remains selected at the common target cutoff. Selected peer prices, reports, and classifications feed the existing output evidence and maximum availability calculation (`387–394`). Unit compatibility remains checked by `_raw_valuation` (`76–89`). No new material breakage was identified in these changed paths.

## Verification and limits

- Read the prior review and correction appendix. Read the supplied diff once; output truncation was recovered through targeted source reads rather than rereading the diff.
- The implementation report records **17 focused tests passed** and **468 full-suite tests passed** for the fix round. These are reported results, not reruns by this reviewer. No additional probe was needed after source inspection resolved the scoped contract questions.
- This is a scoped fix review, not renewed validation of the whole branch or real provider data. No network access, subagents, suite reruns, implementation edits, or git mutations were performed. The only write is this report.
