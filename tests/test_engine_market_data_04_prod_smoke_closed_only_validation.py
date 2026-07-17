from app.engine_market_data.prod_smoke import validate_closed_only_rows


def candle(**overrides):
    row = {"open_time_ms": 0, "close_time_ms": 59_999, "open": 10, "high": 12,
           "low": 9, "close": 11, "volume": 1, "is_closed": True, "data_checksum": "abc"}
    row.update(overrides)
    return row


def test_closed_only_accepts_fully_closed_valid_candle():
    result = validate_closed_only_rows("1m", 120_001, [candle(open_time_ms=60_000, close_time_ms=119_999)])
    assert result["passed"]


def test_closed_only_rejects_current_unclosed_and_invalid_data():
    result = validate_closed_only_rows("1m", 120_001, [candle(
        open_time_ms=120_000, close_time_ms=179_999, is_closed=False,
        high=8, low=11, volume=-1, data_checksum=None)], checksum_required=True)
    reasons = set(result["issues"][0]["reasons"])
    assert {"is_closed_false", "current_or_future_open", "future_candle", "invalid_ohlc",
            "negative_volume", "missing_checksum"} <= reasons
