# SDD ledger — plan: docs/superpowers/plans/2026-09-11-quant-dca-data-pit-foundation.md

## Scope
User mandates development only. No lockbox execution, no production handoff. Source docs retained unchanged at b7e994a. Fresh dedicated repository on research/development-v1; no existing checkout to isolate. Dependencies installed successfully; use python -m pytest.

## Preflight review
| Task | Internal consistency | Dependencies / consumer checks |
|---|---|---|
| 0 | Coverage and actual access must be distinguished from documented capability. | Adapter selection feeds Task 3; no verified complete dataset supplied. |
| 1 | Example tests alone do not prove immutability or naive-date rejection. | Typed contracts feed Tasks 2-9; require actual mutation/naive rejection tests. |
| 2 | Example includes 2026 calendar dates, not financial data. | Calendar supplies true eligible session indices to Tasks 6/8 and later targets. |
| 3 | CSV example lacks exchange/currency. | Must use explicit provider metadata; no guessed listing metadata in real ingestion. |
| 4 | Extreme discontinuities versus genuine crisis outliers require distinction. | Quarantine unresolved suspected errors with reason; preserve raw and audit exclusions. |
| 5 | latest_known example single series/period only. | Partition by series/entity/period before vintage selection; ambiguous mixed groups rejected. |
| 6 | Minimal example omits full eligibility fields. | Spec requires all filters; incomplete data cannot silently pass research eligibility. |
| 7 | Scalar dividend test not complete split/FX implementation. | Shared economic cost used later by targets and simulator; entitlement and split units required. |
| 8 | Quote example safe but no stale/currency coverage policy. | Explicit missing quote failure; never later fixing. |
| 9 | Hash example insufficient to prove immutability. | Layer isolation, canonical sort, timezone metadata and source lineage need tests. |
| 10 | Fixture success alone not real-data readiness. | Upstream data audit must retain unresolved gaps; model research cannot consume fixtures as evidence. |

Ruling: Preserve frozen design and treat simplified plan examples as minimum smoke tests, never as permission to omit mandatory fields or filters — authoritative spec requires strict PIT truth — cost if wrong: additional tests/contracts may require later interface changes.
Ruling: Lockbox implementation/execution and final configuration freeze are deferred to explicit human review; only development proposal is authorized — user's stop point overrides Subproject 4 execution instructions — cost if wrong: later separate lockbox session required.

## Activity
- Task 0 research dispatched to provider_audit; baseline commit b7e994a.
- Local setup: Python 3.12.14; required packages installed successfully. No model experiments run.
- Direct bounded Stooq request d1=20230103,d2=20230106 returned HTTP 404. No payload acquired.

- Task 0: partial checkpoint fad27d3, BLOCKED. 11-domain documentation audit; no full provider freeze; independent reviewer audit_review dispatched.
- Incident: provider documentation exposed lockbox-dated response examples to provider_audit. All external research stopped. Cannot certify untouched lockbox; do not restart research without user review.
- Remaining Tasks 1-10: NOT STARTED. Downstream phases: NOT STARTED. No investment experiments.

- Task 0 checkpoint review: scope correction committed 1b461d8; independent re-review all findings addressed. Partial handoff approved as accurate; Task 0 NOT complete.
- Model/feature/policy experiment ledger remains empty. No further financial research authorized by assumption following incident.

## Resume authorization — user protocol amendment
User accepted incident and explicitly directed continuation from Task 1. docs/evaluation-protocol-amendment-2026-09-11.md is controlling. Prior stop is resolved. Historical holdout is retrospective, not pristine. No holdout evaluation now. Provider gaps remain research limitations, not a stop to software implementation.

- Task 1 complete: f77de14; RED missing module recorded; GREEN 98 tests; independent review_task1 spec PASS/quality PASS, no findings.
- Task 2 dispatched foundation_task2 from f77de14; exchange calendar boundary tests and implementation.
- User supplied FRED credential for bounded validation; credential excluded from reports, source, git and saved deliverables.

- Task 2 complete d6d219d: 60 calendar tests, 158 total; review_task2 spec/quality PASS, no findings.
- 2026-09-13 resume: Task3 previous dispatch produced no files before session interruption. Redispatched task3_ingestion from 424d201; only current task3 agent may write provider files. Runtime dependencies reinstalled, no code work lost.

- Task 3 complete: 91fba11 + 635b549; 27 provider tests passed after fixing missing price-basis inference and timezone-dependent vintage validation. Independent review_task3: both findings addressed; spec/quality PASS. SEC remains an explicitly unavailable integration, not a functioning data source.
- Task 4 resumed after interruption from 635b549: prior draft tests retained, canonical implementation absent. Fresh task4_validation assigned; runtime dependencies being restored. No model experiments or holdout evaluations.

