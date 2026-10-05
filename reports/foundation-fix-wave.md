# Foundation combined fix wave

Date: 2026-09-16. Base: 25ee9c7. One combined continuation of the existing
F1–F6 implementation patch; no provider audit/admission changes.
Authority: frozen design, evaluation-protocol-amendment-2026-09-11.md,
whole-review F1–F6 and execution-ledger revision/admission rulings.

## Finding-to-change mapping

| Finding | Implementation and regression evidence |
| --- | --- |
| F1 | Shared selector gates by availability then orders explicit revision/publication chronology; canonical identities cannot mix. Universe delegates to it, preventing delayed open-ended listings or memberships from resurrecting delistings. FRED vintage dates remain date-level clocks, without invented intraday times; overlapping date intervals, mixed clocks and unresolved ordering fail closed. Tests cover delayed originals/revisions, cutoffs, ties, FRED normalization and universe delisting. |
| F2 | Resolve `(security_id, action_id)` before effective-date filtering; exact repeats deduplicate, unknown/conflicting revision order fails. Labels record selected action versions and mature no earlier than their availability, including corrections removing events from the window. Features also retain selected-version provenance, quality and availability when a correction removes an adjustment. Tests cover split duplication/correction, dividend amounts, corrected dates, unknown ordering and removal provenance. |
| F3 | Admission preserves distinct explicitly ordered price revisions and quarantines conflicting session duplicates. Mapping history resolves revisions before active intervals. Admission discontinuity anchors are selected at each row's knowledge time; `as_of` validation reselects a coherent panel and mappings at the cutoff. Feature consumer enforces this second stage and forwards auditable discontinuity evidence. Tests cover preserved vintages, changed/invalid mappings and later corrected anchors. |
| F4 | Canonical validation requires actual supported-exchange session and exact scheduled open/close; feature and execution boundaries independently enforce the same clocks. No timestamp repair. Tests cover weekends, US/EU holidays, DST, early closes and wrong clocks through all boundaries. |
| F5 | Snapshot logical hashing encodes typed sequences recursively and normalizes Arrow/Parquet list child-field names while preserving element types/nullability. Actual Task7 records, including applied splits and nested selected-version provenance, round-trip with source/action attribution, verified metadata/lineage and repeat identity. |
| F6 | Execution fill/baseline and split-adjustment inputs must be actual OHLCV instances with unadjusted basis. Actual feature output and canonical-shaped adjusted input are rejected; producer-to-consumer regressions enforce this. |

Two legacy fixture adjustments use the actual XNYS open and a real session
instead of Jan 1; they do not weaken assertions or silently repair raw data.
The finishing pass implemented three already-written failing edge cases:
removed-action feature provenance, as-of mapping cutoff, and feature-panel
discontinuity-evidence forwarding.

## Verification and decisions

- Inherited original RED: 19 failures in 1.30s, attributed to prior fixer.
- Fresh recovery RED after dependency restore: 3 failed, 19 passed in 1.31s.
- Fresh final focused suite: 22 passed in 1.19s.
- Fresh full suite: 388 passed in 1.93s (366 baseline plus 22 regressions).
- Two fresh fixture CLI runs exited 0 with byte-identical JSON and unchanged
  canonical, feature and data hashes; compileall and diff checks passed.
- Exact commands/results and hashes: foundation-fix-tests.txt.

## Remaining boundaries

Independent scoped re-review is still required; this implementation report
does not approve the software gate. Real-data research remains NOT READY:
Task0, actual quality-tier assignment and panel admission remain unresolved.
No market requests, holdout evaluation, credentials, purchases or model research
were performed; only authorized dependency restoration used package downloads.
Raw-only FRED chunk evidence is unchanged and is not admitted by these fixes.

Labels are selected from the supplied version set, not guaranteed final-action
truth; later corrections require rebuilding. Including all selected actions for
that security in maturity/provenance is deliberately conservative. Versioned
price consumers must use the as-of validation stage after revision admission.
Ambiguous PIT selection raises rather than guessing. Request-clipped FRED
intervals are not stitched here. Calendars describe regular scheduled sessions,
not security-specific halts or execution liquidity. Sequence persistence is
limited to supported typed sequence elements, not arbitrary Python objects.
