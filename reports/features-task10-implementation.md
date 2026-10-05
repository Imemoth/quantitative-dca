# Task 10 implementation — immutable integration and dictionaries

Status: implementation complete, controller independent review pending. This report does not mark the subsystem or research gates PASS. Base: `2d993a55bf219e177a3b132660259f9f103c4269` on `research/development-v1`. Synthetic software fixtures only; financial/OOS research runs: **0**. No raw/provider data was read and no provider request was made. Existing untracked raw and fixture-snapshot paths were neither read nor staged.

## Delivered interfaces and coverage

- `quant_dca.features.snapshots.build_feature_snapshot(as_of, registry_version, *, ...)` accepts seven exact typed producer bundles and content-bound historical universe evidence. Every registered output is required exactly once. Source references must verify as Foundation immutable canonical/PIT snapshots and have the exact serialized producer evidence, outputs, masks and configuration. Selected evidence clocks are checked separately from the hash.
- `quant_dca.targets.store.build_target_store(start, end, *, ...)` calls the existing Task 7 economic target builder using explicit materialized inputs and FX quotes. It writes 20 target rows per signal in the physically separate `targets` layer. Each horizon retains its own maturity, censor reason and full economic evidence. A censored 60D label does not suppress mature 5D/20D labels.
- `quant_dca.regimes.integration.build_regime_features(...)` calls Task 9 prediction on a fitted candidate and combines its outputs with a PIT-validated Task 8 result. It binds fold, region, calendar, fit identity/fingerprint, training evidence, model configuration, sequence policy, parameter scope and exact branch inputs. Fit-end must be no later than prediction; the complete fixture uses inner validation strictly after synthetic training.
- `python -m quant_dca.dictionaries --output reports` deterministically generates both committed CSV dictionaries without data access.

| Producer | Registered outputs | Implementation basis |
|---|---:|---|
| `PriceFeatureSnapshot` | 22 | Existing adjusted trailing price, volatility/drawdown and USD liquidity calculations |
| `RelativeFeatureSnapshot` | 8 | Existing historical eligible cross section and sector/market relative returns |
| `FundamentalFeatureSnapshot` | 12 | Existing published fundamental vintages and applicability masks |
| `ValuationFeatureSnapshot` | 10 | Existing compatible-share valuation, eligible sector ranks and causal own-history transforms |
| `MacroFeatureSnapshot` | 13 | Existing region/jurisdiction macro producer; now retains actual prior-vintage dependencies and explicit series map |
| `EventFeatureSnapshot` | 6 | Existing announced-calendar producer |
| `MarketStructuralSnapshot` | 10 | New six market-context and four structural producers described below |
| **Total non-regime** | **81** | No count-padding or dummy columns |

The feature dictionary has **94** rows: 81 registered base outputs and **13 reserved candidate slots** (five interpretable plus eight maximum unsupervised slots). Reserved dictionary entries do not assert active features. The complete integration fixture has **89 active columns**: 81 + 5 + a three-state GMM candidate. No arbitrary padding to eight states, no chosen research winner, no retained state count claim. Base-only snapshots are explicitly marked `base_only_incomplete_regime_integration`.

The target dictionary has **20** named labels. It records O0 reference, O5/O20/O60 exits, O0..O4/O19 wait windows, fixed 1.5%/3% better-entry thresholds inherited from Task 7, gross economic adjustment, local/HUF cashflow basis and per-horizon maturity. Wait-label maturity accurately preserves Task 7's requirement for the horizon's O5/O20 evidence as well.

## Controller-approved candidate choices

These are transparent versioned software choices, not empirically selected or final research configuration:

- Region codes US=0, EU=1. Sector codes are explicit caller mappings over controlled economic sector names; arbitrary identifiers and implicit identity encoding are rejected.
- USD market-cap boundaries: 2bn, 10bn, 200bn; equality enters the upper bucket. The producer requires unadjusted close with matching unadjusted reported share units, matching listing currency/region/calendar, and known spot FX when conversion is required. Missing FX remains missing. The registry dependency clarification replaces generic adjusted price history with unadjusted close, historical currency and FX dependencies; no new feature was added.
- Beta boundaries: 0.8 and 1.2; equality enters the upper bucket. Beta is covariance/variance of exactly 252 daily adjusted returns from 253 matching actual sessions. Missing/misaligned history and zero market variance remain missing. The existing Task 2 computed adjusted-close path is retained in its snapshot and reused; corporate-action arithmetic was not reimplemented.
- Market/sector momentum reuses Task 2's 20D/60D outputs. Explicit region, benchmark identity, source and calendar bindings are checked against the actual producer evidence; historical sector assignment is PIT-selected.
- VIX acceleration is `(Vt - Vt-20) - (Vt-20 - Vt-40)` in index points, with the registered 43-session minimum retained. Level uses the latest knowable source close; acceleration remains missing without a complete actual source-session window. Source, calendar, region and units are explicit.
- Target security admission here is US XNYS/XNAS or EU XETR/XPAR. XLON calendar capability does not admit UK securities. No benchmark was selected empirically.

