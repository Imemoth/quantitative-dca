# Quant DCA Models, Policy & Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evaluate whether the frozen PIT feature/target system provides economically meaningful DCA timing edge on 2015-2023 development OOS data using a constrained champion/challenger stack and executable policy simulation.

**Architecture:** A nested expanding walk-forward orchestrator produces purged/embargoed folds. Each target receives a simple baseline and one permitted non-linear challenger; probabilities are calibrated inside training only. Model outputs feed a constrained NetWaitEV estimator and DCA policy, which is judged against fixed benchmarks with cohort-level statistics and reproducible cost stress tests.

**Tech Stack:** Python 3.12+, scikit-learn, XGBoost-compatible gradient boosting, statsmodels quantile regression, NumPy/Pandas, scipy, DuckDB/Parquet, pytest.

**Spec:** `docs/quant-dca-engine-v1-design-spec.md`

## Global Constraints

- Development OOS is 2015-2023 only; lockbox rows must be inaccessible to research-selection functions.
- Outer block and refit frequency are quarterly.
- Training rows require `target_end_timestamp <= training_cutoff`.
- Five-trading-session embargo applies after latest included target end before next validation/test signal block.
- Model families are constrained; deep learning and unrestricted AutoML are forbidden.
- Ensemble is disabled unless both components independently pass OOS value/non-redundancy/incremental-value gates.
- `WAIT` initial gate: calibrated 5D better-entry probability >= 60% AND NetWaitEV_5D >= +0.50%.
- Extension gate: 20D better-entry probability >= 65% AND incremental NetWaitEV >= +0.75%.
- Hard maximum wait: 20 eligible trading sessions after baseline.
- `NO_EDGE` means execute baseline/next eligible open, not cash.

---

## File map

- Create: `src/quant_dca/validation/folds.py`, `purge.py`, `orchestrator.py`.
- Create: `src/quant_dca/models/classification.py`, `regression.py`, `quantile.py`, `selection.py`.
- Create: `src/quant_dca/calibration/probability.py`.
- Create: `src/quant_dca/policy/net_wait_ev.py`, `engine.py`, `confidence.py`.
- Create: `src/quant_dca/backtest/execution.py`, `benchmarks.py`, `simulator.py`.
- Create: `src/quant_dca/metrics/timing.py`, `probability.py`, `returns.py`, `bootstrap.py`.
- Create: `src/quant_dca/experiments/ledger.py`, `run.py`, `walk_forward.py`.
- Create: `src/quant_dca/tools/verify_lockbox_untouched.py` — guard/audit CLI shared with the freeze phase.
- Create: `configs/model_search_v1.yaml`, `configs/policy_v1.yaml`, `configs/cost_scenarios_v1.yaml`, `configs/research_v1.yaml`.

### Task 1: Implement nested expanding quarterly fold generator

**Interfaces:**
- Produces: `OuterFold(train_end, test_start, test_end)`, `inner_folds(outer_fold)`.

- [ ] **Step 1: Write chronological fold test**

```python
from quant_dca.validation.folds import outer_folds


def test_first_outer_fold_is_2015_q1_with_pre_2015_training():
    fold = outer_folds("2010-01-01", "2023-12-31")[0]
    assert str(fold.test_start).startswith("2015-01")
    assert fold.train_end < fold.test_start
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/validation/test_folds.py -v`

- [ ] **Step 3: Implement quarterly expanding folds**

Do not create random train/test splits anywhere in the research stack.

- [ ] **Step 4: Run tests and commit**

Run: `pytest tests/validation/test_folds.py -v`

```bash
git add src/quant_dca/validation/folds.py tests/validation/test_folds.py
git commit -m "feat: add expanding quarterly validation folds"
```

### Task 2: Implement label maturity, purge and five-session embargo

**Interfaces:**
- Produces: `eligible_training_rows(rows, training_cutoff, next_test_start, calendar)`.

- [ ] **Step 1: Write overlap-removal test**

```python
from quant_dca.validation.purge import training_row_allowed


def test_row_whose_target_matures_after_cutoff_is_purged():
    assert not training_row_allowed(
        target_end="2020-04-10",
        training_cutoff="2020-03-31",
        embargo_ok=True,
    )
```

- [ ] **Step 2: Add five-session embargo test**

