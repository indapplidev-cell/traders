from app.experiments.ml38_2_fv3_tuning_matrix import (
    ML382FV3TuningMatrix,
    ML38_2_FV3_TUNING_CONFIG_IDS,
    ML38_6_CONFIDENCE_PROFIT_CONFIG_IDS,
    ML38_9_FLAT_BIAS_CONFIG_IDS,
)


def test_ml38_6_fv3_matrix_includes_confidence_profit_configs() -> None:
    payload = ML382FV3TuningMatrix().build()

    assert payload["missing_configs"] == []
    assert payload["confidence_profitability_stage"] == "ML38.6"
    assert payload["confidence_profit_config_count"] == len(ML38_6_CONFIDENCE_PROFIT_CONFIG_IDS)
    assert payload["confidence_profit_config_count"] == 6
    assert set(ML38_6_CONFIDENCE_PROFIT_CONFIG_IDS).issubset(set(payload["config_ids"]))


def test_fv3_matrix_count_matches_ml38_9_expanded_grid() -> None:
    payload = ML382FV3TuningMatrix().build()

    assert payload["flat_bias_stage"] == "ML38.9"
    assert payload["flat_bias_config_count"] == len(ML38_9_FLAT_BIAS_CONFIG_IDS)
    assert payload["flat_bias_config_count"] == 4
    assert payload["config_count"] == len(ML38_2_FV3_TUNING_CONFIG_IDS)
    assert payload["config_count"] == 24
    assert set(ML38_9_FLAT_BIAS_CONFIG_IDS).issubset(set(payload["config_ids"]))
