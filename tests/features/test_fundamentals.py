from dataclasses import replace
from datetime import datetime, timedelta, timezone

import exchange_calendars
import pytest

from quant_dca.features.fundamentals import (
    ConsensusEstimate,
    ReportedFundamentals,
    build_fundamental_features,
    fundamental_features,
)
from quant_dca.features.relative import SectorClassification
from quant_dca.features.valuation import ValuationPrice, build_valuation_features
from quant_dca.types import QualityTier, Region, Security, UniverseMembership
from quant_dca.universe.membership import (
    EligibilityThresholds,
    FundamentalReport,
    LiquidityMetric,
    TradingSession,
    UniverseIndex,
)


UTC = timezone.utc
AS_OF = datetime(2022, 1, 10, 23, tzinfo=UTC)
REPORT_AVAILABLE = datetime(2021, 11, 1, 13, tzinfo=UTC)
FUNDAMENTAL_NAMES = {
    "revenue_growth_yoy_raw", "eps_growth_yoy_raw", "fcf_growth_yoy_raw",
    "gross_margin_raw", "operating_margin_raw", "fcf_margin_raw", "roic_raw",
    "roe_raw", "net_debt_to_ebitda_raw", "interest_coverage_raw",
    "share_dilution_yoy_raw", "last_known_earnings_surprise_raw",
}
VALUATION_NAMES = {
    "trailing_pe_raw", "trailing_pe_sector_percentile",
    "trailing_pe_own_history_zscore", "ev_to_ebitda_raw",
    "ev_to_ebitda_sector_percentile", "ev_to_ebitda_own_history_zscore",
    "price_to_sales_raw", "fcf_yield_raw", "fcf_yield_sector_percentile",
    "fcf_yield_own_history_zscore",
}


def _values(**changes):
    values = dict(
        revenue=200.0, prior_year_revenue=100.0,
        diluted_eps=-1.0, prior_year_diluted_eps=-2.0,
        free_cash_flow=20.0, prior_year_free_cash_flow=10.0,
        gross_profit=80.0, operating_income=40.0, prior_year_operating_income=30.0,
        nopat=30.0, invested_capital=150.0, net_income=24.0,
        average_equity=120.0, net_debt=50.0, ebitda=25.0, ebit=30.0,
        interest_expense=5.0, diluted_shares=10.0, prior_year_diluted_shares=8.0,
    )
    return values | changes


def _report(security_id="A", **changes):
    values = dict(
        security_id=security_id, period_end="2021-09-30",
        published_at=datetime(2021, 11, 1, 12, tzinfo=UTC),
        available_at=REPORT_AVAILABLE, revised_at=None,
        currency="USD", per_share_basis="split_adjusted_v1", sector_id="TECH",
        valuation_period_basis="trailing_twelve_months",
        values=_values(), quality=QualityTier.A, source="reported-fixture",
        revision_id="report-v1", region=Region.US, exchange="XNYS",
    )
    return ReportedFundamentals(**(values | changes))


def _consensus(**changes):
    values = dict(
        security_id="A", period_end="2021-09-30", value=-1.5,
        available_at=datetime(2021, 11, 1, 11, tzinfo=UTC), currency="USD",
        per_share_basis="split_adjusted_v1", quality=QualityTier.A,
        source="pit-consensus-fixture", revision_id="estimate-v1",
    )
    return ConsensusEstimate(**(values | changes))


def test_pure_fundamental_helper_covers_registry_and_structural_masks():
    output = fundamental_features(_values() | {"sector": "Financials"})

    assert set(output) == FUNDAMENTAL_NAMES | {"net_debt_to_ebitda"} | {
        f"{name.removesuffix('_raw')}_applicable" for name in FUNDAMENTAL_NAMES
    }
    assert output["eps_growth_yoy_raw"] == pytest.approx(0.5)
    assert output["net_debt_to_ebitda_raw"] is None
    assert output["net_debt_to_ebitda"] is None
    assert output["net_debt_to_ebitda_applicable"] is False
    assert output["fcf_margin_raw"] is None
    assert output["fcf_margin_applicable"] is False
    assert output["roe_raw"] == pytest.approx(0.2)


