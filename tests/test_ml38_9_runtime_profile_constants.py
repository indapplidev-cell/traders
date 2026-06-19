import run_fv3_cached_tuning
from app.experiments.ml38_2_fv3_tuning_matrix import ML38_9_4_BOUNDED_CALIBRATION_CONFIG_IDS


EXPECTED_QUICK_QUALITY_CONFIGS = (
    "lv9_h08_thr052_tp10_sl10_bc",
    "lv9_h12_thr06_tp12_sl12_bc",
    "lv9_h16_thr065_tp15_sl15_bc",
)

EXPECTED_SINGLE_SYMBOL_FULL_CONFIGS = (
    "lv9_h08_thr052_tp10_sl10_bc",
    "lv9_h12_thr06_tp12_sl12_bc",
    "lv9_h16_thr065_tp15_sl15_bc",
)


def test_ml38_9_single_symbol_full_uses_calibrated_decision_shortlist() -> None:
    args = run_fv3_cached_tuning.parse_args([
        "--single-symbol-full",
        "--single-symbol-full-symbol",
        "SOLUSDT",
    ])
    wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(args)

    assert wrapper.runtime_profile == "single_symbol_full"
    assert wrapper.symbols == ("SOLUSDT",)
    assert wrapper.selected_config_ids == EXPECTED_SINGLE_SYMBOL_FULL_CONFIGS
    assert all(config_id in ML38_9_4_BOUNDED_CALIBRATION_CONFIG_IDS for config_id in wrapper.selected_config_ids)
    assert all(config_id.endswith("_bc") for config_id in wrapper.selected_config_ids)


def test_ml38_9_quick_quality_and_single_symbol_full_use_calibrated_decision_shortlists() -> None:
    quick_args = run_fv3_cached_tuning.parse_args([
        "--quick-quality",
        "--quick-quality-symbol",
        "SOLUSDT",
    ])
    full_args = run_fv3_cached_tuning.parse_args([
        "--single-symbol-full",
        "--single-symbol-full-symbol",
        "SOLUSDT",
    ])

    quick_wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(quick_args)
    full_wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(full_args)

    assert quick_wrapper.selected_config_ids == EXPECTED_QUICK_QUALITY_CONFIGS
    assert full_wrapper.selected_config_ids == EXPECTED_SINGLE_SYMBOL_FULL_CONFIGS
