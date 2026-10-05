from dataclasses import replace
from datetime import date, timedelta
import math
import statistics

import pytest

from quant_dca.calendars.service import eligible_session_close, eligible_session_open
from quant_dca.features.price import trailing_return, compute_trailing_features
from quant_dca.features.history import ActionCoverage, VolumeEvidence, build_price_features
from quant_dca.canonical.validate import DiscontinuityEvidence, validate_ohlcv
from quant_dca.features.registry import FeatureRegistry
from quant_dca.types import OHLCV, CorporateAction, QualityTier, Region, FXQuote, Security


def bars(n=120, currency="USD"):
    result = []
    day = date(2020, 1, 2)
    while len(result) < n:
        close = eligible_session_close("XNYS", day)
        if close:
            p = 100 + len(result)
            result.append(OHLCV(security_id="TEST", session_date=day.isoformat(),
                open=p, high=p+1, low=p-1, close=p, volume=1000,
                currency=currency, region=Region.US, exchange="XNYS",
                session_open_at=eligible_session_open("XNYS", day), session_close_at=close,
                available_at=close, quality=QualityTier.A, source="fixture", revision_id="v1"))
        day += timedelta(days=1)
    return result


def build(rows, *, as_of=None, actions=(), volumes=None, fx_quotes=(), discontinuity_evidence=(), listings=None):
    cutoff = as_of or rows[-1].session_close_at
    coverage = ActionCoverage("TEST", min(r.session_date for r in rows), max(r.session_date for r in rows),
                              rows[0].available_at, "fixture", "audited actions")
    if volumes is None:
        volumes = [VolumeEvidence(r.security_id, r.session_date, r.revision_id,
                     r.volume, "original_share_units", r.available_at, "fixture", "units audit") for r in rows]
    return build_price_features(rows, actions, security_id="TEST", exchange="XNYS",
        as_of=cutoff, action_coverage=coverage, volume_evidence=volumes, fx_quotes=fx_quotes,
        discontinuity_evidence=discontinuity_evidence,
        listing_history=listings if listings is not None else [Security(security_id="TEST", ticker="TEST", name="fixture", currency=rows[0].currency,
            region=Region.US, exchange="XNYS", active_from=rows[0].session_date, available_at=rows[0].available_at,
            quality=QualityTier.A, source="fixture", revision_id="v1")],
        fx_max_age=timedelta(days=4))


def values(result):
    return {r.feature:r.value for r in result.features}


def test_pure_return_and_short_history():
    assert trailing_return([100, 102, 101], 2) == pytest.approx(.01)
    result = values(build(bars()))
    assert result["return_20d_raw"] == pytest.approx(219/199-1)
    assert result["return_60d_raw"] == pytest.approx(219/159-1)
    assert result["return_120d_raw"] is None
    assert result["return_252d_raw"] is None


def test_actual_ingress_ignores_future_and_late_revision():
    rows = bars(122)
    cutoff = rows[119].available_at
    first = build(rows, as_of=cutoff)
    mutated = rows[:120] + [replace(r, close=9000, high=9001, open=9000, low=8999) for r in rows[120:]]
    mutated.append(replace(rows[110], close=5000, high=5001, available_at=rows[-1].available_at,
                           revised_at=rows[-1].available_at, revision_id="v2"))
    assert first == build(mutated, as_of=cutoff)
    assert all(r.max_input_available_at <= cutoff for r in first.features)


def test_gap_is_not_compressed_or_filled():
    rows = bars()
    assert values(build(rows[:110]+rows[111:]))["return_20d_raw"] is None
    assert values(build(rows[:40]+rows[41:]))["return_20d_raw"] is not None