def test_zero_denominators_and_missing_consensus_remain_missing():
    output = fundamental_features(_values(
        prior_year_revenue=0.0, prior_year_diluted_eps=0.0,
        invested_capital=0.0, average_equity=0.0, interest_expense=0.0,
        prior_year_diluted_shares=0.0,
    ) | {"sector": "Technology"})

    for name in (
        "revenue_growth_yoy_raw", "eps_growth_yoy_raw", "roic_raw", "roe_raw",
        "interest_coverage_raw", "share_dilution_yoy_raw",
        "last_known_earnings_surprise_raw",
    ):
        assert output[name] is None


def test_evidenced_fundamentals_select_revisions_before_latest_period_and_no_backward_fill():
    older_original = _report(
        period_end="2021-06-30", values=_values(revenue=100.0),
        published_at=datetime(2021, 8, 1, 12, tzinfo=UTC),
        available_at=datetime(2021, 8, 1, 13, tzinfo=UTC), revision_id="old-v1",
    )
    older_revision = replace(
        older_original, values=_values(revenue=999.0), revision_id="old-v2",
        revised_at=datetime(2021, 12, 1, 12, tzinfo=UTC),
        available_at=datetime(2021, 12, 1, 13, tzinfo=UTC),
    )
    latest = _report()
    future_revision = replace(
        latest, values=_values(revenue=9_999.0), revision_id="future-v2",
        revised_at=AS_OF + timedelta(days=1), available_at=AS_OF + timedelta(days=1),
    )

    snapshot = build_fundamental_features(
        security_id="A", as_of=AS_OF,
        reports=[older_original, older_revision, latest, future_revision],
        consensus_estimates=[_consensus()],
    )
    values = {row.feature: row.value for row in snapshot.features}
    assert set(values) == FUNDAMENTAL_NAMES
    assert snapshot.selected_report is latest
    assert snapshot.selected_consensus == _consensus()
    assert values["revenue_growth_yoy_raw"] == 1.0
    assert values["last_known_earnings_surprise_raw"] == pytest.approx(0.5)
    assert all(row.max_input_available_at <= row.available_at <= AS_OF for row in snapshot.features)

    before_publication = datetime(2021, 10, 29, 23, tzinfo=UTC)
    with pytest.raises(LookupError, match="NO_PUBLISHED_FUNDAMENTAL_REPORT"):
        build_fundamental_features(
            security_id="A", as_of=before_publication, reports=[latest],
            consensus_estimates=[_consensus()],
        )


def test_consensus_must_be_real_pit_evidence_known_before_report():
    late = _consensus(available_at=datetime(2021, 11, 1, 12, 30, tzinfo=UTC))
    snapshot = build_fundamental_features(
        security_id="A", as_of=AS_OF, reports=[_report()],
        consensus_estimates=[late],
    )
    assert {row.feature: row.value for row in snapshot.features}[
        "last_known_earnings_surprise_raw"
    ] is None
    assert snapshot.selected_consensus is None

    future_mutation = replace(
        _consensus(), value=999.0, available_at=AS_OF + timedelta(days=1),
        revised_at=AS_OF + timedelta(days=1), revision_id="future-estimate",
    )
    baseline = build_fundamental_features(
        security_id="A", as_of=AS_OF, reports=[_report()],
        consensus_estimates=[_consensus()],
    )
    assert build_fundamental_features(
        security_id="A", as_of=AS_OF, reports=[_report()],
        consensus_estimates=[_consensus(), future_mutation],
    ) == baseline


def test_registry_tier_b_floor_does_not_admit_tier_c_report_or_consensus():
    with pytest.raises(ValueError, match="QUALITY_BELOW_FLOOR"):
        build_fundamental_features(
            security_id="A", as_of=AS_OF,
            reports=[_report(quality=QualityTier.C)],
        )
    snapshot = build_fundamental_features(
        security_id="A", as_of=AS_OF, reports=[_report()],
        consensus_estimates=[_consensus(quality=QualityTier.C)],
    )
    assert snapshot.selected_consensus is None
    assert {row.feature: row.value for row in snapshot.features}[
        "last_known_earnings_surprise_raw"
    ] is None


