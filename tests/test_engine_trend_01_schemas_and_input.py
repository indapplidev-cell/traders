from __future__ import annotations

import pytest

from app.market_reader.engine_trend.input_period import EngineTrendInputPeriod
from app.market_reader.engine_trend.ohlc_integrity import validate_ohlc_integrity
from app.market_reader.engine_trend.schemas import (
    BookEvidence,
    BookSource,
    ConfidenceDecomposition,
    EngineTrendCandle,
    EngineTrendEvidence,
    EngineTrendRegime,
    EngineTrendResult,
    EngineTrendSafety,
    TradeSignal,
)


def make_candle(timestamp: str = "2026-01-01T00:00:00Z") -> EngineTrendCandle:
    return EngineTrendCandle(
        timestamp=timestamp,
        open=100.0,
        high=110.0,
        low=90.0,
        close=105.0,
        volume=10.0,
    )


def test_engine_trend_regime_values() -> None:
    assert EngineTrendRegime.UP.value == "UP"
    assert EngineTrendRegime.DOWN.value == "DOWN"
    assert EngineTrendRegime.FLAT.value == "FLAT"
    assert EngineTrendRegime.UNKNOWN.value == "UNKNOWN"


def test_trade_signal_is_locked_to_not_evaluated() -> None:
    assert TradeSignal.NOT_EVALUATED.value == "NOT_EVALUATED"


def test_candle_accepts_valid_ohlcv() -> None:
    candle = make_candle()
    assert candle.open == 100.0
    assert candle.high == 110.0
    assert candle.low == 90.0
    assert candle.close == 105.0
    assert candle.volume == 10.0


def test_candle_rejects_high_below_body() -> None:
    with pytest.raises(ValueError, match="high must be"):
        EngineTrendCandle("x", 100.0, 99.0, 90.0, 105.0, 1.0)


def test_candle_rejects_low_above_body() -> None:
    with pytest.raises(ValueError, match="low must be"):
        EngineTrendCandle("x", 100.0, 110.0, 101.0, 99.0, 1.0)


def test_candle_rejects_negative_volume() -> None:
    with pytest.raises(ValueError, match="volume must be non-negative"):
        EngineTrendCandle("x", 100.0, 110.0, 90.0, 105.0, -1.0)


def test_evidence_requires_code() -> None:
    with pytest.raises(ValueError, match="evidence code"):
        EngineTrendEvidence(BookSource.NISON, "", "empty code")


def test_evidence_rejects_out_of_range_contribution() -> None:
    with pytest.raises(ValueError, match="contribution"):
        EngineTrendEvidence(BookSource.NISON, "X", "bad contribution", 2.0)


def test_book_evidence_collects_reason_codes() -> None:
    evidence = BookEvidence(
        nison=(EngineTrendEvidence(BookSource.NISON, "DOJI_INDECISION", "doji", 0.1),),
        schwager=(EngineTrendEvidence(BookSource.SCHWAGER, "TRADING_RANGE_DETECTED", "range", 0.2),),
    )
    assert evidence.reason_codes() == ("DOJI_INDECISION", "TRADING_RANGE_DETECTED")


def test_confidence_decomposition_clamps_total() -> None:
    confidence = ConfidenceDecomposition(trend_score=0.8, range_score=0.8, conflict_penalty=-0.1)
    assert confidence.total() == 1.0


def test_safety_defaults_fail_closed() -> None:
    safety = EngineTrendSafety()
    assert safety.trade_signal is TradeSignal.NOT_EVALUATED
    assert safety.safe_for_runtime_trading is False
    assert safety.live_trading_connected is False


def test_safety_rejects_runtime_safe_true() -> None:
    with pytest.raises(ValueError, match="runtime trading"):
        EngineTrendSafety(safe_for_runtime_trading=True)


def test_safety_rejects_live_trading_connection() -> None:
    with pytest.raises(ValueError, match="live trading"):
        EngineTrendSafety(live_trading_connected=True)


def test_engine_trend_result_to_dict_is_safe() -> None:
    result = EngineTrendResult(
        symbol="BTCUSDT",
        interval="15m",
        period_start="2026-01-01T00:00:00Z",
        period_end="2026-01-01T01:00:00Z",
        candle_count=5,
        market_regime=EngineTrendRegime.UNKNOWN,
        confidence=0.0,
    )

    payload = result.to_dict()

    assert payload["service"] == "ENGINE_TREND"
    assert payload["market_regime"] == "UNKNOWN"
    assert payload["safety"]["trade_signal"] == "NOT_EVALUATED"
    assert payload["safety"]["safe_for_runtime_trading"] is False


def test_engine_trend_result_rejects_empty_symbol() -> None:
    with pytest.raises(ValueError, match="symbol"):
        EngineTrendResult("", "15m", None, None, 0, EngineTrendRegime.UNKNOWN, 0.0)


def test_engine_trend_result_rejects_bad_confidence() -> None:
    with pytest.raises(ValueError, match="confidence"):
        EngineTrendResult("BTCUSDT", "15m", None, None, 0, EngineTrendRegime.UNKNOWN, 1.5)


def test_input_period_requires_candles() -> None:
    with pytest.raises(ValueError, match="candles"):
        EngineTrendInputPeriod("BTCUSDT", "15m", ())


def test_input_period_exposes_period_bounds() -> None:
    period = EngineTrendInputPeriod(
        symbol="BTCUSDT",
        interval="15m",
        candles=(
            make_candle("2026-01-01T00:00:00Z"),
            make_candle("2026-01-01T00:15:00Z"),
        ),
    )

    assert period.period_start == "2026-01-01T00:00:00Z"
    assert period.period_end == "2026-01-01T00:15:00Z"
    assert period.candle_count == 2


def test_ohlc_integrity_passes_valid_candles() -> None:
    result = validate_ohlc_integrity(
        (make_candle("2026-01-01T00:00:00Z"), make_candle("2026-01-01T00:15:00Z"))
    )

    assert result.status == "PASS"
    assert result.is_valid is True
    assert result.errors == ()


def test_ohlc_integrity_fails_without_candles() -> None:
    result = validate_ohlc_integrity(())

    assert result.status == "FAIL"
    assert result.is_valid is False
    assert result.errors == ("NO_CANDLES_PROVIDED",)


def test_ohlc_integrity_warns_on_duplicate_timestamp() -> None:
    result = validate_ohlc_integrity(
        (make_candle("2026-01-01T00:00:00Z"), make_candle("2026-01-01T00:00:00Z"))
    )

    assert result.status == "PASS_WITH_WARNINGS"
    assert result.is_valid is True
    assert result.warnings == ("DUPLICATE_TIMESTAMP:2026-01-01T00:00:00Z",)


def test_ohlc_integrity_fails_on_timestamp_order_error() -> None:
    result = validate_ohlc_integrity(
        (make_candle("2026-01-01T00:15:00Z"), make_candle("2026-01-01T00:00:00Z"))
    )

    assert result.status == "FAIL"
    assert result.is_valid is False
    assert result.errors == ("TIMESTAMP_ORDER_ERROR:index=1",)
