# Task 7 implementation — corporate-action economics

## Interfaces

- `economic_price_improvement(baseline_cost, delayed_fill, foregone_distribution) -> float`
- `economic_acquisition_cost(fill, delayed_from, actions, fx_service) -> EconomicAcquisitionCost`
- `split_adjusted_feature_prices(prices, actions, *, as_of) -> tuple[SplitAdjustedFeaturePrice, ...]`
- `FXRateService.resolve(base, quote, at_or_before) -> FXQuote` is the
  deliberately narrow evidenced protocol consumed from Task 8. Task 8 retains
  its scalar `rate` convenience API alongside this evidence-returning method.

`EconomicAcquisitionCost` reports HUF `total`, HUF `fill_cost`, HUF
`foregone_distributions`, the split-adjusted `share_units`, and
`label_matures_at`. Its immutable `EconomicCashflow` entries preserve native
amount, units, currency, cashflow timestamp, HUF amount, FX rate/fixing/
availability and the canonical `FXQuote` evidence. HUF-native flows carry no
fabricated 1.0 FX quote. `SplitAdjustedFeaturePrice` is a separate immutable
view; an executable `OHLCV` row is never rewritten or relabeled.

## Decisions

- One share at the baseline `delayed_from` bar defines the economic position.
  Every intervening split multiplies the units purchased at the delayed fill.
- A dividend is foregone only when the baseline session is strictly before its
  ex-date and the delayed fill is on or after that date. Its amount uses the
  share units in force on that ex-date.
- Fill currency conversion uses `fill.session_open_at`. Dividend conversion
  uses `CorporateAction.payable_at`; a relevant dividend without `payable_at`
  fails closed.
- Each non-HUF conversion resolves a canonical quote and rejects mismatched
  currency legs or fixing/availability later than its cashflow timestamp.
- Label maturity is the maximum of baseline/fill bar availability, relevant
  action availability, fill/payable timestamps and resolved FX availability.
  Known required timestamps after the authorized 2023-12-31 development
  boundary raise `EconomicLabelUnavailable` before any FX lookup.
- Relevant mergers, spin-offs, or unknown action types raise
  `NotImplementedError`; they are never treated as zero-value events.
- A split and dividend sharing an ex-date are rejected because the canonical
  action type has no intraday/unit-order field.
- Feature adjustment includes only splits whose actual shared-calendar session
  open and `available_at` are both `<= as_of`. This comparison is by absolute
  instant, independent of the caller's timezone offset. Historical bars are
  backward-adjusted onto the latest known share basis; raw execution bars stay
  unchanged.
- Feature rows expose PIT-compatible `available_at`, `as_of` and
  `max_input_available_at`, plus raw/action sources, revisions, applied action
  IDs, and the worst quality tier among their actual inputs. They interoperate
  directly with `assert_pit_safe` without promoting source quality.
- Non-finite/nonpositive fills, feature prices, FX rates and split ratios fail
  closed. Dividend amounts must be finite and nonnegative.

## Test evidence

TDD RED was observed before production code existed. The focused suite then
passed 16 tests, and the full repository regression passed 304 tests. Exact
commands and outcomes are recorded in `reports/task-7-tests.txt`.

Review fix round 1 reproduced seven focused failures before implementation;
the expanded focused suite passed 20 tests and the repository passed 309.

Coverage includes false ex-dividend dips, 2-for-1 and multi-split invariance,
dividend entitlement boundaries, per-cashflow FX timestamps, label maturity,
the development FX cutoff, unsupported actions, ambiguous same-day actions,
PIT split-adjusted feature prices, raw-bar preservation and invalid values.

## Concerns and deferred work

- The canonical `CorporateAction` contract supplies an exchange-local ex-date,
  not an effective timestamp or same-day sequence. Same-day split/dividend
  cases therefore require richer upstream data before they can be supported.
- Task 8 must implement the consumed `resolve` protocol and scalar `rate`
  convenience API with no-later-fixing selection and explicit missing-quote
  behavior.
- Merger, spin-off and other terminal economics remain intentionally
  unavailable until consideration and unit-allocation fields exist.
