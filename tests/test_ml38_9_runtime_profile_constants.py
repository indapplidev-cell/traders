import run_fv3_cached_tuning
from app.experiments.ml38_2_fv3_tuning_matrix import ML38_9_5_DECISION_POLICY_CONFIG_IDS


EXPECTED_QUICK_QUALITY_CONFIGS = (
    "lv11_h08_thr052_tp10_sl10_fv4",
    "lv11_h12_thr06_tp12_sl12_fv4",
    "lv11_h16_thr065_tp15_sl15_fv4",
)

EXPECTED_SINGLE_SYMBOL_FULL_CONFIGS = (
    "lv10_h08_thr052_tp10_sl10_dp",
    "lv10_h12_thr06_tp12_sl12_dp",
    "lv10_h16_thr065_tp15_sl15_dp",
)


def test_ml38_9_5_single_symbol_full_uses_decision_policy_shortlist() -> None:
    args = run_fv3_cached_tuning.parse_args([
        "--single-symbol-full",
        "--single-symbol-full-symbol",
        "SOLUSDT",
    ])
    wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(args)

    assert wrapper.runtime_profile == "single_symbol_full"
    assert wrapper.symbols == ("SOLUSDT",)
    assert wrapper.selected_config_ids == EXPECTED_SINGLE_SYMBOL_FULL_CONFIGS
    assert all(config_id in ML38_9_5_DECISION_POLICY_CONFIG_IDS for config_id in wrapper.selected_config_ids)
    assert all(config_id.endswith("_dp") for config_id in wrapper.selected_config_ids)


def test_ml38_9_5_quick_quality_and_single_symbol_full_use_decision_policy_shortlists() -> None:
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
