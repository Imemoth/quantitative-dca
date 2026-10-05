"""Explicit validation and lossless quarantine for canonical market data."""

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
import math
import numbers
import re
from typing import Any

from quant_dca.types import QualityTier, Region, Security
from quant_dca.calendars.service import assert_session_clock
from quant_dca.point_in_time.asof import latest_known, revision_order


_MISSING = object()
_CURRENCY = re.compile(r"[A-Z]{3}")
_EXCHANGE = re.compile(r"[A-Z0-9]{4}")
_SECURITY_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]*")


@dataclass(frozen=True, slots=True)
class DiscontinuityEvidence:
    """Auditable evidence that explains one screened price transition."""

    security_id: str
    prior_session: str
    session_date: str
    kind: str
    source: str
    reference: str
    verified_at: datetime

    def __post_init__(self) -> None:
        if self.kind not in {"corporate_action", "market_move"}:
            raise ValueError("Unsupported discontinuity evidence kind")
        if not self.security_id or not self.source.strip() or not self.reference.strip():
            raise ValueError("Discontinuity evidence requires security, source and reference")
        try:
            prior = date.fromisoformat(self.prior_session)
            current = date.fromisoformat(self.session_date)
        except (TypeError, ValueError):
            raise ValueError("Discontinuity evidence requires ISO session dates") from None
        if prior >= current:
            raise ValueError("Discontinuity evidence sessions must be chronological")
        if not _aware(self.verified_at):
            raise ValueError("Discontinuity evidence verification time must be timezone-aware")


@dataclass(frozen=True, slots=True)
class QuarantinedRow:
    """An original input object and every validation reason found for it."""

    row: object
    reasons: tuple[str, ...]

    @property
    def reason(self) -> str:
        return self.reasons[0]


@dataclass(frozen=True, slots=True)
class ValidationResult:
    valid_rows: list[object]
    quarantined_rows: list[QuarantinedRow]
    reasons: dict[str, int]
    discontinuity_evidence: list[DiscontinuityEvidence]


def _get(row: object, name: str, default: Any = _MISSING) -> Any:
    if isinstance(row, Mapping):
        return row.get(name, default)
    return getattr(row, name, default)


def _aware(value: object) -> bool:
    return (isinstance(value, datetime) and value.tzinfo is not None
            and value.utcoffset() is not None)


def _iso_date(value: object) -> date | None:
    try:
        return date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


def _finite_number(value: object) -> bool:
    return isinstance(value, numbers.Real) and not isinstance(value, bool) and math.isfinite(value)


def _add(reasons: list[str], reason: str) -> None:
    if reason not in reasons:
        reasons.append(reason)


def _validate_provenance(row: object, reasons: list[str]) -> None:
    source = _get(row, "source")
    if not isinstance(source, str) or not source.strip():
        _add(reasons, "MISSING_SOURCE")
    revision = _get(row, "revision_id")
    if not isinstance(revision, str) or not revision.strip():
        _add(reasons, "MISSING_REVISION_ID")
    if not isinstance(_get(row, "quality"), QualityTier):
        _add(reasons, "INVALID_QUALITY")

    for field in ("available_at", "published_at", "revised_at"):
        value = _get(row, field)
        if value is _MISSING:
            if field == "available_at":
                _add(reasons, "MISSING_TIMESTAMP:available_at")
            continue
        if value is None and field != "available_at":
            continue
        if not _aware(value):
            _add(reasons, f"INVALID_TIMESTAMP:{field}")

    available = _get(row, "available_at")
    published = _get(row, "published_at")
    revised = _get(row, "revised_at")
    if _aware(available) and _aware(published) and available < published:
        _add(reasons, "AVAILABILITY_BEFORE_PUBLICATION")
    if _aware(available) and _aware(revised) and available < revised:
        _add(reasons, "AVAILABILITY_BEFORE_REVISION")


def _validate_price_numbers(row: object, reasons: list[str], *, allow_missing_volume: bool = False) -> None:
    high, low = _get(row, "high"), _get(row, "low")
    if _finite_number(high) and _finite_number(low) and high < low:
        _add(reasons, "HIGH_BELOW_LOW")

    for field in ("open", "high", "low", "close"):
        value = _get(row, field)
        if value is _MISSING or value is None:
            _add(reasons, "MISSING_PRICE")
        elif not _finite_number(value):
            _add(reasons, "NONFINITE_PRICE")
        elif value <= 0:
            _add(reasons, "NONPOSITIVE_PRICE")

    volume = _get(row, "volume")
    if volume is _MISSING or volume is None:
        if not allow_missing_volume:
            _add(reasons, "MISSING_VOLUME")
    elif not _finite_number(volume):
        _add(reasons, "NONFINITE_VOLUME")
    elif volume < 0:
        _add(reasons, "NEGATIVE_VOLUME")

    if all(_finite_number(value) for value in (high, low)) and high >= low:
        for field in ("open", "close"):
            value = _get(row, field)
            if _finite_number(value) and not low <= value <= high:
                _add(reasons, "PRICE_OUTSIDE_RANGE")