- Raw US macro audit 515d454: bounded 2010-01-01..2023-12-31 observation AND vintage intervals; CPIAUCSL/CPILFESL/UNRATE/FEDFUNDS fetched and structurally validated, not normalized/admitted. DGS10/DGS2 failed before persistence, exact cause not retained. Quality remains unassigned. No model experiment.
Ruling: Task10 wording suggesting B/C assignment for a missing PIT source is superseded by explicit user instruction: missing/unverified data remains unavailable with no tier; only actual evidenced observations can receive A/B/C — prevents fake evidence — cost if wrong: smaller admissible prototype panel.

- Task4 implementation92b4529: targeted43/full228 tests pass; independent review_task4 dispatched, gate pending. RED/GREEN evidence retained.

- Task4 review1 FAIL: quarantined-row anchor contamination (P1), ungated future verification evidence (P1), missing identity admission (P2). Fix round1 dispatched to original implementer.
Ruling: Discontinuity evidence must be known by the canonical bar available_at; later verification requires a separately versioned bar with later availability — ties admission to the same downstream PIT guard without adding an independent cutoff — cost if wrong: more historical bars remain quarantined until corrected versions are supplied.

- Task4 fix round1:6994d7e, all3 findings addressed, no new material breakage; review_task4 spec PASS/quality PASS. 48targeted/233full tests pass. Task4 complete (92b4529 +6994d7e).
- Task5 dispatch from a6c0be8: PIT as-of selection and hard leakage guard.

- Task5 complete7bc30d5:28targeted/261full tests passed; review_task5 spec/quality PASS without findings.
- Task6 dispatched task6_universe from7bc30d5; fail-closed historical eligibility including actual session history, configured liquidity and published fundamentals.

- 2026-09-14 runtime recovery: Task6 previous agent did not survive interruption; no source files existed at resume. Restored dependencies and resumed from7bc30d5.
- Task6 implementationce57b7b:18targeted/279full tests pass; independent review_task6 pending.
- SEC audit93654ff: two bounded quarterly indexes and one original2010accession retrieved, acceptance header observed but dissemination/timezone and canonical facts remain unverified. No quality tier or research admission granted.

- Task6 review1 FAIL: configurable minimum below120, history reset by membership start, incomplete same-day session counted, unsupported calendar evidence raised rather than excluding. Fix round1 dispatched to original implementer. No next task until re-review passes.

- Task6 fixround1 439e841: mandatory120floor, listing-history independence, actual sessionclose and missing calendar handling fixed. 87calendar+universe/288full tests pass; scoped re-review pending.

- Task6 complete ce57b7b+439e841: all4reviewfindings addressed, spec/qualityPASS;288full tests.
- Task7 dispatched task7_economics from439e841: corporate-action economics, per-cashflowFX and PIT feature adjustment.

- Recovery after environment_offline: repository reachable again at5f4f129, clean worktree, no Task7 draft survived. Resumed Task7 with task7_economics_resume; restored transient Python dependencies. Task1–6 review gates remain complete. No new market-data requests or holdout evaluation during recovery.

- Task7 implementation4968aeb:16focused/304full tests passed; review_task7 dispatched. Corporate-action economics and immutable split-adjusted feature views implemented; review gate pending, not yet a completed task.

- Task7 review1 FAIL: maturity omitted input availability; feature views missing canonical availability/provenance; native cashflow diagnostics discarded; ex-date comparison depends on caller timezone. Fixround1 dispatched to original implementer.
Ruling: Extend the Task7/8 FX interface with an evidenced quote/resolution in addition to the planned scalar rate API — cashflow availability and lineage cannot be reconstructed from a float alone — cost if wrong: a small extra interface and receipt type to maintain, without changing FX selection methodology.

- 2026-09-15 recovery: retained Task7 fix commit9b74b00; previous reviewer did not survive the session. Re-dispatched scoped fixround1 review as task7_rereview, without assuming approval. Restored Python dependencies and reproduced `python -m pytest -q`:309 passed in1.49s. No new market-data requests or holdout evaluation.

- Task7 fixround1 complete:4968aeb..9b74b00; all4 findings ADDRESSED, no new material breakage, independent task7_rereview spec PASS/quality PASS. Task7 complete;20 focused/309 full tests. Proceed to Task8 evidenced PIT FX service.

