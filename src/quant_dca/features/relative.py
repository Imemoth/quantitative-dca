"""Historical relative-strength features with explicit PIT eligibility.

Percentiles use average zero-based positional ranks scaled to ``[0, 1]``.
Ties therefore share their average position, a singleton receives ``0.5``,
and an ineligible or missing/non-finite target receives ``None``.  Eligibility
is always supplied by the caller; this module has no current-universe lookup.
"""

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
import math

from quant_dca.calendars.service import eligible_session_close
from quant_dca.features.registry import FeatureRegistry
from quant_dca.point_in_time.asof import assert_pit_safe, latest_known
from quant_dca.types import FeatureValue, QualityTier, Region, Security
from quant_dca.universe.membership import UniverseIndex


_HORIZONS = (20, 60, 120)
_QUALITY_ORDER = {QualityTier.A: 0, QualityTier.B: 1, QualityTier.C: 2}


def _require_aware(value: object, field: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field} must be a timezone-aware datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be a timezone-aware datetime")
    return value


def _iso_date(value: object, field: str) -> date:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be an ISO date string")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date string") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{field} must be an ISO date string")
    return parsed


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


@dataclass(frozen=True, slots=True, kw_only=True)
class SectorClassification:
    """A versioned sector assignment known over an effective date interval."""

    security_id: str
    sector_id: str
    active_from: str
    available_at: datetime
    quality: QualityTier
    source: str
    revision_id: str
    active_to: str | None = None
    published_at: datetime | None = None
    revised_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.security_id or not self.sector_id:
            raise ValueError("classification security_id and sector_id must be non-empty")
        start = _iso_date(self.active_from, "active_from")
        end = _iso_date(self.active_to, "active_to") if self.active_to is not None else None
        if end is not None and end <= start:
            raise ValueError("active_to must be after active_from")
        available = _require_aware(self.available_at, "available_at")
        for field in ("published_at", "revised_at"):
            value = getattr(self, field)
            if value is not None:
                timestamp = _require_aware(value, field)
                if timestamp > available:
                    raise ValueError(f"{field} cannot be after available_at")
        if (
            self.published_at is not None
            and self.revised_at is not None
            and self.revised_at < self.published_at
        ):
            raise ValueError("revised_at cannot be before published_at")
        if not isinstance(self.quality, QualityTier):
            raise TypeError("quality must be a QualityTier")
        if not self.source.strip() or not self.revision_id.strip():
            raise ValueError("classification provenance must be non-empty")


@dataclass(frozen=True, slots=True)
class RelativeFeatureSnapshot:
    """Derived outputs plus the exact historical evidence used to build them."""

    features: tuple[FeatureValue, ...]
    eligible_security_ids: tuple[str, ...]
    selected_cross_section: tuple[FeatureValue, ...]
    selected_classifications: tuple[SectorClassification, ...]
    selected_stock_returns: tuple[FeatureValue, ...]
    selected_sector_benchmark_returns: tuple[FeatureValue, ...]
    selected_market_benchmark_returns: tuple[FeatureValue, ...]


def percentile_in_universe(
    security_id: str,
    values: Mapping[str, float | None],
    eligible: Iterable[str],
) -> float | None:
    """Return an eligible-only average positional percentile for one security."""
    eligible_ids = frozenset(eligible)
    target = _number(values.get(security_id))
    if security_id not in eligible_ids or target is None:
        return None
    ranked = sorted(
        value
        for member in eligible_ids
        if (value := _number(values.get(member))) is not None
    )
    if not ranked:
        return None
    if len(ranked) == 1:
        return 0.5
    lower = sum(value < target for value in ranked)
    equal = sum(value == target for value in ranked)
    average_zero_based_rank = lower + (equal - 1) / 2
    return average_zero_based_rank / (len(ranked) - 1)


def _difference(left: object, right: object) -> float | None:
    left_number, right_number = _number(left), _number(right)
    if left_number is None or right_number is None:
        return None
    return left_number - right_number