def test_split_and_dividend_integrity_and_raw_turnover():
    rows = bars(22)
    rows = [replace(r, open=100, high=101, low=99, close=100) for r in rows]
    rows[10:] = [replace(r, open=50, high=50.5, low=49.5, close=50, volume=2000) for r in rows[10:]]
    rows[15:] = [replace(r, open=49, high=49.5, low=48.5, close=49) for r in rows[15:]]
    def action(kind, i, **kwargs):
        return CorporateAction(security_id="TEST", action_id=kind, action_type=kind,
            ex_date=rows[i].session_date, currency="USD", region=Region.US, exchange="XNYS",
            available_at=rows[0].available_at, quality=QualityTier.A, source="fixture", revision_id="v1", **kwargs)
    actions = [action("split",10,split_ratio=2), action("dividend",15,cash_amount=1)]
    result = build(rows, actions=actions)
    assert values(result)["return_20d_raw"] == pytest.approx(0)
    assert values(result)["amihud_illiquidity_20d_log"] == pytest.approx(0, abs=1e-15)
    assert result.usd_turnover[9:11] == (100000,100000)
    assert rows[0].close == 100


def test_fx_at_each_historical_eod_and_explicit_volume_basis():
    rows = bars(22, "EUR")
    quotes = [FXQuote(base_currency="EUR", quote_currency="USD", rate=2,
        fixing_at=r.session_close_at, available_at=r.session_close_at,
        quality=QualityTier.A, source="fixture", revision_id="v1") for r in rows]
    result = build(rows, fx_quotes=quotes)
    assert result.usd_turnover[-1] == 121*1000*2
    late = replace(quotes[-1], rate=900, available_at=quotes[-1].available_at+timedelta(hours=1))
    assert build(rows,fx_quotes=quotes+[late]) == result
    assert values(build(rows,volumes=[]))["median_dollar_volume_20d_log"] is None
    assert values(build(rows,fx_quotes=[]))["median_dollar_volume_20d_log"] is None


def test_all_numeric_formulas_and_crisis_preserved():
    prices = [100.] * 252 + [50.]
    result = compute_trailing_features(prices, [p+1 for p in prices], [p-1 for p in prices], [1000.]*253)
    assert result["return_5d_raw"] == -.5
    assert result["maximum_drawdown_60d_raw"] == -.5
    assert result["current_drawdown_raw"] == -.5
    assert result["drawdown_duration_sessions_raw"] == 1
    assert result["realized_volatility_20d_raw"] == pytest.approx(abs(math.log(.5))*math.sqrt(252/20))
    assert result["distance_ma20_raw"] == pytest.approx(50/97.5-1)
    assert result["atr_20d_percent_price_raw"] == pytest.approx((19*2+51)/20/50)


def test_every_registry_output_and_lookback():
    prices = [100 + i + 2*math.sin(i) for i in range(253)]
    result = compute_trailing_features(prices,prices,prices,[1000]*253)
    definitions = [d for d in FeatureRegistry.v1() if d.domain in {"price_trend","volatility_drawdown","volume_liquidity"}]
    assert set(result) == {d.name for d in definitions}
    for d in definitions:
        n = d.lookback_sessions
        assert compute_trailing_features(prices[:n-1],prices[:n-1],prices[:n-1],[1000]*(n-1))[d.name] is None
        assert compute_trailing_features(prices[:n],prices[:n],prices[:n],[1000]*n)[d.name] is not None
    for n in (5,20,60,120,252):
        assert result[f"return_{n}d_raw"] == pytest.approx(prices[-1]/prices[-n-1]-1)
    for n in (20,50,200):
        assert result[f"distance_ma{n}_raw"] == pytest.approx(prices[-1]/statistics.mean(prices[-n:])-1)
    assert result["distance_52week_high_raw"] == pytest.approx(prices[-1]/max(prices[-252:])-1)
    for n in (20,60):
        log_returns = [math.log(prices[i]/prices[i-1]) for i in range(253-n,253)]
        assert result[f"realized_volatility_{n}d_raw"] == pytest.approx(statistics.stdev(log_returns)*math.sqrt(252))
        ys = [math.log(p) for p in prices[-n:]]
        fit = statistics.linear_regression(list(range(n)),ys)
        rmse = math.sqrt(statistics.mean((y-fit.intercept-fit.slope*i)**2 for i,y in enumerate(ys)))
        assert result[f"trend_slope_{n}d_normalized"] == pytest.approx(fit.slope/rmse)
    assert result["downside_volatility_60d_raw"] == pytest.approx(statistics.stdev([min(r,0) for r in log_returns])*math.sqrt(252))
    assert result["volatility_ratio_20d_60d_raw"] == pytest.approx(result["realized_volatility_20d_raw"]/result["realized_volatility_60d_raw"])
    assert result["median_dollar_volume_20d_log"] == pytest.approx(math.log1p(1000))
    assert result["amihud_illiquidity_20d_log"] == pytest.approx(math.log1p(statistics.mean(abs(prices[i]/prices[i-1]-1)/1000 for i in range(233,253))))


