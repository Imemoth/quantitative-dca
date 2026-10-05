"""Corporate-action economics preserve economically equivalent ownership."""
from datetime import datetime, timedelta, timezone
import math

import pytest

from quant_dca.corporate_actions.economics import (
    EconomicLabelUnavailable,
    economic_acquisition_cost,
    economic_price_improvement,
    split_adjusted_feature_prices,
)
from quant_dca.point_in_time.asof import assert_pit_safe
from quant_dca.types import CorporateAction, FXQuote, OHLCV, QualityTier, Region


UTC = timezone.utc


def ts(year: int, month: int, day: int, hour: int = 14, minute: int = 30) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def bar(
    day: str,
    price: float,
    *,
    security_id: str = "US-1",
    currency: str = "USD",
    quality: QualityTier = QualityTier.A,
    source: str = "fixture",
    revision_id: str = "v1",
) -> OHLCV:
    year, month, date = map(int, day.split("-"))
    return OHLCV(
        security_id=security_id,
        session_date=day,
        open=price,
        high=price,
        low=price,
        close=price,
        volume=1_000.0,
        currency=currency,
        region=Region.US,
        exchange="XNYS",
        session_open_at=ts(year, month, date),
        session_close_at=ts(year, month, date, 21, 0),
        available_at=ts(year, month, date, 21, 1),
        quality=quality,
        source=source,
        revision_id=revision_id,
    )


def action(
    action_id: str,
    action_type: str,
    ex_date: str,
    *,
    cash_amount: float | None = None,
    split_ratio: float | None = None,
    currency: str = "USD",
    available_at: datetime | None = None,
    payable_at: datetime | None = None,
    quality: QualityTier = QualityTier.A,
    source: str = "fixture",
    revision_id: str = "v1",
) -> CorporateAction:
    year, month, date = map(int, ex_date.split("-"))
    known = available_at or ts(year, month, max(1, date - 1), 12, 0)
    return CorporateAction(
        security_id="US-1",
        action_id=action_id,
        action_type=action_type,
        ex_date=ex_date,
        currency=currency,
        region=Region.US,
        exchange="XNYS",
        cash_amount=cash_amount,
        split_ratio=split_ratio,
        payable_at=payable_at,
        available_at=known,
        quality=quality,
        source=source,
        revision_id=revision_id,
    )


class FixtureFX:
    """Strict fixture: a wrong currency or timestamp cannot accidentally pass."""

    def __init__(self, quotes: dict[tuple[str, str, datetime], FXQuote]):
        self._quotes = quotes
        self.calls: list[tuple[str, str, datetime]] = []

    def resolve(self, base: str, quote: str, at_or_before: datetime) -> FXQuote:
        key = (base, quote, at_or_before)
        self.calls.append(key)
        return self._quotes[key]


def fx_quote(
    currency: str,
    cashflow_at: datetime,
    rate: float,
    *,
    fixing_at: datetime | None = None,
    available_at: datetime | None = None,
) -> FXQuote:
    fixing = fixing_at or cashflow_at - timedelta(minutes=1)
    available = available_at or fixing
    return FXQuote(
        base_currency=currency,
        quote_currency="HUF",
        rate=rate,
        fixing_at=fixing,
        available_at=available,
        quality=QualityTier.A,
        source="fx-fixture",
        revision_id=f"{currency}-{fixing.isoformat()}",
    )


def huf_fx(*_timestamps: datetime) -> FixtureFX:
    return FixtureFX({})


def test_dividend_drop_is_not_free_timing_edge():
    improvement = economic_price_improvement(
        baseline_cost=100.0,
        delayed_fill=98.0,
        foregone_distribution=2.0,
    )
    assert improvement == 0.0


