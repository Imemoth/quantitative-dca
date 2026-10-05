"""Immutable provider-independent point-in-time records.

Dates are ISO calendar-date strings; timestamps are timezone-aware datetimes.
``available_at`` is the earliest usable time of this particular vintage, not
its observation date. Unknown publication/revision times remain None: adapters
must never invent them or treat a missing capability as an automatic Tier C.
Quality labels describe provenance assessed outside these structural contracts.
Numeric validity and cross-row consistency belong to the ingestion validator.
"""
from dataclasses import dataclass, fields
from datetime import datetime
from enum import StrEnum


class QualityTier(StrEnum):
    A = "A"
    B = "B"
    C = "C"


class Region(StrEnum):
    US = "US"
    EU = "EU"
    GLOBAL = "GLOBAL"


@dataclass(frozen=True, slots=True, kw_only=True)
class _Provenance:
    available_at: datetime
    quality: QualityTier
    source: str
    revision_id: str
    published_at: datetime | None = None
    revised_at: datetime | None = None

    def __post_init__(self) -> None:
        # Check every timestamp, including optional domain timestamps. A tzinfo
        # object alone does not guarantee awareness (utcoffset may be None).
        for field in fields(self):
            if field.name.endswith("_at") or field.name == "as_of":
                value = getattr(self, field.name)
                if value is None and field.default is None:
                    continue
                if not isinstance(value, datetime):
                    raise TypeError(f"{field.name} must be a timezone-aware datetime")
                if value.tzinfo is None or value.utcoffset() is None:
                    raise ValueError(f"{field.name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class Observation(_Provenance):
    series: str
    entity_id: str | None
    observation_date: str
    value: float | None
    currency: str | None = None
    region: Region | None = None
    exchange: str | None = None
    unit: str | None = None
    # Provider real-time validity interval, inclusive dates; may be request-clipped.
    vintage_start: str | None = None
    vintage_end: str | None = None


@dataclass(frozen=True, slots=True)
class Security(_Provenance):
    """A historical security/listing version; exchange is an explicit MIC."""

    security_id: str
    ticker: str
    name: str
    currency: str
    region: Region
    exchange: str
    active_from: str
    active_to: str | None = None
    isin: str | None = None
    security_type: str = "common_equity"
    primary_listing: bool = True
    monetary_jurisdiction: str | None = None
    currency_area: str | None = None


@dataclass(frozen=True, slots=True)
class UniverseMembership(_Provenance):
    """Historical membership interval [active_from, active_to); None is open."""

    universe_id: str
    security_id: str
    active_from: str
    region: Region
    exchange: str
    currency: str
    active_to: str | None = None
    index_id: str | None = None


@dataclass(frozen=True, slots=True)
class CorporateAction(_Provenance):
    """Cash amount is per share; split ratio is new shares per old share.

    Ex-date determines entitlement; payable_at determines the cash-flow time.
    Action-type validation and economic adjustment are separate services.
    """

    security_id: str
    action_id: str
    action_type: str
    ex_date: str
    currency: str
    region: Region
    exchange: str
    cash_amount: float | None = None
    split_ratio: float | None = None
    announced_at: datetime | None = None
    payable_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class FXQuote(_Provenance):
    """Rate is quote-currency units per one base-currency unit."""

    base_currency: str
    quote_currency: str
    rate: float
    fixing_at: datetime
    quote_type: str = "spot"


@dataclass(frozen=True, slots=True)
class FeatureValue(_Provenance):
    """Feature vintage with decision cutoff and latest input-availability time.

    The later as-of service must enforce input and value availability <= as_of;
    these records preserve the times needed to audit that constraint.
    """

    feature: str
    entity_id: str | None
    observation_date: str
    as_of: datetime
    value: float | None
    max_input_available_at: datetime
    computed_at: datetime | None = None
    currency: str | None = None
    region: Region | None = None
    exchange: str | None = None


@dataclass(frozen=True, slots=True)
class OHLCV(_Provenance):
    """Daily bar; session_date is exchange-local and prices default to raw.

    Preserve suspect numeric data for explicit downstream quarantine. Never
    silently substitute vendor-adjusted prices for executable raw prices.
    """

    security_id: str
    session_date: str
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: float | None
    currency: str
    region: Region
    exchange: str
    session_open_at: datetime
    session_close_at: datetime
    price_basis: str = "unadjusted"