def test_degenerate_scales_zero_turnover_and_missing_values():
    r = compute_trailing_features([100]*253,[100]*253,[100]*253,[0]*253)
    assert r["trend_slope_20d_normalized"] is None
    assert r["volatility_ratio_20d_60d_raw"] is None
    assert r["median_dollar_volume_20d_log"] == 0
    assert r["amihud_illiquidity_20d_log"] is None
    assert r["drawdown_duration_sessions_raw"] == 0
    assert trailing_return([100,None,101],2) is None


def test_ingress_preserves_verified_crisis_and_evidence():
    rows = bars(22)
    rows = [replace(r,open=100,high=101,low=99,close=100) for r in rows]
    rows[-1] = replace(rows[-1],open=20,high=21,low=19,close=20)
    e = DiscontinuityEvidence("TEST",rows[-2].session_date,rows[-1].session_date,
        "market_move","fixture","verified crash",rows[-1].available_at)
    result = build(rows,discontinuity_evidence=[e])
    assert values(result)["return_20d_raw"] == pytest.approx(-.8)
    assert result.discontinuity_evidence == (e,)
    assert all(r.max_input_available_at == e.verified_at for r in result.features)


def test_missing_last_bar_and_after_close_vintage_wait_for_eod():
    rows = bars(22)
    cutoff = rows[-1].available_at
    late = replace(rows[-1],available_at=cutoff+timedelta(minutes=1))
    result = build(rows[:-1]+[late],as_of=cutoff+timedelta(hours=1))
    assert values(result)["return_5d_raw"] is None
    assert result.sessions[-1] == rows[-1].session_date


def test_future_action_revision_does_not_change_ingress():
    rows = bars(22)
    a = CorporateAction(security_id="TEST",action_id="div",action_type="dividend",
        ex_date=rows[10].session_date,currency="USD",region=Region.US,exchange="XNYS",cash_amount=1,
        available_at=rows[0].available_at,quality=QualityTier.A,source="fixture",revision_id="v1")
    future = rows[-1].available_at+timedelta(days=1)
    revision = replace(a,cash_amount=10000,available_at=future,revised_at=future,revision_id="v2")
    assert build(rows,actions=[a]) == build(rows,actions=[a,revision])


def test_unverified_volume_does_not_block_price_and_late_fx_is_missing():
    rows = bars(22,"EUR")
    volumes = [VolumeEvidence(r.security_id,r.session_date,r.revision_id,r.volume,"unknown",
        r.available_at,"fixture","unverified units") for r in rows]
    result = values(build(rows,volumes=volumes))
    assert result["return_20d_raw"] is not None
    assert result["median_dollar_volume_20d_log"] is None
    quotes = [FXQuote(base_currency="EUR",quote_currency="USD",rate=2,
        fixing_at=rows[-1].session_close_at,available_at=rows[-1].session_close_at,
        quality=QualityTier.A,source="fixture",revision_id="v1")]
    assert values(build(rows,fx_quotes=quotes))["median_dollar_volume_20d_log"] is None


def test_future_volume_evidence_cannot_change_historical_snapshot():
    rows = bars(22)
    future = VolumeEvidence("TEST", rows[-1].session_date, "v1", 99999,
        "original_share_units", rows[-1].available_at+timedelta(days=1), "", "")
    assert build(rows, volumes=[]) == build(rows, volumes=[future])


def test_historical_currency_required_and_worst_quality_propagates():
    rows = bars(22)
    result = build(rows, listings=[])
    assert values(result)["return_20d_raw"] is not None
    assert values(result)["median_dollar_volume_20d_log"] is None
    listing = Security(security_id="TEST", ticker="TEST", name="fixture", currency="USD",
        region=Region.US, exchange="XNYS", active_from=rows[0].session_date,
        available_at=rows[0].available_at, quality=QualityTier.C, source="audit", revision_id="v1")
    result = build(rows, listings=[listing])
    assert result.selected_listings
    assert all(f.quality == QualityTier.C for f in result.features)
    with pytest.raises(ValueError, match="MISMATCHED_HISTORICAL_CURRENCY"):
        build(rows, listings=[replace(listing,currency="EUR")])


