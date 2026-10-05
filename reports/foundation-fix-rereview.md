# Foundation combined fix wave — scoped independent re-review

Date: 2026-09-16. Reviewed implementation: `8e6097a..0c3a2c9`, using the supplied `foundation-fix-review.diff` and corresponding source. Intervening documentation/raw-audit changes are outside this review. This is one scoped re-review of F1–F6 and material regressions introduced by their fixes, not a new whole-project review.

## Verdict

- **Spec compliance: FAIL.** The action-selection repair introduces a material label-maturity dependency on unrelated future economic events, incompatible with usable horizon-specific expanding walk-forward training.
- **Code quality: FAIL.** The label producer's dependency scope does not compose with full security action history and the training-cutoff consumer contract.
- **Foundation software phase gate: NOT PASSED.** The mandatory whole-phase acceptance gate remains open; Subproject 2 is not approved by this review.
- **Real-data readiness: independently NOT READY.** RAW_ONLY evidence, incomplete Task0, unassigned actual quality tiers and missing panel admission are not reasons for this software verdict and are not changed here.

## Scope and evidence

Read the original whole review, combined fix report, `reports/foundation-fix-tests.txt`, supplied diff, changed implementation and focused regressions. Applied frozen design §§9–10 and §15.4 with the controlling evaluation amendment: development history only through 2023, no retrospective-holdout use, historical features require actual availability, raw execution stays separate from feature adjustment, and calendar/economic causality remains binding.

The reported 22 focused / 388 full passing tests and two byte-identical fixture CLI outputs with unchanged hashes are accepted as scoped evidence, not independently rerun. No test suite, CLI build, network request, market-data access, holdout experiment, implementation mutation or subagent was used. One short in-memory offline probe tested a concrete new action-history dependency risk using existing fixture constructors and production economics/calendar APIs; all supplied economic dates were 2020–2023. This report is the only intentional file write.

## Original findings

| Finding | Verdict | Basis |
| --- | --- | --- |
| F1 — delayed revisions resurrect superseded facts | ADDRESSED | Shared selection gates knowledge by availability, then orders explicit revision/publication or date-level vintage chronology. Universe listing/membership consumers delegate to it. Unknown/mixed clocks, conflicting ties and overlapping FRED intervals fail closed. |
| F2 — action revisions counted as multiple events | NOT ADDRESSED | Duplicate-event arithmetic is repaired, but the complete requested action-version/maturity contract is not acceptable: the repair now makes unrelated later action identities dependencies of every earlier label. See R1. This is not a claim that duplicate splits still multiply. |
| F3 — legitimate price vintages destroyed at admission | ADDRESSED | Explicitly ordered, distinct revision identities survive admission; mapping revisions are resolved before interval relevance. As-of validation selects and rechecks a coherent price panel, and feature production enforces that stage with discontinuity evidence. |
| F4 — bars bypass actual exchange calendar | ADDRESSED | Canonical admission and both feature/execution entry boundaries check exact supported-exchange session clocks against the schedule. Non-sessions and mismatches reject rather than silently repair timestamps. |
| F5 — feature provenance cannot be snapshotted | ADDRESSED | Recursive sequence encoding covers actual action/source and nested selected-version fields; list child-name normalization preserves element type/nullability across Arrow/Parquet. Producer-to-persistence regression includes empty/action-bearing feature rows and verified repeat identity. |
| F6 — adjusted features accepted as raw fills | ADDRESSED | Runtime checks require actual OHLCV instances with unadjusted basis at fill, baseline and feature-adjustment boundaries. Actual feature output and adjusted canonical-shaped bars are explicitly rejected. |

### F1 detail

`point_in_time/asof.py` separates eligibility from revision order, deduplicates exact repeats and identifies canonical action/session/universe/security groups. Opaque IDs are not ordering clocks. Original publication timestamps can order originals against revisions; FRED vintage chronology remains date-level without invented publication times. `universe/membership.py` now uses that selector and fails eligibility closed on ambiguity, so delayed open-ended rows cannot supersede a known delisting. Focused tests cover delayed originals/revisions, cutoffs, conflicts, FRED normalized intervals and both listing/membership delisting paths. No material new F1 breakage identified in this scoped review.

### F2 detail

`corporate_actions/economics.py:_selected_actions` groups by security/action identity, resolves one revision and fails unresolved chronology closed. Both feature adjustment and economic accumulation use it before date relevance. Exact repeats do not multiply events; corrected split ratios/dividend amounts and dates are handled in the new regressions. Features remain cutoff-gated, including provenance for a known correction that removes an adjustment. However, label selection and maturity indiscriminately include every selected action identity for the security, not only causally relevant identities and their necessary correction evidence. R1 is introduced by this repair and prevents accepting F2's complete boundary contract.

### F3 detail

`canonical/validate.py:239–353` distinguishes revision admission from selected-panel validation. Distinct IDs with unambiguous clocks are retained; conflicting duplicates remain quarantined. Admission anchors use knowledge cutoffs, while the as-of panel is screened again to catch later anchor corrections. Mapping selection uses the requested as-of cutoff when present and selects a revision before checking its active interval. The feature producer forwards the same auditable discontinuity evidence. Tests exercise preserved price versions, corrected/invalid mappings, later price-anchor revisions and accepted discontinuity evidence. This resolves the original admission/PIT composition defect within the documented two-stage contract.

