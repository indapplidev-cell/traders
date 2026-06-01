"""Пакетная историческая загрузка свечей из публичного Binance REST."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Callable

from app.exchange.binance_public_client import BinancePublicClient
from app.market.candle_service import CandleService


HistoricalProgressCallback = Callable[[int, int, int], None]


@dataclass(slots=True)
class HistoricalLoadResult:
    """Сводка по завершённой исторической загрузке."""

    symbol: str
    interval: str
    days: int
    chunks_loaded: int
    candles_saved: int
    started_at: datetime
    finished_at: datetime
    first_open_time: datetime | None
    last_open_time: datetime | None


class HistoricalLoader:
    """Загружает историю свечей Binance по частям и сохраняет её в БД."""

    MAX_CANDLES_PER_REQUEST = 1000

    def __init__(
        self,
        client: BinancePublicClient | None = None,
        candle_service: CandleService | None = None,
    ) -> None:
        self.client = client or BinancePublicClient()
        self.candle_service = candle_service or CandleService(client=self.client)

    async def load_history(
        self,
        *,
        symbol: str,
        interval: str,
        days: int,
        progress_callback: HistoricalProgressCallback | None = None,
    ) -> HistoricalLoadResult:
        """Загружает историю за последние N дней чанками по 1000 свечей.

        Binance ограничивает размер одного ответа, поэтому загрузка выполняется
        последовательно по `startTime/endTime`. Если биржа вернула пустой список,
        цикл завершается без попытки вставить пустой батч в БД.
        """

        if days <= 0:
            raise ValueError("Параметр days должен быть положительным целым числом.")

        finished_at = datetime.now(UTC)
        started_at = finished_at - timedelta(days=days)
        cursor_ms = self._to_millis(started_at)
        end_time_ms = self._to_millis(finished_at)

        chunks_loaded = 0
        candles_saved = 0
        first_open_time: datetime | None = None
        last_open_time: datetime | None = None

        while cursor_ms < end_time_ms:
            raw_candles = await self.client.get_klines(
                symbol=symbol,
                interval=interval,
                limit=self.MAX_CANDLES_PER_REQUEST,
                start_time_ms=cursor_ms,
                end_time_ms=end_time_ms,
            )
            if not raw_candles:
                break

            saved_now = self.candle_service.store_candles(symbol=symbol, interval=interval, raw_candles=raw_candles)
            chunks_loaded += 1
            candles_saved += saved_now

            batch_first_open = self._from_millis(int(raw_candles[0]["open_time"]))
            batch_last_open = self._from_millis(int(raw_candles[-1]["open_time"]))
            batch_last_close_ms = int(raw_candles[-1]["close_time"])

            if first_open_time is None:
                first_open_time = batch_first_open
            last_open_time = batch_last_open

            if progress_callback is not None:
                progress_callback(chunks_loaded, candles_saved, min(batch_last_close_ms, end_time_ms))

            next_cursor_ms = batch_last_close_ms + 1
            if next_cursor_ms <= cursor_ms:
                break
            cursor_ms = next_cursor_ms

        return HistoricalLoadResult(
            symbol=symbol.upper(),
            interval=interval,
            days=days,
            chunks_loaded=chunks_loaded,
            candles_saved=candles_saved,
            started_at=started_at,
            finished_at=finished_at,
            first_open_time=first_open_time,
            last_open_time=last_open_time,
        )

    @staticmethod
    def _to_millis(value: datetime) -> int:
        """Переводит UTC datetime в миллисекунды Unix time."""

        normalized = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        return int(normalized.timestamp() * 1000)

    @staticmethod
    def _from_millis(value: int) -> datetime:
        """Переводит миллисекунды Unix time в UTC datetime."""

        return datetime.fromtimestamp(value / 1000, tz=UTC)
