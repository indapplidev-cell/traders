from app.diagnostics.diagnostics_service import DiagnosticsService


def test_probability_report_uses_calibrated_decision_layer(tmp_path) -> None:
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
        label_version="lv8_h12_thr06_tp12_sl12_cd",
        label_config={
            "config_id": "lv8_h12_thr06_tp12_sl12_cd",
            "decision_calibration_enabled": True,
            "decision_flat_if_max_prob_below": 0.42,
            "decision_flat_if_margin_below": 0.06,
            "decision_min_direction_prob": 0.40,
            "decision_min_up_down_margin": 0.03,
        },
    )

    assert payload["prediction_decision_source"] == "calibrated_decision_layer"
    assert "raw_probability_diagnostics" in payload
    assert "calibrated_decision_diagnostics" in payload
    assert (
        payload["predicted_direction_ratios"]["FLAT"]
        > payload["raw_probability_diagnostics"]["predicted_direction_ratios"]["FLAT"]
    )
