"""Leakage-safe rolling, cross-sectional, and fold-local transforms.

The evidenced cross-sectional boundary operates on canonical ``FeatureValue``
records and an explicit historical ``UniverseIndex``.  ``FoldImputer`` accepts
only bounded partitions: it is deliberately not a whole-feature-table helper.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import math
import re
from statistics import stdev
from types import MappingProxyType

import pandas as pd

from quant_dca.point_in_time.asof import assert_pit_safe, latest_known
from quant_dca.types import FeatureValue, Region, Security
from quant_dca.universe.membership import UniverseIndex


_NORMALIZATION_METHODS = frozenset({"percentile", "zscore"})
_NUMERIC_STRATEGIES = frozenset({None, "median"})
_CATEGORICAL_STRATEGIES = frozenset({None, "most_frequent"})
_IDENTITY_TOKENS = frozenset(
    {
        "ticker",
        "symbol",
        "isin",
        "cusip",
        "sedol",
        "figi",
        "securityid",
        "entityid",
    }
)
_TARGET_TOKENS = frozenset({"target", "label", "outcome"})
_KNOWN_TARGET_PREFIXES = (
    "better_entry_",
    "executable_min_return_",
    "target_end_",
)
_KNOWN_TARGET_NAMES = frozenset({"return_5d", "return_20d", "return_60d"})
_CANONICAL_RETURN_TARGET = re.compile(r"(?:return|direction)_(?:5|20|60)d_(?:local|huf)")


def _aware(value: object, field: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field} must be a timezone-aware datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be a timezone-aware datetime")
    return value


def _number(value: object, *, field: str) -> float | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field} must contain only numeric values or missing values")
    result = float(value)
    return result if math.isfinite(result) else None


def rolling_zscore(
    series: Sequence[float | int | None], window: int
) -> list[float | None]:
    """Return sample z-scores from inclusive trailing windows only.

    A complete finite window is required.  Missing values and zero-dispersion
    windows stay missing rather than being assigned an artificial neutral value.
    """
    if not isinstance(window, int) or isinstance(window, bool) or window < 2:
        raise ValueError("window must be an integer of at least 2")
    values = [_number(value, field="series") for value in series]
    output: list[float | None] = []
    for position, current in enumerate(values):
        if position + 1 < window:
            output.append(None)
            continue
        trailing = values[position + 1 - window : position + 1]
        if current is None or any(value is None for value in trailing):
            output.append(None)
            continue
        finite = [value for value in trailing if value is not None]
        scale = stdev(finite)
        if scale == 0:
            output.append(None)
            continue
        output.append((current - sum(finite) / window) / scale)
    return output


@dataclass(frozen=True, slots=True)
class CrossSectionSnapshot:
    """Normalized values and the exact PIT cohort/input evidence used."""

    values: Mapping[str, float | None]
    eligible_security_ids: tuple[str, ...]
    selected_inputs: tuple[FeatureValue, ...]
    eligibility_evidence: tuple[Security, ...]
    historical_cutoff: datetime
    prediction_timestamp: datetime
    method: str


class CrossSectionNormalizer:
    """Normalize one feature across an explicitly reconstructed historical cohort."""

    def __init__(self, method: str) -> None:
        if method not in _NORMALIZATION_METHODS:
            raise ValueError(f"method must be one of {sorted(_NORMALIZATION_METHODS)}")
        self._method = method

    def transform(
        self,
        rows: Iterable[FeatureValue],
        *,
        universe_index: UniverseIndex,
        historical_cutoff: datetime,
        prediction_timestamp: datetime,
        region: Region,
    ) -> CrossSectionSnapshot:
        """Select known vintages and normalize only historically eligible names."""
        cutoff = _aware(historical_cutoff, "historical_cutoff")
        prediction = _aware(prediction_timestamp, "prediction_timestamp")
        if cutoff > prediction:
            raise ValueError("PIT_LEAKAGE:cross_section_cutoff_after_prediction")
        if not isinstance(universe_index, UniverseIndex):
            raise TypeError("universe_index must be a UniverseIndex")
        if region not in (Region.US, Region.EU):
            raise ValueError("region must be US or EU")

        materialized = tuple(rows)
        if any(not isinstance(row, FeatureValue) for row in materialized):
            raise TypeError("cross-section inputs must be FeatureValue records")
        known = tuple(row for row in materialized if row.available_at <= cutoff)
        if not known:
            raise ValueError("NO_KNOWN_CROSS_SECTION_INPUTS")

        feature_names = {row.feature for row in known}
        observation_dates = {row.observation_date for row in known}
        if len(feature_names) != 1 or len(observation_dates) != 1:
            raise ValueError("UNALIGNED_CROSS_SECTION_INPUTS")
        if any(row.entity_id is None for row in known):
            raise ValueError("CROSS_SECTION_ENTITY_REQUIRED")

        securities = tuple(universe_index.eligible_universe(cutoff, region))
        eligible_ids = tuple(security.security_id for security in securities)
        eligible = frozenset(eligible_ids)
        groups: dict[str, list[FeatureValue]] = defaultdict(list)
        for row in known:
            if row.entity_id in eligible:
                groups[row.entity_id].append(row)

        selected: dict[str, FeatureValue] = {}
        for security_id in eligible_ids:
            candidates = groups.get(security_id)
            if not candidates:
                continue
            row = latest_known(candidates, cutoff)
            assert_pit_safe([row], prediction)
            if row.available_at > cutoff or row.max_input_available_at > cutoff:
                raise ValueError("PIT_LEAKAGE:cross_section_input_after_cutoff")
            if row.region is not region:
                raise ValueError("CROSS_SECTION_REGION_MISMATCH")
            selected[security_id] = row

        numbers = {
            security_id: _number(row.value, field="cross-section value")
            for security_id, row in selected.items()
        }
        finite = sorted(value for value in numbers.values() if value is not None)
        normalized: dict[str, float | None] = {}
        if self._method == "percentile":
            for security_id, value in numbers.items():
                if value is None or not finite:
                    normalized[security_id] = None
                elif len(finite) == 1:
                    normalized[security_id] = 0.5
                else:
                    lower = sum(candidate < value for candidate in finite)
                    equal = sum(candidate == value for candidate in finite)
                    normalized[security_id] = (lower + (equal - 1) / 2) / (
                        len(finite) - 1
                    )
        else:
            scale = stdev(finite) if len(finite) >= 2 else 0.0
            mean = sum(finite) / len(finite) if finite else 0.0
            for security_id, value in numbers.items():
                normalized[security_id] = (
                    None if value is None or scale == 0 else (value - mean) / scale
                )

        return CrossSectionSnapshot(
            values=MappingProxyType(normalized),
            eligible_security_ids=eligible_ids,
            selected_inputs=tuple(selected[key] for key in sorted(selected)),
            eligibility_evidence=securities,
            historical_cutoff=cutoff,
            prediction_timestamp=prediction,
            method=self._method,
        )


class PartitionRole(StrEnum):
    TRAIN = "train"
    VALIDATION = "validation"
    OUTER_OOS = "outer_oos"
    HOLDOUT = "holdout"


@dataclass(frozen=True, slots=True, kw_only=True)
class FoldPartition:
    """Feature-only matrix with explicit fold role, time bounds, and missing mask."""

    data: pd.DataFrame
    role: PartitionRole
    fold_id: str
    starts_at: datetime
    ends_at: datetime
    structural_missing: pd.DataFrame | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.data, pd.DataFrame):
            raise TypeError("data must be a pandas DataFrame")
        if not isinstance(self.role, PartitionRole):
            raise TypeError("role must be a PartitionRole")
        if not isinstance(self.fold_id, str) or not self.fold_id.strip():
            raise ValueError("fold_id must be non-empty")
        start = _aware(self.starts_at, "starts_at")
        end = _aware(self.ends_at, "ends_at")
        if start > end:
            raise ValueError("partition starts_at must not follow ends_at")
        if self.data.columns.has_duplicates or any(
            not isinstance(column, str) or not column for column in self.data.columns
        ):
            raise ValueError("partition columns must be unique non-empty strings")

        data = self.data.copy(deep=True)
        if self.structural_missing is None:
            mask = pd.DataFrame(False, index=data.index, columns=data.columns)
        else:
            if not isinstance(self.structural_missing, pd.DataFrame):
                raise TypeError("structural_missing must be a pandas DataFrame")
            mask = self.structural_missing.copy(deep=True)
            if not mask.index.equals(data.index) or not mask.columns.equals(data.columns):
                raise ValueError("structural_missing must align exactly with data")
            if any(dtype != bool for dtype in mask.dtypes):
                raise TypeError("structural_missing must contain booleans")
            if (mask & data.notna()).to_numpy().any():
                raise ValueError("structural missing cells must be missing in data")
        object.__setattr__(self, "data", data)
        object.__setattr__(self, "structural_missing", mask)


def _tokens(name: str) -> frozenset[str]:
    return frozenset(token for token in re.split(r"[^a-z0-9]+", name.lower()) if token)


def _validate_feature_name(name: str) -> None:
    compact = re.sub(r"[^a-z0-9]", "", name.lower())
    if _tokens(name) & _IDENTITY_TOKENS or compact in _IDENTITY_TOKENS:
        raise ValueError(f"direct identity feature is forbidden: {name!r}")
    if (
        _tokens(name) & _TARGET_TOKENS
        or name.lower().startswith(_KNOWN_TARGET_PREFIXES)
        or name.lower() in _KNOWN_TARGET_NAMES
        or _CANONICAL_RETURN_TARGET.fullmatch(name.lower()) is not None
    ):
        raise ValueError(f"target data is forbidden in FoldImputer: {name!r}")


class FoldImputer:
    """Fit-once, train-partition-only imputation for a single declared fold."""

    def __init__(
        self,
        *,
        numeric_columns: Sequence[str] = (),
        categorical_columns: Sequence[str] = (),
        numeric_strategy: str | None = "median",
        categorical_strategy: str | None = "most_frequent",
    ) -> None:
        numeric = tuple(numeric_columns)
        categorical = tuple(categorical_columns)
        if not numeric and not categorical:
            raise ValueError("at least one feature column is required")
        if len(set((*numeric, *categorical))) != len(numeric) + len(categorical):
            raise ValueError("numeric and categorical columns must be disjoint and unique")
        for name in (*numeric, *categorical):
            if not isinstance(name, str) or not name:
                raise TypeError("feature column names must be non-empty strings")
            _validate_feature_name(name)
        if numeric_strategy not in _NUMERIC_STRATEGIES:
            raise ValueError("numeric_strategy must be 'median' or None")
        if categorical_strategy not in _CATEGORICAL_STRATEGIES:
            raise ValueError("categorical_strategy must be 'most_frequent' or None")
        self._numeric_columns = numeric
        self._categorical_columns = categorical
        self._numeric_strategy = numeric_strategy
        self._categorical_strategy = categorical_strategy
        self._numeric_statistics: dict[str, float | None] | None = None
        self._categorical_statistics: dict[str, str | None] | None = None
        self._fold_id: str | None = None
        self._train_bounds: tuple[datetime, datetime] | None = None

    @property
    def numeric_statistics(self) -> dict[str, float | None]:
        if self._numeric_statistics is None:
            raise RuntimeError("FoldImputer is not fitted")
        return dict(self._numeric_statistics)

    @property
    def categorical_statistics(self) -> dict[str, str | None]:
        if self._categorical_statistics is None:
            raise RuntimeError("FoldImputer is not fitted")
        return dict(self._categorical_statistics)

    def _validate_partition(self, partition: object) -> FoldPartition:
        if not isinstance(partition, FoldPartition):
            raise TypeError("FoldImputer requires a FoldPartition")
        expected = set((*self._numeric_columns, *self._categorical_columns))
        actual = set(partition.data.columns)
        if actual != expected:
            raise ValueError(
                f"FEATURE_SCHEMA_MISMATCH: expected={sorted(expected)}, actual={sorted(actual)}"
            )
        for column in self._numeric_columns:
            for value in partition.data[column].dropna():
                _number(value, field=column)
        for column in self._categorical_columns:
            if any(not isinstance(value, str) for value in partition.data[column].dropna()):
                raise TypeError(f"categorical column {column!r} must contain strings or missing")
        return partition

    def fit(self, train: FoldPartition) -> FoldImputer:
        """Fit explicit strategies on one training partition, exactly once."""
        if self._fold_id is not None:
            raise RuntimeError("FoldImputer is already fitted")
        partition = self._validate_partition(train)
        if partition.role is not PartitionRole.TRAIN:
            raise ValueError("TRAIN_PARTITION_REQUIRED")

        numeric_statistics: dict[str, float | None] = {}
        for column in self._numeric_columns:
            values = [
                _number(value, field=column)
                for value in partition.data[column]
                if not pd.isna(value)
            ]
            numeric_statistics[column] = (
                None
                if self._numeric_strategy is None or not values
                else float(pd.Series(values, dtype="float64").median())
            )
        categorical_statistics: dict[str, str | None] = {}
        for column in self._categorical_columns:
            values = [value for value in partition.data[column] if not pd.isna(value)]
            if self._categorical_strategy is None or not values:
                categorical_statistics[column] = None
            else:
                counts = Counter(values)
                highest = max(counts.values())
                categorical_statistics[column] = min(
                    value for value, count in counts.items() if count == highest
                )

        self._numeric_statistics = numeric_statistics
        self._categorical_statistics = categorical_statistics
        self._fold_id = partition.fold_id
        self._train_bounds = (partition.starts_at, partition.ends_at)
        return self

    def transform(self, data: FoldPartition) -> pd.DataFrame:
        """Apply stored train statistics without learning from transformed data."""
        if self._fold_id is None or self._train_bounds is None:
            raise RuntimeError("FoldImputer is not fitted")
        partition = self._validate_partition(data)
        if partition.fold_id != self._fold_id:
            raise ValueError("FOLD_ID_MISMATCH")
        train_start, train_end = self._train_bounds
        if partition.role is PartitionRole.TRAIN:
            if (partition.starts_at, partition.ends_at) != (train_start, train_end):
                raise ValueError("TRAIN_PARTITION_BOUNDARY_MISMATCH")
        elif partition.starts_at <= train_end:
            raise ValueError("PARTITION_BOUNDARY_OVERLAP")

        result = partition.data.copy(deep=True)
        statistics: dict[str, object | None] = {
            **self.numeric_statistics,
            **self.categorical_statistics,
        }
        for column, statistic in statistics.items():
            structural = partition.structural_missing[column]
            ordinary_missing = result[column].isna() & ~structural
            if statistic is not None:
                result.loc[ordinary_missing, column] = statistic
            result.loc[structural, column] = pd.NA
        return result
