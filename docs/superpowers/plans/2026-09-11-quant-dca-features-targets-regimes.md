# Quant DCA Features, Targets & Regimes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform PIT-safe canonical data into a versioned 80-95-feature panel, executable 5D/20D/60D targets and parallel interpretable/unsupervised market-regime features without leakage.

**Architecture:** Feature builders are pure functions over past/present snapshots; target builders are isolated functions over future executable opens. Rolling normalization and cross-sectional ranks are calculated only from historically eligible observations. Regime outputs become normal input features only after each regime estimator is fit within the current training fold.

**Tech Stack:** Python 3.12+, Pandas/NumPy, scikit-learn, statsmodels, hmmlearn, Parquet/DuckDB, pytest.

**Spec:** `docs/quant-dca-engine-v1-design-spec.md`

## Global Constraints

- Feature and target pipelines are physically separate.
- 5D/20D/60D are the only prediction horizons.
- Better-entry labels use future eligible **open** prices and economic acquisition cost, never future intraday lows.
- 5D threshold = 1.5%; 20D threshold = 3.0%.
- Feature normalization is rolling/train-local/cross-sectional as defined; never full-history.
- Direct ticker identity is forbidden.
- Sector-inapplicable metrics remain structurally missing.
- Scheduled event dates are features only if the announcement itself was known by the prediction timestamp.

---

## File map

- Create: `src/quant_dca/features/price.py`, `volatility.py`, `liquidity.py`, `relative.py`.
- Create: `src/quant_dca/features/fundamentals.py`, `valuation.py`, `macro.py`, `events.py`.
- Create: `src/quant_dca/features/normalize.py`, `registry.py`, `builder.py`.
- Create: `src/quant_dca/targets/executable.py`, `returns.py`, `builder.py`.
- Create: `src/quant_dca/regimes/interpretable.py`, `unsupervised.py`, `selection.py`.
- Create: `configs/features_v1.yaml`, `configs/regimes_v1.yaml`.
- Create: `reports/feature-dictionary.csv`, `reports/target-dictionary.csv`.
- Create tests under parallel `tests/features`, `tests/targets`, `tests/regimes`.

### Task 1: Build feature registry and dependency contract

**Interfaces:**
- Produces: `FeatureDefinition(name, domain, lookback_sessions, availability_rule, quality_floor, transform)` and `FeatureRegistry`.

- [ ] **Step 1: Write failing registry tests**

```python
from quant_dca.features.registry import FeatureRegistry


def test_v1_registry_rejects_ticker_identity():
    registry = FeatureRegistry.v1()
    assert "ticker" not in registry.names()
    assert 50 <= len(registry.base_signal_names()) <= 100
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/features/test_registry.py -v`

- [ ] **Step 3: Implement versioned registry**

Every definition names its raw dependencies and PIT availability rule. `configs/features_v1.yaml` is the human-readable frozen list; code validates it at startup.

- [ ] **Step 4: Run tests and commit**

Run: `pytest tests/features/test_registry.py -v`

```bash
git add src/quant_dca/features/registry.py configs/features_v1.yaml tests/features/test_registry.py
git commit -m "feat: define controlled V1 feature registry"
```

### Task 2: Implement price/trend/volatility/liquidity features

**Interfaces:**
- Produces per security/as-of: returns 5/20/60/120/252, MA distances 20/50/200, slopes 20/60, 52W-high distance, realized vol 20/60, vol ratio, downside vol, ATR%, current/max drawdown, drawdown duration, dollar-volume and Amihud-style liquidity signals.

- [ ] **Step 1: Write no-future rolling test**

```python
import pandas as pd
from quant_dca.features.price import trailing_return


def test_trailing_return_ignores_future_rows():
    px = pd.Series([100, 102, 101, 110], index=pd.date_range("2020-01-01", periods=4))
    first = trailing_return(px.iloc[:3], 2)
    mutated = px.copy(); mutated.iloc[3] = 9999
    second = trailing_return(mutated.iloc[:3], 2)
    assert first == second
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/features/test_price_vol_liquidity.py -v`

- [ ] **Step 3: Implement pure trailing feature functions**

Use total-return/adjusted feature series with verified corporate-action handling. Preserve genuine crisis outliers.

- [ ] **Step 4: Add missing-lookback tests**

A security with 120 sessions may produce 20D/60D features while 252D features remain missing.

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/features/test_price_vol_liquidity.py -v`

```bash
git add src/quant_dca/features tests/features/test_price_vol_liquidity.py
git commit -m "feat: add trailing price volatility and liquidity features"
```

### Task 3: Implement historical relative-strength and cross-sectional features

**Interfaces:**
- Produces: stock-vs-sector and stock-vs-market relative returns at 20/60/120D plus historical sector/universe percentiles.

- [ ] **Step 1: Write historical-universe rank test**

```python
from quant_dca.features.relative import percentile_in_universe


