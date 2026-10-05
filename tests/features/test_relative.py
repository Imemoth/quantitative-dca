from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

import exchange_calendars
import pytest

from quant_dca.features.relative import (
    SectorClassification,
    build_relative_features,
    compute_relative_features,
    percentile_in_universe,
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
CUTOFF = datetime(2022, 1, 10, 23, tzinfo=UTC)
EOD = datetime(2022, 1, 10, 21, tzinfo=UTC)
HISTORICAL = datetime(2020, 1, 2, tzinfo=UTC)


def test_percentile_uses_literal_historical_eligible_ranks():
    values = {"A": 0.10, "B": 0.20, "DELISTED_LATER": 0.15, "FUTURE_MEMBER": 0.99}
    eligible = {"A", "B", "DELISTED_LATER"}

    assert percentile_in_universe("A", values, eligible) == 0.0
    assert percentile_in_universe("DELISTED_LATER", values, eligible) == 0.5
    assert percentile_in_universe("B", values, eligible) == 1.0
    assert percentile_in_universe("FUTURE_MEMBER", values, eligible) is None

    mutated = values | {"FUTURE_MEMBER": -999.0, "NEVER_MEMBER": 999.0}
    assert percentile_in_universe("A", mutated, eligible) == 0.0


def test_percentile_tie_singleton_and_missing_conventions_are_deterministic():
    tied = {"LOW": 1.0, "TIE_A": 2.0, "TIE_B": 2.0, "HIGH": 3.0}
    assert percentile_in_universe("TIE_A", tied, set(tied)) == pytest.approx(0.5)
    assert percentile_in_universe("ONLY", {"ONLY": 4.0}, {"ONLY"}) == 0.5
    assert percentile_in_universe("MISSING", {"MISSING": None}, {"MISSING"}) is None
    assert percentile_in_universe("BAD", {"BAD": float("inf")}, {"BAD"}) is None


def test_pure_relative_formulas_cover_all_registry_outputs():
    result = compute_relative_features(
        "A",
        stock_returns={20: 0.20, 60: 0.30, 120: 0.40},
        sector_returns={20: 0.05, 60: 0.10, 120: 0.20},
        market_returns={20: 0.02, 60: 0.04, 120: 0.08},
        return_120d_values={"A": 0.40, "B": 0.60, "DELISTED_LATER": 0.50},
        eligible_sector={"A", "DELISTED_LATER"},
        eligible_universe={"A", "B", "DELISTED_LATER"},
    )

    assert result == {
        "return_relative_sector_20d_raw": pytest.approx(0.15),
        "return_relative_sector_60d_raw": pytest.approx(0.20),
        "return_relative_sector_120d_raw": pytest.approx(0.20),
        "return_relative_market_20d_raw": pytest.approx(0.18),
        "return_relative_market_60d_raw": pytest.approx(0.26),
        "return_relative_market_120d_raw": pytest.approx(0.32),
        "momentum_sector_percentile": 0.0,
        "momentum_universe_percentile": 0.0,
    }


def _security(security_id, *, active_from="2020-01-02", active_to=None, available_at=HISTORICAL):
    return Security(
        security_id=security_id,
        ticker=security_id,
        name=security_id,
        currency="USD",
        region=Region.US,
        exchange="XNYS",
        active_from=active_from,
        active_to=active_to,
        available_at=available_at,
        quality=QualityTier.A,
        source="historical-fixture",
        revision_id="v1",
    )


def _membership(security_id, *, active_from="2020-01-02", active_to=None, available_at=HISTORICAL):
    return UniverseMembership(
        universe_id="RESEARCH_US",
        security_id=security_id,
        active_from=active_from,
        active_to=active_to,
        region=Region.US,
        exchange="XNYS",
        currency="USD",
        available_at=available_at,
        quality=QualityTier.A,
        source="historical-fixture",
        revision_id="v1",
    )


def _universe(
    *,
    target_active_to=None,
    delisted_active_to="2022-02-01",
    future_active_from="2022-02-01",
):
    historical_ids = ("A", "B", "DELISTED_LATER")
    future_id = "FUTURE_MEMBER"
    securities = [
        _security("A", active_to=target_active_to),
        _security("B"),
        _security("DELISTED_LATER", active_to=delisted_active_to),
        _security(future_id, active_from=future_active_from),
    ]
    memberships = [
        _membership("A", active_to=target_active_to),
        _membership("B"),
        _membership("DELISTED_LATER", active_to=delisted_active_to),
        _membership(future_id, active_from=future_active_from),
    ]
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
        for security_id in (*historical_ids, future_id)
        for label in labels
    ]
    liquidity = [
        LiquidityMetric(
            security_id=security_id,
            measured_at=datetime(2022, 1, 7, 20, tzinfo=UTC),
            available_at=datetime(2022, 1, 7, 21, tzinfo=UTC),
            value=1_000_000,
        )
        for security_id in (*historical_ids, future_id)
    ]
    reports = [
        FundamentalReport(
            security_id=security_id,
            published_at=datetime(2021, 11, 1, 12, tzinfo=UTC),
            available_at=datetime(2021, 11, 1, 13, tzinfo=UTC),
        )
        for security_id in (*historical_ids, future_id)
    ]
    return UniverseIndex.from_rows(
        memberships,
        securities=securities,
        trading_sessions=sessions,
        liquidity_metrics=liquidity,
        fundamental_reports=reports,
        thresholds=EligibilityThresholds(120, 1_000_000, True),
    )


