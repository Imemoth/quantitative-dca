"""Versioned, machine-validated feature registry.

The registry describes inputs and transformations; it does not calculate
features, select providers, fit normalizers, or make empirical feature choices.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any

import yaml

from quant_dca.types import QualityTier


_PIT_JOIN_RULE = "available_at <= prediction_timestamp"
_HISTORICAL_EOD_FX_JOIN_RULE = (
    "fixing_at <= historical_eod and available_at <= historical_eod"
)
_PIT_AVAILABILITY_FIELD = "available_at"
_PIT_REVISION_POLICY = "as_of_vintage"
_FORBIDDEN_IDENTITY_COMPONENTS = frozenset(
    {
        "ticker",
        "symbol",
        "isin",
        "cusip",
        "sedol",
        "figi",
        "securityid",
        "entityid",
        "instrumentid",
    }
)
_FORBIDDEN_IDENTITY_PAIRS = frozenset(
    {
        ("security", "id"),
        ("security", "identifier"),
        ("entity", "id"),
        ("entity", "identifier"),
        ("instrument", "id"),
        ("instrument", "identifier"),
        ("issuer", "id"),
        ("issuer", "identifier"),
    }
)
_FEATURE_FIELDS = frozenset(
    {
        "name",
        "domain",
        "base_signal",
        "raw_dependencies",
        "lookback_sessions",
        "availability_rule",
        "quality_floor",
        "transform",
        "formula",
        "normalization",
        "applicability",
        "missing_policy",
    }
)
_DEPENDENCY_FIELDS = frozenset(
    {
        "name",
        "availability_field",
        "join_rule",
        "revision_policy",
        "value_basis",
        "required_provenance",
    }
)
_ROOT_FIELDS = frozenset(
    {"schema_version", "registry_version", "panel_budget", "dependencies", "features"}
)
_ALLOWED_DOMAINS = frozenset(
    {
        "price_trend",
        "volatility_drawdown",
        "volume_liquidity",
        "relative_strength",
        "fundamentals",
        "valuation",
        "market_cross_asset",
        "event_calendar",
        "structural",
        "macro",
    }
)
_ALLOWED_AVAILABILITY_RULES = frozenset(
    {
        "next_eod_after_all_inputs_available",
        "reported_value_as_of_prediction_then_next_eod",
        "known_event_date_as_of_prediction_then_next_eod",
        "historical_membership_as_of_prediction",
    }
)
_ALLOWED_MISSING_POLICIES = frozenset(
    {"preserve_missing", "structural_missing_not_imputed"}
)


class FeatureRegistryError(ValueError):
    """Raised when a registry file violates the frozen schema."""


@dataclass(frozen=True, slots=True)
class RawDependency:
    """A raw input and its mandatory point-in-time selection semantics."""

    name: str
    availability_field: str
    join_rule: str
    revision_policy: str
    value_basis: str
    required_provenance: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FeatureDefinition:
    """Auditable contract for one final model feature."""

    name: str
    domain: str
    raw_dependencies: tuple[RawDependency, ...]
    lookback_sessions: int
    availability_rule: str
    quality_floor: QualityTier
    transform: str
    base_signal: str
    formula: str
    normalization: str
    applicability: str
    missing_policy: str


@dataclass(frozen=True, slots=True)
class PanelBudget:
    """Bounded allocation for registered features and later regime outputs."""

    final_min: int
    final_max: int
    registered_feature_count: int
    reserved_interpretable_regime_slots: int
    reserved_unsupervised_regime_slots: int


class FeatureRegistry:
    """Immutable collection of feature definitions keyed by unique name."""

    def __init__(
        self,
        *,
        version: str,
        definitions: tuple[FeatureDefinition, ...],
        panel_budget: PanelBudget,
    ):
        if not version:
            raise FeatureRegistryError("registry_version must be non-empty")
        by_name: dict[str, FeatureDefinition] = {}
        for definition in definitions:
            if definition.name in by_name:
                raise FeatureRegistryError(
                    f"duplicate feature name: {definition.name!r}"
                )
            by_name[definition.name] = definition
        self._version = version
        self._definitions = definitions
        self._by_name: Mapping[str, FeatureDefinition] = MappingProxyType(by_name)
        self._panel_budget = panel_budget
        if panel_budget.registered_feature_count != len(definitions):
            raise FeatureRegistryError(
                "panel_budget.registered_feature_count must match features"
            )
        if not panel_budget.final_min <= self.final_panel_size <= panel_budget.final_max:
            raise FeatureRegistryError("planned final panel falls outside panel_budget")

    @property
    def version(self) -> str:
        return self._version

    @property
    def panel_budget(self) -> PanelBudget:
        return self._panel_budget

    @property
    def final_panel_size(self) -> int:
        return (
            self._panel_budget.registered_feature_count
            + self._panel_budget.reserved_interpretable_regime_slots
            + self._panel_budget.reserved_unsupervised_regime_slots
        )

    def __iter__(self) -> Iterator[FeatureDefinition]:
        return iter(self._definitions)

    def __len__(self) -> int:
        return len(self._definitions)

    def __getitem__(self, name: str) -> FeatureDefinition:
        return self._by_name[name]

    def names(self) -> tuple[str, ...]:
        return tuple(self._by_name)

    def base_signal_names(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(d.base_signal for d in self._definitions))

    @classmethod
    def v1(cls) -> FeatureRegistry:
        path = Path(__file__).resolve().parents[3] / "configs" / "features_v1.yaml"
        registry = cls.from_yaml(path)
        if registry.version != "features-v1":
            raise FeatureRegistryError("V1 file must declare registry_version features-v1")
        if not 50 <= len(registry.base_signal_names()) <= 100:
            raise FeatureRegistryError("V1 must contain 50-100 controlled base signals")
        if registry.panel_budget.final_min != 80 or registry.panel_budget.final_max != 95:
            raise FeatureRegistryError("V1 final panel bounds must be 80-95")
        return registry

    @classmethod
    def from_yaml(cls, path: str | Path) -> FeatureRegistry:
        source = Path(path)
        try:
            payload = yaml.safe_load(source.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise FeatureRegistryError(f"cannot load feature registry {source}: {exc}") from exc
        if not isinstance(payload, dict):
            raise FeatureRegistryError("registry root must be a mapping")
        if set(payload) != _ROOT_FIELDS:
            raise FeatureRegistryError(
                "registry fields invalid; "
                f"missing={sorted(_ROOT_FIELDS - set(payload))}, "
                f"unknown={sorted(set(payload) - _ROOT_FIELDS)}"
            )
        if payload.get("schema_version") != 1:
            raise FeatureRegistryError("schema_version must be 1")
        version = _required_string(payload, "registry_version", "registry")
        panel_budget = _parse_panel_budget(payload.get("panel_budget"))
        dependency_specs = _parse_dependency_specs(payload.get("dependencies"))
        rows = payload.get("features")
        if not isinstance(rows, list) or not rows:
            raise FeatureRegistryError("features must be a non-empty list")
        definitions = tuple(
            _parse_feature(row, dependency_specs, index) for index, row in enumerate(rows)
        )
        return cls(
            version=version, definitions=definitions, panel_budget=panel_budget
        )


def _parse_panel_budget(raw: Any) -> PanelBudget:
    fields = {
        "final_min",
        "final_max",
        "registered_feature_count",
        "reserved_interpretable_regime_slots",
        "reserved_unsupervised_regime_slots",
    }
    if not isinstance(raw, dict) or set(raw) != fields:
        raise FeatureRegistryError(f"panel_budget must contain exactly {sorted(fields)}")
    if any(isinstance(raw[field], bool) or not isinstance(raw[field], int) for field in fields):
        raise FeatureRegistryError("panel_budget values must be integers")
    if raw["final_min"] < 1 or raw["final_max"] < raw["final_min"]:
        raise FeatureRegistryError("panel_budget bounds are invalid")
    if raw["registered_feature_count"] < 1:
        raise FeatureRegistryError("registered_feature_count must be positive")
    if raw["reserved_interpretable_regime_slots"] != 5:
        raise FeatureRegistryError("interpretable regime reserve must be 5")
    if not 3 <= raw["reserved_unsupervised_regime_slots"] <= 8:
        raise FeatureRegistryError("unsupervised regime reserve must be between 3 and 8")
    return PanelBudget(**{field: raw[field] for field in fields})


def _parse_dependency_specs(raw: Any) -> dict[str, RawDependency]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise FeatureRegistryError("dependencies must be a mapping")
    parsed: dict[str, RawDependency] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            raise FeatureRegistryError("dependency entries must be named mappings")
        parsed[key] = _parse_dependency(value, f"dependency {key!r}")
    return parsed


def _parse_dependency(raw: Any, context: str) -> RawDependency:
    if not isinstance(raw, dict):
        raise FeatureRegistryError(f"{context} must be a mapping")
    unknown = set(raw) - _DEPENDENCY_FIELDS
    missing = _DEPENDENCY_FIELDS - set(raw)
    if unknown or missing:
        raise FeatureRegistryError(
            f"{context} fields invalid; missing={sorted(missing)}, unknown={sorted(unknown)}"
        )
    dependency = RawDependency(
        name=_required_string(raw, "name", context),
        availability_field=_required_string(raw, "availability_field", context),
        join_rule=_required_string(raw, "join_rule", context),
        revision_policy=_required_string(raw, "revision_policy", context),
        value_basis=_required_string(raw, "value_basis", context),
        required_provenance=_required_string_list(
            raw, "required_provenance", context
        ),
    )
    if dependency.availability_field != _PIT_AVAILABILITY_FIELD:
        raise FeatureRegistryError(f"{context} must use available_at")
    expected_join_rule = (
        _HISTORICAL_EOD_FX_JOIN_RULE
        if dependency.name == "fx.quotes"
        else _PIT_JOIN_RULE
    )
    if dependency.join_rule != expected_join_rule:
        raise FeatureRegistryError(f"{context} must enforce {expected_join_rule}")
    if dependency.revision_policy != _PIT_REVISION_POLICY:
        raise FeatureRegistryError(f"{context} must use as_of_vintage")
    _reject_identity(dependency.name, context)
    return dependency


def _parse_feature(
    raw: Any, dependency_specs: Mapping[str, RawDependency], index: int
) -> FeatureDefinition:
    context = f"feature[{index}]"
    if not isinstance(raw, dict):
        raise FeatureRegistryError(f"{context} must be a mapping")
    unknown = set(raw) - _FEATURE_FIELDS
    missing = _FEATURE_FIELDS - set(raw)
    if unknown or missing:
        raise FeatureRegistryError(
            f"{context} fields invalid; missing={sorted(missing)}, unknown={sorted(unknown)}"
        )
    dependencies_raw = raw["raw_dependencies"]
    if not isinstance(dependencies_raw, list) or not dependencies_raw:
        raise FeatureRegistryError(f"{context}.raw_dependencies must be non-empty")
    dependencies: list[RawDependency] = []
    for dependency_index, dependency_raw in enumerate(dependencies_raw):
        dependency_context = f"{context}.raw_dependencies[{dependency_index}]"
        if isinstance(dependency_raw, str):
            try:
                dependencies.append(dependency_specs[dependency_raw])
            except KeyError as exc:
                raise FeatureRegistryError(
                    f"{dependency_context} references unknown dependency {dependency_raw!r}"
                ) from exc
        else:
            dependencies.append(_parse_dependency(dependency_raw, dependency_context))

    lookback = raw["lookback_sessions"]
    if isinstance(lookback, bool) or not isinstance(lookback, int) or lookback < 0:
        raise FeatureRegistryError(f"{context}.lookback_sessions must be a nonnegative int")
    try:
        quality_floor = QualityTier(raw["quality_floor"])
    except (TypeError, ValueError) as exc:
        raise FeatureRegistryError(f"{context}.quality_floor must be A, B, or C") from exc
    domain = _required_string(raw, "domain", context)
    if domain not in _ALLOWED_DOMAINS:
        raise FeatureRegistryError(f"{context}.domain is not controlled: {domain!r}")
    availability_rule = _required_string(raw, "availability_rule", context)
    if availability_rule not in _ALLOWED_AVAILABILITY_RULES:
        raise FeatureRegistryError(
            f"{context}.availability_rule is not controlled: {availability_rule!r}"
        )
    missing_policy = _required_string(raw, "missing_policy", context)
    if missing_policy not in _ALLOWED_MISSING_POLICIES:
        raise FeatureRegistryError(
            f"{context}.missing_policy is not controlled: {missing_policy!r}"
        )

    string_fields = {
        field: _required_string(raw, field, context)
        for field in (
            "name",
            "base_signal",
            "transform",
            "formula",
            "normalization",
            "applicability",
        )
    }
    for field, value in string_fields.items():
        _reject_identity(value, f"{context}.{field}")
    return FeatureDefinition(
        name=string_fields["name"],
        domain=domain,
        base_signal=string_fields["base_signal"],
        raw_dependencies=tuple(dependencies),
        lookback_sessions=lookback,
        availability_rule=availability_rule,
        quality_floor=quality_floor,
        transform=string_fields["transform"],
        formula=string_fields["formula"],
        normalization=string_fields["normalization"],
        applicability=string_fields["applicability"],
        missing_policy=missing_policy,
    )


def _required_string(raw: Mapping[str, Any], field: str, context: str) -> str:
    value = raw.get(field)
    if not isinstance(value, str) or not value.strip():
        raise FeatureRegistryError(f"{context}.{field} must be a non-empty string")
    return value


def _required_string_list(
    raw: Mapping[str, Any], field: str, context: str
) -> tuple[str, ...]:
    value = raw.get(field)
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item.strip() for item in value)
    ):
        raise FeatureRegistryError(
            f"{context}.{field} must be a non-empty list of non-empty strings"
        )
    return tuple(value)


def _reject_identity(value: str, context: str) -> None:
    components = re.findall(r"[a-z0-9]+", value.lower())
    component_set = set(components)
    adjacent_pairs = set(zip(components, components[1:]))
    if (
        component_set & _FORBIDDEN_IDENTITY_COMPONENTS
        or adjacent_pairs & _FORBIDDEN_IDENTITY_PAIRS
    ):
        raise FeatureRegistryError(f"{context} contains prohibited direct security identity")
