"""Causal valuation features on explicitly compatible price/share bases."""

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import math
import statistics

from quant_dca.calendars.service import eligible_session_close, previous_eligible_eod
from quant_dca.features.fundamentals import ReportedFundamentals, select_report
from quant_dca.features.registry import FeatureRegistry
from quant_dca.features.relative import SectorClassification, percentile_in_universe
from quant_dca.point_in_time.asof import assert_pit_safe, latest_known
from quant_dca.types import FeatureValue, QualityTier, Region
from quant_dca.universe.membership import UniverseIndex


_VALUATION_NAMES = tuple(
    definition.name for definition in FeatureRegistry.v1()
    if definition.domain == "valuation"
)
_QUALITY_ORDER = {QualityTier.A: 0, QualityTier.B: 1, QualityTier.C: 2}
_ADMISSIBLE_PRICE_BASES = frozenset({"unadjusted", "split_adjusted_feature"})


def _aware(value: object, field: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field} must be a timezone-aware datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be a timezone-aware datetime")
    return value


def _day(value: object, field: str) -> date:
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


def _divide(numerator: object, denominator: object, *, positive_denominator=False) -> float | None:
    numerator, denominator = _number(numerator), _number(denominator)
    if numerator is None or denominator is None or denominator == 0:
        return None
    if positive_denominator and denominator < 0:
        return None
    return numerator / denominator


def _financial(sector: str | None) -> bool:
    return isinstance(sector, str) and sector.strip().casefold() in {
        "financial", "financials", "banks", "insurance"
    }


def _known_nonfinancial(sector: str | None) -> bool:
    return isinstance(sector, str) and bool(sector.strip()) and not _financial(sector)


def _raw_valuation(
    report: ReportedFundamentals, price: "ValuationPrice", sector: str | None
) -> dict[str, float | None]:
    if price.price_basis not in _ADMISSIBLE_PRICE_BASES:
        raise ValueError("VALUATION_PRICE_BASIS_MISMATCH")
    if (
        (price.price_basis == "unadjusted" and price.per_share_basis != "unadjusted")
        or (
            price.price_basis == "split_adjusted_feature"
            and not price.per_share_basis.startswith("split_adjusted")
        )
    ):
        raise ValueError("VALUATION_UNIT_BASIS_MISMATCH")
    if report.currency != price.currency:
        raise ValueError("VALUATION_CURRENCY_MISMATCH")
    if report.per_share_basis != price.per_share_basis:
        raise ValueError("VALUATION_UNIT_BASIS_MISMATCH")
    close = _number(price.close)
    shares = _number(report.values.get("diluted_shares"))
    if close is None or close <= 0 or shares is None or shares <= 0:
        market_cap = None
    else:
        market_cap = close * shares
    eps = _number(report.values.get("diluted_eps"))
    trailing_pe = None if eps is None or eps <= 0 else _divide(close, eps)
    price_to_sales = _divide(market_cap, report.values.get("revenue"))
    if not _known_nonfinancial(sector):
        ev_to_ebitda = None
        fcf_yield = None
    else:
        net_debt = _number(report.values.get("net_debt"))
        enterprise_value = None if market_cap is None or net_debt is None else market_cap + net_debt
        ev_to_ebitda = _divide(enterprise_value, report.values.get("ebitda"))
        fcf_yield = _divide(report.values.get("free_cash_flow"), market_cap)
    return {
        "trailing_pe_raw": trailing_pe,
        "ev_to_ebitda_raw": ev_to_ebitda,
        "price_to_sales_raw": price_to_sales,
        "fcf_yield_raw": fcf_yield,
    }


def _zscore(values: list[float | None], window: int = 756) -> float | None:
    """Sample z-score of the last value using exactly the causal session window."""
    tail = values[-window:]
    if len(tail) != window or any(_number(value) is None for value in tail):
        return None
    numeric = [float(value) for value in tail if value is not None]
    scale = statistics.stdev(numeric)
    return None if scale == 0 else (numeric[-1] - statistics.mean(numeric)) / scale