def _validate_bar_metadata(row: object, reasons: list[str]) -> None:
    security_id = _get(row, "security_id")
    if security_id is _MISSING or security_id is None or (
            isinstance(security_id, str) and not security_id.strip()):
        _add(reasons, "MISSING_SECURITY_ID")
    elif not isinstance(security_id, str) or _SECURITY_ID.fullmatch(security_id) is None:
        _add(reasons, "INVALID_SECURITY_ID")
    if _iso_date(_get(row, "session_date")) is None:
        _add(reasons, "INVALID_SESSION_DATE")
    currency = _get(row, "currency")
    if not isinstance(currency, str) or _CURRENCY.fullmatch(currency) is None:
        _add(reasons, "INVALID_CURRENCY")
    if not isinstance(_get(row, "region"), Region):
        _add(reasons, "INVALID_REGION")
    exchange = _get(row, "exchange")
    if not isinstance(exchange, str) or _EXCHANGE.fullmatch(exchange) is None:
        _add(reasons, "INVALID_EXCHANGE")
    if _get(row, "price_basis", "unadjusted") != "unadjusted":
        _add(reasons, "INVALID_PRICE_BASIS")

    for field in ("session_open_at", "session_close_at"):
        value = _get(row, field)
        if value is _MISSING:
            _add(reasons, f"MISSING_TIMESTAMP:{field}")
        elif not _aware(value):
            _add(reasons, f"INVALID_TIMESTAMP:{field}")
    opened, closed, available = (_get(row, field) for field in
                                 ("session_open_at", "session_close_at", "available_at"))
    if _aware(opened) and _aware(closed) and opened > closed:
        _add(reasons, "INVALID_SESSION_CHRONOLOGY")
    if _aware(closed) and _aware(available) and available < closed:
        _add(reasons, "AVAILABILITY_BEFORE_SESSION_CLOSE")
    try:
        assert_session_clock(exchange, _get(row, "session_date"), opened, closed)
    except ValueError as exc:
        _add(reasons, str(exc))


def _mapping_reasons(row: object, securities: list[Security],
                     as_of: datetime | None = None) -> list[str]:
    session = _iso_date(_get(row, "session_date"))
    available = as_of or _get(row, "available_at")
    if session is None or not _aware(available):
        return []
    candidates = []
    for security in securities:
        if (security.security_id == _get(row, "security_id")
                and security.available_at <= available):
            candidates.append(security)
    if not candidates:
        return ["MISSING_SECURITY_MAPPING"]
    # Exact duplicated mapping evidence remains an admission conflict. Resolve
    # legitimate versions before active interval relevance (a delisting can move).
    if any(left == right for i, left in enumerate(candidates) for right in candidates[i+1:]):
        return ["AMBIGUOUS_SECURITY_MAPPING"]
    try:
        security = latest_known(candidates, available)
    except (ValueError, TypeError, LookupError):
        return ["AMBIGUOUS_SECURITY_MAPPING"]
    active_from, active_to = _iso_date(security.active_from), _iso_date(security.active_to)
    if (active_from is None or (security.active_to is not None and active_to is None)
            or not (active_from <= session and (active_to is None or session < active_to))):
        return ["MISSING_SECURITY_MAPPING"]
    reasons = []
    if security.currency != _get(row, "currency"):
        reasons.append("CURRENCY_MAPPING_MISMATCH")
    if security.exchange != _get(row, "exchange"):
        reasons.append("EXCHANGE_MAPPING_MISMATCH")
    if security.region != _get(row, "region"):
        reasons.append("REGION_MAPPING_MISMATCH")
    return reasons


def _finish(rows: list[object], row_reasons: list[list[str]],
            accepted: list[DiscontinuityEvidence] | None = None) -> ValidationResult:
    valid = [row for row, reasons in zip(rows, row_reasons) if not reasons]
    quarantined = [QuarantinedRow(row, tuple(reasons)) for row, reasons in
                   zip(rows, row_reasons) if reasons]
    counts = Counter(reason for item in quarantined for reason in item.reasons)
    return ValidationResult(valid, quarantined, dict(counts), accepted or [])


