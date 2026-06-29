from __future__ import annotations

import run_fv3_cached_tuning

from app.experiments.ml38_2_fv3_tuning_matrix import ML382FV3TuningMatrix
from app.experiments.ml38_2_fv3_tuning_matrix import ML38_10_5_TRADE_TWO_STAGE_CONFIG_IDS
from app.experiments.ml38_2_fv3_tuning_matrix import ML38_10_6_TWO_STAGE_THRESHOLD_CONFIG_IDS
from app.experiments.ml38_2_fv3_tuning_matrix import ML38_10_7_SETUP_QUALITY_FILTER_CONFIG_IDS
from app.experiments.ml38_2_fv3_tuning_matrix import ML38_10_8_SETUP_QUALITY_DECISION_MASK_CONFIG_IDS
from app.labels.label_config import LABEL_MODE_SETUP_PURE_FIRST_TOUCH
from app.labels.label_quality_grid import LabelQualityGridPlanner


def test_ml38_10_7_setup_quality_configs_are_in_grid_and_runtime_shortlists() -> None:
    grid_payload = LabelQualityGridPlanner().build_grid()
    configs_by_id = {item["config_id"]: item for item in grid_payload["configs"]}

    for config_id in ML38_10_7_SETUP_QUALITY_FILTER_CONFIG_IDS:
        assert config_id in configs_by_id
        payload = configs_by_id[config_id]
        assert payload["training_objective"] == "trade_two_stage"
        assert payload["label_mode"] == LABEL_MODE_SETUP_PURE_FIRST_TOUCH
        assert payload["setup_quality_min_threshold"] is not None

    assert run_fv3_cached_tuning.FAST_DEBUG_CONFIGS[:2] == (
        "lv31_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_exit45_probe",
        "lv31_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_bad_dates_probe",
    )
    assert run_fv3_cached_tuning.QUICK_QUALITY_CONFIGS[:5] == (
        "lv31_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_exit45_probe",
        "lv31_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_exit75_probe",
        "lv31_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_bad_dates_probe",
        "lv31_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_bad_dates_probe",
        "lv31_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_bad_dates_exit45_probe",
    )
    assert "lv32_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_feature_guard_probe" in (
        run_fv3_cached_tuning.FAST_DEBUG_CONFIGS
    )
    assert "lv32_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_feature_guard_probe" in (
        run_fv3_cached_tuning.QUICK_QUALITY_CONFIGS
    )

    matrix_payload = ML382FV3TuningMatrix().build()
    assert matrix_payload["setup_quality_filter_stage"] == "ML38.10.7"
    assert matrix_payload["setup_quality_filter_config_ids"] == list(ML38_10_7_SETUP_QUALITY_FILTER_CONFIG_IDS)
    assert matrix_payload["setup_quality_decision_mask_stage"] == "ML38.10.8"
    assert matrix_payload["setup_quality_decision_mask_config_ids"] == list(
        ML38_10_8_SETUP_QUALITY_DECISION_MASK_CONFIG_IDS
    )
    assert all(config_id in configs_by_id for config_id in ML38_10_8_SETUP_QUALITY_DECISION_MASK_CONFIG_IDS)
    assert all(config_id in matrix_payload["config_ids"] for config_id in ML38_10_5_TRADE_TWO_STAGE_CONFIG_IDS)
    assert all(config_id in matrix_payload["config_ids"] for config_id in ML38_10_6_TWO_STAGE_THRESHOLD_CONFIG_IDS)
