"""Synthetic contracts: no provider data, fitting, or economic validation."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import math

import pytest
import yaml

from quant_dca.features.normalize import PartitionRole
from quant_dca.types import FeatureValue, QualityTier, Region


def model():
    try:
        from quant_dca.regimes.interpretable import InterpretableRegimeModel
    except ModuleNotFoundError:
        pytest.fail("InterpretableRegimeModel is not implemented")
    return InterpretableRegimeModel.default()


STATES = ("EXPANSION_RISK_ON", "CORRECTION", "HIGH_VOL_STRESS", "CRISIS", "RECOVERY")
NAMES = ("broad_market_momentum_20d_raw", "vix_level_raw", "high_yield_spread_raw")
UNITS = dict(zip(NAMES, ("fractional_return", "index_points", "percentage_points")))
CURRENT = datetime(2023, 9, 5, 20, tzinfo=timezone.utc)
PRIOR = datetime(2023, 9, 1, 20, tzinfo=timezone.utc)


def scalars(trend=1., vol=-1., credit=-1.):
    return dict(zip(("market_trend", "vol_z", "credit_z"), (trend, vol, credit)))


def snapshot(values=(.05, 10., 2.), at=CURRENT, region=Region.US):
    return tuple(FeatureValue(
        feature=name, entity_id=None, observation_date=at.date().isoformat(),
        as_of=at, value=value, max_input_available_at=at, available_at=at,
        published_at=at, quality=QualityTier.B, source="synthetic", revision_id="v1",
        region=Region.GLOBAL if name == "vix_level_raw" else region,
    ) for name, value in zip(NAMES, values))


def request(**changes):
    args = dict(historical_inputs=snapshot(at=PRIOR), prediction_timestamp=CURRENT,
                current_eod=CURRENT, prior_eod=PRIOR, benchmark_exchange="XNYS",
                region=Region.US, partition_role=PartitionRole.TRAIN, feature_units=UNITS)
    args.update(changes)
    return args


@pytest.mark.parametrize("values,previous,want", [
    ((1., -1., -1.), None, "EXPANSION_RISK_ON"),
    ((-1., 0., 0.), None, "CORRECTION"),
    ((0., 2., 1.), None, "HIGH_VOL_STRESS"),
    ((-2., 3., 3.), None, "CRISIS"),
    ((1., 0., 0.), (-2., 3., 3.), "RECOVERY"),
])
def test_synthetic_reference_states_are_distinct(values, previous, want):
    result = model().explain(scalars(*values), previous=None if previous is None else scalars(*previous))
    assert tuple(result.probabilities) == STATES
    assert result.hard_state == want
    assert sum(result.probabilities.values()) == pytest.approx(1.)
    assert all(0 <= value <= 1 for value in result.probabilities.values())
    assert not result.pit_validated


def test_plan_scalar_example_has_no_provenance_claim_or_invented_recovery():
    estimator = model()
    result = estimator.explain({"market_trend": -1., "vol_z": 2., "credit_z": 1.5})
    assert estimator.predict_proba(scalars(-1., 2., 1.5)) == result.probabilities
    assert sum(result.probabilities.values()) == pytest.approx(1.)
    assert result.probabilities["RECOVERY"] == 0
    assert result.evidence == ()
    assert "uncalibrated" in result.explanation
    assert "fixed reference" in result.explanation


def test_score_explanation_reconstructs_literal_distance_and_deterministic_tie():
    result = model().explain(scalars())
    assert result.score_contributions["CORRECTION"] == dict(market_trend=-4., vol_z=-1., credit_z=-1.)
    assert result.scores["CORRECTION"] == -6.
    assert result.scores["EXPANSION_RISK_ON"] == 0.
    tied = model().explain(scalars(0., -.5, -.5))
    assert tied.probabilities["EXPANSION_RISK_ON"] == tied.probabilities["CORRECTION"]
    assert tied.hard_state == "EXPANSION_RISK_ON"


@pytest.mark.parametrize("previous,current", [
    ((0., 0., 0.), (1., 0., 0.)),  # no preceding stress
    ((-2., 3., 3.), (0., 0., 0.)),  # no positive rebound
    ((-2., 1., 1.), (1., 2., 0.)),  # one risk dimension worsens
    ((-2., 1., 1.), (1., 1., 1.)),  # no easing
])
def test_recovery_requires_stress_positive_rebound_and_easing(previous, current):
    result = model().explain(scalars(*current), previous=scalars(*previous))
    assert not result.recovery_eligible
    assert result.probabilities["RECOVERY"] == 0


@pytest.mark.parametrize("bad", [None, math.nan, math.inf, -math.inf, True, "1"])
def test_missing_nonfinite_and_nonnumeric_scalar_fail_closed(bad):
    with pytest.raises((ValueError, TypeError)):
        model().predict_proba(scalars(vol=bad))


@pytest.mark.parametrize("name", ["ticker", "target_return_20d", "return_5d", "unknown"])
def test_scalar_schema_rejects_identity_target_and_unknown_inputs(name):
    with pytest.raises(ValueError, match="SCHEMA"):
        model().predict_proba({**scalars(), name: 1.})


def test_extreme_finite_inputs_have_stable_probabilities():
    result = model().explain(scalars(1e308, -1e308, 1e308))
    assert all(math.isfinite(value) for value in result.probabilities.values())
    assert sum(result.probabilities.values()) == pytest.approx(1.)
    assert result.normalized_inputs == scalars(4., -4., 4.)


def test_clipping_cannot_hide_worsening_risk_in_recovery_gate():
    result = model().explain(scalars(1., 7., 0.), previous=scalars(-1., 6., 1.))
    assert not result.recovery_eligible
    assert result.probabilities["RECOVERY"] == 0.


def test_explanation_preserves_unclipped_gate_inputs_and_failure_reason():
    result = model().explain(scalars(1., 7., 0.), previous=scalars(-1., 6., 1.))
    assert result.raw_inputs == scalars(1., 7., 0.)
    assert result.previous_raw_inputs == scalars(-1., 6., 1.)
    assert result.recovery_checks == {
        "history_present": True, "prior_stress": True, "positive_rebound": True,
        "risk_nonincreasing": False, "risk_easing": True,
    }
    with pytest.raises(TypeError):
        result.recovery_checks["risk_nonincreasing"] = True


def test_missing_scalar_feature_is_not_silently_neutral():
    with pytest.raises(ValueError, match="SCHEMA"):
        model().predict_proba({"market_trend": 1., "vol_z": 0.})


def test_evidenced_us_recovery_keeps_both_snapshots_and_config_lineage():
    rows = snapshot((.05, 20., 4.))
    past = snapshot((-.1, 50., 10.), at=PRIOR)
    result = model().predict(rows, **request(historical_inputs=past))
    assert result.hard_state == "RECOVERY"
    assert result.pit_validated
    assert result.evidence == (*rows, *past)
    assert result.prediction_timestamp == CURRENT
    assert result.region is Region.US
    assert result.partition_role is PartitionRole.TRAIN
    assert len(result.config_hash) == 64
    with pytest.raises(TypeError):
        result.probabilities["CRISIS"] = 1.
    with pytest.raises(TypeError):
        result.configuration["weights"]["vol_z"] = 99.


def test_extreme_finite_canonical_values_cannot_overflow_fixed_scaling():
    result = model().predict(snapshot((1e308, 1e308, 1e308)), **request())
    assert sum(result.probabilities.values()) == pytest.approx(1.)
    assert result.normalized_inputs == scalars(4., 4., 4.)


def test_evidenced_recovery_gate_uses_raw_changes_before_clipping():
    result = model().predict(snapshot((.05, 90., 4.)),
        **request(historical_inputs=snapshot((-.05, 80., 6.), at=PRIOR)))
    assert not result.recovery_eligible


def test_eu_snapshot_uses_only_previously_available_global_vix():
    close = datetime(2023, 9, 5, 15, 30, tzinfo=timezone.utc)
    past = datetime(2023, 9, 4, 15, 30, tzinfo=timezone.utc)
    rows = list(snapshot(at=close, region=Region.EU))
    # Last US value known before this EU EOD, not the forthcoming US close.
    rows[1] = replace(rows[1], observation_date="2023-09-01", available_at=PRIOR,
                      published_at=PRIOR, max_input_available_at=PRIOR)
    result = model().predict(rows, **request(current_eod=close, prior_eod=past,
        prediction_timestamp=close, historical_inputs=snapshot(at=past, region=Region.EU),
        region=Region.EU, benchmark_exchange="XETR", partition_role=PartitionRole.VALIDATION))
    assert result.hard_state == "EXPANSION_RISK_ON"
    rows[1] = replace(rows[1], available_at=CURRENT, published_at=CURRENT, max_input_available_at=CURRENT)
    with pytest.raises(ValueError, match="PIT_LEAKAGE"):
        model().predict(rows, **request(current_eod=close, prior_eod=past,
            prediction_timestamp=close, historical_inputs=snapshot(at=past, region=Region.EU),
            region=Region.EU, benchmark_exchange="XETR"))


class UnreadableFloat(float):
    def __float__(self):
        raise AssertionError("forbidden value consumed")


@pytest.mark.parametrize("role", [PartitionRole.OUTER_OOS, PartitionRole.HOLDOUT])
def test_forbidden_partition_is_rejected_before_input_iteration(role):
    def forbidden():
        raise AssertionError("partition read")
        yield
    with pytest.raises(ValueError, match="PARTITION"):
        model().predict(forbidden(), **request(partition_role=role))


@pytest.mark.parametrize("year", [2009, 2024])
def test_development_boundary_rejects_metadata_without_consuming_values(year):
    # Only forbidden metadata is constructed, never post-development market data.
    rows = snapshot((UnreadableFloat(1), 20., 4.))
    with pytest.raises(ValueError, match="DEVELOPMENT"):
        model().predict(rows, **request(prediction_timestamp=CURRENT.replace(year=year)))


@pytest.mark.parametrize("field", ["available_at", "max_input_available_at", "as_of", "published_at", "revised_at"])
def test_every_source_clock_checked_before_any_current_or_prior_value(field):
    rows = snapshot((UnreadableFloat(1), 20., 4.))
    past = list(snapshot(at=PRIOR))
    past[2] = replace(past[2], **{field: CURRENT})
    with pytest.raises(ValueError, match="PIT_|SNAPSHOT"):
        model().predict(rows, **request(historical_inputs=past))


@pytest.mark.parametrize("changes", [
    {"feature": "target_return_20d"}, {"feature": "ticker"}, {"feature": "unregistered"},
    {"entity_id": "SECURITY"}, {"region": Region.EU}, {"source": ""},
    {"revision_id": ""}, {"observation_date": "2023-09-06"},
    {"observation_date": "2024-01-01"},
])
def test_evidenced_input_metadata_fails_before_other_numeric_values(changes):
    rows = list(snapshot((UnreadableFloat(1), 20., 4.)))
    rows[2] = replace(rows[2], **changes)
    with pytest.raises(ValueError):
        model().predict(rows, **request())


@pytest.mark.parametrize("bad", [None, math.nan, math.inf])
def test_missing_or_nonfinite_past_stress_is_not_imputed(bad):
    with pytest.raises(ValueError, match="FINITE"):
        model().predict(snapshot(), **request(historical_inputs=snapshot((0., bad, 4.), at=PRIOR)))


def test_historical_evidence_is_required_and_cannot_be_cherry_picked():
    with pytest.raises(ValueError, match="HISTORY"):
        model().predict(snapshot(), **request(historical_inputs=None))
    wrong = PRIOR - timedelta(days=1)
    with pytest.raises(ValueError, match="PRIOR_EOD"):
        model().predict(snapshot(), **request(prior_eod=wrong, historical_inputs=snapshot(at=wrong)))


@pytest.mark.parametrize("changes", [
    {"current_eod": CURRENT - timedelta(minutes=1)},
    {"benchmark_exchange": "XETR"},
    {"feature_units": {**UNITS, "high_yield_spread_raw": "basis_points"}},
    {"feature_units": {}}, {"region": "US"}, {"partition_role": "train"},
    {"prediction_timestamp": CURRENT.replace(tzinfo=None)},
])
def test_explicit_boundary_contract_is_strict(changes):
    with pytest.raises((ValueError, TypeError)):
        model().predict(snapshot(), **request(**changes))


def test_evidenced_schema_rejects_duplicate_or_missing_feature():
    rows = snapshot()
    for bad in (rows[:-1], (*rows, rows[0])):
        with pytest.raises(ValueError, match="SCHEMA"):
            model().predict(bad, **request())


def test_custom_config_controls_scores_and_hash_without_fitting(tmp_path):
    from quant_dca.regimes.interpretable import InterpretableRegimeModel
    from pathlib import Path
    config = yaml.safe_load(Path("configs/regimes_v1.yaml").read_text())
    original = model().explain(scalars())
    config["weights"]["market_trend"] = 2.
    path = tmp_path / "regimes.yaml"
    path.write_text(yaml.safe_dump(config))
    changed = InterpretableRegimeModel.from_yaml(path).explain(scalars())
    assert changed.scores["CORRECTION"] == -10.
    assert changed.config_hash != original.config_hash


@pytest.mark.parametrize("key,value", [
    ("temperature", 0.), ("temperature", math.inf), ("clip", -1.),
    ("recovery_lookback_sessions", 2), ("weights", {"ticker": 1.}),
    ("prototypes", {}), ("unknown", 1),
])
def test_invalid_configuration_fails_closed(tmp_path, key, value):
    from pathlib import Path
    from quant_dca.regimes.interpretable import InterpretableRegimeModel
    config = yaml.safe_load(Path("configs/regimes_v1.yaml").read_text())
    config[key] = value
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml.safe_dump(config))
    with pytest.raises((ValueError, TypeError)):
        InterpretableRegimeModel.from_yaml(path)
