from decimal import Decimal

from app.engine_paper.analytical_exit import (
    AnalyticalExitDecision,
    ClosedAnalysisCandle,
    analyze_position_exit,
    classify_analytical_exit,
)


BOUNDARY = 1_800_000_000_000


def candles(timeframe: str, *, falling: bool = False, future: bool = False):
    duration = 60_000 if timeframe == "1m" else 300_000
    values = []
    for index in range(96):
        open_ms = BOUNDARY - (96 - index) * duration
        base = Decimal("200") - Decimal(index) if falling else Decimal("100") + Decimal(index)
        values.append(ClosedAnalysisCandle(
            symbol="BTCUSDT", timeframe=timeframe, open_time_ms=open_ms,
            close_boundary_ms=open_ms + duration,
            open_price=base, high_price=base + Decimal("0.5"),
            low_price=base - Decimal("0.5"), close_price=(
                base - Decimal("0.25") if falling else base + Decimal("0.25")
            ),
            volume=Decimal(100 + index), quote_volume=Decimal(10000 + index),
            trades_count=100 + index, source="TEST", is_closed=True,
        ))
    if future:
        last = values[-1]
        values.append(ClosedAnalysisCandle(
            symbol=last.symbol, timeframe=timeframe,
            open_time_ms=BOUNDARY, close_boundary_ms=BOUNDARY + duration,
            open_price=Decimal("1"), high_price=Decimal("1000"),
            low_price=Decimal("0.1"), close_price=Decimal("999"),
            volume=Decimal("999999"), quote_volume=Decimal("999999"),
            trades_count=999999, source="FUTURE", is_closed=True,
        ))
    return tuple(values)


def evaluate(one=None, five=None, **kwargs):
    return analyze_position_exit(
        position_id="position:1", symbol="BTCUSDT", side="LONG",
        entry_price=Decimal("150"), stop_price=Decimal("140"),
        target_price=Decimal("220"), opened_at_ms=BOUNDARY - 20 * 60_000,
        candles_1m=one or candles("1m"), candles_5m=five or candles("5m"),
        boundary_ms=BOUNDARY, **kwargs,
    )


def test_real_volume_reaches_vwap_and_future_candle_is_ignored():
    baseline = evaluate()
    with_future = evaluate(candles("1m", future=True), candles("5m", future=True))
    assert baseline.volume_1m["available"] is True
    assert baseline.technical_1m["vwap"] is not None
    assert with_future.exit_score == baseline.exit_score
    assert with_future.source_1m_boundary_ms == BOUNDARY
    assert with_future.future_bars_used is False


def test_gap_fails_closed_for_analytical_exit():
    broken = list(candles("1m"))
    del broken[-10]
    result = evaluate(tuple(broken), candles("5m"))
    assert result.decision is AnalyticalExitDecision.DATA_UNAVAILABLE
    assert result.exit_score == 0


def test_bearish_multi_timeframe_evidence_is_not_hold_for_long():
    first = evaluate(candles("1m", falling=True), candles("5m", falling=True))
    assert first.component_scores["technical_indicators"] > 0
    pending = classify_analytical_exit(
        exit_score=70, strong_reversal=False, prior_exit_scores=(),
        net_positive=False, target_progress=0,
    )
    confirmed = classify_analytical_exit(
        exit_score=70, strong_reversal=False, prior_exit_scores=(70,),
        net_positive=False, target_progress=0,
    )
    assert pending[0] is AnalyticalExitDecision.EXIT_CONFIRMATION_PENDING
    assert confirmed[0] is AnalyticalExitDecision.ANALYTICAL_EXIT


def test_single_indicator_cannot_reach_exit_threshold():
    result = evaluate()
    assert result.component_scores["technical_indicators"] <= 35
    assert result.component_scores["technical_indicators"] < 70