Assert that a row whose target ends fewer than five eligible sessions before test start is excluded.

- [ ] **Step 3: Verify failure**

Run: `pytest tests/validation/test_purge.py -v`

- [ ] **Step 4: Implement and run tests**

Run: `pytest tests/validation/test_purge.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/quant_dca/validation/purge.py tests/validation/test_purge.py
git commit -m "feat: enforce target maturity purge and embargo"
```

### Task 3: Implement classification champion/challenger families

**Interfaces:**
- Produces: `fit_classifier(family, X_train, y_train, config)`, `predict_probability(model, X)`.

- [ ] **Step 1: Write deterministic classifier test**

```python
from quant_dca.models.classification import make_classifier


def test_logistic_classifier_is_reproducible():
    a = make_classifier("elastic_logistic", seed=7)
    b = make_classifier("elastic_logistic", seed=7)
    assert a.get_params() == b.get_params()
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/models/test_classification.py -v`

- [ ] **Step 3: Implement exact allowed families**

Baseline: Elastic-Net logistic. Challenger: gradient-boosted trees. Search spaces live in YAML and are deliberately small; code rejects unknown model families.

- [ ] **Step 4: Run tests and commit**

Run: `pytest tests/models/test_classification.py -v`

```bash
git add src/quant_dca/models/classification.py configs/model_search_v1.yaml tests/models/test_classification.py
git commit -m "feat: add constrained classification model families"
```

### Task 4: Implement return and quantile model families

**Interfaces:**
- Produces: Elastic Net/Huber/boosted return regressors and linear/boosted quantile regressors for Q25/Q50/Q75.

- [ ] **Step 1: Write allowed-quantile test**

```python
from quant_dca.models.quantile import allowed_quantiles


def test_v1_quantiles_are_fixed():
    assert allowed_quantiles() == (0.25, 0.50, 0.75)
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/models/test_regression_quantile.py -v`

- [ ] **Step 3: Implement families and constrained configs**

Do not add neural or arbitrary AutoML estimators.

- [ ] **Step 4: Run tests and commit**

Run: `pytest tests/models/test_regression_quantile.py -v`

```bash
git add src/quant_dca/models/regression.py src/quant_dca/models/quantile.py tests/models/test_regression_quantile.py
git commit -m "feat: add return and entry-distribution model families"
```

### Task 5: Implement fold-local probability calibration

**Interfaces:**
- Produces: `fit_calibrator(method, y_val, p_val)`, methods `platt` and `isotonic` only.

- [ ] **Step 1: Write method whitelist test**

```python
import pytest
from quant_dca.calibration.probability import make_calibrator


def test_unknown_calibrator_is_rejected():
    with pytest.raises(ValueError):
        make_calibrator("temperature_scaling")
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/calibration/test_probability.py -v`

- [ ] **Step 3: Implement calibration wrappers**

Calibration data must come from inner validation predictions, never outer OOS or lockbox.

- [ ] **Step 4: Run tests and commit**

Run: `pytest tests/calibration/test_probability.py -v`

```bash
git add src/quant_dca/calibration tests/calibration
git commit -m "feat: add train-local probability calibration"
```

### Task 6: Implement champion/challenger and optional ensemble gate

**Interfaces:**
- Produces: `select_champion(candidates, metrics, complexity_hurdle)` and `ensemble_allowed(a, b, diagnostics)`.

- [ ] **Step 1: Write simplicity-wins test**

```python
from quant_dca.models.selection import select_champion


def test_complex_model_loses_when_increment_is_negligible():
    winner = select_champion({"simple": 0.071, "boosted": 0.073}, min_increment=0.005)
    assert winner == "simple"
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/models/test_selection.py -v`

- [ ] **Step 3: Implement selection policy**

Use target-appropriate nested-OOS metrics; ensemble requires independent positive value, non-redundant errors and economically meaningful nested-OOS improvement. Only weighted averaging is permitted.

- [ ] **Step 4: Run tests and commit**

Run: `pytest tests/models/test_selection.py -v`

```bash
git add src/quant_dca/models/selection.py tests/models/test_selection.py
git commit -m "feat: enforce champion challenger complexity gates"
```

### Task 7: Implement the two permitted NetWaitEV estimators

**Interfaces:**
- Produces: `ComponentEVEstimator`, `CrossFittedPolicyValueEstimator`, each with `fit(...)` and `predict(...)`.