def test_percentile_uses_only_eligible_names():
    values = {"A": 0.10, "B": 0.20, "DELISTED_LATER": 0.15, "FUTURE_MEMBER": 0.99}
    eligible = {"A", "B", "DELISTED_LATER"}
    pct = percentile_in_universe("A", values, eligible)
    assert 0.0 <= pct <= 1.0
    assert "FUTURE_MEMBER" not in eligible
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/features/test_relative.py -v`

- [ ] **Step 3: Implement cross-sectional rank functions**

All rank universes are passed explicitly from `UniverseIndex`; functions may not query current membership implicitly.

- [ ] **Step 4: Run tests and commit**

Run: `pytest tests/features/test_relative.py -v`

```bash
git add src/quant_dca/features/relative.py tests/features/test_relative.py
git commit -m "feat: add historical cross-sectional relative features"
```

### Task 4: Implement fundamentals, valuation and applicability masks

**Interfaces:**
- Produces: revenue/EPS/FCF growth, margins, ROIC/ROE, leverage/coverage where meaningful, dilution, earnings surprise, valuation ratios, own-history valuation z-scores and sector percentiles.

- [ ] **Step 1: Write PIT and financial-sector applicability tests**

```python
from quant_dca.features.fundamentals import fundamental_features


def test_bank_does_not_receive_net_debt_to_ebitda_imputation():
    out = fundamental_features({"sector": "Financials", "net_debt_to_ebitda": None})
    assert out["net_debt_to_ebitda"] is None
    assert out["net_debt_to_ebitda_applicable"] is False
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/features/test_fundamentals.py -v`

- [ ] **Step 3: Implement sector-aware feature computation**

Forward-carry only the latest historically published report. Never backward-fill. Own-history valuation z-scores use trailing observations available at that date only.

- [ ] **Step 4: Run tests and commit**

Run: `pytest tests/features/test_fundamentals.py -v`

```bash
git add src/quant_dca/features/fundamentals.py src/quant_dca/features/valuation.py tests/features/test_fundamentals.py
git commit -m "feat: add point-in-time fundamental and valuation features"
```

### Task 5: Implement region-aware macro and scheduled-event features

**Interfaces:**
- Produces: inflation/labor/policy/curve/credit/conditions/liquidity signals plus known-event distance/risk fields.

- [ ] **Step 1: Write macro vintage and event-announcement tests**

```python
from quant_dca.features.events import days_until_known_event


def test_unannounced_future_earnings_date_is_missing():
    value = days_until_known_event(
        prediction_date="2020-01-10",
        event_date="2020-02-01",
        announced_at="2020-01-20",
    )
    assert value is None
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/features/test_macro_events.py -v`

- [ ] **Step 3: Implement macro level/trend/acceleration transforms**

Use level plus selected 3M/6M/12M deltas and acceleration only where economically meaningful. Map EU securities through `monetary_jurisdiction` for ECB versus local central-bank policy.

- [ ] **Step 4: Implement event availability rules**

Known earnings/FOMC/ECB/CPI/HICP dates may be encoded only after their announcement/public calendar availability.

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/features/test_macro_events.py -v`

```bash
git add src/quant_dca/features/macro.py src/quant_dca/features/events.py tests/features/test_macro_events.py
git commit -m "feat: add region-aware macro and known-event features"
```

### Task 6: Implement rolling normalization and train-safe imputation

**Interfaces:**
- Produces: `rolling_zscore(series, window)`, `CrossSectionNormalizer`, `FoldImputer.fit(train).transform(data)`.

- [ ] **Step 1: Write future-mutation invariance test**

```python
from quant_dca.features.normalize import rolling_zscore


def test_rolling_normalization_does_not_change_when_future_changes():
    x = [1, 2, 3, 4, 5]
    a = rolling_zscore(x[:4], 3)[-1]
    y = x.copy(); y[-1] = 5000
    b = rolling_zscore(y[:4], 3)[-1]
    assert a == b
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/features/test_normalize.py -v`

- [ ] **Step 3: Implement normalization utilities**

Fit imputation/scaling statistics only on the current training partition. Tree-model native missing handling remains available; do not globally impute the stored feature table.

- [ ] **Step 4: Run tests and commit**

Run: `pytest tests/features/test_normalize.py -v`

