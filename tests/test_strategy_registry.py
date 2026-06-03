from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.db.models import Candle
from app.market.indicator_service import IndicatorSnapshot
from app.strategy.base_strategy import StrategyDecision
from app.strategy.simple_trend_strategy import SimpleTrendStrategy
from app.strategy.strategy_context import StrategyContext
from app.strategy.strategy_registry import StrategyRegistry, get_strategy, list_strategies


def build_context() -> StrategyContext:
    now = datetime.now(UTC)
    candle = Candle(
        symbol="BTCUSDT",
        interval="15m",
        open_time=now - timedelta(minutes=15),
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100"),
        volume=Decimal("10"),
        close_time=now - timedelta(minutes=1),
    )
    snapshot = IndicatorSnapshot(
        ema_20=Decimal("100"),
        ema_50=Decimal("100"),
        ema_200=Decimal("100"),
        rsi_14=Decimal("50"),
        atr_14=Decimal("1"),
        volume_sma_20=Decimal("10"),
        last_close=Decimal("100"),
        last_volume=Decimal("10"),
    )
    return StrategyContext(
        symbol="BTCUSDT",
        interval="15m",
        candles=[candle],
        indicators={
            "snapshot": snapshot,
            "ema_20": snapshot.ema_20,
            "ema_50": snapshot.ema_50,
            "ema_200": snapshot.ema_200,
            "rsi_14": snapshot.rsi_14,
            "atr_14": snapshot.atr_14,
            "volume_sma_20": snapshot.volume_sma_20,
            "last_close": snapshot.last_close,
            "last_volume": snapshot.last_volume,
        },
        market_regime="SIDEWAYS",
        open_positions=[],
        portfolio_state={"balance_usdt": "1000"},
        last_decisions=[],
        settings=SimpleNamespace(),
    )


def test_registry_returns_known_default_strategy() -> None:
    assert "simple_trend" in list_strategies()
    assert isinstance(get_strategy("simple_trend"), SimpleTrendStrategy)


def test_registry_rejects_unknown_strategy() -> None:
    registry = StrategyRegistry()
    registry.register_strategy(SimpleTrendStrategy())

    with pytest.raises(ValueError, match="Unknown strategy: missing"):
        registry.get_strategy("missing")


def test_simple_trend_returns_strategy_decision() -> None:
    decision = SimpleTrendStrategy().decide(build_context())

    assert isinstance(decision, StrategyDecision)
    assert decision.strategy_name == "simple_trend"
    assert decision.strategy_version == "1.0"
    assert decision.symbol == "BTCUSDT"
    assert decision.interval == "15m"
    assert decision.action in {"BUY", "SELL", "HOLD"}
    assert 0.0 <= decision.confidence <= 1.0


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_strategy_decision_rejects_invalid_confidence(confidence: float) -> None:
    with pytest.raises(ValueError, match="confidence"):
        StrategyDecision(
            strategy_name="simple_trend",
            strategy_version="1.0",
            symbol="BTCUSDT",
            interval="15m",
            action="HOLD",
            reason="test",
            confidence=confidence,
        )
