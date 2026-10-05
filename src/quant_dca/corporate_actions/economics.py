"""Corporate-action-safe feature prices and delayed-entry economics.

Execution prices remain raw.  Feature prices are separate records adjusted
only with split facts that were both effective and available at the requested
point in time.
"""
from collections.abc import Iterable
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
import math
from typing import Protocol

from quant_dca.calendars.service import eligible_session_open, assert_session_clock
from quant_dca.point_in_time.asof import latest_known
from quant_dca.canonical.validate import DiscontinuityEvidence, validate_ohlcv
from quant_dca.types import CorporateAction, FXQuote, OHLCV, QualityTier, Region


_DEVELOPMENT_END = datetime(2023, 12, 31, 23, 59, 59, 999999, tzinfo=timezone.utc)
_SUPPORTED_ACTIONS = {"dividend", "split"}


class FXRateService(Protocol):
    """Narrow evidenced interface supplied by the FX layer in Task 8."""

    def resolve(self, base: str, quote: str, at_or_before: datetime) -> FXQuote:
        """Return the exact quote and provenance used for conversion."""


@dataclass(frozen=True, slots=True)
class EconomicCashflow:
    """One native cashflow and its auditable HUF conversion, if required."""

    kind: str
    action_id: str | None
    native_amount: float
    share_units: float
    currency: str
    cashflow_at: datetime
    huf_amount: float
    fx_rate: float | None
    fx_fixing_at: datetime | None
    fx_available_at: datetime | None
    fx_quote: FXQuote | None


@dataclass(frozen=True, slots=True)
class EconomicAcquisitionCost:
    """Cost of buying the baseline holder's equivalent position, in HUF."""

    total: float
    fill_cost: float
    foregone_distributions: float
    share_units: float
    label_matures_at: datetime
    cashflows: tuple[EconomicCashflow, ...]
    selected_action_versions: tuple[tuple[str, str, str], ...] = ()
    currency: str = "HUF"


@dataclass(frozen=True, slots=True)
class SplitAdjustedFeaturePrice:
    """A feature-only view; it cannot be mistaken for an executable raw bar."""

    security_id: str
    session_date: str
    open: float
    high: float
    low: float
    close: float
    currency: str
    region: Region
    exchange: str
    session_open_at: datetime
    session_close_at: datetime
    raw_available_at: datetime
    available_at: datetime
    published_at: datetime | None
    revised_at: datetime | None
    as_of: datetime
    max_input_available_at: datetime
    feature: str
    entity_id: str
    observation_date: str
    value: float
    quality: QualityTier
    source: str
    revision_id: str
    applied_action_ids: tuple[str, ...]
    input_sources: tuple[str, ...]
    split_factor: float
    selected_action_versions: tuple[tuple[str, str, str], ...] = ()
    price_basis: str = "split_adjusted_feature"


class EconomicLabelUnavailable(LookupError):
    """A target needs a cashflow beyond the authorized development history."""

    def __init__(self, label_matures_at: datetime):
        super().__init__(
            "DEVELOPMENT_CASHFLOW_FX_UNAVAILABLE:"
            f"label matures at {label_matures_at.isoformat()}"
        )
        self.label_matures_at = label_matures_at


def _finite(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _aware(value: object, field: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"INVALID_TIMESTAMP:{field}")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"INVALID_TIMESTAMP:{field}")
    return value


def _day(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"INVALID_DATE:{field}") from exc


def _positive(value: object, error: str) -> float:
    if not _finite(value) or value <= 0:
        raise ValueError(error)
    return float(value)


def _nonnegative(value: object, error: str) -> float:
    if not _finite(value) or value < 0:
        raise ValueError(error)
    return float(value)


