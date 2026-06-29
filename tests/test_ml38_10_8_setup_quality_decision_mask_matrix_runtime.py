from __future__ import annotations

import run_fv3_cached_tuning

from app.experiments.ml38_2_fv3_tuning_matrix import ML382FV3TuningMatrix
from app.experiments.ml38_2_fv3_tuning_matrix import ML38_10_5_TRADE_TWO_STAGE_CONFIG_IDS
from app.experiments.ml38_2_fv3_tuning_matrix import ML38_10_6_TWO_STAGE_THRESHOLD_CONFIG_IDS
from app.experiments.ml38_2_fv3_tuning_matrix import ML38_10_7_SETUP_QUALITY_FILTER_CONFIG_IDS
from app.experiments.ml38_2_fv3_tuning_matrix import ML38_10_8_SETUP_QUALITY_DECISION_MASK_CONFIG_IDS
from app.labels.label_quality_grid import LabelQualityGridPlanner


def test_ml38_10_8_grid_matrix_and_runtime_shortlists_keep_historical_configs() -> None:
    grid = LabelQualityGridPlanner().build_grid()
    configs_by_id = {item["config_id"]: item for item in grid["configs"]}

    for config_id in ML38_10_8_SETUP_QUALITY_DECISION_MASK_CONFIG_IDS:
        assert config_id in configs_by_id
        payload = configs_by_id[config_id]
        assert payload["training_objective"] == "trade_two_stage"
        assert payload["setup_quality_decision_mask_enabled"] is True
        assert payload["setup_quality_decision_mask_min_threshold"] is not None

    matrix = ML382FV3TuningMatrix().build()
    assert matrix["setup_quality_decision_mask_stage"] == "ML38.10.8"
    assert matrix["setup_quality_decision_mask_config_ids"] == list(ML38_10_8_SETUP_QUALITY_DECISION_MASK_CONFIG_IDS)
    
    assert run_fv3_cached_tuning.FAST_DEBUG_CONFIGS == (
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
    
    assert run_fv3_cached_tuning.QUICK_QUALITY_CONFIGS == (
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

    for config_id in (
        *ML38_10_5_TRADE_TWO_STAGE_CONFIG_IDS,
        *ML38_10_6_TWO_STAGE_THRESHOLD_CONFIG_IDS,
        *ML38_10_7_SETUP_QUALITY_FILTER_CONFIG_IDS,
        *ML38_10_8_SETUP_QUALITY_DECISION_MASK_CONFIG_IDS,
    ):
        assert config_id in configs_by_id
        assert config_id in matrix["config_ids"]
