"""Immutable position state and transition result."""
from __future__ import annotations
from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.engine_execution import ExecutionMode
from app.engine_position.enums import PositionSide, PositionStatus
from app.engine_position.serialization import (canonical_json, decimal, freeze, parse_utc,
                                                position_schema_version, require_schema, thaw, utc_iso)


TERMINAL_STATUSES = frozenset({PositionStatus.CLOSED, PositionStatus.REJECTED,
                               PositionStatus.CANCELLED, PositionStatus.DISABLED})


@dataclass(frozen=True, slots=True)
class Position:
    position_id: str
    position_key: str
    execution_intent_id: str
    execution_acknowledgement_id: str
    execution_idempotency_key: str
    mode: ExecutionMode
    symbol: str
    side: PositionSide
    status: PositionStatus
    opened_at_utc: datetime | None
    updated_at_utc: datetime
    closed_at_utc: datetime | None
    source_timeframe: str
    source_window_close_ms: int
    setup_id: str
    strategy_decision_id: str
    risk_decision_id: str
    initial_quantity: Decimal
    open_quantity: Decimal
    closed_quantity: Decimal
    average_entry_price: Decimal
    last_mark_price: Decimal
    stop_price: Decimal | None
    target_price: Decimal | None
    gross_realized_pnl: Decimal = Decimal("0")
    fees_paid: Decimal = Decimal("0")
    net_realized_pnl: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    close_reason: str | None = None
    applied_event_ids: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    position_schema_version: int = field(default=position_schema_version, init=False)

    def __post_init__(self) -> None:
        if self.position_schema_version != position_schema_version:
            raise ValueError("unsupported position schema version")
        object.__setattr__(self, "mode", ExecutionMode(self.mode))
        object.__setattr__(self, "side", PositionSide(self.side))
        object.__setattr__(self, "status", PositionStatus(self.status))
        object.__setattr__(self, "symbol", str(self.symbol).upper())
        for name in ("initial_quantity", "open_quantity", "closed_quantity", "average_entry_price",
                     "last_mark_price", "gross_realized_pnl", "fees_paid", "net_realized_pnl",
                     "unrealized_pnl"):
            object.__setattr__(self, name, decimal(getattr(self, name)))
        object.__setattr__(self, "stop_price", decimal(self.stop_price, optional=True))
        object.__setattr__(self, "target_price", decimal(self.target_price, optional=True))
        object.__setattr__(self, "applied_event_ids", tuple(str(v) for v in self.applied_event_ids))
        object.__setattr__(self, "reason_codes", tuple(str(v) for v in self.reason_codes))
        object.__setattr__(self, "warnings", tuple(str(v) for v in self.warnings))
        object.__setattr__(self, "metadata", freeze(self.metadata))
        utc_iso(self.updated_at_utc)
        if self.opened_at_utc is not None:
            utc_iso(self.opened_at_utc)
        if self.closed_at_utc is not None:
            utc_iso(self.closed_at_utc)
        if not self.position_id or not self.position_key or not self.symbol:
            raise ValueError("position identity and symbol are required")
        if min(self.initial_quantity, self.open_quantity, self.closed_quantity) < 0:
            raise ValueError("position quantities cannot be negative")
        if self.open_quantity + self.closed_quantity != self.initial_quantity:
            raise ValueError("open_quantity + closed_quantity must equal initial_quantity")
        if self.initial_quantity <= 0 or self.average_entry_price <= 0 or self.last_mark_price <= 0:
            raise ValueError("quantity and prices must be positive")
        if self.fees_paid < 0:
            raise ValueError("fees cannot be negative")
        if self.status in {PositionStatus.OPEN, PositionStatus.PARTIALLY_CLOSED} and self.open_quantity <= 0:
            raise ValueError("active position requires open quantity")
        if self.status is PositionStatus.CLOSED and (self.open_quantity != 0 or self.closed_at_utc is None):
            raise ValueError("closed position requires zero open quantity and closed timestamp")
        if self.status is not PositionStatus.CLOSED and self.closed_at_utc is not None:
            raise ValueError("closed_at_utc is only valid for CLOSED")

    def to_dict(self) -> dict[str, Any]:
        return {
            "position_schema_version": self.position_schema_version,
            "position_id": self.position_id, "position_key": self.position_key,
            "execution_intent_id": self.execution_intent_id,
            "execution_acknowledgement_id": self.execution_acknowledgement_id,
            "execution_idempotency_key": self.execution_idempotency_key,
            "mode": self.mode.value, "symbol": self.symbol, "side": self.side.value,
            "status": self.status.value,
            "opened_at_utc": None if self.opened_at_utc is None else utc_iso(self.opened_at_utc),
            "updated_at_utc": utc_iso(self.updated_at_utc),
            "closed_at_utc": None if self.closed_at_utc is None else utc_iso(self.closed_at_utc),
            "source_timeframe": self.source_timeframe,
            "source_window_close_ms": self.source_window_close_ms,
            "setup_id": self.setup_id, "strategy_decision_id": self.strategy_decision_id,
            "risk_decision_id": self.risk_decision_id,
            "initial_quantity": str(self.initial_quantity), "open_quantity": str(self.open_quantity),
            "closed_quantity": str(self.closed_quantity),
            "average_entry_price": str(self.average_entry_price), "last_mark_price": str(self.last_mark_price),
            "stop_price": None if self.stop_price is None else str(self.stop_price),
            "target_price": None if self.target_price is None else str(self.target_price),
            "gross_realized_pnl": str(self.gross_realized_pnl), "fees_paid": str(self.fees_paid),
            "net_realized_pnl": str(self.net_realized_pnl), "unrealized_pnl": str(self.unrealized_pnl),
            "close_reason": self.close_reason, "applied_event_ids": list(self.applied_event_ids),
            "reason_codes": list(self.reason_codes), "warnings": list(self.warnings),
            "metadata": thaw(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Position":
        require_schema(payload)
        values = dict(payload); values.pop("position_schema_version", None)
        for name in ("opened_at_utc", "updated_at_utc", "closed_at_utc"):
            if values.get(name) is not None:
                values[name] = parse_utc(str(values[name]))
        return cls(**values)

    def canonical_json(self) -> str:
        return canonical_json(self.to_dict())
@dataclass(frozen=True, slots=True)
class PositionTransitionResult:
    position_id: str
    event_id: str
    previous_status: PositionStatus
    new_status: PositionStatus
    applied: bool
    occurred_at_utc: datetime
    reason_codes: tuple[str, ...]
    warnings: tuple[str, ...]
    position: Position
    metadata: Mapping[str, Any] = field(default_factory=dict)
    position_schema_version: int = field(default=position_schema_version, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "previous_status", PositionStatus(self.previous_status))
        object.__setattr__(self, "new_status", PositionStatus(self.new_status))
        object.__setattr__(self, "reason_codes", tuple(str(v) for v in self.reason_codes))
        object.__setattr__(self, "warnings", tuple(str(v) for v in self.warnings))
        object.__setattr__(self, "metadata", freeze(self.metadata)); utc_iso(self.occurred_at_utc)

    def to_dict(self) -> dict[str, Any]:
        return {"position_schema_version": 1, "position_id": self.position_id,
                "event_id": self.event_id, "previous_status": self.previous_status.value,
                "new_status": self.new_status.value, "applied": self.applied,
                "occurred_at_utc": utc_iso(self.occurred_at_utc),
                "reason_codes": list(self.reason_codes), "warnings": list(self.warnings),
                "position": self.position.to_dict(), "metadata": thaw(self.metadata)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PositionTransitionResult":
        require_schema(payload)
        return cls(position_id=str(payload["position_id"]), event_id=str(payload["event_id"]),
                   previous_status=PositionStatus(payload["previous_status"]),
                   new_status=PositionStatus(payload["new_status"]), applied=bool(payload["applied"]),
                   occurred_at_utc=parse_utc(str(payload["occurred_at_utc"])),
                   reason_codes=tuple(payload.get("reason_codes", ())), warnings=tuple(payload.get("warnings", ())),
                   position=Position.from_dict(payload["position"]), metadata=payload.get("metadata", {}))

    def canonical_json(self) -> str:
        return canonical_json(self.to_dict())

