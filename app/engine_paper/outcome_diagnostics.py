"""Historical-only MAE/MFE diagnostics for closed PAPER trades."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
import json
from pathlib import Path
from datetime import timezone
from typing import Literal, Sequence

from sqlalchemy import select

from app.db.paper_models import PaperPositionRecord, ScalpingOutcomeDiagnosticRecord
from app.engine_market_data.db.candle_tables import Candle1m


OUTCOME_DIAGNOSTIC_VERSION = "scalping-mae-mfe-v1"


@dataclass(frozen=True, slots=True)
class OutcomeCandle:
    open_time_ms: int
    high: Decimal
    low: Decimal


@dataclass(frozen=True, slots=True)
class ClosedTradePath:
    position_id: str
    side: Literal["LONG", "SHORT"]
    entry_price: Decimal
    planned_stop: Decimal
    planned_target: Decimal
    actual_exit_price: Decimal
    opened_at_ms: int
    closed_at_ms: int
    exit_reason: str


@dataclass(frozen=True, slots=True)
class StopTargetDiagnostics:
    position_id: str
    mae: Decimal
    mfe: Decimal
    time_to_mae_ms: int
    time_to_mfe_ms: int
    planned_stop_distance: Decimal
    actual_stop_slippage: Decimal | None
    planned_target_distance: Decimal
    target_reached_after_stop: bool
    max_favorable_before_stop: Decimal
    max_adverse_before_target: Decimal
    holding_time_ms: int
    historical_diagnostic_only: Literal[True] = True


def compute_stop_target_diagnostics(
    trade: ClosedTradePath, candles: Sequence[OutcomeCandle]
) -> StopTargetDiagnostics:
    if trade.closed_at_ms < trade.opened_at_ms or trade.entry_price <= 0:
        raise ValueError("invalid closed trade interval")
    path = tuple(
        candle for candle in candles
        if trade.opened_at_ms <= candle.open_time_ms <= trade.closed_at_ms
    )
    if not path:
        raise ValueError("closed trade diagnostics require a causal candle path")
    if trade.side == "LONG":
        adverse = tuple(max(Decimal("0"), trade.entry_price - row.low) for row in path)
        favorable = tuple(max(Decimal("0"), row.high - trade.entry_price) for row in path)
        stop_hit = lambda row: row.low <= trade.planned_stop
        target_hit = lambda row: row.high >= trade.planned_target
        stop_slippage = trade.planned_stop - trade.actual_exit_price
    else:
        adverse = tuple(max(Decimal("0"), row.high - trade.entry_price) for row in path)
        favorable = tuple(max(Decimal("0"), trade.entry_price - row.low) for row in path)
        stop_hit = lambda row: row.high >= trade.planned_stop
        target_hit = lambda row: row.low <= trade.planned_target
        stop_slippage = trade.actual_exit_price - trade.planned_stop
    mae = max(adverse)
    mfe = max(favorable)
    mae_index = adverse.index(mae)
    mfe_index = favorable.index(mfe)
    stop_index = next((i for i, row in enumerate(path) if stop_hit(row)), None)
    target_index = next((i for i, row in enumerate(path) if target_hit(row)), None)
    before_stop = favorable if stop_index is None else favorable[: stop_index + 1]
    before_target = adverse if target_index is None else adverse[: target_index + 1]
    target_after_stop = bool(
        stop_index is not None and any(target_hit(row) for row in path[stop_index + 1 :])
    )
    return StopTargetDiagnostics(
        position_id=trade.position_id, mae=mae, mfe=mfe,
        time_to_mae_ms=path[mae_index].open_time_ms - trade.opened_at_ms,
        time_to_mfe_ms=path[mfe_index].open_time_ms - trade.opened_at_ms,
        planned_stop_distance=abs(trade.entry_price - trade.planned_stop),
        actual_stop_slippage=(max(Decimal("0"), stop_slippage) if "STOP" in trade.exit_reason else None),
        planned_target_distance=abs(trade.planned_target - trade.entry_price),
        target_reached_after_stop=target_after_stop,
        max_favorable_before_stop=max(before_stop, default=Decimal("0")),
        max_adverse_before_target=max(before_target, default=Decimal("0")),
        holding_time_ms=trade.closed_at_ms - trade.opened_at_ms,
    )


class OutcomeDiagnosticsStore:
    """Idempotent offline store; it has no command or position dependencies."""

    def __init__(self, path: Path):
        self.path = path

    def save(self, value: StopTargetDiagnostics) -> None:
        rows = {}
        if self.path.exists():
            rows = json.loads(self.path.read_text(encoding="utf-8"))
        rows[value.position_id] = {
            key: str(item) if isinstance(item, Decimal) else item
            for key, item in asdict(value).items()
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(rows, sort_keys=True), encoding="utf-8")
        temporary.replace(self.path)


class PostgresOutcomeDiagnosticsProcessor:
    """Compute exactly one bounded diagnostic when a PAPER position closes."""

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def process(self, position_id: str) -> StopTargetDiagnostics | None:
        with self._session_factory() as session, session.begin():
            if session.get(ScalpingOutcomeDiagnosticRecord, position_id) is not None:
                return None
            position = session.get(PaperPositionRecord, position_id)
            if position is None or position.state != "CLOSED" or position.closed_at is None:
                return None
            opened_ms = int(position.opened_at.astimezone(timezone.utc).timestamp() * 1000)
            closed_ms = int(position.closed_at.astimezone(timezone.utc).timestamp() * 1000)
            candles = tuple(session.scalars(
                select(Candle1m).where(
                    Candle1m.symbol == position.symbol,
                    Candle1m.open_time_ms >= opened_ms,
                    Candle1m.open_time_ms <= closed_ms,
                    Candle1m.is_closed.is_(True),
                ).order_by(Candle1m.open_time_ms)
            ))
            if not candles:
                return None
            diagnostic = compute_stop_target_diagnostics(
                ClosedTradePath(
                    position_id=position.position_id,
                    side=position.side,
                    entry_price=position.average_entry_price,
                    planned_stop=position.stop_price,
                    planned_target=position.target_price,
                    actual_exit_price=position.average_exit_price,
                    opened_at_ms=opened_ms,
                    closed_at_ms=closed_ms,
                    exit_reason=position.reason_code,
                ),
                tuple(OutcomeCandle(row.open_time_ms, row.high, row.low) for row in candles),
            )
            session.add(ScalpingOutcomeDiagnosticRecord(
                position_id=diagnostic.position_id,
                mae=diagnostic.mae, mfe=diagnostic.mfe,
                time_to_mae_ms=diagnostic.time_to_mae_ms,
                time_to_mfe_ms=diagnostic.time_to_mfe_ms,
                planned_stop_distance=diagnostic.planned_stop_distance,
                actual_stop_slippage=diagnostic.actual_stop_slippage,
                planned_target_distance=diagnostic.planned_target_distance,
                target_reached_after_stop=diagnostic.target_reached_after_stop,
                max_favorable_before_stop=diagnostic.max_favorable_before_stop,
                max_adverse_before_target=diagnostic.max_adverse_before_target,
                holding_time_ms=diagnostic.holding_time_ms,
                diagnostic_version=OUTCOME_DIAGNOSTIC_VERSION,
                created_at=position.closed_at,
            ))
            return diagnostic


__all__ = (
    "ClosedTradePath", "OutcomeCandle", "OutcomeDiagnosticsStore",
    "OUTCOME_DIAGNOSTIC_VERSION", "PostgresOutcomeDiagnosticsProcessor",
    "StopTargetDiagnostics", "compute_stop_target_diagnostics",
)
