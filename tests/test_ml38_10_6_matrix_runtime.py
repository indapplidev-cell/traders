from __future__ import annotations

import run_fv3_cached_tuning

from app.experiments.ml38_2_fv3_tuning_matrix import ML382FV3TuningMatrix
from app.experiments.ml38_2_fv3_tuning_matrix import ML38_10_6_TWO_STAGE_THRESHOLD_CONFIG_IDS
from app.experiments.ml38_2_fv3_tuning_matrix import ML38_10_7_SETUP_QUALITY_FILTER_CONFIG_IDS
from app.experiments.ml38_2_fv3_tuning_matrix import ML38_10_8_SETUP_QUALITY_DECISION_MASK_CONFIG_IDS
from app.labels.label_config import LABEL_MODE_SETUP_PURE_FIRST_TOUCH
from app.labels.label_quality_grid import LabelQualityGridPlanner


def test_ml38_10_6_threshold_configs_are_in_grid_and_matrix() -> None:
    grid = LabelQualityGridPlanner().build_grid()
    configs_by_id = {item["config_id"]: item for item in grid["configs"]}

    for config_id in ML38_10_6_TWO_STAGE_THRESHOLD_CONFIG_IDS:
        assert config_id in configs_by_id
        payload = configs_by_id[config_id]
        assert payload["training_objective"] == "trade_two_stage"
        assert payload["label_mode"] == LABEL_MODE_SETUP_PURE_FIRST_TOUCH
        assert payload["opportunity_threshold_sweep_enabled"] is True
        assert payload["opportunity_probability_threshold"] >= 0.60
        assert payload["decision_policy_grid_stage"] == "ML38.10.6"
        assert payload["experimental"] is True

    matrix = ML382FV3TuningMatrix().build()
    assert matrix["two_stage_threshold_stage"] == "ML38.10.6"
    assert matrix["two_stage_threshold_config_ids"] == list(ML38_10_6_TWO_STAGE_THRESHOLD_CONFIG_IDS)


def test_ml38_10_6_runtime_shortlists_use_current_configs() -> None:
    assert run_fv3_cached_tuning.FAST_DEBUG_CONFIGS == (
        "lv21_h08_tts_thr065_sqmask060_epq065",
        "lv19_h08_tts_thr065_sqmask060",
    )
    assert run_fv3_cached_tuning.QUICK_QUALITY_CONFIGS == (
        "lv21_h12_tts_thr065_sqmask060_epq065",
        "lv21_h12_tts_thr065_sqmask060_epq070",
        "lv19_h12_tts_thr065_sqmask060",
    )
    assert "lv21_h08_tts_thr065_sqmask060_epq065" in run_fv3_cached_tuning.FAST_DEBUG_CONFIGS
    assert "lv19_h08_tts_thr065_sqmask060" in run_fv3_cached_tuning.FAST_DEBUG_CONFIGS
    assert "lv21_h12_tts_thr065_sqmask060_epq065" in run_fv3_cached_tuning.QUICK_QUALITY_CONFIGS

    matrix_config_ids = ML382FV3TuningMatrix().build()["config_ids"]
    assert all(config_id in matrix_config_ids for config_id in ML38_10_7_SETUP_QUALITY_FILTER_CONFIG_IDS)
    assert all(config_id in matrix_config_ids for config_id in ML38_10_8_SETUP_QUALITY_DECISION_MASK_CONFIG_IDS)
