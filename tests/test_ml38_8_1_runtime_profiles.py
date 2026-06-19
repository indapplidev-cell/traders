import run_fv3_cached_tuning


def test_quick_quality_profile_uses_one_symbol_short_range_and_selected_config() -> None:
    args = run_fv3_cached_tuning.parse_args(["--quick-quality", "--quick-quality-symbol", "SOLUSDT"])
    wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(args)

    assert wrapper.runtime_profile == "quick_quality"
    assert wrapper.fast_debug is False
    assert wrapper.quick_quality is True
    assert wrapper.single_symbol_full is False
    assert wrapper.symbols == ("SOLUSDT",)
    assert wrapper.selected_config_ids == (
        "lv12_h08_ft_tp10_sl10",
        "lv12_h12_ft_tp12_sl12",
        "lv12_h12_setup_ft_tp12_sl12",
    )
    assert wrapper.start_date == "2026-04-01"
    assert wrapper.end_date == "2026-06-15"
    assert wrapper._expected_candidate_count() == 3
    assert wrapper._full_quality_run() is False
    assert wrapper._quality_decision_allowed() is False

    command = wrapper._symbol_command("SOLUSDT", "quick_quality_experiment")

    assert "--skip-candle-load" in command
    assert "--base-label-config-id" in command
    config_values = [
        command[index + 1]
        for index, value in enumerate(command)
        if value == "--base-label-config-id"
    ]
    assert config_values == [
        "lv12_h08_ft_tp10_sl10",
        "lv12_h12_ft_tp12_sl12",
        "lv12_h12_setup_ft_tp12_sl12",
    ]
    assert command[command.index("--start-date") + 1] == "2026-04-01"
    assert command[command.index("--end-date") + 1] == "2026-06-15"


def test_single_symbol_full_profile_uses_one_symbol_full_range_and_selected_config() -> None:
    args = run_fv3_cached_tuning.parse_args(["--single-symbol-full", "--single-symbol-full-symbol", "SOLUSDT"])
    wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(args)

    assert wrapper.runtime_profile == "single_symbol_full"
    assert wrapper.fast_debug is False
    assert wrapper.quick_quality is False
    assert wrapper.single_symbol_full is True
    assert wrapper.symbols == ("SOLUSDT",)
    assert wrapper.selected_config_ids == (
        "lv10_h08_thr052_tp10_sl10_dp",
        "lv10_h12_thr06_tp12_sl12_dp",
        "lv10_h16_thr065_tp15_sl15_dp",
    )
    assert wrapper.start_date == "2025-01-01"
    assert wrapper.end_date == "2026-06-15"
    assert wrapper._expected_candidate_count() == 3
    assert wrapper._full_quality_run() is False
    assert wrapper._quality_decision_allowed() is False

    command = wrapper._symbol_command("SOLUSDT", "single_symbol_full_experiment")

    assert "--skip-candle-load" in command
    assert "--base-label-config-id" in command
    config_values = [
        command[index + 1]
        for index, value in enumerate(command)
        if value == "--base-label-config-id"
    ]
    assert config_values == [
        "lv10_h08_thr052_tp10_sl10_dp",
        "lv10_h12_thr06_tp12_sl12_dp",
        "lv10_h16_thr065_tp15_sl15_dp",
    ]
    assert command[command.index("--start-date") + 1] == "2025-01-01"
    assert command[command.index("--end-date") + 1] == "2026-06-15"


def test_full_profile_still_expects_original_three_symbol_full_grid() -> None:
    args = run_fv3_cached_tuning.parse_args([])
    wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(args)

    assert wrapper.runtime_profile == "full"
    assert wrapper.symbols == ("BTCUSDT", "ETHUSDT", "SOLUSDT")
    assert wrapper.selected_config_ids == ()
    assert wrapper.start_date == "2025-01-01"
    assert wrapper.end_date == "2026-06-15"
    assert wrapper._expected_candidate_count() == run_fv3_cached_tuning.DEFAULT_EXPECTED_CANDIDATE_COUNT
    assert wrapper._full_quality_run() is True
    assert wrapper._quality_decision_allowed() is True


def test_quick_quality_recommends_single_symbol_full_only_after_accepted_candidate() -> None:
    args = run_fv3_cached_tuning.parse_args(["--quick-quality", "--quick-quality-symbol", "SOLUSDT"])
    wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(args)

    wrapper.multi_symbol_result = {"accepted_candidate_count": 0}
    assert wrapper._next_recommended_action() == (
        "Do not run full multi-symbol validation; continue improving labels/features/model."
    )

    wrapper.multi_symbol_result = {"accepted_candidate_count": 1}
    assert wrapper._next_recommended_action() == (
        "Run single-symbol-full for SOLUSDT; do not auto-activate the model."
    )


def test_single_symbol_full_recommends_full_run_only_after_accepted_candidate() -> None:
    args = run_fv3_cached_tuning.parse_args(["--single-symbol-full", "--single-symbol-full-symbol", "SOLUSDT"])
    wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(args)

    wrapper.multi_symbol_result = {"accepted_candidate_count": 0}
    assert wrapper._next_recommended_action() == (
        "Do not run full multi-symbol validation; one-symbol full-period did not produce ACCEPTED."
    )

    wrapper.multi_symbol_result = {"accepted_candidate_count": 1}
    assert wrapper._next_recommended_action() == (
        "Run full BTCUSDT/ETHUSDT/SOLUSDT validation; do not auto-activate the model."
    )
