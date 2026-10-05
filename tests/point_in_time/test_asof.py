"""Point-in-time selection must fail closed when history is ambiguous."""
from datetime import datetime, timedelta, timezone, tzinfo

import pytest

from quant_dca.point_in_time.asof import assert_pit_safe, latest_known
from quant_dca.types import FeatureValue, Observation, QualityTier


BASE = datetime(2020, 3, 6, 12, tzinfo=timezone.utc)


def stamp(days: int = 0) -> datetime:
    return BASE + timedelta(days=days)


def observation(**changes: object) -> Observation:
    values = dict(
        series="CPI",
        entity_id="US",
        observation_date="2020-02-29",
        value=4.0,
        available_at=stamp(),
        published_at=stamp(),
        quality=QualityTier.A,
        source="fixture",
        revision_id="v1",
    )
    return Observation(**(values | changes))


def feature(**changes: object) -> FeatureValue:
    values = dict(
        feature="cpi_yoy",
        entity_id="US-1",
        observation_date="2020-02-29",
        as_of=stamp(1),
        value=2.3,
        max_input_available_at=stamp(),
        available_at=stamp(1),
        quality=QualityTier.A,
        source="fixture",
        revision_id="v1",
    )
    return FeatureValue(**(values | changes))


def test_latest_known_uses_historical_vintage_from_minimal_dicts():
    rows = [
        {"value": 4.0, "available_at": stamp()},
        {"value": 3.9, "available_at": stamp(28)},
    ]
    assert latest_known(rows, stamp(9))["value"] == 4.0


def test_latest_known_uses_latest_revision_known_at_cutoff():
    rows = [
        observation(),
        observation(value=4.1, revision_id="v2", revised_at=stamp(2), available_at=stamp(2)),
        observation(value=3.9, revision_id="v3", revised_at=stamp(28), available_at=stamp(28)),
    ]
    assert latest_known(rows, stamp(9)).value == 4.1


def test_latest_known_compares_aware_offsets_as_absolute_instants():
    equivalent = stamp(2).astimezone(timezone(timedelta(hours=2)))
    rows = [observation(), observation(value=4.1, revision_id="v2", revised_at=equivalent,
                                       available_at=equivalent)]
    assert latest_known(rows, stamp(2)).value == 4.1


def test_latest_known_rejects_mixed_observation_periods_before_selection():
    rows = [observation(), observation(observation_date="2020-03-31", available_at=stamp(28))]
    with pytest.raises(ValueError, match="PIT_MIXED_GROUP"):
        latest_known(rows, stamp(1))


def test_latest_known_rejects_mixed_series_or_entities():
    for changed in (observation(series="GDP"), observation(entity_id="EU")):
        with pytest.raises(ValueError, match="PIT_MIXED_GROUP"):
            latest_known([observation(), changed], stamp(1))


def test_latest_known_rejects_partially_specified_group_dicts():
    rows = [
        {"series": "CPI", "entity_id": "US", "observation_date": "2020-02-29",
         "value": 4.0, "available_at": stamp()},
        {"value": 4.1, "available_at": stamp(1)},
    ]
    with pytest.raises(ValueError, match="PIT_AMBIGUOUS_GROUP"):
        latest_known(rows, stamp(2))


def test_latest_known_rejects_ambiguous_tied_vintages_without_ordering_them_by_id():
    rows = [
        observation(value=4.1, revision_id="z-last", revised_at=stamp(2), available_at=stamp(2)),
        observation(value=4.2, revision_id="a-first", revised_at=stamp(2), available_at=stamp(2)),
    ]
    with pytest.raises(ValueError, match="PIT_AMBIGUOUS_VINTAGE"):
        latest_known(rows, stamp(3))


def test_latest_known_accepts_an_exact_duplicate_deterministically():
    row = {"value": 4.0, "available_at": stamp()}
    assert latest_known([row, dict(row)], stamp()) is row


