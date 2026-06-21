import run_fv3_cached_tuning

from app.experiments.ml38_2_fv3_tuning_matrix import ML382FV3TuningMatrix


def test_ml38_9_3_matrix_includes_calibrated_decision_configs() -> None:
    payload = ML382FV3TuningMatrix().build()
    config_ids = set(payload["config_ids"])

    assert "lv8_h10_thr055_tp10_sl10_cd" in config_ids
    assert "lv8_h12_thr06_tp12_sl12_cd" in config_ids
    assert "lv8_h16_thr065_tp15_sl15_cd" in config_ids


def test_quick_quality_uses_current_prompt_4_6_smoke_configs() -> None:
    args = run_fv3_cached_tuning.parse_args(["--quick-quality", "--quick-quality-symbol", "SOLUSDT"])
    wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(args)

    assert wrapper.runtime_profile == "quick_quality"
    assert wrapper.symbols == ("SOLUSDT",)
    assert wrapper.selected_config_ids == run_fv3_cached_tuning.QUICK_QUALITY_CONFIGS
    assert "lv22_h12_tts_thr065_sqmask060_epq070_sp045" in wrapper.selected_config_ids
