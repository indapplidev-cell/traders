from math import inf, nan

import pytest

from app.market_reader.engine_trend.analysis_contract import (
    AnalysisReadiness,
    AnalysisWindowConfig,
    analysis_readiness,
    interval_duration,
    parse_market_timestamp,
)
from app.market_reader.engine_trend.engine import normalize_candle_row
from app.market_reader.engine_trend.engine import run_engine_trend_from_rows
from app.market_reader.engine_trend.ohlc_integrity import validate_ohlc_integrity
from app.market_reader.engine_trend.schemas import EngineTrendCandle


def candle(timestamp: str, value: float = 100.0) -> EngineTrendCandle:
    return EngineTrendCandle(timestamp, value, value + 2, value - 2, value + 1, 10)


def test_timestamp_and_interval_contract() -> None:
    assert parse_market_timestamp("2026-01-01T00:00:00Z").utcoffset().total_seconds() == 0
    assert parse_market_timestamp("1767225600000").year == 2026
    assert interval_duration("15m").total_seconds() == 900
    with pytest.raises(ValueError):
        interval_duration("monthly")


def test_full_analysis_readiness_is_not_one_candle() -> None:
    config = AnalysisWindowConfig()
    assert analysis_readiness(1, config) is AnalysisReadiness.PARTIAL
    assert analysis_readiness(64, config) is AnalysisReadiness.FULL


@pytest.mark.parametrize("value", [nan, inf, -inf])
def test_non_finite_market_values_fail_integrity(value: float) -> None:
    result = validate_ohlc_integrity(
        (EngineTrendCandle("2026-01-01T00:00:00Z", value, value, value, value, 0),)
    )
    assert result.is_valid is False
    assert any(code.startswith("NON_FINITE") for code in result.errors)


def test_real_row_normalization_rejects_non_positive_prices() -> None:
    with pytest.raises(ValueError, match="positive"):
        normalize_candle_row(
            {"timestamp": "2026-01-01T00:00:00Z", "open": 1, "high": 2, "low": 0, "close": 1}
        )


def test_strict_series_detects_gap_and_missing_count() -> None:
    result = validate_ohlc_integrity(
        (
            candle("2026-01-01T00:00:00Z"),
            candle("2026-01-01T00:15:00Z"),
            candle("2026-01-01T00:45:00Z"),
        ),
        interval="15m",
        strict_timestamps=True,
    )
    assert result.is_valid is False
    assert result.missing_candle_count == 1
    assert any(code.startswith("CANDLE_GAP") for code in result.errors)


def test_public_row_facade_fails_closed_on_partial_history() -> None:
    rows = [
        {
            "timestamp": f"2026-01-01T00:{index * 15:02d}:00Z",
            "open": 100,
            "high": 102,
            "low": 99,
            "close": 101,
            "volume": 10,
        }
        for index in range(4)
    ]
    output = run_engine_trend_from_rows("TEST", "15m", rows).composer_output
    assert output.result.market_regime.value == "UNKNOWN"
    assert output.ohlc_integrity.readiness is AnalysisReadiness.PARTIAL
    assert "COMPOSER_PARTIAL_ANALYSIS_UNKNOWN" in output.decision_trace.reason_codes
    assert output.result.to_dict()["final_answer"]["is_abstention"] is True