def test_revision_timestamp_breaks_same_availability_tie():
    rows = [
        observation(value=4.0, revision_id="z", revised_at=stamp(1), available_at=stamp(2)),
        observation(value=4.1, revision_id="a", revised_at=stamp(2), available_at=stamp(2)),
    ]
    assert latest_known(rows, stamp(2)).value == 4.1


@pytest.mark.parametrize(
    "row",
    [
        {"value": 4.0},
        {"value": 4.0, "available_at": "2020-03-06T12:00:00Z"},
        {"value": 4.0, "available_at": BASE.replace(tzinfo=None)},
        {"value": 4.0, "available_at": stamp(), "published_at": stamp(1)},
        {"value": 4.0, "available_at": stamp(), "revised_at": stamp(1)},
        {"value": 4.0, "available_at": stamp(2), "published_at": stamp(1),
         "revised_at": stamp()},
    ],
    ids=["missing", "string", "naive", "before-publication", "before-revision", "revision-before-publication"],
)
def test_latest_known_rejects_invalid_or_inconsistent_chronology(row):
    with pytest.raises((TypeError, ValueError), match="PIT_INVALID"):
        latest_known([row], stamp(3))


def test_latest_known_rejects_invalid_cutoff_and_no_known_vintage():
    with pytest.raises(ValueError, match="as_of"):
        latest_known([{"value": 4.0, "available_at": stamp()}], stamp().replace(tzinfo=None))
    with pytest.raises(LookupError, match="PIT_NO_KNOWN_VINTAGE"):
        latest_known([{"value": 4.0, "available_at": stamp(2)}], stamp())


def test_future_datetime_feature_is_hard_failure():
    with pytest.raises(ValueError, match="PIT_LEAKAGE"):
        assert_pit_safe([stamp(10)], stamp(9))


def test_actual_feature_value_is_safe_when_value_and_inputs_were_available():
    assert_pit_safe([feature()], stamp(2))


@pytest.mark.parametrize(
    "unsafe",
    [
        feature(available_at=stamp(3)),
        feature(max_input_available_at=stamp(3)),
        feature(as_of=stamp(3)),
        feature(available_at=stamp(1), max_input_available_at=stamp(2)),
        feature(as_of=stamp(), max_input_available_at=stamp(1)),
        feature(as_of=stamp(), available_at=stamp(1)),
    ],
    ids=["feature-after-prediction", "input-after-prediction", "as-of-after-prediction",
         "input-after-feature", "input-after-feature-as-of", "feature-after-feature-as-of"],
)
def test_feature_timestamp_leakage_is_a_hard_failure(unsafe):
    with pytest.raises(ValueError, match="PIT_LEAKAGE"):
        assert_pit_safe([unsafe], stamp(2))


def test_offline_computation_may_occur_after_prediction():
    assert_pit_safe([feature(computed_at=stamp(30))], stamp(2))


def test_assert_pit_safe_rejects_naive_or_invalid_timestamps():
    with pytest.raises(ValueError, match="prediction_timestamp"):
        assert_pit_safe([], stamp().replace(tzinfo=None))
    with pytest.raises(ValueError, match="PIT_INVALID_TIMESTAMP"):
        assert_pit_safe([stamp().replace(tzinfo=None)], stamp())
    with pytest.raises(TypeError, match="PIT_INVALID_TIMESTAMP"):
        assert_pit_safe([{"available_at": "today"}], stamp())


def test_assert_pit_safe_rejects_inconsistent_feature_chronology():
    row = feature(published_at=stamp(2), available_at=stamp(1))
    with pytest.raises(ValueError, match="PIT_INVALID_CHRONOLOGY"):
        assert_pit_safe([row], stamp(3))


class NoOffset(tzinfo):
    def utcoffset(self, dt):
        return None


def test_timezone_object_without_offset_is_not_aware():
    bad = stamp().replace(tzinfo=NoOffset())
    with pytest.raises(ValueError, match="PIT_INVALID_TIMESTAMP"):
        assert_pit_safe([bad], stamp())