def _feature(entity_id, horizon, value, **changes):
    values = dict(
        feature=f"return_{horizon}d_raw",
        entity_id=entity_id,
        observation_date="2022-01-10",
        as_of=CUTOFF,
        value=value,
        max_input_available_at=EOD,
        available_at=EOD,
        quality=QualityTier.A,
        source="verified-price-features",
        revision_id="features-v1",
        region=Region.US,
        exchange="XNYS",
    )
    return FeatureValue(**(values | changes))


def _classification(security_id, sector_id, **changes):
    values = dict(
        security_id=security_id,
        sector_id=sector_id,
        active_from="2020-01-02",
        active_to=None,
        available_at=HISTORICAL,
        quality=QualityTier.A,
        source="classification-fixture",
        revision_id="v1",
    )
    return SectorClassification(**(values | changes))


def _build(**changes):
    target = {n: _feature("A", n, value) for n, value in {20: 0.20, 60: 0.30, 120: 0.40}.items()}
    sector = {n: _feature("TECH", n, value) for n, value in {20: 0.05, 60: 0.10, 120: 0.20}.items()}
    market = {n: _feature("US_MARKET", n, value) for n, value in {20: 0.02, 60: 0.04, 120: 0.08}.items()}
    cross_section = [
        _feature("A", 120, 0.40),
        _feature("B", 120, 0.60),
        _feature("DELISTED_LATER", 120, 0.50, quality=QualityTier.C),
        _feature("FUTURE_MEMBER", 120, 0.99),
    ]
    classifications = [
        _classification("A", "TECH"),
        _classification("B", "FINANCE"),
        _classification("DELISTED_LATER", "TECH", quality=QualityTier.B),
        _classification("FUTURE_MEMBER", "TECH"),
    ]
    arguments = dict(
        security_id="A",
        region=Region.US,
        as_of=CUTOFF,
        universe_index=_universe(),
        stock_returns=target,
        cross_section_returns=cross_section,
        sector_benchmark_returns=sector,
        market_benchmark_returns=market,
        sector_classifications=classifications,
    )
    return build_relative_features(**(arguments | changes))