@dataclass(frozen=True, slots=True, kw_only=True)
class ValuationPrice:
    """An economic close admitted specifically for per-share valuation use."""

    security_id: str
    session_date: str
    close: float
    session_close_at: datetime
    available_at: datetime
    currency: str
    per_share_basis: str
    price_basis: str
    quality: QualityTier
    source: str
    revision_id: str
    region: Region
    exchange: str
    published_at: datetime | None = None
    revised_at: datetime | None = None

    def __post_init__(self) -> None:
        session = _day(self.session_date, "session_date")
        close_at = _aware(self.session_close_at, "session_close_at")
        available = _aware(self.available_at, "available_at")
        expected = eligible_session_close(self.exchange, session)
        if expected is None or expected != close_at:
            raise ValueError("VALUATION_PRICE_NOT_ACTUAL_SESSION")
        for field in ("published_at", "revised_at"):
            timestamp = getattr(self, field)
            if timestamp is not None and _aware(timestamp, field) > available:
                raise ValueError(f"{field} cannot be after available_at")
        if _number(self.close) is None or self.close <= 0:
            raise ValueError("valuation close must be finite and positive")
        if not self.security_id or not self.currency or not self.per_share_basis:
            raise ValueError("valuation price identity and unit metadata must be non-empty")
        if not self.source.strip() or not self.revision_id.strip():
            raise ValueError("valuation price provenance must be non-empty")
        if not isinstance(self.quality, QualityTier):
            raise TypeError("quality must be a QualityTier")


@dataclass(frozen=True, slots=True)
class ValuationFeatureSnapshot:
    features: tuple[FeatureValue, ...]
    applicability: Mapping[str, bool]
    eligible_security_ids: tuple[str, ...]
    selected_prices: tuple[ValuationPrice, ...]
    selected_reports: tuple[ReportedFundamentals, ...]
    selected_classifications: tuple[SectorClassification, ...]


def _selected_prices(
    prices: Iterable[ValuationPrice], prediction: datetime
) -> dict[str, dict[str, ValuationPrice]]:
    groups: dict[tuple[str, str], list[ValuationPrice]] = defaultdict(list)
    for row in prices:
        if not isinstance(row, ValuationPrice):
            raise TypeError("prices must contain ValuationPrice")
        if (
            row.session_close_at <= prediction
            and row.available_at <= row.session_close_at
        ):
            groups[(row.security_id, row.session_date)].append(row)
    selected: dict[str, dict[str, ValuationPrice]] = defaultdict(dict)
    for (security_id, session), group in groups.items():
        row = latest_known(group, group[0].session_close_at)
        if row.quality is QualityTier.C:
            raise ValueError("QUALITY_BELOW_FLOOR:valuation_price_requires_tier_b")
        if row.price_basis not in _ADMISSIBLE_PRICE_BASES:
            raise ValueError("VALUATION_PRICE_BASIS_MISMATCH")
        selected[security_id][session] = row
    return dict(selected)


def _active_classifications(
    rows: Iterable[SectorClassification], cutoff: datetime, eligible_ids: frozenset[str]
) -> dict[str, SectorClassification]:
    groups: dict[tuple[str, str], list[SectorClassification]] = defaultdict(list)
    for row in rows:
        if not isinstance(row, SectorClassification):
            raise TypeError("classifications must contain SectorClassification")
        if row.security_id in eligible_ids and row.available_at <= cutoff:
            groups[(row.security_id, row.active_from)].append(row)
    candidates: dict[str, list[SectorClassification]] = defaultdict(list)
    for group in groups.values():
        row = latest_known(group, cutoff)
        if row.quality is QualityTier.C:
            raise ValueError("QUALITY_BELOW_FLOOR:classification_requires_tier_b")
        if row.active_from <= cutoff.date().isoformat() and (
            row.active_to is None or cutoff.date().isoformat() < row.active_to
        ):
            candidates[row.security_id].append(row)
    result = {}
    for security_id, active in candidates.items():
        if len(active) != 1:
            raise ValueError("AMBIGUOUS_HISTORICAL_SECTOR_CLASSIFICATION")
        result[security_id] = active[0]
    return result