def test_two_for_one_split_preserves_same_economic_share_units():
    baseline = bar("2020-01-02", 100.0, currency="HUF")
    delayed = bar("2020-01-10", 50.0, currency="HUF")
    split = action("split-1", "split", "2020-01-06", split_ratio=2.0, currency="HUF")

    result = economic_acquisition_cost(
        delayed, baseline, [split], huf_fx(delayed.session_open_at)
    )

    assert result.share_units == 2.0
    assert result.fill_cost == 100.0
    assert result.foregone_distributions == 0.0
    assert result.total == 100.0


def test_multiple_splits_and_dividends_use_units_in_force_on_each_ex_date():
    baseline = bar("2020-01-02", 125.0, currency="HUF")
    delayed = bar("2020-03-02", 20.0, currency="HUF")
    actions = [
        action("split-1", "split", "2020-01-10", split_ratio=2.0, currency="HUF"),
        action("div-1", "dividend", "2020-01-20", cash_amount=1.0, currency="HUF",
               payable_at=ts(2020, 2, 1, 12, 0)),
        action("split-2", "split", "2020-02-10", split_ratio=3.0, currency="HUF"),
        action("div-2", "dividend", "2020-02-20", cash_amount=0.5, currency="HUF",
               payable_at=ts(2020, 3, 1, 12, 0)),
    ]
    fx = huf_fx(delayed.session_open_at, actions[1].payable_at, actions[3].payable_at)

    result = economic_acquisition_cost(delayed, baseline, actions, fx)

    assert result.share_units == 6.0
    assert result.fill_cost == 120.0
    assert result.foregone_distributions == 5.0
    assert result.total == 125.0
    assert result.label_matures_at == delayed.available_at
    assert [flow.native_amount for flow in result.cashflows] == [120.0, 2.0, 3.0]
    assert all(flow.currency == "HUF" and flow.fx_quote is None for flow in result.cashflows)


def test_foregone_dividend_requires_baseline_before_and_delayed_on_or_after_ex_date():
    dividend = action("div", "dividend", "2020-01-10", cash_amount=2.0, currency="HUF",
                      payable_at=ts(2020, 1, 20, 12, 0))
    delayed = bar("2020-01-10", 98.0, currency="HUF")
    result = economic_acquisition_cost(
        delayed,
        bar("2020-01-09", 100.0, currency="HUF"),
        [dividend],
        huf_fx(delayed.session_open_at, dividend.payable_at),
    )
    assert result.foregone_distributions == 2.0

    already_ex = economic_acquisition_cost(
        bar("2020-01-13", 98.0, currency="HUF"),
        bar("2020-01-10", 98.0, currency="HUF"),
        [dividend],
        huf_fx(ts(2020, 1, 13)),
    )
    assert already_ex.foregone_distributions == 0.0


def test_fill_and_each_dividend_use_their_own_fx_cashflow_timestamp():
    baseline = bar("2020-01-02", 100.0)
    delayed = bar("2020-03-02", 49.0)
    split = action("split", "split", "2020-01-10", split_ratio=2.0)
    paid = ts(2020, 2, 3, 16, 0)
    dividend = action("div", "dividend", "2020-01-20", cash_amount=1.0,
                      payable_at=paid)
    fill_quote = fx_quote("USD", delayed.session_open_at, 310.0)
    dividend_quote = fx_quote("USD", paid, 300.0)
    fx = FixtureFX({
        ("USD", "HUF", delayed.session_open_at): fill_quote,
        ("USD", "HUF", paid): dividend_quote,
    })

    result = economic_acquisition_cost(delayed, baseline, [split, dividend], fx)

    assert result.fill_cost == 30_380.0
    assert result.foregone_distributions == 600.0
    assert result.total == 30_980.0
    assert result.cashflows[0].kind == "fill"
    assert result.cashflows[0].native_amount == 98.0
    assert result.cashflows[0].share_units == 2.0
    assert result.cashflows[0].fx_quote is fill_quote
    assert result.cashflows[1].kind == "foregone_dividend"
    assert result.cashflows[1].native_amount == 2.0
    assert result.cashflows[1].currency == "USD"
    assert result.cashflows[1].fx_quote is dividend_quote


