# Features, Targets & Regimes — subsystem checkpoint

Status: **SOFTWARE/PIT SUBSYSTEM PASS — ready for human checkpoint review**.
Updated: 2026-10-05. This is not a financial research report or frozen model configuration.

## Accepted task evidence

| Task | Implementation and corrections | Final independent review | Status |
|---|---|---|---|
|1 Registry/dependencies|5d8d3fc, 73c3daf|features-task1-fix-review.md|PASS|
|2 Price/volatility/liquidity|3e619c7, 557a84e|features-task2-fix-review.md|PASS|
|3 Historical relative features|8415bb8, 607c42e|features-task3-fix-review.md|PASS|
|4 Fundamentals/valuation|755b302, e789525|features-task4-fix-review.md|PASS|
|5 Macro/known events|9342d16, 5ab58af|features-task5-fix-review.md|PASS|
|6 Train-safe normalization|d4d45e9, 4ca82df|features-task6-fix-review.md|PASS|
|7 Isolated executable targets|2729520, 9db34ca, 024634e|features-task7-fix2-review.md|PASS|
|8 Interpretable regimes|0925763|features-task8-review.md|PASS|
|9 HMM/GMM candidate framework|152b68d, 48f03f3|features-task9-fix-review.md|PASS|
|10 Immutable integration/dictionaries|c6e8715, 02a61d8|features-task10-fix-review.md|PASS|

Final implementation commit: **41db8f6**, correcting the whole review's three cross-task findings. Fresh verification: **804 full-suite tests** (37.62s), **410 subsystem tests** (37.04s),126focusedtests; compileall and git diff --check passed. Independent `features-final-fix-review.md` closes all three findings with spec PASS / quality PASS and no new material breakage. Original FAIL findings and all correction evidence remain in reports/git history.

The final corrections cover canonical target-name exclusion in both imputer schemas, agreement between cross-sectional producer cohorts and snapshot universe lineage, and peer-calendar freshness of valuation prices. Valid missing peers and different-calendar prior closes remain accepted. These changes reinforce the frozen methodology and do not select a financial model.

## Research boundary

- Financial research runs: **0**. Financial/OOS model research: **not performed**.
- Synthetic numerical fits are software tests, not development financial evidence.
- Retrospective holdout: **NOT RUN**, and not pristine/blind. Historical access incidents remain documented; no claim that the whole project was untouched by excluded information.
- True forward lockbox: not started; begins only with genuinely new observations after final configuration freeze, with ex-ante predictions.
- No production/Codex handoff or final research configuration freeze.
- Real provider audit: **OPEN / INCOMPLETE**; no admitted actual development panel or real-panel leakage PASS.

## Known data-quality gaps

The retained provider audit (`development-panel-audit-followup.md`, qualified by `mnb-search-access-incident-2026-09-17.md`) reports narrow RAW_ONLY samples rather than an admitted dataset. Major missing evidence includes historical active/delisted US/EU universe, corporate-action and terminal economics, broad EU prices/fundamentals, execution-safe continuous FX, sector/index history and ex-ante event schedules. Macro vintage stitching, intraday availability, source units and licensing also remain admission obligations. Missing capabilities have not been relabeled as available Tier C data; unassigned source quality stays NULL.

The implementation review does not close these limitations. Financial research requires all four gates together: Tasks1–10 review PASS, actual PIT development panel, panel quality/admission report and real-panel leakage PASS.

## Implemented artifacts

- `feature-dictionary.csv`:94 definitions, comprising81 registered base outputs and13 explicitly reserved candidate regime slots. No research-selected state count.
- `target-dictionary.csv`:20 labels with execution, horizon, economic/FX and maturity definitions.
- All81 base outputs have actual typed producers; the complete integration fixture calls them and produces89 active columns with five interpretable and three GMM probabilities. Higher3–8candidate counts remain available without padding.
- Feature/target stores use separate immutable layers and content-bound source/configuration/lineage. Join identifiers are not predictor columns. Structural missing masks survive storage.
- Regime storage validates current, historical and training evidence at their proper cutoffs, carries model fit identity and preserves worst branch-specific evidence tier; passing hashes never assigns a provider tier.
- Target snapshots preserve independent per-horizon maturity and executable economic acquisition costs; later unavailable60D labels do not erase mature5D/20D labels.

## Reproduction

Verified Python3.12.14; required dependencies declared in `pyproject.toml`. In an isolated environment install `pip install -e '.[test]'`, then run:

```bash
python -m pytest -q
python -m pytest tests/features tests/targets tests/regimes -v
python -m compileall -q src tests
git diff --check
python -m quant_dca.dictionaries --output reports
```

The tests use synthetic development-date fixtures; these commands do not request market data. Numerical dependencies: NumPy2.2.6,SciPy1.15.3,scikit-learn1.7.2,hmmlearn0.3.3. The final archive will contain a complete git bundle plus committed source/reports. Reproduction hashes identify software, not a real-data experiment.

Dictionary SHA-256:

| Artifact | Rows | SHA-256 |
|---|---:|---|
|feature-dictionary.csv|94|9ae01f5b155b7639fd708462ca072f787f5c678e283544ade22f0e12d482292f|
|target-dictionary.csv|20|e6c120d28c6862dd30fe7a37dcb76076822d77ffaa5d237cb1b31cef3e47e9b8|

## Stop point and next gate

Keep `research/development-v1` intact for human review. The requested feature/target/regime software checkpoint is complete; this is not the final V1 research checkpoint. The next prerequisite is a real development panel with audited quality/admission and real-panel leakage PASS. Thirteen model/policy/validation plan tasks and the development evidence/freeze proposal remain after those prerequisites. No retrospective holdout or production handoff is authorized by this checkpoint.
