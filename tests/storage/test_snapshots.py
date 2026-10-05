from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json

import pandas as pd
import pyarrow.parquet as pq
import pytest

from quant_dca.lineage import FeatureLineage, lookup_lineage
from quant_dca.storage.snapshots import snapshot_hash, write_snapshot


AS_OF = datetime(2023, 3, 7, 21, tzinfo=timezone.utc)
SOURCE_A = "a" * 64
SOURCE_B = "b" * 64


def test_snapshot_hash_is_deterministic():
    df = pd.DataFrame({"b": [2, 1], "a": ["x", "y"]})
    assert snapshot_hash(df) == snapshot_hash(df.copy())


def test_hash_canonicalizes_column_and_row_order_with_nulls():
    original = pd.DataFrame(
        {"symbol": ["BBB", None, "AAA"], "value": [2.0, float("nan"), 1.0]}
    )
    permuted = original.loc[[2, 0, 1], ["value", "symbol"]].reset_index(drop=True)
    assert snapshot_hash(original) == snapshot_hash(permuted)


def test_hash_retains_type_and_timezone_semantics():
    integers = pd.DataFrame({"value": pd.Series([1, 2], dtype="int64")})
    floats = pd.DataFrame({"value": pd.Series([1.0, 2.0], dtype="float64")})
    utc = pd.DataFrame({"at": pd.to_datetime(["2023-01-01T12:00:00Z"])})
    new_york = pd.DataFrame(
        {"at": pd.to_datetime(["2023-01-01T07:00:00-05:00"])}
    )
    assert snapshot_hash(integers) != snapshot_hash(floats)
    assert snapshot_hash(utc) != snapshot_hash(new_york)


def test_write_snapshot_persists_canonical_parquet_and_metadata(tmp_path):
    df = pd.DataFrame(
        {
            "symbol": ["BBB", "AAA"],
            "available_at": pd.to_datetime(
                ["2023-03-07T20:00:00Z", "2023-03-07T19:00:00Z"]
            ),
        }
    )
    ref = write_snapshot(
        df,
        "canonical",
        AS_OF,
        root=tmp_path,
        source_hashes=[SOURCE_B, SOURCE_A, SOURCE_A],
        schema_version="bars-v1",
    )

    metadata = json.loads(ref.metadata_path.read_text())
    assert ref.data_sha256 == snapshot_hash(df)
    assert metadata["sha256"] == ref.sha256
    assert metadata["data_sha256"] == ref.data_sha256
    assert ref.path.stem == ref.sha256
    assert metadata["layer"] == "canonical"
    assert metadata["as_of"] == "2023-03-07T21:00:00+00:00"
    assert metadata["source_hashes"] == [SOURCE_A, SOURCE_B]
    assert metadata["row_count"] == 2
    assert metadata["schema_version"] == "bars-v1"
    assert len(metadata["parquet_sha256"]) == 64
    restored = pq.read_table(ref.path)
    assert restored.column_names == ["available_at", "symbol"]
    assert str(restored.schema.field("available_at").type) == "timestamp[ns, tz=UTC]"
    assert restored.column("symbol").to_pylist() == ["AAA", "BBB"]


def test_repeat_write_verifies_existing_artifacts_and_never_overwrites(tmp_path):
    df = pd.DataFrame({"value": [2, 1]})
    first = write_snapshot(df, "canonical", AS_OF, root=tmp_path)
    parquet_before = first.path.read_bytes()
    sidecar_before = first.metadata_path.read_bytes()
    assert write_snapshot(df.copy(), "canonical", AS_OF, root=tmp_path) == first

    first.path.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="integrity"):
        write_snapshot(df, "canonical", AS_OF, root=tmp_path)
    assert first.path.read_bytes() == b"tampered"
    assert first.metadata_path.read_bytes() == sidecar_before
    first.path.write_bytes(parquet_before)

    first.metadata_path.write_text("{}")
    with pytest.raises(ValueError, match="integrity"):
        write_snapshot(df, "canonical", AS_OF, root=tmp_path)
    assert first.metadata_path.read_text() == "{}"


@pytest.mark.parametrize(
    "layer", ["../targets", "features/targets", "/tmp", ".", "featurez"]
)
def test_write_snapshot_rejects_invalid_or_traversing_layer(tmp_path, layer):
    with pytest.raises(ValueError, match="layer"):
        write_snapshot(pd.DataFrame({"value": [1]}), layer, AS_OF, root=tmp_path)