```bash
git add src/quant_dca/features/normalize.py tests/features/test_normalize.py
git commit -m "feat: add leakage-safe feature normalization"
```

### Task 7: Implement isolated target builder

**Interfaces:**
- Produces `TargetRow` with return_5d/20d/60d, executable_min_return_5d/20d, better_entry_5d/20d local and HUF versions, and `target_end_timestamp`.

- [ ] **Step 1: Write next-open target test**

```python
from quant_dca.targets.executable import best_executable_improvement


def test_better_entry_uses_future_opens_not_lows():
    baseline = 100.0
    opens = [101.0, 98.0, 99.0]
    lows = [90.0, 90.0, 90.0]
    assert best_executable_improvement(baseline, opens) == 0.02
```

- [ ] **Step 2: Add dividend-economic-equivalence target test**

A 2% ex-dividend quoted drop with a 2% foregone distribution must not label a 1.5% better economic entry.

- [ ] **Step 3: Verify failure**

Run: `pytest tests/targets/test_executable.py -v`

- [ ] **Step 4: Implement target builder in the target-only package**

The feature package must not import from `quant_dca.targets`. Add an architecture test that fails if such an import appears.

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/targets -v`

```bash
git add src/quant_dca/targets tests/targets
git commit -m "feat: build executable future targets in isolated pipeline"
```

### Task 8: Implement interpretable regime branch

**Interfaces:**
- Produces five regime probabilities plus hard state using only current/past market+macro features.

- [ ] **Step 1: Write probability-sum and deterministic fixture tests**

```python
from quant_dca.regimes.interpretable import InterpretableRegimeModel


def test_regime_probabilities_sum_to_one():
    model = InterpretableRegimeModel.default()
    probs = model.predict_proba({"market_trend": -1.0, "vol_z": 2.0, "credit_z": 1.5})
    assert abs(sum(probs.values()) - 1.0) < 1e-9
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/regimes/test_interpretable.py -v`

- [ ] **Step 3: Implement transparent score-to-probability mapping**

Keep thresholds/weights in `configs/regimes_v1.yaml`; every state decision must be explainable from inputs.

- [ ] **Step 4: Run tests and commit**

Run: `pytest tests/regimes/test_interpretable.py -v`

```bash
git add src/quant_dca/regimes/interpretable.py configs/regimes_v1.yaml tests/regimes/test_interpretable.py
git commit -m "feat: add interpretable five-state regime baseline"
```

### Task 9: Implement unsupervised HMM/GMM candidates and 3-8 state search

**Interfaces:**
- Produces: `fit_regime_candidate(train, family, n_states, seed)`, `predict_state_proba(model, X)` and candidate diagnostics.

- [ ] **Step 1: Write train-only fit boundary test**

```python
from quant_dca.regimes.selection import candidate_grid


def test_regime_grid_is_exactly_three_to_eight_states():
    assert [c.n_states for c in candidate_grid("hmm")] == [3, 4, 5, 6, 7, 8]
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/regimes/test_unsupervised.py -v`

- [ ] **Step 3: Implement HMM and GMM wrappers**

Expose likelihood, state occupancy, transition stability and probability outputs through one protocol. Set reproducible seeds.

- [ ] **Step 4: Implement selection diagnostics**

Selection inputs are OOS likelihood, temporal/state stability, transition stability, economic interpretability annotations and downstream incremental value. Do not choose by in-sample likelihood alone.

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/regimes -v`

```bash
git add src/quant_dca/regimes tests/regimes
git commit -m "feat: add unsupervised regime candidate framework"
```

### Task 10: Build immutable feature/target snapshots and dictionaries

**Interfaces:**
- Produces: `build_feature_snapshot(as_of, registry_version)`, `build_target_store(start, end)`, dictionary CSVs.

- [ ] **Step 1: Add end-to-end fixture test**

For an as-of date, assert every stored feature's `available_at <= prediction_timestamp`, target start is later, ticker identity is absent, and feature count is within the approved V1 range.

- [ ] **Step 2: Build dictionaries**

Each feature row in `reports/feature-dictionary.csv` contains: name, domain, formula/transform, raw source, lookback, availability rule, normalization, applicability, missing-data rule and quality floor.

Each target row in `reports/target-dictionary.csv` contains: name, horizon, reference execution, economic adjustment, currency basis and target-end rule.

- [ ] **Step 3: Run complete feature/target/regime tests**

Run: `pytest tests/features tests/targets tests/regimes -v`

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/quant_dca/features src/quant_dca/targets src/quant_dca/regimes reports/feature-dictionary.csv reports/target-dictionary.csv
git commit -m "docs: freeze V1 feature and target contracts"
```
