# Work Handoff Prompt — Quant Equity Probability & DCA Engine V1

You are the research/build lead for **Quant Equity Probability & DCA Engine V1**.

## Authoritative inputs

Read these files completely before taking action:

1. `docs/quant-dca-engine-v1-design-spec.md` — **authoritative methodology/design specification**.
2. `docs/superpowers/plans/2026-09-11-quant-dca-master-roadmap.md` — execution order and phase gates.
3. The four subproject plans under `docs/superpowers/plans/` — exact implementation/research tasks.

The design specification is frozen for V1. Do not silently redesign the investment methodology. If an implementation detail is impossible because of an actual provider/data limitation, record the limitation, classify its data-quality impact, and use the narrowest substitution consistent with the spec.

## Mission

Build and research the V1 prototype through the **2015-2023 development OOS stage**, following the plans and automated tests. Do **not** inspect, summarize, graph, tune on, or otherwise use the **2024-01-01 through 2026-09-10 lockbox** until every V1 research choice is frozen and the lockbox phase explicitly begins.

## Operating rules

- Preserve point-in-time truth. `feature.available_at > prediction_timestamp` is a hard failure.
- EOD signals execute no earlier than the next eligible session open.
- Better-entry targets use executable future opens and economic acquisition cost; never use future intraday lows as fills.
- Use free/low-cost data first. Build provider adapters so vendors can be replaced later.
- Maintain A/B/C data-quality tiers and report results both for A/B-only evidence and all permitted data.
- Keep features and targets physically/logically separate.
- No deep learning, unrestricted AutoML, direct ticker identity, intraday optimization, stock-selection optimization, derivatives or multi-month timing carry-over in V1.
- Use TDD and commit/review at each plan task boundary.
- Maintain the experiment ledger for every model/feature/policy research experiment.
- Complexity must earn its place. When simple and complex methods are economically equivalent OOS, select the simpler method.
- Do not buy institutional datasets merely to improve convenience. Escalate only when a specific data-quality limitation blocks a decision that already shows credible development evidence.

## Required development deliverables before lockbox

Produce and make reviewable:

1. audited data-source inventory and quality-tier map;
2. historical universe reconstruction report;
3. canonical PIT schema and leakage test evidence;
4. feature dictionary and target dictionary;
5. regime comparison including 3-8 unsupervised states;
6. baseline/challenger comparison for each prediction target;
7. probability calibration report;
8. quarterly nested expanding walk-forward results for 2015-2023;
9. benchmark comparison against Fixed DCA, Random DCA, Simple Dip, Trend/Dip, Buy Now and Oracle;
10. year/sector/region/regime robustness analysis;
11. 0/10/25/50 bps cost stress;
12. A/B quality versus AllData sensitivity;
13. selected NetWaitEV method or documented WAIT disablement;
14. proposed frozen V1 configuration;
15. proof that the final lockbox has not been accessed.

## Stop point

Stop after the development evidence and proposed frozen configuration are complete. Return the reports/artifacts for human review before the lockbox is executed.

Do not move to production Codex architecture. The later Codex handoff is created only after development review, configuration freeze and one-time lockbox evaluation.
