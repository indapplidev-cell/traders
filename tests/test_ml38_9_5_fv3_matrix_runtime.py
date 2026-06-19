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


def test_runtime_profiles_use_current_smoke_configs_and_keep_single_symbol_full_lv10() -> None:
    fast_args = run_fv3_cached_tuning.parse_args(["--fast-debug"])
    fast_wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(fast_args)
    assert fast_wrapper.runtime_profile == "fast_debug"
    assert fast_wrapper.selected_config_ids == run_fv3_cached_tuning.FAST_DEBUG_CONFIGS
    assert "lv16_h08_trade_two_stage" in fast_wrapper.selected_config_ids

    quick_args = run_fv3_cached_tuning.parse_args(["--quick-quality", "--quick-quality-symbol", "SOLUSDT"])
    quick_wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(quick_args)
    assert quick_wrapper.runtime_profile == "quick_quality"
    assert quick_wrapper.symbols == ("SOLUSDT",)
    assert quick_wrapper.selected_config_ids == run_fv3_cached_tuning.QUICK_QUALITY_CONFIGS
    assert "lv16_h12_trade_two_stage" in quick_wrapper.selected_config_ids

    full_args = run_fv3_cached_tuning.parse_args(["--single-symbol-full", "--single-symbol-full-symbol", "SOLUSDT"])
    full_wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(full_args)
    assert full_wrapper.runtime_profile == "single_symbol_full"
    assert full_wrapper.symbols == ("SOLUSDT",)
    assert full_wrapper.selected_config_ids == (
        "lv10_h08_thr052_tp10_sl10_dp",
        "lv10_h12_thr06_tp12_sl12_dp",
        "lv10_h16_thr065_tp15_sl15_dp",
    )