def test_future_cashflow_exposes_maturity_and_development_cutoff_prevents_fx_query():
    baseline = bar("2023-12-20", 100.0)
    delayed = bar("2023-12-29", 98.0)
    payable = ts(2024, 1, 5, 16, 0)
    dividend = action("div", "dividend", "2023-12-28", cash_amount=2.0,
                      payable_at=payable)
    fx = FixtureFX({})

    with pytest.raises(EconomicLabelUnavailable, match="DEVELOPMENT_CASHFLOW_FX_UNAVAILABLE") as exc:
        economic_acquisition_cost(delayed, baseline, [dividend], fx)

    assert exc.value.label_matures_at == payable
    assert fx.calls == []


def test_2024_action_availability_fails_before_any_fx_query():
    baseline = bar("2023-12-20", 100.0)
    delayed = bar("2023-12-29", 98.0)
    dividend = action(
        "late-revision",
        "dividend",
        "2023-12-28",
        cash_amount=2.0,
        payable_at=ts(2023, 12, 29, 16, 0),
        available_at=ts(2024, 1, 2, 12, 0),
    )
    fx = FixtureFX({})

    with pytest.raises(EconomicLabelUnavailable) as exc:
        economic_acquisition_cost(delayed, baseline, [dividend], fx)

    assert exc.value.label_matures_at == dividend.available_at
    assert fx.calls == []


@pytest.mark.parametrize("bad_field", ["fixing", "availability"])
def test_fx_evidence_must_be_known_no_later_than_cashflow(bad_field):
    baseline = bar("2020-01-02", 100.0)
    delayed = bar("2020-01-10", 98.0)
    late = delayed.session_open_at + timedelta(minutes=1)
    quote = fx_quote(
        "USD",
        delayed.session_open_at,
        300.0,
        fixing_at=late if bad_field == "fixing" else None,
        available_at=late if bad_field == "availability" else None,
    )
    fx = FixtureFX({("USD", "HUF", delayed.session_open_at): quote})

    with pytest.raises(ValueError, match="PIT_FX_AFTER_CASHFLOW"):
        economic_acquisition_cost(delayed, baseline, [], fx)


def test_relevant_merger_or_spinoff_is_not_silently_omitted():
    baseline = bar("2020-01-02", 100.0)
    delayed = bar("2020-01-10", 98.0)
    for action_type in ("merger", "spinoff"):
        unsupported = action("unsupported", action_type, "2020-01-06")
        with pytest.raises(NotImplementedError, match="UNSUPPORTED_CORPORATE_ACTION"):
            economic_acquisition_cost(delayed, baseline, [unsupported], FixtureFX({}))


def test_same_day_split_and_dividend_reject_ambiguous_unit_ordering():
    baseline = bar("2020-01-02", 100.0)
    delayed = bar("2020-01-10", 48.0)
    actions = [
        action("split", "split", "2020-01-06", split_ratio=2.0),
        action("div", "dividend", "2020-01-06", cash_amount=1.0,
               payable_at=ts(2020, 1, 20, 12, 0)),
    ]
    with pytest.raises(ValueError, match="AMBIGUOUS_SAME_DAY_ACTION_ORDER"):
        economic_acquisition_cost(delayed, baseline, actions, FixtureFX({}))


