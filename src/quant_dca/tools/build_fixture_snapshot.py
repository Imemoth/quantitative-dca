"""Build a deterministic synthetic snapshot for foundation verification only."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
import json
from pathlib import Path
from typing import Sequence

import pandas as pd

from quant_dca.canonical.validate import validate_observations
from quant_dca.lineage import FeatureLineage
from quant_dca.point_in_time.asof import latest_known
from quant_dca.storage.snapshots import SnapshotRef, write_snapshot
from quant_dca.types import FeatureValue, Observation, QualityTier, Region


FIXTURE_CLASSIFICATION = "SYNTHETIC_NOT_RESEARCH_EVIDENCE"


@dataclass(frozen=True, slots=True)
class FixtureBuildResult:
    """Machine-auditable result of one synthetic foundation build."""

    canonical_snapshot: SnapshotRef
    snapshot: SnapshotRef
    quarantined_rows: int
    quarantine_reasons: dict[str, int]
    selected_revision_ids: tuple[str, ...]


def _utc(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=timezone.utc)


def _fixture_observations() -> tuple[Observation, ...]:
    provenance = {
        "quality": QualityTier.C,
        "source": "synthetic_fixture",
        "entity_id": None,
        "currency": None,
        "exchange": None,
    }
    return (
        Observation(
            series="us_macro_fixture",
            observation_date="2020-01-01",
            value=1.0,
            region=Region.US,
            revision_id="us-first",
            published_at=_utc(2020, 2, 14),
            available_at=_utc(2020, 2, 14),
            **provenance,
        ),
        Observation(
            series="us_macro_fixture",
            observation_date="2020-01-01",
            value=1.1,
            region=Region.US,
            revision_id="us-revised",
            published_at=_utc(2020, 2, 14),
            revised_at=_utc(2020, 3, 10),
            available_at=_utc(2020, 3, 10),
            **provenance,
        ),
        Observation(
            series="us_macro_fixture",
            observation_date="2020-01-01",
            value=1.2,
            region=Region.US,
            revision_id="us-future-revision",
            published_at=_utc(2020, 2, 14),
            revised_at=_utc(2020, 4, 10),
            available_at=_utc(2020, 4, 10),
            **provenance,
        ),
        Observation(
            series="eu_macro_fixture",
            observation_date="2020-01-01",
            value=0.5,
            region=Region.EU,
            revision_id="eu-first",
            published_at=_utc(2020, 2, 20),
            available_at=_utc(2020, 2, 20),
            **provenance,
        ),
        Observation(
            series="quarantine_fixture",
            observation_date="2020-01-01",
            value=None,
            region=Region.GLOBAL,
            revision_id="invalid-missing-value",
            published_at=_utc(2020, 2, 1),
            available_at=_utc(2020, 2, 1),
            **provenance,
        ),
    )


def _frame(rows: tuple[object, ...]) -> pd.DataFrame:
    frame = pd.DataFrame(asdict(row) for row in rows)
    return frame.astype(object).where(pd.notna(frame), None)


def build_fixture_snapshot(
    as_of: datetime, *, root: str | Path = Path("data/fixture_snapshots")
) -> FixtureBuildResult:
    """Validate, reconstruct and persist a synthetic lineage-bound feature snapshot."""
    if not isinstance(as_of, datetime):
        raise TypeError("as_of must be a timezone-aware datetime")
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    cutoff = as_of.astimezone(timezone.utc)

    validation = validate_observations(_fixture_observations())
    grouped: dict[tuple[str, str], list[Observation]] = {}
    for row in validation.valid_rows:
        assert isinstance(row, Observation)
        grouped.setdefault((row.series, row.observation_date), []).append(row)
    selected = tuple(latest_known(grouped[key], cutoff) for key in sorted(grouped))

    canonical_snapshot = write_snapshot(
        _frame(selected),
        "canonical",
        cutoff,
        root=root,
        schema_version="synthetic-fixture-v1",
    )
    features = tuple(
        FeatureValue(
            feature=row.series,
            entity_id=row.entity_id,
            observation_date=row.observation_date,
            as_of=cutoff,
            value=row.value,
            max_input_available_at=row.available_at,
            available_at=row.available_at,
            quality=row.quality,
            source=row.source,
            revision_id=row.revision_id,
            published_at=row.published_at,
            revised_at=row.revised_at,
            currency=row.currency,
            region=row.region,
            exchange=row.exchange,
        )
        for row in selected
    )
    lineage = tuple(
        FeatureLineage(
            feature=row.series,
            provider="synthetic_fixture",
            source_snapshot=canonical_snapshot.sha256,
            transform="identity_fixture_value",
            availability_rule="latest_known_available_at_lte_as_of",
            source_observations=(
                f"{row.series}:{row.observation_date}:{row.revision_id}",
            ),
            source_timestamps=(row.available_at,),
        )
        for row in selected
    )
    snapshot = write_snapshot(
        _frame(features),
        "features",
        cutoff,
        root=root,
        source_hashes=(canonical_snapshot.sha256,),
        schema_version="synthetic-fixture-v1",
        lineage=lineage,
    )
    return FixtureBuildResult(
        canonical_snapshot=canonical_snapshot,
        snapshot=snapshot,
        quarantined_rows=len(validation.quarantined_rows),
        quarantine_reasons=validation.reasons,
        selected_revision_ids=tuple(sorted(row.revision_id for row in selected)),
    )


def _parse_date(value: str) -> datetime:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "--as-of must be an ISO date (YYYY-MM-DD)"
        ) from error
    return datetime.combine(parsed, datetime.min.time(), timezone.utc)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", required=True, type=_parse_date)
    parser.add_argument("--root", type=Path, default=Path("data/fixture_snapshots"))
    arguments = parser.parse_args(argv)
    result = build_fixture_snapshot(arguments.as_of, root=arguments.root)
    output = {
        "as_of": arguments.as_of.isoformat(),
        "canonical_snapshot_sha256": result.canonical_snapshot.sha256,
        "data_sha256": result.snapshot.data_sha256,
        "fixture_classification": FIXTURE_CLASSIFICATION,
        "quarantine_reasons": result.quarantine_reasons,
        "quarantined_rows": result.quarantined_rows,
        "snapshot_path": str(result.snapshot.path),
        "snapshot_sha256": result.snapshot.sha256,
    }
    print(json.dumps(output, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
