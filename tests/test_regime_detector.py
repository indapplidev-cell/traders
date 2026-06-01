from decimal import Decimal

from app.market.indicator_service import IndicatorSnapshot
from app.market.regime_detector import RegimeDetector
from app.strategy.trade_decision import MarketRegime


def test_regime_detector_returns_bull() -> None:
    snapshot = IndicatorSnapshot(
        ema_20=Decimal("101"),
        ema_50=Decimal("100"),
        ema_200=Decimal("95"),
        rsi_14=Decimal("60"),
        atr_14=Decimal("1"),
        volume_sma_20=Decimal("10"),
        last_close=Decimal("102"),
        last_volume=Decimal("12"),
    )
    assert RegimeDetector().detect(snapshot) == MarketRegime.BULL


def test_regime_detector_returns_bear() -> None:
    snapshot = IndicatorSnapshot(
        ema_20=Decimal("90"),
        ema_50=Decimal("91"),
        ema_200=Decimal("100"),
        rsi_14=Decimal("40"),
        atr_14=Decimal("1"),
        volume_sma_20=Decimal("10"),
        last_close=Decimal("89"),
        last_volume=Decimal("12"),
    )
    assert RegimeDetector().detect(snapshot) == MarketRegime.BEAR


def test_regime_detector_returns_sideways() -> None:
    snapshot = IndicatorSnapshot(
        ema_20=Decimal("100.10"),
        ema_50=Decimal("100.20"),
        ema_200=Decimal("100"),
        rsi_14=Decimal("50"),
        atr_14=Decimal("1"),
        volume_sma_20=Decimal("10"),
        last_close=Decimal("100"),
        last_volume=Decimal("12"),
    )
    assert RegimeDetector().detect(snapshot) == MarketRegime.SIDEWAYS


def test_regime_detector_returns_unknown() -> None:
    snapshot = IndicatorSnapshot(
        ema_20=Decimal("100"),
        ema_50=Decimal("100"),
        ema_200=Decimal("100"),
        rsi_14=Decimal("80"),
        atr_14=Decimal("2"),
        volume_sma_20=Decimal("10"),
        last_close=Decimal("100"),
        last_volume=Decimal("12"),
    )
    assert RegimeDetector().detect(snapshot) == MarketRegime.UNKNOWN

