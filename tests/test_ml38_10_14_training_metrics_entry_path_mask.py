from app.training.metrics import TrainingMetrics


def test_ml38_10_14_entry_path_mask_removes_low_quality_trade_predictions() -> None:
    payload = TrainingMetrics.apply_entry_path_quality_decision_mask(
        predicted_trade_flags=[1, 1, 1, 0],
        entry_path_quality_scores=[0.80, 0.40, 0.70, 0.20],
        stop_pressure_risk_scores=[0.20, 0.60, 0.30, 0.90],
        entry_path_quality_filter_enabled=True,
        entry_path_quality_min_threshold=0.65,
        stop_pressure_max_risk_score=0.55,
    )

    assert payload["entry_path_quality_filter_enabled"] is True
    assert payload["masked_predicted_trade_flags"] == [1, 0, 1, 0]
    assert payload["entry_path_quality_forced_no_trade_count"] == 1


def test_ml38_10_14_entry_path_mask_is_noop_when_disabled() -> None:
    payload = TrainingMetrics.apply_entry_path_quality_decision_mask(
        predicted_trade_flags=[1, 1, 0],
        entry_path_quality_scores=[0.10, 0.10, 0.10],
        stop_pressure_risk_scores=[0.90, 0.90, 0.90],
        entry_path_quality_filter_enabled=False,
        entry_path_quality_min_threshold=0.65,
        stop_pressure_max_risk_score=0.55,
    )

    assert payload["masked_predicted_trade_flags"] == [1, 1, 0]
    assert payload["entry_path_quality_filter_enabled"] is False

def test_ml38_10_14_entry_path_false_positive_count_is_separate_from_setup_mask() -> None:
    metrics = TrainingMetrics().compute(
        direction_probabilities=[
            [0.90, 0.05, 0.05],
            [0.90, 0.05, 0.05],
            [0.90, 0.05, 0.05],
            [0.05, 0.05, 0.90],
        ],
        direction_targets=[0, 0, 0, 2],
        tp_sl_probabilities=[0.5, 0.5, 0.5, 0.5],
        tp_sl_targets=[True, True, True, True],
        expected_move_predictions=[0.0, 0.0, 0.0, 0.0],
        expected_move_targets=[0.0, 0.0, 0.0, 0.0],
        opportunity_probabilities=[0.90, 0.90, 0.90, 0.10],
        opportunity_targets=[1, 0, 0, 0],
        opportunity_probability_threshold=0.65,
        setup_quality_scores=[0.80, 0.40, 0.80, 0.80],
        setup_quality_decision_mask_enabled=True,
        setup_quality_decision_mask_min_threshold=0.60,
        entry_path_quality_filter_enabled=True,
        entry_path_quality_scores=[0.80, 0.80, 0.40, 0.80],
        stop_pressure_risk_scores=[0.20, 0.20, 0.80, 0.20],
        entry_path_quality_min_threshold=0.65,
        stop_pressure_max_risk_score=0.55,
        training_objective="trade_two_stage",
    )

    assert metrics["raw_opportunity_false_positive_rate"] > metrics["opportunity_false_positive_rate"]
    assert metrics["setup_quality_mask_false_positive_removed_count"] == 1
    assert metrics["entry_path_quality_mask_false_positive_removed_count"] == 1
    assert metrics["opportunity_false_positive_count"] == 0