def _report_or_none(
    reports: tuple[ReportedFundamentals, ...], security_id: str, cutoff: datetime
) -> ReportedFundamentals | None:
    try:
        return select_report(reports, security_id, cutoff)
    except LookupError:
        return None


def _append_unique(rows: list, row: object | None) -> None:
    if row is not None and not any(existing == row for existing in rows):
        rows.append(row)


def build_valuation_features(
    *, security_id: str, region: Region, as_of: datetime,
    reports: Iterable[ReportedFundamentals], prices: Iterable[ValuationPrice],
    universe_index: UniverseIndex,
    sector_classifications: Iterable[SectorClassification],
) -> ValuationFeatureSnapshot:
    """Build registered valuation outputs from causal report and price histories."""
    prediction = _aware(as_of, "as_of")
    if not isinstance(universe_index, UniverseIndex):
        raise TypeError("universe_index must be a UniverseIndex")
    all_reports, all_classifications = tuple(reports), tuple(sector_classifications)
    prices_by_security = _selected_prices(tuple(prices), prediction)
    target_history = prices_by_security.get(security_id, {})
    if not target_history:
        raise LookupError("NO_ADMISSIBLE_VALUATION_PRICE")
    latest_session = max(target_history)
    target_price = target_history[latest_session]
    if target_price.region is not region:
        raise ValueError("VALUATION_REGION_MISMATCH")
    cutoff = target_price.session_close_at
    if cutoff != previous_eligible_eod(target_price.exchange, prediction):
        raise ValueError("STALE_VALUATION_PRICE")
    if any(
        row.exchange != target_price.exchange
        or row.region is not region
        or row.currency != target_price.currency
        for row in target_history.values()
    ):
        raise ValueError("INCONSISTENT_VALUATION_PRICE_HISTORY")
    eligible = tuple(universe_index.eligible_universe(cutoff, region))
    eligible_ids = tuple(row.security_id for row in eligible)
    if security_id not in eligible_ids:
        raise ValueError("INELIGIBLE_SECURITY_AT_VALUATION_CUTOFF")
    classifications = _active_classifications(
        all_classifications, cutoff, frozenset(eligible_ids)
    )
    target_classification = classifications.get(security_id)
    target_report = _report_or_none(all_reports, security_id, cutoff)
    if target_report is None:
        raise LookupError("NO_PUBLISHED_FUNDAMENTAL_REPORT")
    sector = target_classification.sector_id if target_classification else None
    current = _raw_valuation(target_report, target_price, sector)

    histories = {name: [] for name in ("trailing_pe_raw", "ev_to_ebitda_raw", "fcf_yield_raw")}
    used_prices: list[ValuationPrice] = []
    used_reports: list[ReportedFundamentals] = []
    used_classifications: list[SectorClassification] = []
    first_session = _day(min(target_history), "session_date")
    last_session = _day(latest_session, "session_date")
    aligned_sessions: list[str] = []
    cursor = first_session
    while cursor <= last_session:
        if eligible_session_close(target_price.exchange, cursor) is not None:
            aligned_sessions.append(cursor.isoformat())
        cursor += timedelta(days=1)
    for session in aligned_sessions:
        price = target_history.get(session)
        if price is None:
            for name in histories:
                histories[name].append(None)
            continue
        report = _report_or_none(all_reports, security_id, price.session_close_at)
        classification = _active_classifications(
            all_classifications, price.session_close_at, frozenset({security_id})
        ).get(security_id)
        _append_unique(used_prices, price)
        _append_unique(used_reports, report)
        _append_unique(used_classifications, classification)
        raw = (
            {name: None for name in histories}
            if report is None
            else _raw_valuation(report, price, classification.sector_id if classification else None)
        )
        for name in histories:
            histories[name].append(raw[name])

    raw_cross_sections = {
        name: {} for name in ("trailing_pe_raw", "ev_to_ebitda_raw", "fcf_yield_raw")
    }
    for peer in eligible:
        member = peer.security_id
        expected_close = previous_eligible_eod(peer.exchange, cutoff)
        peer_prices = [
            row for row in prices_by_security.get(member, {}).values()
            if row.exchange == peer.exchange and row.session_close_at == expected_close
        ]
        price = max(peer_prices, key=lambda row: row.session_close_at) if peer_prices else None
        report = (
            None if price is None
            else _report_or_none(all_reports, member, price.session_close_at)
        )
        classification = classifications.get(member)
        if (
            price is None or report is None
            or price.region is not region
        ):
            raw = {name: None for name in raw_cross_sections}
        else:
            raw = _raw_valuation(report, price, classification.sector_id if classification else None)
            _append_unique(used_prices, price)
            _append_unique(used_reports, report)
            _append_unique(used_classifications, classification)
        for name in raw_cross_sections:
            raw_cross_sections[name][member] = raw[name]

    sector_ids = {
        member for member in eligible_ids
        if target_classification is not None
        and classifications.get(member) is not None
        and classifications[member].sector_id == target_classification.sector_id
    }
    values = dict(current)
    values.update({
        "trailing_pe_own_history_zscore": _zscore(histories["trailing_pe_raw"]),
        "ev_to_ebitda_own_history_zscore": _zscore(histories["ev_to_ebitda_raw"]),
        "fcf_yield_own_history_zscore": _zscore(histories["fcf_yield_raw"]),
        "trailing_pe_sector_percentile": percentile_in_universe(
            security_id, raw_cross_sections["trailing_pe_raw"], sector_ids
        ),
        "ev_to_ebitda_sector_percentile": percentile_in_universe(
            security_id, raw_cross_sections["ev_to_ebitda_raw"], sector_ids
        ),
        "fcf_yield_sector_percentile": percentile_in_universe(
            security_id, raw_cross_sections["fcf_yield_raw"], sector_ids
        ),
    })
    if _financial(sector):
        for name in (
            "ev_to_ebitda_raw", "ev_to_ebitda_sector_percentile",
            "ev_to_ebitda_own_history_zscore", "fcf_yield_raw",
            "fcf_yield_sector_percentile", "fcf_yield_own_history_zscore",
        ):
            values[name] = None
    applicability = {
        "trailing_pe_raw": current["trailing_pe_raw"] is not None,
        "trailing_pe_sector_percentile": current["trailing_pe_raw"] is not None and bool(sector_ids),
        "trailing_pe_own_history_zscore": current["trailing_pe_raw"] is not None,
        "ev_to_ebitda_raw": _known_nonfinancial(sector),
        "ev_to_ebitda_sector_percentile": _known_nonfinancial(sector) and bool(sector_ids),
        "ev_to_ebitda_own_history_zscore": _known_nonfinancial(sector),
        "price_to_sales_raw": True,
        "fcf_yield_raw": _known_nonfinancial(sector),
        "fcf_yield_sector_percentile": _known_nonfinancial(sector) and bool(sector_ids),
        "fcf_yield_own_history_zscore": _known_nonfinancial(sector),
    }
    if set(values) != set(_VALUATION_NAMES):
        raise ValueError("TASK4_VALUATION_REGISTRY_MISMATCH")
    _append_unique(used_prices, target_price)
    _append_unique(used_reports, target_report)
    _append_unique(used_classifications, target_classification)
    evidence = [*used_prices, *used_reports, *used_classifications]
    max_input = max(row.available_at for row in evidence)
    quality = max((row.quality for row in evidence), key=_QUALITY_ORDER.__getitem__)
    features = tuple(
        FeatureValue(
            feature=name, entity_id=security_id, observation_date=latest_session,
            as_of=prediction, value=values[name], max_input_available_at=max_input,
            available_at=cutoff, quality=quality, source="pit_valuation_features",
            revision_id="features-v1", currency=target_price.currency,
            region=region, exchange=target_price.exchange,
        ) for name in _VALUATION_NAMES
    )
    assert_pit_safe(features, prediction)
    return ValuationFeatureSnapshot(
        features, applicability, eligible_ids,
        tuple(sorted(used_prices, key=lambda row: (row.security_id, row.session_date, row.revision_id))),
        tuple(sorted(used_reports, key=lambda row: (row.security_id, row.period_end, row.available_at))),
        tuple(sorted(used_classifications, key=lambda row: (row.security_id, row.active_from, row.available_at))),
    )
