# Whole-subsystem independent review — 2026-10-05

Reviewer `features_final_review`; software scope `25c6b04..02a61d8`.

**Spec FAIL; quality FAIL pending three Important fixes.** No Critical/Minor findings.

## Findings

**F1: Canonical targets bypass feature-only imputer admission.** normalize.py:42–48,268–273 rejects bare return_5d and wait prefixes, but accepts all return/direction {5,20,60}d_{local,huf} names created by targets/store.py:85–92. Isolated AST execution of the unchanged validator against the committed dictionary accepted12/20targets and rejected8. Reject all20 canonical targets in both constructor schema paths while retaining legitimate trailing return_*_raw predictors. Use precise patterns or a neutral naming contract; no feature import of target pipeline.

**F2: Snapshot universe lineage may contradict producer cohort.** features/snapshots.py:71–88,106–109 reconstructs the supplied universe only to admit the target; it does not compare RelativeFeatureSnapshot/ValuationFeatureSnapshot.eligible_security_ids (relative.py:99,419;valuation.py:170,401). Genuine content-bound outputs computed with eligible{A,B} can be assembled with valid universe{A}, yet B still influences the ranks while the new universe hash is stamped on their lineage. Enforce cohort agreement and actual historical-universe binding; test two legitimate universe evidences with unchanged producer bundles.

**F3: Valuation sector ranks reuse stale peer closes over missing sessions.** valuation.py:318–335 chooses the latest supplied peer close before cutoff without comparing the peer's expected eligible close. At2022-01-10EOD, currentA P/E10 and B priceonly2021-11-01 implying P/E5 yields rank1.0 although missing currentB should leave singletonA rank0.5. Compare peer price with previous_eligible_eod(peer.exchange,target_cutoff); preserve valid different-calendar/holiday prior closes. Regress both cases.

F2/F3 established by static control flow; proposed numeric end-to-end probes not executed because interpreter was absent. F1 isolated guard probe did run without dependencies or file modification. Existing758full/364subsystemPASS is reported prior verification, not rerun by reviewer.

## Strengths and scope

All81base signals have actual producers; regimes add only active columns. Separate immutable feature/target stores,20targetdefinitions,horizon-specific censoring and economic provenance are coherent. Accepted target session convention and corporate-action/FX handling remain consistent. Regime training-local scaling, causal filtering, fitted-state integrity and repaired clocks/quality are sound.

Reviewer read complete frozen specification, amended scope,plan/preflight,evidence,diff and relevant code/tests. Read-only; no raw/provider data,network,research,edits or full-suite rerun.

## Declined to judge — controller dispositions

- Actual provider vintage truth/completeness/tiers/paneladmission: accepted upstream audit deferral; remainsOPEN.
- Financial usefulness,calibration,state selection,candidate thresholds: accepted later research scope; no software test is evidence of utility.
- Purging/embargo and downstream models/policy/backtests: accepted subsequent subsystem scope, not claimed complete here.
- Production/deployment: explicitly excluded by user; no production certification.
- Alternative horizons,continuous HMM carry,replacement staged-evidence architecture: accepted decisions retained absent demonstrated invariant failure.
- Historical pristine claim: user amendment binding; retrospective2024-01-01..2026-09-11 NOT_RUN/notpristine; trueforward only after finalfreeze.

Controller inspected all three affected code paths and accepts the findings. A single bounded final-review fix batch is assigned, followed by scoped independent re-review. Whole-subsystem gate withheld; no methodological redesign or financial research is authorized.