def _cashflow(
    *,
    kind: str,
    action_id: str | None,
    native_amount: float,
    share_units: float,
    currency: str,
    cashflow_at: datetime,
    fx_service: FXRateService,
) -> EconomicCashflow:
    if currency == "HUF":
        return EconomicCashflow(
            kind=kind,
            action_id=action_id,
            native_amount=native_amount,
            share_units=share_units,
            currency=currency,
            cashflow_at=cashflow_at,
            huf_amount=native_amount,
            fx_rate=None,
            fx_fixing_at=None,
            fx_available_at=None,
            fx_quote=None,
        )

    quote = fx_service.resolve(currency, "HUF", cashflow_at)
    if quote.base_currency != currency or quote.quote_currency != "HUF":
        raise ValueError("MISMATCHED_FX_QUOTE")
    rate = _positive(quote.rate, "INVALID_FX_RATE")
    fixing_at = _aware(quote.fixing_at, "fx.fixing_at")
    available_at = _aware(quote.available_at, "fx.available_at")
    if fixing_at > cashflow_at or available_at > cashflow_at:
        raise ValueError("PIT_FX_AFTER_CASHFLOW")
    if available_at < fixing_at:
        raise ValueError("INVALID_FX_CHRONOLOGY")
    return EconomicCashflow(
        kind=kind,
        action_id=action_id,
        native_amount=native_amount,
        share_units=share_units,
        currency=currency,
        cashflow_at=cashflow_at,
        huf_amount=native_amount * rate,
        fx_rate=rate,
        fx_fixing_at=fixing_at,
        fx_available_at=available_at,
        fx_quote=quote,
    )


def economic_price_improvement(
    baseline_cost: float,
    delayed_fill: float,
    foregone_distribution: float,
) -> float:
    """Return the economic improvement after charging foregone distributions."""
    baseline = _positive(baseline_cost, "INVALID_ECONOMIC_COST:baseline_cost")
    delayed = _positive(delayed_fill, "INVALID_ECONOMIC_COST:delayed_fill")
    distribution = _nonnegative(
        foregone_distribution, "INVALID_ECONOMIC_COST:foregone_distribution"
    )
    return (baseline - delayed - distribution) / baseline


def _relevant_actions(
    delayed_from: OHLCV,
    fill: OHLCV,
    actions: Iterable[CorporateAction],
) -> list[CorporateAction]:
    if delayed_from.security_id != fill.security_id:
        raise ValueError("MISMATCHED_SECURITY")
    start = _day(delayed_from.session_date, "delayed_from.session_date")
    end = _day(fill.session_date, "fill.session_date")
    if start > end or delayed_from.session_open_at > fill.session_open_at:
        raise ValueError("INVALID_DELAY_WINDOW")

    relevant = []
    for item in actions:
        if item.security_id != fill.security_id:
            continue
        ex_day = _day(item.ex_date, "action.ex_date")
        # The baseline must be pre-ex and the delayed fill on/after ex.
        if start < ex_day <= end:
            relevant.append(item)
    return relevant


def _raw_bar(row: OHLCV) -> None:
    if not isinstance(row, OHLCV) or row.price_basis != "unadjusted":
        raise ValueError("RAW_CANONICAL_BAR_REQUIRED")
    assert_session_clock(row.exchange, row.session_date,
                         row.session_open_at, row.session_close_at)
    if row.available_at < row.session_close_at:
        raise ValueError("AVAILABILITY_BEFORE_SESSION_CLOSE")


def _selected_actions(actions: Iterable[CorporateAction], security_id: str,
                      cutoff: datetime) -> list[CorporateAction]:
    groups = defaultdict(list)
    for item in actions:
        if item.security_id == security_id:
            if not item.action_id:
                raise ValueError("MISSING_ACTION_IDENTITY")
            groups[item.action_id].append(item)
    selected = []
    for key in sorted(groups):
        try:
            selected.append(latest_known(groups[key], cutoff))
        except LookupError:
            continue
    return selected


def _validate_action_order(actions: Iterable[CorporateAction]) -> None:
    by_day: dict[str, set[str]] = {}
    for item in actions:
        by_day.setdefault(item.ex_date, set()).add(item.action_type)
    if any({"split", "dividend"} <= kinds for kinds in by_day.values()):
        raise ValueError("AMBIGUOUS_SAME_DAY_ACTION_ORDER")


