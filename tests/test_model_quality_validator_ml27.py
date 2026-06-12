from app.diagnostics.gap_quality_diagnostics import GapQualityDiagnostics
from app.evaluation.model_quality_validator import QUALITY_REJECTED, validate_model_quality


def test_model_quality_validator_ml27_adds_new_sections_and_specific_reasons() -> None:
    result = validate_model_quality(
        training_summary={
            "model_version": "ml_candle_mlp_v1_2026_06_12_040449",
            "run_id": "train_ml_candle_mlp_v1_2026_06_12_040449",
            "dataset_summary": {
                "dataset_rows": 50402,
                "train_rows": 28985,
                "validation_rows": 11520,
                "test_rows": 9897,
            },
            "test_metrics": {"accuracy": 0.3724360917449732},
            "real_training_executed": True,
            "sample_mode": False,
        },
        baseline_summary={"baselines": {"majority_class": {"test": {"accuracy": 0.3699100737597252}}}},
        probability_diagnostics={
            "actual_direction_counts": {"UP": 3661, "DOWN": 3787, "FLAT": 2449},
            "predicted_direction_counts": {"UP": 8516, "DOWN": 421, "FLAT": 960},
            "avg_prob_up": 0.35053143812825466,
            "avg_prob_down": 0.3242517144370226,
            "avg_prob_flat": 0.3252168477448813,
            "max_prob_q90": 0.3655545234680176,
            "margin_q90": 0.04313697814941406,
            "margin_q50": 0.020096540451049805,
            "rows_above_thresholds": {"0.45": 0},
        },
        calibration_summary={"calibration_status": "ACCEPTABLE"},
        profit_aware_summary={
            "gate_results": [
                {"gate_type": "max_prob", "threshold": 0.34, "resolved_signal_count": 615, "total_r": -385.25, "profit_factor": 0.916},
                {"gate_type": "max_prob", "threshold": 0.36, "resolved_signal_count": 164, "total_r": -95.13, "profit_factor": 0.918},
            ]
        },
        walk_forward_summary={
            "summary": {
                "fold_count": 48,
                "profitable_fold_ratio": 0.6153846153846154,
                "global_total_r": -28.888598120001276,
                "global_profit_factor": 0.9888248912688763,
                "total_test_signal_count": 4756,
            }
        },
        gate_policy_replay_summary={"gate_policy_replay_status": "SAMPLE_ONLY", "total_records": 5, "valid_records": 4, "invalid_records": 1},
        gap_quality_summary=GapQualityDiagnostics().analyze(
            symbol="BTCUSDT",
            interval="15m",
            start_date="2025-01-01",
            end_date="2026-06-12",
            gap_count=79,
        ),
        label_config_summary={"label_version": "lv1", "horizon_candles": 8},
        feature_config_summary={"feature_version": "fv1"},
    )

    payload = result.to_dict()

    assert payload["quality_status"] == QUALITY_REJECTED
    assert "gap_quality" in payload
    assert "anti_collapse" in payload
    assert "candidate_selection" in payload
    assert "quality_gates_summary" in payload
    assert any(reason in payload["reasons"] for reason in ("gap_quality_not_clean", "directional_bias_up", "low_margin_detected"))
    assert "walk_forward_unstable" in payload["reasons"]
