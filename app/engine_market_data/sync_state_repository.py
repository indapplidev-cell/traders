"""PostgreSQL idempotent upsert for daemon state (never candle data)."""

from collections.abc import Callable
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.engine_market_data.continuous_sync_state import MarketDataSyncState, SyncStateUpdate
from app.engine_market_data.market_symbol import normalize_market_symbol


class SyncStateRepository:
    def __init__(self, session_or_factory: Session | Callable[[], Session]) -> None:
        self._session_or_factory = session_or_factory

    @contextmanager
    def _session(self) -> Iterator[Session]:
        if isinstance(self._session_or_factory, Session):
            yield self._session_or_factory
            return
        with self._session_or_factory() as session:
            yield session

    def upsert(self, state: SyncStateUpdate) -> None:
        values = state.values()
        values["symbol"] = normalize_market_symbol(state.symbol)
        stmt = insert(MarketDataSyncState).values(**values)
        excluded = stmt.excluded
        mutable = {key: getattr(excluded, key) for key in values if key not in {"symbol", "timeframe"}}
        mutable["updated_at"] = excluded.updated_at
        stmt = stmt.on_conflict_do_update(
            index_elements=[MarketDataSyncState.symbol, MarketDataSyncState.timeframe], set_=mutable)
        with self._session() as session:
            session.execute(stmt)
            session.commit()

    def get(self, symbol: str, timeframe: str) -> MarketDataSyncState | None:
        query = select(MarketDataSyncState).where(
            MarketDataSyncState.symbol == normalize_market_symbol(symbol),
            MarketDataSyncState.timeframe == timeframe,
        )
        with self._session() as session:
            return session.scalar(query)

    def list_for(self, symbols: list[str], timeframes: list[str]) -> list[MarketDataSyncState]:
        query = select(MarketDataSyncState).where(
            MarketDataSyncState.symbol.in_([normalize_market_symbol(value) for value in symbols]),
            MarketDataSyncState.timeframe.in_(timeframes),
        )
        with self._session() as session:
            return list(session.scalars(query))

