"""Historical universe selection uses only facts knowable at the cutoff."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import exchange_calendars
import pytest

from quant_dca.types import QualityTier, Region, Security, UniverseMembership
from quant_dca.universe.membership import (
    EligibilityThresholds,
    FundamentalReport,
    LiquidityMetric,
    TradingSession,
    UniverseIndex,
)


UTC = timezone.utc
CUTOFF = datetime(2022, 1, 10, 23, tzinfo=UTC)
META = dict(
    available_at=datetime(2020, 1, 2, tzinfo=UTC),
    quality=QualityTier.A,
    source="historical-fixture",
    revision_id="v1",
)


def security(**changes: object) -> Security:
    values = dict(
        security_id="OLD",
        ticker="OLD",
        name="Old Company",
        currency="USD",
        region=Region.US,
        exchange="XNYS",
        active_from="2020-01-02",
        active_to="2022-02-01",
        security_type="common_equity",
        primary_listing=True,
        **META,
    )
    return Security(**(values | changes))


def membership(**changes: object) -> UniverseMembership:
    values = dict(
        universe_id="RESEARCH_US",
        security_id="OLD",
        active_from="2020-01-02",
        active_to="2022-02-01",
        region=Region.US,
        exchange="XNYS",
        currency="USD",
        **META,
    )
    return UniverseMembership(**(values | changes))


def session(day: str, **changes: object) -> TradingSession:
    values = dict(
        security_id="OLD",
        exchange="XNYS",
        session_date=day,
        available_at=datetime.fromisoformat(day).replace(tzinfo=UTC) + timedelta(days=1),
    )
    return TradingSession(**(values | changes))


def liquidity(**changes: object) -> LiquidityMetric:
    values = dict(
        security_id="OLD",
        measured_at=datetime(2022, 1, 7, 22, tzinfo=UTC),
        available_at=datetime(2022, 1, 8, tzinfo=UTC),
        value=1_000_000.0,
    )
    return LiquidityMetric(**(values | changes))


def report(**changes: object) -> FundamentalReport:
    values = dict(
        security_id="OLD",
        published_at=datetime(2021, 11, 1, 12, tzinfo=UTC),
        available_at=datetime(2021, 11, 1, 13, tzinfo=UTC),
    )
    return FundamentalReport(**(values | changes))


SESSION_LABELS = exchange_calendars.get_calendar("XNYS").sessions_in_range(
    "2021-01-01", "2021-12-31"
)[:120]
FULL_HISTORY = [session(label.date().isoformat()) for label in SESSION_LABELS]


def index(
    *,
    securities=None,
    memberships=None,
    sessions=None,
    liquidity_metrics=None,
    fundamental_reports=None,
    thresholds=None,
) -> UniverseIndex:
    return UniverseIndex.from_rows(
        memberships if memberships is not None else [membership()],
        securities=securities if securities is not None else [security()],
        trading_sessions=sessions if sessions is not None else FULL_HISTORY,
        liquidity_metrics=liquidity_metrics if liquidity_metrics is not None else [liquidity()],
        fundamental_reports=fundamental_reports if fundamental_reports is not None else [report()],
        thresholds=thresholds if thresholds is not None else EligibilityThresholds(
            min_trading_sessions=120,
            min_liquidity=1_000_000.0,
            require_fundamental_report=True,
        ),
    )


def test_delisted_security_remains_eligible_before_delisting_only():
    idx = index()
    assert idx.is_eligible("OLD", CUTOFF)
    assert not idx.is_eligible("OLD", datetime(2022, 2, 1, tzinfo=UTC))


def test_intervals_are_start_inclusive_and_end_exclusive():
    idx = index(
        memberships=[membership(active_from="2022-01-10")],
    )
    assert idx.is_eligible("OLD", CUTOFF)
    assert not idx.is_eligible("OLD", datetime(2022, 2, 1, tzinfo=UTC))


def test_eligible_universe_returns_matching_region_security_records():
    eu_security = security(
        security_id="EU1", ticker="EU1", name="Europe One", currency="EUR",
        region=Region.EU, exchange="XETR", active_to=None,
    )
    eu_membership = membership(
        universe_id="RESEARCH_EU", security_id="EU1", currency="EUR",
        region=Region.EU, exchange="XETR", active_to=None,
    )
    idx = index(securities=[security(), eu_security], memberships=[membership(), eu_membership])
    assert idx.eligible_universe(CUTOFF, Region.US) == [security()]
    assert idx.eligible_universe(CUTOFF, Region.EU) == []


@pytest.mark.parametrize(
    "changed",
    [
        {"security_type": "preferred_equity"},
        {"primary_listing": False},
        {"region": Region.GLOBAL},
    ],
    ids=["not-common-equity", "secondary-listing", "unsupported-region"],
)
def test_only_primary_us_or_eu_common_equity_is_eligible(changed):
    assert not index(securities=[security(**changed)]).is_eligible("OLD", CUTOFF)


def test_history_counts_distinct_known_actual_exchange_sessions():
    rows = FULL_HISTORY[:119] + [
        FULL_HISTORY[0],
        session("2022-01-08"),  # Saturday must not count.
        session("2022-01-07", available_at=CUTOFF + timedelta(seconds=1)),
    ]
    assert not index(sessions=rows).is_eligible("OLD", CUTOFF)
    assert index(sessions=rows + [FULL_HISTORY[119]]).is_eligible("OLD", CUTOFF)


def test_configured_120_session_history_threshold_is_enforced():
    cutoff = datetime(2021, 12, 31, 23, tzinfo=UTC)
    threshold = EligibilityThresholds(120, 1_000_000.0, True)
    historical_liquidity = liquidity(
        measured_at=datetime(2021, 6, 1, tzinfo=UTC),
        available_at=datetime(2021, 6, 2, tzinfo=UTC),
    )
    assert not index(sessions=FULL_HISTORY[:119], liquidity_metrics=[historical_liquidity],
                     thresholds=threshold).is_eligible("OLD", cutoff)
    assert index(sessions=FULL_HISTORY, liquidity_metrics=[historical_liquidity],
                 thresholds=threshold).is_eligible("OLD", cutoff)


def test_configuration_cannot_weaken_frozen_120_session_minimum():
    with pytest.raises(ValueError, match="at least 120"):
        EligibilityThresholds(119, 1_000_000.0, True)


def test_established_listing_history_predating_current_membership_counts():
    recent_membership = membership(active_from="2022-01-03")
    assert index(memberships=[recent_membership]).is_eligible("OLD", CUTOFF)


def test_current_session_counts_only_at_its_actual_close():
    current = session(
        "2022-01-10",
        available_at=datetime(2022, 1, 10, 20, tzinfo=UTC),
    )
    idx = index(sessions=FULL_HISTORY[:119] + [current])
    assert not idx.is_eligible("OLD", datetime(2022, 1, 10, 20, 59, 59, tzinfo=UTC))
    assert idx.is_eligible("OLD", datetime(2022, 1, 10, 21, tzinfo=UTC))


def test_unknown_exchange_calendar_is_ineligible_instead_of_raising():
    unknown_sessions = [replace(row, exchange="XXXX") for row in FULL_HISTORY]
    idx = index(
        securities=[security(exchange="XXXX")],
        memberships=[membership(exchange="XXXX")],
        sessions=unknown_sessions,
    )
    assert not idx.is_eligible("OLD", CUTOFF)


def test_session_outside_calendar_coverage_is_ineligible_instead_of_raising():
    idx = index(
        securities=[security(active_from="2008-01-01")],
        memberships=[membership(active_from="2008-01-01")],
        sessions=[session("2008-12-31")] * 120,
    )
    assert not idx.is_eligible("OLD", CUTOFF)


def test_liquidity_uses_latest_measurement_that_was_known_at_cutoff():
    rows = [
        liquidity(value=900_000.0),
        liquidity(value=2_000_000.0, measured_at=CUTOFF + timedelta(days=1),
                  available_at=CUTOFF + timedelta(days=1)),
    ]
    assert not index(liquidity_metrics=rows).is_eligible("OLD", CUTOFF)
    assert index(liquidity_metrics=[replace(rows[0], value=1_000_000.0)]).is_eligible("OLD", CUTOFF)


def test_fundamental_report_must_be_published_and_known_when_required():
    future = report(published_at=CUTOFF + timedelta(days=1), available_at=CUTOFF + timedelta(days=1, hours=1))
    assert not index(fundamental_reports=[future]).is_eligible("OLD", CUTOFF)
    assert index(
        fundamental_reports=[],
        thresholds=EligibilityThresholds(120, 1_000_000.0, False),
    ).is_eligible("OLD", CUTOFF)


@pytest.mark.parametrize(
    "missing",
    ["securities", "memberships", "sessions", "liquidity_metrics", "fundamental_reports"],
)
def test_missing_required_evidence_fails_closed(missing):
    changes = {missing: []}
    assert not index(**changes).is_eligible("OLD", CUTOFF)


def test_future_security_and_membership_versions_are_not_backcast():
    future = CUTOFF + timedelta(days=1)
    assert not index(securities=[security(available_at=future)]).is_eligible("OLD", CUTOFF)
    assert not index(memberships=[membership(available_at=future)]).is_eligible("OLD", CUTOFF)


def test_mismatched_membership_metadata_fails_closed():
    assert not index(memberships=[membership(exchange="XNAS")]).is_eligible("OLD", CUTOFF)
    assert not index(memberships=[membership(currency="EUR")]).is_eligible("OLD", CUTOFF)


def test_queries_reject_naive_times_and_unconfigured_regions():
    idx = index()
    with pytest.raises(ValueError, match="timezone-aware"):
        idx.is_eligible("OLD", CUTOFF.replace(tzinfo=None))
    with pytest.raises(ValueError, match="US or EU"):
        idx.eligible_universe(CUTOFF, Region.GLOBAL)
