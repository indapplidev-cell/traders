import json

from app.labels.label_quality_grid import LabelQualityGridPlanner


def test_label_quality_grid_returns_multiple_unique_valid_configs() -> None:
    payload = LabelQualityGridPlanner().build_grid()

    assert payload["config_count"] >= 5
    config_ids = [item["config_id"] for item in payload["configs"]]
    assert len(config_ids) == len(set(config_ids))
    for item in payload["configs"]:
        assert item["config_id"]
        assert item["horizon"] > 0
        assert item["threshold"] > 0
        assert item["take_profit_atr"] > 0
        assert item["stop_loss_atr"] > 0
    config_ids = {item["config_id"] for item in payload["configs"]}
    assert "lv15_h08_setup_pure_ft" in config_ids
    assert "lv15_h12_setup_pure_ft" in config_ids
    assert "lv15_h16_setup_pure_ft" in config_ids
    json.dumps(payload, ensure_ascii=False, sort_keys=True)
