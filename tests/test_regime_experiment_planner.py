from app.experiments.regime_experiment_planner import RegimeExperimentPlanner


def test_regime_experiment_planner_ready_false_when_regime_data_unavailable() -> None:
    payload = RegimeExperimentPlanner().build_plan(
        symbol="BTCUSDT",
        interval="15m",
        start_date="2025-01-01",
        regime_data_available=False,
    )

    assert payload["ready_for_real_regime_training"] is False
    assert payload["reason"] == "regime data unavailable in dataset/features"
    assert payload["missing_data"]
    assert payload["recommendations"]


def test_regime_experiment_planner_ready_true_when_regime_data_available() -> None:
    payload = RegimeExperimentPlanner().build_plan(
        symbol="BTCUSDT",
        interval="15m",
        start_date="2025-01-01",
        regime_data_available=True,
    )

    assert payload["ready_for_real_regime_training"] is True
    assert payload["missing_data"] == []
    assert payload["recommendations"]
