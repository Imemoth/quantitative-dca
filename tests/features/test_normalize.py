from dataclasses import replace
from datetime import datetime, timedelta, timezone

import exchange_calendars
import pandas as pd
import pytest

from quant_dca.features.normalize import (
    CrossSectionNormalizer,
    FoldImputer,
    FoldPartition,
    PartitionRole,
    rolling_zscore,
)
from quant_dca.types import FeatureValue, QualityTier, Region, Security, UniverseMembership
from quant_dca.universe.membership import (
    EligibilityThresholds,
    FundamentalReport,
    LiquidityMetric,
    TradingSession,
    UniverseIndex,
)


UTC = timezone.utc
CUTOFF = datetime(2022, 1, 10, 21, tzinfo=UTC)
PREDICTION = datetime(2022, 1, 10, 23, tzinfo=UTC)


def test_rolling_zscore_uses_literal_trailing_sample_statistics():
    assert rolling_zscore([1.0, 2.0, 3.0, 4.0], 3) == [None, None, 1.0, 1.0]


def test_rolling_zscore_is_invariant_to_future_and_out_of_window_mutations():
    baseline = rolling_zscore([1.0, 2.0, 3.0, 4.0, 5.0], 3)
    future_mutated = rolling_zscore([1.0, 2.0, 3.0, 4.0, 5000.0], 3)
    old_history_mutated = rolling_zscore([1.0, -9999.0, 3.0, 4.0, 5.0], 3)

    assert baseline[:4] == future_mutated[:4]
    assert baseline[-1] == old_history_mutated[-1] == 1.0


def test_rolling_zscore_preserves_incomplete_and_zero_dispersion_windows():
    assert rolling_zscore([1.0, None, 3.0, 4.0, 5.0], 3) == [
        None,
        None,
        None,
        None,
        1.0,
    ]
    assert rolling_zscore([2.0, 2.0, 2.0], 3) == [None, None, None]
    with pytest.raises(ValueError, match="window"):
        rolling_zscore([1.0], 1)


def _security(security_id: str, *, active_from="2020-01-02") -> Security:
    return Security(
        security_id=security_id,
        ticker=security_id,
        name=security_id,
        currency="USD",
        region=Region.US,
        exchange="XNYS",
        active_from=active_from,
        available_at=datetime(2020, 1, 2, tzinfo=UTC),
        quality=QualityTier.A,
        source="historical-fixture",
        revision_id="v1",
    )


def _membership(security_id: str, *, active_from="2020-01-02") -> UniverseMembership:
    return UniverseMembership(
        universe_id="RESEARCH_US",
        security_id=security_id,
        active_from=active_from,
        region=Region.US,
        exchange="XNYS",
        currency="USD",
        available_at=datetime(2020, 1, 2, tzinfo=UTC),
        quality=QualityTier.A,
        source="historical-fixture",
        revision_id="v1",
    )


def _universe() -> UniverseIndex:
    historical = ("A", "B", "DELISTED_LATER")
    security_ids = (*historical, "FUTURE_MEMBER")
    labels = exchange_calendars.get_calendar("XNYS").sessions_in_range(
        "2021-01-01", "2021-12-31"
    )[:120]
    sessions = [
        TradingSession(
            security_id=security_id,
            exchange="XNYS",
            session_date=label.date().isoformat(),
            available_at=datetime.combine(label.date(), datetime.min.time(), UTC)
            + timedelta(days=1),
        )
        for security_id in security_ids
        for label in labels
    ]
    return UniverseIndex.from_rows(
        [
            *(_membership(security_id) for security_id in historical),
            _membership("FUTURE_MEMBER", active_from="2022-02-01"),
        ],
        securities=[
            *(_security(security_id) for security_id in historical),
            _security("FUTURE_MEMBER", active_from="2022-02-01"),
        ],
        trading_sessions=sessions,
        liquidity_metrics=[
            LiquidityMetric(
                security_id=security_id,
                measured_at=datetime(2022, 1, 7, 20, tzinfo=UTC),
                available_at=datetime(2022, 1, 7, 21, tzinfo=UTC),
                value=1_000_000,
            )
            for security_id in security_ids
        ],
        fundamental_reports=[
            FundamentalReport(
                security_id=security_id,
                published_at=datetime(2021, 11, 1, 12, tzinfo=UTC),
                available_at=datetime(2021, 11, 1, 13, tzinfo=UTC),
            )
            for security_id in security_ids
        ],
        thresholds=EligibilityThresholds(120, 1_000_000, True),
    )


def _feature(entity_id: str, value: float | None, **changes) -> FeatureValue:
    values = dict(
        feature="valuation_signal",
        entity_id=entity_id,
        observation_date="2022-01-10",
        as_of=PREDICTION,
        value=value,
        max_input_available_at=CUTOFF,
        available_at=CUTOFF,
        quality=QualityTier.A,
        source="verified-features",
        revision_id="features-v1",
        region=Region.US,
        exchange="XNYS",
        published_at=CUTOFF,
    )
    return FeatureValue(**(values | changes))


