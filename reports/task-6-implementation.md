# Task 6 — historical universe eligibility

## Interfaces

Implemented `quant_dca.universe.membership` with:

- `UniverseIndex.is_eligible(security_id, as_of)` for one security.
- `UniverseIndex.eligible_universe(as_of, region)` for a deterministic list of
  historically eligible `Security` records.
- `UniverseIndex.from_rows(...)` for complete typed security, membership,
  trading-session, liquidity and fundamental-report evidence.
- Immutable `EligibilityThresholds`, `TradingSession`, `LiquidityMetric` and
  `FundamentalReport` input contracts.

Queries require aware datetimes. The frozen minimum is 120 sessions; callers
may configure a stricter count but cannot weaken it. Callers also configure the
liquidity threshold and whether a known fundamental report is required. The
implementation supplies no optimized liquidity or research-policy default.

## Eligibility decisions

The selector first chooses the latest security and membership versions whose
`available_at` is no later than the cutoff. It does not use a current or future
version to fill a historical gap. Conflicting records tied at the latest
availability time fail closed.

An eligible security must be a primary common-equity listing in `Region.US` or
`Region.EU`; its security and membership intervals must contain the UTC cutoff
date under `[active_from, active_to)` semantics. Membership region, MIC and
currency must agree with the selected security record. An ended interval still
qualifies at earlier cutoffs, preserving historically eligible delisted names.

History counts distinct supplied `TradingSession` dates that were known by the
cutoff, fall inside the security's listing history and are actual sessions for
the security MIC according to the offline exchange calendar. A new current
membership does not erase an established listing's earlier history. A session
counts only once its scheduled close is at or before the cutoff. Listing age,
duplicate rows, weekends, unfinished sessions and future-known sessions do not
inflate the count. Unsupported MICs or dates outside verified calendar coverage
make the security ineligible rather than escaping as calendar exceptions.

Liquidity uses the latest measured value that was itself available by the
cutoff and applies the caller's threshold inclusively. A required fundamental
report must have both `published_at <= as_of` and `available_at <= as_of`.
Missing security, membership, session history, liquidity or required-report
evidence yields `False`; unavailable evidence is never relabeled as Tier C.

## TDD and tests

The first focused RED run failed during collection with the expected
`ModuleNotFoundError: No module named 'quant_dca.universe'`. After the minimal
implementation, the focused suite passed 18 tests. A fresh full regression run
passed all 279 repository tests. `reports/task-6-tests.txt` preserves the RED
and GREEN evidence.

Review round 1 added three observed RED stages: the universe suite exposed that
the policy accepted a 119-session configuration and reset history at a recent
membership start; the calendar suite failed to import the required actual-close
helper; and the universe suite then exposed premature current-session counting
plus propagated unknown-MIC and coverage errors. The fixes enforce the floor,
count listing history independently of membership tenure, use the shared actual
session close, and translate unavailable calendar evidence to ineligibility.
The final focused calendar/universe run passed 87 tests, and the fresh full
repository run passed all 288 tests.

Tests cover delisted-name survivorship, inclusive/exclusive interval boundaries,
regional selection, common-equity and primary-listing filters, actual and
distinct session counting, the configured 119/120 session boundary, future
availability exclusion, history predating a recent membership, just-before/at-
close behavior, unknown MIC and calendar-coverage gaps, inclusive liquidity
thresholding, optional/required fundamentals, missing inputs, mismatched
membership metadata and naive query times. All inputs are offline fixtures; no
network or retrospective-holdout data was accessed.

## Concerns and limits

- `LiquidityMetric.value` is deliberately policy-neutral. Its economic unit,
  lookback and acceptable age must be defined by the upstream configured metric
  pipeline; this task does not optimize or default them.
- `FundamentalReport` proves only that a specific report was published and
  knowable. Real US/EU and active/delisted report coverage remains a provider
  evidence requirement before research use.
- `TradingSession` is explicit history evidence, not proof that an executable
  bar passed canonical quality validation. Downstream consumers must feed only
  accepted historical observations.
- Fixture success establishes software behavior only. It does not establish
  actual 2015–2023 universe completeness or survivorship-free provider coverage.
