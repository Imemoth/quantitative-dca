"""Transparent five-state heuristic with a separate evidenced PIT boundary.

``predict_proba`` / ``explain`` are pure numeric demonstrations. Their historical
aliases vol_z/credit_z mean fixed reference scores, NOT estimated z-scores.
Only ``predict`` checks canonical feature provenance and benchmark chronology.
No fitting, threshold selection, future labels, or research data access occurs.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
from types import MappingProxyType

import yaml

from quant_dca.calendars.service import previous_eligible_eod
from quant_dca.features.normalize import PartitionRole
from quant_dca.point_in_time.asof import assert_pit_safe
from quant_dca.types import FeatureValue, QualityTier, Region


STATES = ("EXPANSION_RISK_ON", "CORRECTION", "HIGH_VOL_STRESS", "CRISIS", "RECOVERY")
_DIMENSIONS = ("market_trend", "vol_z", "credit_z")
_FEATURES = ("broad_market_momentum_20d_raw", "vix_level_raw", "high_yield_spread_raw")
_UNITS = dict(zip(_FEATURES, ("fractional_return", "index_points", "percentage_points")))
_CONFIG_KEYS = frozenset({
    "schema_version", "model_version", "interpretation", "centers", "scales",
    "input_units", "weights", "temperature", "clip", "prototypes",
    "recovery_lookback_sessions", "recovery_stress_threshold", "recovery_rebound_threshold",
})


def _freeze(value):
    return MappingProxyType({key: _freeze(item) for key, item in value.items()}) if isinstance(value, Mapping) else value


def _number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("FINITE_NUMERIC_REQUIRED")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError("FINITE_NUMERIC_REQUIRED") from exc
    if not math.isfinite(result):
        raise ValueError("FINITE_NUMERIC_REQUIRED")
    return result


def _vector(values: object) -> dict[str, float]:
    if not isinstance(values, Mapping) or set(values) != set(_DIMENSIONS):
        # Exact allowlist rejects identity, targets, and arbitrary extra signals.
        raise ValueError("REGIME_SCALAR_SCHEMA_MISMATCH")
    return {key: _number(values[key]) for key in _DIMENSIONS}


def _timestamp(value: object) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone-aware timestamp required")
    utc = value.astimezone(timezone.utc)
    if not 2010 <= utc.year <= 2023:
        raise ValueError("DEVELOPMENT_BOUNDARY: only 2010 through 2023")
    return utc


@dataclass(frozen=True, slots=True, kw_only=True)
class RegimePrediction:
    probabilities: Mapping[str, float]
    hard_state: str
    scores: Mapping[str, float]
    score_contributions: Mapping[str, Mapping[str, float]]
    normalized_inputs: Mapping[str, float]
    previous_inputs: Mapping[str, float] | None
    raw_inputs: Mapping[str, float]
    previous_raw_inputs: Mapping[str, float] | None
    recovery_checks: Mapping[str, bool]
    recovery_eligible: bool
    configuration: Mapping
    config_hash: str
    explanation: str
    pit_validated: bool = False
    evidence: tuple[FeatureValue, ...] = ()
    prediction_timestamp: datetime | None = None
    current_eod: datetime | None = None
    prior_eod: datetime | None = None
    benchmark_exchange: str | None = None
    region: Region | None = None
    partition_role: PartitionRole | None = None


class InterpretableRegimeModel:
    """Fixed prototype-distance model; there is deliberately no fit method.

    Configurable parameters define an unvalidated software baseline. Changing
    them is a versioned design choice, not permission for economic selection.
    """

    def __init__(self, configuration: Mapping):
        if not isinstance(configuration, Mapping) or set(configuration) != _CONFIG_KEYS:
            raise ValueError("REGIME_CONFIG_SCHEMA_MISMATCH")
        config = dict(configuration)
        if type(config["schema_version"]) is not int or config["schema_version"] != 1:
            raise ValueError("unsupported config schema")
        if not isinstance(config["model_version"], str) or not config["model_version"].strip():
            raise ValueError("model_version required")
        if config["interpretation"] != "uncalibrated_heuristic_membership":
            raise ValueError("heuristic interpretation required")
        if type(config["recovery_lookback_sessions"]) is not int or config["recovery_lookback_sessions"] != 1:
            raise ValueError("exactly one prior benchmark session required")
        if config["input_units"] != _UNITS:
            raise ValueError("canonical explicit input units required")
        config["input_units"] = dict(_UNITS)
        for key in ("centers", "scales", "weights"):
            config[key] = _vector(config[key])
        for key in ("temperature", "clip", "recovery_stress_threshold", "recovery_rebound_threshold"):
            config[key] = _number(config[key])
        if any(value <= 0 for key in ("weights", "scales") for value in config[key].values()):
            raise ValueError("weights and scales must be positive")
        if config["temperature"] <= 0 or config["clip"] <= 0:
            raise ValueError("temperature and clip must be positive")
        if config["recovery_stress_threshold"] <= 0 or config["recovery_rebound_threshold"] < 0:
            raise ValueError("recovery requires positive stress and nonnegative rebound threshold")
        if not isinstance(config["prototypes"], Mapping) or set(config["prototypes"]) != set(STATES):
            raise ValueError("all five prototypes required")
        config["prototypes"] = {state: _vector(config["prototypes"][state]) for state in STATES}
        if any(abs(value) > config["clip"] for row in config["prototypes"].values() for value in row.values()):
            raise ValueError("prototypes must lie within clip bounds")
        # Reject parameters whose scoring/physical-threshold arithmetic could overflow.
        try:
            bound = sum(4 * config["clip"] ** 2 * weight for weight in config["weights"].values()) / config["temperature"]
            _number(bound)
            for dimension in _DIMENSIONS:
                center, scale = config["centers"][dimension], config["scales"][dimension]
                for coordinate in (-config["clip"], config["clip"], config["recovery_stress_threshold"], config["recovery_rebound_threshold"]):
                    _number(center + coordinate * scale)
                _number(2 * config["clip"] * scale)
        except (ValueError, OverflowError) as exc:
            raise ValueError("unsafe config arithmetic") from exc
        self._hash = hashlib.sha256(json.dumps(config, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        self._config = _freeze(config)

    @classmethod
    def default(cls) -> InterpretableRegimeModel:
        return cls.from_yaml(Path(__file__).resolve().parents[3] / "configs" / "regimes_v1.yaml")

    @classmethod
    def from_yaml(cls, path: str | Path) -> InterpretableRegimeModel:
        return cls(yaml.safe_load(Path(path).read_text(encoding="utf-8")))

    def _recovery(self, current, previous, centers, scales) -> dict[str, bool]:
        threshold = self._config["recovery_stress_threshold"]
        risk = ("vol_z", "credit_z")
        return {
            "history_present": previous is not None,
            "prior_stress": previous is not None and any(previous[key] >= centers[key] + threshold * scales[key] for key in risk),
            "positive_rebound": current["market_trend"] > centers["market_trend"] + self._config["recovery_rebound_threshold"] * scales["market_trend"],
            "risk_nonincreasing": previous is not None and all(current[key] <= previous[key] for key in risk),
            "risk_easing": previous is not None and any(current[key] < previous[key] for key in risk),
        }

    def _normalize(self, values, centers, scales) -> dict[str, float]:
        limit = self._config["clip"]
        # Clip in physical units before subtracting/dividing to avoid overflow
        # for finite extremes. Recovery compares original values separately.
        return {
            key: max(-limit, min(limit, (
                max(centers[key] - limit * scales[key], min(centers[key] + limit * scales[key], values[key]))
                - centers[key]
            ) / scales[key])) for key in _DIMENSIONS
        }

    def _score(self, current, previous, *, centers, scales) -> RegimePrediction:
        recovery_checks = self._recovery(current, previous, centers, scales)
        recovery = all(recovery_checks.values())
        values = self._normalize(current, centers, scales)
        old = None if previous is None else self._normalize(previous, centers, scales)
        contributions = {
            state: {key: -self._config["weights"][key] * (values[key] - prototype[key]) ** 2 for key in _DIMENSIONS}
            for state, prototype in self._config["prototypes"].items()
        }
        scores = {state: sum(contributions[state].values()) for state in STATES}
        eligible = STATES if recovery else STATES[:-1]
        maximum = max(scores[state] for state in eligible)
        masses = {state: math.exp((scores[state] - maximum) / self._config["temperature"]) if state in eligible else 0. for state in STATES}
        total = sum(masses.values())
        probabilities = {state: masses[state] / total for state in STATES}
        return RegimePrediction(
            probabilities=_freeze(probabilities), hard_state=max(STATES, key=probabilities.__getitem__),
            scores=_freeze(scores), score_contributions=_freeze(contributions),
            normalized_inputs=_freeze(values), previous_inputs=None if old is None else _freeze(old),
            raw_inputs=_freeze(current), previous_raw_inputs=None if previous is None else _freeze(previous),
            recovery_checks=_freeze(recovery_checks),
            recovery_eligible=recovery, configuration=self._config, config_hash=self._hash,
            explanation=("uncalibrated heuristic memberships; fixed reference coordinates, not estimated z-scores. "
                         "Score = sum of displayed negative weighted squared distances; softmax(score / temperature) "
                         "over eligible states. Recovery requires prior stress, positive trend and easing risk. "
                         f"Recovery eligible: {recovery}. Exact ties use the documented state order. "
                         "Numeric helpers carry no PIT provenance."),
        )

    def explain(self, features: Mapping[str, float], *, previous: Mapping[str, float] | None = None) -> RegimePrediction:
        """Pure arithmetic only; optional prior scalars establish no chronology."""
        current = _vector(features)
        past = None if previous is None else _vector(previous)
        return self._score(current, past, centers=dict.fromkeys(_DIMENSIONS, 0.), scales=dict.fromkeys(_DIMENSIONS, 1.))

    def predict_proba(self, features: Mapping[str, float], *, previous: Mapping[str, float] | None = None) -> Mapping[str, float]:
        """Plan example helper; never use this as evidence of PIT compliance."""
        return self.explain(features, previous=previous).probabilities

    @staticmethod
    def _snapshot(rows: Iterable[FeatureValue], cutoff: datetime, region: Region) -> tuple[FeatureValue, ...]:
        records = tuple(rows)
        if any(not isinstance(row, FeatureValue) for row in records):
            raise TypeError("canonical FeatureValue required")
        if len(records) != len(_FEATURES) or {row.feature for row in records} != set(_FEATURES):
            raise ValueError("REGIME_FEATURE_SCHEMA_MISMATCH")
        for row in records:
            if row.entity_id is not None:
                raise ValueError("identity input forbidden")
            allowed_regions = (region, Region.GLOBAL) if row.feature == "vix_level_raw" else (region,)
            if not isinstance(row.region, Region) or row.region not in allowed_regions:
                raise ValueError("REGIME_REGION_MISMATCH")
            if not isinstance(row.quality, QualityTier) or (row.feature == "high_yield_spread_raw" and row.quality is QualityTier.C):
                raise ValueError("REGIME_INPUT_QUALITY")
            if any(not isinstance(value, str) or not value.strip() for value in (row.source, row.revision_id)):
                raise ValueError("REGIME_PROVENANCE_REQUIRED")
            for field in ("available_at", "as_of", "max_input_available_at", "published_at", "revised_at"):
                stamp = getattr(row, field)
                if stamp is not None:
                    _timestamp(stamp)
            try:
                observed = date.fromisoformat(row.observation_date)
            except (TypeError, ValueError) as exc:
                raise ValueError("invalid observation_date") from exc
            if observed.isoformat() != row.observation_date or not 2010 <= observed.year <= 2023:
                raise ValueError("DEVELOPMENT_BOUNDARY: observation_date")
            if observed > cutoff.date() or observed > row.available_at.astimezone(timezone.utc).date():
                raise ValueError("PIT_FUTURE_OBSERVATION")
        assert_pit_safe(records, cutoff)
        if any(row.as_of != cutoff for row in records):
            raise ValueError("REGIME_SNAPSHOT_CUTOFF_MISMATCH")
        return records

    def predict(
        self, inputs: Iterable[FeatureValue], *, historical_inputs: Iterable[FeatureValue] | None,
        prediction_timestamp: datetime, current_eod: datetime, prior_eod: datetime,
        benchmark_exchange: str, region: Region, partition_role: PartitionRole,
        feature_units: Mapping[str, str],
    ) -> RegimePrediction:
        """Score two canonical snapshots after ALL metadata checks, before values.

        Both snapshots must already be PIT-selected by their producers. No
        revision selection, normalization fitting or imputation is performed.
        Unit declarations apply to both snapshots; HY spreads are percentage
        points, never silently interpreted as basis points. Global VIX may be
        stale, but its own publication/input clocks must precede the regional EOD.
        computed_at is offline audit time and is not an economic-data clock.
        """
        if not isinstance(partition_role, PartitionRole):
            raise TypeError("PartitionRole required")
        if partition_role not in (PartitionRole.TRAIN, PartitionRole.VALIDATION):
            raise ValueError("DEVELOPMENT_PARTITION_REQUIRED")
        prediction, current, prior = map(_timestamp, (prediction_timestamp, current_eod, prior_eod))
        if not isinstance(region, Region) or region not in (Region.US, Region.EU):
            raise ValueError("explicit US or EU Region required")
        exchanges = ("XNYS", "XNAS") if region is Region.US else ("XETR", "XLON", "XPAR")
        if benchmark_exchange not in exchanges:
            raise ValueError("BENCHMARK_REGION_MISMATCH")
        if current != previous_eligible_eod(benchmark_exchange, prediction):
            raise ValueError("CURRENT_EOD_MISMATCH")
        if prior != previous_eligible_eod(benchmark_exchange, current - timedelta(microseconds=1)):
            raise ValueError("PRIOR_EOD_MISMATCH")
        if not isinstance(feature_units, Mapping) or dict(feature_units) != dict(self._config["input_units"]):
            raise ValueError("EXPLICIT_FEATURE_UNITS_REQUIRED")
        if historical_inputs is None:
            raise ValueError("HISTORY_REQUIRED")
        rows = self._snapshot(inputs, current, region)
        history = self._snapshot(historical_inputs, prior, region)
        # No numeric field is consumed until BOTH snapshots pass every check.
        current_by_name = {row.feature: row for row in rows}
        previous_by_name = {row.feature: row for row in history}
        values = {dimension: _number(current_by_name[name].value) for dimension, name in zip(_DIMENSIONS, _FEATURES)}
        past = {dimension: _number(previous_by_name[name].value) for dimension, name in zip(_DIMENSIONS, _FEATURES)}
        result = self._score(values, past, centers=self._config["centers"], scales=self._config["scales"])
        return replace(result, pit_validated=True, evidence=(*rows, *history),
                       prediction_timestamp=prediction, current_eod=current, prior_eod=prior,
                       benchmark_exchange=benchmark_exchange, region=region, partition_role=partition_role,
                       explanation=result.explanation + " This evidenced call validated both canonical snapshots at consecutive benchmark EODs.")
