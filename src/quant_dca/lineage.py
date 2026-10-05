"""Explicit, serializable feature-to-source lineage records."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from quant_dca.storage.snapshots import SnapshotRef


_SHA256 = re.compile(r"[0-9a-f]{64}")
_PROVIDER = re.compile(r"[a-z][a-z0-9_]*")


def _aware(value: object, field: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field} must be a timezone-aware datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value


@dataclass(frozen=True, slots=True)
class FeatureLineage:
    """Evidence linking one feature transform to immutable source snapshots."""

    feature: str
    provider: str
    source_snapshot: str
    transform: str
    availability_rule: str
    source_observations: tuple[str, ...] = ()
    source_timestamps: tuple[datetime, ...] = ()
    universe_snapshot: str | None = None

    def __post_init__(self) -> None:
        for field in ("feature", "transform", "availability_rule"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"lineage {field} must be explicit")
        if not isinstance(self.provider, str) or not _PROVIDER.fullmatch(self.provider):
            raise ValueError("lineage provider must be a canonical identifier")
        if not isinstance(self.source_snapshot, str) or not _SHA256.fullmatch(
            self.source_snapshot
        ):
            raise ValueError("lineage source snapshot must be a SHA-256 digest")
        if self.universe_snapshot is not None and (
            not isinstance(self.universe_snapshot, str)
            or not _SHA256.fullmatch(self.universe_snapshot)
        ):
            raise ValueError("lineage universe snapshot must be a SHA-256 digest")
        if not isinstance(self.source_observations, tuple) or any(
            not isinstance(value, str) or not value.strip()
            for value in self.source_observations
        ):
            raise ValueError("lineage source observations must be explicit identifiers")
        if not isinstance(self.source_timestamps, tuple):
            raise TypeError("lineage source timestamps must be a tuple")
        for value in self.source_timestamps:
            _aware(value, "lineage source timestamp")
        object.__setattr__(
            self, "source_observations", tuple(sorted(set(self.source_observations)))
        )
        object.__setattr__(
            self,
            "source_timestamps",
            tuple(sorted(set(self.source_timestamps))),
        )

    def to_dict(self) -> dict[str, object]:
        values = asdict(self)
        values["source_observations"] = list(self.source_observations)
        values["source_timestamps"] = [
            value.astimezone(timezone.utc).isoformat() for value in self.source_timestamps
        ]
        return values

    @classmethod
    def from_dict(cls, values: dict[str, object]) -> "FeatureLineage":
        required = {
            "feature",
            "provider",
            "source_snapshot",
            "transform",
            "availability_rule",
        }
        if not required.issubset(values):
            raise ValueError("Incomplete lineage record")
        observations = values.get("source_observations", [])
        timestamps = values.get("source_timestamps", [])
        if not isinstance(observations, list) or not isinstance(timestamps, list):
            raise ValueError("Invalid lineage record")
        return cls(
            feature=values["feature"],  # type: ignore[arg-type]
            provider=values["provider"],  # type: ignore[arg-type]
            source_snapshot=values["source_snapshot"],  # type: ignore[arg-type]
            transform=values["transform"],  # type: ignore[arg-type]
            availability_rule=values["availability_rule"],  # type: ignore[arg-type]
            source_observations=tuple(observations),
            source_timestamps=tuple(datetime.fromisoformat(value) for value in timestamps),
            universe_snapshot=values.get("universe_snapshot"),  # type: ignore[arg-type]
        )


def canonical_lineage(records: Iterable[FeatureLineage]) -> tuple[FeatureLineage, ...]:
    materialized = tuple(records)
    if any(not isinstance(record, FeatureLineage) for record in materialized):
        raise TypeError("lineage must contain FeatureLineage records")
    return tuple(
        sorted(
            set(materialized),
            key=lambda record: json.dumps(
                record.to_dict(), sort_keys=True, separators=(",", ":")
            ),
        )
    )


def lookup_lineage(
    snapshot: SnapshotRef | str | Path, feature: str
) -> tuple[FeatureLineage, ...]:
    """Read lineage only after verifying its immutable snapshot pair."""
    if not isinstance(feature, str) or not feature:
        raise ValueError("feature must be explicit")
    from quant_dca.storage.snapshots import read_snapshot_metadata

    document = read_snapshot_metadata(snapshot)
    records = document.get("lineage")
    if not isinstance(records, list):
        raise ValueError("Snapshot has no valid lineage sidecar")
    matches = tuple(
        FeatureLineage.from_dict(record)
        for record in records
        if isinstance(record, dict) and record.get("feature") == feature
    )
    if not matches:
        raise LookupError(f"No lineage for feature: {feature}")
    return canonical_lineage(matches)
