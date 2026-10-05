# Features Task 6 independent review

Date: 2026-09-17
Reviewed range: `293d776..d4d45e9`
Spec verdict: **FAIL**
Quality verdict: **FAIL — one important boundary omission**

## Finding

- **P2 — Canonical entity identity is accepted as a model feature.**
  `src/quant_dca/features/normalize.py:255–258` rejects selected identity tokens,
  but accepts `entity_id`. This is not an invented alias: the same module uses
  `FeatureValue.entity_id` as the security identity at lines 139–148. Therefore a
  caller passing a canonical feature-panel entity identifier as a categorical
  column can fit and retain direct security identity despite the required
  identity rejection boundary. A focused constructor diagnostic confirmed
  `FoldImputer(categorical_columns=("entity_id",))` succeeds, while `security_id`
  and `ticker` fail. Add the canonical entity identifier to the rejected identity
  names and cover it with a regression test. No need to redesign the schema or
  add broader feature research.

## Otherwise satisfied

- Rolling normalization uses actual inclusive trailing dependencies; tests
  mutate future and out-of-window observations and check literal values.
- Cross-sectional normalization requires historical `UniverseIndex` eligibility,
  a consistent feature and observation date, known vintages and canonical PIT
  validation; the result retains selected records and cohort security evidence.
- Imputation has an explicit fold role and aware boundary contract, fit-once
  training statistics, copied public statistics, evaluation overlap rejection,
  preserved structural missingness and optional native missing handling.
- Bare whole-table frames cannot enter fit/transform. No global storage write
  or empirical normalization/model choice was introduced.

## Review scope and evidence

Read the exact Task 6 brief, Features plan preflight, implementation report and
supplied one-range diff. Inspected the directly invoked canonical PIT helper to
check its timestamp guarantees. Accepted the reported 14 focused and 495 full
passing tests as execution evidence; did not rerun either suite. Ran only the
small identity-constructor diagnostic described above. No network, git mutation,
financial experiments or source/test edits were performed.

Later label maturity, purging and embargo remain model-subproject responsibilities
and are not findings against this feature-preprocessing task.
