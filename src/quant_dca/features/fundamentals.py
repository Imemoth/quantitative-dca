"""Point-in-time reported fundamental features.

Growth across a sign change uses ``(current - prior) / abs(prior)``.  This
keeps improvement from a loss toward profit positive, deterioration negative,
and leaves a zero prior denominator missing.  Structural applicability is
separate from ordinary missing data and is never filled here.
"""

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
import math

from quant_dca.calendars.service import previous_eligible_eod
from quant_dca.features.registry import FeatureRegistry
from quant_dca.point_in_time.asof import assert_pit_safe, latest_known
from quant_dca.types import FeatureValue, QualityTier, Region


_FUNDAMENTAL_NAMES = tuple(
    definition.name
    for definition in FeatureRegistry.v1()
    if definition.domain == "fundamentals"
)
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


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _ratio(numerator: object, denominator: object) -> float | None:
    numerator, denominator = _number(numerator), _number(denominator)
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _growth(current: object, prior: object) -> float | None:
    current, prior = _number(current), _number(prior)
    if current is None or prior is None or prior == 0:
        return None
    return (current - prior) / abs(prior)


def _is_financial(sector: object) -> bool:
    return isinstance(sector, str) and sector.strip().casefold() in {
        "financial", "financials", "banks", "insurance"
    }


def fundamental_features(values: Mapping[str, object]) -> dict[str, float | bool | None]:
    """Calculate all registered Task 4 fundamentals from one selected report.

    This pure helper accepts no timestamps and makes no availability claim.  The
    evidenced builder below is the admissible point-in-time boundary.
    """
    if not isinstance(values, Mapping):
        raise TypeError("values must be a mapping")
    financial = _is_financial(values.get("sector"))
    applicable = {
        "revenue_growth_yoy": True,
        "eps_growth_yoy": True,
        "fcf_growth_yoy": not financial,
        "gross_margin": not financial,
        "operating_margin": True,
        "fcf_margin": not financial,
        "roic": not financial,
        "roe": True,
        "net_debt_to_ebitda": not financial,
        "interest_coverage": not financial,
        "share_dilution_yoy": True,
        "last_known_earnings_surprise": _number(values.get("consensus_eps")) is not None,
    }
    computed = {
        "revenue_growth_yoy_raw": _growth(values.get("revenue"), values.get("prior_year_revenue")),
        "eps_growth_yoy_raw": _growth(values.get("diluted_eps"), values.get("prior_year_diluted_eps")),
        "fcf_growth_yoy_raw": _growth(values.get("free_cash_flow"), values.get("prior_year_free_cash_flow")),
        "gross_margin_raw": _ratio(values.get("gross_profit"), values.get("revenue")),
        "operating_margin_raw": _ratio(values.get("operating_income"), values.get("revenue")),
        "fcf_margin_raw": _ratio(values.get("free_cash_flow"), values.get("revenue")),
        "roic_raw": _ratio(values.get("nopat"), values.get("invested_capital")),
        "roe_raw": _ratio(values.get("net_income"), values.get("average_equity")),
        "net_debt_to_ebitda_raw": _ratio(values.get("net_debt"), values.get("ebitda")),
        "interest_coverage_raw": _ratio(values.get("ebit"), values.get("interest_expense")),
        "share_dilution_yoy_raw": _growth(values.get("diluted_shares"), values.get("prior_year_diluted_shares")),
        "last_known_earnings_surprise_raw": None,
    }
    actual, consensus = _number(values.get("diluted_eps")), _number(values.get("consensus_eps"))
    if actual is not None and consensus is not None:
        computed["last_known_earnings_surprise_raw"] = actual - consensus
    for name in _FUNDAMENTAL_NAMES:
        stem = name.removesuffix("_raw")
        if not applicable[stem]:
            computed[name] = None
        computed[f"{stem}_applicable"] = applicable[stem]
    # Preserve the plan's literal illustrative helper key without registering
    # a duplicate panel feature.
    computed["net_debt_to_ebitda"] = computed["net_debt_to_ebitda_raw"]
    if set(computed).intersection(_FUNDAMENTAL_NAMES) != set(_FUNDAMENTAL_NAMES):
        raise ValueError("TASK4_FUNDAMENTAL_REGISTRY_MISMATCH")
    return computed


@dataclass(frozen=True, slots=True, kw_only=True)
class ReportedFundamentals:
    """One provider-normalized report vintage with explicit economic units."""

    security_id: str
    period_end: str
    published_at: datetime
    available_at: datetime
    currency: str
    per_share_basis: str
    sector_id: str
    valuation_period_basis: str
    values: Mapping[str, float | None]
    quality: QualityTier
    source: str
    revision_id: str
    region: Region
    exchange: str
    revised_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.security_id or not self.currency or not self.per_share_basis:
            raise ValueError("fundamental identity and unit metadata must be non-empty")
        if self.valuation_period_basis != "trailing_twelve_months":
            raise ValueError(
                "VALUATION_PERIOD_BASIS: expected upstream trailing_twelve_months"
            )
        _iso_date(self.period_end, "period_end")
        published = _aware(self.published_at, "published_at")
        available = _aware(self.available_at, "available_at")
        if published > available:
            raise ValueError("published_at cannot be after available_at")
        if self.revised_at is not None:
            revised = _aware(self.revised_at, "revised_at")
            if revised < published or revised > available:
                raise ValueError("invalid report revision chronology")
        if not isinstance(self.values, Mapping):
            raise TypeError("values must be a mapping")
        if any(value is not None and _number(value) is None for value in self.values.values()):
            raise ValueError("fundamental values must be finite numbers or None")
        if not isinstance(self.quality, QualityTier):
            raise TypeError("quality must be a QualityTier")
        if not self.source.strip() or not self.revision_id.strip():
            raise ValueError("fundamental provenance must be non-empty")