def compute_relative_features(
    security_id: str,
    *,
    stock_returns: Mapping[int, float | None],
    sector_returns: Mapping[int, float | None],
    market_returns: Mapping[int, float | None],
    return_120d_values: Mapping[str, float | None],
    eligible_sector: Iterable[str],
    eligible_universe: Iterable[str],
) -> dict[str, float | None]:
    """Apply the eight frozen V1 formulas to already selected PIT values."""
    output: dict[str, float | None] = {}
    for horizon in _HORIZONS:
        output[f"return_relative_sector_{horizon}d_raw"] = _difference(
            stock_returns.get(horizon), sector_returns.get(horizon)
        )
        output[f"return_relative_market_{horizon}d_raw"] = _difference(
            stock_returns.get(horizon), market_returns.get(horizon)
        )
    output["momentum_sector_percentile"] = percentile_in_universe(
        security_id, return_120d_values, eligible_sector
    )
    output["momentum_universe_percentile"] = percentile_in_universe(
        security_id, return_120d_values, eligible_universe
    )
    return output


def _validate_feature_at_prediction(row: FeatureValue, prediction: datetime) -> None:
    if not isinstance(row, FeatureValue):
        raise TypeError("relative feature inputs must be FeatureValue records")
    assert_pit_safe([row], prediction)
    if not row.source.strip() or not row.revision_id.strip():
        raise ValueError("INVALID_FEATURE_PROVENANCE")
    if not isinstance(row.quality, QualityTier):
        raise TypeError("feature quality must be a QualityTier")
    if row.value is not None and _number(row.value) is None:
        raise ValueError("INVALID_RELATIVE_INPUT_VALUE")


def _validate_feature(row: FeatureValue, prediction: datetime, cutoff: datetime) -> None:
    _validate_feature_at_prediction(row, prediction)
    if row.available_at > cutoff or row.max_input_available_at > cutoff:
        raise ValueError("PIT_LEAKAGE:relative_input_after_feature_cutoff")


def _select_direct_returns(
    rows: Mapping[int, FeatureValue], prediction: datetime, cutoff: datetime
) -> dict[int, FeatureValue]:
    selected: dict[int, FeatureValue] = {}
    for horizon, row in rows.items():
        _validate_feature(row, prediction, cutoff)
        if horizon not in _HORIZONS or row.feature != f"return_{horizon}d_raw":
            raise ValueError("RELATIVE_INPUT_FEATURE_MISMATCH")
        selected[horizon] = row
    return {horizon: selected[horizon] for horizon in _HORIZONS if horizon in selected}


def _select_cross_section(
    rows: Iterable[FeatureValue],
    *,
    prediction: datetime,
    cutoff: datetime,
    observation_date: str,
    eligible_ids: frozenset[str],
) -> dict[str, FeatureValue]:
    groups: dict[str, list[FeatureValue]] = defaultdict(list)
    for row in rows:
        if not isinstance(row, FeatureValue):
            raise TypeError("cross-section inputs must be FeatureValue records")
        if row.available_at > cutoff:
            continue
        if (
            row.entity_id in eligible_ids
            and row.feature == "return_120d_raw"
            and row.observation_date == observation_date
        ):
            groups[row.entity_id].append(row)
    selected: dict[str, FeatureValue] = {}
    for security_id in sorted(groups):
        row = latest_known(groups[security_id], cutoff)
        _validate_feature(row, prediction, cutoff)
        selected[security_id] = row
    return selected


def _active(classification: SectorClassification, day: date) -> bool:
    start = _iso_date(classification.active_from, "active_from")
    end = (
        _iso_date(classification.active_to, "active_to")
        if classification.active_to is not None
        else None
    )
    return start <= day and (end is None or day < end)


