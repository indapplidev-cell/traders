from datetime import datetime, timezone
from decimal import Decimal
from typing import Any


class CandleNormalizer:
    def normalize_kline(self, symbol: str, interval: str, kline: list[Any]) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "interval": interval,
            "open_time": self._from_milliseconds(kline[0]),
            "close_time": self._from_milliseconds(kline[6]),
            "open": Decimal(str(kline[1])),
            "high": Decimal(str(kline[2])),
            "low": Decimal(str(kline[3])),
            "close": Decimal(str(kline[4])),
            "volume": Decimal(str(kline[5])),
            "quote_asset_volume": Decimal(str(kline[7])),
            "number_of_trades": int(kline[8]),
            "taker_buy_base_volume": Decimal(str(kline[9])),
            "taker_buy_quote_volume": Decimal(str(kline[10])),
            "source": "binance",
        }

    def normalize_many(self, symbol: str, interval: str, klines: list[list[Any]]) -> list[dict[str, Any]]:
        return [self.normalize_kline(symbol, interval, kline) for kline in klines]

    @staticmethod
    def _from_milliseconds(value: int | str) -> datetime:
        return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)
