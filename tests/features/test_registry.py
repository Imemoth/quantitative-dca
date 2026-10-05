from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
import yaml

from quant_dca.features.registry import (
    FeatureRegistry,
    FeatureRegistryError,
)
from quant_dca.types import QualityTier


CONFIG_PATH = Path(__file__).parents[2] / "configs" / "features_v1.yaml"


def test_v1_registry_is_controlled_and_excludes_security_identity():
    registry = FeatureRegistry.v1()

    assert registry.version == "features-v1"
    assert 50 <= len(registry.base_signal_names()) <= 100
    assert registry.panel_budget.registered_feature_count == len(registry.names())
    assert registry.panel_budget.reserved_interpretable_regime_slots == 5
    assert registry.panel_budget.reserved_unsupervised_regime_slots == 8
    assert registry.final_panel_size == 94
    assert 80 <= registry.final_panel_size <= 95
    assert len(registry.names()) == len(set(registry.names()))

    forbidden = {"ticker", "security_id", "isin", "entity_id"}
    exposed = set(registry.names()) | set(registry.base_signal_names())
    exposed |= {
        dependency.name
        for definition in registry
        for dependency in definition.raw_dependencies
    }
    assert forbidden.isdisjoint(exposed)


def test_v1_definitions_are_immutable_auditable_and_point_in_time():
    registry = FeatureRegistry.v1()
    definition = registry["return_20d_raw"]

    assert definition.domain == "price_trend"
    assert definition.base_signal == "return_20d"
    assert definition.lookback_sessions == 21
    assert definition.availability_rule == "next_eod_after_all_inputs_available"
    assert definition.quality_floor is QualityTier.C
    assert definition.transform == "raw"
    assert definition.formula == "adjusted_close_t / adjusted_close_t_minus_20 - 1"
    assert definition.normalization == "none"
    assert definition.applicability == "all_eligible_equities"
    assert definition.missing_policy == "preserve_missing"
    assert definition.raw_dependencies
    assert all(
        dependency.availability_field == "available_at"
        and dependency.join_rule == "available_at <= prediction_timestamp"
        and dependency.revision_policy == "as_of_vintage"
        for dependency in definition.raw_dependencies
    )

    with pytest.raises(FrozenInstanceError):
        definition.name = "changed"


def test_v1_contract_covers_regions_events_and_structural_missingness():
    registry = FeatureRegistry.v1()

    assert registry["policy_rate_change_3m_raw"].applicability == (
        "security_monetary_jurisdiction"
    )
    assert registry["days_to_announced_earnings_raw"].availability_rule == (
        "known_event_date_as_of_prediction_then_next_eod"
    )
    assert registry["net_debt_to_ebitda_raw"].applicability == (
        "non_financials_when_economically_meaningful"
    )
    assert registry["net_debt_to_ebitda_raw"].missing_policy == (
        "structural_missing_not_imputed"
    )
    assert registry["trailing_pe_sector_percentile"].normalization == (
        "eligible_sector_percentile_as_of"
    )
    assert registry["trailing_pe_own_history_zscore"].normalization == (
        "trailing_history_as_of"
    )
    assert registry["distance_52week_high_raw"].lookback_sessions == 252
    assert registry["drawdown_duration_sessions_raw"].lookback_sessions == 252
    assert registry["interest_coverage_raw"].missing_policy == (
        "structural_missing_not_imputed"
    )
    assert registry["share_dilution_yoy_raw"].formula
    assert registry["last_known_earnings_surprise_raw"].formula
    assert registry["vix_acceleration_raw"].formula


def test_momentum_universe_percentile_uses_historical_eligible_universe():
    definition = FeatureRegistry.v1()["momentum_universe_percentile"]

    assert definition.domain == "relative_strength"
    assert definition.formula == (
        "percentile_rank_return_120d_within_historical_eligible_universe"
    )
    assert definition.normalization == "eligible_universe_percentile_as_of"
    assert definition.applicability == "historical_eligible_universe_members"
    assert "universe.historical_membership" in {
        dependency.name for dependency in definition.raw_dependencies
    }