def test_evidenced_boundary_uses_historical_universe_sector_and_quality():
    snapshot = _build()
    values = {row.feature: row.value for row in snapshot.features}

    assert values["return_relative_sector_20d_raw"] == pytest.approx(0.15)
    assert values["return_relative_market_120d_raw"] == pytest.approx(0.32)
    assert values["momentum_sector_percentile"] == 0.0
    assert values["momentum_universe_percentile"] == 0.0
    assert snapshot.eligible_security_ids == ("A", "B", "DELISTED_LATER")
    assert {row.security_id for row in snapshot.selected_classifications} == {
        "A", "B", "DELISTED_LATER"
    }
    assert all(row.entity_id == "A" for row in snapshot.features)
    assert all(row.quality is QualityTier.C for row in snapshot.features)
    assert all(row.max_input_available_at <= row.available_at <= CUTOFF for row in snapshot.features)


def test_future_membership_classification_and_value_mutations_do_not_backcast():
    baseline = _build()
    future = CUTOFF + timedelta(days=30)
    mutated_cross_section = list(baseline.selected_cross_section) + [
        _feature(
            "B",
            120,
            -999.0,
            available_at=future,
            max_input_available_at=future,
            as_of=future,
            revision_id="future-v2",
        )
    ]
    mutated_classifications = list(baseline.selected_classifications) + [
        _classification(
            "DELISTED_LATER",
            "FINANCE",
            available_at=future,
            revised_at=future,
            revision_id="future-v2",
        )
    ]

    assert _build(
        cross_section_returns=mutated_cross_section,
        sector_classifications=mutated_classifications,
    ) == baseline


def test_selected_feature_with_future_derived_input_clock_is_rejected():
    future_input = EOD + timedelta(minutes=1)
    target = {n: _feature("A", n, value) for n, value in {20: 0.20, 60: 0.30, 120: 0.40}.items()}
    target[20] = replace(target[20], max_input_available_at=future_input)

    with pytest.raises(ValueError, match="PIT_LEAKAGE"):
        _build(stock_returns=target)


def test_unknown_sector_at_cutoff_preserves_sector_outputs_as_missing():
    future = CUTOFF + timedelta(days=1)
    classifications = [
        _classification("A", "TECH", available_at=future),
        _classification("B", "FINANCE"),
        _classification("DELISTED_LATER", "TECH"),
    ]
    values = {row.feature: row.value for row in _build(sector_classifications=classifications).features}

    assert values["return_relative_sector_20d_raw"] is None
    assert values["return_relative_sector_60d_raw"] is None
    assert values["return_relative_sector_120d_raw"] is None
    assert values["momentum_sector_percentile"] is None
    assert values["return_relative_market_20d_raw"] == pytest.approx(0.18)
    assert values["momentum_universe_percentile"] == 0.0


def test_builder_never_uses_prediction_time_membership_as_a_current_fallback():
    prediction = datetime(2022, 1, 10, 20, tzinfo=UTC)  # Before Monday close.
    friday_eod = datetime(2022, 1, 7, 21, tzinfo=UTC)

    def historical_feature(entity_id, horizon, value):
        return _feature(
            entity_id,
            horizon,
            value,
            observation_date="2022-01-07",
            as_of=prediction,
            available_at=friday_eod,
            max_input_available_at=friday_eod,
        )

    snapshot = build_relative_features(
        security_id="A",
        region=Region.US,
        as_of=prediction,
        # End-exclusive interval makes A ineligible on Monday, but it was
        # eligible at the Friday feature cutoff and must remain rankable there.
        universe_index=_universe(target_active_to="2022-01-10"),
        stock_returns={n: historical_feature("A", n, v) for n, v in {20: .2, 60: .3, 120: .4}.items()},
        cross_section_returns=[
            historical_feature("A", 120, .4),
            historical_feature("B", 120, .6),
            historical_feature("DELISTED_LATER", 120, .5),
        ],
        sector_benchmark_returns={n: historical_feature("TECH", n, v) for n, v in {20: .05, 60: .1, 120: .2}.items()},
        market_benchmark_returns={n: historical_feature("US_MARKET", n, v) for n, v in {20: .02, 60: .04, 120: .08}.items()},
        sector_classifications=[
            _classification("A", "TECH"),
            _classification("B", "FINANCE"),
            _classification("DELISTED_LATER", "TECH"),
        ],
    )

    assert snapshot.eligible_security_ids == ("A", "B", "DELISTED_LATER")
    assert {row.feature: row.value for row in snapshot.features}[
        "momentum_sector_percentile"
    ] == 0.0


