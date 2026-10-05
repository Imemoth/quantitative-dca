# Task 10 implementation — PIT foundation audit artifact

## Implementation

`quant_dca.tools.build_fixture_snapshot` is a thin, offline CLI over the
existing services. It passes fixed synthetic observations through
`validate_observations`, selects the knowable vintage with `latest_known`,
writes a canonical snapshot, then writes a feature snapshot with
`FeatureLineage` bound to the canonical snapshot. It performs no network or
provider request and contains no observation or event after 2023.

The CLI emits one sorted compact JSON object. It distinguishes the
metadata-bound `snapshot_sha256` from the table-only `data_sha256` and labels
the fixture `SYNTHETIC_NOT_RESEARCH_EVIDENCE`.

## TDD evidence

The focused test first failed at collection with
`ModuleNotFoundError: No module named 'quant_dca.tools'`. The first
implementation run then failed because pandas converted an optional
`revised_at=None` into `NaT`; the established PIT validator rejected it as
`PIT_INVALID_TIMESTAMP:revised_at`. The CLI now preserves nullable timestamp
values as `None` before snapshot validation. No engine validation was copied or
relaxed.

The focused GREEN passed 2 tests. Exact commands and outputs, both identical
CLI runs, and the complete-suite result are recorded in
`reports/task-10-tests.txt`.

## Audit decisions

- The quality map covers all eleven required domains and separately accounts
  for all six observed inventory rows.
- Actual provider quality tiers remain unassigned. Conditional tier ceilings
  from the earlier documentation matrix are not promoted to evidence.
- `RAW_ONLY` artifacts remain outside canonical research admission. Failed or
  missing source paths are `UNAVAILABLE`, not Tier B/C data.
- Fixture quarantine and lineage prove software behavior only. They do not
  establish provider quality, historical universe coverage, corporate-action
  completeness, survivorship control or research readiness.
- Software readiness and real-data research readiness are recorded as separate
  gates. This task does not freeze provider configuration or V1 and contains no
  OOS or holdout result.