### F4 detail

`calendars/service.py:assert_session_clock` requires a real scheduled session and exact opening/closing instants. `_validate_bar_metadata` and `_raw_bar` enforce it on canonical and direct consumer paths. The supplied regressions include US/EU holidays, weekend rejection, US/EU DST and early closes through canonical, feature and execution paths. Correcting the two legacy fixtures to actual clocks/sessions is legitimate and does not weaken assertions. Security-specific halts remain an explicitly separate limitation.

### F5 detail

`storage/snapshots.py:_json_value` recursively handles lists/tuples; `_logical_type` normalizes only sequence child-field naming while binding nested type/nullability. This is the relevant representation generated by `asdict(SplitAdjustedFeaturePrice)` through Arrow. The focused test writes actual no-action/applied-split outputs, verifies metadata and lineage, checks retained attribution and publishes twice with the same identity. Generic arbitrary-object support is neither claimed nor required. Existing scalar hash behavior is consistent with the unchanged CLI evidence.

### F6 detail

`corporate_actions/economics.py:_raw_bar` rejects a feature record regardless of its similar attributes and rejects an OHLCV carrying any non-unadjusted basis. It runs for both baseline and fill and before feature readjustment. The regression directly supplies the real feature producer's output at each forbidden boundary. This closes the original false execution-price edge.

## R1 — P1: unrelated future action identities make historical labels unavailable

**Introduced locations:** `src/quant_dca/corporate_actions/economics.py:287–292` selects across the complete supplied security history; `:313–319` adds the availability of **all** selected actions to `required_knowledge`; `:350–361` publishes that maximum as label maturity and all identities as provenance. The policy is expressly documented in the fix report, so this is an evaluated producer/consumer policy defect, not a documentation discrepancy.

Selecting a corrected version before deciding whether its event affects a delay window is necessary. It does **not** imply that a distinct dividend or split years after the window is needed to know an already completed target. With full history, all labels for a security inherit at least its latest action availability. A dividend-paying security can therefore lose years of otherwise mature 5D/20D/60D training rows at earlier refits. This fails closed rather than leaking a future feature, but fail-closed loss of the intended training population is material software breakage.

### Offline reproduction

Used `tests/foundation/test_fix_wave.py` constructors via `runpy`; generated 16 separate quarterly dividend identities for 2020–2023. Each has cash amount 1 HUF, ex-date on the first XNYS session on/after the sixth day of January/April/July/October, availability/revision two days before ex-date and payment ten days after it. There are no corrections or duplicate identities in this probe. Raw baseline is 2020-01-02 at 100 HUF; fills at the actual fifth, twentieth and sixtieth following exchange sessions are also 100 HUF. HUF avoids any FX dependency. Compared full supplied history with the economically intersecting action subset; the subset is a diagnostic control, not a proposed unsafe caller-side revision filter.

| Horizon | Fill session | Cost with either input set | Window-only maturity | Full-history maturity | Eligible at 2021-01-01 with full history? |
| --- | --- | --- | --- | --- | --- |
| 5 sessions | 2020-01-09 | 101 HUF | 2020-01-16 00:00 UTC | 2023-10-04 00:00 UTC | No |
| 20 sessions | 2020-01-31 | 101 HUF | 2020-01-31 21:01 UTC | 2023-10-04 00:00 UTC | No |
| 60 sessions | 2020-03-30 | 101 HUF | 2020-03-30 20:01 UTC | 2023-10-04 00:00 UTC | No |

Every full-history result reports 16 selected identities although only the January 2020 dividend affects any of these windows. The same loss occurs at 2022 and early-2023 training cutoffs. The value/cashflows are unchanged; only the new blanket dependency postpones maturity by years. With a development history ending in 2023, this systematically defeats horizon-specific historical usability for securities with later actions. No 2024+ data are needed to demonstrate it.

**Why existing evidence misses it:** the F2 tests contain one logical action identity with revisions and correctly require a removal correction's availability. They do not add independent later identities and check mature historical labels at earlier training cutoffs. The macro fixture does not exercise this contract.

**Required acceptance condition:** define and enforce a causal label dependency policy that retains revision resolution before relevance, retains availability/provenance for corrections that add/remove relevant events, and does not attach wholly unrelated later action identities to historical labels. If the intended alternative is rebuilding explicitly bounded action vintages per training cutoff, the producer must expose/enforce that contract and the consuming path must actually use it; a general statement that later corrections require rebuilding is insufficient. Do not fix this by filtering raw revisions by current ex-date before resolving identity, or by dropping necessary maturity evidence. Add full-history, unrelated-later-action invariance and 5/20/60-session training-cutoff usability regressions alongside the existing removed-event correction tests.

No additional material finding is raised outside this fix diff. The five accepted findings remain accepted; R1/F2 prevents the combined gate from passing.
