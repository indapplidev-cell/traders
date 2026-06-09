from datetime import timezone
from decimal import Decimal

from app.data.candle_normalizer import CandleNormalizer


def test_candle_normalizer_maps_binance_kline_to_internal_schema() -> None:
    normalizer = CandleNormalizer()
    raw_kline = [
        1735689600000,
        "42000.10",
        "42100.20",
        "41950.30",
        "42050.40",
        "12.5",
        1735690499999,
        "525000.55",
        321,
        "7.25",
        "304500.66",
        "0",
    ]

    normalized = normalizer.normalize_kline("BTCUSDT", "15m", raw_kline)

    assert normalized["symbol"] == "BTCUSDT"
    assert normalized["interval"] == "15m"
    assert normalized["open_time"].tzinfo == timezone.utc
    assert normalized["close_time"].tzinfo == timezone.utc
    assert normalized["open"] == Decimal("42000.10")
    assert normalized["high"] == Decimal("42100.20")
    assert normalized["low"] == Decimal("41950.30")
    assert normalized["close"] == Decimal("42050.40")
    assert normalized["volume"] == Decimal("12.5")
    assert normalized["quote_asset_volume"] == Decimal("525000.55")
    assert normalized["number_of_trades"] == 321
    assert normalized["taker_buy_base_volume"] == Decimal("7.25")
    assert normalized["taker_buy_quote_volume"] == Decimal("304500.66")
    assert normalized["source"] == "binance"
