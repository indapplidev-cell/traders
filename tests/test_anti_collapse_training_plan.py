from app.training.anti_collapse_training_plan import AntiCollapseTrainingPlan


def test_anti_collapse_training_plan_contains_ml30_controls() -> None:
    payload = AntiCollapseTrainingPlan().build_plan()

    assert payload["plan_version"] == "ml30"
    assert payload["class_weights_supported"] is True
    assert payload["prediction_distribution_gate"]["max_predicted_class_share"] == 0.70
    assert payload["recommended_thresholds"]["min_prediction_margin"] == 0.05
    assert payload["approved_for_live_trading"] is False
    assert payload["approved_for_auto_activation"] is False
    assert payload["orders_enabled"] is False
    assert payload["traders_core_connected"] is False
