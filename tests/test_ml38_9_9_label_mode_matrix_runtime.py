import run_fv3_cached_tuning

from app.experiments.ml38_2_fv3_tuning_matrix import ML382FV3TuningMatrix
from app.labels.label_quality_grid import LabelQualityGridPlanner


def test_ml38_9_9_matrix_keeps_label_modes_and_runtime_uses_prompt_4_6_smoke_shortlist() -> None:
    grid = LabelQualityGridPlanner().build_grid()
    configs_by_id = {item["config_id"]: item for item in grid["configs"]}

    assert configs_by_id["lv12_h08_ft_tp10_sl10"]["experimental"] is True
    assert configs_by_id["lv12_h08_ft_tp10_sl10"]["label_mode"] == "first_touch_tp_sl"
    assert configs_by_id["lv12_h12_setup_ft_tp12_sl12"]["label_mode"] == "setup_aware_first_touch"

    payload = ML382FV3TuningMatrix().build()
    assert payload["label_mode_config_ids"] == [
        "lv12_h08_ft_tp10_sl10",
        "lv12_h12_ft_tp12_sl12",
        "lv12_h16_ft_tp15_sl15",
        "lv12_h12_setup_ft_tp12_sl12",
    ]

    fast_wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(
        run_fv3_cached_tuning.parse_args(["--fast-debug"])
    )
    assert fast_wrapper.selected_config_ids == (
        "lv13_h08_opportunity_ft",
        "lv14_h08_cm_setup",
    )

    quick_wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(
        run_fv3_cached_tuning.parse_args(["--quick-quality", "--symbol", "SOLUSDT"])
    )
    assert quick_wrapper.selected_config_ids == (
        "lv13_h08_opportunity_ft",
        "lv13_h12_opportunity_ft",
        "lv14_h08_cm_setup",
    )
    assert len(quick_wrapper.selected_config_ids) == 3
