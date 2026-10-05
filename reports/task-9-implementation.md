# Task 9 implementation — immutable snapshots and lineage

## Interfaces

- `snapshot_hash(df) -> str` returns a canonical logical-data SHA-256 over
  sorted column names, Arrow schema types and canonically sorted rows. DataFrame
  index and input row/column order are deliberately not logical data.
- `write_snapshot(df, layer, as_of, *, root=Path("data"), source_hashes=(),
  schema_version="1", lineage=()) -> SnapshotRef` writes canonical Parquet and
  a JSON completion sidecar. `SnapshotRef.sha256` identifies the complete
  snapshot, while `SnapshotRef.data_sha256` is the table-only digest returned
  by `snapshot_hash`; `path` and `metadata_path` identify the immutable pair.
- `FeatureLineage` records feature, provider, source snapshot, transform and
  availability rule. It can additionally preserve exact source-observation
  identifiers, aware source timestamps and a universe snapshot reference.
- `lookup_lineage(snapshot, feature) -> tuple[FeatureLineage, ...]` verifies the
  immutable Parquet/sidecar pair before returning matching lineage records.

## Decisions

- Logical data, snapshot identity and physical digests are separate.
  `data_sha256` identifies canonical table content and Arrow schema, `sha256`
  binds that digest to layer, cutoff, source hashes, row count, schema version
  and lineage, and `parquet_sha256` verifies the actual file bytes. This avoids
  pretending a particular Parquet encoding is the logical dataset while
  allowing the same cells with different legitimate provenance to coexist.
- Canonicalization sorts column names and rows while retaining Arrow types,
  nulls and timezone-bearing timestamp types. The persisted Parquet uses the
  same canonical table order as the logical digest.
- The only admitted layers are `canonical`, `point_in_time`, `features` and
  `targets`. Generated UTC cutoff and digest path components prevent traversal,
  and dedicated layer directories keep feature and target artifacts physically
  separate. The default root is the repository-local `data` directory.
- `as_of` and lineage source timestamps must be timezone-aware. The cutoff is
  normalized to UTC for path and metadata determinism. Source hashes are only
  caller-supplied, validated SHA-256 values; they are de-duplicated and sorted.
  No source hash, quality tier or lineage claim is synthesized.
- Feature snapshots use the established `assert_pit_safe` guard on every row
  and require `feature`, `available_at`, `max_input_available_at` and `as_of`.
  Their explicit lineage must cover exactly the feature set. Every source and
  optional universe snapshot must appear in `source_hashes`, and every lineage
  timestamp must be known by the snapshot cutoff.
- Feature- and target-shaped rows are classified from their semantic identity
  columns as well as the requested layer. A feature row presented under any
  other layer still runs the PIT guard before failing as misclassified, so a
  future feature timestamp cannot bypass validation through a target label.
- Publication uses same-directory temporary files and exclusive hard links.
  Parquet is installed before its JSON completion sidecar. Existing pairs are
  byte-hash verified and never replaced; a sidecar without Parquet fails as an
  integrity violation. A crash after Parquet installation leaves no completion
  sidecar, so the partial artifact is not a complete snapshot and an identical
  retry can safely finish publication.
- Runtime dependencies on pandas and PyArrow are declared explicitly. DuckDB
  is not needed by this narrow writer/lookup task.
- Lineage lookup uses one narrow verified-read boundary. It requires both
  files, verifies ref, filename, layer and UTC-cutoff path consistency, checks
  the physical and logical table digests and row count, and validates canonical
  bound metadata before deserializing lineage. This detects altered or orphaned
  local pairs; it is not a signature scheme against replacement of the entire
  pair and its external reference.

## TDD and verification

The brief's first test failed at collection because `quant_dca.storage` did not
exist, then passed after canonical hashing was added. The expanded snapshot and
lineage suite next failed because `quant_dca.lineage` did not exist. The first
implementation run exposed a missing `timezone` import (8 failed, 7 passed),
which was corrected before the focused suite became green.

Self-review added two further regressions before fixes: an unknown layer could
bypass feature-layer validation, and a lineage source timestamp could postdate
the snapshot. Each test failed for that exact reason and passed after the
allowlist and lineage cutoff guard were added.

Final command outputs are recorded in `reports/task-9-tests.txt`.

## Limitations

- Logical hashing intentionally supports scalar tabular values convertible by
  pandas/PyArrow. Unsupported nested Python values fail rather than receive an
  unstable representation.
- A feature snapshot is a long-form panel with an explicit `feature` column and
  row-level PIT provenance. A future wide feature store would need its own
  equally explicit per-column lineage and availability contract.
- This task persists and looks up supplied evidence. It does not construct
  transforms, source-observation identifiers, provider timestamps or universe
  membership, and it cannot certify upstream vendor meaning.
- The sidecar is the completion marker; consumers must not treat an orphaned
  Parquet file as a complete snapshot. A broader catalog/discovery API is not
  introduced in this foundation task.

## Resume self-review (2026-09-15)

- Reviewed the resumed draft against the Task 9 brief and the established
  `assert_pit_safe` contract. Feature rows are validated with the snapshot
  cutoff as the prediction timestamp, so `available_at`, input availability or
  feature `as_of` after prediction remains a hard `PIT_LEAKAGE` failure.
- Confirmed the layer allowlist routes `features` and `targets` to distinct
  directories and rejects traversal or near-match layer names.
- Confirmed a snapshot is published as immutable Parquet followed by its JSON
  completion sidecar. Repeated writes verify content and metadata; neither an
  existing file nor sidecar is replaced.
- Confirmed Task 9 code, tests and reports contain no network market-data
  access, credentials or observations dated 2024 or later. Existing unrelated
  foundation tests include future-boundary fixtures and were not modified.
- No production or test changes were required during the resume review. The
  retained RED/GREEN evidence remains the TDD record; only dependency recovery,
  fresh verification and reporting were performed after interruption.

## Review fix round 1 (2026-09-15)

- Added RED regressions for a feature-shaped target bypass, misclassified safe
  feature rows, schema/lineage identity collisions, an orphaned sidecar,
  valid-looking lineage mutations and a pair moved under the wrong layer.
- Replaced table-only artifact identity with metadata-bound snapshot identity
  while retaining `snapshot_hash` as the logical table digest exposed through
  `SnapshotRef.data_sha256`.
- Added the verified local pair read used by `lookup_lineage`; no discovery,
  catalog or external trust layer was introduced.
- Focused GREEN passed 26 tests and the full foundation suite passed 364 tests.
  Exact commands and outputs are recorded in `reports/task-9-tests.txt`.