@pytest.mark.parametrize(
    "estimates",
    [
        [],
        [_consensus(available_at=datetime(2021, 11, 1, 12, 30, tzinfo=UTC))],
        [_consensus(quality=QualityTier.C)],
    ],
    ids=["absent", "late", "tier-c"],
)
def test_embedded_consensus_never_bypasses_verified_estimate_boundary(estimates):
    report = _report(values=_values(consensus_eps=999.0))
    snapshot = build_fundamental_features(
        security_id="A", as_of=AS_OF, reports=[report],
        consensus_estimates=estimates,
    )

    assert snapshot.selected_consensus is None
    assert {row.feature: row.value for row in snapshot.features}[
        "last_known_earnings_surprise_raw"
    ] is None


def test_unknown_report_sector_fails_closed_at_evidenced_boundary():
    report = _report(sector_id="")

    with pytest.raises(ValueError, match="UNKNOWN_FUNDAMENTAL_SECTOR"):
        build_fundamental_features(
            security_id="A", as_of=AS_OF, reports=[report],
        )


def test_valuation_requires_declared_trailing_period_normalization():
    with pytest.raises(ValueError, match="VALUATION_PERIOD_BASIS"):
        _report(valuation_period_basis="quarterly")


def _security(security_id, *, exchange="XNYS"):
    return Security(
        security_id=security_id, ticker=security_id, name=security_id,
        currency="USD", region=Region.US, exchange=exchange, active_from="2018-01-02",
        available_at=datetime(2018, 1, 2, tzinfo=UTC), quality=QualityTier.A,
        source="listing-fixture", revision_id="v1",
    )


def _membership(security_id, *, exchange="XNYS"):
    return UniverseMembership(
        universe_id="RESEARCH_US", security_id=security_id, active_from="2018-01-02",
        region=Region.US, exchange=exchange, currency="USD",
        available_at=datetime(2018, 1, 2, tzinfo=UTC), quality=QualityTier.A,
        source="membership-fixture", revision_id="v1",
    )


def _universe(session_dates):
    ids = ("A", "B", "OTHER_SECTOR")
    sessions = [
        TradingSession(
            security_id=security_id, exchange="XNYS", session_date=day,
            available_at=datetime.fromisoformat(day).replace(tzinfo=UTC),
        )
        for security_id in ids for day in session_dates
    ]
    liquidity = [
        LiquidityMetric(
            security_id=security_id, measured_at=datetime(2022, 1, 7, 20, tzinfo=UTC),
            available_at=datetime(2022, 1, 7, 21, tzinfo=UTC), value=1_000_000,
        ) for security_id in ids
    ]
    reports = [
        FundamentalReport(
            security_id=security_id,
            published_at=datetime(2021, 11, 1, 12, tzinfo=UTC),
            available_at=REPORT_AVAILABLE,
        ) for security_id in ids
    ]
    return UniverseIndex.from_rows(
        [_membership(i) for i in ids], securities=[_security(i) for i in ids],
        trading_sessions=sessions, liquidity_metrics=liquidity,
        fundamental_reports=reports,
        thresholds=EligibilityThresholds(120, 1_000_000, True),
    )


def _price(security_id, day, close, *, exchange="XNYS", **changes):
    calendar = exchange_calendars.get_calendar("XNYS" if exchange == "XNAS" else exchange)
    session_close = calendar.session_close(day).to_pydatetime()
    values = dict(
        security_id=security_id, session_date=day, close=close,
        session_close_at=session_close, available_at=session_close,
        currency="USD", per_share_basis="split_adjusted_v1",
        price_basis="split_adjusted_feature", quality=QualityTier.A,
        source="valuation-price-fixture", revision_id=f"{security_id}-{day}",
        region=Region.US, exchange=exchange,
    )
    return ValuationPrice(**(values | changes))


def _classification(security_id, sector="TECH", **changes):
    values = dict(
        security_id=security_id, sector_id=sector, active_from="2018-01-02",
        available_at=datetime(2018, 1, 2, tzinfo=UTC), quality=QualityTier.A,
        source="classification-fixture", revision_id="v1",
    )
    return SectorClassification(**(values | changes))


