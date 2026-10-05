# Features Task 6 implementation

Date: 2026-09-17
Scope: rolling and historical cross-sectional normalization; fold-local imputation
Status: implementation complete; pending independent review

## Implemented contract

- `rolling_zscore(series, window)` uses only the inclusive trailing window,
  requires a complete finite window, and uses sample standard deviation. Missing
  or zero-dispersion windows remain missing.
- `CrossSectionNormalizer` supports the explicitly selected `percentile` and
  `zscore` representations. Its production boundary requires canonical
  `FeatureValue` records, an aware historical cutoff and prediction timestamp,
  an explicit region, and a real `UniverseIndex`.
- `CrossSectionSnapshot` retains the normalized values, selected input vintages,
  historically eligible security records, eligible identifiers, cutoff,
  prediction timestamp, and method. The result is therefore auditable PIT
  evidence rather than a claim made over an unevidenced scalar array.
- `FoldImputer.fit(train).transform(data)` accepts only `FoldPartition` objects.
  A partition declares fold identity, role, aware time bounds, feature-only
  data, and an aligned structural-missing mask.

## Leakage and missing-data decisions

- Rolling tests use literal hand-calculated results and mutate both a future
  value and history outside the active window. They do not establish causality
  merely by slicing the future row away before both calls.
- Cross-sectional eligibility is reconstructed at the historical cutoff. A
  future member with an extreme value cannot affect the historical result.
  Within each eligible entity, only a vintage known by the cutoff is selected;
  each selected input must also pass the canonical PIT guard.
- Cross-sectional sample z-scores and percentile tie handling are deterministic.
  A singleton percentile is `0.5`; absent/non-finite values and zero-dispersion
  z-scores remain missing.
- `FoldImputer` fits exactly once and only when `role == train`. Transformations
  hard-fail on a different fold, overlapping evaluation boundary, or mismatched
  training boundary. OOS values cannot update fitted statistics.
- Numeric median and categorical most-frequent imputation are separate,
  explicitly configured strategies. Deterministic lexical ordering resolves a
  categorical frequency tie. Either strategy may be `None`, preserving native
  missing handling for downstream models.
- Structural missing cells remain missing during transform. Ordinary missing
  cells may be filled from training-only statistics; all-missing training
  columns retain `None` statistics and therefore remain missing.
- The imputer accepts only its declared feature schema. Direct security identity
  and Task 7 target/label/outcome names are rejected. Registered feature names
  such as `return_5d_raw` remain distinct from the forbidden target `return_5d`.
- There is no whole-table fit or implicit partition path. Passing a bare data
  frame to `fit` or `transform` fails rather than globally imputing a stored
  feature table.

## TDD and verification evidence

The runtime initially lacked test extras, so the allowed local command
`python -m pip install -e '.[test]'` restored them. The first collected RED was:

```text
python -m pytest tests/features/test_normalize.py -v
ModuleNotFoundError: No module named 'quant_dca.features.normalize'
```

After the first implementation, the focused suite passed 13 tests. Mutation
review then added the exact Task 7 name `return_5d`; it failed because only
generic `target_*` names were rejected:

```text
Failed: DID NOT RAISE ValueError
1 failed, 13 passed
```

The narrow target-boundary fix produced:

```text
python -m pytest tests/features/test_normalize.py -q
14 passed in 1.09s
```

Final verification:

```text
git diff --check
python -m compileall -q src/quant_dca/features/normalize.py tests/features/test_normalize.py
python -m pytest -q
495 passed in 8.56s
```

## Limits and research status

- All tests use synthetic fixtures. They demonstrate software boundaries, not
  provider coverage, empirical distribution quality, or financial usefulness.
- No provider/network data, actual development panel, 2024+ holdout, model fit,
  backtest, OOS evaluation, or regime/target research was accessed or run.
- This task does not choose whether a model family should impute, choose a
  normalization method from results, add missing indicators, or select an
  empirical threshold. Those remain explicit frozen configuration/research
  decisions outside this utility layer.
- The fold partition describes feature preprocessing boundaries only. Label
  maturity, purging, and embargo are owned by later training-set construction;
  this task neither implements nor weakens those contracts.

## Fix round 1 — canonical entity identity

Accepted the independent review's P2 finding that `entity_id`, the canonical
security identity used by `FeatureValue`, passed the imputer schema boundary.
The root cause was a single omission: normalization's compact identity set did
not include `entityid`, although the existing registry identity contract already
recognizes that exact canonical name.

Regression coverage exercises both constructor paths. Before the fix,
`entity_id` was admitted as either numeric or categorical:

```text
python -m pytest tests/features/test_normalize.py -q
2 failed, 14 passed
```

The implementation adds only `entityid` to the existing normalization identity
set. It does not add aliases, change the feature schema, or broaden model/data
work. Focused GREEN:

```text
python -m pytest tests/features/test_normalize.py -q
16 passed in 1.08s
```

Fix-round verification:

```text
git diff --check
python -m compileall -q src/quant_dca/features/normalize.py tests/features/test_normalize.py
python -m pytest -q
497 passed in 8.34s
```
