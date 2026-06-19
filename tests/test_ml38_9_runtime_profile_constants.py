import run_fv3_cached_tuning
from app.experiments.ml38_2_fv3_tuning_matrix import ML38_9_5_DECISION_POLICY_CONFIG_IDS
from app.experiments.ml38_2_fv3_tuning_matrix import ML38_10_3_CLASS_MARGIN_CONFIG_IDS
from app.experiments.ml38_2_fv3_tuning_matrix import ML38_10_4_SETUP_SEMANTICS_CONFIG_IDS


EXPECTED_FAST_DEBUG_CONFIGS = (
    "lv15_h08_setup_pure_ft",
    "lv14_h08_cm_setup",
)

EXPECTED_QUICK_QUALITY_CONFIGS = (
    "lv15_h08_setup_pure_ft",
    "lv15_h12_setup_pure_ft",
    "lv14_h08_cm_setup",
)

EXPECTED_SINGLE_SYMBOL_FULL_CONFIGS = (
    "lv10_h08_thr052_tp10_sl10_dp",
    "lv10_h12_thr06_tp12_sl12_dp",
    "lv10_h16_thr065_tp15_sl15_dp",
)


def test_fast_debug_uses_prompt_4_6_smoke_shortlist() -> None:
    args = run_fv3_cached_tuning.parse_args(["--fast-debug"])
    wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(args)

    assert wrapper.runtime_profile == "fast_debug"
    assert wrapper.symbols == ("BTCUSDT", "SOLUSDT")
    assert wrapper.selected_config_ids == EXPECTED_FAST_DEBUG_CONFIGS
    assert wrapper._expected_candidate_count() == 4
    assert "lv15_h08_setup_pure_ft" in ML38_10_4_SETUP_SEMANTICS_CONFIG_IDS
    assert "lv14_h08_cm_setup" in ML38_10_3_CLASS_MARGIN_CONFIG_IDS


def test_quick_quality_uses_prompt_4_6_smoke_shortlist() -> None:
    args = run_fv3_cached_tuning.parse_args([
        "--quick-quality",
        "--quick-quality-symbol",
        "SOLUSDT",
    ])
    wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(args)

    assert wrapper.runtime_profile == "quick_quality"
    assert wrapper.symbols == ("SOLUSDT",)
    assert wrapper.selected_config_ids == EXPECTED_QUICK_QUALITY_CONFIGS
    assert wrapper._expected_candidate_count() == 3

    setup_semantics_configs = [
        config_id
        for config_id in wrapper.selected_config_ids
        if config_id in ML38_10_4_SETUP_SEMANTICS_CONFIG_IDS
    ]
    class_margin_configs = [
        config_id
        for config_id in wrapper.selected_config_ids
        if config_id in ML38_10_3_CLASS_MARGIN_CONFIG_IDS
    ]

    assert setup_semantics_configs == [
        "lv15_h08_setup_pure_ft",
        "lv15_h12_setup_pure_ft",
    ]
    assert class_margin_configs == ["lv14_h08_cm_setup"]


def test_ml38_9_5_single_symbol_full_still_uses_decision_policy_shortlist() -> None:
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
