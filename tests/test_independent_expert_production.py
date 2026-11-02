from decimal import Decimal

from app.engine_analysis.independent_expert import entry_verdict, weighted_score
from app.engine_market_data.candle import Candle


def _candles(timeframe: str, count: int, *, future_jump: float = 0.0):
    duration = 60_000 if timeframe == "1m" else 300_000
    values = []
    for index in range(count):
        base = 100.0 + index * 0.08
        if index == count - 1:
            base += future_jump
        values.append(Candle(
            symbol="BTCUSDT", timeframe=timeframe,
            open_time_ms=index * duration,
            close_time_ms=(index + 1) * duration - 1,
            open=Decimal(str(base)), high=Decimal(str(base + 0.12)),
            low=Decimal(str(base - 0.04)), close=Decimal(str(base + 0.09)),
            volume=Decimal(str(100 + index)), source="test", is_closed=True,
        ))
    return tuple(values)


def test_verified_weights_are_reproducible_and_normalized():
    boundary = 60 * 300_000 - 1
    verdict = entry_verdict("BTCUSDT", boundary, _candles("1m", 300), _candles("5m", 60))
    weights = {"structure": 8, "context": 22, "momentum": 14, "volume": 2,
               "entry_quality": 22, "liquidity": 22, "confirmation": 10}
    assert sum(weights.values()) == 100
    assert verdict["future_bars_used"] is False
    assert weighted_score(verdict["entry_components"], weights) >= 50


def test_future_candle_mutation_does_not_change_past_verdict():
    boundary = 59 * 300_000 - 1
    first = entry_verdict("BTCUSDT", boundary, _candles("1m", 300), _candles("5m", 60))
    second = entry_verdict(
        "BTCUSDT", boundary, _candles("1m", 300, future_jump=50),
        _candles("5m", 60, future_jump=50),
    )
    assert first == second
