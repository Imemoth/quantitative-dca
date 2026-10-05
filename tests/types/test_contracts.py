"""Canonical records must resist mutation and reject ambiguous PIT timestamps."""
from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timedelta, timezone, tzinfo

import pytest

from quant_dca.types import (
    CorporateAction, FeatureValue, FXQuote, Observation, OHLCV,
    QualityTier, Region, Security, UniverseMembership,
)

UTC = datetime(2020, 3, 11, 12, 30, tzinfo=timezone.utc)
META = dict(available_at=UTC, quality=QualityTier.A, source="fixture", revision_id="v1",
            published_at=UTC, revised_at=UTC)
ROWS = [
    Observation(series="US_CPI", entity_id=None, observation_date="2020-02-29",
                value=2.3, **META),
    Security(security_id="US-1", ticker="OLD", name="Old Company", currency="USD",
             region=Region.US, exchange="XNYS", active_from="2012-01-01",
             active_to="2020-06-01", **META),
    UniverseMembership(universe_id="RESEARCH_US", security_id="US-1",
                       active_from="2012-01-01", active_to="2020-06-01",
                       region=Region.US, exchange="XNYS", currency="USD", **META),
    CorporateAction(security_id="US-1", action_id="div-1", action_type="dividend",
                    ex_date="2020-03-12", currency="USD", region=Region.US,
                    exchange="XNYS", cash_amount=2.0, announced_at=UTC,
                    payable_at=UTC + timedelta(days=10), **META),
    FXQuote(base_currency="USD", quote_currency="HUF", rate=300.0,
            fixing_at=UTC, **META),
    FeatureValue(feature="cpi_yoy", entity_id="US-1", observation_date="2020-02-29",
                 as_of=UTC, value=2.3, max_input_available_at=UTC, computed_at=UTC,
                 currency="USD", region=Region.US, exchange="XNYS", **META),
    OHLCV(security_id="US-1", session_date="2020-03-11", open=100.0, high=103.0,
          low=99.0, close=102.0, volume=12000.0, currency="USD", region=Region.US,
          exchange="XNYS", session_open_at=UTC, session_close_at=UTC,
          **META),
]


@pytest.mark.parametrize("row", ROWS, ids=lambda r: type(r).__name__)
def test_records_reject_mutation_and_deletion(row):
    for field in fields(row):
        before = getattr(row, field.name)
        with pytest.raises(FrozenInstanceError):
            setattr(row, field.name, None)
        with pytest.raises(FrozenInstanceError):
            delattr(row, field.name)
        assert getattr(row, field.name) == before


TIMESTAMP_CASES = [pytest.param(row, field.name, id=f"{type(row).__name__}.{field.name}")
                   for row in ROWS for field in fields(row)
                   if isinstance(getattr(row, field.name), datetime)]


class NoOffset(tzinfo):
    def utcoffset(self, dt):
        return None


@pytest.mark.parametrize("row,field_name", TIMESTAMP_CASES)
@pytest.mark.parametrize("bad", [UTC.replace(tzinfo=None), UTC.replace(tzinfo=NoOffset())],
                         ids=["no-tzinfo", "no-utc-offset"])
def test_every_timestamp_rejects_naive_datetimes(row, field_name, bad):
    with pytest.raises(ValueError, match=field_name):
        replace(row, **{field_name: bad})


@pytest.mark.parametrize("row,field_name", TIMESTAMP_CASES)
def test_every_timestamp_accepts_aware_non_utc_datetimes(row, field_name):
    offset_time = UTC.astimezone(timezone(timedelta(hours=2)))
    copy = replace(row, **{field_name: offset_time})
    assert getattr(copy, field_name) == UTC


def test_observation_preserves_contract_and_optional_missing_value():
    row = Observation(series="US_CPI", entity_id=None, observation_date="2020-02-29",
                      value=2.3, available_at=UTC, quality=QualityTier.A,
                      source="fixture", revision_id="v1")
    assert row.quality is QualityTier.A
    assert row.available_at.tzinfo is not None
    assert row.published_at is None
    assert row.revised_at is None
    assert replace(row, value=None).value is None


def test_vintage_update_creates_distinct_record_without_rewriting_original():
    first = ROWS[0]
    revision = replace(first, value=2.4, revision_id="v2", revised_at=UTC + timedelta(days=30),
                       available_at=UTC + timedelta(days=30))
    assert first.value == 2.3
    assert first.revision_id == "v1"
    assert revision.value == 2.4
    assert revision.available_at > first.available_at


def test_string_enum_values_are_stable_for_serialization():
    assert [tier.value for tier in QualityTier] == ["A", "B", "C"]
    assert Region.US == "US"
    assert Region.EU == "EU"


def test_ohlcv_prices_are_explicitly_unadjusted():
    assert ROWS[-1].price_basis == "unadjusted"