def test_valuation_builder_covers_registry_uses_explicit_historical_sector():
    days = [d.date().isoformat() for d in exchange_calendars.get_calendar("XNYS").sessions_in_range("2021-01-01", "2022-01-10")]
    reports = [
        _report("A"),
        _report("B", values=_values(diluted_eps=2.0, diluted_shares=10.0), sector_id="TECH"),
        _report("OTHER_SECTOR", values=_values(diluted_eps=5.0), sector_id="HEALTH"),
    ]
    prices = [_price("A", day, 10.0 + index / 100) for index, day in enumerate(days)]
    prices += [_price("B", days[-1], 30.0), _price("OTHER_SECTOR", days[-1], 1.0)]

    snapshot = build_valuation_features(
        security_id="A", region=Region.US, as_of=AS_OF,
        reports=reports, prices=prices, universe_index=_universe(days),
        sector_classifications=[
            _classification("A"), _classification("B"),
            _classification("OTHER_SECTOR", "HEALTH"),
        ],
    )
    values = {row.feature: row.value for row in snapshot.features}
    assert set(values) == VALUATION_NAMES
    assert values["trailing_pe_raw"] is None  # Negative EPS convention.
    assert values["price_to_sales_raw"] == pytest.approx(prices[len(days)-1].close * 10 / 200)
    assert values["ev_to_ebitda_raw"] is not None
    assert values["fcf_yield_sector_percentile"] == 1.0
    assert snapshot.eligible_security_ids == ("A", "B", "OTHER_SECTOR")
    assert {row.security_id for row in snapshot.selected_classifications} == set(snapshot.eligible_security_ids)


def test_sector_percentile_counts_xnas_peer_at_its_own_latest_close():
    days = [
        d.date().isoformat()
        for d in exchange_calendars.get_calendar("XNYS").sessions_in_range(
            "2021-06-01", "2022-01-10"
        )
    ]
    ids = (("A", "XNYS"), ("B", "XNAS"))
    universe = UniverseIndex.from_rows(
        [_membership(security_id, exchange=exchange) for security_id, exchange in ids],
        securities=[_security(security_id, exchange=exchange) for security_id, exchange in ids],
        trading_sessions=[
            TradingSession(
                security_id=security_id, exchange=exchange, session_date=day,
                available_at=datetime.fromisoformat(day).replace(tzinfo=UTC),
            )
            for security_id, exchange in ids for day in days
        ],
        liquidity_metrics=[
            LiquidityMetric(
                security_id=security_id,
                measured_at=datetime(2022, 1, 7, 20, tzinfo=UTC),
                available_at=datetime(2022, 1, 7, 21, tzinfo=UTC),
                value=1_000_000,
            ) for security_id, _ in ids
        ],
        fundamental_reports=[
            FundamentalReport(
                security_id=security_id,
                published_at=datetime(2021, 11, 1, 12, tzinfo=UTC),
                available_at=REPORT_AVAILABLE,
            ) for security_id, _ in ids
        ],
        thresholds=EligibilityThresholds(120, 1_000_000, True),
    )
    peer = _price("B", days[-1], 10.0, exchange="XNAS")
    target = _price(
        "A", days[-1], 20.0,
        available_at=peer.session_close_at - timedelta(minutes=10),
    )
    snapshot = build_valuation_features(
        security_id="A", region=Region.US, as_of=AS_OF,
        reports=[
            _report("A", values=_values(diluted_eps=2.0)),
            _report("B", values=_values(diluted_eps=2.0)),
        ],
        prices=[target, peer], universe_index=universe,
        sector_classifications=[_classification("A"), _classification("B")],
    )
    values = {row.feature: row.value for row in snapshot.features}

    assert values["trailing_pe_sector_percentile"] == 1.0
    assert any(row.security_id == "B" and row.exchange == "XNAS" for row in snapshot.selected_prices)
    assert next(
        row for row in snapshot.features
        if row.feature == "trailing_pe_sector_percentile"
    ).max_input_available_at == peer.available_at


def test_valuation_refuses_total_return_or_mismatched_share_and_currency_bases():
    days = [d.date().isoformat() for d in exchange_calendars.get_calendar("XNYS").sessions_in_range("2021-01-01", "2022-01-10")]
    common = dict(
        security_id="A", region=Region.US, as_of=AS_OF, reports=[_report()],
        universe_index=_universe(days), sector_classifications=[_classification("A"), _classification("B"), _classification("OTHER_SECTOR", "HEALTH")],
    )
    good = _price("A", days[-1], 10.0)
    for bad in (
        replace(good, price_basis="split_and_dividend_total_return_feature"),
        replace(good, per_share_basis="unadjusted"),
        replace(good, currency="EUR"),
    ):
        with pytest.raises(ValueError, match="VALUATION_(PRICE_BASIS|UNIT_BASIS|CURRENCY)_MISMATCH"):
            build_valuation_features(prices=[bad], **common)