- Task8 implementation6ac1607:22 focused/331 full tests passed; canonical evidenced direct-pair FX resolution, explicit age policy, daily-open constraints and Task7 integration. Independent review_task8 dispatched; task gate pending.

- Task8 review1 FAIL: delayed older revision outranks newer known revision; arbitrary quote_type bypasses same-day daily-open restriction. Fixround1 assigned to original task8_fx implementer with RED regressions. No Task9 dispatch until scoped re-review passes.
Ruling: FX revision selection uses explicit revision chronology within the latest eligible fixing; availability remains a hard eligibility bound, not a substitute for revision ordering — delayed delivery does not make a superseded revision current — cost if wrong: ambiguous timestamp-poor rows must remain unavailable rather than inferred.
- Foundation broad-review follow-up: inspect non-FX uses of Task5 availability-first selection for delayed delivery of superseded revisions. FX is being fixed locally; this cross-task question is not silently declared resolved by the FX fix.

- Task8 fixround1 f428350: both findings ADDRESSED, no new material breakage; review_task8 spec PASS/quality PASS. Task8 complete,29 focused/49 Task7+8/338 full tests. Task9 immutable snapshots and lineage is next.

- Task9 prior implementer interrupted by workspace credit exhaustion after writing draft source/tests/reports; no Task9 commit or independent review was produced. Retained report records17 focused/355 foundation tests, not yet independently reviewed. User directed continuation; task9_resume assigned the existing draft fromaf84366 for final verification and scopedcommit. Task9 remains incomplete.

- Task9 implementation5df1984 committed after dependency restoration and fresh17 focused/355 foundation tests. Independent review_task9 dispatched with scoped diff; gate pending, not yet complete.

- Task9 review1 FAIL: feature-shaped rows bypass PIT checks when mislabeled targets; lineage lookup accepts orphaned/tampered snapshot pairs; table-only identity does not bind schema version and lineage. Fixround1 assigned to resumed implementer.
Ruling: Keep standalone snapshot_hash as the logical table digest, but bind complete snapshot identity to its explicit metadata/provenance as well as data — reproducibility needs the transformation and source version, not merely equal numeric cells — cost if wrong: an additional digest/identity distinction and revised internal snapshot paths.

- Task9 fixround1 070e941: all3 findings ADDRESSED, no new material breakage; review_task9 spec PASS/quality PASS. Task9 complete,26 focused/364 foundation tests. Proceed to Task10 fixture build and audit; real-data admission remains unresolved.

- Task10 implementationa07f9a6:2 focused/366 full tests; exact CLI twice emitted identical full snapshot identitye5f0c42009db82bb3f217d44a451c1ad44960c62e97eaabeb28c4de3ef5f0972. Eleven-domain quality map and audit written; independent review_task10 pending. Actualdata tiers remain unassigned and Task0 unresolved. No final Foundation or real-data approval claimed.

- Task10 completea07f9a6: resumed independent review_task10_resume spec PASS/quality PASS, no material findings. All Tasks1–10 individually reviewed. Foundation whole-branch review follows before Subproject2; Task0 real-source qualification remains incomplete.

- Foundation whole-review FAIL (reports/foundation-whole-review.md): F1 superseded revisions/universe resurrection; F2 repeated corporate-action vintages; F3 legitimate price vintages quarantined; F4 calendar admission bypass; F5 Task7 provenance cannot persist; F6 adjusted feature prices accepted for execution. Six reproduced cross-component findings require one combined fix wave and scoped re-review. Subproject2 remains unstarted.
Ruling: Canonical price admission must retain legitimate revision history while as-of selection resolves session-level truth; duplicate checks and discontinuity anchors must respect that separation — rejecting every corrected session loses PIT history — cost if wrong: stricter ambiguity quarantine and a documented extra selection boundary.

- Combined-fix recovery: previous agent left tests/foundation/test_fix_wave.py only, without source changes or a fix commit/report. foundation_fix_resume assigned existing draft from27b11b8; dependencies need restoration. No finding is yet closed.
- Bounded FRED DGS10/DGS2 retries both returned HTTP400; no rows persisted. Subsequent bounded error-body diagnostic was interrupted with no retained result. Details in reports/fred-yield-retry-2026-09-15.md; no new data admission or inferred cause.

- Follow-up diagnostic identified DGS10's3444 vintage dates exceeding the JSON2000 limit. Four smaller pre-bounded requests succeeded for DGS10/DGS2, persisted only after response-bound/completeness checks. Each series3501 distinct nonmissing observation dates2010-01-04..2023-12-28; overlapping raw chunks remain RAW_ONLY/unassigned. Inventory/audit supplemented; no model experiment.
Ruling: Split only the allowed realtime request interval at the observed provider volume limit — narrow data-access substitution, not methodology change — cost if wrong: clipped/overlapping interval boundaries could be misread as revisions, so no normalization/admission until a reviewed stitching policy exists.