## Architecture and leakage evidence

Requests, development bounds (2010–2023) and roles (train/validation only) are checked before lazy inputs, source reads or numeric consumption. Per-target signal bounds are checked across the request batch before histories or FX resolution. Materialized evidence is required at the integration boundary. Canonical source metadata and supplied records are content-bound; future selected input clocks cannot be hidden behind earlier feature metadata.

Historical universe inputs are stored as separate immutable evidence and reconstructed through `UniverseIndex` at the feature/signal EOD. A removed member with a later unavailable reinstatement stays ineligible. Feature long rows contain administrative `entity_id` only for joins; `predictors` contains solely the exact registered/active feature names. Join keys and structural missing masks are separate. No ticker or target column is added to predictors. The existing architecture test continues to reject feature imports of the target pipeline.

The same-signal end-to-end fixture builds feature and target snapshots with the same entity/time metadata, verifies all feature clocks at or before signal, baseline open strictly after signal, and separate immutable storage layers. All seven base producers are actually called. Missing consensus, history and unannounced events retain the existing producer missing semantics, and financial-sector structural masks survive serialization.

Regime training diagnostic probabilities are not relabelled as earlier ex-ante predictor values. The stored candidate retains `full_training_partition_not_walk_forward` and reset sequence policy, plus fit identity. The completed fixture is a later validation prediction; future fit, different fold, different inputs and unevidenced heuristic output are rejected.

## TDD and verification evidence

Runtime restoration: the prescribed venv Python launcher had disappeared. Recreated the venv and installed declared `.[test]` dependencies. Installation reported pre-existing invalid-distribution remnants in that environment; test output itself is clean.

RED/GREEN progression, using `/workspace/scratch/616ad772b2da/quant-dca-test-env/bin/python`:

| Stage / test command | RED observed | GREEN evidence |
|---|---|---|
| `-m pytest tests/features/test_market_structural.py -q` | Initial four failures: market/structural producer absent | First four literal producer/PIT tests passed |
| `-m pytest tests/features/test_snapshots.py -q` (later renamed `test_feature_integration.py`) | Four failures: integration interface absent | Four base snapshot/mask/hash/guard tests passed |
| Same integration module, regime tests | Two failures: regime integration absent | Six integration tests passed, including 89-column fixture |
| `-m pytest tests/targets/test_store.py -q` | Three failures: target store absent | Three target tests passed |
| `-m pytest tests/features/test_dictionaries.py -q` | Generator absent | Deterministic generator and subprocess CLI passed |
| Market/structural edge tests | Literal failures for unrelated VIX degrading cap quality, missing latest VIX fallback, and unenforced benchmark raw source | Per-dependency quality, latest known source close, source binding passed |
| Feature evidence clock test | Future raw bar accepted despite old derived clocks | Selected-evidence PIT guard rejects it |
| `-m pytest tests/features/test_macro_events.py -q` | Prior macro observation lost from returned lineage | Actual prior dependencies and series map retained; 14 passed |
| Price evidence config test | Changing FX max-age left evidence hash unchanged | Price and new structural evidence bind FX max-age |
| Cap dependency test | Compatible split-adjusted price silently accepted despite unadjusted registry declaration | Unadjusted cap dependency enforced |

First full repository run exposed a test-module basename collision with existing `tests/storage/test_snapshots.py`. Renamed the new feature integration module; no production workaround or test suppression. Subsequent full suites passed (719, then 720 as final edge tests were added). The final same-signal integration test also passed in its focused run (10 integration tests).

Final verification commands and exact results are recorded in the task report alongside the commit. No required suite failure is omitted. The required subsystem command is `-m pytest tests/features tests/targets tests/regimes -v`; full repository command is `-m pytest -q`; bytecode check is `-m compileall -q src tests`; whitespace check is `git diff --check` (also checked for staged files).

## Limitations and review boundary

Immutable hashes and explicit source/unit/tier declarations establish evidence identity and software validation only. They do **not** prove actual provider vintage truth, source units, audited quality tiers, panel admission, corporate-action completeness, regional benchmark suitability or real-data coverage. Such evidence must be audited upstream. This integration accepts staged typed producer outputs; it is not a new provider ingestion facade and does not fetch missing data.

Source objects include declared complete selected evidence, including previously omitted macro priors and price/structural FX staleness configuration. All actual economic calculations remain in the existing producers or the ten explicitly required new outputs. No imputer fitting, new normalization selection, OOS selection, deployment or research freeze occurred.

Tasks 1–9 reviewed baseline is inherited from controller checkpoint `2d993a5`; Task 9 implementation/integrity commits are `152b68d` / `48f03f3`. The controller owns the final cross-task commit/review inventory, independent Task 10 review, parent status files and subsystem checkpoint. This task does not modify or certify those files.


## Final verified result

