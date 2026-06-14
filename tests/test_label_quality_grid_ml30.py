from app.labels.label_quality_grid import LabelQualityGridPlanner


def test_label_quality_grid_ml30_contains_old_and_new_configs() -> None:
    payload = LabelQualityGridPlanner().build_grid()
    config_ids = {item["config_id"] for item in payload["configs"]}

    assert payload["planner_version"] == "ml30"
    assert payload["config_count"] >= 15
    assert "lv2_h08_thr03_tp10_sl10" in config_ids
    assert "lv2_h08_thr04_tp10_sl10" in config_ids
    assert "lv2_h12_thr04_tp15_sl10" in config_ids
    assert "lv2_h16_thr05_tp20_sl10" in config_ids
    assert "lv3_h32_thr08_tp20_sl15" in config_ids
