# Task 8 independent review — 2026-10-04

Reviewer: independent agent `regimes_task8_review`. Scope: `49ef5f6..0925763`.

## Spec compliance: PASS

Implements five named memberships and deterministic hard state, configurable prototype distances, recovery gating and replayable explanations (`interpretable.py:176–203`; `configs/regimes_v1.yaml:1–31`). Fixed reference scaling uses no fitting or full-history statistics. Exact input allowlists exclude ticker identities, targets and unknown signals (`interpretable.py:54–58,165–174,216–247`). Evidenced prediction validates partitions, development timestamps, regional benchmark chronology and both snapshots before numeric consumption (`interpretable.py:264–289`).

## Code quality: PASS — approved

No critical, important or minor defect found within the task scope. Pure arithmetic and evidenced PIT entry points are clearly separated; helper outputs lack PIT certification. Recovery requires the exact preceding benchmark snapshot and uses unclipped values. Bounded configuration arithmetic, stable softmax, immutable explanations and config hashing support reproducibility. Synthetic tests cover states, ties, missing values, provenance rejection, boundary metadata and config changes.

## Checks and limits

The reviewer read the supplied diff and inspected unchanged canonical FeatureValue/PIT validation and previous_eligible_eod dependencies for named clock and prior-session risks. Required clocks are aware, PIT checks enforce availability/source chronology before values, and the inclusive close contract supports subtracting one microsecond to select the preceding close. No suite rerun, mutations, network, market data or additional agents were used by the reviewer.

Implementer: 67 focused / 623 complete tests PASS. Controller independently reran the complete suite at `0925763` on 2026-10-03: 623 passed in 8.36 seconds; compileall and git diff --check exit 0. Review completed after those checks, as required.

Approval covers a synthetic implementation candidate, not calibration, financial selection, configuration freeze or downstream integration.

## Cross-task observations carried forward

- Actual revision selection, source-unit correctness and feature/target integration remain producer/Task 10 admission obligations.
- Region.EU permits XLON as an aggregate benchmark calendar. This does not admit UK-listed securities because inputs are aggregate, entity-free records. The task brief does not choose a regional benchmark policy; that policy needs explicit integration verification.

Controller ruling: the calendar allowlist is software capability, not approval of a UK instrument or selection of a regional benchmark. V1 remains USA plus EU-listed equities. Task 10 must bind a regional aggregate to its evidenced source calendar; no implicit XLON default or inferred EU equity eligibility is permitted. A real source/calendar choice remains open until data admission. Cost if wrong: the integration gate must reject incoherent regional clocks before any research.
