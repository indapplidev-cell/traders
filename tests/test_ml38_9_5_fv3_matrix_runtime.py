import run_fv3_cached_tuning
from app.experiments.ml38_2_fv3_tuning_matrix import ML382FV3TuningMatrix


def test_ml38_9_5_matrix_includes_decision_policy_configs() -> None:
    payload = ML382FV3TuningMatrix().build()
    config_ids = set(payload.get("config_ids") or payload.get("configs") or [])

    if not config_ids:
        config_ids = {
            item.get("config_id")
            for item in payload.get("config_matrix", [])
            if isinstance(item, dict)
        }

    assert "lv10_h08_thr052_tp10_sl10_dp" in config_ids
    assert "lv10_h12_thr06_tp12_sl12_dp" in config_ids
    assert "lv10_h16_thr065_tp15_sl15_dp" in config_ids
    assert payload.get("decision_policy_grid_stage") == "ML38.9.5"
    assert payload.get("decision_policy_config_count") == 3


def test_ml38_9_5_runtime_profiles_use_lv10_configs() -> None:
    fast_args = run_fv3_cached_tuning.parse_args(["--fast-debug"])
    fast_wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(fast_args)
    assert fast_wrapper.selected_config_ids == ("lv10_h12_thr06_tp12_sl12_dp",)

    quick_args = run_fv3_cached_tuning.parse_args(["--quick-quality", "--quick-quality-symbol", "SOLUSDT"])
    quick_wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(quick_args)
    assert quick_wrapper.selected_config_ids == (
        "lv10_h08_thr052_tp10_sl10_dp",
        "lv10_h12_thr06_tp12_sl12_dp",
        "lv10_h16_thr065_tp15_sl15_dp",
    )
