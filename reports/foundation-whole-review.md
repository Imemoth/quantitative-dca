# Data & PIT Foundation — whole-branch review

Review date: 2026-09-15. Implementation scope: `0431304..0180553`, using the supplied log/stat/diff package and the corresponding source. `3a1ee90` closes Task10 review; current HEAD `8e6097a` additionally corrects status wording. The changes after `0180553` are reporting-only and do not alter the reviewed implementation.

## Verdict

- **Spec compliance: FAIL — six material cross-component findings below.**
- **Code quality: FAIL — revision handling and consumer contracts do not yet compose safely.**
- **Foundation software gate: NOT PASSED.** Resolve these findings in one combined fix wave and obtain scoped independent re-review before Subproject 2.
- **Real-data research readiness: NOT READY, independently of these software findings.** Task0 remains incomplete, actual source tiers remain unassigned, and no US/EU panel is admitted. Passing the software gate will not change those facts.

The individual task approvals, recorded 366 passing tests, and two identical fixture CLI runs are retained as valid scoped evidence. This review does not claim that those suites failed. They miss the concrete combinations below. The Task10 fixture is a two-series synthetic macro path and therefore cannot certify the price/action/universe integration paths.

## Authority and method

Read the review brief, frozen design (especially §§9–12, 24 and mandatory tests), controlling evaluation amendment, Foundation implementation plan, latest execution ledger, Task10 audit and eleven-domain map. Inspected all Foundation implementation modules and relevant existing tests. No market network requests, holdout evaluation, purchases, model experiments, implementation edits, or commits were performed. No subagents were dispatched.

Ran only short offline Python probes for specific newly identified risks. They used existing test fixture constructors via `runpy`, production service calls, and in-memory data frames. No full or targeted pytest suite was rerun. Results are recorded below; the probes wrote no data artifacts. This review report is the only file written by this reviewer.

## Material findings

### F1 — P1: availability ordering resurrects superseded revisions, including delistings

**Locations:** `src/quant_dca/point_in_time/asof.py:103–108`; `src/quant_dca/universe/membership.py:151–160`, consumed by `_security` and `_membership` at lines 168–190. FRED integration consideration: `src/quant_dca/providers/fred.py:116–121`.

The shared selector first chooses the greatest availability timestamp and considers explicit revision chronology only within that availability tie. An older revision delivered later therefore displaces a newer revision already known. UniverseIndex separately implements the same availability-only policy and does not consult `revised_at` at all. The local FX repair did not fix either path.

**Reproduced scenario:** for one observation, old value 1 has `revised_at=2020-01-02`, `available_at=2020-01-10`; corrected value 2 has `revised_at=2020-01-03`, `available_at=2020-01-04`. At January 11, `latest_known` returns **1**, although revision 2 is known and supersedes it. Both rows have valid publication/availability chronology.

**Reproduced universe consequence:** a security correction known January 8, 2022 establishes delisting on January 7 (`active_to=2022-01-07`, revision January 7). An older open-ended listing revision from January 2 arrives January 10. With otherwise sufficient historical membership, 120 actual completed sessions, liquidity and a published fundamental report, `is_eligible` at January 10 returns **True**. The known delisting is undone by delayed delivery. This is a survivorship/eligibility error, not only stale macro data.

**Required fix:** separate knowledge eligibility from economic revision ordering across the shared selector and universe consumers. Define explicit grouping and ambiguity behavior for versioned canonical records; do not lexically order opaque revision IDs. Preserve FRED's date-level vintage chronology as such: its normalized rows currently retain `vintage_start/end` but have no explicit revision timestamp, so a fix that only handles `revised_at` must not silently imply that its date-level rows are solved. Do not invent intraday publication times. Add delayed-original/delayed-revision, pre/post-cutoff, tie and delisting regressions; retain the FX protections.

**Basis:** design §§9.6–9.7 and the execution ledger's retained cross-task ruling.

### F2 — P1: corporate-action revisions are applied as multiple economic events

**Locations:** `src/quant_dca/corporate_actions/economics.py:198–218`, action accumulation at lines 255–271, and `_known_effective_splits` at lines 320–344, consumed at lines 371–374.

Both economic acquisition cost and feature adjustment append every supplied action row. Neither establishes one selected revision per `(security_id, action_id)` nor rejects multiple revisions. The canonical action record explicitly carries revision provenance, so a version-preserving action store naturally supplies this input. No upstream action-vintage selection boundary exists in this Foundation.

