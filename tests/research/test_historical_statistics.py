from dataclasses import asdict
import pytest

from app.engine_paper.scalping_statistics import PaperOutcome
from traders_ml.parameter_sweep.historical_statistics import HistoricalStatistics, validate_outcome_time
from traders_ml.parameter_sweep.result_search import fingerprint


def payload():
    x = {"outcomes": [asdict(PaperOutcome("BTCUSDT", "SETUP", "BULLISH", "TREND", "LOW", won,
                                        parameter_set_id=parameter_set, observed_at_ms=t))
                      for t, won, parameter_set in [(10, True, "set"), (20, False, "set"),
                                                   (30, True, "set"), (0, True, "set"),
                                                   (5, True, "other")]]}
    return x | {"fingerprint": fingerprint(x)}


def test_future_unknown_and_other_set_do_not_enter_hierarchy():
    s = HistoricalStatistics(payload(), 20)
    h = s.resolve(symbol="BTCUSDT", setup_type="SETUP", direction="BULLISH",
                  regime="TREND", cost_bucket="LOW", parameter_set_id="set")
    assert h.outcome_count == 2 and h.exact.samples == 2 and h.exact.wins == 1
    assert s.trace[0]["excluded_future_or_undated"] == 2


def test_empty_past_is_explicit_not_future_backfill():
    s = HistoricalStatistics(payload(), 1)
    assert s.resolve(symbol="BTCUSDT", setup_type="SETUP", direction="BULLISH").outcome_count == 0


def test_fingerprint_tampering_rejected():
    p = payload(); p["outcomes"][0]["won"] = False
    with pytest.raises(ValueError, match="FINGERPRINT"):
        HistoricalStatistics(p, 20)


@pytest.mark.parametrize("change,reason", [
    ({}, None),
    ({"completed_at": "1970-01-01T00:00:01Z"}, "FUTURE_OUTCOME_CANDLE"),
    ({"completed_at": "1970-01-01T00:02:00"}, "UNDATED_COMPLETION"),
    ({"closed_candle_path": []}, "OUTCOME_PATH_MISSING"),
    ({"path_diagnostics": {"missing_open_time_ms": [60000]}}, "OUTCOME_PATH_INCOMPLETE"),
    ({"closed_candle_path": [{"open_time_ms": 0, "close_time_ms": 1}]}, "INVALID_CANDLE_INTERVAL"),
    ({"closed_candle_path": [{"open_time_ms": 0, "close_time_ms": 59999}] * 2}, "OUTCOME_PATH_GAPS_OR_DUPLICATES"),
])
def test_recorded_causal_outcome_path(change, reason):
    record = {"completed_at": "1970-01-01T00:02:00Z",
              "closed_candle_path": [{"open_time_ms": 0, "close_time_ms": 59999},
                                     {"open_time_ms": 60000, "close_time_ms": 119999}]}
    assert validate_outcome_time(record | change) == reason
