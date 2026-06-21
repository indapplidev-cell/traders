from __future__ import annotations

import run_fv3_cached_tuning

from app.experiments.ml38_2_fv3_tuning_matrix import ML382FV3TuningMatrix
from app.labels.label_config import LABEL_MODE_SETUP_PURE_FIRST_TOUCH
from app.labels.label_quality_grid import LabelQualityGridPlanner


def test_ml38_10_4_setup_pure_configs_are_in_grid_and_matrix() -> None:
    grid = LabelQualityGridPlanner().build_grid()
    configs_by_id = {item["config_id"]: item for item in grid["configs"]}

    for config_id in (
        "lv15_h08_setup_pure_ft",
        "lv15_h12_setup_pure_ft",
        "lv15_h16_setup_pure_ft",
    ):
        assert config_id in configs_by_id
        assert configs_by_id[config_id]["label_mode"] == LABEL_MODE_SETUP_PURE_FIRST_TOUCH
        assert configs_by_id[config_id]["training_objective"] == "opportunity_first"
        assert configs_by_id[config_id]["experimental"] is True

    matrix = ML382FV3TuningMatrix().build()
    assert matrix["setup_semantics_stage"] == "ML38.10.4"
    assert matrix["setup_semantics_config_ids"] == [
        "lv15_h08_setup_pure_ft",
        "lv15_h12_setup_pure_ft",
        "lv15_h16_setup_pure_ft",
    ]


def test_ml38_10_4_runtime_profiles_follow_current_smoke_shortlists() -> None:
    fast_wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(
        run_fv3_cached_tuning.parse_args(["--fast-debug"])
    )
    assert fast_wrapper.selected_config_ids == (
        "lv22_h08_tts_thr065_sqmask060_epq070_sp045",
        "lv19_h08_tts_thr065_sqmask060",
    )

    quick_wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(
        run_fv3_cached_tuning.parse_args(["--quick-quality", "--quick-quality-symbol", "SOLUSDT"])
    )
    assert quick_wrapper.selected_config_ids == (
        "lv22_h12_tts_thr065_sqmask060_epq070_sp045",
        "lv21_h12_tts_thr065_sqmask060_epq070",
        "lv19_h12_tts_thr065_sqmask060",
    )
