from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.db.models import MarketCandles


class CandleRepository:
    UPSERT_BATCH_SIZE = 500

    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_many(self, candles: list[dict[str, Any]]) -> int:
        if not candles:
            return 0

        for start in range(0, len(candles), self.UPSERT_BATCH_SIZE):
            batch = candles[start : start + self.UPSERT_BATCH_SIZE]
            statement = self._build_insert_statement(batch)
            excluded = statement.excluded
            update_columns = {
                column.name: getattr(excluded, column.name)
                for column in MarketCandles.__table__.columns
                if column.name not in {"id", "created_at"}
            }
            upsert_statement = statement.on_conflict_do_update(
                index_elements=["symbol", "interval", "open_time"],
                set_=update_columns,
            )
            self._session.execute(upsert_statement)
        self._session.commit()
        return len(candles)

    def get_range(
        self,
        symbol: str,
        interval: str,
        start_at: datetime,
        end_at: datetime,
    ) -> list[MarketCandles]:
        statement = (
            select(MarketCandles)
            .where(MarketCandles.symbol == symbol)
            .where(MarketCandles.interval == interval)
            .where(MarketCandles.open_time >= start_at)
            .where(MarketCandles.open_time < end_at)
            .order_by(MarketCandles.open_time.asc())
        )
        return list(self._session.scalars(statement))

    def count_range(
        self,
        symbol: str,
        interval: str,
        start_at: datetime,
        end_at: datetime,
    ) -> int:
        statement = (
            select(func.count())
            .select_from(MarketCandles)
            .where(MarketCandles.symbol == symbol)
            .where(MarketCandles.interval == interval)
            .where(MarketCandles.open_time >= start_at)
            .where(MarketCandles.open_time < end_at)
        )
        return int(self._session.scalar(statement) or 0)

    def get_last_open_time(self, symbol: str, interval: str) -> datetime | None:
        statement = (
            select(func.max(MarketCandles.open_time))
            .where(MarketCandles.symbol == symbol)
            .where(MarketCandles.interval == interval)
        )
        return self._session.scalar(statement)

    def get_all(self, symbol: str, interval: str) -> list[MarketCandles]:
        statement = (
            select(MarketCandles)
            .where(MarketCandles.symbol == symbol)
            .where(MarketCandles.interval == interval)
            .order_by(MarketCandles.open_time.asc())
        )
        return list(self._session.scalars(statement))

    def get_last_n(self, symbol: str, interval: str, limit: int) -> list[MarketCandles]:
        statement = (
            select(MarketCandles)
            .where(MarketCandles.symbol == symbol)
            .where(MarketCandles.interval == interval)
            .order_by(MarketCandles.open_time.desc())
            .limit(limit)
        )
        return list(reversed(list(self._session.scalars(statement))))

    def _build_insert_statement(self, candles: list[dict[str, Any]]):
        dialect_name = self._session.bind.dialect.name if self._session.bind is not None else ""
        if dialect_name == "postgresql":
            return postgresql_insert(MarketCandles).values(candles)
        if dialect_name == "sqlite":
            return sqlite_insert(MarketCandles).values(candles)
        raise ValueError(f"Unsupported database dialect for candle upsert: {dialect_name}")
