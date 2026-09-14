from dataclasses import asdict
import pytest

from app.engine_paper.scalping_statistics import PaperOutcome
from traders_ml.parameter_sweep.historical_statistics import HistoricalStatistics
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
