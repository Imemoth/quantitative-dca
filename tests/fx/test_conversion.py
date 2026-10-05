"""Point-in-time FX conversion uses only fully evidenced canonical quotes."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import math

import pytest

from quant_dca.corporate_actions.economics import economic_acquisition_cost
from quant_dca.fx.conversion import FXQuoteUnavailable, FXService, StaleFXQuote
from quant_dca.types import FXQuote, OHLCV, QualityTier, Region


UTC = timezone.utc


def ts(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2020, 1, day, hour, minute, tzinfo=UTC)


def quote(
    rate: float,
    fixing_at: datetime,
    *,
    base: str = "USD",
    counter: str = "HUF",
    available_at: datetime | None = None,
    published_at: datetime | None = None,
    revised_at: datetime | None = None,
    revision_id: str = "v1",
    quality: QualityTier = QualityTier.A,
    source: str = "evidenced-fixture",
    quote_type: str = "spot",
) -> FXQuote:
    available = available_at or fixing_at
    return FXQuote(
        base_currency=base,
        quote_currency=counter,
        rate=rate,
        fixing_at=fixing_at,
        available_at=available,
        published_at=published_at,
        revised_at=revised_at,
        quality=quality,
        source=source,
        revision_id=revision_id,
        quote_type=quote_type,
    )


def bar(open_at: datetime, price: float = 10.0) -> OHLCV:
    return OHLCV(
        security_id="US-1",
        session_date=open_at.date().isoformat(),
        open=price,
        high=price,
        low=price,
        close=price,
        volume=1_000.0,
        currency="USD",
        region=Region.US,
        exchange="XNYS",
        session_open_at=open_at,
        session_close_at=open_at + timedelta(hours=6, minutes=30),
        available_at=open_at + timedelta(hours=6, minutes=31),
        quality=QualityTier.A,
        source="price-fixture",
        revision_id="price-v1",
    )


def test_fx_never_uses_a_fixing_or_vintage_unknown_at_execution():
    execution = ts(2, 15)
    known = quote(300.0, ts(2, 14, 30), available_at=ts(2, 14, 31))
    later_fixing = quote(305.0, ts(2, 21), revision_id="later-fixing")
    late_publication = quote(
        304.0,
        ts(2, 14, 45),
        available_at=ts(2, 15, 1),
        revision_id="not-known-yet",
    )
    service = FXService.from_rows([known, later_fixing, late_publication], max_age=None)

    assert service.resolve("USD", "HUF", execution) is known
    assert service.rate("USD", "HUF", execution) == 300.0


def test_latest_known_revision_of_latest_eligible_fixing_preserves_evidence():
    fixing = ts(2, 14, 30)
    first = quote(300.0, fixing, published_at=fixing, revision_id="v1")
    revised = quote(
        301.0,
        fixing,
        available_at=ts(2, 14, 50),
        published_at=fixing,
        revised_at=ts(2, 14, 45),
        revision_id="v2",
        quality=QualityTier.C,
        source="corrected-source",
    )
    service = FXService.from_rows([first, revised], max_age=None)

    selected = service.resolve("USD", "HUF", ts(2, 15))

    assert selected is revised
    assert selected.quality is QualityTier.C
    assert selected.source == "corrected-source"
    assert selected.published_at == fixing
    assert selected.revised_at == ts(2, 14, 45)


def test_revision_timestamp_outranks_delayed_availability_for_same_fixing():
    fixing = ts(2, 9)
    older_revision_delayed = quote(
        300.0,
        fixing,
        available_at=ts(2, 12),
        revised_at=ts(2, 10),
        revision_id="v2-delayed",
    )
    newer_revision_arrived_first = quote(
        301.0,
        fixing,
        available_at=ts(2, 11, 1),
        revised_at=ts(2, 11),
        revision_id="v3",
    )
    service = FXService.from_rows(
        [older_revision_delayed, newer_revision_arrived_first], max_age=None
    )

    assert service.resolve("USD", "HUF", ts(2, 13)) is newer_revision_arrived_first


def test_same_revision_timestamp_conflict_is_ambiguous_despite_arrival_order():
    fixing = ts(2, 9)
    rows = [
        quote(300.0, fixing, available_at=ts(2, 11), revised_at=ts(2, 10)),
        quote(
            301.0,
            fixing,
            available_at=ts(2, 12),
            revised_at=ts(2, 10),
            revision_id="conflict",
        ),
    ]
    service = FXService.from_rows(rows, max_age=None)

    with pytest.raises(ValueError, match="PIT_AMBIGUOUS_VINTAGE"):
        service.resolve("USD", "HUF", ts(2, 13))


def test_conflicting_indistinguishable_revisions_fail_closed():
    fixing = ts(2, 14, 30)
    known = ts(2, 14, 45)
    rows = [
        quote(300.0, fixing, available_at=known, revised_at=known, revision_id="a"),
        quote(301.0, fixing, available_at=known, revised_at=known, revision_id="b"),
    ]
    service = FXService.from_rows(rows, max_age=None)

    with pytest.raises(ValueError, match="PIT_AMBIGUOUS_VINTAGE"):
        service.resolve("USD", "HUF", ts(2, 15))


def test_missing_and_caller_configured_stale_quotes_are_distinct_failures():
    service = FXService.from_rows([quote(300.0, ts(1, 14))], max_age=timedelta(hours=12))

    with pytest.raises(FXQuoteUnavailable, match="FX_QUOTE_UNAVAILABLE"):
        service.resolve("EUR", "HUF", ts(1, 15))
    with pytest.raises(StaleFXQuote, match="STALE_FX_QUOTE"):
        service.resolve("USD", "HUF", ts(2, 14, 1))

    unbounded = FXService.from_rows([quote(300.0, ts(1, 14))], max_age=None)
    assert unbounded.rate("USD", "HUF", ts(2, 14, 1)) == 300.0


def test_daily_fallback_requires_same_day_open_evidence():
    prior_open = quote(298.0, ts(1, 8), quote_type="daily_open")
    service = FXService.from_rows([prior_open], max_age=None)
    with pytest.raises(FXQuoteUnavailable, match="FX_DAILY_OPEN_UNAVAILABLE"):
        service.resolve("USD", "HUF", ts(2, 15))

    same_day_open = quote(
        300.0,
        ts(2, 8),
        available_at=ts(2, 8, 1),
        quote_type="daily_open",
        source="documented-open-feed",
    )
    same_day = FXService.from_rows([prior_open, same_day_open], max_age=None)
    assert same_day.resolve("USD", "HUF", ts(2, 15)) is same_day_open


def test_daily_close_is_not_treated_as_an_open_fallback():
    service = FXService.from_rows(
        [quote(302.0, ts(1, 21), quote_type="daily_close")], max_age=None
    )
    with pytest.raises(ValueError, match="UNSUPPORTED_DAILY_FX_QUOTE_TYPE"):
        service.resolve("USD", "HUF", ts(2, 15))


@pytest.mark.parametrize(
    "unsupported_type",
    ["close", "eod", "open", " daily_open", "DAILY_OPEN"],
)
def test_unknown_quote_types_cannot_bypass_daily_evidence_rules(unsupported_type):
    service = FXService.from_rows(
        [quote(302.0, ts(1, 21), quote_type=unsupported_type)], max_age=None
    )
    with pytest.raises(ValueError, match="INVALID_FX_QUOTE_TYPE"):
        service.resolve("USD", "HUF", ts(2, 15))


@pytest.mark.parametrize("bad_rate", [0.0, -1.0, math.nan, math.inf, True])
def test_invalid_rates_fail_closed(bad_rate):
    service = FXService.from_rows([quote(bad_rate, ts(2, 14))], max_age=None)
    with pytest.raises(ValueError, match="INVALID_FX_RATE"):
        service.resolve("USD", "HUF", ts(2, 15))


@pytest.mark.parametrize(
    "bad_row",
    [
        quote(300.0, ts(2, 14), base="usd"),
        quote(300.0, ts(2, 14), base="USD", counter="USD"),
        quote(300.0, ts(2, 14), available_at=ts(2, 13)),
        quote(300.0, ts(2, 14), published_at=ts(2, 15)),
        quote(300.0, ts(2, 14), revised_at=ts(2, 15)),
    ],
    ids=["lowercase", "same-leg", "available-before-fixing", "late-publication", "late-revision"],
)
def test_incoherent_currency_or_chronology_fails_closed(bad_row):
    service = FXService.from_rows([bad_row], max_age=None)
    with pytest.raises(ValueError, match="INVALID_FX_|PIT_INVALID_CHRONOLOGY"):
        service.resolve("USD", "HUF", ts(2, 16))


def test_naive_request_time_and_invalid_age_policy_are_rejected():
    with pytest.raises(ValueError, match="INVALID_MAX_FX_AGE"):
        FXService.from_rows([], max_age=timedelta(seconds=-1))
    service = FXService.from_rows([quote(300.0, ts(2, 14))], max_age=None)
    with pytest.raises(ValueError, match="INVALID_TIMESTAMP"):
        service.rate("USD", "HUF", ts(2, 15).replace(tzinfo=None))


def test_to_huf_validates_amount_and_native_huf_needs_no_fabricated_quote():
    service = FXService.from_rows([quote(300.0, ts(2, 14))], max_age=None)
    assert service.to_huf(2.0, "USD", ts(2, 15)) == 600.0
    assert service.to_huf(-2.0, "HUF", ts(2, 15)) == -2.0
    with pytest.raises(ValueError, match="INVALID_FX_AMOUNT"):
        service.to_huf(math.nan, "USD", ts(2, 15))


def test_real_fx_service_integrates_with_task7_economic_cashflow_evidence():
    execution = ts(2, 14, 30)
    selected = quote(
        300.0,
        ts(2, 14),
        available_at=ts(2, 14, 1),
        quality=QualityTier.B,
        source="task8-fixture",
    )
    service = FXService.from_rows([selected], max_age=timedelta(hours=1))

    baseline_open = datetime(2019, 12, 31, 14, 30, tzinfo=UTC)
    result = economic_acquisition_cost(bar(execution), bar(baseline_open, 11.0), [], service)

    assert result.fill_cost == 3_000.0
    assert result.cashflows[0].fx_quote is selected
    assert result.cashflows[0].fx_fixing_at == ts(2, 14)
    assert result.cashflows[0].fx_available_at == ts(2, 14, 1)


def test_request_offsets_compare_as_absolute_instants():
    fixing = ts(2, 14)
    service = FXService.from_rows([quote(300.0, fixing)], max_age=timedelta(hours=1))
    execution = ts(2, 14, 30).astimezone(timezone(timedelta(hours=2)))
    assert service.resolve("USD", "HUF", execution).fixing_at == fixing


def test_input_collection_is_snapshotted():
    rows = [quote(300.0, ts(2, 14))]
    service = FXService.from_rows(rows, max_age=None)
    rows.append(replace(rows[0], rate=999.0, fixing_at=ts(2, 14, 59)))
    assert service.rate("USD", "HUF", ts(2, 15)) == 300.0


def test_from_rows_rejects_the_unevidenced_tuple_shortcut():
    invented = [("USDHUF", ts(2, 14), 300.0)]
    with pytest.raises(TypeError, match="canonical FXQuote required"):
        FXService.from_rows(invented, max_age=None)