- `/workspace/scratch/616ad772b2da/quant-dca-test-env/bin/python -m pytest tests/features tests/targets tests/regimes -v`: **327 passed in 18.68s**.
- `/workspace/scratch/616ad772b2da/quant-dca-test-env/bin/python -m pytest -q`: **721 passed in 20.26s** (695 baseline + 26 added tests), output clean.
- `/workspace/scratch/616ad772b2da/quant-dca-test-env/bin/python -m compileall -q src tests`: exit 0.
- `git diff --check` and `git diff --cached --check`: exit 0, no whitespace errors.
- Dictionary generation: `/workspace/scratch/616ad772b2da/quant-dca-test-env/bin/python -m quant_dca.dictionaries --output reports`; generated CSVs committed. Determinism and CLI invocation verified in tests.
- Self-review completed; no known software blocker. Remaining limitations are the explicit upstream real-data/provider-admission and research-selection gates, not claims of completed research.

Task-owned files: `configs/features_v1.yaml`; `src/quant_dca/{snapshot_contracts,dictionaries}.py`; `src/quant_dca/features/{history,macro,market_structural,snapshots}.py`; `src/quant_dca/regimes/integration.py`; `src/quant_dca/targets/store.py`; `tests/features/{test_macro_events,test_market_structural,test_feature_integration,test_dictionaries}.py`; `tests/targets/test_store.py`; both dictionary CSVs and this durable implementation report. The requested `.superpowers/.../task-10-report.md` is also written, but remains in the repository's ignored local workflow area consistent with its gitignore rule.


## Task 10 fix round 1 — R1 regime chronology and R2 composite quality

Controller accepted independent review R1 and added R2 in `reports/features-task10-review.md`. Both are addressed narrowly; independent re-review remains pending.

**R1:** Construction no longer trusts `pit_validated` as sufficient proof. The adapter reapplies Task 8's canonical metadata validator to interpreted current/prior evidence and Task 9 training evidence at each original row `as_of` inside the fit bounds. Current and historical cutoffs remain exactly the inherited current/prior benchmark EODs; this is not a new vintage-selection policy. Prediction evidence is independently checked, including during staged snapshot admission. The feature snapshot entry point performs staged regime preflight before universe/source reads, and the append boundary rechecks it before immutable source verification. Checks cover actual `available_at`, `published_at`, `revised_at`, `max_input_available_at`, row as-of/observations, schema, quality and provenance. Output max-input and availability conservatively incorporate all actual dependency clocks, with fit-end included for unsupervised outputs.

**R2:** Removed hardcoded B. Each interpretable probability inherits the worst selected current/historical input tier. Each unsupervised probability inherits the worst current/model-training input tier. Unrelated training C therefore does not degrade the independent heuristic branch, while no C dependency is promoted into A/B output eligibility. Unknown/invalid tiers fail through the canonical validator before source reads. The generated regime dictionary now records composite floor C and explicitly describes the branch-specific dependency policy plus the existing high-yield-spread minimum B input requirement. No provider tier is inferred or upgraded.

**RED evidence:** `python -m pytest tests/features/test_feature_integration.py -q` produced **37 failed, 10 passed in 23.82s** before fixes. Failures covered four clocks across current/historical/training construction and staged prediction branches, the reviewer's future historical availability with a valid content-bound source, unknown tiers, all three C-tier dependency locations, A/B exclusion after Parquet serialization, and max-input aggregation. `python -m pytest tests/features/test_dictionaries.py -q` separately failed because reserved regime rows still declared B rather than C.

**Focused GREEN:** the combined feature-integration and dictionary command passed **48 tests in 23.07s**. All numeric predictions still use the existing Task 8/9 machinery; no state choice, feature count, target arithmetic, thresholds or other research configuration changed.

Prescribed runtime launcher disappeared again and was restored with the declared `.[test]` dependencies. Changes are limited to regime integration, the feature-store metadata preflight, dictionary generator/CSV, focused tests and appended reports. Parent status/ledger/manifest/checkpoint/review files remain excluded. Actual provider data/network reads and financial/OOS runs remain **0**.

**Fix-round final verification:**

- `/workspace/scratch/616ad772b2da/quant-dca-test-env/bin/python -m pytest tests/features tests/targets tests/regimes -v`: **364 passed in 34.46s**.
- `/workspace/scratch/616ad772b2da/quant-dca-test-env/bin/python -m pytest -q`: **758 passed in 35.68s**, clean output.
- `/workspace/scratch/616ad772b2da/quant-dca-test-env/bin/python -m compileall -q src tests`: exit 0.
- `git diff --check` and scoped `git diff --cached --check`: exit 0.
- `/workspace/scratch/616ad772b2da/quant-dca-test-env/bin/python -m quant_dca.dictionaries --output reports`: exit 0; only the 13 reserved regime rows changed, preserving 81 base definitions and all 20 target definitions.

Self-review: branch-specific clocks and tiers remain independent, validation occurs before staged source access, and the focused diff contains no unrelated changes. Both R1 and R2 are ready for the controller's scoped independent re-review; no subsystem PASS claim is made.