def test_local_currency_and_fx_rescaling_preserve_usd_liquidity():
    rows = bars(22,"EUR")
    def quotes(rate):
        return [FXQuote(base_currency="EUR",quote_currency="USD",rate=rate,
            fixing_at=r.session_close_at,available_at=r.session_close_at,
            quality=QualityTier.A,source="fixture",revision_id="v1") for r in rows]
    original = build(rows,fx_quotes=quotes(2))
    scaled = [replace(r,open=r.open*2,high=r.high*2,low=r.low*2,close=r.close*2) for r in rows]
    converted = build(scaled,fx_quotes=quotes(1))
    assert original.usd_turnover == converted.usd_turnover
    for name in ("median_dollar_volume_20d_log","amihud_illiquidity_20d_log"):
        assert values(original)[name] == pytest.approx(values(converted)[name])


def test_zero_volume_ingress_is_valid_but_amihud_missing():
    rows = [replace(r,volume=0) for r in bars(22)]
    result = build(rows)
    assert values(result)["median_dollar_volume_20d_log"] == 0
    assert values(result)["amihud_illiquidity_20d_log"] is None


def test_action_availability_cannot_precede_explicit_announcement():
    rows = bars(22)
    action = CorporateAction(security_id="TEST",action_id="div",action_type="dividend",
        ex_date=rows[10].session_date,currency="USD",region=Region.US,exchange="XNYS",cash_amount=10,
        available_at=rows[0].available_at,announced_at=rows[-1].available_at+timedelta(days=1),
        quality=QualityTier.A,source="fixture",revision_id="v1")
    with pytest.raises(ValueError, match="AVAILABILITY_BEFORE_ANNOUNCEMENT"):
        build(rows,actions=[action])
    absent = replace(action,announced_at=None)
    assert build(rows,actions=[absent]).selected_actions[0].announced_at is None
    future = replace(action,available_at=rows[-1].available_at+timedelta(hours=1))
    assert build(rows,actions=[future]) == build(rows)


def test_missing_canonical_volume_preserves_price_only_and_independent_turnover():
    rows = [replace(r,volume=None) for r in bars(22)]
    result = build(rows,volumes=[])
    assert values(result)["return_20d_raw"] == pytest.approx(121/101-1)
    assert values(result)["median_dollar_volume_20d_log"] is None
    assert all(r.volume is None for r in result.raw_bars)
    evidence = [VolumeEvidence("TEST",r.session_date,r.revision_id,1000,
        "original_share_units",r.available_at,"fixture","independent audit") for r in rows]
    audited = build(rows,volumes=evidence)
    assert audited.usd_turnover[-1] == 121000
    assert values(audited)["median_dollar_volume_20d_log"] == pytest.approx(math.log1p(111500))
    strict = validate_ohlcv(rows,as_of=rows[-1].available_at)
    assert strict.valid_rows == []
    assert strict.reasons == {"MISSING_VOLUME":22}


@pytest.mark.parametrize("change,reason", [
    ({"close":-1},"NONPOSITIVE_PRICE"),
    ({"open":10,"high":11,"low":9,"close":10},"UNEXPLAINED_DISCONTINUITY"),
    ({"volume":-1},"NEGATIVE_VOLUME"),
])
def test_price_only_view_does_not_bypass_invalid_bars(change,reason):
    rows = [replace(r,volume=None) for r in bars(22)]
    rows[-1] = replace(rows[-1],**change)
    with pytest.raises(ValueError,match=reason):
        build(rows,volumes=[])


def test_price_only_view_retains_session_clock_validation():
    rows = [replace(r,volume=None) for r in bars(22)]
    rows[-1] = replace(rows[-1],session_open_at=rows[-1].session_open_at+timedelta(minutes=1))
    with pytest.raises(ValueError,match="SESSION_CLOCK_MISMATCH"):
        build(rows,volumes=[])