def test_feature_prices_are_pit_split_adjusted_without_mutating_raw_bars():
    raw = [
        bar("2020-01-02", 100.0, source="prices", revision_id="price-v1"),
        bar("2020-01-03", 102.0),
        bar("2020-01-06", 51.0),
    ]
    known_split = action(
        "split-known", "split", "2020-01-06", split_ratio=2.0,
        available_at=ts(2020, 1, 3, 20, 0),
        quality=QualityTier.C, source="actions", revision_id="action-v2",
    )
    unavailable_split = action(
        "split-unavailable", "split", "2020-01-07", split_ratio=2.0,
        available_at=ts(2020, 1, 8, 20, 0),
    )

    adjusted = split_adjusted_feature_prices(
        raw, [known_split, unavailable_split], as_of=ts(2020, 1, 7, 22, 0)
    )

    assert [row.open for row in adjusted] == [50.0, 51.0, 51.0]
    assert [row.split_factor for row in adjusted] == [2.0, 2.0, 1.0]
    assert all(row.price_basis == "split_adjusted_feature" for row in adjusted)
    assert_pit_safe(adjusted, ts(2020, 1, 7, 22, 0))
    assert adjusted[0].available_at == adjusted[0].max_input_available_at
    assert adjusted[0].quality == QualityTier.C
    assert adjusted[0].source == "prices"
    assert adjusted[0].revision_id == "price-v1|split-known:action-v2"
    assert adjusted[0].applied_action_ids == ("split-known",)
    assert raw[0].open == 100.0
    assert raw[0].price_basis == "unadjusted"


def test_split_effective_boundary_uses_exchange_open_as_an_absolute_instant():
    raw = [bar("2020-01-03", 100.0)]
    split = action(
        "split", "split", "2020-01-06", split_ratio=2.0,
        available_at=ts(2020, 1, 3, 20, 0),
    )
    before_open = datetime(2020, 1, 7, 4, 0, tzinfo=timezone(timedelta(hours=14)))
    same_instant_utc = before_open.astimezone(UTC)

    local_result = split_adjusted_feature_prices(raw, [split], as_of=before_open)
    utc_result = split_adjusted_feature_prices(raw, [split], as_of=same_instant_utc)

    assert local_result[0].open == 100.0
    assert utc_result[0].open == 100.0

    at_exchange_open = ts(2020, 1, 6, 14, 30)
    assert split_adjusted_feature_prices(raw, [split], as_of=at_exchange_open)[0].open == 50.0


@pytest.mark.parametrize(
    ("baseline", "delayed", "distribution"),
    [(0.0, 98.0, 2.0), (-1.0, 98.0, 2.0), (100.0, 0.0, 2.0),
     (100.0, math.nan, 2.0), (100.0, 98.0, -1.0)],
)
def test_economic_price_improvement_rejects_invalid_costs(baseline, delayed, distribution):
    with pytest.raises(ValueError, match="INVALID_ECONOMIC_COST"):
        economic_price_improvement(baseline, delayed, distribution)


def test_economic_acquisition_cost_rejects_bad_fill_or_action_values():
    baseline = bar("2020-01-02", 100.0)
    with pytest.raises(ValueError, match="INVALID_FILL_PRICE"):
        economic_acquisition_cost(bar("2020-01-10", math.nan), baseline, [], FixtureFX({}))

    bad_split = action("split", "split", "2020-01-06", split_ratio=0.0)
    with pytest.raises(ValueError, match="INVALID_SPLIT_RATIO"):
        economic_acquisition_cost(bar("2020-01-10", 50.0), baseline, [bad_split], FixtureFX({}))

    missing_payable = action("div", "dividend", "2020-01-06", cash_amount=1.0)
    with pytest.raises(ValueError, match="MISSING_PAYABLE_AT"):
        economic_acquisition_cost(bar("2020-01-10", 99.0), baseline, [missing_payable], FixtureFX({}))


def test_feature_adjustment_rejects_nonpositive_price_and_future_as_of_leakage():
    with pytest.raises(ValueError, match="INVALID_FEATURE_PRICE"):
        split_adjusted_feature_prices([bar("2020-01-02", 0.0)], [], as_of=ts(2020, 1, 3))

    future_bar = bar("2020-01-06", 100.0)
    with pytest.raises(ValueError, match="PIT_FEATURE_PRICE_AFTER_AS_OF"):
        split_adjusted_feature_prices([future_bar], [], as_of=ts(2020, 1, 3))