- 2026-09-16 bounded yield audit review: yield_audit_resume independently checked all4 payload/manifest pairs, bound/completeness checks, counts, ranges and hashes; evidence/spec PASS and report-quality PASS. This approves the accuracy of the access audit only, not data admission or provider freeze.
- Combined-fix recovery on2026-09-16 preserved existing source edits and tests; foundation_finish_fixes recorded prior RED evidence and restored dependencies. Fresh focused22/full388 tests passed; final CLI checks and fix commit pending, software gate still not passed.

- Combined fix wave committed0c3a2c9:22 focused/388 full tests, byte-identical two CLI runs with prior hashes; compile/diff checks clean. Independent foundation_fix_rereview is checking F1–F6 and new fix-diff breakage. No phase approval follows merely from green tests.

- 2026-09-16 scoped final re-review complete: reports/foundation-fix-rereview.md; spec FAIL / quality FAIL. F1/F3/F4/F5/F6 ADDRESSED. F2 duplicate arithmetic repaired, but new R1 (P1) makes unrelated future actions dependencies of historical labels. Offline 2020 5/20/60-session probe with full 2020–2023 action history confirms all three maturities move to October2023 despite unchanged economics. No network request or holdout use in the probe. Foundation phase gate remains NOT PASSED; Subproject2 has not started.
Ruling: Accept the scoped reviewer’s R1 as real and load-bearing; do not waive it as conservative maturity or equate green tests with phase acceptance. The smallest required repair is a causal event-identity dependency boundary preserving revision-before-relevance and removal-correction evidence, tested against unrelated later identities and historical training cutoffs — without it the specified expanding training population is materially corrupted — cost if wrong: additional bounded implementation/review effort before research can begin.
- The SDD final-review allowance (one combined fix wave, one scoped re-review) is exhausted. No second wave was dispatched. Surface the residual and request authorization for a narrowly scoped extra F2/R1 repair/review cycle; do not advance a failing Foundation gate. This is a workflow review decision, not a claim of impossible implementation or project cancellation. Actual data qualification remains separately incomplete.

- User explicitly answered “Igen” to the extra targeted F2/R1 repair and independent review. Authorized extension begins from6fa1901; brief reports/foundation-r1-authorized-brief.md. No waiver of failed Foundation gate or expansion into holdout/production. Prior review findings remain preserved.

- Authorized repair17bea46:6 RED maturity regressions,48 covering tests GREEN,394 full tests GREEN. Causal dependency set includes an identity when any supplied revision intersects the delay window; only its selected revision contributes economics and required knowledge. Unrelated identities no longer attach maturity/provenance; corrections removing an event remain evidenced. Full report reports/foundation-r1-authorized-fix.md. Independent foundation_r1_review dispatched; gate decision pending.
- Data-admission limitation retained: latest-only action snapshots cannot establish omitted historical event relevance. The repaired producer requires relevant version history; this software correction grants no actual provider a tier or research admission.

- Authorized F2/R1 independent review complete: foundation_r1_review, reports/foundation-r1-authorized-review.md. R1 ADDRESSED, spec PASS, quality PASS, no material new breakage. Controller fresh verification: `python -m pytest -q`394 passed in1.93s; `git diff --check` clean.
- Foundation software/PIT phase gate PASSED: individual Tasks1–10 accepted; prior scoped review acceptedF1/F3/F4/F5/F6; authorized residual review now closesF2/R1. No finding was waived. Real-data readiness remains NOT READY, Task0 incomplete, no actual provider quality/admission inferred, no OOS or holdout run. Next implementation task is Features/Targets/Regimes Task1; it has not started at this checkpoint.

- User accepted Foundation and explicitly authorized Features/Targets/Regimes Tasks1–10, separate data-audit stream, four mandatory real-research gates, and a pause afterTask7 before regime modelling. Controlling instruction recorded docs/features-stage-execution-amendment.md.
- b8135c8 reconciles readiness-manifest: Foundation PASS, real-data audit OPEN_INCOMPLETE, feature/target/regime NOT_YET_COMPLETE, financial/OOS runs0, retrospective holdout NOT_RUN. Historical incident/BLOCKED reports untouched.
- Features preflight recorded reports/features-plan-preflight.md. SDD helper task-brief could not invoke its non-executable nested script; extracted exact task sections to plan-scoped scratch briefs instead, without changing skill files. Task1 initially dispatched but agent lost before any draft/commit; resumed as features_task1_resume fromb8135c8. Separate development_data_audit report-only agent has no code ownership.

