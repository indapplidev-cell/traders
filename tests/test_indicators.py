from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.db.models import Candle
from app.market.indicator_service import IndicatorService


def build_candles(count: int = 240) -> list[Candle]:
    """Генерирует закрытые свечи для unit-тестов."""

    start = datetime.now(UTC) - timedelta(minutes=count * 15)
    candles: list[Candle] = []
    for index in range(count):
        close = Decimal("100") + Decimal(index) * Decimal("0.5")
        candles.append(
            Candle(
                symbol="BTCUSDT",
                interval="15m",
                open_time=start + timedelta(minutes=index * 15),
                open=close - Decimal("0.2"),
                high=close + Decimal("0.7"),
                low=close - Decimal("0.8"),
                close=close,
                volume=Decimal("10") + Decimal(index % 7),
                close_time=start + timedelta(minutes=index * 15 + 14),
            )
        )
    return candles


def test_indicator_service_calculates_ema_and_rsi() -> None:
    candles = build_candles()
    snapshot = IndicatorService().calculate(candles)

    assert snapshot.ema_20 > Decimal("0")
    assert snapshot.ema_50 > Decimal("0")
    assert snapshot.ema_200 > Decimal("0")
    assert Decimal("0") <= snapshot.rsi_14 <= Decimal("100")


def test_indicator_service_returns_neutral_rsi_for_flat_market() -> None:
    start = datetime.now(UTC) - timedelta(minutes=240 * 15)
    candles = [
        Candle(
            symbol="BTCUSDT",
            interval="15m",
            open_time=start + timedelta(minutes=index * 15),
            open=Decimal("100"),
            high=Decimal("100"),
            low=Decimal("100"),
            close=Decimal("100"),
            volume=Decimal("10"),
            close_time=start + timedelta(minutes=index * 15 + 14),
        )
        for index in range(240)
    ]

    snapshot = IndicatorService().calculate(candles)

    assert snapshot.rsi_14 == Decimal("50.0")
