"""Immutable public models for safe execution intent and acknowledgement."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from types import MappingProxyType
from typing import Any

from app.engine_execution.enums import (
    ExecutionAcknowledgementStatus,
    ExecutionIntentStatus,
    ExecutionMode,
    ExecutionOrderType,
    ExecutionSide,
)
from app.engine_execution.serialization import canonical_json, execution_schema_version, parse_utc, utc_iso


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return tuple(_freeze(item) for item in sorted(value, key=repr))
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _decimal(value: Any, *, optional: bool = False) -> Decimal | None:
    if value is None and optional:
        return None
    if isinstance(value, bool) or value is None:
        raise ValueError("numeric contract value is missing")
    return value if isinstance(value, Decimal) else Decimal(str(value))


@dataclass(frozen=True, slots=True)
class ExecutionIntent:
    execution_intent_id: str
    idempotency_key: str
    created_at_utc: datetime
    symbol: str
    side: ExecutionSide
    execution_mode: ExecutionMode
    order_type: ExecutionOrderType
    quantity: Decimal
    reference_price: Decimal
    limit_price: Decimal | None
    stop_price: Decimal
    target_price: Decimal
    time_in_force: str | None
    reduce_only: bool
    strategy_decision_id: str
    risk_decision_id: str
    setup_id: str
    source_window_close_ms: int
    source_timeframe: str
    status: ExecutionIntentStatus
    reason_codes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", self.symbol.upper())
        object.__setattr__(self, "side", ExecutionSide(self.side))
        object.__setattr__(self, "execution_mode", ExecutionMode(self.execution_mode))
        object.__setattr__(self, "order_type", ExecutionOrderType(self.order_type))
        object.__setattr__(self, "status", ExecutionIntentStatus(self.status))
        object.__setattr__(self, "quantity", _decimal(self.quantity))
        object.__setattr__(self, "reference_price", _decimal(self.reference_price))
        object.__setattr__(self, "limit_price", _decimal(self.limit_price, optional=True))
        object.__setattr__(self, "stop_price", _decimal(self.stop_price))
        object.__setattr__(self, "target_price", _decimal(self.target_price))
        object.__setattr__(self, "reason_codes", tuple(str(value) for value in self.reason_codes))
        object.__setattr__(self, "warnings", tuple(str(value) for value in self.warnings))
        object.__setattr__(self, "metadata", _freeze(self.metadata))
        utc_iso(self.created_at_utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_schema_version": execution_schema_version,
            "execution_intent_id": self.execution_intent_id,
            "idempotency_key": self.idempotency_key,
            "created_at_utc": utc_iso(self.created_at_utc),
            "symbol": self.symbol,
            "side": self.side.value,
            "execution_mode": self.execution_mode.value,
            "order_type": self.order_type.value,
            "quantity": str(self.quantity),
            "reference_price": str(self.reference_price),
            "limit_price": None if self.limit_price is None else str(self.limit_price),
            "stop_price": str(self.stop_price),
            "target_price": str(self.target_price),
            "time_in_force": self.time_in_force,
            "reduce_only": self.reduce_only,
            "strategy_decision_id": self.strategy_decision_id,
            "risk_decision_id": self.risk_decision_id,
            "setup_id": self.setup_id,
            "source_window_close_ms": self.source_window_close_ms,
            "source_timeframe": self.source_timeframe,
            "status": self.status.value,
            "reason_codes": list(self.reason_codes),
            "warnings": list(self.warnings),
            "metadata": _thaw(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ExecutionIntent":
        if int(payload.get("execution_schema_version", 0)) != execution_schema_version:
            raise ValueError("unsupported execution schema version")
        values = dict(payload)
        values.pop("execution_schema_version", None)
        values["created_at_utc"] = parse_utc(str(values["created_at_utc"]))
        return cls(**values)

    def canonical_json(self) -> str:
        return canonical_json(self.to_dict())


@dataclass(frozen=True, slots=True)
class ExecutionAcknowledgement:
    execution_intent_id: str
    idempotency_key: str
    mode: ExecutionMode
    status: ExecutionAcknowledgementStatus
    accepted_at_utc: datetime | None
    external_order_id: str | None = None
    reason_codes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", ExecutionMode(self.mode))
        object.__setattr__(self, "status", ExecutionAcknowledgementStatus(self.status))
        object.__setattr__(self, "reason_codes", tuple(str(value) for value in self.reason_codes))
        object.__setattr__(self, "warnings", tuple(str(value) for value in self.warnings))
        object.__setattr__(self, "metadata", _freeze(self.metadata))
        if self.accepted_at_utc is not None:
            utc_iso(self.accepted_at_utc)
        if self.mode in {ExecutionMode.PAPER, ExecutionMode.DRY_RUN} and self.external_order_id is not None:
            raise ValueError("safe modes cannot expose an external order id")

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_schema_version": execution_schema_version,
            "execution_intent_id": self.execution_intent_id,
            "idempotency_key": self.idempotency_key,
            "mode": self.mode.value,
            "status": self.status.value,
            "accepted_at_utc": None if self.accepted_at_utc is None else utc_iso(self.accepted_at_utc),
            "external_order_id": self.external_order_id,
            "reason_codes": list(self.reason_codes),
            "warnings": list(self.warnings),
            "metadata": _thaw(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ExecutionAcknowledgement":
        if int(payload.get("execution_schema_version", 0)) != execution_schema_version:
            raise ValueError("unsupported execution schema version")
        values = dict(payload)
        values.pop("execution_schema_version", None)
        if values.get("accepted_at_utc") is not None:
            values["accepted_at_utc"] = parse_utc(str(values["accepted_at_utc"]))
        return cls(**values)

    def canonical_json(self) -> str:
        return canonical_json(self.to_dict())