- Separate audit522b1fa: official MNB WSDL established precise SOAP endpoint/action after initial HTTPS404; one pre-bounded2023-12-29EUR/USD request succeeded with redirects disabled. One479-byte rawresponse retained/hashed, qualityNULL, RAW_ONLY. Inventories updated, no execution-time FX admission. Remaining real panel gaps documented reports/development-panel-audit-followup.md. Controller verified artifact hash/bounds and CSV structures7x21/11x24.
- Features Task1 implementation5d8d3fc:80outputs/69base signals plus13reservedregime slots;6focused/400full tests reported (focused rerun after allocation changes). Independent features_task1_review specFAIL/qualityFAIL: missing required universe percentile; ambiguous split/currency turnover semantics; identity synonym/component bypasses. Fixround1 assigned original implementer, noTask2yet.
Ruling: Define dollar turnover as canonical raw close times verified original-unit volume converted to USD using only FX known at the historical EOD; require explicit currency/FX and volume-basis metadata — a joint-region raw-turnover feature otherwise mixes currencies and adjustment units — cost if wrong: more missing liquidity signals until volume basis and timely FX are audited. Numeric split/FX invariance belongs to Task2; Task1 validates this metadata contract without creating an unplanned calculator.

- Features Task1 fixround1 resumed after workspace-credit interruption, preserving draft and RED11failures. Declared testdependencies restored (package installation only, no marketdata). Commit73c3daf:21focused/415fullPASS. Independent registry_fix_review:all3findingsADDRESSED, specPASS/qualityPASS, no newmaterialbreakage. Task1 complete5d8d3fc+73c3daf. Registry81outputs plus13reservedregime slots=max94; actualproviderquality unchanged. NextTask2 carries numerical split/FX invariance.

- Task2 original features_task2 agent interrupted by credit exhaustion; draft preserved. Recovery checkpoint retained three explicit unreviewed WIPfiles over0249889. Existing gitbundle head was verified0249889 after bundle recreation hit an existing lock; no lock/deletion or unrelated data mutation. Resumed as features_task2_resume.
- Task2 implementation3e619c7:22outputs,16focused/431fulltests. Resumed draft12baseline tests; newREDcaught future-volume-provenance validation beforecutoff filtering, fixedbeforeGREEN. Historicalcurrency andverifiedvolume required, split/dividendtotalreturn chain, actualsessiongaps preserved. Report reports/features-task2-implementation.md. Independent features_task2_review pending; Task2notyetcomplete.

- Task2 independentreviewFAIL: P1 explicit futureactionannouncement accepted with contradictory earlieravailability; P2 missingcanonicalvolume aborts price-onlyfeature computation even withindependentauditedunits. All22formulas/lookbacks otherwiseaccepted. Fixround1 assignedfeatures_task2_resume; strictcanonicalvalidation mustremainstrict, explicitfeaturedependency handling mustnotfabricatevolume or bypassOHLC/calendar/discontinuitychecks. NoTask3untilreviewPASS.

- Task2 fixround1 557a84e:22focused/118covering/437fullPASS. Independent features_task2_fix_review: P1/P2ADDRESSED, specPASS/qualityPASS, no newmaterialbreakage. Task2 complete3e619c7+557a84e. Strictcanonicaldefault preserved; opt-in priceview documented. Task3 next.

- 2026-09-17 Task3 implementation 8415bb8: 9 focused / 103 covering / 446 full tests passed. Literal historical ranks, future mutation invariance, historical classification and benchmark identity, and PIT input clocks covered. Independent features_task3_review pending; Task3 is not yet accepted, Task4 not started. No financial/OOS research or holdout run.

- Task3 independent review FAIL: historical cutoff derived from prediction rather than supplied return observation date; future-available direct operands silently skipped. Fix round 1/5 assigned to original implementer. Direct mapping operands are already selected inputs and must hard-fail; future-unavailable candidate vintages in cross-sectional/classification histories remain filtered before selection. Historical population must match the aligned return observation EOD, including stale observations evaluated after a later close. Review report preserved; Task4 remains pending.

- Task3 correction 607c42e: 5 RED regressions, 14 focused / 451 full GREEN. Independent features_task3_fix_review: both findings ADDRESSED, spec PASS / quality PASS, no new material breakage. Task3 complete; Task4 fundamentals/valuation dispatched. Financial/OOS runs remain 0; data admission still incomplete.

