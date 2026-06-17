from app.experiments.ml38_2_fv3_tuning_matrix import (
    ML382FV3TuningMatrix,
    ML38_6_CONFIDENCE_PROFIT_CONFIG_IDS,
)


def test_ml38_6_fv3_matrix_includes_confidence_profit_configs() -> None:
    payload = ML382FV3TuningMatrix().build()

    assert payload["missing_configs"] == []
    assert payload["confidence_profitability_stage"] == "ML38.6"
    assert payload["confidence_profit_config_count"] == 6
    assert payload["config_count"] == 20
    assert set(ML38_6_CONFIDENCE_PROFIT_CONFIG_IDS).issubset(set(payload["config_ids"]))
