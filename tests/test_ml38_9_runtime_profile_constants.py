import run_fv3_cached_tuning
from app.experiments.ml38_2_fv3_tuning_matrix import ML38_9_5_DECISION_POLICY_CONFIG_IDS
from app.experiments.ml38_2_fv3_tuning_matrix import ML38_10_3_CLASS_MARGIN_CONFIG_IDS
from app.experiments.ml38_2_fv3_tuning_matrix import ML38_10_4_SETUP_SEMANTICS_CONFIG_IDS
from app.experiments.ml38_2_fv3_tuning_matrix import ML38_10_6_TWO_STAGE_THRESHOLD_CONFIG_IDS
from app.experiments.ml38_2_fv3_tuning_matrix import ML38_10_7_SETUP_QUALITY_FILTER_CONFIG_IDS
from app.experiments.ml38_2_fv3_tuning_matrix import ML38_10_8_SETUP_QUALITY_DECISION_MASK_CONFIG_IDS


EXPECTED_FAST_DEBUG_CONFIGS = (
    "lv31_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_exit45_probe",
    "lv31_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_bad_dates_probe",
    "lv30_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_wf_totalr_probe",
    "lv29_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_wf_relax",
    "lv28_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_only",
    "lv27_h08_tts_thr065_sqmask060_epq070_sp045_rguard_dirbias",
    "lv26_h08_tts_thr065_sqmask060_epq070_sp045_recovery_guard",
    "lv25_h08_tts_thr065_sqmask060_epq070_sp045_exit_mit",
    "lv24_h08_tts_thr065_sqmask060_epq068_sp047_mae",
    "lv23_h08_tts_thr065_sqmask060_epq065_sp050_eff",
    "lv22_h08_tts_thr065_sqmask060_epq070_sp045",
    "lv19_h08_tts_thr065_sqmask060",
)

EXPECTED_QUICK_QUALITY_CONFIGS = (
    "lv31_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_exit45_probe",
    "lv31_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_exit75_probe",
    "lv31_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_bad_dates_probe",
    "lv31_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_bad_dates_probe",
    "lv31_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_bad_dates_exit45_probe",
    "lv30_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_wf_totalr_probe",
    "lv30_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_wf_totalr_probe",
    "lv29_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_wf_relax",
    "lv29_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_wf_relax",
    "lv29_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_wf_relax",
    "lv28_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_only",
    "lv28_h12_tts_thr065_sqmask060_epq070_sp045_rguard_short_only",
    "lv28_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short",
    "lv27_h12_tts_thr065_sqmask060_epq070_sp045_rguard_dirbias",
    "lv27_h12_tts_thr065_sqmask060_epq072_sp043_rguard_dirbias_strict",
    "lv26_h12_tts_thr065_sqmask060_epq070_sp045_recovery_guard",
    "lv26_h12_tts_thr065_sqmask060_epq072_sp043_recovery_guard_strict",
    "lv25_h12_tts_thr065_sqmask060_epq070_sp045_exit_mit",
    "lv25_h12_tts_thr065_sqmask060_epq072_sp043_exit_mit_strict",
    "lv24_h12_tts_thr065_sqmask060_epq068_sp047_mae",
    "lv24_h12_tts_thr065_sqmask060_epq070_sp045_mae_rr",
    "lv23_h12_tts_thr065_sqmask060_epq065_sp050_eff",
    "lv23_h12_tts_thr065_sqmask060_epq068_sp047_eff",
    "lv22_h12_tts_thr065_sqmask060_epq070_sp045",
    "lv21_h12_tts_thr065_sqmask060_epq070",
    "lv19_h12_tts_thr065_sqmask060",
)

EXPECTED_SINGLE_SYMBOL_FULL_CONFIGS = (
    "lv10_h08_thr052_tp10_sl10_dp",
    "lv10_h12_thr06_tp12_sl12_dp",
    "lv10_h16_thr065_tp15_sl15_dp",
)


def test_fast_debug_uses_prompt_4_6_smoke_shortlist() -> None:
    args = run_fv3_cached_tuning.parse_args(["--fast-debug"])
    wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(args)

    assert wrapper.runtime_profile == "fast_debug"
    assert wrapper.symbols == ("BTCUSDT", "SOLUSDT")
    assert wrapper.selected_config_ids == EXPECTED_FAST_DEBUG_CONFIGS
    assert wrapper._expected_candidate_count() == 24
    assert "lv15_h08_setup_pure_ft" in ML38_10_4_SETUP_SEMANTICS_CONFIG_IDS
    assert "lv19_h08_tts_thr065_sqmask060" in wrapper.selected_config_ids


def test_quick_quality_uses_prompt_4_6_smoke_shortlist() -> None:
    args = run_fv3_cached_tuning.parse_args([
        "--quick-quality",
        "--quick-quality-symbol",
        "SOLUSDT",
    ])
    wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(args)

    assert wrapper.runtime_profile == "quick_quality"
    assert wrapper.symbols == ("SOLUSDT",)
    assert wrapper.selected_config_ids == EXPECTED_QUICK_QUALITY_CONFIGS
    assert wrapper._expected_candidate_count() == 26

    setup_semantics_configs = [
        config_id
        for config_id in wrapper.selected_config_ids
        if config_id in ML38_10_4_SETUP_SEMANTICS_CONFIG_IDS
    ]
    class_margin_configs = [
        config_id
        for config_id in wrapper.selected_config_ids
        if config_id in ML38_10_3_CLASS_MARGIN_CONFIG_IDS
    ]
    threshold_configs = [
        config_id
        for config_id in wrapper.selected_config_ids
        if config_id in ML38_10_6_TWO_STAGE_THRESHOLD_CONFIG_IDS
    ]
    setup_quality_filter_configs = [
        config_id
        for config_id in wrapper.selected_config_ids
        if config_id in ML38_10_7_SETUP_QUALITY_FILTER_CONFIG_IDS
    ]

    assert setup_semantics_configs == []
    assert class_margin_configs == []
    assert threshold_configs == []
    assert setup_quality_filter_configs == []
    assert "lv22_h12_tts_thr065_sqmask060_epq070_sp045" in EXPECTED_QUICK_QUALITY_CONFIGS
    assert "lv21_h12_tts_thr065_sqmask060_epq070" in EXPECTED_QUICK_QUALITY_CONFIGS
    assert "lv19_h12_tts_thr065_sqmask060" in EXPECTED_QUICK_QUALITY_CONFIGS


def test_ml38_9_5_single_symbol_full_still_uses_decision_policy_shortlist() -> None:
    args = run_fv3_cached_tuning.parse_args([
        "--single-symbol-full",
        "--single-symbol-full-symbol",
        "SOLUSDT",
    ])
    wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(args)

    assert wrapper.runtime_profile == "single_symbol_full"
    assert wrapper.symbols == ("SOLUSDT",)
    assert wrapper.selected_config_ids == EXPECTED_SINGLE_SYMBOL_FULL_CONFIGS
    assert all(config_id in ML38_9_5_DECISION_POLICY_CONFIG_IDS for config_id in wrapper.selected_config_ids)
    assert all(config_id.endswith("_dp") for config_id in wrapper.selected_config_ids)
