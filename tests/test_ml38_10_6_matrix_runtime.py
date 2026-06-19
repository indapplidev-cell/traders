from __future__ import annotations

import run_fv3_cached_tuning

from app.experiments.ml38_2_fv3_tuning_matrix import ML382FV3TuningMatrix
from app.experiments.ml38_2_fv3_tuning_matrix import ML38_10_6_TWO_STAGE_THRESHOLD_CONFIG_IDS
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


def test_ml38_10_6_runtime_shortlists_use_threshold_configs() -> None:
    assert run_fv3_cached_tuning.FAST_DEBUG_CONFIGS == (
        "lv17_h08_tts_thr060",
        "lv16_h08_trade_two_stage",
    )
    assert run_fv3_cached_tuning.QUICK_QUALITY_CONFIGS == (
        "lv17_h08_tts_thr060",
        "lv17_h08_tts_thr065",
        "lv17_h12_tts_thr065",
    )