def _select_classifications(
    rows: Iterable[SectorClassification],
    *,
    cutoff: datetime,
    eligible_ids: frozenset[str],
) -> dict[str, SectorClassification]:
    groups: dict[tuple[str, str], list[SectorClassification]] = defaultdict(list)
    for row in rows:
        if not isinstance(row, SectorClassification):
            raise TypeError("sector classifications must be SectorClassification records")
        if row.available_at <= cutoff and row.security_id in eligible_ids:
            groups[(row.security_id, row.active_from)].append(row)
    active: dict[str, list[SectorClassification]] = defaultdict(list)
    for group in groups.values():
        row = latest_known(group, cutoff)
        if _active(row, cutoff.date()):
            active[row.security_id].append(row)
    selected = {}
    for security_id, candidates in active.items():
        if len(candidates) != 1:
            raise ValueError("AMBIGUOUS_HISTORICAL_SECTOR_CLASSIFICATION")
        selected[security_id] = candidates[0]
    return selected


def _require_consistent_entity(rows: Mapping[int, FeatureValue], label: str) -> None:
    identities = {row.entity_id for row in rows.values()}
    if len(identities) > 1 or (identities and None in identities):
        raise ValueError(f"INCONSISTENT_{label}_ENTITY")


def build_relative_features(
    *,
    security_id: str,
    region: Region,
    as_of: datetime,
    universe_index: UniverseIndex,
    stock_returns: Mapping[int, FeatureValue],
    cross_section_returns: Iterable[FeatureValue],
    sector_benchmark_returns: Mapping[int, FeatureValue],
    market_benchmark_returns: Mapping[int, FeatureValue],
    sector_classifications: Iterable[SectorClassification],
) -> RelativeFeatureSnapshot:
    """Build one security's Task 3 outputs from explicit historical evidence.

    Membership is resolved only through the supplied ``UniverseIndex`` at the
    historical feature EOD.  Future-unavailable values and classification
    revisions are ignored before vintage selection; selected input clocks must
    still pass the canonical PIT guard and cannot extend beyond that EOD.
    """
    prediction = _require_aware(as_of, "as_of")
    if not isinstance(universe_index, UniverseIndex):
        raise TypeError("universe_index must be a UniverseIndex")
    if region not in (Region.US, Region.EU):
        raise ValueError("region must be US or EU")

    # The target's supplied historical feature metadata identifies the calendar;
    # querying membership at prediction time here would reintroduce a current-
    # universe fallback for a prior-EOD snapshot.
    known_stock_metadata = list(stock_returns.values())
    for row in known_stock_metadata:
        _validate_feature_at_prediction(row, prediction)
    exchanges = {row.exchange for row in known_stock_metadata}
    regions = {row.region for row in known_stock_metadata}
    entities = {row.entity_id for row in known_stock_metadata}
    if not known_stock_metadata:
        raise ValueError("NO_AVAILABLE_STOCK_RETURN_FEATURES")
    if exchanges == {None} or len(exchanges) != 1:
        raise ValueError("INCONSISTENT_STOCK_RETURN_EXCHANGE")
    if regions != {region} or entities != {security_id}:
        raise ValueError("STOCK_RETURN_ENTITY_MISMATCH")
    observation_dates = {row.observation_date for row in known_stock_metadata}
    if len(observation_dates) != 1:
        raise ValueError("UNALIGNED_STOCK_RETURN_OBSERVATIONS")
    observation_date = next(iter(observation_dates))
    cutoff = eligible_session_close(
        next(iter(exchanges)), _iso_date(observation_date, "observation_date")
    )
    if cutoff is None:
        raise ValueError("INVALID_STOCK_OBSERVATION_SESSION")
    if cutoff > prediction:
        raise ValueError("PIT_LEAKAGE:stock_observation_after_prediction")

    eligible_securities = tuple(universe_index.eligible_universe(cutoff, region))
    eligible_by_id: dict[str, Security] = {row.security_id: row for row in eligible_securities}
    target = eligible_by_id.get(security_id)
    if target is None:
        raise ValueError("INELIGIBLE_SECURITY_AT_FEATURE_CUTOFF")
    eligible_ids = frozenset(eligible_by_id)

    selected_stock = _select_direct_returns(stock_returns, prediction, cutoff)
    selected_sector = _select_direct_returns(sector_benchmark_returns, prediction, cutoff)
    selected_market = _select_direct_returns(market_benchmark_returns, prediction, cutoff)
    if not selected_stock:
        raise ValueError("NO_AVAILABLE_STOCK_RETURN_FEATURES")
    if any(row.entity_id != security_id for row in selected_stock.values()):
        raise ValueError("STOCK_RETURN_ENTITY_MISMATCH")
    _require_consistent_entity(selected_sector, "SECTOR_BENCHMARK")
    _require_consistent_entity(selected_market, "MARKET_BENCHMARK")

    for rows in (selected_sector, selected_market):
        if any(row.observation_date != observation_date for row in rows.values()):
            raise ValueError("UNALIGNED_BENCHMARK_RETURN_OBSERVATIONS")

    selected_cross = _select_cross_section(
        (*cross_section_returns, *selected_stock.values()),
        prediction=prediction,
        cutoff=cutoff,
        observation_date=observation_date,
        eligible_ids=eligible_ids,
    )
    selected_classifications = _select_classifications(
        sector_classifications, cutoff=cutoff, eligible_ids=eligible_ids
    )
    target_classification = selected_classifications.get(security_id)
    if target_classification is not None and any(
        row.entity_id != target_classification.sector_id
        for row in selected_sector.values()
    ):
        raise ValueError("SECTOR_BENCHMARK_ENTITY_MISMATCH")
    sector_ids = (
        frozenset(
            member_id
            for member_id, classification in selected_classifications.items()
            if classification.sector_id == target_classification.sector_id
        )
        if target_classification is not None
        else frozenset()
    )

    raw_values = compute_relative_features(
        security_id,
        stock_returns={horizon: row.value for horizon, row in selected_stock.items()},
        sector_returns=(
            {horizon: row.value for horizon, row in selected_sector.items()}
            if target_classification is not None
            else {}
        ),
        market_returns={horizon: row.value for horizon, row in selected_market.items()},
        return_120d_values={member_id: row.value for member_id, row in selected_cross.items()},
        eligible_sector=sector_ids,
        eligible_universe=eligible_ids,
    )
    definitions = tuple(d for d in FeatureRegistry.v1() if d.domain == "relative_strength")
    if set(raw_values) != {definition.name for definition in definitions}:
        raise ValueError("TASK3_REGISTRY_MISMATCH")

    evidence: tuple[object, ...] = (
        *selected_stock.values(),
        *selected_sector.values(),
        *selected_market.values(),
        *selected_cross.values(),
        *selected_classifications.values(),
        *eligible_securities,
    )
    quality = max((row.quality for row in evidence), key=_QUALITY_ORDER.__getitem__)
    max_input_available_at = max(
        [
            max(row.available_at, row.max_input_available_at)
            for row in evidence
            if isinstance(row, FeatureValue)
        ]
        + [row.available_at for row in evidence if not isinstance(row, FeatureValue)]
    )
    outputs = tuple(
        FeatureValue(
            feature=definition.name,
            entity_id=security_id,
            observation_date=observation_date,
            as_of=prediction,
            value=raw_values[definition.name],
            max_input_available_at=max_input_available_at,
            available_at=cutoff,
            quality=quality,
            source="verified_relative_features",
            revision_id="features-v1",
            region=region,
            exchange=target.exchange,
        )
        for definition in definitions
    )
    assert_pit_safe(outputs, prediction)
    return RelativeFeatureSnapshot(
        features=outputs,
        eligible_security_ids=tuple(sorted(eligible_ids)),
        selected_cross_section=tuple(selected_cross[key] for key in sorted(selected_cross)),
        selected_classifications=tuple(
            selected_classifications[key] for key in sorted(selected_classifications)
        ),
        selected_stock_returns=tuple(selected_stock[horizon] for horizon in _HORIZONS if horizon in selected_stock),
        selected_sector_benchmark_returns=tuple(
            selected_sector[horizon] for horizon in _HORIZONS if horizon in selected_sector
        ),
        selected_market_benchmark_returns=tuple(
            selected_market[horizon] for horizon in _HORIZONS if horizon in selected_market
        ),
    )
