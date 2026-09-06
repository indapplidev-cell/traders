"""Historical-only MAE/MFE diagnostics for closed PAPER trades."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
import json
from pathlib import Path
from typing import Literal, Sequence


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


__all__ = (
    "ClosedTradePath", "OutcomeCandle", "OutcomeDiagnosticsStore",
    "StopTargetDiagnostics", "compute_stop_target_diagnostics",
)
