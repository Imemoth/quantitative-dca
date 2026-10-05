# Quant DCA Freeze, Lockbox & Reporting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze the V1 research configuration, prove the 2024-2026 lockbox has remained untouched, execute it exactly once, and produce an auditable PASS/FAIL/NARROW_EDGE decision package for the user and later production Codex work.

**Architecture:** Development artifacts are converted into a cryptographically hashed freeze manifest. Lockbox execution is a separate command that refuses to run without the matching freeze manifest and records a one-time evaluation receipt. Reporting reads only persisted predictions/backtest outputs and never retrains or tunes models.

**Tech Stack:** Python 3.12+, JSON/YAML, SHA-256, Parquet/DuckDB, Markdown/CSV reporting, pytest.

**Spec:** `docs/quant-dca-engine-v1-design-spec.md`

## Global Constraints

- Lockbox: 2024-01-01 through 2026-09-10 EOD.
- The lockbox is run once only after feature schema, model families, hyperparameter protocol, regime configuration, calibration method, NetWaitEV method, policy thresholds, benchmark definitions and success/kill criteria are frozen.
- If the lockbox fails, it cannot be reused as an untouched final test for a revised V2.
- Final recommendation must be exactly one of `PASS`, `FAIL`, `NARROW_EDGE` with evidence.
- `NARROW_EDGE` is reserved for a clearly defined stable subset such as a sector/region/regime, not for an ambiguous near-pass.

---

## File map

- Create: `src/quant_dca/freeze/manifest.py`, `guard.py`.
- Create: `src/quant_dca/lockbox/run.py`, `receipt.py`.
- Create: `src/quant_dca/reporting/final.py`.
- Create: `configs/frozen_v1.yaml` only after development research concludes.
- Create: `reports/freeze-manifest.json`, `reports/lockbox-receipt.json`, `reports/final-v1-report.md`, `reports/final-v1-metrics.csv`, `reports/codex-handoff-manifest.md`.

### Task 1: Build freeze manifest generator

**Interfaces:**
- Produces: `FreezeManifest` with hashes for data snapshot, feature schema, target schema, model/search protocol, regime config, calibration, policy, benchmarks, costs and source code commit.

- [ ] **Step 1: Write completeness test**

```python
from quant_dca.freeze.manifest import REQUIRED_FREEZE_KEYS


def test_freeze_manifest_covers_all_methodology_choices():
    required = {
        "data_snapshot_hash", "feature_schema_hash", "target_schema_hash",
        "model_protocol_hash", "regime_config_hash", "calibration_hash",
        "net_wait_ev_method", "policy_hash", "benchmark_hash",
        "success_kill_hash", "code_version"
    }
    assert required <= set(REQUIRED_FREEZE_KEYS)
```

- [ ] **Step 2: Verify failure**

Run: `pytest tests/freeze/test_manifest.py -v`

- [ ] **Step 3: Implement manifest creation and SHA-256 verification**

The command refuses configs containing unapproved model families, thresholds or post-2023 selection metrics.

- [ ] **Step 4: Run tests and commit**

Run: `pytest tests/freeze/test_manifest.py -v`

```bash
git add src/quant_dca/freeze tests/freeze
git commit -m "feat: add immutable V1 methodology freeze manifest"
```

### Task 2: Implement technical lockbox guard and one-time receipt

**Interfaces:**
- Produces: `assert_lockbox_access_allowed(mode, freeze_manifest)`, `LockboxReceipt`.

- [ ] **Step 1: Write pre-freeze denial test**

```python
import pytest
from quant_dca.freeze.guard import assert_lockbox_access_allowed


def test_lockbox_read_is_denied_without_valid_freeze():
    with pytest.raises(PermissionError, match="LOCKBOX_NOT_FROZEN"):
        assert_lockbox_access_allowed(mode="research", freeze_manifest=None)
```

- [ ] **Step 2: Write second-run denial test**

After a receipt exists for the same freeze hash and lockbox range, a second final run must fail unless explicitly labeled a non-final diagnostic that cannot alter the original conclusion.

- [ ] **Step 3: Implement guard and signed/hash receipt**

Receipt contains freeze hash, lockbox start/end, start/end timestamps, code version, data hash, run ID and output hashes.

- [ ] **Step 4: Run tests and commit**

Run: `pytest tests/freeze tests/lockbox -v`

```bash
git add src/quant_dca/freeze src/quant_dca/lockbox tests/lockbox
git commit -m "feat: protect one-time historical lockbox evaluation"
```

### Task 3: Freeze the development-selected V1 configuration

**Files:**
- Create: `configs/frozen_v1.yaml`
- Create: `reports/freeze-manifest.json`

- [ ] **Step 1: Generate frozen configuration only from 2015-2023 development evidence**

Include selected regime family/state count, champions per target, calibration methods, permitted ensemble weights if any, NetWaitEV estimator, WAIT availability by horizon, feature schema version and all policy thresholds.

