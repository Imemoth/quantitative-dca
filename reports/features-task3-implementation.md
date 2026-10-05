# Features Task 3 implementation

## Scope and status

Implemented the eight frozen V1 relative-strength outputs in `src/quant_dca/features/relative.py`, with focused coverage in `tests/features/test_relative.py`. The feature registry, Foundation contracts, controller ledger, and status files were not changed. No market/network data requests, raw-data work, holdout/OOS evaluation, model research, or Task 4 work was performed.

## Interfaces and conventions

- `percentile_in_universe(security_id, values, eligible)` retains the brief's public signature. It ranks only finite, explicitly eligible values. The deterministic convention is average zero-based positional rank divided by `n - 1`; ties share their average position, a singleton is `0.5`, and ineligible/missing/non-finite targets are missing.
- `compute_relative_features` is a pure helper implementing the registry formulas: stock return minus sector benchmark return and stock return minus regional broad-market return at 20/60/120 sessions, plus sector and universe 120-session momentum percentiles. Missing operands remain missing.
- `build_relative_features` is the evidenced Task 10-facing boundary. It requires an explicit `UniverseIndex`, canonical `FeatureValue` return inputs, and versioned `SectorClassification` records. It emits the eight registered relative-strength `FeatureValue` records plus a `RelativeFeatureSnapshot` retaining selected inputs, classifications, and historical eligible IDs.
- The target exchange calendar comes from supplied historical stock feature metadata. `UniverseIndex` is queried only at the resulting historical feature EOD, never at a current/prediction-time membership fallback. This preserves securities that delist after the historical cutoff and excludes securities that join later.
- Sector classifications use start-inclusive/end-exclusive intervals and only versions available at the historical feature EOD. Overlapping active classifications fail closed. A missing target classification preserves all sector-relative outputs as missing. The supplied sector benchmark entity must match the target's historical sector ID.
- Future-unavailable feature/classification versions are filtered before vintage selection. Every selected `FeatureValue` passes the canonical PIT guard; `available_at` and `max_input_available_at` must also be no later than the historical feature EOD. Output clocks conservatively cover selected features, classifications, and eligible security versions.
- Output quality is the worst selected canonical tier. The snapshot preserves exact provenance-bearing inputs; entity/security IDs remain grouping metadata and are never emitted as numeric model features.

## TDD evidence

The environment initially lacked the declared test extra:

```text
$ python -m pytest tests/features/test_relative.py -v
/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python: No module named pytest
```

`python -m pip install -e '.[test]'` completed successfully. The intended initial RED then failed because the new production module did not exist:

```text
$ python -m pytest tests/features/test_relative.py -v
E   ModuleNotFoundError: No module named 'quant_dca.features.relative'
```

After the first GREEN, a mutation review added a regression proving that prediction-time/current membership cannot replace historical feature-EOD eligibility. It failed with `INELIGIBLE_SECURITY_AT_PREDICTION`, then passed after exchange-calendar resolution was moved to historical stock feature metadata. A separate benchmark-classification regression first failed because a mismatched sector benchmark was accepted, then passed after fail-closed entity validation.

Final focused GREEN:

```text
$ python -m pytest tests/features/test_relative.py -q
9 passed in 1.41s
```

Focused covering integration:

```text
$ python -m pytest tests/features/test_relative.py tests/features/test_registry.py tests/features/test_price_vol_liquidity.py tests/universe/test_membership.py tests/point_in_time/test_asof.py -q
103 passed in 4.98s
```

Required single full-suite run after implementation:

```text
$ python -m pytest -q
446 passed in 6.24s
```

`python -m compileall -q src/quant_dca/features/relative.py tests/features/test_relative.py` and `git diff --check` exited 0.

## Self-review and limits

Tests use literal hand-derived ranks and returns, including deterministic ties/singletons/missing values, a later-delisted historical member, a future member with an extreme value, future value and classification revisions, missing historical classification, worst-quality propagation, future-derived input clocks, and mismatched sector benchmark identity. No expected rank is computed with the implementation under test.

The builder consumes already constructed `UniverseIndex` and canonical return features; it does not discover memberships, sector mappings, or benchmark series. Eligibility-evidence completeness remains the responsibility of `UniverseIndex`, and benchmark construction remains outside this task. Percentile convention is explicitly frozen here because the registry names the transformation but does not prescribe a library-specific rank implementation. No empirical feature selection or normalization is introduced.

## Independent review correction round 1

Accepted both Important findings in `reports/features-task3-review.md` and limited the correction to the historical cutoff and direct-input contracts.

- The historical feature cutoff is now the actual `eligible_session_close` for the aligned stock-return `observation_date`, not the most recent EOD before prediction. Stock observation dates must align, parse as ISO dates, identify a real exchange session, and not lie after prediction. `UniverseIndex`, cross-sectional vintages, and sector classifications all use that exact observation EOD. A stale Friday snapshot evaluated after Monday close therefore retains a constituent delisted Monday, excludes a Monday joiner, and uses the Friday-effective classification.
- Stock, sector-benchmark, and market-benchmark mappings are direct selected inputs, not vintage pools. Every supplied row now passes canonical PIT/provenance/value validation and must have both availability clocks no later than the historical feature EOD. Missing mappings/horizons may preserve missing outputs, but a supplied future-available row hard-fails. Cross-sectional returns and classifications remain vintage pools: genuinely unavailable future candidates are filtered before selection, preserving the original future-mutation invariance contract.

Focused RED before the production correction:

```text
$ python -m pytest tests/features/test_relative.py -q
5 failed, 9 passed in 1.72s
```

The failures showed the later-delisted name missing from the stale Friday universe, no exception for a future-available direct row in each of the three mapping roles, and a weekend observation reaching benchmark alignment instead of calendar rejection.

Final focused GREEN and the required single full-suite run:

```text
$ python -m pytest tests/features/test_relative.py -q
14 passed in 1.49s

$ python -m pytest -q
451 passed in 6.04s
```

`python -m compileall -q src/quant_dca/features/relative.py tests/features/test_relative.py` and the final staged diff check exited 0. No network/data research, holdout/OOS work, controller/status edits, or Task 4 work occurred.
