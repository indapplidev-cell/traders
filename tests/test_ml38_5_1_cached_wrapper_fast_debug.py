import run_fv3_cached_tuning


def test_fast_debug_plan_uses_two_symbols_one_config_and_short_range() -> None:
    args = run_fv3_cached_tuning.parse_args(["--fast-debug"])
    wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(args)

    assert wrapper.fast_debug is True
    assert wrapper.symbols == ("BTCUSDT", "SOLUSDT")
    assert wrapper.debug_config_ids == ("lv2_h08_thr03_tp10_sl10",)
    assert wrapper.start_date == "2026-05-01"
    assert wrapper.end_date == "2026-06-15"
    assert wrapper._expected_candidate_count() == 2

    command = wrapper._symbol_command("BTCUSDT", "debug_experiment")
    assert "--base-label-config-id" in command
    config_index = command.index("--base-label-config-id") + 1
    assert command[config_index] == "lv2_h08_thr03_tp10_sl10"


def test_default_wrapper_still_expects_full_42_candidates() -> None:
    args = run_fv3_cached_tuning.parse_args([])
    wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(args)

    assert wrapper.fast_debug is False
    assert wrapper.symbols == ("BTCUSDT", "ETHUSDT", "SOLUSDT")
    assert wrapper.debug_config_ids == ()
    assert wrapper.start_date == "2025-01-01"
    assert wrapper.end_date == "2026-06-15"
    assert wrapper._expected_candidate_count() == 42
