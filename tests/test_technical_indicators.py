from app.features.technical_indicators import TechnicalIndicators


def test_technical_indicators_compute_expected_seeded_values() -> None:
    closes = [float(value) for value in range(1, 21)]
    highs = [close_value + 1 for close_value in closes]
    lows = [close_value - 1 for close_value in closes]

    ema_3 = TechnicalIndicators.ema(closes, 3)
    atr_14 = TechnicalIndicators.atr(highs, lows, closes, 14)
    rsi_14 = TechnicalIndicators.rsi(closes, 14)

    assert ema_3[:2] == [None, None]
    assert ema_3[2] == 2.0
    assert round(ema_3[3], 6) == 3.0
    assert atr_14[12] is None
    assert round(atr_14[13], 6) == 2.0
    assert rsi_14[13] is None
    assert rsi_14[14] == 100.0
