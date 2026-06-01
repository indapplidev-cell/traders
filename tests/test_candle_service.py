from __future__ import annotations

import asyncio

from app.market.candle_service import CandleService


class EmptyKlinesClient:
    """Тестовый клиент, который имитирует пустой ответ Binance."""

    async def get_klines(self, symbol: str, interval: str, limit: int = 300) -> list[dict]:
        _ = (symbol, interval, limit)
        return []


def test_candle_service_returns_zero_for_empty_response(monkeypatch) -> None:
    """Проверяет, что пустой ответ не приводит к попытке вставки в БД."""

    for key in ("DATABASE_URL", "BINANCE_PUBLIC_REST_URL", "PAPER_POSITION_SIZE_FRACTION", "PAPER_RISK_PER_TRADE"):
        monkeypatch.delenv(key, raising=False)

    service = CandleService(client=EmptyKlinesClient())

    saved_count = asyncio.run(service.fetch_and_store_candles(symbol="BTCUSDT", interval="15m", limit=10))

    assert saved_count == 0
