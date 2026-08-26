from __future__ import annotations

from types import SimpleNamespace

from app.engine_analysis.scalping_semantics import project_scalping_analysis_semantics
from app.engine_market_data.candle import Candle
from app.engine_market_data.market_data_snapshot import MarketDataSnapshot


def snapshot(ranges: list[float]) -> MarketDataSnapshot:
    candles = []
    for index, width in enumerate(ranges):
        open_time = index * 300_000
        candles.append(Candle(
            symbol="BTCUSDT", timeframe="5m", open_time_ms=open_time,
            close_time_ms=open_time + 299_999, open=100, high=100 + width,
            low=100, close=100 + width / 2, volume=10, is_closed=True,
            source="test",
        ))
    return MarketDataSnapshot(
        symbol="BTCUSDT", timeframe="5m", closed_until_ms=len(candles) * 300_000,
        candles=candles, source="test", has_gaps=False, future_bars_used=False,
        health_status="OK", enough_data=True,
    )


def test_not_evaluated_is_distinct_and_has_reason_and_provenance():
    result = project_scalping_analysis_semantics(
        SimpleNamespace(regime="UP", entry_quality="NOT_EVALUATED", analysis_context={}),
        snapshot([1.0] * 20),
    )
    assert result["market_regime"] == "UP"
    assert result["entry_evidence_strength"] == "NOT_EVALUATED"
    evaluation = result["entry_evidence_evaluation"]
    assert evaluation["status"] != "WEAK"
    assert evaluation["reason_codes"] == ["ENTRY_PATTERN_NOT_PRESENT_AT_DECISION_BOUNDARY"]
    assert evaluation["provenance"] == "CLOSED_5M_IMPULSE_PHASE_DIAGNOSTIC"
    assert result["future_bars_used"] is False


def test_range_compression_expansion_and_conflict_are_explicit():
    base = SimpleNamespace(regime="FLAT", entry_quality="ACCEPTABLE", analysis_context={})
    assert project_scalping_analysis_semantics(base, snapshot([1.0] * 20))["market_regime"] == "RANGE"
    assert project_scalping_analysis_semantics(base, snapshot([2.0] * 15 + [.5] * 5))["market_regime"] == "COMPRESSION"
    assert project_scalping_analysis_semantics(base, snapshot([.5] * 15 + [2.0] * 5))["market_regime"] == "EXPANSION"
    conflict = SimpleNamespace(
        regime="UP", entry_quality="GOOD",
        analysis_context={"confluence_conflict": {"conflict_level": "HIGH"}},
    )
    assert project_scalping_analysis_semantics(
        conflict, snapshot([1.0] * 20)
    )["entry_evidence_strength"] == "CONFLICTING"
