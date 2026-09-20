"""Transactional production trading-universe activation authority."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.paper_models import (
    PaperFirstCanarySessionRecord, TradingUniverseRuntimeStateRecord,
    TradingUniverseSymbolPreflightRecord,
)
from app.engine_paper.first_canary_correlation import TERMINAL_CANARY_STATES
from app.trading_universe.domain import TradingUniverseVersion, resolve_universe, runtime_universe


class TradingUniverseActivationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class TradingUniverseRuntimeState:
    active_version_id: str
    previous_version_id: str | None
    generation: int
    activated_at: datetime
    activation_reason: str
    runtime_revision: str


def _snapshot(row: TradingUniverseRuntimeStateRecord) -> TradingUniverseRuntimeState:
    resolve_universe(row.active_version_id)
    if row.previous_version_id is not None:
        resolve_universe(row.previous_version_id)
    activated_at = row.activated_at
    if activated_at.tzinfo is None:
        activated_at = activated_at.replace(tzinfo=timezone.utc)
    return TradingUniverseRuntimeState(
        active_version_id=row.active_version_id,
        previous_version_id=row.previous_version_id,
        generation=row.generation,
        activated_at=activated_at,
        activation_reason=row.activation_reason,
        runtime_revision=row.runtime_revision,
    )


class SqlAlchemyTradingUniverseStore:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def current_state(self) -> TradingUniverseRuntimeState:
        with self._session_factory() as session:
            row = session.get(TradingUniverseRuntimeStateRecord, "PRODUCTION")
            if row is None:
                raise TradingUniverseActivationError("TRADING_UNIVERSE_STATE_UNAVAILABLE")
            return _snapshot(row)

    def active_universe(self) -> TradingUniverseVersion:
        return runtime_universe(self.current_state().active_version_id)

    def activate(
        self,
        *,
        expected_active_version_id: str,
        target_version_id: str,
        reason: str,
        runtime_revision: str,
        now: datetime | None = None,
    ) -> TradingUniverseRuntimeState:
        target = resolve_universe(target_version_id)
        if not reason or len(reason) > 80 or not runtime_revision or len(runtime_revision) > 64:
            raise TradingUniverseActivationError("INVALID_ACTIVATION_AUDIT")
        with self._session_factory() as session:
            try:
                row = session.scalar(
                    select(TradingUniverseRuntimeStateRecord)
                    .where(TradingUniverseRuntimeStateRecord.environment == "PRODUCTION")
                    .with_for_update()
                )
                if row is None:
                    raise TradingUniverseActivationError("TRADING_UNIVERSE_STATE_UNAVAILABLE")
                if row.active_version_id == target.version_id:
                    return _snapshot(row)
                if row.active_version_id != expected_active_version_id:
                    raise TradingUniverseActivationError("STALE_ACTIVE_UNIVERSE")
                activation_time = now or datetime.now(timezone.utc)
                if target.version_id == "trading-universe-v3":
                    preflight = tuple(session.scalars(select(
                        TradingUniverseSymbolPreflightRecord
                    ).where(
                        TradingUniverseSymbolPreflightRecord.environment == "PRODUCTION",
                        TradingUniverseSymbolPreflightRecord.universe_version_id == target.version_id,
                    )))
                    by_symbol = {item.symbol: item for item in preflight}
                    minimum_observed_at = activation_time - timedelta(minutes=15)
                    if set(by_symbol) != set(target.symbols) or any(
                        not item.active
                        or item.status != "PASS"
                        or not item.one_minute_fresh
                        or not item.five_minute_fresh
                        or item.commission_authority != "BINANCE_ACCOUNT_COMMISSION_SNAPSHOT"
                        or (
                            item.observed_at.replace(tzinfo=timezone.utc)
                            if item.observed_at.tzinfo is None else item.observed_at
                        ) < minimum_observed_at
                        for item in by_symbol.values()
                    ):
                        raise TradingUniverseActivationError("SYMBOL_PREFLIGHT_NOT_READY")
                active_canary = session.scalar(
                    select(PaperFirstCanarySessionRecord.canary_id)
                    .where(PaperFirstCanarySessionRecord.state.not_in(tuple(TERMINAL_CANARY_STATES)))
                    .limit(1)
                )
                if active_canary is not None:
                    raise TradingUniverseActivationError("ACTIVE_CANARY_BLOCKS_UNIVERSE_ACTIVATION")
                row.previous_version_id = row.active_version_id
                row.active_version_id = target.version_id
                row.generation += 1
                row.activated_at = activation_time
                row.activation_reason = reason
                row.runtime_revision = runtime_revision
                session.flush()
                value = _snapshot(row)
                session.commit()
                return value
            except TradingUniverseActivationError:
                session.rollback()
                raise
            except SQLAlchemyError as exc:
                session.rollback()
                raise TradingUniverseActivationError("TRADING_UNIVERSE_ACTIVATION_FAILED") from exc


__all__ = (
    "SqlAlchemyTradingUniverseStore",
    "TradingUniverseActivationError",
    "TradingUniverseRuntimeState",
)
