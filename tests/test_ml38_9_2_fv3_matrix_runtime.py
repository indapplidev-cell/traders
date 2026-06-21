import run_fv3_cached_tuning

from app.experiments.ml38_2_fv3_tuning_matrix import ML382FV3TuningMatrix


def test_ml38_9_2_matrix_contains_baseline_edge_configs() -> None:
    payload = ML382FV3TuningMatrix().build()

    assert payload["baseline_edge_stage"] == "ML38.9.2"
    assert payload["baseline_edge_config_count"] == 3
    assert "lv7_h08_thr052_tp10_sl10_be" in payload["baseline_edge_config_ids"]
    assert "lv7_h10_thr055_tp10_sl10_be" in payload["baseline_edge_config_ids"]
    assert "lv7_h12_thr06_tp12_sl12_be" in payload["baseline_edge_config_ids"]


def test_ml38_9_2_runtime_profile_uses_current_prompt_4_6_quick_quality_shortlist() -> None:
    args = run_fv3_cached_tuning.parse_args(["--quick-quality", "--quick-quality-symbol", "SOLUSDT"])
    wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(args)

    assert wrapper.runtime_profile == "quick_quality"
    assert wrapper.symbols == ("SOLUSDT",)
    assert wrapper.selected_config_ids == run_fv3_cached_tuning.QUICK_QUALITY_CONFIGS
    assert "lv21_h12_tts_thr065_sqmask060_epq065" in wrapper.selected_config_ids
