"""Загрузка и сохранение свечей."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.db.models import Candle
from app.db.session import session_scope
from app.exchange.binance_public_client import BinancePublicClient


class CandleService:
    """Сервис загрузки и upsert свечей в PostgreSQL."""

    def __init__(self, client: BinancePublicClient | None = None) -> None:
        self.client = client or BinancePublicClient()

    async def fetch_and_store_candles(self, symbol: str, interval: str, limit: int) -> int:
        """Получает свечи Binance и сохраняет их в БД.

        При конфликте по `symbol + interval + open_time` обновляются
        значения OHLCV и close_time. Это позволяет безопасно повторно
        дотягивать историю и дообновлять последнюю свечу.
        """

        raw_candles = await self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
        return self.store_candles(symbol=symbol, interval=interval, raw_candles=raw_candles)

    def store_candles(self, symbol: str, interval: str, raw_candles: list[dict[str, object]]) -> int:
        """Сохраняет уже полученные свечи в БД.

        Этот метод нужен, чтобы один и тот же upsert можно было переиспользовать
        и для короткой подзагрузки, и для длинной исторической загрузки по чанкам.
        """

        if not raw_candles:
            return 0

        rows = [self._normalize_candle(symbol=symbol, interval=interval, payload=item) for item in raw_candles]

        with session_scope() as session:
            statement = self._build_upsert_statement(session=session, rows=rows)
            session.execute(statement)

        return len(rows)

    @staticmethod
    def _build_upsert_statement(session: Session, rows: list[dict[str, object]]):
        """Собирает dialect-aware upsert для PostgreSQL и SQLite.

        В production проект рассчитан на PostgreSQL, но тесты используют SQLite.
        Поэтому SQL для upsert выбирается по текущему диалекту, а не пришивается
        только к PostgreSQL.
        """

        dialect_name = session.bind.dialect.name if session.bind is not None else "postgresql"
        if dialect_name == "sqlite":
            statement = sqlite_insert(Candle).values(rows)
            update_columns = {
                "open": statement.excluded.open,
                "high": statement.excluded.high,
                "low": statement.excluded.low,
                "close": statement.excluded.close,
                "volume": statement.excluded.volume,
                "close_time": statement.excluded.close_time,
            }
            return statement.on_conflict_do_update(
                index_elements=["symbol", "interval", "open_time"],
                set_=update_columns,
            )

        statement = postgres_insert(Candle).values(rows)
        update_columns = {
            "open": statement.excluded.open,
            "high": statement.excluded.high,
            "low": statement.excluded.low,
            "close": statement.excluded.close,
            "volume": statement.excluded.volume,
            "close_time": statement.excluded.close_time,
        }
        return statement.on_conflict_do_update(
            constraint="uq_candles_symbol_interval_open_time",
            set_=update_columns,
        )

    @staticmethod
    def _normalize_candle(symbol: str, interval: str, payload: dict[str, object]) -> dict[str, object]:
        """Приводит ответ Binance к формату БД."""

        return {
            "symbol": symbol.upper(),
            "interval": interval,
            "open_time": datetime.fromtimestamp(int(payload["open_time"]) / 1000, tz=UTC),
            "open": Decimal(str(payload["open"])),
            "high": Decimal(str(payload["high"])),
            "low": Decimal(str(payload["low"])),
            "close": Decimal(str(payload["close"])),
            "volume": Decimal(str(payload["volume"])),
            "close_time": datetime.fromtimestamp(int(payload["close_time"]) / 1000, tz=UTC),
        }
