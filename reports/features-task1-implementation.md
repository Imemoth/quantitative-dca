# Features / Targets / Regimes — Task 1 implementation

Status: implemented and verified as a software/schema contract. This task did
not fetch market data, inspect holdout data, fit a transform or model, select a
provider, or make an empirical feature-selection claim.

## Delivered contract

`configs/features_v1.yaml` is the frozen human-readable V1 source. The Python
loader converts it to immutable `RawDependency`, `FeatureDefinition`,
`PanelBudget`, and `FeatureRegistry` objects and rejects invalid files before a
consumer can use them. PyYAML is now an explicit runtime dependency rather than
an undeclared environment assumption.

Each final feature definition records:

- unique name, controlled economic domain, and underlying base signal;
- one or more raw dependency names;
- dependency-level `available_at` field, literal
  `available_at <= prediction_timestamp` join rule, and `as_of_vintage`
  revision policy;
- required trailing-session lookback and controlled feature-availability rule;
- minimum accepted quality tier, transform, formula, normalization,
  applicability, and missing-value policy.

The quality floor is an input-acceptance contract. It does not assign or infer
a tier for any provider. Provider mappings and tiers are outside this registry;
unknown root, dependency, and feature fields are rejected. Direct security
identity tokens including ticker, security ID, ISIN, and entity ID are rejected
even when nested in a dependency or formula.

## Deterministic schema allocation

The registry contains 81 non-regime final outputs derived from 70 controlled
base signals. Five panel slots are reserved for the interpretable regime branch
and eight are reserved as an upper bound for the later 3–8-state unsupervised
branch. This produces a maximum planned V1 panel of 94 features within the
frozen 80–95 range. The eight-slot unsupervised reserve does not choose eight
states and does not fit a regime model; later tasks may use three through eight
of those slots without changing the feature budget.

| Domain | Registered outputs |
| --- | ---: |
| Price / trend | 11 |
| Volatility / drawdown | 9 |
| Volume / liquidity | 2 |
| Relative strength / cross-sectional | 8 |
| Fundamentals / quality / growth | 12 |
| Valuation | 10 |
| Market / cross-asset | 6 |
| Known event calendar | 6 |
| Categorical structural | 4 |
| Macro | 13 |
| **Registered subtotal** | **81** |
| Reserved interpretable-regime probabilities | **5** |
| Reserved unsupervised-regime probabilities | **8** |
| **Maximum planned final panel** | **94** |

The macro allocation retains all minimum architecture blocks: headline and
core CPI/HICP, unemployment, monetary-jurisdiction policy rate, US 10Y–2Y and
10Y–3M curves, EU sovereign curve proxy, regional high-yield and
investment-grade spreads, regional financial conditions, central-bank
liquidity, and global risk-off. Region and monetary-jurisdiction applicability
select the appropriate series; the registry does not infer a source or tier.

Cross-sectional transforms explicitly require historical membership and
classification dependencies and describe eligible-sector normalization.
Fundamental and valuation definitions preserve structural missingness where a
metric is economically invalid, including industrial leverage and EBITDA
metrics for financials. Event features require the future event date to have
been announced as of the prediction timestamp. EOD features retain the
conservative next-EOD convention.

## Deliberately unregistered candidates

The bounded initial schema retains every output explicitly assigned to Tasks 2
and 4, including 52-week-high distance, drawdown duration, interest coverage,
dilution, earnings surprise, sector valuation percentiles, and trailing
own-history valuation z-scores. To preserve the budget, optional duplicate
representations were trimmed before any task-mandated raw output.

The following design-spec candidates remain outside the controlled initial
schema: trend consistency, downside/upside asymmetry, abnormal-volume direction
interaction, sector volatility/drawdown percentiles, days since earnings,
earnings yield, growth-tech benchmark momentum, market breadth, index
volatility, regional-market momentum, and mechanical expansion of every macro
series across 3M/6M/12M transforms.

