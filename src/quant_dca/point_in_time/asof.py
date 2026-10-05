"""Fail-closed helpers for point-in-time feature reconstruction."""
from collections.abc import Iterable, Mapping
from datetime import date, datetime
from typing import TypeVar


T = TypeVar("T")
_MISSING = object()
_GROUP_FIELDS = ("series", "feature", "entity_id", "observation_date")


def _get(row: object, field: str) -> object:
    if isinstance(row, Mapping):
        return row.get(field, _MISSING)
    return getattr(row, field, _MISSING)


def _aware(value: object) -> bool:
    return (
        isinstance(value, datetime)
        and value.tzinfo is not None
        and value.utcoffset() is not None
    )


def _require_timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"PIT_INVALID_TIMESTAMP:{field}")
    if not _aware(value):
        raise ValueError(f"PIT_INVALID_TIMESTAMP:{field}")
    return value


def _validate_chronology(row: object) -> tuple[datetime, datetime | None]:
    available = _require_timestamp(_get(row, "available_at"), "available_at")
    timestamps: dict[str, datetime | None] = {}
    for field in ("published_at", "revised_at"):
        value = _get(row, field)
        if value is _MISSING or value is None:
            timestamps[field] = None
        else:
            timestamps[field] = _require_timestamp(value, field)

    published = timestamps["published_at"]
    revised = timestamps["revised_at"]
    if published is not None and available < published:
        raise ValueError("PIT_INVALID_CHRONOLOGY:availability_before_publication")
    if revised is not None and available < revised:
        raise ValueError("PIT_INVALID_CHRONOLOGY:availability_before_revision")
    if published is not None and revised is not None and revised < published:
        raise ValueError("PIT_INVALID_CHRONOLOGY:revision_before_publication")
    return available, revised


def _group_key(row: object) -> tuple[str, object, object, object] | None:
    if _get(row, "security_id") is not _MISSING and _get(row, "feature") is _MISSING:
        for identity in ("action_id", "session_date", "universe_id"):
            if _get(row, identity) is not _MISSING:
                return identity, _get(row, "security_id"), _get(row, identity), None
        return "security", _get(row, "security_id"), None, None
    values = {field: _get(row, field) for field in _GROUP_FIELDS}
    present = {field for field, value in values.items() if value is not _MISSING}
    if not present:
        return None

    names = [name for name in ("series", "feature") if name in present]
    if len(names) != 1 or "entity_id" not in present or "observation_date" not in present:
        raise ValueError("PIT_AMBIGUOUS_GROUP:series/entity/period must be explicit")
    name = names[0]
    return name, values[name], values["entity_id"], values["observation_date"]


def _same_record(left: object, right: object) -> bool:
    try:
        result = left == right
        return result if isinstance(result, bool) else False
    except (TypeError, ValueError):
        return False


def latest_known(rows: Iterable[T], as_of: datetime) -> T:
    """Return the latest knowable vintage for one logical observation group.

    Rows may be canonical records or mappings. Mappings containing only
    ``value`` and ``available_at`` form one implicit group. Once identity
    metadata is supplied, every row must identify the same series (or feature),
    entity and observation period.
    """
    cutoff = _require_timestamp(as_of, "as_of")
    materialized = list(rows)
    validated: list[tuple[T, datetime, datetime | None]] = []
    keys = []
    for row in materialized:
        keys.append(_group_key(row))
        available, revised = _validate_chronology(row)
        revision_order(row)
        validated.append((row, available, revised))

    explicit = [key for key in keys if key is not None]
    if explicit and len(explicit) != len(keys):
        raise ValueError("PIT_AMBIGUOUS_GROUP:implicit and explicit identities mixed")
    if explicit and any(key != explicit[0] for key in explicit[1:]):
        raise ValueError("PIT_MIXED_GROUP:latest_known accepts one series/entity/period")

    eligible = [item for item in validated if item[1] <= cutoff]
    if not eligible:
        raise LookupError("PIT_NO_KNOWN_VINTAGE")

    # Availability gates knowledge; it never makes an older canonical version
    # economically newer. Date-level vintages remain dates, not invented times.
    unique = []
    for item in eligible:
        if not any(_same_record(item[0], other[0]) for other in unique):
            unique.append(item)
    if len(unique) == 1:
        return unique[0][0]
    orders = [revision_order(item[0]) for item in unique]
    if all(order is None for order in orders) and not explicit and all(
        _get(item[0], "revision_id") is _MISSING for item in unique
    ):
        # Legacy minimal scalar mappings have no claim to canonical revisions.
        orders = [("availability", item[1]) for item in unique]
    if any(order is None for order in orders) or len({order[0] for order in orders}) != 1:
        raise ValueError("PIT_AMBIGUOUS_VINTAGE:missing or mixed revision chronology")
    if orders[0][0] == "date":
        for i, (item, order) in enumerate(zip(unique, orders)):
            end = _get(item[0], "vintage_end")
            if end is _MISSING or end is None:
                continue
            for other, other_order in zip(unique[i+1:], orders[i+1:]):
                other_end = _get(other[0], "vintage_end")
                if other_end is not _MISSING and other_end is not None and (
                    max(order[1], other_order[1]) <= min(date.fromisoformat(end), date.fromisoformat(other_end))
                ):
                    raise ValueError("PIT_AMBIGUOUS_VINTAGE:overlapping date validity intervals")
    latest_order = max(order[1] for order in orders)
    tied = [item for item, order in zip(unique, orders) if order[1] == latest_order]

    selected = tied[0][0]
    if any(not _same_record(selected, item[0]) for item in tied[1:]):
        raise ValueError("PIT_AMBIGUOUS_VINTAGE:indistinguishable revision order")
    return selected


