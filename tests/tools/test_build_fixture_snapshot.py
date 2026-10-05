import json
from datetime import datetime, timezone

import pandas as pd

from quant_dca.lineage import lookup_lineage
from quant_dca.storage.snapshots import read_snapshot_metadata
from quant_dca.tools.build_fixture_snapshot import build_fixture_snapshot, main


def test_fixture_build_selects_known_revisions_and_binds_lineage(tmp_path):
    result = build_fixture_snapshot(
        datetime(2020, 3, 12, tzinfo=timezone.utc), root=tmp_path
    )

    assert result.quarantined_rows == 1
    assert result.quarantine_reasons == {"MISSING_VALUE": 1}
    assert result.selected_revision_ids == ("eu-first", "us-revised")

    features = pd.read_parquet(result.snapshot.path)
    assert features[["feature", "value"]].to_dict(orient="records") == [
        {"feature": "eu_macro_fixture", "value": 0.5},
        {"feature": "us_macro_fixture", "value": 1.1},
    ]

    metadata = read_snapshot_metadata(result.snapshot)
    assert metadata["source_hashes"] == [result.canonical_snapshot.sha256]
    assert result.snapshot.sha256 == metadata["sha256"]
    assert result.snapshot.data_sha256 == metadata["data_sha256"]
    for feature in ("eu_macro_fixture", "us_macro_fixture"):
        lineage = lookup_lineage(result.snapshot, feature)
        assert len(lineage) == 1
        assert lineage[0].provider == "synthetic_fixture"
        assert lineage[0].source_snapshot == result.canonical_snapshot.sha256


def test_cli_emits_repeatable_machine_output_for_date_cutoff(tmp_path, capsys):
    args = ["--as-of", "2020-03-12", "--root", str(tmp_path)]

    assert main(args) == 0
    first = json.loads(capsys.readouterr().out)
    assert main(args) == 0
    second = json.loads(capsys.readouterr().out)

    assert first == second
    assert first["as_of"] == "2020-03-12T00:00:00+00:00"
    assert first["fixture_classification"] == "SYNTHETIC_NOT_RESEARCH_EVIDENCE"
    assert first["quarantined_rows"] == 1
    assert len(first["snapshot_sha256"]) == 64
    assert len(first["data_sha256"]) == 64
    assert first["snapshot_sha256"] != first["data_sha256"]
