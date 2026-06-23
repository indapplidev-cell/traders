import run_fv3_cached_tuning


def test_fast_debug_plan_uses_two_symbols_prompt_4_6_configs_and_short_range() -> None:
    args = run_fv3_cached_tuning.parse_args(["--fast-debug"])
    wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(args)

    assert wrapper.fast_debug is True
    assert wrapper.symbols == ("BTCUSDT", "SOLUSDT")
    assert wrapper.debug_config_ids == run_fv3_cached_tuning.FAST_DEBUG_CONFIGS
    assert "lv22_h08_tts_thr065_sqmask060_epq070_sp045" in wrapper.debug_config_ids
    assert wrapper.start_date == "2026-05-01"
    assert wrapper.end_date == "2026-06-15"
    assert wrapper._expected_candidate_count() == 6

    command = wrapper._symbol_command("BTCUSDT", "debug_experiment")

    start_date_index = command.index("--start-date") + 1
    end_date_index = command.index("--end-date") + 1
    assert command[start_date_index] == "2026-05-01"
    assert command[end_date_index] == "2026-06-15"
    assert "--skip-candle-load" in command
    assert "--base-label-config-id" in command

    config_values = [
        command[index + 1]
        for index, value in enumerate(command)
        if value == "--base-label-config-id"
    ]
    assert config_values == [
        "lv23_h08_tts_thr065_sqmask060_epq065_sp050_eff",
        "lv22_h08_tts_thr065_sqmask060_epq070_sp045",
        "lv19_h08_tts_thr065_sqmask060",
    ]


def test_default_wrapper_expects_full_60_candidates() -> None:
    args = run_fv3_cached_tuning.parse_args([])
    wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(args)

    assert wrapper.fast_debug is False
    assert wrapper.symbols == ("BTCUSDT", "ETHUSDT", "SOLUSDT")
    assert wrapper.debug_config_ids == ()
    assert wrapper.start_date == "2025-01-01"
    assert wrapper.end_date == "2026-06-15"
    assert wrapper._expected_candidate_count() == run_fv3_cached_tuning.DEFAULT_EXPECTED_CANDIDATE_COUNT


def test_fast_debug_final_result_marks_builder_date_range_expected() -> None:
    args = run_fv3_cached_tuning.parse_args(["--fast-debug"])
    wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(args)
    wrapper.current_branch = "test"
    wrapper.archive_stage_dir = None
    wrapper.archive_path = None
    wrapper.candle_cache_results = []
    wrapper.experiments = []
    wrapper.multi_symbol_result = None

    result = wrapper._build_final_result(
        status="ok",
        wrapper_completed_end_to_end=True,
        archive_size_bytes=123,
        training_skipped=False,
    )

    assert result["fast_debug"] is True
    assert result["full_quality_run"] is False
    assert result["quality_decision_allowed"] is False
    assert result["debug_start_date"] == "2026-05-01"
    assert result["debug_end_date"] == "2026-06-15"
    assert result["debug_date_range_expected_to_limit_builders"] is True
