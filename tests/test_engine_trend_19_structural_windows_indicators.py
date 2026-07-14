from app.market_reader.engine_trend.altunina_trend_context import (
    detect_volatility_aware_swing_points,
)
from app.market_reader.engine_trend.analysis_contract import AnalysisWindowConfig
from app.market_reader.engine_trend.schemas import EngineTrendCandle
from app.market_reader.engine_trend.technical_indicator_context import (
    IndicatorDirection,
    analyze_technical_indicators,
)
from app.market_reader.engine_trend.unified_market_context import (
    build_unified_market_context,
)


def candles(count: int = 96, direction: int = 1) -> list[EngineTrendCandle]:
    output = []
    for index in range(count):
        trend = direction * index * 0.35
        wave = (index % 6 - 3) * 0.2
        close = 100 + trend + wave
        output.append(
            EngineTrendCandle(
                f"2026-01-{1 + index // 96:02d}T{(index % 96) // 4:02d}:{(index % 4) * 15:02d}:00Z",
                close - direction * 0.1,
                close + 0.8,
                close - 0.8,
                close,
                100 + index,
            )
        )
    return output


def test_analysis_window_limits_decision_events_but_keeps_context() -> None:
    context = build_unified_market_context(
        candles(),
        AnalysisWindowConfig(decision_candles=24, confirmation_candles=3),
    )
    assert context.analysis_window.context_start_index == 0
    assert context.analysis_window.decision_start_index == 72
    assert context.analysis_window.confirmation_lookahead == 3


def test_indicator_context_confirms_persistent_direction() -> None:
    bullish = analyze_technical_indicators(candles(direction=1))
    bearish = analyze_technical_indicators(candles(direction=-1))
    assert bullish.direction is IndicatorDirection.BULLISH
    assert bearish.direction is IndicatorDirection.BEARISH
    assert bullish.atr_14 and bullish.adx_14 is not None
    assert bullish.macd is not None and bullish.rsi_14 is not None


def test_volatility_aware_swings_are_not_denser_than_raw_candles() -> None:
    items = candles()
    pivots = detect_volatility_aware_swing_points(items)
    assert len(pivots) < len(items) // 2
    assert all(first.point_type is not second.point_type for first, second in zip(pivots, pivots[1:]))