- MNB publication-policy audit 3452995 corrected by 047d593: broad documentation searches exposed prohibited 2026 market observations in expanded live-page results twice. No financial use or admission; disclosed to user. Detailed access/cause/control record: reports/mnb-search-access-incident-2026-09-17.md. No further audit network requests in this work stage. Broad provider searches with automatic live-page expansion disallowed; exact static documentation and pre-bounded provider adapters remain distinct. Task4 software work continues. Historical incident reports preserved.

- Task4 implementation 755b302: 12 fundamental and 10 valuation outputs, 11 focused / 462 full tests passed. Independent features_task4_review pending; not yet accepted. Task5 not started. Implementation used synthetic fixtures only, separate from the MNB audit and its access incident.

- Task4 independent review FAIL: embedded consensus bypasses evidence admission; cross-exchange eligible sector peers are omitted; unknown fundamental sector is treated as nonfinancial. All three accepted, fix round1/5 assigned original implementer. Reviewer also flags upstream trailing-period normalization as unverified; require explicit input semantics before real admission, not inferred quarterly/annual comparability. No methodology or feature-list change authorized. Task5 remains pending.

- Task4 fixround1 e789525: 6 RED regressions, 17 focused / 468 full GREEN. Independent features_task4_fix_review: all3findingsADDRESSED, specPASS/qualityPASS, no newmaterialfindings; explicitTTM declaration accepted. Task4 complete755b302+e789525. Task5 macro/events dispatched. Remaining market/structural producer coverage recorded as mandatory Task10 integration follow-up in preflight9f30830.

- Task5 implementation9342d16: exactly13macro/6eventoutputs,9focused/477fullPASS. Independent features_task5_review pending; Task6notstarted. No network/data/modelresearch in implementation.

- Task5 independentreviewFAIL: eventdistance timezone-representation dependence; omitted cancellation/relevance-revision provenance; missing security effective-interval check. ThreeP2 accepted, fixround1/5 assignedfeatures_task5. Scope causal known eventselection evidence only, no unrelated future-event dependencies. Task6 pending.

- Task5 correction5ab58af:13focused/481fullPASS. Scoped review interrupted by workspace-credit error, resumed on user's continuation without repeating implementation. reports/features-task5-fix-review.md: all3P2RESOLVED, specPASS/qualityPASS, no newfindings. Task5 complete9342d16+5ab58af. Task6 normalization/imputation dispatched; no financialresearch or holdout run.

- Task6 implementationd4d45e9:14focused/495fullPASS; literalrollingmutation, historicalcrosssection, typedfold/trainonlystatistics, structuralmissing andidentity/targetboundaries. Independentfeatures_task6_reviewpending; Task7notstarted. No actualmodelresearch.

- Task6 independentreviewFAIL, oneP2: canonicalentity_id accepted as categoricalfeature byFoldImputer. Accepted, fixround1assignedoriginalimplementer, literalcanonicalidentityregression required. Otherreviewedcontracts satisfied; Task7pending.

- Task6 fix4ca82df:2RED regressions,16focused/497fullGREEN. Independentfeatures_task6_fix_review specPASS/qualityPASS,entity_idfindingresolved,nonewmaterialbreakage. Task6complete. Task7isolatedtargetbuilderdispatched; mandatorypauseafteritsreviewbeforeTask8 remains. No financialresearch.

- 2026-09-18 Task7 resumed from retained test draft after user continuation; no completed implementation or review claimed.
Ruling: Number the first eligible post-signal open O0; return horizons exit at O5/O20/O60, while five/twenty-open wait windows contain O0..O4/O19 — explicit executable-session convention for otherwise abbreviated horizon wording, without adding prediction horizons — cost if wrong: target definitions require review before research. Preserve per-horizon maturity and censor reasons; unavailable60D cannot erase completed5D/20D or delay their individual training admission. Aggregate target_end_timestamp is conservative and does not replace per-target admission.

- Task7 implementation2729520:40target/537fulltestsPASS; per-horizon maturity/censor, rawfutureopenlocal/HUFtargets, explicitcoverage, Foundationeconomicreuse, no sharedsourcechanges. Independentfeatures_task7_reviewpending. Task8untouched; nofinancial/OOS/holdoutrun.

- Task7 independentreviewFAIL, HighR1: eager history iterable materialization precedes horizon bounds; synthetic sentinel proves all-censored2024 horizons still consume input. No actualmarketdataused byprobe. Fixround1/5 assignedoriginalimplementer: allcensoredzeroingress, mixedwindowconcreteboundedmaterializedinputcontract rejecting unboundedlazyiteration beforeconsumption; testsrequired. Otherreviewedeconomic/maturity/architecturecontracts pass. Task8notstarted.

