"""Deterministic logical hashes and immutable Parquet snapshots."""
from __future__ import annotations

from datetime import date, datetime, time, timezone
from dataclasses import dataclass
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Iterable

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from quant_dca.lineage import FeatureLineage, canonical_lineage
from quant_dca.point_in_time.asof import assert_pit_safe


DEFAULT_SNAPSHOT_ROOT = Path("data")
_LAYERS = frozenset({"canonical", "point_in_time", "features", "targets"})
_SCHEMA_VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
_SHA256 = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True, slots=True)
class SnapshotRef:
    """Reference to one immutable snapshot pair.

    ``sha256`` identifies the complete snapshot metadata and logical data.
    ``data_sha256`` is the logical table-only digest returned by
    :func:`snapshot_hash`.
    """

    path: Path
    metadata_path: Path
    sha256: str
    data_sha256: str


def _json_value(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return {"sequence": [_json_value(item) for item in value]}
    if isinstance(value, (datetime, date, time)):
        return {"temporal": value.isoformat()}
    if isinstance(value, bytes):
        return {"bytes": value.hex()}
    if isinstance(value, Decimal):
        return {"decimal": str(value)}
    if isinstance(value, float):
        if value != value:
            return {"float": "nan"}
        if value == float("inf"):
            return {"float": "+inf"}
        if value == float("-inf"):
            return {"float": "-inf"}
    if isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"Unsupported snapshot value type: {type(value).__name__}")


def _canonical_table(df: pd.DataFrame) -> tuple[pa.Table, list[list[object]]]:
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    if not df.columns.is_unique or not all(isinstance(name, str) for name in df.columns):
        raise ValueError("Snapshot columns must have unique string names")

    names = sorted(df.columns)
    table = pa.Table.from_pandas(df.loc[:, names], preserve_index=False).replace_schema_metadata(None)
    rows = [
        [_json_value(table.column(column)[row].as_py()) for column in range(table.num_columns)]
        for row in range(table.num_rows)
    ]
    order = sorted(
        range(len(rows)),
        key=lambda row: json.dumps(rows[row], sort_keys=True, separators=(",", ":")),
    )
    if order:
        table = table.take(pa.array(order, type=pa.int64()))
    return table, [rows[index] for index in order]


def _canonical_payload(df: pd.DataFrame) -> bytes:
    table, _ = _canonical_table(df)
    return _canonical_arrow_payload(table)


def _canonical_arrow_payload(table: pa.Table) -> bytes:
    if len(set(table.column_names)) != table.num_columns:
        raise ValueError("Snapshot columns must be unique")
    table = table.select(sorted(table.column_names)).replace_schema_metadata(None)
    rows = [
        [
            _json_value(table.column(column)[row].as_py())
            for column in range(table.num_columns)
        ]
        for row in range(table.num_rows)
    ]
    rows.sort(key=lambda row: json.dumps(row, sort_keys=True, separators=(",", ":")))
    schema = [{"name": field.name, "type": _logical_type(field.type)} for field in table.schema]
    return json.dumps(
        {"schema": schema, "rows": rows},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _logical_type(kind: pa.DataType) -> object:
    # Parquet renames list child fields from item to element. Child field names
    # are not sequence data, but element type and nullability remain bound.
    if pa.types.is_list(kind) or pa.types.is_large_list(kind):
        return {"sequence": "large_list" if pa.types.is_large_list(kind) else "list",
                "value_type": _logical_type(kind.value_type),
                "nullable": kind.value_field.nullable}
    return str(kind)


def snapshot_hash(df: pd.DataFrame) -> str:
    """Return a SHA-256 digest of canonical schema and row content."""
    return hashlib.sha256(_canonical_payload(df)).hexdigest()


def _arrow_table_hash(table: pa.Table) -> str:
    return hashlib.sha256(_canonical_arrow_payload(table)).hexdigest()


_IDENTITY_FIELDS = frozenset(
    {
        "as_of",
        "data_sha256",
        "layer",
        "lineage",
        "row_count",
        "schema_version",
        "source_hashes",
    }
)
_METADATA_FIELDS = _IDENTITY_FIELDS | {"parquet_sha256", "sha256"}


def _identity_digest(metadata: dict[str, object]) -> str:
    payload = {field: metadata[field] for field in sorted(_IDENTITY_FIELDS)}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _normalize_hashes(source_hashes: Iterable[str]) -> tuple[str, ...]:
    if isinstance(source_hashes, (str, bytes)):
        raise TypeError("source_hashes must be an iterable of SHA-256 digests")
    values = tuple(source_hashes)
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in values):
        raise ValueError("Invalid source hash")
    return tuple(sorted(set(values)))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _publish(candidate: Path, destination: Path, expected_digest: str) -> None:
    try:
        os.link(candidate, destination)
    except FileExistsError:
        if _sha256_file(destination) != expected_digest:
            raise ValueError(f"Immutable snapshot integrity violation: {destination.name}")


