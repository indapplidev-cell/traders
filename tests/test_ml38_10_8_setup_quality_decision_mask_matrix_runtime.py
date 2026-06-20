from __future__ import annotations

import run_fv3_cached_tuning

from app.experiments.ml38_2_fv3_tuning_matrix import ML382FV3TuningMatrix
from app.experiments.ml38_2_fv3_tuning_matrix import ML38_10_5_TRADE_TWO_STAGE_CONFIG_IDS
from app.experiments.ml38_2_fv3_tuning_matrix import ML38_10_6_TWO_STAGE_THRESHOLD_CONFIG_IDS
from app.experiments.ml38_2_fv3_tuning_matrix import ML38_10_7_SETUP_QUALITY_FILTER_CONFIG_IDS
from app.experiments.ml38_2_fv3_tuning_matrix import ML38_10_8_SETUP_QUALITY_DECISION_MASK_CONFIG_IDS
from app.labels.label_quality_grid import LabelQualityGridPlanner


def test_ml38_10_8_grid_matrix_and_runtime_shortlists_include_lv19_without_removing_historical_configs() -> None:
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
        "lv19_h08_tts_thr065_sqmask060",
        "lv18_h12_tts_thr065_sq060",
    )
    assert run_fv3_cached_tuning.QUICK_QUALITY_CONFIGS == tuple(ML38_10_8_SETUP_QUALITY_DECISION_MASK_CONFIG_IDS)

    for config_id in (
        *ML38_10_5_TRADE_TWO_STAGE_CONFIG_IDS,
        *ML38_10_6_TWO_STAGE_THRESHOLD_CONFIG_IDS,
        *ML38_10_7_SETUP_QUALITY_FILTER_CONFIG_IDS,
        *ML38_10_8_SETUP_QUALITY_DECISION_MASK_CONFIG_IDS,
    ):
        assert config_id in configs_by_id
        assert config_id in matrix["config_ids"]
