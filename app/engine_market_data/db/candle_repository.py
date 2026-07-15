"""Closed-candle repository with PostgreSQL idempotent upsert."""

from collections.abc import Callable, Sequence
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
from typing import Iterator

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.engine_market_data.candle import Candle
from app.engine_market_data.db.candle_tables import CANDLE_MODELS, CandleTableMixin
from app.engine_market_data.market_symbol import normalize_market_symbol
from app.engine_market_data.timeframe import timeframe_to_milliseconds


# PostgreSQL's extended query protocol accepts at most 65,535 bind parameters.
# A candle upsert binds 15 values, so 1,000 rows leaves ample headroom and also
# matches Binance's maximum public kline batch size.
MAX_UPSERT_BATCH_SIZE = 1000
MAX_LOOKUP_BATCH_SIZE = 10_000


def utc_datetime_from_ms(timestamp_ms: int) -> datetime:
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)


def candle_checksum(candle: Candle) -> str:
    values = (candle.open, candle.high, candle.low, candle.close, candle.volume,
              candle.quote_volume, candle.trades_count, candle.close_time_ms)
    return hashlib.sha256("|".join(str(value) for value in values).encode()).hexdigest()


class CandleRepository:
    def __init__(self, session_or_factory: Session | Callable[[], Session]) -> None:
        self._session_or_factory = session_or_factory

    @contextmanager
    def _session(self) -> Iterator[Session]:
        if isinstance(self._session_or_factory, Session):
            yield self._session_or_factory
            return
        with self._session_or_factory() as session:
            yield session

    @staticmethod
    def _model(timeframe: str) -> type[CandleTableMixin]:
        try:
            return CANDLE_MODELS[timeframe]
        except KeyError as exc:
            raise ValueError(f"No candle table for timeframe {timeframe!r}") from exc

    @staticmethod
    def _values(candle: Candle) -> dict[str, object]:
        if not candle.is_closed:
            raise ValueError("PostgreSQL candle tables accept closed candles only")
        return {
            "symbol": candle.symbol, "open_time_ms": candle.open_time_ms,
            "close_time_ms": candle.close_time_ms,
            "open_time_utc": utc_datetime_from_ms(candle.open_time_ms),
            "close_time_utc": utc_datetime_from_ms(candle.close_time_ms),
            "open": candle.open, "high": candle.high, "low": candle.low,
            "close": candle.close, "volume": candle.volume,
            "quote_volume": candle.quote_volume, "trades_count": candle.trades_count,
            "source": candle.source, "is_closed": True,
            "data_checksum": candle_checksum(candle),
        }

    def upsert_candle(self, candle: Candle) -> None:
        self.upsert_candles([candle])

    def upsert_candles(self, candles: Sequence[Candle]) -> int:
        if not candles:
            return 0
        timeframes = {c.timeframe for c in candles}
        if len(timeframes) != 1:
            return sum(self.upsert_candles([c for c in candles if c.timeframe == tf]) for tf in timeframes)
        return sum(
            self._upsert_batch(candles[offset:offset + MAX_UPSERT_BATCH_SIZE])
            for offset in range(0, len(candles), MAX_UPSERT_BATCH_SIZE)
        )

    def _upsert_batch(self, candles: Sequence[Candle]) -> int:
        model = self._model(candles[0].timeframe)
        values = [self._values(candle) for candle in candles]
        stmt = insert(model).values(values)
        excluded = stmt.excluded
        update_values = {
            name: getattr(excluded, name) for name in (
                "close_time_ms", "open_time_utc", "close_time_utc", "open", "high", "low",
                "close", "volume", "quote_volume", "trades_count", "source", "data_checksum",
            )
        }
        update_values["is_closed"] = True
        update_values["updated_at_utc"] = func.now()
        stmt = stmt.on_conflict_do_update(
            index_elements=[model.symbol, model.open_time_ms], set_=update_values,
            where=model.data_checksum.is_distinct_from(excluded.data_checksum),
        )
        with self._session() as session:
            result = session.execute(stmt)
            session.commit()
            return max(result.rowcount or 0, 0)

    def get_candles(self, symbol: str, timeframe: str, start_time_ms: int | None = None,
                    end_time_ms: int | None = None, limit: int | None = None) -> list[Candle]:
        model = self._model(timeframe)
        query = select(model).where(model.symbol == normalize_market_symbol(symbol), model.is_closed.is_(True))
        if start_time_ms is not None: query = query.where(model.open_time_ms >= start_time_ms)
        if end_time_ms is not None: query = query.where(model.open_time_ms <= end_time_ms)
        if limit is not None:
            if limit < 0: raise ValueError("limit must be non-negative")
            query = query.order_by(model.open_time_ms.desc()).limit(limit)
        else:
            query = query.order_by(model.open_time_ms)
        with self._session() as session:
            rows = list(session.scalars(query))
        if limit is not None: rows.reverse()
        return [self._to_candle(row, timeframe) for row in rows]

    @staticmethod
    def _to_candle(row: CandleTableMixin, timeframe: str) -> Candle:
        return Candle(symbol=row.symbol, timeframe=timeframe, open_time_ms=row.open_time_ms,
            close_time_ms=row.close_time_ms, open=row.open, high=row.high, low=row.low,
            close=row.close, volume=row.volume, quote_volume=row.quote_volume,
            trades_count=row.trades_count, is_closed=True, source=row.source)

    def get_latest_closed_candle(self, symbol: str, timeframe: str) -> Candle | None:
        candles = self.get_candles(symbol, timeframe, limit=1)
        return candles[0] if candles else None

    def has_candle(self, symbol: str, timeframe: str, open_time_ms: int) -> bool:
        model = self._model(timeframe)
        query = select(model.id).where(model.symbol == normalize_market_symbol(symbol),
            model.open_time_ms == open_time_ms, model.is_closed.is_(True)).limit(1)
        with self._session() as session: return session.scalar(query) is not None

    def count(self, symbol: str, timeframe: str) -> int:
        model = self._model(timeframe)
        query = select(func.count()).select_from(model).where(
            model.symbol == normalize_market_symbol(symbol), model.is_closed.is_(True))
        with self._session() as session: return int(session.scalar(query) or 0)

    def find_missing_open_times(self, symbol: str, timeframe: str,
                                expected_open_times: Sequence[int]) -> list[int]:
        expected = sorted(set(expected_open_times))
        if not expected: return []
        duration = timeframe_to_milliseconds(timeframe)
        if any(value < 0 or value % duration for value in expected):
            raise ValueError("expected open times must be non-negative and timeframe-aligned")
        model = self._model(timeframe)
        normalized = normalize_market_symbol(symbol)
        existing: set[int] = set()
        for offset in range(0, len(expected), MAX_LOOKUP_BATCH_SIZE):
            existing.update(self._find_existing_open_times_batch(
                model, normalized, expected[offset:offset + MAX_LOOKUP_BATCH_SIZE]))
        return [value for value in expected if value not in existing]

    def _find_existing_open_times_batch(
        self, model: type[CandleTableMixin], symbol: str, expected: Sequence[int],
    ) -> set[int]:
        query = select(model.open_time_ms).where(
            model.symbol == symbol, model.open_time_ms.in_(expected), model.is_closed.is_(True))
        with self._session() as session:
            return set(session.scalars(query))
