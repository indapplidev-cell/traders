from app.diagnostics.diagnostics_service import DiagnosticsService


def test_probability_report_contains_bounded_calibration_payload(tmp_path) -> None:
    service = DiagnosticsService(
        dataset_builder=object(),
        feature_repository=object(),
        model_registry_repository=object(),
        artifact_storage=object(),
        reports_dir=tmp_path,
    )
    rows = [
        {
            "actual_label": "FLAT",
            "predicted_label": "UP",
            "prob_up": 0.39,
            "prob_down": 0.34,
            "prob_flat": 0.27,
            "confidence": 0.39,
        },
        {
            "actual_label": "DOWN",
            "predicted_label": "UP",
            "prob_up": 0.41,
            "prob_down": 0.38,
            "prob_flat": 0.21,
            "confidence": 0.41,
        },
        {
            "actual_label": "UP",
            "predicted_label": "UP",
            "prob_up": 0.62,
            "prob_down": 0.22,
            "prob_flat": 0.16,
            "confidence": 0.62,
        },
    ]
    service._build_prediction_rows = lambda **_: [dict(row) for row in rows]

    payload = service.probability_report(
        model_version="mv1",
        symbol="SOLUSDT",
        interval="15m",
        horizon_candles=12,
        feature_version="fv3_candle_ta_context",
        label_version="lv9_h12_thr06_tp12_sl12_bc",
        label_config={
            "config_id": "lv9_h12_thr06_tp12_sl12_bc",
            "decision_calibration_enabled": True,
            "decision_calibration_mode": "bounded_calibration",
            "decision_flat_if_max_prob_below": 0.43,
            "decision_flat_if_margin_below": 0.065,
            "decision_min_direction_prob": 0.405,
            "decision_min_up_down_margin": 0.035,
            "decision_fallback_to_raw": True,
            "decision_max_flat_ratio": 0.45,
            "decision_max_dominant_class_ratio": 0.75,
            "decision_min_down_ratio_when_actual_down_high": 0.12,
            "decision_min_up_ratio_when_actual_up_high": 0.12,
            "decision_require_non_worse_baseline_edge": True,
            "decision_baseline_edge_tolerance": 0.0,
        },
    )

    assert "bounded_calibrated_decision_selection" in payload
    assert "prediction_decision_source" in payload
    assert "raw_probability_diagnostics" in payload
    assert "calibrated_probability_diagnostics" in payload
    assert "calibrated_decision_diagnostics" in payload
    assert payload["bounded_calibrated_decision_selection"]["enabled"] is True
    assert payload["prediction_decision_source"].startswith("raw_argmax_fallback")
