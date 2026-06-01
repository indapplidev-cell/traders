"""Публичный REST-клиент Binance."""

from __future__ import annotations

from typing import Any

import httpx

from app.config.settings import get_settings


class BinancePublicClient:
    """Клиент для чтения публичных рыночных данных Binance.

    На этом этапе используются только публичные REST-методы и никакие
    API-ключи проектом не запрашиваются и не поддерживаются.
    """

    def __init__(self, timeout: float = 10.0) -> None:
        self.settings = get_settings()
        self.timeout = timeout

    async def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 300,
        start_time_ms: int | None = None,
        end_time_ms: int | None = None,
    ) -> list[dict[str, Any]]:
        """Возвращает нормализованный список свечей Binance.

        В ответе Binance приходит массив массивов. Здесь он приводится
        к словарям с понятными именами полей, чтобы остальной код не был
        жёстко привязан к позициям элементов внутри исходного массива.
        """

        url = f"{self.settings.binance_public_rest_url}/api/v3/klines"
        params = {"symbol": symbol.upper(), "interval": interval, "limit": limit}
        if start_time_ms is not None:
            params["startTime"] = start_time_ms
        if end_time_ms is not None:
            params["endTime"] = end_time_ms

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise RuntimeError("Не удалось получить свечи Binance: превышено время ожидания ответа.") from exc
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Не удалось получить свечи Binance: HTTP {exc.response.status_code}."
            ) from exc
        except httpx.HTTPError as exc:
            raise RuntimeError("Не удалось получить свечи Binance: сетевая ошибка.") from exc

        payload = response.json()
        if not isinstance(payload, list):
            raise RuntimeError("Binance вернул неожиданный формат ответа для списка свечей.")

        normalized: list[dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, list) or len(item) < 7:
                raise RuntimeError("Binance вернул некорректную структуру свечи.")

            normalized.append(
                {
                    "open_time": item[0],
                    "open": item[1],
                    "high": item[2],
                    "low": item[3],
                    "close": item[4],
                    "volume": item[5],
                    "close_time": item[6],
                }
            )

        return normalized
