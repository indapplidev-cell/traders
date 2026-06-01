from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.db.models import Candle
from app.market.indicator_service import IndicatorSnapshot
from app.strategy.simple_trend_strategy import SimpleTrendStrategy
from app.strategy.trade_decision import DecisionType, MarketRegime


def build_candles() -> list[Candle]:
    now = datetime.now(UTC)
    return [
        Candle(
            symbol="BTCUSDT",
            interval="15m",
            open_time=now - timedelta(minutes=15),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100.5"),
            volume=Decimal("15"),
            close_time=now - timedelta(minutes=1),
        )
    ]


def test_strategy_returns_buy() -> None:
    snapshot = IndicatorSnapshot(
        ema_20=Decimal("100"),
        ema_50=Decimal("99"),
        ema_200=Decimal("95"),
        rsi_14=Decimal("65"),
        atr_14=Decimal("1"),
        volume_sma_20=Decimal("10"),
        last_close=Decimal("101"),
        last_volume=Decimal("12"),
    )

    decision = SimpleTrendStrategy().evaluate(
        symbol="BTCUSDT",
        interval="15m",
        candles=build_candles(),
        indicator_snapshot=snapshot,
        market_regime=MarketRegime.BULL,
    )

    assert decision.decision == DecisionType.BUY


def test_strategy_returns_hold_when_rsi_above_70() -> None:
    snapshot = IndicatorSnapshot(
        ema_20=Decimal("100"),
        ema_50=Decimal("99"),
        ema_200=Decimal("95"),
        rsi_14=Decimal("71"),
        atr_14=Decimal("1"),
        volume_sma_20=Decimal("10"),
        last_close=Decimal("101"),
        last_volume=Decimal("12"),
    )

    decision = SimpleTrendStrategy().evaluate(
        symbol="BTCUSDT",
        interval="15m",
        candles=build_candles(),
        indicator_snapshot=snapshot,
        market_regime=MarketRegime.BULL,
    )

    assert decision.decision != DecisionType.BUY


def test_strategy_returns_sell_with_reason() -> None:
    snapshot = IndicatorSnapshot(
        ema_20=Decimal("100"),
        ema_50=Decimal("101"),
        ema_200=Decimal("105"),
        rsi_14=Decimal("50"),
        atr_14=Decimal("1"),
        volume_sma_20=Decimal("10"),
        last_close=Decimal("99"),
        last_volume=Decimal("12"),
    )

    decision = SimpleTrendStrategy().evaluate(
        symbol="BTCUSDT",
        interval="15m",
        candles=build_candles(),
        indicator_snapshot=snapshot,
        market_regime=MarketRegime.BEAR,
    )

    assert decision.decision == DecisionType.SELL
    assert "выход" in decision.reason.lower() or "медвеж" in decision.reason.lower()