def test_cross_section_uses_explicit_historical_eligibility_and_retains_evidence():
    rows = [
        _feature("A", 10.0),
        _feature("B", 20.0),
        _feature("DELISTED_LATER", 15.0),
        _feature("FUTURE_MEMBER", 9999.0),
    ]

    snapshot = CrossSectionNormalizer("percentile").transform(
        rows,
        universe_index=_universe(),
        historical_cutoff=CUTOFF,
        prediction_timestamp=PREDICTION,
        region=Region.US,
    )

    assert dict(snapshot.values) == {"A": 0.0, "B": 1.0, "DELISTED_LATER": 0.5}
    assert snapshot.eligible_security_ids == ("A", "B", "DELISTED_LATER")
    assert tuple(row.entity_id for row in snapshot.selected_inputs) == (
        "A",
        "B",
        "DELISTED_LATER",
    )
    assert tuple(row.security_id for row in snapshot.eligibility_evidence) == (
        "A",
        "B",
        "DELISTED_LATER",
    )
    assert snapshot.historical_cutoff == CUTOFF


def test_cross_section_selects_only_vintages_known_by_historical_cutoff():
    old_b = _feature("B", 20.0, revision_id="b-v1")
    future_b = replace(
        old_b,
        value=-5000.0,
        available_at=PREDICTION + timedelta(days=1),
        max_input_available_at=PREDICTION + timedelta(days=1),
        published_at=PREDICTION + timedelta(days=1),
        revision_id="b-v2",
    )
    snapshot = CrossSectionNormalizer("percentile").transform(
        [_feature("A", 10.0), old_b, future_b, _feature("DELISTED_LATER", 15.0)],
        universe_index=_universe(),
        historical_cutoff=CUTOFF,
        prediction_timestamp=PREDICTION,
        region=Region.US,
    )

    assert dict(snapshot.values)["B"] == 1.0
    assert next(row for row in snapshot.selected_inputs if row.entity_id == "B") == old_b


def test_cross_section_rejects_unevidenced_or_future_cutoffs():
    rows = [_feature("A", 10.0)]
    normalizer = CrossSectionNormalizer("zscore")
    with pytest.raises(TypeError, match="UniverseIndex"):
        normalizer.transform(
            rows,
            universe_index=None,
            historical_cutoff=CUTOFF,
            prediction_timestamp=PREDICTION,
            region=Region.US,
        )
    with pytest.raises(ValueError, match="PIT_LEAKAGE"):
        normalizer.transform(
            rows,
            universe_index=_universe(),
            historical_cutoff=PREDICTION + timedelta(seconds=1),
            prediction_timestamp=PREDICTION,
            region=Region.US,
        )


def _partition(
    data: dict[str, list[object]],
    *,
    role: PartitionRole,
    start_day: int,
    end_day: int,
    fold_id: str = "fold-1",
    structural_missing: dict[str, list[bool]] | None = None,
) -> FoldPartition:
    frame = pd.DataFrame(data)
    mask = None if structural_missing is None else pd.DataFrame(structural_missing)
    return FoldPartition(
        data=frame,
        role=role,
        fold_id=fold_id,
        starts_at=datetime(2022, 1, start_day, tzinfo=UTC),
        ends_at=datetime(2022, 1, end_day, tzinfo=UTC),
        structural_missing=mask,
    )


def _train() -> FoldPartition:
    return _partition(
        {"value": [1.0, None, 3.0], "sector": ["growth", None, "growth"]},
        role=PartitionRole.TRAIN,
        start_day=1,
        end_day=3,
        structural_missing={
            "value": [False, True, False],
            "sector": [False, True, False],
        },
    )


def test_fold_imputer_uses_train_statistics_and_preserves_structural_missingness():
    validation = _partition(
        {
            "value": [None, None, 1000.0],
            "sector": [None, None, "value"],
        },
        role=PartitionRole.OUTER_OOS,
        start_day=4,
        end_day=6,
        structural_missing={
            "value": [False, True, False],
            "sector": [False, True, False],
        },
    )
    imputer = FoldImputer(
        numeric_columns=("value",),
        categorical_columns=("sector",),
        numeric_strategy="median",
        categorical_strategy="most_frequent",
    ).fit(_train())

    result = imputer.transform(validation)

    assert result.loc[0, "value"] == 2.0
    assert pd.isna(result.loc[1, "value"])
    assert result.loc[2, "value"] == 1000.0
    assert result.loc[0, "sector"] == "growth"
    assert pd.isna(result.loc[1, "sector"])
    assert result.loc[2, "sector"] == "value"
    assert imputer.numeric_statistics == {"value": 2.0}
    assert imputer.categorical_statistics == {"sector": "growth"}


def test_transform_cannot_refit_from_mutated_oos_values():
    imputer = FoldImputer(numeric_columns=("value",), categorical_columns=("sector",)).fit(
        _train()
    )
    extreme_oos = _partition(
        {"value": [None, 1_000_000.0], "sector": [None, "other"]},
        role=PartitionRole.OUTER_OOS,
        start_day=4,
        end_day=5,
    )
    later_oos = _partition(
        {"value": [None], "sector": [None]},
        role=PartitionRole.OUTER_OOS,
        start_day=6,
        end_day=6,
    )

    assert imputer.transform(extreme_oos).loc[0, "value"] == 2.0
    assert imputer.transform(later_oos).loc[0, "value"] == 2.0
    assert imputer.numeric_statistics == {"value": 2.0}
    with pytest.raises(RuntimeError, match="already fitted"):
        imputer.fit(_train())


