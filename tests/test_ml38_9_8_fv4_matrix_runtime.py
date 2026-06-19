import run_fv3_cached_tuning

from app.experiments.ml38_2_fv3_tuning_matrix import ML382FV3TuningMatrix


def test_fv4_matrix_and_runtime_profiles_use_lv11_configs_while_keeping_lv10_available() -> None:
    payload = ML382FV3TuningMatrix().build()

    assert payload["feature_version"] == "fv4_book_setup_context"
    assert payload["book_setup_context_stage"] == "ML38.9.8"
    assert payload["book_setup_context_config_ids"] == [
        "lv11_h08_thr052_tp10_sl10_fv4",
        "lv11_h12_thr06_tp12_sl12_fv4",
        "lv11_h16_thr065_tp15_sl15_fv4",
    ]
    assert "lv10_h08_thr052_tp10_sl10_dp" in payload["config_ids"]
    assert "lv10_h12_thr06_tp12_sl12_dp" in payload["config_ids"]
    assert "lv10_h16_thr065_tp15_sl15_dp" in payload["config_ids"]

    fast_wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(
        run_fv3_cached_tuning.parse_args(["--fast-debug"])
    )
    assert fast_wrapper.selected_config_ids == ("lv11_h08_thr052_tp10_sl10_fv4",)

    quick_wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(
        run_fv3_cached_tuning.parse_args(["--quick-quality", "--symbol", "SOLUSDT"])
    )
    assert quick_wrapper.symbols == ("SOLUSDT",)
    assert quick_wrapper.selected_config_ids == (
        "lv11_h08_thr052_tp10_sl10_fv4",
        "lv11_h12_thr06_tp12_sl12_fv4",
        "lv11_h16_thr065_tp15_sl15_fv4",
    )