def _validate_feature_snapshot(
    df: pd.DataFrame,
    as_of: datetime,
    records: tuple[FeatureLineage, ...],
    source_hashes: tuple[str, ...],
) -> None:
    required = {"feature", "available_at", "max_input_available_at", "as_of"}
    if not required.issubset(df.columns):
        raise ValueError("Feature snapshot requires complete PIT provenance")
    assert_pit_safe(df.to_dict(orient="records"), as_of)
    features = set(df["feature"])
    if not features or any(not isinstance(feature, str) or not feature for feature in features):
        raise ValueError("Feature snapshot requires explicit feature identities")
    lineage_features = {record.feature for record in records}
    if lineage_features != features:
        raise ValueError("Feature snapshot lineage must cover exactly its features")
    declared = set(source_hashes)
    for record in records:
        referenced = {record.source_snapshot}
        if record.universe_snapshot is not None:
            referenced.add(record.universe_snapshot)
        if not referenced.issubset(declared):
            raise ValueError("Lineage source snapshot is not a declared source hash")
        if any(timestamp > as_of for timestamp in record.source_timestamps):
            raise ValueError("PIT_LEAKAGE:lineage_source_after_snapshot")


def _reject_misclassified_rows(df: pd.DataFrame, layer: str, as_of: datetime) -> None:
    if layer != "features" and "feature" in df.columns:
        assert_pit_safe(df.to_dict(orient="records"), as_of)
        raise ValueError("misclassified feature rows require the features layer")
    if layer != "targets" and "target" in df.columns:
        raise ValueError("misclassified target rows require the targets layer")


def write_snapshot(
    df: pd.DataFrame,
    layer: str,
    as_of: datetime,
    *,
    root: str | Path = DEFAULT_SNAPSHOT_ROOT,
    source_hashes: Iterable[str] = (),
    schema_version: str = "1",
    lineage: Iterable[FeatureLineage] = (),
) -> SnapshotRef:
    """Publish a canonical Parquet file and its deterministic completion sidecar.

    The Parquet file is installed first and the JSON sidecar last. Consumers
    should treat only a verified pair as a complete snapshot.
    """
    if not isinstance(layer, str) or layer not in _LAYERS:
        raise ValueError("Invalid snapshot layer")
    if not isinstance(as_of, datetime):
        raise TypeError("as_of must be a timezone-aware datetime")
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    if not isinstance(schema_version, str) or not _SCHEMA_VERSION.fullmatch(schema_version):
        raise ValueError("Invalid schema version")
    cutoff = as_of.astimezone(timezone.utc)
    sources = _normalize_hashes(source_hashes)
    lineage_records = canonical_lineage(lineage)
    _reject_misclassified_rows(df, layer, cutoff)
    if layer == "features":
        if "target" in df.columns:
            raise ValueError("misclassified target rows require the targets layer")
        _validate_feature_snapshot(df, cutoff, lineage_records, sources)
    elif lineage_records:
        raise ValueError("Feature lineage requires the features layer")

    table, _ = _canonical_table(df)
    data_digest = snapshot_hash(df)
    identity_metadata: dict[str, object] = {
        "as_of": cutoff.isoformat(),
        "data_sha256": data_digest,
        "layer": layer,
        "lineage": [record.to_dict() for record in lineage_records],
        "row_count": len(df),
        "schema_version": schema_version,
        "source_hashes": list(sources),
    }
    snapshot_digest = _identity_digest(identity_metadata)
    cutoff_key = cutoff.strftime("%Y%m%dT%H%M%S.%fZ")
    directory = Path(root) / layer / cutoff_key
    directory.mkdir(parents=True, exist_ok=True)
    parquet_path = directory / f"{snapshot_digest}.parquet"
    metadata_path = directory / f"{snapshot_digest}.json"
    if metadata_path.exists() and not parquet_path.exists():
        raise ValueError("Immutable snapshot integrity violation: sidecar without Parquet")

    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{snapshot_digest}.", suffix=".parquet.tmp", dir=directory, delete=False
        ) as temporary:
            temporary_name = temporary.name
        candidate = Path(temporary_name)
        pq.write_table(table, candidate, compression="zstd", version="2.6")
        parquet_digest = _sha256_file(candidate)
        _publish(candidate, parquet_path, parquet_digest)

        metadata = dict(identity_metadata)
        metadata.update(parquet_sha256=parquet_digest, sha256=snapshot_digest)
        encoded = json.dumps(metadata, indent=2, sort_keys=True).encode("utf-8") + b"\n"
        sidecar_digest = hashlib.sha256(encoded).hexdigest()
        with tempfile.NamedTemporaryFile(
            prefix=f".{snapshot_digest}.", suffix=".json.tmp", dir=directory, delete=False
        ) as sidecar:
            sidecar.write(encoded)
            sidecar_name = sidecar.name
        try:
            _publish(Path(sidecar_name), metadata_path, sidecar_digest)
        finally:
            Path(sidecar_name).unlink(missing_ok=True)
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)

    if _sha256_file(parquet_path) != parquet_digest:
        raise ValueError("Immutable snapshot integrity violation: Parquet digest mismatch")
    if metadata_path.read_bytes() != encoded:
        raise ValueError("Immutable snapshot integrity violation: sidecar mismatch")
    return SnapshotRef(parquet_path, metadata_path, snapshot_digest, data_digest)


