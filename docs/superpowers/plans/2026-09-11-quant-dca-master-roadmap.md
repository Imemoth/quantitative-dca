# Quant DCA Engine V1 Master Roadmap

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement each sub-plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a research-grade, point-in-time-correct Quant Equity Probability & DCA Engine V1 prototype whose timing edge can be evaluated without leakage and whose final 2024-2026 lockbox remains untouched until configuration freeze.

**Architecture:** The work is decomposed into four independently reviewable subprojects. Each subproject must pass its own tests and produce immutable artifacts consumed by the next one; no downstream phase may silently repair upstream data or methodology.

**Tech Stack:** Python 3.12+, Parquet, DuckDB, PyArrow/Pandas, scikit-learn, XGBoost-compatible gradient boosting, hmmlearn-compatible HMM, pytest, YAML/JSON configuration, Markdown reports.

**Spec:** `docs/quant-dca-engine-v1-design-spec.md`

## Global Constraints

- Markets: USA + European Union primary-listed liquid common equities.
- Historical raw data starts in 2010.
- Warm-up/training starts 2010-01-01; development OOS is 2015-01-01 through 2023-12-31.
- Final lockbox is 2024-01-01 through 2026-09-10 EOD and must remain unread by model/feature/policy selection code before freeze.
- Daily/EOD only; signal at EOD t executes no earlier than the next eligible session open.
- Horizons are exactly 5D, 20D, 60D; no 10D target in V1.
- Better-entry thresholds are 1.5% for 5D and 3.0% for 20D, measured on executable economically adjusted acquisition cost.
- Default investor base currency is HUF; local-currency diagnostics are retained.
- Deep learning, unrestricted AutoML, ticker identity, intraday execution optimization, stock-selection optimization and multi-month cash carry-over are excluded from V1.
- `NO_EDGE` always falls back to baseline DCA; it never means indefinite cash.
- Any `feature.available_at > prediction_timestamp` is a hard failure.
- Complexity must beat its simpler baseline by the predefined OOS economic hurdle or the simpler method wins.

---

## Subproject order

1. **Data & PIT Foundation** — canonical schemas, exchange calendars, provider adapters, as-of semantics, universe reconstruction, quality tiers, corporate actions, FX, immutable snapshots.
   - Plan: `docs/superpowers/plans/2026-09-11-quant-dca-data-pit-foundation.md`
   - Exit artifact: point-in-time-safe canonical datasets plus audit report.

2. **Features, Targets & Regimes** — 80-95 feature architecture, cross-sectional/rolling normalization, executable-price targets, interpretable regime branch, HMM/GMM challenger branch.
   - Plan: `docs/superpowers/plans/2026-09-11-quant-dca-features-targets-regimes.md`
   - Exit artifact: frozen feature/target dictionaries and reproducible training-table builder.

3. **Models, Policy & Validation** — nested expanding walk-forward, purging/embargo, champion/challenger models, calibration, NetWaitEV, DCA actions, benchmarks and evaluation metrics.
   - Plan: `docs/superpowers/plans/2026-09-11-quant-dca-model-policy-validation.md`
   - Exit artifact: 2015-2023 development OOS evidence and candidate frozen V1 configuration.

4. **Freeze, Lockbox & Reporting** — configuration freeze, technical lockbox guard, one-time 2024-2026 evaluation, PASS/FAIL/NARROW_EDGE report and Codex handoff package.
   - Plan: `docs/superpowers/plans/2026-09-11-quant-dca-freeze-lockbox-reporting.md`
   - Exit artifact: final historical conclusion and production implementation mandate or kill decision.

## Phase gates

- [ ] Do not start Subproject 2 until Subproject 1 PIT/leakage tests pass.
- [ ] Do not start model selection until the feature and target dictionaries are version-frozen for that research run.
- [ ] Do not inspect lockbox metrics while development decisions remain open.
- [ ] Do not purchase institutional data before V1 passes the evidence gates with free/low-cost data or demonstrates a specific data-quality blocker worth funding.
- [ ] Do not hand the project to production Codex implementation unless the final result is `PASS` or a deliberately scoped `NARROW_EDGE` that the user explicitly chooses to pursue.
