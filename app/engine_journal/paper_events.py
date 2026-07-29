"""Immutable, bounded PAPER domain events without a bus or persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.engine_safety.paper_domain import (
    PaperEventType,
    PaperReasonCode,
    require_identity,
    require_enum,
    require_nonnegative_int,
    require_utc,
)


@dataclass(frozen=True, slots=True)
class PaperDomainEvent:
    event_id: str
    event_type: PaperEventType
    occurred_at: datetime
    aggregate_type: str
    aggregate_id: str
    correlation_id: str
    causation_id: str
    reason_code: PaperReasonCode
    aggregate_version: int

    def __post_init__(self) -> None:
        for name in (
            "event_id",
            "aggregate_type",
            "aggregate_id",
            "correlation_id",
            "causation_id",
        ):
            object.__setattr__(self, name, require_identity(getattr(self, name), name))
        object.__setattr__(
            self,
            "event_type",
            require_enum(
                self.event_type,
                PaperEventType,
                PaperReasonCode.PAPER_INTERNAL_INVARIANT_VIOLATION,
                "event_type",
            ),
        )
        object.__setattr__(
            self,
            "reason_code",
            require_enum(
                self.reason_code,
                PaperReasonCode,
                PaperReasonCode.PAPER_INTERNAL_INVARIANT_VIOLATION,
                "reason_code",
            ),
        )
        require_utc(self.occurred_at, "occurred_at")
        require_nonnegative_int(self.aggregate_version, "aggregate_version")
