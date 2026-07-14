from app.market_reader.engine_trend.market_hypothesis import (
    HypothesisDirection,
    HypothesisStatus,
    HypothesisType,
    analyze_market_hypotheses,
)
from app.market_reader.engine_trend.regime_composer import compose_engine_trend_result
from app.market_reader.engine_trend.schemas import EngineTrendCandle, EngineTrendRegime
from app.market_reader.engine_trend.unified_market_context import (
    build_unified_market_context,
)


def candle(
    timestamp: str,
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: float = 0.0,
) -> EngineTrendCandle:
    return EngineTrendCandle(timestamp, open_, high, low, close, volume)


def range_candles() -> list[EngineTrendCandle]:
    values = (
        (105, 106, 104, 105),
        (105, 110, 104, 109),
        (109, 109.5, 100, 101),
        (101, 106, 99.9, 105),
        (105, 110.1, 104, 109),
        (109, 109.4, 100.1, 101),
        (101, 106, 99.8, 105),
        (105, 110, 104, 109),
        (109, 109.5, 100, 101),
    )
    return [candle(str(index), *item, 100 + index) for index, item in enumerate(values)]


def test_all_layers_share_one_normalized_structural_map() -> None:
    context = build_unified_market_context(range_candles())
    structural_indexes = {item.index for item in context.structural_swing_points}
    zone_indexes = {
        index
        for zone in context.schwager_context.zones
        for index in zone.source_indexes
    }
    assert context.altunina_context.swing_points == context.structural_swing_points
    assert zone_indexes <= structural_indexes
    assert len(context.raw_swing_points) >= len(context.structural_swing_points)


def test_false_breakout_becomes_opposite_direction_hypothesis() -> None:
    candles = range_candles() + [
        candle("break", 109, 112, 108, 111, 240),
        candle("return", 111, 111.5, 99.5, 104.8, 260),
    ]
    result = analyze_market_hypotheses(build_unified_market_context(candles))
    bull_trap = next(
        item
        for item in result.hypotheses
        if item.hypothesis_type is HypothesisType.BULL_TRAP
    )
    assert bull_trap.direction is HypothesisDirection.BEARISH
    assert bull_trap.status is HypothesisStatus.CONFIRMED
    assert bull_trap.trigger_index < bull_trap.confirmation_index


def test_uncontextualized_bullish_candles_do_not_select_up() -> None:
    candles = tuple(
        candle(str(index), 100 + index, 102 + index, 99 + index, 101.8 + index)
        for index in range(8)
    )
    output = compose_engine_trend_result("TEST", "15m", candles)
    assert "BULLISH_BODY_DOMINANCE" in output.matrix.nison_context.reason_codes
    assert output.matrix.hypothesis_result.dominant_hypothesis is None
    assert output.result.market_regime is EngineTrendRegime.UNKNOWN


def test_matrix_exports_contextual_events_and_hypotheses() -> None:
    output = compose_engine_trend_result("TEST", "15m", range_candles())
    payload = output.matrix.to_dict()
    assert "unified_context" in payload
    assert "hypothesis_result" in payload
    assert payload["hypothesis_result"]["hypotheses"]
    assert output.result.market_regime is EngineTrendRegime.FLAT