- [ ] **Step 1: Write component identity test**

```python
from quant_dca.policy.net_wait_ev import component_net_wait_ev


def test_component_ev_subtracts_miss_cost_and_friction():
    value = component_net_wait_ev(
        p_better=0.60,
        gain_if_better=0.03,
        miss_cost=0.02,
        friction=0.001,
    )
    assert round(value, 4) == round(0.60*0.03 - 0.40*0.02 - 0.001, 4)
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/policy/test_net_wait_ev.py -v`

- [ ] **Step 3: Implement both estimators with cross-fitting boundaries**

The cross-fitted estimator may use only current PIT features and out-of-fold upstream model outputs. It cannot be an unconstrained meta-learner.

- [ ] **Step 4: Add fallback test**

When neither estimator meets stability/calibration criteria, `wait_enabled=False` for that horizon.

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/policy/test_net_wait_ev.py -v`

```bash
git add src/quant_dca/policy/net_wait_ev.py tests/policy/test_net_wait_ev.py
git commit -m "feat: add constrained net wait value estimators"
```

### Task 8: Implement DCA action policy and WAIT state machine

**Interfaces:**
- Produces: `PolicyDecision(action, reason_codes, next_evaluation, deadline)`; actions exactly `BUY_NOW`, `WAIT`, `NO_EDGE`.

- [ ] **Step 1: Write initial WAIT gate test**

```python
from quant_dca.policy.engine import decide_initial


def test_wait_requires_probability_and_ev_gate():
    assert decide_initial(p_better_5d=0.61, net_wait_ev_5d=0.0049, confidence_ok=True).action != "WAIT"
    assert decide_initial(p_better_5d=0.61, net_wait_ev_5d=0.0051, confidence_ok=True).action == "WAIT"
```

- [ ] **Step 2: Add extension and hard-deadline tests**

Assert 20D extension requires 0.65 probability and 0.0075 incremental EV; assert twentieth subsequent eligible session forces execution.

- [ ] **Step 3: Add NO_EDGE fallback test**

At initial decision, `NO_EDGE` executes the baseline first-eligible monthly open. During an existing wait, it executes next eligible open.

- [ ] **Step 4: Implement policy engine and config validation**

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/policy/test_engine.py -v`

```bash
git add src/quant_dca/policy/engine.py configs/policy_v1.yaml tests/policy/test_engine.py
git commit -m "feat: implement constrained DCA timing policy"
```

### Task 9: Implement executable benchmarks

**Interfaces:**
- Produces benchmark paths B0-B5: Fixed DCA, Random DCA, Simple Dip, Trend/Dip heuristic, Always Buy Now, Oracle.

- [ ] **Step 1: Write same-cash/same-security fairness test**

```python
from quant_dca.backtest.benchmarks import benchmark_context


def test_benchmarks_share_security_cash_and_initial_date():
    ctx = benchmark_context("AMD", 5500.0, "2020-03-02")
    assert ctx.security_id == "AMD"
    assert ctx.contribution_huf == 5500.0
    assert ctx.initial_date == "2020-03-02"
```

- [ ] **Step 2: Write Random DCA reproducibility test**

Exactly 5,000 full-path simulations with persisted seeds.

- [ ] **Step 3: Write Oracle non-tradable separation test**

Oracle may calculate best future executable open but cannot feed any policy/model feature.

- [ ] **Step 4: Implement benchmarks and run tests**

Run: `pytest tests/backtest/test_benchmarks.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/quant_dca/backtest/benchmarks.py tests/backtest/test_benchmarks.py
git commit -m "feat: add fair executable DCA benchmarks"
```

### Task 10: Implement portfolio/execution simulator and cost scenarios

**Interfaces:**
- Produces executed acquisition costs under 0/10/25/50 bps scenarios, local and HUF basis.

- [ ] **Step 1: Write next-open execution test**

Signal generated from Tuesday EOD must never fill Tuesday close; first permissible fill is Wednesday eligible open.

- [ ] **Step 2: Write FX/dividend/cost accounting test**

Assert HUF acquisition cost includes timestamp-safe FX and foregone distribution economic adjustment exactly once.

- [ ] **Step 3: Implement simulator**

Use configured fractional-share/fee rules; keep model return targets independent from portfolio cash accounting.