def test_sector_benchmark_must_match_historical_target_classification():
    wrong_sector = {
        n: _feature("FINANCE", n, value)
        for n, value in {20: 0.05, 60: 0.10, 120: 0.20}.items()
    }

    with pytest.raises(ValueError, match="SECTOR_BENCHMARK_ENTITY_MISMATCH"):
        _build(sector_benchmark_returns=wrong_sector)


def test_stale_after_close_snapshot_uses_observation_eod_membership_and_classification():
    friday_eod = datetime(2022, 1, 7, 21, tzinfo=UTC)

    def stale_feature(entity_id, horizon, value):
        return _feature(
            entity_id,
            horizon,
            value,
            observation_date="2022-01-07",
            available_at=friday_eod,
            max_input_available_at=friday_eod,
        )

    snapshot = build_relative_features(
        security_id="A",
        region=Region.US,
        as_of=CUTOFF,  # Monday after close; supplied returns remain Friday's.
        universe_index=_universe(
            delisted_active_to="2022-01-10",
            future_active_from="2022-01-10",
        ),
        stock_returns={n: stale_feature("A", n, v) for n, v in {20: .2, 60: .3, 120: .4}.items()},
        cross_section_returns=[
            stale_feature("A", 120, .4),
            stale_feature("B", 120, .6),
            stale_feature("DELISTED_LATER", 120, .5),
            stale_feature("FUTURE_MEMBER", 120, .99),
        ],
        sector_benchmark_returns={n: stale_feature("TECH", n, v) for n, v in {20: .05, 60: .1, 120: .2}.items()},
        market_benchmark_returns={n: stale_feature("US_MARKET", n, v) for n, v in {20: .02, 60: .04, 120: .08}.items()},
        sector_classifications=[
            _classification("A", "TECH"),
            _classification("B", "FINANCE"),
            _classification("DELISTED_LATER", "TECH", active_to="2022-01-10"),
            _classification("DELISTED_LATER", "FINANCE", active_from="2022-01-10"),
            _classification("FUTURE_MEMBER", "TECH", active_from="2022-01-10"),
        ],
    )

    assert snapshot.eligible_security_ids == ("A", "B", "DELISTED_LATER")
    assert {
        row.security_id: row.sector_id for row in snapshot.selected_classifications
    } == {"A": "TECH", "B": "FINANCE", "DELISTED_LATER": "TECH"}
    assert {row.feature: row.value for row in snapshot.features}[
        "momentum_sector_percentile"
    ] == 0.0
    assert all(row.available_at == friday_eod for row in snapshot.features)


@pytest.mark.parametrize(
    "mapping_name",
    ["stock_returns", "sector_benchmark_returns", "market_benchmark_returns"],
)
def test_future_available_direct_input_hard_fails(mapping_name):
    future_available = EOD + timedelta(minutes=1)
    if mapping_name == "stock_returns":
        entity_id = "A"
    elif mapping_name == "sector_benchmark_returns":
        entity_id = "TECH"
    else:
        entity_id = "US_MARKET"
    direct = {
        n: _feature(entity_id, n, value)
        for n, value in {20: 0.20, 60: 0.30, 120: 0.40}.items()
    }
    direct[20] = replace(direct[20], available_at=future_available)

    with pytest.raises(ValueError, match="PIT_LEAKAGE:relative_input_after_feature_cutoff"):
        _build(**{mapping_name: direct})


def test_stock_observation_date_must_be_an_exchange_session():
    weekend = {
        n: _feature("A", n, value, observation_date="2022-01-08")
        for n, value in {20: 0.20, 60: 0.30, 120: 0.40}.items()
    }

    with pytest.raises(ValueError, match="INVALID_STOCK_OBSERVATION_SESSION"):
        _build(stock_returns=weekend)