def validate_ohlcv(rows: Iterable[object], *, securities: Iterable[Security] | None = None,
                   max_price_ratio: float = 5.0,
                   discontinuity_evidence: Iterable[DiscontinuityEvidence] = (),
                   as_of: datetime | None = None,
                   allow_missing_volume: bool = False) -> ValidationResult:
    """Validate bars without changing values, ordering, or object identity.

    Default admission preserves explicitly ordered revisions and screens each
    against prior sessions knowable at its availability. ``as_of`` instead
    selects one version per session and re-screens that coherent PIT panel.
    Consumers of versioned history must use this second stage. Evidence still
    must be available by the version's own availability, never backfilled.

    ``allow_missing_volume=True`` is an explicit price-feature view, not raw
    canonical admission. Only absent/None volume is tolerated; prices, present
    volume, provenance, calendars and discontinuities remain fully checked.
    Missing volume is never filled, and cannot establish a liquidity input.
    """
    if not _finite_number(max_price_ratio) or max_price_ratio <= 1:
        raise ValueError("max_price_ratio must be a finite number greater than one")
    materialized = list(rows)
    if as_of is not None:
        if not _aware(as_of):
            raise ValueError("PIT_INVALID_TIMESTAMP:as_of")
        groups = defaultdict(list)
        for row in materialized:
            groups[(_get(row, "security_id"), _get(row, "session_date"))].append(row)
        materialized = []
        for group in groups.values():
            try:
                materialized.append(latest_known(group, as_of))
            except LookupError:
                continue
    mappings = None if securities is None else list(securities)
    evidence = list(discontinuity_evidence)
    if any(not isinstance(item, DiscontinuityEvidence) for item in evidence):
        raise ValueError("discontinuity_evidence must contain DiscontinuityEvidence records")
    row_reasons = [[] for _ in materialized]

    for row, reasons in zip(materialized, row_reasons):
        _validate_price_numbers(row, reasons, allow_missing_volume=allow_missing_volume)
        _validate_bar_metadata(row, reasons)
        _validate_provenance(row, reasons)
        if mappings is not None:
            for reason in _mapping_reasons(row, mappings, as_of):
                _add(reasons, reason)

    duplicate_groups: dict[tuple[object, object], list[int]] = defaultdict(list)
    for index, row in enumerate(materialized):
        key = (_get(row, "security_id"), _get(row, "session_date"))
        if _MISSING not in key:
            duplicate_groups[key].append(index)
    duplicate_indices = set()
    for group in duplicate_groups.values():
        if len(group) < 2:
            continue
        try:
            clocks = [revision_order(materialized[i]) for i in group]
            ids = [_get(materialized[i], "revision_id") for i in group]
            legitimate = (None not in clocks and len(set(clocks)) == len(group)
                          and len({clock[0] for clock in clocks}) == 1
                          and len(set(ids)) == len(group))
        except (TypeError, ValueError):
            legitimate = False
        if not legitimate:
            duplicate_indices.update(group)
    for index in duplicate_indices:
        _add(row_reasons[index], "DUPLICATE_SESSION")

    accepted: list[DiscontinuityEvidence] = []
    previous = defaultdict(list)
    first_sessions = defaultdict(set)
    last_first_session = {}
    for index, row in enumerate(materialized):
        security_id = _get(row, "security_id")
        session_text = _get(row, "session_date")
        session = _iso_date(session_text)
        close = _get(row, "close")
        if (security_id is _MISSING or session is None or not _finite_number(close)
                or close <= 0 or index in duplicate_indices):
            continue
        matched_evidence = None
        if session not in first_sessions[security_id]:
            if security_id in last_first_session and session < last_first_session[security_id]:
                _add(row_reasons[index], "NONMONOTONIC_SESSION")
                continue
            first_sessions[security_id].add(session)
            last_first_session[security_id] = session
        if row_reasons[index]:
            continue
        cutoff = as_of or _get(row, "available_at")
        anchors = defaultdict(list)
        for candidate in previous[security_id]:
            if _get(candidate, "session_date") < session_text and _get(candidate, "available_at") <= cutoff:
                anchors[_get(candidate, "session_date")].append(candidate)
        if anchors:
            prior_text = max(anchors)
            try:
                prior = latest_known(anchors[prior_text], cutoff)
            except (LookupError, ValueError, TypeError):
                _add(row_reasons[index], "AMBIGUOUS_DISCONTINUITY_ANCHOR")
                continue
            prior_close = _get(prior, "close")
            ratio = max(close / prior_close, prior_close / close)
            if ratio > max_price_ratio:
                match = next((item for item in evidence
                              if item.security_id == security_id
                              and item.prior_session == prior_text
                              and item.session_date == session_text
                              and _aware(_get(row, "available_at"))
                              and item.verified_at <= _get(row, "available_at")), None)
                if match is None:
                    _add(row_reasons[index], "UNEXPLAINED_DISCONTINUITY")
                else:
                    matched_evidence = match
        if not row_reasons[index]:
            previous[security_id].append(row)
            if matched_evidence is not None and matched_evidence not in accepted:
                accepted.append(matched_evidence)

    return _finish(materialized, row_reasons, accepted)


def validate_observations(rows: Iterable[object]) -> ValidationResult:
    """Validate generic observations while preserving missing values in quarantine."""
    materialized = list(rows)
    row_reasons = [[] for _ in materialized]
    for row, reasons in zip(materialized, row_reasons):
        value = _get(row, "value")
        if value is _MISSING or value is None:
            _add(reasons, "MISSING_VALUE")
        elif not _finite_number(value):
            _add(reasons, "NONFINITE_VALUE")
        if _iso_date(_get(row, "observation_date")) is None:
            _add(reasons, "INVALID_OBSERVATION_DATE")
        series = _get(row, "series")
        if not isinstance(series, str) or not series.strip():
            _add(reasons, "MISSING_SERIES")
        _validate_provenance(row, reasons)
    return _finish(materialized, row_reasons)
