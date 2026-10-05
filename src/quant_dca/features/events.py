"""Point-in-time scheduled-event distance and risk features."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import exchange_calendars

from quant_dca.calendars.service import (
    MIC_CALENDARS,
    is_eligible_session,
    previous_eligible_eod,
)
from quant_dca.features.registry import FeatureRegistry
from quant_dca.point_in_time.asof import assert_pit_safe, latest_known
from quant_dca.types import FeatureValue, QualityTier, Region, Security


_EVENT_NAMES = tuple(
    definition.name for definition in FeatureRegistry.v1()
    if definition.domain == "event_calendar"
)
_EVENT_TYPES = frozenset({"earnings", "policy_decision", "inflation_release"})
_QUALITY_ORDER = {QualityTier.A: 0, QualityTier.B: 1, QualityTier.C: 2}


def _aware(value: object, field: str) -> datetime:
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


def days_until_known_event(
    prediction_date: str, event_date: str, announced_at: str,
) -> int | None:
    """Illustrative date-only distance with a conservative availability gate.

    Date granularity cannot establish ordering within the announcement day, so
    only an announcement on an earlier date can make the future event known.
    Evidenced production features use :func:`build_event_features` instead.
    """
    prediction = _iso_date(prediction_date, "prediction_date")
    event = _iso_date(event_date, "event_date")
    announced = _iso_date(announced_at, "announced_at")
    if announced >= prediction or event < prediction:
        return None
    return (event - prediction).days


@dataclass(frozen=True, slots=True, kw_only=True)
class ScheduledEvent:
    """One announced-calendar version, including cancellations/reschedules."""

    event_id: str
    event_type: str
    event_date: str
    event_at: datetime
    announced_at: datetime
    available_at: datetime
    status: str
    quality: QualityTier
    source: str
    revision_id: str
    security_id: str | None = None
    region: Region | None = None
    monetary_jurisdiction: str | None = None
    published_at: datetime | None = None
    revised_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.event_id or not self.source or not self.revision_id:
            raise ValueError("event identity and provenance must be non-empty")
        if self.event_type not in _EVENT_TYPES:
            raise ValueError(f"unsupported event_type: {self.event_type}")
        if self.status not in {"scheduled", "cancelled"}:
            raise ValueError("event status must be scheduled or cancelled")
        event_day = _iso_date(self.event_date, "event_date")
        event_time = _aware(self.event_at, "event_at")
        announced = _aware(self.announced_at, "announced_at")
        available = _aware(self.available_at, "available_at")
        if event_time.date() != event_day:
            raise ValueError("event_at must fall on event_date in its supplied timezone")
        if announced > available:
            raise ValueError("announced_at cannot be after available_at")
        for field in ("published_at", "revised_at"):
            value = getattr(self, field)
            if value is not None and _aware(value, field) > available:
                raise ValueError(f"{field} cannot be after available_at")
        if self.published_at is not None and self.revised_at is not None and self.revised_at < self.published_at:
            raise ValueError("revised_at cannot precede published_at")
        if not isinstance(self.quality, QualityTier):
            raise TypeError("quality must be a QualityTier")
        dimensions = {
            "earnings": bool(self.security_id),
            "policy_decision": bool(self.monetary_jurisdiction),
            "inflation_release": isinstance(self.region, Region),
        }
        if not dimensions[self.event_type]:
            raise ValueError(f"{self.event_type} is missing its relevance key")


@dataclass(frozen=True, slots=True)
class EventFeatureSnapshot:
    features: tuple[FeatureValue, ...]
    selected: dict[str, ScheduledEvent | None]
    dependencies: dict[str, tuple[ScheduledEvent, ...]]


def _relevant(row: ScheduledEvent, security: Security) -> bool:
    if row.event_type == "earnings":
        return row.security_id == security.security_id
    if row.event_type == "policy_decision":
        return row.monetary_jurisdiction == security.monetary_jurisdiction
    return row.region == security.region


def _known_versions(
    events: tuple[ScheduledEvent, ...], cutoff: datetime,
) -> tuple[dict[str, ScheduledEvent], dict[str, tuple[ScheduledEvent, ...]]]:
    grouped: dict[str, list[ScheduledEvent]] = defaultdict(list)
    for row in events:
        if not isinstance(row, ScheduledEvent):
            raise TypeError("events must contain ScheduledEvent records")
        grouped[row.event_id].append(row)
    selected: dict[str, ScheduledEvent] = {}
    known: dict[str, tuple[ScheduledEvent, ...]] = {}
    for event_id, rows in grouped.items():
        try:
            selected[event_id] = latest_known(rows, cutoff)
        except LookupError:
            continue
        known[event_id] = tuple(row for row in rows if row.available_at <= cutoff)
    return selected, known


def _exchange_day(exchange: str, instant: datetime) -> date:
    try:
        timezone = exchange_calendars.get_calendar(MIC_CALENDARS[exchange]).tz
    except KeyError:
        # Keep the calendar service's public unsupported-MIC error contract.
        is_eligible_session(exchange, instant.date())
        raise AssertionError("unreachable")
    return instant.astimezone(timezone).date()


def _session_distance(exchange: str, cutoff: datetime, event: ScheduledEvent) -> int:
    event_day = _exchange_day(exchange, event.event_at)
    cursor = _exchange_day(exchange, cutoff) + timedelta(days=1)
    count = 0
    while cursor <= event_day:
        if is_eligible_session(exchange, cursor):
            count += 1
        cursor += timedelta(days=1)
    return count


def build_event_features(
    *, security: Security, as_of: datetime, events: Iterable[ScheduledEvent],
) -> EventFeatureSnapshot:
    """Build all six registered event features using the announced PIT calendar."""
    prediction = _aware(as_of, "as_of")
    if not isinstance(security, Security):
        raise TypeError("security must be a canonical Security")
    cutoff = previous_eligible_eod(security.exchange, prediction)
    assert_pit_safe((security,), cutoff)
    if security.quality is QualityTier.C:
        raise ValueError("QUALITY_BELOW_FLOOR:classification_requires_tier_b")
    effective_day = _exchange_day(security.exchange, cutoff)
    active_from = _iso_date(security.active_from, "active_from")
    active_to = None if security.active_to is None else _iso_date(security.active_to, "active_to")
    if effective_day < active_from or (active_to is not None and effective_day >= active_to):
        raise ValueError("INACTIVE_SECURITY_CLASSIFICATION")
    if not security.monetary_jurisdiction:
        raise ValueError("UNKNOWN_MONETARY_JURISDICTION")

    current, histories = _known_versions(tuple(events), cutoff)
    causal: dict[str, list[ScheduledEvent]] = defaultdict(list)
    for event_id, versions in histories.items():
        # Scope dependencies to identities that were plausible future events
        # for this security in at least one version known by the cutoff.  The
        # identity's latest version then captures cancellations and revisions
        # that remove or change relevance without pulling in unrelated events.
        kinds = {
            row.event_type for row in versions
            if _relevant(row, security) and row.event_at > cutoff
        }
        for kind in kinds:
            causal[kind].append(current[event_id])

    candidates: dict[str, list[ScheduledEvent]] = defaultdict(list)
    for kind in _EVENT_TYPES:
        for row in causal[kind]:
            if row.quality is QualityTier.C:
                raise ValueError("QUALITY_BELOW_FLOOR:event_calendar_requires_tier_b")
    for row in current.values():
        if not _relevant(row, security):
            continue
        if row.status == "scheduled" and row.event_at > cutoff:
            candidates[row.event_type].append(row)
    selected = {
        kind: min(candidates[kind], key=lambda row: row.event_at)
        if candidates[kind] else None
        for kind in _EVENT_TYPES
    }

    def distance(kind: str) -> float | None:
        row = selected[kind]
        return None if row is None else float(_session_distance(security.exchange, cutoff, row))

    earnings = distance("earnings")
    policy = distance("policy_decision")
    inflation = distance("inflation_release")
    calculated = {
        "days_to_announced_earnings_raw": earnings,
        "announced_earnings_within_5d": None if earnings is None else float(0 <= earnings <= 5),
        "announced_earnings_within_20d": None if earnings is None else float(0 <= earnings <= 20),
        "days_to_relevant_policy_decision_raw": policy,
        "major_policy_event_within_5d": None if policy is None else float(0 <= policy <= 5),
        "days_to_relevant_inflation_release_raw": inflation,
    }
    if set(calculated) != set(_EVENT_NAMES):
        raise ValueError("TASK5_EVENT_REGISTRY_MISMATCH")
    kind_by_feature = {
        "days_to_announced_earnings_raw": "earnings",
        "announced_earnings_within_5d": "earnings",
        "announced_earnings_within_20d": "earnings",
        "days_to_relevant_policy_decision_raw": "policy_decision",
        "major_policy_event_within_5d": "policy_decision",
        "days_to_relevant_inflation_release_raw": "inflation_release",
    }
    features = []
    for name in _EVENT_NAMES:
        kind = kind_by_feature[name]
        inputs = (security, *causal[kind])
        features.append(FeatureValue(
            feature=name, entity_id=security.security_id,
            observation_date=cutoff.date().isoformat(), as_of=prediction,
            value=calculated[name],
            max_input_available_at=max(row.available_at for row in inputs),
            available_at=cutoff,
            quality=max((row.quality for row in inputs), key=_QUALITY_ORDER.__getitem__),
            source="announced_event_calendar_features", revision_id="features-v1",
            currency=security.currency, region=security.region, exchange=security.exchange,
        ))
    dependencies = {
        kind: tuple(sorted(causal[kind], key=lambda row: row.event_id))
        for kind in _EVENT_TYPES
    }
    result = EventFeatureSnapshot(tuple(features), selected, dependencies)
    assert_pit_safe(result.features, prediction)
    return result
