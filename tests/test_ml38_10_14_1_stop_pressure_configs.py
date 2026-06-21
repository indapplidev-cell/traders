import run_fv3_cached_tuning
from app.experiments.ml38_2_fv3_tuning_matrix import ML382FV3TuningMatrix
from app.labels.label_quality_grid import LabelQualityGridPlanner


def test_ml38_10_14_1_grid_contains_stronger_stop_pressure_configs() -> None:
    grid = LabelQualityGridPlanner().build_grid()
    configs = {item["config_id"]: item for item in grid["configs"]}

    for config_id in (
        "lv22_h08_tts_thr065_sqmask060_epq070_sp045",
        "lv22_h12_tts_thr065_sqmask060_epq070_sp045",
        "lv22_h12_tts_thr065_sqmask060_epq075_sp040",
    ):
        assert config_id in configs
        payload = configs[config_id]
        assert payload["training_objective"] == "trade_two_stage"
        assert payload["entry_path_quality_filter_enabled"] is True
        assert payload["entry_path_quality_min_threshold"] >= 0.70
        assert payload["stop_pressure_max_risk_score"] <= 0.45


def test_ml38_10_14_1_matrix_and_runtime_use_stronger_stop_pressure_shortlists() -> None:
    matrix = ML382FV3TuningMatrix().build()
    assert matrix["entry_path_stop_pressure_stage"] == "ML38.10.14.1"
    assert "lv22_h12_tts_thr065_sqmask060_epq070_sp045" in matrix["config_ids"]

    fast_wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(
        run_fv3_cached_tuning.parse_args(["--fast-debug"])
    )
    assert fast_wrapper.selected_config_ids == run_fv3_cached_tuning.FAST_DEBUG_CONFIGS
    assert "lv22_h08_tts_thr065_sqmask060_epq070_sp045" in fast_wrapper.selected_config_ids

    quick_wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(
        run_fv3_cached_tuning.parse_args(["--quick-quality", "--symbol", "SOLUSDT"])
    )
    assert quick_wrapper.selected_config_ids == run_fv3_cached_tuning.QUICK_QUALITY_CONFIGS
    assert "lv22_h12_tts_thr065_sqmask060_epq070_sp045" in quick_wrapper.selected_config_ids
    assert "lv21_h12_tts_thr065_sqmask060_epq070" in quick_wrapper.selected_config_ids
    assert "lv19_h12_tts_thr065_sqmask060" in quick_wrapper.selected_config_ids
