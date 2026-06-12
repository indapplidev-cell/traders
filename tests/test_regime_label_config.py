import json

from app.labels.regime_label_config import RegimeLabelConfigPlanner


def test_regime_label_config_planner_returns_multiple_unique_configs() -> None:
    payload = RegimeLabelConfigPlanner().build_configs()
    config_ids = [item["config_id"] for item in payload["configs"]]

    assert payload["planner_version"] == "ml32"
    assert payload["config_count"] >= 6
    assert len(config_ids) == len(set(config_ids))
    assert all(item["risk_note"] for item in payload["configs"])
    assert json.dumps(payload)
