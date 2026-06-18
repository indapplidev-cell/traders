from app.diagnostics.class_bias_diagnostics import ClassBiasDiagnostics


def test_ml38_9_1_class_bias_detects_up_dominance_flat_underprediction_and_down_blindness() -> None:
    payload = ClassBiasDiagnostics().analyze(
        symbol="SOLUSDT",
        config_id="lv6_h12_thr06_tp12_sl12_ba",
        predicted_distribution={"UP": 0.90, "DOWN": 0.095, "FLAT": 0.005},
        actual_distribution={"UP": 0.40, "DOWN": 0.36, "FLAT": 0.24},
    )

    assert payload["diagnostic_version"] == "ml38_9_1"
    assert payload["up_dominance_detected"] is True
    assert payload["flat_underprediction_detected"] is True
    assert payload["down_blindness_detected"] is True
    assert payload["bias_gate_failed"] is True
    assert payload["symbol_bias_severity"] == "CRITICAL"
    assert "up_dominance_detected" in payload["bias_rejection_reasons"]
    assert "flat_underprediction_detected" in payload["bias_rejection_reasons"]
    assert "down_blindness_detected" in payload["bias_rejection_reasons"]