@dataclass(frozen=True, slots=True, kw_only=True)
class ConsensusEstimate:
    """A real point-in-time EPS estimate; absence never creates a consensus."""

    security_id: str
    period_end: str
    value: float
    available_at: datetime
    currency: str
    per_share_basis: str
    quality: QualityTier
    source: str
    revision_id: str
    published_at: datetime | None = None
    revised_at: datetime | None = None

    def __post_init__(self) -> None:
        _iso_date(self.period_end, "period_end")
        available = _aware(self.available_at, "available_at")
        for field in ("published_at", "revised_at"):
            timestamp = getattr(self, field)
            if timestamp is not None and _aware(timestamp, field) > available:
                raise ValueError(f"{field} cannot be after available_at")
        if _number(self.value) is None:
            raise ValueError("consensus value must be finite")
        if not self.currency or not self.per_share_basis or not self.source or not self.revision_id:
            raise ValueError("consensus units and provenance must be non-empty")
        if not isinstance(self.quality, QualityTier):
            raise TypeError("quality must be a QualityTier")


@dataclass(frozen=True, slots=True)
class FundamentalFeatureSnapshot:
    features: tuple[FeatureValue, ...]
    applicability: Mapping[str, bool]
    selected_report: ReportedFundamentals
    selected_consensus: ConsensusEstimate | None


def select_report(
    reports: Iterable[ReportedFundamentals], security_id: str, cutoff: datetime
) -> ReportedFundamentals:
    """Select revisions within period first, then the latest reported period."""
    groups: dict[str, list[ReportedFundamentals]] = defaultdict(list)
    for row in reports:
        if not isinstance(row, ReportedFundamentals):
            raise TypeError("reports must contain ReportedFundamentals")
        if row.security_id == security_id and row.available_at <= cutoff:
            groups[row.period_end].append(row)
    if not groups:
        raise LookupError("NO_PUBLISHED_FUNDAMENTAL_REPORT")
    selected_by_period = [latest_known(group, cutoff) for group in groups.values()]
    selected = max(selected_by_period, key=lambda row: _iso_date(row.period_end, "period_end"))
    if selected.quality is QualityTier.C:
        raise ValueError("QUALITY_BELOW_FLOOR:fundamentals_requires_tier_b")
    return selected


def _select_consensus(
    estimates: Iterable[ConsensusEstimate], report: ReportedFundamentals
) -> ConsensusEstimate | None:
    candidates = [
        row for row in estimates
        if isinstance(row, ConsensusEstimate)
        and row.security_id == report.security_id
        and row.period_end == report.period_end
        and row.available_at <= report.published_at
        and row.currency == report.currency
        and row.per_share_basis == report.per_share_basis
    ]
    if not candidates:
        return None
    selected = latest_known(candidates, report.published_at)
    return None if selected.quality is QualityTier.C else selected


def build_fundamental_features(
    *, security_id: str, as_of: datetime,
    reports: Iterable[ReportedFundamentals],
    consensus_estimates: Iterable[ConsensusEstimate] = (),
) -> FundamentalFeatureSnapshot:
    """Build the latest report snapshot known by the latest eligible EOD."""
    prediction = _aware(as_of, "as_of")
    materialized = tuple(reports)
    exchanges = {row.exchange for row in materialized if row.security_id == security_id}
    if len(exchanges) != 1:
        raise ValueError("INCONSISTENT_FUNDAMENTAL_EXCHANGE")
    cutoff = previous_eligible_eod(next(iter(exchanges)), prediction)
    report = select_report(materialized, security_id, cutoff)
    if not isinstance(report.sector_id, str) or not report.sector_id.strip():
        raise ValueError("UNKNOWN_FUNDAMENTAL_SECTOR")
    consensus = _select_consensus(tuple(consensus_estimates), report)
    inputs = dict(report.values)
    # Consensus is a separate PIT evidence stream.  Provider report payloads
    # cannot smuggle an estimate past that boundary.
    inputs.pop("consensus_eps", None)
    inputs["sector"] = report.sector_id
    if consensus is not None:
        inputs["consensus_eps"] = consensus.value
    calculated = fundamental_features(inputs)
    applicability = {
        key.removesuffix("_applicable"): bool(value)
        for key, value in calculated.items() if key.endswith("_applicable")
    }
    input_rows = (report,) if consensus is None else (report, consensus)
    max_input = max(row.available_at for row in input_rows)
    quality = max((row.quality for row in input_rows), key=_QUALITY_ORDER.__getitem__)
    features = tuple(
        FeatureValue(
            feature=name, entity_id=security_id, observation_date=report.period_end,
            as_of=prediction, value=calculated[name], max_input_available_at=max_input,
            available_at=cutoff, quality=quality, source="reported_fundamental_features",
            revision_id="features-v1", currency=report.currency,
            region=report.region, exchange=report.exchange,
        ) for name in _FUNDAMENTAL_NAMES
    )
    assert_pit_safe(features, prediction)
    return FundamentalFeatureSnapshot(features, applicability, report, consensus)