- [ ] **Step 4: Run tests and commit**

Run: `pytest tests/backtest/test_execution.py -v`

```bash
git add src/quant_dca/backtest/execution.py src/quant_dca/backtest/simulator.py configs/cost_scenarios_v1.yaml tests/backtest/test_execution.py
git commit -m "feat: add realistic DCA execution simulator"
```

### Task 11: Implement metrics and cohort-level moving-block bootstrap

**Interfaces:**
- Produces EPI, hit rate, opportunity cost, regret, oracle capture, WAIT failure, forward returns, Brier/BSS, rank IC and 95% CI.

- [ ] **Step 1: Write EPI formula test**

```python
from quant_dca.metrics.timing import epi


def test_epi_positive_for_cheaper_model_entry():
    assert epi(benchmark_cost=100.0, model_cost=99.0) == 0.01
```

- [ ] **Step 2: Write cohort aggregation test**

Security rows are first equal-weighted within each calendar-month DCA cohort; the primary time series contains one mean EPI per month.

- [ ] **Step 3: Write bootstrap configuration test**

Default block length = 3 months, resamples = 10,000, fixed seed persisted in run metadata.

- [ ] **Step 4: Implement metrics and bootstrap**

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/metrics -v`

```bash
git add src/quant_dca/metrics tests/metrics
git commit -m "feat: add economic and probabilistic evaluation metrics"
```

### Task 12: Implement experiment ledger, run identity and research guardrails

**Interfaces:**
- Produces: immutable `RunManifest` and append-only experiment ledger rows.

- [ ] **Step 1: Write run reproducibility test**

```python
from quant_dca.experiments.run import make_run_id


def test_run_id_changes_when_feature_schema_changes():
    a = make_run_id("data1", "features1", "model1", 7)
    b = make_run_id("data1", "features2", "model1", 7)
    assert a != b
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/experiments/test_run.py -v`

- [ ] **Step 3: Implement required manifest fields**

Include `run_id`, `data_snapshot_hash`, `feature_schema_version`, `model_config_hash`, `code_version`, `random_seed`, `training_cutoff`, hypothesis, search space, result and decision. Create `configs/research_v1.yaml` to bind the approved development range, quarterly folds/refits, model-search config, policy config, cost scenarios and lockbox start date.

- [ ] **Step 4: Add lockbox-path access guard test**

Implement `src/quant_dca/tools/verify_lockbox_untouched.py` from the same access-log/guard contract. Research-mode code must raise if asked to load observations dated 2024-01-01 or later.

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/experiments -v`

```bash
git add src/quant_dca/experiments tests/experiments
git commit -m "feat: add reproducible experiment governance"
```

### Task 13: Run 2015-2023 development walk-forward research

**Files:**
- Create: `reports/development-oos-summary.md`
- Create: `reports/regime-model-comparison.csv`
- Create: `reports/model-target-comparison.csv`
- Create: `reports/calibration-summary.csv`
- Create: `reports/benchmark-summary.csv`
- Create: `reports/robustness-by-year-sector-region-regime.csv`
- Create: `reports/cost-stress.csv`
- Create: `reports/data-quality-sensitivity.csv`

- [ ] **Step 1: Execute only the predefined search spaces**

Implement `src/quant_dca/experiments/walk_forward.py` as the orchestration CLI over the fold generator, model selection, policy simulator, benchmark engine and experiment ledger, then run:

Run: `python -m quant_dca.experiments.walk_forward --config configs/research_v1.yaml --end 2023-12-31`

- [ ] **Step 2: Verify lockbox access log is empty**

Run: `python -m quant_dca.tools.verify_lockbox_untouched`

Expected: PASS and zero lockbox reads.

- [ ] **Step 3: Evaluate success/kill gates using development OOS only**

Report Fixed-DCA EPI, Simple-Dip increment, Oracle capture, WAIT value/failure, calibration/BSS, rank IC, year/regime/sector/region concentration and all four cost scenarios.

- [ ] **Step 4: Choose NetWaitEV estimator and champion models**

Freeze only choices justified by nested development OOS. If no NetWaitEV estimator is stable, disable WAIT for the affected horizon.

- [ ] **Step 5: Commit development evidence**

```bash
git add reports experiments configs
git commit -m "research: complete 2015-2023 development walk-forward"
```