def _snapshot_paths(
    snapshot: SnapshotRef | str | Path,
) -> tuple[Path, Path, str | None, str | None]:
    if isinstance(snapshot, SnapshotRef):
        return snapshot.path, snapshot.metadata_path, snapshot.sha256, snapshot.data_sha256
    path = Path(snapshot)
    if path.suffix == ".json":
        return path.with_suffix(".parquet"), path, None, None
    if path.suffix == ".parquet":
        return path, path.with_suffix(".json"), None, None
    raise ValueError("Immutable snapshot integrity violation: invalid snapshot path")


def read_snapshot_metadata(snapshot: SnapshotRef | str | Path) -> dict[str, object]:
    """Verify an immutable snapshot pair and return its bound metadata."""
    try:
        parquet_path, metadata_path, expected_identity, expected_data = _snapshot_paths(
            snapshot
        )
        if (
            parquet_path.parent != metadata_path.parent
            or parquet_path.stem != metadata_path.stem
            or not parquet_path.is_file()
            or not metadata_path.is_file()
        ):
            raise ValueError
        document = json.loads(metadata_path.read_text())
        if not isinstance(document, dict) or set(document) != _METADATA_FIELDS:
            raise ValueError
        identity = document["sha256"]
        data_digest = document["data_sha256"]
        parquet_digest = document["parquet_sha256"]
        if any(
            not isinstance(value, str) or not _SHA256.fullmatch(value)
            for value in (identity, data_digest, parquet_digest)
        ):
            raise ValueError
        if identity != _identity_digest(document) or metadata_path.stem != identity:
            raise ValueError
        if expected_identity is not None and expected_identity != identity:
            raise ValueError
        if expected_data is not None and expected_data != data_digest:
            raise ValueError

        layer = document["layer"]
        as_of = document["as_of"]
        schema_version = document["schema_version"]
        row_count = document["row_count"]
        if not isinstance(layer, str) or layer not in _LAYERS:
            raise ValueError
        if parquet_path.parent.parent.name != layer:
            raise ValueError
        if not isinstance(as_of, str):
            raise ValueError
        cutoff = datetime.fromisoformat(as_of)
        if (
            cutoff.tzinfo is None
            or cutoff.utcoffset() is None
            or cutoff.astimezone(timezone.utc).isoformat() != as_of
            or parquet_path.parent.name != cutoff.strftime("%Y%m%dT%H%M%S.%fZ")
        ):
            raise ValueError
        if not isinstance(schema_version, str) or not _SCHEMA_VERSION.fullmatch(
            schema_version
        ):
            raise ValueError
        if type(row_count) is not int or row_count < 0:
            raise ValueError
        source_hashes = document["source_hashes"]
        if (
            not isinstance(source_hashes, list)
            or list(_normalize_hashes(source_hashes)) != source_hashes
        ):
            raise ValueError
        raw_lineage = document["lineage"]
        if not isinstance(raw_lineage, list) or any(
            not isinstance(record, dict) for record in raw_lineage
        ):
            raise ValueError
        parsed_lineage = canonical_lineage(
            FeatureLineage.from_dict(record) for record in raw_lineage
        )
        if [record.to_dict() for record in parsed_lineage] != raw_lineage:
            raise ValueError

        if _sha256_file(parquet_path) != parquet_digest:
            raise ValueError
        table = pq.read_table(parquet_path)
        if table.num_rows != row_count or _arrow_table_hash(table) != data_digest:
            raise ValueError
    except (OSError, KeyError, TypeError, ValueError, pa.ArrowException):
        raise ValueError("Immutable snapshot integrity violation") from None
    return document