- [ ] **Step 2: Generate and verify manifest**

Run: `python -m quant_dca.freeze.manifest --config configs/frozen_v1.yaml --out reports/freeze-manifest.json`

Run: `python -m quant_dca.freeze.manifest --verify reports/freeze-manifest.json`

Expected: PASS.

- [ ] **Step 3: Verify lockbox untouched before first read**

Run: `python -m quant_dca.tools.verify_lockbox_untouched`

Expected: PASS.

- [ ] **Step 4: Commit freeze before lockbox execution**

```bash
git add configs/frozen_v1.yaml reports/freeze-manifest.json
git commit -m "research: freeze Quant DCA V1 before lockbox"
```

### Task 4: Execute the lockbox exactly once

**Interfaces:**
- Consumes only frozen configuration and PIT observations available through 2026-09-10 EOD.
- Produces persisted predictions, executions, benchmarks, metrics and lockbox receipt.

- [ ] **Step 1: Run lockbox command**

Run: `python -m quant_dca.lockbox.run --freeze reports/freeze-manifest.json --start 2024-01-01 --end 2026-09-10`

- [ ] **Step 2: Verify no tuning artifacts were written**

The run may create predictions/backtests/reports only; it must not modify `configs/frozen_v1.yaml`, feature registry, model search space or policy thresholds.

- [ ] **Step 3: Verify receipt hashes**

Run: `python -m quant_dca.lockbox.receipt --verify reports/lockbox-receipt.json`

Expected: PASS.

- [ ] **Step 4: Commit immutable lockbox outputs**

```bash
git add reports/lockbox-receipt.json data/predictions data/backtest_results
git commit -m "research: record one-time V1 lockbox results"
```

### Task 5: Evaluate predefined PASS/FAIL/NARROW_EDGE criteria

**Interfaces:**
- Produces: deterministic `classify_result(metrics) -> PASS | FAIL | NARROW_EDGE` plus reason codes.

- [ ] **Step 1: Write primary PASS gate test**

```python
from quant_dca.reporting.final import classify_result


def test_nonpositive_fixed_dca_epi_is_fail():
    decision = classify_result({"net_epi_fixed": 0.0, "simple_dip_increment": 0.2})
    assert decision.status == "FAIL"
```

- [ ] **Step 2: Write narrow-edge test**

A positive aggregate driven almost entirely by one stable sector/regime should return `NARROW_EDGE`, not `PASS`.

- [ ] **Step 3: Implement criteria from spec**

Primary checks include >=0.50% net mean EPI versus Fixed DCA, bootstrap lower CI >0, +0.15% versus Simple Dip, positive NetTimingValue, BSS >0, stable rank IC if the return layer affects policy, time/regime/cross-sectional robustness and cost-stress survival.

- [ ] **Step 4: Run tests and commit**

Run: `pytest tests/reporting/test_final.py -v`

```bash
git add src/quant_dca/reporting tests/reporting
git commit -m "feat: classify V1 evidence against frozen gates"
```

### Task 6: Produce final auditable report

**Files:**
- Create: `reports/final-v1-report.md`
- Create: `reports/final-v1-metrics.csv`

- [ ] **Step 1: Generate report from persisted artifacts only**

Run: `python -m quant_dca.reporting.final --freeze reports/freeze-manifest.json --receipt reports/lockbox-receipt.json --out reports/final-v1-report.md`

- [ ] **Step 2: Report development and lockbox separately**

Required sections: data quality, universe limitations, selected regimes/models, calibration, development OOS, lockbox, benchmark table, WAIT behavior, costs, year/sector/region/regime robustness, Tier A/B vs AllData sensitivity, success/kill checklist, final status and reason codes.

- [ ] **Step 3: Verify report lineage**

Every headline metric must point to a run ID and persisted result file/hash.

- [ ] **Step 4: Commit**

```bash
git add reports/final-v1-report.md reports/final-v1-metrics.csv
git commit -m "docs: publish audited Quant DCA V1 conclusion"
```

### Task 7: Build Codex production handoff or kill memo

**Files:**
- Create: `reports/codex-handoff-manifest.md`

- [ ] **Step 1: Branch on final result**

If `FAIL`, state that no production implementation mandate exists and list the failed frozen gates without proposing rescue tuning against the spent lockbox.

If `NARROW_EDGE`, define the exact approved subset and explicitly prohibit representing it as a general DCA engine.

If `PASS`, include validated provider choices, canonical schemas, feature/target dictionaries, champion models, calibration, regime config, policy, benchmarks, success/kill criteria, research run IDs and lockbox conclusion.

- [ ] **Step 2: Run final full test suite**

Run: `pytest -q`

Expected: PASS.

- [ ] **Step 3: Commit final handoff**

```bash
git add reports/codex-handoff-manifest.md
git commit -m "docs: prepare Quant DCA production handoff"
```