def economic_acquisition_cost(
    fill: OHLCV,
    delayed_from: OHLCV,
    actions: Iterable[CorporateAction],
    fx_service: FXRateService,
) -> EconomicAcquisitionCost:
    """Price a delayed fill for the baseline holder's equivalent share units.

    One share at ``delayed_from`` is the unit of comparison. Splits change the
    delayed share quantity, while each foregone dividend uses the quantity in
    force on its ex-date. Cash distributions mature and convert on payable_at.

    Labels resolve each action identity across the supplied version set, not at
    the fill timestamp. This is a versioned-input label, never final-action truth:
    a dependency is an identity with any supplied version in the delay window.
    Only its selected revision affects economics; its availability and provenance
    remain dependencies even when it moves the event out of the window. Wholly
    unrelated identities do not delay maturity. Later versions require rebuilding.
    """
    _raw_bar(fill)
    _raw_bar(delayed_from)
    fill_price = _positive(fill.open, "INVALID_FILL_PRICE")
    _aware(fill.session_open_at, "fill.session_open_at")
    _aware(delayed_from.session_open_at, "delayed_from.session_open_at")
    if fill.currency != delayed_from.currency:
        raise ValueError("MISMATCHED_FILL_CURRENCY")

    versions = list(actions)
    selection_cutoff = max([fill.available_at, *[
        item.available_at for item in versions if item.security_id == fill.security_id
    ]])
    selected = _selected_actions(versions, fill.security_id, selection_cutoff)
    # Resolve complete identities before relevance. Inspect historical dates only
    # to retain correction evidence, never to select or apply a superseded row.
    dependency_ids = {
        item.action_id for item in _relevant_actions(delayed_from, fill, versions)
    }
    selected = [item for item in selected if item.action_id in dependency_ids]
    relevant = _relevant_actions(delayed_from, fill, selected)
    _validate_action_order(relevant)
    unsupported = sorted({item.action_type for item in relevant} - _SUPPORTED_ACTIONS)
    if unsupported:
        raise NotImplementedError(
            "UNSUPPORTED_CORPORATE_ACTION:" + ",".join(unsupported)
        )

    share_units = 1.0
    dividends_with_units: list[tuple[CorporateAction, float]] = []
    for item in sorted(relevant, key=lambda value: (value.ex_date, value.action_id)):
        _aware(item.available_at, "action.available_at")
        if item.action_type == "split":
            share_units *= _positive(item.split_ratio, "INVALID_SPLIT_RATIO")
        else:
            _nonnegative(item.cash_amount, "INVALID_DIVIDEND_AMOUNT")
            if item.payable_at is None:
                raise ValueError("MISSING_PAYABLE_AT")
            payable = _aware(item.payable_at, "action.payable_at")
            if payable.date() < _day(item.ex_date, "action.ex_date"):
                raise ValueError("INVALID_ACTION_CHRONOLOGY")
            dividends_with_units.append((item, share_units))

    required_knowledge = [
        fill.session_open_at,
        _aware(fill.available_at, "fill.available_at"),
        _aware(delayed_from.available_at, "delayed_from.available_at"),
        *[_aware(item.available_at, "action.available_at") for item in selected],
        *[item.payable_at for item, _units in dividends_with_units],
    ]
    preflight_maturity = max(required_knowledge)
    if preflight_maturity > _DEVELOPMENT_END:
        # All known future requirements are checked before any FX service call.
        raise EconomicLabelUnavailable(preflight_maturity)

    fill_flow = _cashflow(
        kind="fill",
        action_id=None,
        native_amount=fill_price * share_units,
        share_units=share_units,
        currency=fill.currency,
        cashflow_at=fill.session_open_at,
        fx_service=fx_service,
    )
    dividend_flows = tuple(
        _cashflow(
            kind="foregone_dividend",
            action_id=item.action_id,
            native_amount=float(item.cash_amount) * units,
            share_units=units,
            currency=item.currency,
            cashflow_at=item.payable_at,
            fx_service=fx_service,
        )
        for item, units in dividends_with_units
    )
    cashflows = (fill_flow, *dividend_flows)
    fx_availability = [
        flow.fx_available_at for flow in cashflows if flow.fx_available_at is not None
    ]
    label_matures_at = max(required_knowledge + fx_availability)
    fill_huf = fill_flow.huf_amount
    foregone_huf = sum(flow.huf_amount for flow in dividend_flows)
    return EconomicAcquisitionCost(
        total=fill_huf + foregone_huf,
        fill_cost=fill_huf,
        foregone_distributions=foregone_huf,
        share_units=share_units,
        label_matures_at=label_matures_at,
        cashflows=cashflows,
        selected_action_versions=tuple((item.security_id, item.action_id, item.revision_id)
                                       for item in selected),
    )


def _known_effective_splits(
    actions: Iterable[CorporateAction],
    security_id: str,
    exchange: str,
    as_of: datetime,
) -> list[CorporateAction]:
    selected = []
    for item in _selected_actions(actions, security_id, as_of):
        if item.security_id != security_id:
            continue
        if item.exchange != exchange:
            raise ValueError("MISMATCHED_ACTION_EXCHANGE")
        ex_day = _day(item.ex_date, "action.ex_date")
        effective_at = eligible_session_open(item.exchange, ex_day)
        if effective_at is None:
            raise ValueError("INVALID_ACTION_EFFECTIVE_SESSION")
        if item.available_at <= as_of and effective_at <= as_of:
            if item.action_type not in _SUPPORTED_ACTIONS:
                raise NotImplementedError(
                    f"UNSUPPORTED_CORPORATE_ACTION:{item.action_type}"
                )
            if item.action_type == "split":
                _positive(item.split_ratio, "INVALID_SPLIT_RATIO")
                selected.append(item)
    return sorted(selected, key=lambda item: (item.ex_date, item.action_id))