def test_write_snapshot_requires_aware_cutoff_and_valid_source_hash(tmp_path):
    with pytest.raises(ValueError, match="as_of"):
        write_snapshot(
            pd.DataFrame({"value": [1]}),
            "canonical",
            AS_OF.replace(tzinfo=None),
            root=tmp_path,
        )
    with pytest.raises(ValueError, match="source hash"):
        write_snapshot(
            pd.DataFrame({"value": [1]}),
            "canonical",
            AS_OF,
            root=tmp_path,
            source_hashes=["not-a-sha256"],
        )


def _feature_frame(**changes):
    values = {
        "feature": ["momentum_20d"],
        "entity_id": ["ABC"],
        "observation_date": ["2023-03-07"],
        "value": [0.1],
        "available_at": [AS_OF - timedelta(minutes=1)],
        "max_input_available_at": [AS_OF - timedelta(minutes=2)],
        "as_of": [AS_OF],
    }
    values.update(changes)
    return pd.DataFrame(values)


def _lineage():
    return FeatureLineage(
        feature="momentum_20d",
        provider="csv",
        source_snapshot=SOURCE_A,
        transform="trailing_return_20d",
        availability_rule="all_inputs_available_at_or_before_feature_as_of",
        source_observations=("ABC:2023-02-07/2023-03-07",),
        source_timestamps=(AS_OF - timedelta(minutes=2),),
    )


def test_feature_snapshot_enforces_pit_evidence_and_lineage(tmp_path):
    ref = write_snapshot(
        _feature_frame(),
        "features",
        AS_OF,
        root=tmp_path,
        source_hashes=[SOURCE_A],
        lineage=[_lineage()],
    )
    assert ref.path.parent == tmp_path / "features" / "20230307T210000.000000Z"
    assert lookup_lineage(ref, "momentum_20d") == (_lineage(),)


def test_feature_snapshot_fails_closed_on_future_or_missing_evidence(tmp_path):
    with pytest.raises(ValueError, match="PIT_LEAKAGE"):
        write_snapshot(
            _feature_frame(max_input_available_at=[AS_OF + timedelta(seconds=1)]),
            "features",
            AS_OF,
            root=tmp_path,
            source_hashes=[SOURCE_A],
            lineage=[_lineage()],
        )
    with pytest.raises((TypeError, ValueError), match="provenance|PIT_INVALID"):
        write_snapshot(
            _feature_frame().drop(columns="max_input_available_at"),
            "features",
            AS_OF,
            root=tmp_path,
            source_hashes=[SOURCE_A],
            lineage=[_lineage()],
        )
    with pytest.raises(ValueError, match="lineage"):
        write_snapshot(
            _feature_frame(),
            "features",
            AS_OF,
            root=tmp_path,
            source_hashes=[SOURCE_A],
        )


def test_target_layer_cannot_bypass_feature_pit_guard(tmp_path):
    with pytest.raises(ValueError, match="PIT_LEAKAGE"):
        write_snapshot(
            _feature_frame(available_at=[AS_OF + timedelta(seconds=1)]),
            "targets",
            AS_OF,
            root=tmp_path,
        )


def test_target_layer_rejects_misclassified_feature_rows(tmp_path):
    with pytest.raises(ValueError, match="misclassified"):
        write_snapshot(_feature_frame(), "targets", AS_OF, root=tmp_path)


def test_features_and_targets_are_physically_separate(tmp_path):
    feature_ref = write_snapshot(
        _feature_frame(),
        "features",
        AS_OF,
        root=tmp_path,
        source_hashes=[SOURCE_A],
        lineage=[_lineage()],
    )
    target_ref = write_snapshot(
        pd.DataFrame({"target": ["return_5d"], "value": [0.2]}),
        "targets",
        AS_OF,
        root=tmp_path,
        source_hashes=[SOURCE_A],
    )
    assert feature_ref.path.parent.parent == tmp_path / "features"
    assert target_ref.path.parent.parent == tmp_path / "targets"
    assert feature_ref.path != target_ref.path