@pytest.mark.parametrize("role", [PartitionRole.OUTER_OOS, PartitionRole.HOLDOUT])
def test_fold_imputer_rejects_fit_on_non_training_partitions(role):
    partition = _partition(
        {"value": [1.0], "sector": ["growth"]},
        role=role,
        start_day=4,
        end_day=4,
    )
    with pytest.raises(ValueError, match="TRAIN_PARTITION_REQUIRED"):
        FoldImputer(numeric_columns=("value",), categorical_columns=("sector",)).fit(
            partition
        )


def test_fold_imputer_hard_fails_cross_fold_and_overlapping_boundaries():
    imputer = FoldImputer(numeric_columns=("value",), categorical_columns=("sector",)).fit(
        _train()
    )
    wrong_fold = _partition(
        {"value": [None], "sector": [None]},
        role=PartitionRole.OUTER_OOS,
        start_day=4,
        end_day=4,
        fold_id="fold-2",
    )
    overlapping = _partition(
        {"value": [None], "sector": [None]},
        role=PartitionRole.HOLDOUT,
        start_day=3,
        end_day=4,
    )
    with pytest.raises(ValueError, match="FOLD_ID_MISMATCH"):
        imputer.transform(wrong_fold)
    with pytest.raises(ValueError, match="PARTITION_BOUNDARY_OVERLAP"):
        imputer.transform(overlapping)


@pytest.mark.parametrize("target_name", ["target_return_5d", "return_5d"])
def test_fold_imputer_requires_partition_scope_and_rejects_identity_or_targets(
    target_name,
):
    with pytest.raises(TypeError, match="FoldPartition"):
        FoldImputer(numeric_columns=("value",)).fit(pd.DataFrame({"value": [1.0]}))
    with pytest.raises(ValueError, match="identity"):
        FoldImputer(categorical_columns=("ticker",))
    with pytest.raises(ValueError, match="target"):
        FoldImputer(numeric_columns=(target_name,))


@pytest.mark.parametrize("column_kind", ["numeric", "categorical"])
def test_fold_imputer_rejects_canonical_entity_id_in_every_feature_schema(
    column_kind,
):
    arguments = (
        {"numeric_columns": ("entity_id",)}
        if column_kind == "numeric"
        else {"categorical_columns": ("entity_id",)}
    )

    with pytest.raises(ValueError, match="identity"):
        FoldImputer(**arguments)


def test_native_missing_strategies_remain_available_without_mutation():
    validation = _partition(
        {"value": [None], "sector": [None]},
        role=PartitionRole.OUTER_OOS,
        start_day=4,
        end_day=4,
    )
    imputer = FoldImputer(
        numeric_columns=("value",),
        categorical_columns=("sector",),
        numeric_strategy=None,
        categorical_strategy=None,
    ).fit(_train())

    result = imputer.transform(validation)

    assert pd.isna(result.loc[0, "value"])
    assert pd.isna(result.loc[0, "sector"])
    assert imputer.numeric_statistics == {"value": None}
    assert imputer.categorical_statistics == {"sector": None}


@pytest.mark.parametrize('column_kind',['numeric_columns','categorical_columns'])
@pytest.mark.parametrize('target_name',[
    f'{prefix}_{horizon}d_{currency}'
    for prefix,horizons in (('return',(5,20,60)),('direction',(5,20,60)),
                           ('executable_min_return',(5,20)),('better_entry',(5,20)))
    for horizon in horizons for currency in ('local','huf')
])
def test_fold_imputer_rejects_every_canonical_target_in_both_schema_paths(column_kind,target_name):
    with pytest.raises(ValueError,match='target data is forbidden'):
        FoldImputer(**{column_kind:(target_name,)})


def test_all_canonical_target_names_covered_and_trailing_returns_still_impute():
    import csv
    from pathlib import Path
    names={f'{prefix}_{horizon}d_{currency}'
        for prefix,horizons in (('return',(5,20,60)),('direction',(5,20,60)),
                               ('executable_min_return',(5,20)),('better_entry',(5,20)))
        for horizon in horizons for currency in ('local','huf')}
    dictionary=Path(__file__).resolve().parents[2]/'reports'/'target-dictionary.csv'
    with dictionary.open() as stream:
        assert names=={row['name'] for row in csv.DictReader(stream)}
    columns=tuple(f'return_{h}d_raw' for h in (5,20,60,120,252))
    train=_partition({name:[1.,3.,None] for name in columns},role=PartitionRole.TRAIN,start_day=1,end_day=3)
    imputer=FoldImputer(numeric_columns=columns).fit(train)
    result=imputer.transform(train)
    assert result.iloc[2].tolist()==[2.,2.,2.,2.,2.]
