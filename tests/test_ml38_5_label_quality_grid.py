from app.labels.label_quality_grid import LabelQualityGridPlanner


def test_ml38_5_label_quality_grid_contains_anti_collapse_configs() -> None:
    payload = LabelQualityGridPlanner().build_grid()
    configs = {item["config_id"]: item for item in payload["configs"]}

    expected = {
        "lv3_h04_thr02_tp08_sl08_ac": (4, 0.2, 0.8, 0.8),
        "lv3_h04_thr025_tp08_sl08_ac": (4, 0.25, 0.8, 0.8),
        "lv3_h06_thr025_tp10_sl08_ac": (6, 0.25, 1.0, 0.8),
        "lv3_h06_thr03_tp10_sl10_ac": (6, 0.3, 1.0, 1.0),
        "lv3_h08_thr025_tp10_sl08_ac": (8, 0.25, 1.0, 0.8),
        "lv3_h08_thr03_tp12_sl08_ac": (8, 0.3, 1.2, 0.8),
    }

    assert set(expected).issubset(configs)

    for config_id, (horizon, threshold, take_profit, stop_loss) in expected.items():
        config = configs[config_id]
        assert config["horizon"] == horizon
        assert config["threshold"] == threshold
        assert config["take_profit_atr"] == take_profit
        assert config["stop_loss_atr"] == stop_loss
        assert config["anti_collapse_profile"] is not None
