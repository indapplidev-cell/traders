from app.diagnostics.diagnostics_service import DiagnosticsService


def test_probability_report_includes_decision_policy_grid_diagnostics(tmp_path) -> None:
    service = DiagnosticsService(
        dataset_builder=object(),
        feature_repository=object(),
        model_registry_repository=object(),
        artifact_storage=object(),
        reports_dir=tmp_path,
    )
    rows = [
        {
            "actual_label": "DOWN",
            "predicted_label": "UP",
            "prob_up": 0.36,
            "prob_down": 0.34,
            "prob_flat": 0.30,
            "confidence": 0.36,
        },
        {
            "actual_label": "FLAT",
            "predicted_label": "UP",
            "prob_up": 0.35,
            "prob_down": 0.32,
            "prob_flat": 0.33,
            "confidence": 0.35,
        },
        {
            "actual_label": "UP",
            "predicted_label": "UP",
            "prob_up": 0.40,
            "prob_down": 0.39,
            "prob_flat": 0.21,
            "confidence": 0.40,
        },
    ]
    service._build_prediction_rows = lambda **_: [dict(row) for row in rows]

    payload = service.probability_report(
        model_version="mv1",
        symbol="SOLUSDT",
        interval="15m",
        horizon_candles=12,
        feature_version="fv3_candle_ta_context",
        label_version="lv10_h12_thr06_tp12_sl12_dp",
        label_config={
            "config_id": "lv10_h12_thr06_tp12_sl12_dp",
            "decision_calibration_enabled": True,
            "decision_calibration_mode": "bounded_calibration",
            "decision_fallback_to_raw": True,
            "decision_policy_grid_enabled": True,
            "decision_policy_grid_stage": "ML38.9.5",
        },
    )

    assert payload["decision_policy_grid_diagnostics"]["diagnostic_version"] == "ml38_9_5"
    assert payload["prediction_decision_source"].startswith("decision_policy_grid:")


def test_decision_policy_selected_metrics_are_top_level_source() -> None:
    candidate = {
        "model_accuracy": 0.24,
        "baseline_accuracy": 0.39,
        "baseline_edge": -0.15,
        "decision_policy_grid_diagnostics": {
            "selected_decision_source": "decision_policy_grid:raw_argmax",
            "selected_policy": {
                "policy_id": "raw_argmax",
                "accuracy": 0.38,
                "baseline_accuracy": 0.39,
                "baseline_edge": -0.01,
                "predicted_ratios": {"DOWN": 0.07, "FLAT": 0.0, "UP": 0.93},
                "actual_ratios": {"DOWN": 0.36, "FLAT": 0.24, "UP": 0.40},
            },
        },
    }

    from app.diagnostics.decision_policy_grid import apply_selected_decision_policy_metrics

    updated = apply_selected_decision_policy_metrics(candidate)

    assert updated["model_accuracy"] == 0.38
    assert updated["baseline_edge"] == -0.01