def test_liquidity_contract_uses_split_consistent_usd_turnover():
    registry = FeatureRegistry.v1()
    dollar_volume = registry["median_dollar_volume_20d_log"]
    amihud = registry["amihud_illiquidity_20d_log"]
    required = {
        "ohlcv.unadjusted_close",
        "ohlcv.original_unit_volume",
        "security.historical_currency",
        "fx.quotes",
    }

    for definition in (dollar_volume, amihud):
        dependencies = {item.name: item for item in definition.raw_dependencies}
        assert required <= dependencies.keys()
        assert dependencies["ohlcv.unadjusted_close"].value_basis == (
            "canonical_unadjusted_close"
        )
        assert dependencies["ohlcv.original_unit_volume"].value_basis == (
            "verified_original_share_units"
        )
        assert dependencies["ohlcv.original_unit_volume"].required_provenance == (
            "volume_basis=original_share_units",
        )
        assert dependencies["fx.quotes"].join_rule == (
            "fixing_at <= historical_eod and available_at <= historical_eod"
        )
        assert definition.applicability == "requires_pit_fx_conversion_to_usd"

    assert dollar_volume.formula == (
        "log1p_median_unadjusted_close_times_original_unit_volume_times_"
        "local_to_usd_fx_at_each_historical_eod_20"
    )
    assert amihud.formula == (
        "log1p_mean_abs_adjusted_economic_return_over_"
        "unadjusted_close_times_original_unit_volume_times_"
        "local_to_usd_fx_at_each_historical_eod_20"
    )


@pytest.mark.parametrize(
    "identity_alias",
    [
        "ticker_code",
        "issuer_ticker_code",
        "symbol",
        "cusip",
        "sedol",
        "figi",
        "internal_security_id",
        "entity_identifier",
    ],
)
def test_loader_rejects_direct_identity_aliases(
    tmp_path: Path, identity_alias: str
):
    payload = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    payload["features"][0]["formula"] = identity_alias
    config = tmp_path / "features.yaml"
    config.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    with pytest.raises(FeatureRegistryError, match="identity"):
        FeatureRegistry.from_yaml(config)


@pytest.mark.parametrize(
    "economic_term",
    [
        "security_region",
        "entity_value_growth",
        "symbolic_regression_score",
        "market_cap",
        "liquidity_class",
    ],
)
def test_identity_validation_does_not_reject_economic_terms(
    tmp_path: Path, economic_term: str
):
    payload = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    payload["features"][0]["formula"] = economic_term
    config = tmp_path / "features.yaml"
    config.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    assert FeatureRegistry.from_yaml(config)["return_5d_raw"].formula == economic_term


def test_loader_rejects_a_dependency_without_the_pit_join_rule(tmp_path: Path):
    config = tmp_path / "features.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "registry_version": "features-v1",
                    "panel_budget": {
                        "final_min": 1,
                        "final_max": 14,
                        "registered_feature_count": 1,
                        "reserved_interpretable_regime_slots": 5,
                        "reserved_unsupervised_regime_slots": 8,
                    },
                    "dependencies": {},
                    "features": [
                    {
                        "name": "bad_feature",
                        "domain": "price_trend",
                        "base_signal": "bad_signal",
                        "raw_dependencies": [
                            {
                                "name": "ohlcv.close",
                                "availability_field": "observation_date",
                                "join_rule": "observation_date <= prediction_date",
                                "revision_policy": "latest",
                                "value_basis": "raw_close",
                                "required_provenance": ["price_basis"],
                            }
                        ],
                        "lookback_sessions": 2,
                        "availability_rule": "next_eod_after_all_inputs_available",
                        "quality_floor": "C",
                        "transform": "raw",
                        "formula": "close_t / close_t_minus_1 - 1",
                        "normalization": "none",
                        "applicability": "all_eligible_equities",
                        "missing_policy": "preserve_missing",
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(FeatureRegistryError, match="available_at"):
        FeatureRegistry.from_yaml(config)


def test_loader_rejects_identity_dependencies_even_when_nested(tmp_path: Path):
    config = tmp_path / "features.yaml"
    config.write_text(
        """\
schema_version: 1
registry_version: features-v1
panel_budget:
  final_min: 1
  final_max: 14
  registered_feature_count: 1
  reserved_interpretable_regime_slots: 5
  reserved_unsupervised_regime_slots: 8
dependencies: {}
features:
  - name: disguised_identity
    domain: structural
    base_signal: issuer_key
    raw_dependencies:
      - name: security.ticker
        availability_field: available_at
        join_rule: available_at <= prediction_timestamp
        revision_policy: as_of_vintage
        value_basis: direct_identity
        required_provenance: [source]
    lookback_sessions: 0
    availability_rule: available_at_by_prediction_timestamp
    quality_floor: C
    transform: categorical
    formula: ticker
    normalization: categorical
    applicability: all_eligible_equities
    missing_policy: preserve_missing
""",
        encoding="utf-8",
    )

    with pytest.raises(FeatureRegistryError, match="identity"):
        FeatureRegistry.from_yaml(config)


def test_loader_rejects_provider_tier_assignments(tmp_path: Path):
    payload = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    payload["provider_tiers"] = {"example_vendor": "A"}
    config = tmp_path / "features.yaml"
    config.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    with pytest.raises(FeatureRegistryError, match="registry fields"):
        FeatureRegistry.from_yaml(config)
