from app.experiments.label_grid_experiment_runner import LabelGridExperimentRunner
from app.labels.label_quality_grid import LabelQualityGridConfig


def test_ml38_10_14_2_candidate_report_propagates_profit_entry_path_audit() -> None:
    runner = LabelGridExperimentRunner()
    label_config = LabelQualityGridConfig(
        config_id="test_epq_profit",
        label_version="test_epq_profit",
        horizon=12,
        threshold=0.60,
        take_profit_atr=1.2,
        stop_loss_atr=1.2,
        flat_threshold=0.60,
        description="Unit test config for ML38.10.14.2 candidate propagation.",
        risk_note="Test-only config. No live trading, no auto-activation.",
    )

    result = runner._build_candidate_result(
        label_config=label_config,
        quality_payload={
            "quality_status": "REJECTED",
            "candidate_selection": {"candidate_status": "REJECTED"},
            "test_metrics": {
                "entry_path_quality_filter_enabled": True,
                "entry_path_quality_min_threshold": 0.70,
                "stop_pressure_max_risk_score": 0.45,
                "entry_path_quality_masked_row_count": 100,
                "entry_path_quality_forced_no_trade_count": 7,
                "entry_path_quality_mask_trade_prediction_removed_count": 7,
                "entry_path_quality_mask_false_positive_removed_count": 5,
                "entry_path_quality_filter_summary": {"rows_blocked_by_entry_path_filter": 100},
                "entry_path_quality_filter_diagnostics": {"diagnostic_version": "ml38.10.14"},
            },
            "profit_aware_diagnostics": {
                "entry_path_prediction_filter_summary": {
                    "blocked_by_high_stop_pressure_count": 2,
                    "removed_false_positive_count": 1,
                    "stop_pressure_effectiveness_audit": {
                        "diagnostic_version": "ml38.10.14.2",
                        "status": "STOP_PRESSURE_REMOVED_FALSE_POSITIVES",
                    },
                },
                "stop_pressure_effectiveness_audit": {
                    "diagnostic_version": "ml38.10.14.2",
                    "status": "STOP_PRESSURE_REMOVED_FALSE_POSITIVES",
                },
            },
        },
        class_distribution={},
        gate_policy_summary={},
    )

    payload = result.to_dict()
    assert payload["entry_path_quality_filter_enabled"] is True
    assert payload["entry_path_quality_mask_trade_prediction_removed_count"] == 7
    assert payload["entry_path_quality_mask_false_positive_removed_count"] == 5
    assert payload["entry_path_prediction_filter_summary"]["blocked_by_high_stop_pressure_count"] == 2
    assert payload["stop_pressure_effectiveness_audit"]["status"] == "STOP_PRESSURE_REMOVED_FALSE_POSITIVES"