def test_financial_valuation_structural_missing_is_never_imputed():
    day = "2022-01-10"
    history_days = [
        d.date().isoformat()
        for d in exchange_calendars.get_calendar("XNYS").sessions_in_range(
            "2021-06-01", day
        )
    ]
    report = _report(sector_id="Financials")
    snapshot = build_valuation_features(
        security_id="A", region=Region.US, as_of=AS_OF, reports=[report],
        prices=[_price("A", day, 10.0)], universe_index=_universe(history_days),
        sector_classifications=[_classification("A", "Financials")],
    )
    values = {row.feature: row.value for row in snapshot.features}
    for name in (
        "ev_to_ebitda_raw", "ev_to_ebitda_sector_percentile",
        "ev_to_ebitda_own_history_zscore", "fcf_yield_raw",
        "fcf_yield_sector_percentile", "fcf_yield_own_history_zscore",
    ):
        assert values[name] is None
        assert snapshot.applicability[name] is False


def test_own_history_requires_756_actual_causal_sessions_and_ignores_future_rows():
    calendar = exchange_calendars.get_calendar("XNYS")
    days = [d.date().isoformat() for d in calendar.sessions_in_range("2018-12-31", "2022-01-10")][-756:]
    prices = [_price("A", day, 10.0 + index / 100) for index, day in enumerate(days)]
    early_report = _report(
        period_end="2018-09-30",
        published_at=datetime(2018, 11, 1, 12, tzinfo=UTC),
        available_at=datetime(2018, 11, 1, 13, tzinfo=UTC),
        values=_values(diluted_eps=2.0),
    )
    common = dict(
        security_id="A", region=Region.US, as_of=AS_OF, reports=[early_report],
        universe_index=_universe(days), sector_classifications=[_classification("A"), _classification("B"), _classification("OTHER_SECTOR", "HEALTH")],
    )
    full = build_valuation_features(prices=prices, **common)
    short = build_valuation_features(prices=prices[1:], **common)
    assert {row.feature: row.value for row in full.features}["trailing_pe_own_history_zscore"] is not None
    assert {row.feature: row.value for row in short.features}["trailing_pe_own_history_zscore"] is None

    future = replace(
        prices[-1], session_date="2022-01-11", close=9_999.0,
        session_close_at=calendar.session_close("2022-01-11").to_pydatetime(),
        available_at=calendar.session_close("2022-01-11").to_pydatetime(),
        revision_id="future",
    )
    assert build_valuation_features(prices=[*prices, future], **common) == full


def test_report_revision_changes_own_history_only_when_it_becomes_known():
    calendar = exchange_calendars.get_calendar("XNYS")
    days = [d.date().isoformat() for d in calendar.sessions_in_range("2018-12-31", "2022-01-10")][-756:]
    prices = [_price("A", day, 10.0) for day in days]
    original = _report(
        period_end="2018-09-30",
        published_at=datetime(2018, 11, 1, 12, tzinfo=UTC),
        available_at=datetime(2018, 11, 1, 13, tzinfo=UTC),
        values=_values(diluted_eps=2.0), revision_id="original",
    )
    final_close = calendar.session_close(days[-1]).to_pydatetime()
    revision = replace(
        original, values=_values(diluted_eps=4.0), revised_at=final_close,
        available_at=final_close, revision_id="known-only-on-final-session",
    )
    snapshot = build_valuation_features(
        security_id="A", region=Region.US, as_of=AS_OF,
        reports=[original, revision], prices=prices, universe_index=_universe(days),
        sector_classifications=[_classification("A"), _classification("B"), _classification("OTHER_SECTOR", "HEALTH")],
    )
    values = {row.feature: row.value for row in snapshot.features}
    assert values["trailing_pe_raw"] == pytest.approx(2.5)
    assert values["trailing_pe_own_history_zscore"] < -20


