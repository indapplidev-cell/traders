import run_fv3_cached_tuning
from app.experiments.ml38_2_fv3_tuning_matrix import ML38_9_FLAT_BIAS_CONFIG_IDS


EXPECTED_COMPACT_FLAT_BIAS_CONFIGS = (
    "lv5_h06_thr045_tp10_sl10_fb",
    "lv5_h08_thr05_tp10_sl10_fb",
    "lv5_h12_thr055_tp12_sl12_fb",
)


def test_ml38_9_single_symbol_full_uses_flat_bias_shortlist() -> None:
    args = run_fv3_cached_tuning.parse_args([
        "--single-symbol-full",
        "--single-symbol-full-symbol",
        "SOLUSDT",
    ])
    wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(args)

    assert wrapper.runtime_profile == "single_symbol_full"
    assert wrapper.symbols == ("SOLUSDT",)
    assert wrapper.selected_config_ids == EXPECTED_COMPACT_FLAT_BIAS_CONFIGS
    assert all(config_id in ML38_9_FLAT_BIAS_CONFIG_IDS for config_id in wrapper.selected_config_ids)
    assert all(config_id.endswith("_fb") for config_id in wrapper.selected_config_ids)


def test_ml38_9_quick_quality_and_single_symbol_full_use_same_shortlist() -> None:
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

    assert quick_wrapper.selected_config_ids == EXPECTED_COMPACT_FLAT_BIAS_CONFIGS
    assert full_wrapper.selected_config_ids == EXPECTED_COMPACT_FLAT_BIAS_CONFIGS
