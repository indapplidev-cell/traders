from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.db.models import Candle
from app.db.session import session_scope
from app.history.historical_loader import HistoricalLoader


class FakeHistoricalClient:
    """Возвращает заранее подготовленные чанки свечей для исторической загрузки."""

    def __init__(self, chunks: list[list[dict[str, object]]]) -> None:
        self.chunks = chunks
        self.calls: list[tuple[int | None, int | None, int]] = []

    async def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 300,
        start_time_ms: int | None = None,
        end_time_ms: int | None = None,
    ) -> list[dict[str, object]]:
        _ = (symbol, interval)
        self.calls.append((start_time_ms, end_time_ms, limit))
        if self.chunks:
            return self.chunks.pop(0)
        return []


def _build_raw_candle(open_time: datetime, close_price: str) -> dict[str, object]:
    """Строит минимальный нормализованный payload свечи Binance."""

    close_time = open_time + timedelta(minutes=15) - timedelta(milliseconds=1)
    return {
        "open_time": int(open_time.timestamp() * 1000),
        "open": close_price,
        "high": str(Decimal(close_price) + Decimal("1")),
        "low": str(Decimal(close_price) - Decimal("1")),
        "close": close_price,
        "volume": "10",
        "close_time": int(close_time.timestamp() * 1000),
    }


def test_historical_loader_loads_multiple_chunks_into_db(sqlite_session) -> None:
    """Проверяет chunked-загрузку истории и сохранение свечей в БД."""

    _ = sqlite_session
    base = datetime.now(UTC) - timedelta(hours=1)
    chunk_one = [_build_raw_candle(base + timedelta(minutes=15 * index), "100") for index in range(2)]
    chunk_two = [_build_raw_candle(base + timedelta(minutes=15 * (index + 2)), "101") for index in range(2)]
    client = FakeHistoricalClient([chunk_one, chunk_two, []])
    loader = HistoricalLoader(client=client)
    progress_events: list[tuple[int, int, int]] = []

    result = asyncio.run(
        loader.load_history(
            symbol="BTCUSDT",
            interval="15m",
            days=2,
            progress_callback=lambda chunks, candles, cursor: progress_events.append((chunks, candles, cursor)),
        )
    )

    assert result.chunks_loaded == 2
    assert result.candles_saved == 4
    assert len(progress_events) == 2
    assert client.calls[0][2] == 1000

    with session_scope() as session:
        candles = session.execute(select(Candle).order_by(Candle.open_time.asc())).scalars().all()

    assert len(candles) == 4
    assert candles[0].symbol == "BTCUSDT"
    assert candles[-1].close == Decimal("101")


def test_historical_loader_stops_cleanly_on_empty_response(sqlite_session) -> None:
    """Проверяет, что пустой ответ не приводит к ошибке и не пишет пустой батч."""

    _ = sqlite_session
    client = FakeHistoricalClient([[]])
    loader = HistoricalLoader(client=client)

    result = asyncio.run(loader.load_history(symbol="BTCUSDT", interval="15m", days=1))

    assert result.chunks_loaded == 0
    assert result.candles_saved == 0
