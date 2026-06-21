from __future__ import annotations

import run_fv3_cached_tuning

from app.experiments.ml38_2_fv3_tuning_matrix import ML382FV3TuningMatrix
from app.labels.label_config import LABEL_MODE_SETUP_PURE_FIRST_TOUCH
from app.labels.label_quality_grid import LabelQualityGridPlanner


def test_ml38_10_5_trade_two_stage_configs_are_in_grid_and_matrix() -> None:
    grid_payload = LabelQualityGridPlanner().build_grid()
    configs_by_id = {item["config_id"]: item for item in grid_payload["configs"]}

    for config_id in (
        "lv16_h08_trade_two_stage",
        "lv16_h12_trade_two_stage",
        "lv16_h16_trade_two_stage",
    ):
        assert config_id in configs_by_id
        assert configs_by_id[config_id]["label_mode"] == LABEL_MODE_SETUP_PURE_FIRST_TOUCH
        assert configs_by_id[config_id]["training_objective"] == "trade_two_stage"
        assert configs_by_id[config_id]["experimental"] is True

    matrix = ML382FV3TuningMatrix().build()
    assert matrix["trade_two_stage_stage"] == "ML38.10.5"
    assert matrix["trade_two_stage_config_ids"] == [
        "lv16_h08_trade_two_stage",
        "lv16_h12_trade_two_stage",
        "lv16_h16_trade_two_stage",
    ]


def test_ml38_10_5_runtime_smoke_uses_current_shortlists() -> None:
    fast_wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(
        run_fv3_cached_tuning.parse_args(["--fast-debug"])
    )
    assert fast_wrapper.selected_config_ids == (
        "lv21_h08_tts_thr065_sqmask060_epq065",
        "lv19_h08_tts_thr065_sqmask060",
    )

    quick_wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(
        run_fv3_cached_tuning.parse_args(["--quick-quality", "--quick-quality-symbol", "SOLUSDT"])
    )
    assert quick_wrapper.selected_config_ids == (
        "lv21_h12_tts_thr065_sqmask060_epq065",
        "lv21_h12_tts_thr065_sqmask060_epq070",
        "lv19_h12_tts_thr065_sqmask060",
    )
