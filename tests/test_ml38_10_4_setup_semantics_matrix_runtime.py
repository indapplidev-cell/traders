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
    assert fast_wrapper.selected_config_ids == run_fv3_cached_tuning.FAST_DEBUG_CONFIGS
    assert "lv23_h08_tts_thr065_sqmask060_epq065_sp050_eff" in fast_wrapper.selected_config_ids
    assert "lv22_h08_tts_thr065_sqmask060_epq070_sp045" in fast_wrapper.selected_config_ids
    assert "lv19_h08_tts_thr065_sqmask060" in fast_wrapper.selected_config_ids

    quick_wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(
        run_fv3_cached_tuning.parse_args(["--quick-quality", "--quick-quality-symbol", "SOLUSDT"])
    )
    assert quick_wrapper.selected_config_ids == run_fv3_cached_tuning.QUICK_QUALITY_CONFIGS
    assert "lv23_h12_tts_thr065_sqmask060_epq065_sp050_eff" in quick_wrapper.selected_config_ids
    assert "lv23_h12_tts_thr065_sqmask060_epq068_sp047_eff" in quick_wrapper.selected_config_ids
    assert "lv22_h12_tts_thr065_sqmask060_epq070_sp045" in quick_wrapper.selected_config_ids
    assert "lv21_h12_tts_thr065_sqmask060_epq070" in quick_wrapper.selected_config_ids
    assert "lv19_h12_tts_thr065_sqmask060" in quick_wrapper.selected_config_ids
