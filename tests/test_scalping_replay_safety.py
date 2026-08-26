from app.engine_observation.scalping_replay_safety import (
    HistoricalMicrostructureCapture,
    NOT_REPLAYABLE_WITHOUT_FUTURE_LEAKAGE,
    select_historical_microstructure,
    timestamps_are_causal,
)


def capture(timestamp):
    return HistoricalMicrostructureCapture(timestamp, 99, 101, 2, 3, "capture")


def test_replay_selects_latest_capture_at_or_before_original_cutoff():
    result = select_historical_microstructure(
        (capture(900), capture(999), capture(1001)),
        decision_cutoff_ms=1000, maximum_age_ms=100,
    )
    assert result.replayable
    assert result.capture.captured_at_ms == 999


def test_later_only_or_stale_microstructure_is_not_replaced_with_future_quote():
    for captures in ((capture(1001),), (capture(800),)):
        result = select_historical_microstructure(
            captures, decision_cutoff_ms=1000, maximum_age_ms=100,
        )
        assert result.replayable is False
        assert result.capture is None
        assert result.reason == NOT_REPLAYABLE_WITHOUT_FUTURE_LEAKAGE


def test_all_historical_inputs_must_be_at_or_before_cutoff():
    assert timestamps_are_causal((1, 999, 1000), decision_cutoff_ms=1000)
    assert not timestamps_are_causal((1, 1001), decision_cutoff_ms=1000)
