"""Immutable local position events."""
from __future__ import annotations
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, ClassVar
from app.engine_position.enums import PositionFillAction
from app.engine_position.serialization import (canonical_json, decimal, freeze, parse_utc,
                                                position_schema_version, require_schema, thaw, utc_iso)


@dataclass(frozen=True, slots=True)
class PositionEvent:
    event_id: str
    position_id: str
    occurred_at_utc: datetime
    source: str
    reason_codes: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    position_schema_version: int = field(default=position_schema_version, init=False)
    event_type: ClassVar[str] = "POSITION_EVENT"

    def __post_init__(self) -> None:
        if not self.event_id or not self.position_id or not self.source:
            raise ValueError("event identity, position and source are required")
        utc_iso(self.occurred_at_utc)
        object.__setattr__(self, "reason_codes", tuple(str(v) for v in self.reason_codes))
        object.__setattr__(self, "metadata", freeze(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        result = {"position_schema_version": 1, "event_type": self.event_type,
                  "event_id": self.event_id, "position_id": self.position_id,
                  "occurred_at_utc": utc_iso(self.occurred_at_utc), "source": self.source,
                  "reason_codes": list(self.reason_codes), "metadata": thaw(self.metadata)}
        for name in ("fill_quantity", "fill_price", "fee", "action", "mark_price",
                     "source_window_close_ms", "source_timeframe", "close_quantity",
                     "close_price", "close_reason"):
            if hasattr(self, name):
                value = getattr(self, name)
                result[name] = value.value if isinstance(value, PositionFillAction) else (str(value) if isinstance(value, Decimal) else value)
        return result

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PositionEvent":
        require_schema(payload)
        event_cls = EVENT_TYPES.get(str(payload.get("event_type")))
        if event_cls is None:
            raise ValueError("unknown position event type")
        keys = set(event_cls.__dataclass_fields__) - {"position_schema_version", "event_type"}
        values = {key: payload[key] for key in keys if key in payload}
        values["occurred_at_utc"] = parse_utc(str(values["occurred_at_utc"]))
        return event_cls(**values)

    def canonical_json(self) -> str:
        return canonical_json(self.to_dict())


@dataclass(frozen=True, slots=True)
class PositionFillEvent(PositionEvent):
    fill_quantity: Decimal = Decimal("0")
    fill_price: Decimal = Decimal("0")
    fee: Decimal = Decimal("0")
    action: PositionFillAction = PositionFillAction.OPEN
    event_type: ClassVar[str] = "POSITION_FILL"
    def __post_init__(self) -> None:
        PositionEvent.__post_init__(self)
        object.__setattr__(self, "fill_quantity", decimal(self.fill_quantity)); object.__setattr__(self, "fill_price", decimal(self.fill_price))
        object.__setattr__(self, "fee", decimal(self.fee)); object.__setattr__(self, "action", PositionFillAction(self.action))


@dataclass(frozen=True, slots=True)
class PositionMarkEvent(PositionEvent):
    mark_price: Decimal = Decimal("0")
    source_window_close_ms: int = 0
    source_timeframe: str = ""
    event_type: ClassVar[str] = "POSITION_MARK"
    def __post_init__(self) -> None:
        PositionEvent.__post_init__(self); object.__setattr__(self, "mark_price", decimal(self.mark_price))


@dataclass(frozen=True, slots=True)
class PositionCloseEvent(PositionEvent):
    close_quantity: Decimal = Decimal("0")
    close_price: Decimal = Decimal("0")
    fee: Decimal = Decimal("0")
    close_reason: str | None = None
    event_type: ClassVar[str] = "POSITION_CLOSE"
    def __post_init__(self) -> None:
        PositionEvent.__post_init__(self); object.__setattr__(self, "close_quantity", decimal(self.close_quantity))
        object.__setattr__(self, "close_price", decimal(self.close_price)); object.__setattr__(self, "fee", decimal(self.fee))


@dataclass(frozen=True, slots=True)
class PositionCancelEvent(PositionEvent):
    event_type: ClassVar[str] = "POSITION_CANCEL"


EVENT_TYPES = {c.event_type: c for c in (PositionEvent, PositionFillEvent, PositionMarkEvent,
                                         PositionCloseEvent, PositionCancelEvent)}
