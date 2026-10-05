"""Region-aware point-in-time macro features from canonical observations.

Series identities are caller-controlled metadata.  The builder never infers a
central bank from a broad region, and it selects a knowable vintage within each
observation period before selecting the latest released period.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
import math

from quant_dca.calendars.service import previous_eligible_eod
from quant_dca.features.registry import FeatureRegistry
from quant_dca.point_in_time.asof import assert_pit_safe, latest_known
from quant_dca.types import FeatureValue, Observation, QualityTier, Region, Security


_MACRO_NAMES = tuple(
    definition.name for definition in FeatureRegistry.v1()
    if definition.domain == "macro"
)
_REGIONAL_ROLES = frozenset({
    "headline_inflation", "core_inflation", "unemployment_rate",
    "high_yield_spread", "investment_grade_spread", "financial_conditions",
})
_US_RATE_ROLES = frozenset({"long_10y", "short_2y", "short_3m"})
_EU_RATE_ROLES = frozenset({"sovereign_long", "relevant_short"})
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


def _months_before(value: date, months: int) -> date:
    ordinal = value.year * 12 + value.month - 1 - months
    year, month_zero = divmod(ordinal, 12)
    month = month_zero + 1
    month_lengths = (31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                     31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    return date(year, month, min(value.day, month_lengths[month - 1]))


def _validate_series_mapping(name: str, values: Mapping[str, str], roles: frozenset[str]) -> None:
    if not isinstance(values, Mapping) or set(values) != roles:
        raise ValueError(f"{name} must map exactly {sorted(roles)}")
    if any(not isinstance(series, str) or not series.strip() for series in values.values()):
        raise ValueError(f"{name} series IDs must be non-empty strings")


@dataclass(frozen=True, slots=True, kw_only=True)
class MacroSeriesMap:
    """Explicit semantic-role to provider-series mapping.

    Monetary-jurisdiction maps are deliberately independent of region maps.
    In particular, absence of a local non-euro series remains missing rather
    than falling back to an ECB series.
    """

    regional: Mapping[Region, Mapping[str, str]]
    policy_rate: Mapping[str, str]
    central_bank_liquidity: Mapping[str, str]
    us_rates: Mapping[str, str]
    eu_rates: Mapping[str, str]
    global_risk_off: str

    def __post_init__(self) -> None:
        if not isinstance(self.regional, Mapping):
            raise TypeError("regional must be a mapping")
        for region in (Region.US, Region.EU):
            if region not in self.regional:
                raise ValueError(f"regional mapping missing {region}")
            _validate_series_mapping(f"regional[{region}]", self.regional[region], _REGIONAL_ROLES)
        for name in ("policy_rate", "central_bank_liquidity"):
            values = getattr(self, name)
            if not isinstance(values, Mapping) or any(
                not isinstance(key, str) or not key.strip()
                or not isinstance(value, str) or not value.strip()
                for key, value in values.items()
            ):
                raise ValueError(f"{name} must map non-empty jurisdictions to series IDs")
        _validate_series_mapping("us_rates", self.us_rates, _US_RATE_ROLES)
        _validate_series_mapping("eu_rates", self.eu_rates, _EU_RATE_ROLES)
        if not isinstance(self.global_risk_off, str) or not self.global_risk_off.strip():
            raise ValueError("global_risk_off must be a non-empty series ID")


@dataclass(frozen=True, slots=True)
class MacroFeatureSnapshot:
    features: tuple[FeatureValue, ...]
    selected: Mapping[str, Observation]
    dependencies: Mapping[str, tuple[Observation | Security, ...]]
    series_map: MacroSeriesMap


def _known_periods(
    observations: tuple[Observation, ...], series: str, cutoff: datetime,
) -> list[tuple[date, Observation]]:
    grouped: dict[str, list[Observation]] = defaultdict(list)
    for row in observations:
        if not isinstance(row, Observation):
            raise TypeError("observations must contain canonical Observation records")
        # Validate chronology even for a future candidate; latest_known then
        # filters it instead of permitting caller-side preselection leakage.
        if row.series == series:
            grouped[row.observation_date].append(row)
    selected: list[tuple[date, Observation]] = []
    for period, rows in grouped.items():
        parsed = _iso_date(period, "observation_date")
        try:
            vintage = latest_known(rows, cutoff)
        except LookupError:
            continue
        if parsed <= cutoff.date():
            selected.append((parsed, vintage))
    return selected


def _select(
    observations: tuple[Observation, ...], series: str, cutoff: datetime,
    *, no_later_than: date | None = None,
) -> Observation | None:
    periods = _known_periods(observations, series, cutoff)
    ceiling = no_later_than or cutoff.date()
    candidates = [(period, row) for period, row in periods if period <= ceiling]
    if not candidates:
        return None
    selected = max(candidates, key=lambda item: item[0])[1]
    if selected.quality is QualityTier.C:
        raise ValueError(f"QUALITY_BELOW_FLOOR:macro_requires_tier_b:{series}")
    if selected.value is not None and _number(selected.value) is None:
        raise ValueError(f"INVALID_MACRO_VALUE:{series}")
    return selected


def _difference(left: Observation | None, right: Observation | None) -> float | None:
    a = None if left is None else _number(left.value)
    b = None if right is None else _number(right.value)
    return None if a is None or b is None else a - b


def _percent_change(current: Observation | None, prior: Observation | None) -> float | None:
    now = None if current is None else _number(current.value)
    before = None if prior is None else _number(prior.value)
    return None if now is None or before is None or before == 0 else now / before - 1.0


def build_macro_features(
    *, security: Security, as_of: datetime, observations: Iterable[Observation],
    series_map: MacroSeriesMap,
) -> MacroFeatureSnapshot:
    """Build the 13 registered macro outputs at the latest eligible EOD."""
    prediction = _aware(as_of, "as_of")
    if not isinstance(security, Security):
        raise TypeError("security must be a canonical Security")
    if not isinstance(series_map, MacroSeriesMap):
        raise TypeError("series_map must be a MacroSeriesMap")
    cutoff = previous_eligible_eod(security.exchange, prediction)
    assert_pit_safe((security,), cutoff)
    if security.quality is QualityTier.C:
        raise ValueError("QUALITY_BELOW_FLOOR:classification_requires_tier_b")
    active_from = _iso_date(security.active_from, "active_from")
    active_to = None if security.active_to is None else _iso_date(security.active_to, "active_to")
    if cutoff.date() < active_from or (active_to is not None and cutoff.date() >= active_to):
        raise ValueError("INACTIVE_SECURITY_CLASSIFICATION")
    jurisdiction = security.monetary_jurisdiction
    if not isinstance(jurisdiction, str) or not jurisdiction.strip():
        raise ValueError("UNKNOWN_MONETARY_JURISDICTION")

    materialized = tuple(observations)
    region_series = series_map.regional.get(security.region)
    if region_series is None:
        raise ValueError(f"UNSUPPORTED_MACRO_REGION:{security.region}")
    policy_series = series_map.policy_rate.get(jurisdiction)
    liquidity_series = series_map.central_bank_liquidity.get(jurisdiction)
    roles: dict[str, str | None] = dict(region_series)
    roles["policy_rate"] = policy_series
    roles["central_bank_liquidity"] = liquidity_series
    roles["global_risk_off"] = series_map.global_risk_off
    if security.region is Region.US:
        roles.update({f"us_{role}": series for role, series in series_map.us_rates.items()})
    elif security.region is Region.EU:
        roles.update({f"eu_{role}": series for role, series in series_map.eu_rates.items()})

    selected: dict[str, Observation] = {}
    for role, series in roles.items():
        if series is None:
            continue
        row = _select(materialized, series, cutoff)
        if row is not None:
            selected[role] = row

    policy = selected.get("policy_rate")
    policy_prior = None
    if policy is not None and policy_series is not None:
        policy_prior = _select(
            materialized, policy_series, cutoff,
            no_later_than=_months_before(_iso_date(policy.observation_date, "observation_date"), 3),
        )
    liquidity = selected.get("central_bank_liquidity")
    liquidity_prior = None
    if liquidity is not None and liquidity_series is not None:
        liquidity_prior = _select(
            materialized, liquidity_series, cutoff,
            no_later_than=_months_before(_iso_date(liquidity.observation_date, "observation_date"), 3),
        )

    def value(role: str) -> float | None:
        row = selected.get(role)
        return None if row is None else _number(row.value)

    calculated = {
        "headline_inflation_level_raw": value("headline_inflation"),
        "core_inflation_level_raw": value("core_inflation"),
        "unemployment_rate_level_raw": value("unemployment_rate"),
        "policy_rate_level_raw": value("policy_rate"),
        "policy_rate_change_3m_raw": _difference(policy, policy_prior),
        "us_yield_curve_10y_2y_raw": _difference(selected.get("us_long_10y"), selected.get("us_short_2y")),
        "us_yield_curve_10y_3m_raw": _difference(selected.get("us_long_10y"), selected.get("us_short_3m")),
        "eu_sovereign_curve_proxy_raw": _difference(selected.get("eu_sovereign_long"), selected.get("eu_relevant_short")),
        "high_yield_spread_raw": value("high_yield_spread"),
        "investment_grade_spread_raw": value("investment_grade_spread"),
        "financial_conditions_level_raw": value("financial_conditions"),
        "central_bank_liquidity_change_3m_raw": _percent_change(liquidity, liquidity_prior),
        "global_risk_off_level_raw": value("global_risk_off"),
    }
    if set(calculated) != set(_MACRO_NAMES):
        raise ValueError("TASK5_MACRO_REGISTRY_MISMATCH")

    dependencies: dict[str, tuple[Observation | Security, ...]] = {
        name: (security,) for name in calculated
    }
    role_by_output = {
        "headline_inflation_level_raw": ("headline_inflation",),
        "core_inflation_level_raw": ("core_inflation",),
        "unemployment_rate_level_raw": ("unemployment_rate",),
        "policy_rate_level_raw": ("policy_rate",),
        "us_yield_curve_10y_2y_raw": ("us_long_10y", "us_short_2y"),
        "us_yield_curve_10y_3m_raw": ("us_long_10y", "us_short_3m"),
        "eu_sovereign_curve_proxy_raw": ("eu_sovereign_long", "eu_relevant_short"),
        "high_yield_spread_raw": ("high_yield_spread",),
        "investment_grade_spread_raw": ("investment_grade_spread",),
        "financial_conditions_level_raw": ("financial_conditions",),
        "global_risk_off_level_raw": ("global_risk_off",),
    }
    for name, role_names in role_by_output.items():
        dependencies[name] += tuple(selected[role] for role in role_names if role in selected)
    dependencies["policy_rate_change_3m_raw"] += tuple(
        row for row in (policy, policy_prior) if row is not None
    )
    dependencies["central_bank_liquidity_change_3m_raw"] += tuple(
        row for row in (liquidity, liquidity_prior) if row is not None
    )

    features = []
    for name in _MACRO_NAMES:
        inputs = dependencies[name]
        features.append(FeatureValue(
            feature=name, entity_id=security.security_id,
            observation_date=cutoff.date().isoformat(), as_of=prediction,
            value=calculated[name],
            max_input_available_at=max(row.available_at for row in inputs),
            available_at=cutoff,
            quality=max((row.quality for row in inputs), key=_QUALITY_ORDER.__getitem__),
            source="point_in_time_macro_features", revision_id="features-v1",
            currency=security.currency, region=security.region, exchange=security.exchange,
        ))
    result = MacroFeatureSnapshot(tuple(features), selected, dependencies, series_map)
    assert_pit_safe(result.features, prediction)
    return result