- Task7 correction9db34ca:13newRED,53focused/550fullGREEN. Scoped re-review R1ADDRESSED, newR2blocking: blanketbounds reject legitimatepre2010listinginceptionmetadata despitein-windowknowledge. Fixround2/5 assignedoriginalimplementer; separate historicalclassification effective-startmetadata from2010–23marketobservation/publicationbounds. Noactualdata/networkused bysyntheticreviewprobe.

- Task7 correction024634e: pre2010listinginception andcoverage-start reference metadata separated from bounded observations/vintages;59focused/556fullPASS reported. Independentfeatures_task7_fix2_review: R2ADDRESSED, specPASS/qualityPASS, no blocking fix-scope regression. Task7 complete2729520+9db34ca+024634e. Task8 not started; mandatory higher-reasoning pause reached. Financial/OOS research runs remain0 and retrospective holdout remainsNOT_RUN.

- 2026-09-28: User explicitly authorized Task 8 and subsequent Task 9 only after Task 8 independent spec/code-quality PASS and checkpoint. Resume on the established dedicated research/development-v1 checkout; no new worktree or methodology redesign. Baseline verification: 556 tests passed. Task 8 delegated under subagent-driven-development; no market-data access, real-panel fit, financial/OOS experiment or holdout evaluation authorized in this stage.

Ruling: Task 8 uses an a-priori config-driven negative weighted squared prototype-distance and softmax mapping for the five specified interpretable states. These outputs are heuristic memberships, not calibrated financial probabilities or a development-selected/frozen configuration. Fixed reference input transforms are explicitly not empirically estimated z-scores; the abbreviated scalar API retains the plan's names only. Recovery requires stress followed by improvement in the immediately preceding eligible benchmark-session evidence, rather than an arbitrarily chosen prior date. This fills the plan's unspecified score mapping without fitting data or adding registry base signals. Cost if wrong: the candidate may fail later permitted inner-validation usefulness/calibration checks and must not influence policy until validated.

- 2026-10-03 recovery: retained Task 8 test draft and parent status edits, no Task 8 production code/commit had survived or been completed. Restored declared dependencies in a task-local virtual environment; unchanged suite (`--ignore=tests/regimes`) freshly passed 556 tests. Original implementer resumed; 66 expected Task 8 RED failures reported before production implementation. All inputs synthetic, no provider network or financial experiment.

- 2026-10-04 Task 8 complete: implementation `0925763`, 67 focused / 623 full tests PASS; controller full-suite rerun 2026-10-03: 623 passed, compileall and diff check exit 0. Independent `regimes_task8_review`: spec PASS / quality PASS, no blocking findings. Review: reports/features-task8-review.md. Checkpoint precedes Task 9. Financial/OOS runs remain 0; retrospective holdout NOT_RUN.

Ruling: the XLON calendar capability for entity-free aggregate rows does not expand the EU-listed investment universe or select a benchmark. Task 10 must bind each aggregate to its evidenced source calendar; real provider/calendar policy remains open. Cost if wrong: integration rejects incoherent clocks before research. Upstream revision selection and raw-unit evidence remain admission obligations.

- Task 8 checkpoint `3dc2e00` saved with complete git bundle, ZIP SHA256 `9d94cb016900c8972adf87bf4035472b8be02d407b9cd169cc81a53fa86ae6a1`. Task 9 dispatched to independent implementer `regimes_task9`, BASE `3dc2e00`. Only synthetic HMM/GMM software framework verification authorized here; financial comparison and winner selection remain gated.

- Task 9 interrupted by workspace-credit error after initial implementation; user authorized continuation. Retained 46 expected RED cases and reported 114 focused regime PASS (47 Task 9 cases, including a subsequent boundary-order regression). Runtime reset removed the interpreter during full-suite polling; restore dependencies and rerun complete verification before independent review. No full-suite PASS or Task 9 completion claimed at this checkpoint.

- Task 9 implementation `152b68d`: fresh restored-environment 114 focused / 670 full PASS, compileall and diff check exit 0. Independent `regimes_task9_review` pending; Task 10 not started. Numerical dependencies pinned and reset-only sequence convention explicit. No real data/research run.

- Task 9 review FAIL, important R1: mutable estimator can change predictions while retaining fitted candidate identity. Controller verified reference/consumption; accepted fix round1 to original implementer. Require fingerprint or immutable fitted state, regression RED/GREEN, full verification and scoped re-review. Task10 remains pending.

