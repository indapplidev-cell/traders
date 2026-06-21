from app.experiments.ml38_2_fv3_tuning_matrix import ML382FV3TuningMatrix
from app.labels.label_quality_grid import LabelQualityGridPlanner


def test_ml38_10_14_label_grid_contains_entry_path_quality_configs() -> None:
    configs = {
        item["config_id"]: item
        for item in LabelQualityGridPlanner().build_grid()["configs"]
    }

    for config_id in (
        "lv22_h08_tts_thr065_sqmask060_epq070_sp045",
        "lv22_h12_tts_thr065_sqmask060_epq070_sp045",
        "lv21_h12_tts_thr065_sqmask060_epq070",
    ):
        assert config_id in configs
        assert configs[config_id]["training_objective"] == "trade_two_stage"
        assert configs[config_id]["entry_path_quality_filter_enabled"] is True
        assert configs[config_id]["entry_path_quality_min_threshold"] is not None
        assert configs[config_id]["stop_pressure_max_risk_score"] is not None


def test_ml38_10_14_fv3_matrix_includes_entry_path_quality_stage() -> None:
    payload = ML382FV3TuningMatrix().build()
    assert payload["entry_path_quality_stage"] == "ML38.10.14"
    assert "lv22_h12_tts_thr065_sqmask060_epq070_sp045" in payload["config_ids"]
