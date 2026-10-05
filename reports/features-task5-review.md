# Features Task 5 independent review

Date: 2026-09-17  
Reviewed range: `8fa6560..9342d16`  
Spec: **FAIL**  
Quality: **FAIL**  
Disposition: resolve the findings below before Task 6.

## Findings

1. **P2 — Trading-session distance changes with timestamp representation.** `src/quant_dca/features/events.py:144-150` counts through `event_date`, while the constructor accepts that date in the arbitrary supplied timestamp timezone (`events.py:88-93`). For an XNYS security, the same announced instant represented as `2020-01-15T00:30:00+00:00` or `2020-01-14T19:30:00-05:00` passes validation with different dates. From the January 10 EOD these yield three versus two trading sessions, although both represent the same January 14 after-close event. Normalize to the security exchange's local event day before counting, or enforce an equally explicit exchange-date contract. Add a representation-invariance test crossing UTC midnight and a threshold-boundary assertion. This violates the registered trading-session-distance transform.

2. **P2 — Event provenance drops revisions that determine the selected event.** `src/quant_dca/features/events.py:210-219` records only the final future event and security. A known cancellation of an earlier event is a dependency of selecting the later event, but its availability and quality disappear. The existing cancellation fixture already demonstrates the case: the January 9 cancellation causes selection of the January 14 event announced January 3, yet `max_input_available_at` records January 3. Cancelling the only event leaves provenance based solely on the security; an A-quality surviving event can also hide a B-quality cancellation. Preserve dependency evidence for versions that change event selection, including cancellations and relevance-changing revisions, and propagate their latest availability and worst accepted quality. Assert those fields in the cancellation fixtures. Numeric PIT selection is gated, but the resulting dependency provenance is incomplete.

3. **P2 — Event relevance accepts an ineffective security classification.** `src/quant_dca/features/events.py:162-169` checks classification availability but never validates `active_from` / `active_to`. A previously published security version whose effective interval has ended still supplies the exchange, region, and monetary jurisdiction, so the builder can select an obsolete policy calendar and wrong exchange distance. Conversely, a preannounced future-effective version can be used too early. Apply the same effective-interval check used by the macro builder before using classification fields; cover both endpoints of the half-open interval. Availability alone does not establish historical classification applicability.

## Satisfied portions

- Output names and calculations match exactly the 13 macro and 6 event definitions in the unchanged V1 registry; no additional transform grid or methodology was introduced.
- Macro selection resolves known vintages within each observation period before choosing the latest period. Regional roles and monetary-jurisdiction roles are explicit; absent local EU policy/liquidity series do not fall back to ECB.
- Canonical selection validates publication/revision chronology and filters future candidate versions; both builders hard-fail a future direct security record. Macro observation dates do not establish availability.
- Event versions resolve before relevance selection. Announcement timestamps cannot exceed availability. Known cancellations supersede originals, future revisions remain excluded, and events before the EOD boundary are excluded. The date-only helper conservatively rejects same-day announcement availability.
- Missing evidence remains missing and selected Tier C evidence is rejected. Macro dependency timestamps and worst-quality propagation include the selected level/lag inputs.

## Evidence and scope

Read the Task 5 brief, preflight rulings, implementation report, and supplied diff once. The initial tool output truncated parts of the implementation hunks; only those missing portions were subsequently read. Unchanged registry definitions, canonical record fields, PIT selection, and calendar date semantics were inspected solely to resolve the named contract risks.

The implementation report records **9 focused tests passed** and **477 full-suite tests passed**. Those results are acknowledged as supplied evidence, not independently rerun; no repeated suite, network access, market-data collection, audit, git mutation, or methodology expansion was performed. The identified cases are not asserted by the existing nine tests. All review findings are bounded implementation corrections within Task 5.