These are not rejected by an empirical experiment. They are deferred to keep
the implementation contract economically controlled and inside the panel
budget. Adding one requires an explicit versioned registry change and the
applicable research governance; it must not be generated mechanically from
every available series.

## Validation and TDD evidence

The initial focused run failed during collection because
`quant_dca.features.registry` did not exist. After dependency restoration and
implementation, the focused suite passed. A second RED/GREEN cycle proved the
loader rejected provider-tier assignments instead of ignoring them. A final
focused RED/GREEN cycle split the regime allocation into five interpretable
slots plus an eight-slot upper bound for the unsupervised branch, so both
permitted branches fit without preselecting an unsupervised state count.

- Focused final: `python -m pytest tests/features/test_registry.py -v` —
  **6 passed**.
- Full suite (run once): `python -m pytest -v` — **400 passed** in 2.39s.
- Static checks: `git diff --check` passed; registry load reported 80
  registered outputs, 69 base signals, and final maximum allocation 93.

The full suite preceded the final registry-allocation correction. The focused
registry suite was rerun after that correction and passed. No unrelated
untracked fixture or raw-audit files were modified or staged.

## Boundaries for later tasks

This task defines metadata and validates the contract only. It does not compute
features, resolve region-specific series, perform as-of joins, rank an eligible
universe, fit rolling normalizers, impute values, or create regime
probabilities. Those consumers must preserve these dependency clocks,
applicability masks, and missing policies. Task 2 has not been started.

## Independent-review fix round 1

The review of commit `5d8d3fc` identified three contract gaps. This fix round
addresses all three while leaving feature calculation for Task 2.

1. Registered `momentum_universe_percentile` with the 120-session return,
   historical-membership dependency, historical eligible-universe
   applicability, and `eligible_universe_percentile_as_of` normalization. The
   panel is now 81 registered plus 13 reserved regime outputs, or 94 maximum.
2. Replaced the ambiguous liquidity basis with canonical unadjusted close ×
   verified original-share-unit volume × the local-to-USD FX rate selected for
   each historical EOD. Both median dollar volume and the Amihud denominator
   use this same USD turnover basis; Amihud keeps an adjusted economic-return
   numerator. Raw dependencies now expose `value_basis` and mandatory
   `required_provenance`. The FX dependency requires
   `fixing_at <= historical_eod and available_at <= historical_eod`; missing FX
   therefore remains missing rather than falling back to native currency.
   Numeric split and FX invariance belong to Task 2, when the calculator exists.
3. Identity validation now splits identifier components and rejects ticker,
   symbol, ISIN, CUSIP, SEDOL, FIGI, and internal security/entity/instrument ID
   forms. Parameterized regressions also prove that economic terms such as
   `security_region`, `entity_value_growth`, and `symbolic_regression_score`
   remain allowed.

TDD evidence:

- RED: `python -m pytest tests/features/test_registry.py -v` — **11 failed,
  10 passed** for the absent universe feature, missing liquidity basis/FX
  contract, old panel count, and accepted identity aliases.
- GREEN: the same focused command — **21 passed** in 1.97s.
- Verification environment precondition: the first final invocation of
  `python -m pytest tests/features/test_registry.py -v` exited 1 before
  collection with `No module named pytest`. No test ran. The declared project
  dependencies were then restored with `python -m pip install -e '.[test]'`;
  the completed environment reported pytest 9.1.1 and PyYAML 6.0.3.
- Final focused command: `python -m pytest tests/features/test_registry.py -v`
  — **21 passed in 2.09s** (exit 0).
- Final full-suite command, run once after the focused pass:
  `python -m pytest -v` — **415 passed in 4.38s** (exit 0).

Limitations: Task 1 validates the schema and dependency/provenance contract; it
does not numerically calculate USD turnover. Split and FX invariance tests
remain assigned to the Task 2 calculator. The review fix therefore establishes
the required unadjusted-price/original-unit-volume/PIT-FX inputs without
claiming numerical invariance before that calculator exists. An independent
review is still required before Task 2 starts.
