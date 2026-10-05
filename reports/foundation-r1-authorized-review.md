# Foundation F2/R1 authorized repair — scoped independent review

Date: 2026-09-16. Reviewed implementation: `17bea46` against implementation parent `c13d070` and authorized base `6fa1901`, using the supplied complete fix diff. This review is limited to R1 and material breakage introduced by this repair. Previously accepted F1/F3/F4/F5/F6 boundaries were not reopened.

## Verdict

- **R1: ADDRESSED.** Unrelated later action identities no longer delay historical label maturity or enter dependency provenance. Identity revision resolution still precedes relevance, while corrections that add an event to or remove one from the acquisition window remain causal dependencies.
- **Spec compliance: PASS** for the authorized F2/R1 repair.
- **Code quality: PASS** for the authorized repair. No material new breakage was identified in the fix diff.
- The scoped repair closes the residual software finding that prevented accepting F2 in the prior re-review. The controller retains the overall Foundation gate decision; real-data readiness is not evaluated here.

## Scope and verification basis

I read the authorization brief, the complete prior re-review and R1 acceptance condition, the implementation report, the supplied diff, and the corresponding source/tests at `17bea46`. The supplied artifact uses expanded diff context, so it is not byte-identical to Git's default rendering; its three changed files, blob identities, and changed hunks correspond to implementation commit `17bea46`. A fresh `git diff --check 17bea46^ 17bea46` completed without errors.

Per the review instruction, I did not rerun either the focused or full test suite. I verified the reported test evidence against the diff and code paths. The implementation report records the required TDD RED (`6 failed, 22 deselected` before production change), covering GREEN (`48 passed`), and full-suite GREEN (`394 passed`). The six added parameterized cases are present and directly target the prior failure. No runtime probe was needed because no behavior remained ambiguous after static tracing.

No network request, market/raw-data read, holdout access, subagent, code change, or test-suite execution was used. This report is the only intentional write.

## Finding assessment

| Finding | Verdict | Evidence |
| --- | --- | --- |
| R1 — unrelated future identities postpone historical labels | **ADDRESSED** | `economic_acquisition_cost` first materializes the supplied versions and resolves one selected revision per identity. It then derives dependency IDs from any historical version whose ex-date intersects `(baseline, fill]`, narrows the already-selected rows to those IDs, and only then derives economically relevant selected rows. Maturity and `selected_action_versions` consume the narrowed selected set, so unrelated later identities cannot supply availability timestamps or provenance. |
| R1 acceptance — retain corrections that remove events | **ADDRESSED** | An identity remains a dependency when an older version was in-window even if its selected correction moved outside or onto the excluded baseline boundary. The selected correction contributes availability/provenance, while no superseded row contributes economics. |
| R1 acceptance — retain corrections that add events | **ADDRESSED** | An identity remains a dependency when the selected correction moves into the window even if the older version was outside. The selected correction alone enters the relevant arithmetic. |
| R1 acceptance — unchanged economics and maturity under unrelated full history at 5/20/60 sessions | **ADDRESSED** | The added horizon regression supplies 16 distinct quarterly identities through 2023 and compares full reversed history with the causal subset. It asserts identical total/cashflows, literal horizon-specific maturity, one-identity provenance, and `label_matures_at <=` 2021/2022/2023 training cutoffs. |
| R1 acceptance — no duplicate economics | **ADDRESSED** | Selection remains one row per action identity. The crossing-window regressions include a duplicate copy of the selected correction and assert the exact total and single provenance tuple. Existing F2 duplicate/revision tests remain intact. |

## Causal-path review

The repair is narrowly placed and composes correctly with the existing label path:

1. `_selected_actions(versions, security_id, selection_cutoff)` resolves complete identities before any relevance filter.
2. `_relevant_actions(..., versions)` is used only to identify identities with at least one supplied historical in-window ex-date. This preserves the correction history required to detect both additions and removals.
3. The resolved `selected` rows are narrowed by that identity set. Raw historical rows never reach action ordering, split/dividend arithmetic, maturity, or provenance.
4. `_relevant_actions(..., selected)` determines which selected revisions affect economics.
5. `required_knowledge` and `selected_action_versions` use the same narrowed selected rows, keeping maturity and provenance consistent.

This directly removes the prior blanket dependency on every selected security action while avoiding the prohibited latest-ex-date prefilter.

## Regression evidence assessment

The reported RED is credible and specific to R1: under the pre-fix path, every selected identity fed `required_knowledge`, so the unrelated October 2023 action deterministically became the maximum maturity in all six new parameterized cases. The production change removes exactly that path.

The GREEN assertions cover the required dimensions:

- actual exchange-derived 5/20/60 eligible-session fills;
- invariant economics, cashflows, maturity, and provenance with unrelated later full-history additions;
- historical usability at the stated training cutoffs;
- correction movement out of the window, into the window, and onto the excluded baseline boundary;
- duplicate selected rows without duplicate economics;
- unrelated later split excluded from maturity and provenance.

The existing broader tests continue to provide reported coverage for raw bar/calendar guards, native/HUF cashflows, FX availability, feature/target separation, action ambiguity, and correction-removal behavior. Those unchanged systems were not re-reviewed.

## New breakage review

**No material new breakage identified (severity: none).** The production diff changes only dependency scoping inside `economic_acquisition_cost`; raw-price checks, calendar checks, selected-version ordering, payable cashflow handling, FX conversion/availability, feature price production, and target record shape are unchanged. The narrowed selected set is deliberately shared by maturity and provenance, preventing a mismatch where economics are corrected but unrelated identities remain attached as evidence.

The added tests are deterministic, offline, use only 2020–2023 synthetic facts, consume an iterator to guard single materialization, and assert literal results rather than merely successful execution.

## Out of scope and limitations

- F1/F3/F4/F5/F6 remain accepted from the prior scoped re-review and were not broadly reassessed.
- Real-data readiness, Task0/panel admission, quality-tier assignment, raw-audit artifacts, and any holdout work remain out of scope.
- The producer depends on supplied revision history; a latest-only input cannot reveal an omitted historical in-window version. It does not promise final truth against revisions not supplied yet.
- The policy is intentionally conservative within one identity: if any supplied version intersects the window, the selected revision remains a dependency even when it removes the event. This is required correction knowledge, not the unrelated-identity defect.
- Ambiguous supplied revision chronology continues to fail closed before relevance. That is the preserved pre-existing validation contract, not a regression introduced by this fix.
- Test results are accepted from the implementation report and verified structurally against the diff; they were not independently rerun, as explicitly directed.

## Final decision

The authorized F2/R1 repair satisfies the prior acceptance condition. **R1 is ADDRESSED; spec compliance PASS; code quality PASS.**