def test_valuation_tier_b_floor_rejects_tier_c_price_and_classification():
    days = [d.date().isoformat() for d in exchange_calendars.get_calendar("XNYS").sessions_in_range("2021-06-01", "2022-01-10")]
    common = dict(
        security_id="A", region=Region.US, as_of=AS_OF, reports=[_report()],
        universe_index=_universe(days),
    )
    with pytest.raises(ValueError, match="QUALITY_BELOW_FLOOR"):
        build_valuation_features(
            prices=[_price("A", days[-1], 10.0, quality=QualityTier.C)],
            sector_classifications=[_classification("A")], **common,
        )
    with pytest.raises(ValueError, match="QUALITY_BELOW_FLOOR"):
        build_valuation_features(
            prices=[_price("A", days[-1], 10.0)],
            sector_classifications=[_classification("A", quality=QualityTier.C)],
            **common,
        )


def test_sector_percentile_does_not_carry_stale_peer_over_missing_current_session():
    days=[d.date().isoformat() for d in exchange_calendars.get_calendar('XNYS').sessions_in_range('2021-01-01','2022-01-10')]
    stale=_price('B','2021-11-01',10.)
    snapshot=build_valuation_features(security_id='A',region=Region.US,as_of=AS_OF,
        reports=[_report('A',values=_values(diluted_eps=2.)),_report('B',values=_values(diluted_eps=2.))],
        prices=[_price('A','2022-01-10',20.),stale],universe_index=_universe(days),
        sector_classifications=[_classification('A'),_classification('B')])
    values={r.feature:r.value for r in snapshot.features}
    assert values['trailing_pe_raw']==10.
    assert values['trailing_pe_sector_percentile']==.5
    assert not any(r.security_id=='B' for r in snapshot.selected_prices)
    assert snapshot.eligible_security_ids==('A','B','OTHER_SECTOR')


def test_sector_percentile_keeps_peer_prior_close_when_its_exchange_is_closed():
    from quant_dca.calendars.service import eligible_session_close,previous_eligible_eod
    from datetime import date
    # Paris traded Christmas Eve 2021; Frankfurt did not. The Dec23 Frankfurt
    # close is its current eligible close at the Paris Dec24 early-close cutoff.
    cutoff=eligible_session_close('XPAR',date(2021,12,24))
    prior=eligible_session_close('XETR',date(2021,12,23))
    assert cutoff is not None and prior is not None
    assert previous_eligible_eod('XETR',cutoff)==prior
    securities=[replace(_security('A',exchange='XPAR'),region=Region.EU,currency='EUR'),
                replace(_security('B',exchange='XETR'),region=Region.EU,currency='EUR')]
    membership=[replace(_membership(s.security_id,exchange=s.exchange),region=Region.EU,currency='EUR') for s in securities]
    sessions=[]
    for sec in securities:
        days=exchange_calendars.get_calendar(sec.exchange).sessions_in_range('2021-01-04','2021-10-29')[:120]
        sessions.extend(TradingSession(security_id=sec.security_id,exchange=sec.exchange,session_date=d.date().isoformat(),
            available_at=eligible_session_close(sec.exchange,d.date())) for d in days)
    universe=UniverseIndex(securities=securities,memberships=membership,trading_sessions=sessions,
        liquidity_metrics=[LiquidityMetric(security_id=s.security_id,measured_at=prior,available_at=prior,value=1e6) for s in securities],
        fundamental_reports=[FundamentalReport(security_id=s.security_id,published_at=REPORT_AVAILABLE,available_at=REPORT_AVAILABLE) for s in securities],
        thresholds=EligibilityThresholds(120,1e6,True))
    reports=[_report(s.security_id,exchange=s.exchange,region=Region.EU,currency='EUR',values=_values(diluted_eps=2.)) for s in securities]
    prices=[_price('A','2021-12-24',20.,exchange='XPAR',region=Region.EU,currency='EUR'),
            _price('B','2021-12-23',10.,exchange='XETR',region=Region.EU,currency='EUR')]
    snapshot=build_valuation_features(security_id='A',region=Region.EU,as_of=cutoff,reports=reports,prices=prices,
        universe_index=universe,sector_classifications=[_classification('A'),_classification('B')])
    assert {r.feature:r.value for r in snapshot.features}['trailing_pe_sector_percentile']==1.
    assert any(r.security_id=='B' and r.session_close_at==prior for r in snapshot.selected_prices)
