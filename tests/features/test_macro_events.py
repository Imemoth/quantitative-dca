from dataclasses import replace
from datetime import datetime, timezone

import pytest

from quant_dca.features.events import (
    ScheduledEvent,
    build_event_features,
    days_until_known_event,
)
from quant_dca.features.macro import MacroSeriesMap, build_macro_features
from quant_dca.features.registry import FeatureRegistry
from quant_dca.types import Observation, QualityTier, Region, Security


UTC = timezone.utc


def ts(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed


def security(**changes: object) -> Security:
    values = dict(
        security_id="S", ticker="S", name="Security", currency="USD",
        region=Region.US, exchange="XNYS", active_from="2010-01-01",
        monetary_jurisdiction="FED", currency_area="USD",
        available_at=ts("2010-01-01T00:00:00"), quality=QualityTier.B,
        source="fixture", revision_id="security-v1",
    )
    values.update(changes)
    return Security(**values)


def observation(series: str, day: str, value: float | None, available: str,
                **changes: object) -> Observation:
    values = dict(
        series=series, entity_id=None, observation_date=day, value=value,
        available_at=ts(available), quality=QualityTier.B, source="fixture",
        revision_id=f"{series}-{day}-{available}", vintage_start=available[:10],
    )
    values.update(changes)
    return Observation(**values)


SERIES = MacroSeriesMap(
    regional={
        Region.US: {
            "headline_inflation": "US_HEADLINE",
            "core_inflation": "US_CORE",
            "unemployment_rate": "US_UNEMP",
            "high_yield_spread": "US_HY",
            "investment_grade_spread": "US_IG",
            "financial_conditions": "US_FCI",
        },
        Region.EU: {
            "headline_inflation": "EU_HEADLINE",
            "core_inflation": "EU_CORE",
            "unemployment_rate": "EU_UNEMP",
            "high_yield_spread": "EU_HY",
            "investment_grade_spread": "EU_IG",
            "financial_conditions": "EU_FCI",
        },
    },
    policy_rate={"FED": "FED_RATE", "ECB": "ECB_RATE", "MNB": "MNB_RATE"},
    central_bank_liquidity={"FED": "FED_LIQ", "ECB": "ECB_LIQ", "MNB": "MNB_LIQ"},
    us_rates={"long_10y": "US10Y", "short_2y": "US2Y", "short_3m": "US3M"},
    eu_rates={"sovereign_long": "EU_LONG", "relevant_short": "EU_SHORT"},
    global_risk_off="GLOBAL_RISK",
)


def feature_values(snapshot) -> dict[str, float | None]:
    return {row.feature: row.value for row in snapshot.features}


def test_unannounced_future_earnings_date_is_missing():
    assert days_until_known_event(
        prediction_date="2020-01-10",
        event_date="2020-02-01",
        announced_at="2020-01-20",
    ) is None


def test_date_only_helper_does_not_claim_same_day_announcement_was_available():
    assert days_until_known_event("2020-01-10", "2020-02-01", "2020-01-10") is None
    assert days_until_known_event("2020-01-10", "2020-02-01", "2020-01-09") == 22


def test_macro_builder_selects_latest_known_vintage_then_latest_observation_period():
    rows = [
        observation("US_HEADLINE", "2020-03-01", 2.0, "2020-03-10T13:00:00"),
        observation("US_HEADLINE", "2020-03-01", 2.1, "2020-04-10T13:00:00"),
        observation("US_HEADLINE", "2020-03-01", 99.0, "2020-04-16T13:00:00"),
        observation("US_HEADLINE", "2020-02-01", 88.0, "2020-04-14T13:00:00"),
        observation("US_CORE", "2020-03-01", 1.8, "2020-04-10T13:00:00"),
        observation("US_UNEMP", "2020-03-01", 4.0, "2020-04-03T13:00:00"),
        observation("FED_RATE", "2020-04-01", 1.0, "2020-04-01T13:00:00"),
        observation("FED_RATE", "2020-01-01", 1.5, "2020-01-02T13:00:00"),
        observation("US10Y", "2020-04-15", 1.2, "2020-04-15T18:00:00"),
        observation("US2Y", "2020-04-15", 0.5, "2020-04-15T18:00:00"),
        observation("US3M", "2020-04-15", 0.2, "2020-04-15T18:00:00"),
        observation("US_HY", "2020-04-14", 7.0, "2020-04-15T12:00:00"),
        observation("US_IG", "2020-04-14", 2.0, "2020-04-15T12:00:00"),
        observation("US_FCI", "2020-04-14", -0.4, "2020-04-15T12:00:00"),
        observation("FED_LIQ", "2020-04-01", 110.0, "2020-04-02T13:00:00"),
        observation("FED_LIQ", "2020-01-01", 100.0, "2020-01-02T13:00:00"),
        observation("GLOBAL_RISK", "2020-04-15", 30.0, "2020-04-15T18:00:00"),
    ]
    result = build_macro_features(
        security=security(), as_of=ts("2020-04-15T22:00:00"),
        observations=rows, series_map=SERIES,
    )
    values = feature_values(result)
    assert set(values) == {
        row.name for row in FeatureRegistry.v1() if row.domain == "macro"
    }
    assert len(values) == 13
    assert values["headline_inflation_level_raw"] == pytest.approx(2.1)
    assert values["policy_rate_change_3m_raw"] == pytest.approx(-0.5)
    assert values["us_yield_curve_10y_2y_raw"] == pytest.approx(0.7)
    assert values["us_yield_curve_10y_3m_raw"] == pytest.approx(1.0)
    assert values["eu_sovereign_curve_proxy_raw"] is None
    assert values["central_bank_liquidity_change_3m_raw"] == pytest.approx(0.1)
    assert result.selected["headline_inflation"].value == pytest.approx(2.1)
    assert all(row.as_of == ts("2020-04-15T22:00:00") for row in result.features)
    assert all(row.max_input_available_at <= ts("2020-04-15T20:00:00") for row in result.features)


def test_non_euro_eu_security_uses_its_local_policy_and_never_falls_back_to_ecb():
    hungarian = security(
        currency="HUF", region=Region.EU, exchange="XETR",
        monetary_jurisdiction="MNB", currency_area="HUF",
    )
    rows = [
        observation("ECB_RATE", "2020-04-01", -0.5, "2020-04-01T12:00:00"),
        observation("MNB_RATE", "2020-04-01", 0.9, "2020-04-01T12:00:00"),
        observation("MNB_RATE", "2020-01-01", 0.9, "2020-01-02T12:00:00"),
    ]
    selected = build_macro_features(
        security=hungarian, as_of=ts("2020-04-15T18:00:00"),
        observations=rows, series_map=SERIES,
    )
    assert feature_values(selected)["policy_rate_level_raw"] == pytest.approx(0.9)

    absent_local = build_macro_features(
        security=hungarian, as_of=ts("2020-04-15T18:00:00"),
        observations=[rows[0]], series_map=SERIES,
    )
    assert feature_values(absent_local)["policy_rate_level_raw"] is None


def test_macro_builder_rejects_direct_future_classification_input():
    with pytest.raises(ValueError, match="PIT_LEAKAGE"):
        build_macro_features(
            security=replace(security(), available_at=ts("2020-04-16T00:00:00")),
            as_of=ts("2020-04-15T22:00:00"), observations=[], series_map=SERIES,
        )


def event(event_id: str, event_type: str, event_date: str, event_at: str,
          available_at: str, **changes: object) -> ScheduledEvent:
    values = dict(
        event_id=event_id, event_type=event_type, event_date=event_date,
        event_at=ts(event_at), announced_at=ts(available_at),
        available_at=ts(available_at), status="scheduled", quality=QualityTier.B,
        source="fixture", revision_id=f"{event_id}-{available_at}",
    )
    values.update(changes)
    return ScheduledEvent(**values)


def test_event_builder_uses_announced_events_and_actual_exchange_sessions():
    rows = [
        event("earn", "earnings", "2020-01-21", "2020-01-21T22:00:00", "2020-01-10T15:00:00", security_id="S"),
        event("policy", "policy_decision", "2020-01-22", "2020-01-22T19:00:00", "2020-01-09T15:00:00", monetary_jurisdiction="FED"),
        event("cpi", "inflation_release", "2020-01-23", "2020-01-23T13:30:00", "2020-01-08T15:00:00", region=Region.US),
        event("future", "earnings", "2020-01-20", "2020-01-20T22:00:00", "2020-01-18T15:00:00", security_id="S"),
    ]
    result = build_event_features(
        security=security(), as_of=ts("2020-01-17T22:00:00"), events=rows,
    )
    values = feature_values(result)
    assert set(values) == {
        row.name for row in FeatureRegistry.v1() if row.domain == "event_calendar"
    }
    assert len(values) == 6
    assert values["days_to_announced_earnings_raw"] == 1.0  # MLK holiday does not count.
    assert values["announced_earnings_within_5d"] == 1.0
    assert values["announced_earnings_within_20d"] == 1.0
    assert values["days_to_relevant_policy_decision_raw"] == 2.0
    assert values["major_policy_event_within_5d"] == 1.0
    assert values["days_to_relevant_inflation_release_raw"] == 3.0
    assert all(row.as_of == ts("2020-01-17T22:00:00") for row in result.features)
    assert result.dependencies["earnings"] == (rows[0],)


def test_event_builder_applies_known_cancellations_but_ignores_future_revisions():
    original = event(
        "earn", "earnings", "2020-01-13", "2020-01-13T22:00:00",
        "2020-01-02T15:00:00", security_id="S", quality=QualityTier.A,
        published_at=ts("2020-01-02T15:00:00"),
    )
    cancelled = replace(
        original, status="cancelled", quality=QualityTier.B,
        available_at=ts("2020-01-09T15:00:00"),
        revised_at=ts("2020-01-09T15:00:00"), revision_id="earn-cancelled",
    )
    later = event(
        "earn-2", "earnings", "2020-01-14", "2020-01-14T22:00:00",
        "2020-01-03T15:00:00", security_id="S", quality=QualityTier.A,
    )
    known_cancel = build_event_features(
        security=security(quality=QualityTier.A), as_of=ts("2020-01-10T22:00:00"),
        events=[original, cancelled, later],
    )
    assert feature_values(known_cancel)["days_to_announced_earnings_raw"] == 2.0
    earnings = next(
        row for row in known_cancel.features
        if row.feature == "days_to_announced_earnings_raw"
    )
    assert earnings.max_input_available_at == ts("2020-01-09T15:00:00")
    assert earnings.quality is QualityTier.B
    assert known_cancel.dependencies["earnings"] == (cancelled, later)

    future_cancel = replace(
        cancelled, available_at=ts("2020-01-11T15:00:00"),
        revised_at=ts("2020-01-11T15:00:00"), revision_id="earn-future-cancel",
    )
    still_known = build_event_features(
        security=security(quality=QualityTier.A), as_of=ts("2020-01-10T22:00:00"),
        events=[original, future_cancel, later],
    )
    future_safe = next(
        row for row in still_known.features
        if row.feature == "days_to_announced_earnings_raw"
    )
    assert future_safe.value == 1.0
    assert future_safe.max_input_available_at == ts("2020-01-03T15:00:00")
    assert future_safe.quality is QualityTier.A


def test_only_cancelled_event_preserves_cancellation_as_missing_value_dependency():
    original = event(
        "earn", "earnings", "2020-01-13", "2020-01-13T22:00:00",
        "2020-01-02T15:00:00", security_id="S", quality=QualityTier.A,
        published_at=ts("2020-01-02T15:00:00"),
    )
    cancelled = replace(
        original, status="cancelled", quality=QualityTier.B,
        available_at=ts("2020-01-09T15:00:00"),
        revised_at=ts("2020-01-09T15:00:00"), revision_id="earn-cancelled",
    )
    result = build_event_features(
        security=security(quality=QualityTier.A),
        as_of=ts("2020-01-10T22:00:00"), events=[original, cancelled],
    )
    earnings = next(
        row for row in result.features
        if row.feature == "days_to_announced_earnings_raw"
    )
    assert earnings.value is None
    assert earnings.max_input_available_at == ts("2020-01-09T15:00:00")
    assert earnings.quality is QualityTier.B
    assert result.dependencies["earnings"] == (cancelled,)


def test_known_relevance_change_remains_a_dependency_when_event_becomes_missing():
    original = event(
        "policy", "policy_decision", "2020-01-13", "2020-01-13T19:00:00",
        "2020-01-02T15:00:00", monetary_jurisdiction="FED",
        quality=QualityTier.A, published_at=ts("2020-01-02T15:00:00"),
    )
    changed = replace(
        original, monetary_jurisdiction="ECB", quality=QualityTier.B,
        available_at=ts("2020-01-09T16:00:00"),
        revised_at=ts("2020-01-09T16:00:00"), revision_id="policy-now-ecb",
    )
    result = build_event_features(
        security=security(quality=QualityTier.A),
        as_of=ts("2020-01-10T22:00:00"), events=[original, changed],
    )
    policy = next(
        row for row in result.features
        if row.feature == "days_to_relevant_policy_decision_raw"
    )
    assert policy.value is None
    assert policy.max_input_available_at == ts("2020-01-09T16:00:00")
    assert policy.quality is QualityTier.B
    assert result.dependencies["policy_decision"] == (changed,)


def test_event_distance_and_threshold_use_exchange_local_day_across_utc_midnight():
    common = dict(
        event_id="earn", event_type="earnings",
        announced_at=ts("2020-01-02T15:00:00"),
        available_at=ts("2020-01-02T15:00:00"), status="scheduled",
        quality=QualityTier.B, source="fixture", revision_id="earn-v1",
        security_id="S",
    )
    utc_event = ScheduledEvent(
        event_date="2020-01-22", event_at=ts("2020-01-22T00:30:00+00:00"),
        **common,
    )
    local_event = ScheduledEvent(
        event_date="2020-01-21", event_at=ts("2020-01-21T19:30:00-05:00"),
        **common,
    )
    snapshots = [
        build_event_features(
            security=security(), as_of=ts("2020-01-13T22:00:00"), events=[row],
        )
        for row in (utc_event, local_event)
    ]
    values = [feature_values(snapshot) for snapshot in snapshots]
    assert [item["days_to_announced_earnings_raw"] for item in values] == [5.0, 5.0]
    assert [item["announced_earnings_within_5d"] for item in values] == [1.0, 1.0]


def test_event_builder_applies_security_classification_on_half_open_interval():
    relevant = event(
        "policy", "policy_decision", "2020-01-13", "2020-01-13T19:00:00",
        "2020-01-02T15:00:00", monetary_jurisdiction="FED",
    )
    at_start = build_event_features(
        security=security(active_from="2020-01-10"),
        as_of=ts("2020-01-10T22:00:00"), events=[relevant],
    )
    assert feature_values(at_start)["days_to_relevant_policy_decision_raw"] == 1.0
    with pytest.raises(ValueError, match="INACTIVE_SECURITY_CLASSIFICATION"):
        build_event_features(
            security=security(active_to="2020-01-10"),
            as_of=ts("2020-01-10T22:00:00"), events=[relevant],
        )
    with pytest.raises(ValueError, match="INACTIVE_SECURITY_CLASSIFICATION"):
        build_event_features(
            security=security(active_from="2020-01-11"),
            as_of=ts("2020-01-10T22:00:00"), events=[relevant],
        )


def test_same_day_event_must_still_be_in_the_future_at_the_eod_boundary():
    result = build_event_features(
        security=security(), as_of=ts("2020-01-10T22:00:00"),
        events=[
            event("past", "earnings", "2020-01-10", "2020-01-10T13:00:00", "2020-01-02T15:00:00", security_id="S"),
            event("after", "earnings", "2020-01-10", "2020-01-10T22:00:00", "2020-01-02T15:00:00", security_id="S"),
        ],
    )
    assert feature_values(result)["days_to_announced_earnings_raw"] == 0.0


def test_event_builder_rejects_direct_future_security_and_selected_low_quality_event():
    with pytest.raises(ValueError, match="PIT_LEAKAGE"):
        build_event_features(
            security=replace(security(), available_at=ts("2020-01-11T00:00:00")),
            as_of=ts("2020-01-10T22:00:00"), events=[],
        )
    with pytest.raises(ValueError, match="QUALITY_BELOW_FLOOR"):
        build_event_features(
            security=security(), as_of=ts("2020-01-10T22:00:00"),
            events=[event("earn", "earnings", "2020-01-13", "2020-01-13T22:00:00", "2020-01-02T15:00:00", security_id="S", quality=QualityTier.C)],
        )


def test_macro_snapshot_retains_prior_vintages_and_mapping_for_immutable_lineage():
    past=observation('FED_RATE','2020-01-01',1.5,'2020-01-02T13:00:00')
    current=observation('FED_RATE','2020-04-01',1.,'2020-04-01T13:00:00')
    result=build_macro_features(security=security(),as_of=ts('2020-04-15T22:00:00'),observations=(past,current),series_map=SERIES)
    assert feature_values(result)['policy_rate_change_3m_raw']==-.5
    assert hasattr(result,'dependencies'), 'prior observation is lost from snapshot lineage'
    assert past in result.dependencies['policy_rate_change_3m_raw']
    assert current in result.dependencies['policy_rate_change_3m_raw']
    assert result.series_map==SERIES