**Reproduced scenario:** one January 6 two-for-one split has two known versions with the same action ID, ratio 2, different revision IDs and different availability times. A pre-split raw price 100 becomes **25** in the feature view instead of 50. Buying a delayed raw share at 50 is charged **200 HUF** for four equivalent shares instead of 100 HUF for two. Dividend revisions similarly accumulate foregone distributions twice. Even an exact duplicate can multiply the event.

**Required fix:** establish action identity and revision resolution before economic accumulation. Features must select the version knowable at their cutoff; labels need an explicit selected action version and maturity policy, preserving later availability without adding all versions together. Resolve the revision before testing its ex-date relevance, because corrections can change effective dates. Ambiguity must fail closed. A documented caller preselection contract must be enforced at this boundary if selection remains outside these functions. Cover duplicate rows, corrected split/dividend amounts and dates, and unknown revisions.

**Basis:** design §10 economic equivalence, §9 PIT truth, and Task7's shared feature/target economics requirement.

### F3 — P2: canonical validation destroys legitimate price-vintage history

**Locations:** `src/quant_dca/canonical/validate.py:252–260`; related versioned mapping handling at lines 189–209.

The duplicate key contains only security and session. Consequently every version of a daily price is quarantined whenever a legitimate correction is present. This happens before the planned PIT selection stage. The availability and revision metadata carried by the provider/canonical contracts do not distinguish a revision from a conflicting duplicate. Mapping validation similarly treats multiple known historical versions as ambiguous without resolving revisions; changing only the price duplicate key will not complete the integration.

**Reproduced scenario:** one valid January 2 bar and its January 4 correction with a different revision ID and explicit revised/availability timestamps are passed together to `validate_ohlcv`. Output: **0 valid rows**, `{'DUPLICATE_SESSION': 2}`. The original historical bar is lost along with its correction; downstream as-of reconstruction cannot recover either from valid canonical storage.

**Required fix:** define separate revision-level canonical admission and as-of session-level validation. Preserve legitimate versions and quarantine genuinely indistinguishable/conflicting duplicates. Discontinuity comparisons must use temporally consistent selected anchors, so simply appending revision ID to the duplicate key is insufficient. Either introduce an explicit as-of-aware validation stage or a documented, tested version partitioning stage that composes with PIT selection and mapping history. Keep original raw evidence and quarantine reasons.

**Basis:** design §§9.2, 9.6 and 12's ingestion flow; the plan's revised observations and raw-preservation constraints. Severity is P2 because this presently fails closed, but it blocks admission of corrected price history and can bias coverage.

### F4 — P1: canonical bars can bypass the actual exchange calendar

**Locations:** `src/quant_dca/canonical/validate.py:169–186`; downstream `src/quant_dca/corporate_actions/economics.py:367–369` and execution cashflow timing at lines 286–293. Compare the actual schedule services in `src/quant_dca/calendars/service.py`.

Price validation checks exchange syntax and relative timestamp ordering, but never verifies that the session exists or that the supplied open/close match that exchange's schedule. The CSV provider accepts those explicitly supplied timestamps. The feature consumer trusts the same `session_close_at`, and the economic consumer requests FX at the same supplied `session_open_at`. Thus the calendar module is correct in isolation while the admitted price path can circumvent it.

**Reproduced scenario:** an otherwise valid XNYS bar labeled Saturday January 4, 2020, with open 09:00 UTC, close 10:00 and availability 10:01 passes canonical validation (**1 valid row**) and produces a feature price **100**. An equally malformed weekday bar can claim an early close and expose a full-day OHLC feature before the actual close, or convert an execution at a nonexistent open using the wrong FX quote.

**Required fix:** validate supported exchange/session and the exchange-local date's actual opening/closing instants at the canonical boundary. Missing or contradictory schedule evidence must quarantine or fail closed with an explicit reason. Ensure the consumer entry points cannot obtain trusted execution/feature times from an unvalidated bar. Add US/EU holiday, DST/early-close, nonexistent-session and wrong-clock cross-component regressions. Do not repair raw timestamps silently.

**Basis:** design §9.3, Task2 actual eligible sessions, and the brief's calendar/FX/execution agreement requirement. This is an admission and timing defect, not a request to implement security-specific halt modeling.

### F5 — P2: Task7 feature provenance cannot be persisted by Task9 snapshots

**Locations:** `src/quant_dca/storage/snapshots.py:44–62`, called at lines 72–75 and from `_canonical_arrow_payload`; producer `src/quant_dca/corporate_actions/economics.py:59–95` (`SplitAdjustedFeaturePrice`).

Task7 outputs tuple-valued `applied_action_ids` and `input_sources`. The natural existing serialization pattern, `pd.DataFrame(asdict(row) for row in rows)`, converts these through Arrow into list values. `_json_value` supports scalars only and raises. The same representation is needed on read-back for logical hash verification. Even an empty applied-action tuple is a list scalar after conversion.

