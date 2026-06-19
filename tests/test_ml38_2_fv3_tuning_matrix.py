from app.experiments.ml38_2_fv3_tuning_matrix import (
    ML382FV3TuningMatrix,
    ML38_2_FEATURE_VERSION,
)


def test_ml38_2_fv3_tuning_matrix_contains_fv4_activation_and_keeps_core_grid() -> None:
    payload = ML382FV3TuningMatrix().build()

    assert payload["feature_version"] == ML38_2_FEATURE_VERSION
    assert payload["config_count"] >= 6
    assert payload["missing_configs"] == []
    assert payload["required_symbols"] == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    assert all(item["feature_version"] == ML38_2_FEATURE_VERSION for item in payload["configs"])
    assert {item["horizon"] for item in payload["configs"]} >= {8, 12, 16}
    assert payload["book_setup_context_stage"] == "ML38.9.8"
    assert payload["book_setup_context_config_count"] == 3