def revision_order(row: object) -> tuple[str, object] | None:
    """Explicit economic version clock; opaque IDs are never sortable clocks.

    A publication timestamp orders an original without a revision timestamp.
    Date-level vintage_start takes precedence and must not be mixed with an
    intraday clock across versions. Request-clipped equal dates remain ambiguous.
    """
    vintage = _get(row, "vintage_start")
    if vintage is not _MISSING and vintage is not None:
        try:
            start = date.fromisoformat(vintage)
            end = _get(row, "vintage_end")
            if end is not _MISSING and end is not None and date.fromisoformat(end) < start:
                raise ValueError
            return "date", start
        except (TypeError, ValueError):
            raise ValueError("PIT_INVALID_VINTAGE_DATE") from None
    for field in ("revised_at", "published_at"):
        value = _get(row, field)
        if value is not _MISSING and value is not None:
            return "timestamp", _require_timestamp(value, field)
    return None


def assert_pit_safe(
    feature_values: Iterable[datetime | object], prediction_timestamp: datetime
) -> None:
    """Raise ``PIT_LEAKAGE`` if any feature or input was unknown at prediction.

    Bare datetimes are supported as availability timestamps. Canonical
    ``FeatureValue`` objects and equivalent mappings additionally enforce their
    input cutoff. ``computed_at`` is audit metadata for an offline build and is
    deliberately not constrained to the historical prediction instant.
    """
    prediction = _require_timestamp(prediction_timestamp, "prediction_timestamp")
    for value in feature_values:
        if isinstance(value, datetime):
            available = _require_timestamp(value, "feature_available_at")
            if available > prediction:
                raise ValueError("PIT_LEAKAGE:feature_available_after_prediction")
            continue

        available, _ = _validate_chronology(value)
        if available > prediction:
            raise ValueError("PIT_LEAKAGE:feature_available_after_prediction")

        input_value = _get(value, "max_input_available_at")
        as_of_value = _get(value, "as_of")
        is_feature = _get(value, "feature") is not _MISSING
        if is_feature and (input_value is _MISSING or as_of_value is _MISSING):
            raise TypeError("PIT_INVALID_TIMESTAMP:incomplete_feature_provenance")

        if input_value is not _MISSING:
            input_available = _require_timestamp(input_value, "max_input_available_at")
            if input_available > prediction:
                raise ValueError("PIT_LEAKAGE:input_available_after_prediction")
            if input_available > available:
                raise ValueError("PIT_LEAKAGE:input_available_after_feature")
        else:
            input_available = None

        if as_of_value is not _MISSING:
            feature_as_of = _require_timestamp(as_of_value, "as_of")
            if feature_as_of > prediction:
                raise ValueError("PIT_LEAKAGE:feature_as_of_after_prediction")
            if available > feature_as_of:
                raise ValueError("PIT_LEAKAGE:feature_available_after_feature_as_of")
            if input_available is not None and input_available > feature_as_of:
                raise ValueError("PIT_LEAKAGE:input_available_after_feature_as_of")

        computed = _get(value, "computed_at")
        if computed is not _MISSING and computed is not None:
            _require_timestamp(computed, "computed_at")
