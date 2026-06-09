from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.data.binance_client import BinanceClient
from app.data.historical_loader import HistoricalLoader
from app.db.base import Base
from app.db.repositories.candle_repository import CandleRepository
import app.db.models  # noqa: F401


def test_historical_loader_loads_and_persists_candles() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    fake_client = FakeBinanceDataClient(
        candles=[
            _normalized_candle(datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc), Decimal("100.00")),
            _normalized_candle(datetime(2025, 1, 1, 0, 15, tzinfo=timezone.utc), Decimal("101.00")),
        ]
    )

    with Session(engine) as session:
        repository = CandleRepository(session)
        loader = HistoricalLoader(client=fake_client, repository=repository)
        result = loader.load_range(
            symbol="BTCUSDT",
            interval="15m",
            start_at=datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc),
            end_at=datetime(2025, 1, 1, 0, 30, tzinfo=timezone.utc),
        )

        assert result["loaded"] == 2
        assert result["inserted_or_updated"] == 2
        assert result["first_open_time"] == "2025-01-01T00:00:00+00:00"
        assert result["last_open_time"] == "2025-01-01T00:15:00+00:00"
        assert repository.count_range(
            "BTCUSDT",
            "15m",
            datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc),
            datetime(2025, 1, 1, 0, 30, tzinfo=timezone.utc),
        ) == 2


def test_binance_client_paginates_with_fake_http_data() -> None:
    http_client = FakeHttpClient(
        pages=[
            [
                _raw_kline(1735689600000, "100.00", "101.00"),
                _raw_kline(1735690500000, "101.00", "102.00"),
            ],
            [
                _raw_kline(1735691400000, "102.00", "103.00"),
            ],
        ]
    )
    client = BinanceClient(http_client=http_client)
    client.PAGE_LIMIT = 2

    candles = client.load_klines(
        symbol="BTCUSDT",
        interval="15m",
        start_time=datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc),
        end_time=datetime(2025, 1, 1, 1, 0, tzinfo=timezone.utc),
    )

    assert len(candles) == 3
    assert candles[0]["symbol"] == "BTCUSDT"
    assert candles[-1]["close"] == Decimal("103.00")
    assert len(http_client.calls) == 2


class FakeBinanceDataClient:
    def __init__(self, candles: list[dict[str, Any]]) -> None:
        self._candles = candles

    def load_klines(
        self,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict[str, Any]]:
        return list(self._candles)


class FakeHttpClient:
    def __init__(self, pages: list[list[list[Any]]]) -> None:
        self._pages = list(pages)
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, params: dict[str, Any]) -> "FakeResponse":
        self.calls.append({"url": url, "params": params})
        page = self._pages.pop(0) if self._pages else []
        return FakeResponse(page)


class FakeResponse:
    def __init__(self, payload: list[list[Any]]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> list[list[Any]]:
        return self._payload


def _normalized_candle(open_time: datetime, close_price: Decimal) -> dict[str, Any]:
    return {
        "symbol": "BTCUSDT",
        "interval": "15m",
        "open_time": open_time,
        "close_time": open_time.replace(minute=open_time.minute + 14, second=59),
        "open": Decimal("99.00"),
        "high": Decimal("103.00"),
        "low": Decimal("98.00"),
        "close": close_price,
        "volume": Decimal("10.00"),
        "quote_asset_volume": Decimal("1000.00"),
        "number_of_trades": 20,
        "taker_buy_base_volume": Decimal("5.00"),
        "taker_buy_quote_volume": Decimal("500.00"),
        "source": "binance",
    }


def _raw_kline(open_time_ms: int, open_price: str, close_price: str) -> list[Any]:
    return [
        open_time_ms,
        open_price,
        "105.00",
        "95.00",
        close_price,
        "10.00",
        open_time_ms + 899999,
        "1000.00",
        20,
        "5.00",
        "500.00",
        "0",
    ]