**Reproduced scenario:** produce one valid split-adjusted feature record with no actions, convert it using `asdict`, and call `snapshot_hash`. Output: **`TypeError: Unsupported snapshot value type: list`**. `write_snapshot` reaches the same unsupported-value path after valid PIT/lineage checks. The macro-only Task10 fixture contains none of these compound provenance fields.

**Required fix:** provide deterministic typed encoding and read-back hashing for the nested structures required by the Foundation's own records, or supply an explicit lossless normalized persistence adapter for Task7 outputs. Preserve action/source attribution rather than dropping columns to make hashing work. Test one real Task7 feature result through Task9 write, metadata/lineage verification and deterministic repeat publication, including an applied split.

**Basis:** Task7 auditable feature provenance, Task9 immutable feature snapshots and design §24 lineage. This is an actual producer/consumer compatibility failure, not a request for arbitrary-object serialization.

### F6 — P1: feature-adjusted prices are accepted as executable raw prices

**Locations:** `src/quant_dca/corporate_actions/economics.py:241–245` and lines 286–293; also raw input assumptions at lines 354–378. The feature record explicitly labels itself `price_basis='split_adjusted_feature'` at line 95.

`economic_acquisition_cost` only reads the bar's attributes and never checks its price basis or canonical raw-bar identity. `SplitAdjustedFeaturePrice` deliberately has the same price/session attributes, so the actual output of the feature API is accepted directly as a fill. Type annotations do not enforce this at runtime. The adjustment function also accepts already adjusted input and applies splits again.

**Reproduced scenario:** January 2 baseline raw price 100 HUF and January 3 raw fill 100; a January 6 two-for-one split is used to build the January 3 feature view as of January 10. Passing that actual feature object as the January 3 fill to `economic_acquisition_cost` succeeds and returns **50 HUF**, although the actual historical execution cost was 100. The split is outside the baseline-to-fill window, so action processing does not repair the error. A second probe feeding an adjusted canonical-shaped bar into feature adjustment returned 25 instead of 50.

**Required fix:** enforce unadjusted canonical execution bars at the economics boundary and raw input at the split-adjustment boundary. Reject feature-only records and non-raw bases explicitly, including the baseline record where appropriate. Keep separate types, but back that distinction with runtime checks or an equally strong validated adapter. Add a regression that directly passes the actual feature producer's result into the execution consumer and proves rejection.

**Basis:** design §10 feature/execution separation and the review brief's explicit raw-versus-feature-price boundary. This can manufacture a false timing edge without any future timestamp violation.

## What remains sound or explicitly limited

- Provider transport enforces both observation and realtime request bounds before sending, disables redirects, and rejects incomplete FRED pagination rather than admitting partial history. Availability/quality policy remains caller-reviewed; SEC is explicitly unavailable. No new provider capability is inferred here.
- The shared feature guard rejects future feature/input availability and inconsistent feature cutoffs. Its successful checks cannot repair incorrect version choice or wrongly assigned exchange times.
- Calendar lookup uses actual schedules with strict subsequent opens. FX uses evidenced fixing/availability bounds, explicit age policy and same-day daily-open constraints; its local explicit revision fix is present.
- Corporate-action economics retains native and HUF cashflow receipts and includes relevant input knowledge/payment times in label maturity. Unsupported relevant merger/spinoff handling fails explicitly; complete terminal economics remains outside current evidenced readiness.
- Snapshot identity binds logical data, layer, cutoff, schema, source hashes and lineage; verified reads check the Parquet/sidecar pair. Feature/target classification checks and the prior Task9 integrity repairs are present. F5 is a distinct supported-record compatibility defect.
- Task10 accurately distinguishes synthetic fixture evidence from actual data admission and reports all eleven domains with actual tiers unassigned. Its software-path claims must remain scoped until the whole-branch findings are resolved.

## Combined acceptance target

One fix wave should resolve F1–F6 together, because revision policy, canonical admission, action selection and persistence schemas share boundaries. The scoped re-review should inspect those changes and their producer-to-consumer regressions. Existing mandatory Foundation tests must then remain green, and deterministic CLI evidence should be refreshed only where outputs/schema change or the final gate requires it. Do not substitute another successful macro fixture run for the action/price/universe scenarios above.

Neither this review nor eventual software approval authorizes actual-data admission, provider purchases, retrospective holdout use, or model research using current raw artifacts. Those limitations are correctly documented and are not the reason for the software FAIL verdict.