- Task 9 correction `48f03f3`: 25 new RED/GREEN regressions; 139 focused / 695 full PASS; compileall/diff check PASS. Independent `regimes_task9_fix_review`: R1 ADDRESSED, no new breakage, spec PASS / quality PASS. Task9 complete `152b68d` + `48f03f3`. Task10 next; no financial/OOS research or holdout run.

- Task9 checkpoint `2d993a5` saved with full git bundle; ZIP SHA256 `2fc5e56e0c2f6de20181ba5a884941e3e88c86e40c5895a1f1d26aa4735a5b6f`. Task10 assigned `/root/features_task10`, BASE `2d993a5`; user resumed 2026-10-04. No Task10 completion claimed. This is the final subsystem checkpoint, not the final V1 development-research checkpoint.

Ruling: Task10 fills abbreviated structural transforms with explicit candidate-only defaults: US=0/EU=1; USD market-cap bucket boundaries2e9/10e9/200e9; beta boundaries0.8/1.2 (equality enters upper bucket); beta uses252 exactly aligned adjusted returns/253 sessions, zero variance or insufficient evidence yields missing. VIX acceleration is (Vt−Vt−20)−(Vt−20−Vt−40), retaining the registry43-session minimum. Sector codes require a controlled economic taxonomy and explicit mapping, not arbitrary identity-like categories. All settings/version/units must be preserved, never represented as empirically selected or final-frozen choices. Currency conversion requires actual evidenced PIT FX and minimal dependency declaration clarification if used. Cost if wrong: candidate transform may be rejected at development research; no final policy can use it before validation.

Ruling: Task10 is staged snapshot orchestration, not a new provider facade. Exact typed producer bundles bind selected evidence, values, masks, config/version and cutoff to verified immutable snapshots; hashes prove integrity, not truth or provider admission. The end-to-end synthetic fixture must invoke real existing producers. Regime integration may be optional at API call level but must be implemented and tested with five interpretable plus an actual3–8state candidate (no arbitrary padding); base-only snapshots cannot claim full-regime integration evidence. Cost if wrong: integration gate remains incomplete and must be corrected before research.

- Task10 resumed after workspace credit interruption; retained source and TDD progress. Implementation `c6e8715` now reports721full/327subsystemPASS,compileall/diffcheckPASS,94dictionaryrows(81base+13reserved),20targets,89activefullfixture. Independent `features_task10_review` pending. Neither Task10 nor subsystem acceptance claimed yet; no financial/OOS/holdout run.

- Task10 review FAIL: R1 selected historical regime evidence.available_at may exceed prediction unnoticed at construction and staged admission. Controller verified and added R2: hardcoded regime qualityB promotes permittedC input evidence, compromising quality sensitivity. Both require bounded correction and RED/GREEN regressions before scoped re-review. No actualdata used.

- Task10 correction `02a61d8`:37REDregressions plus dictionaryRED;48focused/364subsystem/758fullPASS;compileall/diffcheckPASS. Independent `features_task10_fix_review`:R1/R2ADDRESSED,specPASS/qualityPASS,no newbreakage. Task10complete `c6e8715`+`02a61d8`; whole-subsystem review still pending before final checkpoint. No financial/OOS/holdout run.

- 2026-10-05 whole-subsystem review FAIL: F1canonicaltargetnames bypassFoldImputer;F2producercohort/snapshotuniverselineage mismatch;F3stalevaluationpeerclose accepted. Controller verified allthree and accepts one finalreviewfixbatch followed by scopedrereview. Declined-to-judge items explicitly retained as lateraudits/researchscope in reports/features-final-review.md. No realdata/research activity.

- Final correction `41db8f6`:27expectedRED then126focusedGREEN;410subsystem/804fullPASS,compileall/diffcheckPASS. Independent `features_final_fix_review`:F1/F2/F3ADDRESSED,specPASS/qualityPASS,no new materialbreakage/no out-of-scopeissues. Whole-subsystem software gatePASS. Canonicaltargetnames barred, actualproducercohorts checked, stalepeerquotes excluded usingowncalendar. Financial/OOSruns0, realdataauditOPEN, retrospectiveNOT_RUN.

Ruling: retain the dedicated research/development-v1 branch and full history for the user's checkpoint review; no merge, push, deployment or production handoff. This follows the requested human review stop point. The next research gate remains actual-panel admission and real-panel leakage, not another synthetic-test count. Final package contains committed source/reports and complete git bundle; ignored workflow recovery notes remain local.