def test_snapshot_identity_binds_schema_version_and_lineage(tmp_path):
    frame = _feature_frame()
    lineage_a = _lineage()
    lineage_b = replace(lineage_a, transform="trailing_return_21d")
    first = write_snapshot(
        frame,
        "features",
        AS_OF,
        root=tmp_path,
        source_hashes=[SOURCE_A],
        schema_version="features-v1",
        lineage=[lineage_a],
    )
    different_schema = write_snapshot(
        frame,
        "features",
        AS_OF,
        root=tmp_path,
        source_hashes=[SOURCE_A],
        schema_version="features-v2",
        lineage=[lineage_a],
    )
    different_lineage = write_snapshot(
        frame,
        "features",
        AS_OF,
        root=tmp_path,
        source_hashes=[SOURCE_A],
        schema_version="features-v1",
        lineage=[lineage_b],
    )

    assert len({first.path, different_schema.path, different_lineage.path}) == 3
    assert len({first.sha256, different_schema.sha256, different_lineage.sha256}) == 3
    assert first.data_sha256 == snapshot_hash(frame)
    assert different_schema.data_sha256 == first.data_sha256
    assert different_lineage.data_sha256 == first.data_sha256


def test_lineage_rejects_unreferenced_source_snapshot(tmp_path):
    with pytest.raises(ValueError, match="source snapshot"):
        write_snapshot(
            _feature_frame(),
            "features",
            AS_OF,
            root=tmp_path,
            source_hashes=[SOURCE_B],
            lineage=[_lineage()],
        )


def test_lineage_round_trips_optional_cross_sectional_universe_snapshot(tmp_path):
    record = FeatureLineage(
        feature="relative_strength_rank",
        provider="csv",
        source_snapshot=SOURCE_A,
        transform="percentile_in_universe",
        availability_rule="inputs_and_membership_known_by_feature_as_of",
        source_observations=("ABC:2023-03-07", "BBB:2023-03-07"),
        source_timestamps=(AS_OF - timedelta(minutes=2),),
        universe_snapshot=SOURCE_B,
    )
    frame = _feature_frame(feature=["relative_strength_rank"])
    ref = write_snapshot(
        frame,
        "features",
        AS_OF,
        root=tmp_path,
        source_hashes=[SOURCE_A, SOURCE_B],
        lineage=[record],
    )
    assert lookup_lineage(ref, "relative_strength_rank") == (record,)


def test_feature_lineage_timestamp_cannot_postdate_snapshot(tmp_path):
    future_lineage = FeatureLineage(
        feature="momentum_20d",
        provider="csv",
        source_snapshot=SOURCE_A,
        transform="trailing_return_20d",
        availability_rule="all_inputs_available_at_or_before_feature_as_of",
        source_timestamps=(AS_OF + timedelta(seconds=1),),
    )
    with pytest.raises(ValueError, match="PIT_LEAKAGE"):
        write_snapshot(
            _feature_frame(),
            "features",
            AS_OF,
            root=tmp_path,
            source_hashes=[SOURCE_A],
            lineage=[future_lineage],
        )


def test_lookup_lineage_rejects_orphaned_sidecar(tmp_path):
    ref = write_snapshot(
        _feature_frame(),
        "features",
        AS_OF,
        root=tmp_path,
        source_hashes=[SOURCE_A],
        lineage=[_lineage()],
    )
    ref.path.unlink()

    with pytest.raises(ValueError, match="integrity"):
        lookup_lineage(ref, "momentum_20d")


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("provider", "fred"),
        ("source_snapshot", SOURCE_B),
        ("transform", "trailing_return_21d"),
        ("availability_rule", "inputs_known_at_month_end"),
    ],
)
def test_lookup_lineage_rejects_altered_valid_lineage(
    tmp_path, field, replacement
):
    ref = write_snapshot(
        _feature_frame(),
        "features",
        AS_OF,
        root=tmp_path,
        source_hashes=[SOURCE_A],
        lineage=[_lineage()],
    )
    metadata = json.loads(ref.metadata_path.read_text())
    metadata["lineage"][0][field] = replacement
    ref.metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")

    with pytest.raises(ValueError, match="integrity"):
        lookup_lineage(ref, "momentum_20d")


def test_lookup_lineage_rejects_pair_moved_to_wrong_layer(tmp_path):
    ref = write_snapshot(
        _feature_frame(),
        "features",
        AS_OF,
        root=tmp_path,
        source_hashes=[SOURCE_A],
        lineage=[_lineage()],
    )
    wrong_directory = tmp_path / "targets" / ref.path.parent.name
    wrong_directory.mkdir(parents=True)
    ref.path.rename(wrong_directory / ref.path.name)
    wrong_metadata = ref.metadata_path.rename(wrong_directory / ref.metadata_path.name)

    with pytest.raises(ValueError, match="integrity"):
        lookup_lineage(wrong_metadata, "momentum_20d")