def split_adjusted_feature_prices(
    prices: Iterable[OHLCV],
    actions: Iterable[CorporateAction],
    *,
    as_of: datetime,
    discontinuity_evidence: Iterable[DiscontinuityEvidence] = (),
) -> tuple[SplitAdjustedFeaturePrice, ...]:
    """Build a PIT split-adjusted feature view while preserving raw bars."""
    cutoff = _aware(as_of, "as_of")
    rows = list(prices)
    if not rows:
        return ()
    for row in rows:
        _raw_bar(row)
        for field in ("open", "high", "low", "close"):
            _positive(getattr(row, field), "INVALID_FEATURE_PRICE")
    security_id = rows[0].security_id
    if any(row.security_id != security_id for row in rows):
        raise ValueError("MIXED_FEATURE_PRICE_SECURITY")
    exchange = rows[0].exchange
    if any(row.exchange != exchange for row in rows):
        raise ValueError("MIXED_FEATURE_PRICE_EXCHANGE")
    selected = _selected_actions(actions, security_id, cutoff)
    splits = _known_effective_splits(selected, security_id, exchange, cutoff)

    groups = defaultdict(list)
    for row in rows:
        groups[row.session_date].append(row)
    try:
        rows = [latest_known(group, cutoff) for group in groups.values()]
    except LookupError:
        raise ValueError("PIT_FEATURE_PRICE_AFTER_AS_OF") from None
    validation = validate_ohlcv(rows, as_of=cutoff,
                                discontinuity_evidence=discontinuity_evidence)
    if validation.quarantined_rows:
        raise ValueError("INVALID_FEATURE_RAW_PANEL:" + ",".join(validation.reasons))

    adjusted = []
    for row in rows:
        if row.available_at > cutoff or row.session_close_at > cutoff:
            raise ValueError("PIT_FEATURE_PRICE_AFTER_AS_OF")
        row_day = _day(row.session_date, "price.session_date")
        factor = math.prod(
            float(item.split_ratio)
            for item in splits
            if row_day < _day(item.ex_date, "action.ex_date")
        )
        values = [
            _positive(getattr(row, field), "INVALID_FEATURE_PRICE") / factor
            for field in ("open", "high", "low", "close")
        ]
        applied = tuple(
            item for item in splits if row_day < _day(item.ex_date, "action.ex_date")
        )
        # A correction that removes an adjustment remains input evidence.
        inputs = [row.available_at, *[item.available_at for item in selected]]
        available_at = max(inputs)
        quality_order = {QualityTier.A: 0, QualityTier.B: 1, QualityTier.C: 2}
        quality = max(
            [row.quality, *[item.quality for item in selected]],
            key=quality_order.__getitem__,
        )
        revision_id = "|".join(
            [row.revision_id, *[f"{item.action_id}:{item.revision_id}" for item in selected]]
        )
        input_sources = tuple(dict.fromkeys([row.source, *[item.source for item in selected]]))
        adjusted.append(
            SplitAdjustedFeaturePrice(
                security_id=row.security_id,
                session_date=row.session_date,
                open=values[0],
                high=values[1],
                low=values[2],
                close=values[3],
                currency=row.currency,
                region=row.region,
                exchange=row.exchange,
                session_open_at=row.session_open_at,
                session_close_at=row.session_close_at,
                raw_available_at=row.available_at,
                available_at=available_at,
                published_at=row.published_at,
                revised_at=row.revised_at,
                as_of=cutoff,
                max_input_available_at=available_at,
                feature="split_adjusted_ohlc",
                entity_id=row.security_id,
                observation_date=row.session_date,
                value=values[3],
                quality=quality,
                source=row.source,
                revision_id=revision_id,
                applied_action_ids=tuple(item.action_id for item in applied),
                input_sources=input_sources,
                split_factor=factor,
                selected_action_versions=tuple((item.security_id, item.action_id, item.revision_id)
                                               for item in selected),
            )
        )
    return tuple(adjusted)
