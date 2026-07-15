from decimal import Decimal

import pytest

from app.engine_market_data.candle import Candle
from app.engine_market_data.errors import CandleValidationError


def candle(**overrides: object) -> Candle:
    values = dict(
        symbol="btcusdt", timeframe="1m", open_time_ms=0, close_time_ms=59_999,
        open="10", high="12", low="9", close="11", volume="5",
        quote_volume="52", trades_count=3, is_closed=True, source="rest",
    )
    values.update(overrides)
    return Candle(**values)  # type: ignore[arg-type]


def test_candle_has_deterministic_identity_and_decimal_values() -> None:
    result = candle()
    assert result.identity == ("BTCUSDT", "1m", 0)
    assert result.open == Decimal("10")


@pytest.mark.parametrize(
    ("field", "value"),
    [("high", "10.5"), ("low", "11.5"), ("volume", "-1"), ("open", "NaN")],
)
def test_candle_rejects_invalid_ohlcv(field: str, value: str) -> None:
    with pytest.raises(CandleValidationError):
        candle(**{field: value})


def test_candle_requires_aligned_utc_millisecond_interval() -> None:
    with pytest.raises(CandleValidationError):
        candle(open_time_ms=1, close_time_ms=60_000)
