# Features Task 4 implementation

## Scope

Implemented the frozen registry's 12 fundamental outputs and 10 valuation
outputs in `fundamentals.py` and `valuation.py`. No registry entry was added,
removed, or mechanically expanded.

The pure `fundamental_features` helper supports the plan example while making
no point-in-time claim. The evidenced builders accept timestamped, revisioned,
quality-tiered report, estimate, price, classification, and universe evidence
and return `FeatureValue` records plus the exact selected evidence and explicit
applicability masks.

The helper retains the brief's literal `net_debt_to_ebitda` demonstration key
as an alias only; the evidenced feature panel contains only the registered
`net_debt_to_ebitda_raw` output, so this adds no mechanical panel feature.

## TDD record

RED:

- `pytest tests/features/test_fundamentals.py -v` could not start because the
  shell did not expose a `pytest` executable on `PATH`.
- `python -m pytest tests/features/test_fundamentals.py -v` then collected the
  new test and failed with `ModuleNotFoundError` for the deliberately absent
  `quant_dca.features.fundamentals` module.

GREEN:

- Focused: `python -m pytest tests/features/test_fundamentals.py -q` ->
  **11 passed**.
- Static checks: `git diff --check` and `python -m compileall -q` for both new
  implementation modules -> **passed**.
- Full suite (run once): `python -m pytest -q` -> **462 passed**.

## Contracts and rulings

- Report vintages are grouped by fiscal period. Revisions are selected within
  each period before the latest period is chosen. A later revision of an older
  period therefore cannot masquerade as the latest report.
- Reports are available only after both their real publication/availability
  clocks and an actual eligible exchange close. The implementation forward
  carries a selected known report; it never backward fills one.
- YoY growth, including EPS across losses and profits, is
  `(current - prior) / abs(prior)`. A zero or missing prior denominator remains
  missing. This sign convention makes movement from a larger loss toward a
  smaller loss positive.
- Earnings surprise exists only when a supplied estimate for the same security
  and fiscal period, currency, and per-share basis was known before report
  publication. Missing, late, future, or Tier C estimates remain missing; no
  consensus or publication clock is inferred.
- The registry's Tier B floor is enforced. A selected Tier C report, valuation
  price, or classification fails closed; a Tier C estimate is unavailable.
- Valuation prices must declare an admissible raw or split-adjusted valuation
  basis and exactly match report currency and per-share basis. Task 2's
  dividend-reinvested total-return economic close is explicitly rejected as a
  valuation price.
- Historical z-scores use exactly 756 exchange sessions ending at the feature
  date, sample standard deviation, and the report/classification vintage known
  at every individual session. Missing sessions or values prevent a z-score.
  A late report revision affects only sessions at and after its availability.
- Sector percentiles reuse `percentile_in_universe`, obtain eligibility from an
  explicit `UniverseIndex`, and obtain sector membership from point-in-time
  `SectorClassification` evidence. Unknown classification fails closed for
  sector-dependent applicability.
- Banks, insurers, and other Financials retain structural missing values and
  false applicability for conventional EV/EBITDA and FCF valuation features,
  as well as industrial fundamental ratios identified by the frozen registry.

## Limitations and research status

- Tests use synthetic fixtures. They establish software behavior only and do
  not establish provider coverage, cross-region comparability, or financial
  usefulness.
- No actual provider requests, 2024+ data access, model fitting, backtest,
  outer-OOS evaluation, holdout evaluation, or financial research run occurred.
- Price/book, tangible-book, capital, and credit-quality measures described as
  possible financial-sector inputs in the design are not in the frozen Task 1
  registry and were not added here.
- Earnings surprise remains absent until reliable point-in-time estimate
  history is explicitly supplied and admitted.

## Fix round 1 — independent review findings

Accepted and fixed the three Important findings in
`reports/features-task4-review.md`.

RED:

- Added regressions for an embedded report `consensus_eps` with absent, late,
  and Tier C estimate evidence; all three exposed an unverified surprise value.
- Added an evidenced blank-sector regression; the builder incorrectly admitted
  industrial applicability.
- Added a literal XNYS target/XNAS same-sector peer regression; the target rank
  was `0.5` because the peer was dropped rather than the required `1.0`.
- Added a typed valuation-period regression; the evidence record did not yet
  declare whether flow values were trailing-period normalized.
- Initial focused RED: **6 failed, 11 passed**.

GREEN:

- Focused: `python -m pytest tests/features/test_fundamentals.py -q` ->
  **17 passed**.
- Full suite (run once for this fix round): `python -m pytest -q` ->
  **468 passed**.

Fixes:

- The evidenced builder removes any report-embedded `consensus_eps` before it
  optionally inserts a separately selected, aligned, pre-publication Tier A/B
  estimate. Report payloads can no longer bypass estimate provenance.
- Blank or non-string selected report sectors hard-fail with
  `UNKNOWN_FUNDAMENTAL_SECTOR`; unknown classification never grants industrial
  applicability.
- Each historically eligible sector peer now contributes its latest admitted
  own-exchange close at or before the target cutoff. Report selection uses that
  peer close, and selected peer clocks are retained in snapshot evidence and
  output `max_input_available_at`. Exchange identity is not a rank filter.
- `ReportedFundamentals` now requires the narrow declaration
  `valuation_period_basis="trailing_twelve_months"`. Revenue, EPS, EBITDA, and
  FCF used in price ratios must therefore already be normalized upstream; this
  layer does not infer, annualize, or otherwise transform provider periods.

Fix-round verification remains synthetic software evidence only. No provider
or market-data request, actual panel admission, model fit, backtest, financial
research run, or 2024+ holdout access occurred.
