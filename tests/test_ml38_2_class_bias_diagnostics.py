from app.diagnostics.class_bias_diagnostics import ClassBiasDiagnostics


def test_ml38_2_class_bias_diagnostics_detects_flat_bias_and_down_blindness() -> None:
    payload = ClassBiasDiagnostics().analyze(
        predicted_distribution={"DOWN": 0.05, "FLAT": 0.62, "UP": 0.33},
        actual_distribution={"DOWN": 0.39, "FLAT": 0.24, "UP": 0.37},
        symbol="SOLUSDT",
        config_id="lv2_h12_thr05_tp15_sl10",
    )

    assert payload["flat_bias_detected"] is True
    assert payload["down_blindness_detected"] is True
    assert payload["symbol_bias_severity"] == "CRITICAL"
    assert payload["dominant_predicted_class"] == "FLAT"
    assert payload["dominant_actual_class"] == "DOWN"


def test_ml38_2_class_bias_diagnostics_returns_ok_for_balanced_distributions() -> None:
    payload = ClassBiasDiagnostics().analyze(
        predicted_distribution={"DOWN": 0.35, "FLAT": 0.27, "UP": 0.38},
        actual_distribution={"DOWN": 0.36, "FLAT": 0.25, "UP": 0.39},
    )

    assert payload["flat_bias_detected"] is False
    assert payload["down_blindness_detected"] is False
    assert payload["symbol_bias_severity"] == "OK"
