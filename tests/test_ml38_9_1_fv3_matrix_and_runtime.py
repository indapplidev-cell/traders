import run_fv3_cached_tuning
from app.experiments.ml38_2_fv3_tuning_matrix import ML38_9_1_BIAS_AWARE_CONFIG_IDS
from app.experiments.ml38_2_fv3_tuning_matrix import ML382FV3TuningMatrix
from app.labels.label_quality_grid import LabelQualityGridPlanner


def test_ml38_9_1_label_grid_and_matrix_include_bias_aware_configs() -> None:
    label_grid = LabelQualityGridPlanner().build_grid()
    label_config_ids = {item["config_id"] for item in label_grid["configs"]}
    matrix = ML382FV3TuningMatrix().build()

    assert matrix["bias_aware_stage"] == "ML38.9.1"
    assert matrix["bias_aware_config_count"] == 4
    assert matrix["config_count"] >= 28

    for config_id in ML38_9_1_BIAS_AWARE_CONFIG_IDS:
        assert config_id in label_config_ids
        assert config_id in matrix["config_ids"]


def test_ml38_9_1_runtime_profiles_use_bias_aware_shortlists() -> None:
    fast_args = run_fv3_cached_tuning.parse_args(["--fast-debug"])
    fast_wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(fast_args)
    assert fast_wrapper.runtime_profile == "fast_debug"
    assert fast_wrapper.selected_config_ids == ("lv10_h12_thr06_tp12_sl12_dp",)

    quick_args = run_fv3_cached_tuning.parse_args(["--quick-quality", "--quick-quality-symbol", "SOLUSDT"])
    quick_wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(quick_args)
    assert quick_wrapper.runtime_profile == "quick_quality"
    assert quick_wrapper.symbols == ("SOLUSDT",)
    assert quick_wrapper.selected_config_ids == (
        "lv10_h08_thr052_tp10_sl10_dp",
        "lv10_h12_thr06_tp12_sl12_dp",
        "lv10_h16_thr065_tp15_sl15_dp",
    )

    full_args = run_fv3_cached_tuning.parse_args(["--single-symbol-full", "--single-symbol-full-symbol", "SOLUSDT"])
    full_wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(full_args)
    assert full_wrapper.runtime_profile == "single_symbol_full"
    assert full_wrapper.symbols == ("SOLUSDT",)
    assert full_wrapper.selected_config_ids == (
        "lv10_h08_thr052_tp10_sl10_dp",
        "lv10_h12_thr06_tp12_sl12_dp",
        "lv10_h16_thr065_tp15_sl15_dp",
    )
    assert run_fv3_cached_tuning.DEFAULT_EXPECTED_CANDIDATE_COUNT == (
        ML382FV3TuningMatrix().build()["config_count"] * len(run_fv3_cached_tuning.DEFAULT_SYMBOLS)
    )
