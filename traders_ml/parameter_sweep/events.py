"""Serializable, presentation-neutral parameter-sweep events."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Mapping


class EventType(StrEnum):
    RUN_STARTED = "RUN_STARTED"
    PREFLIGHT_STARTED = "PREFLIGHT_STARTED"
    PREFLIGHT_COMPLETED = "PREFLIGHT_COMPLETED"
    SEARCH_PLANNING_STARTED = "SEARCH_PLANNING_STARTED"
    SEARCH_PLANNED = "SEARCH_PLANNED"
    CONFIG_STARTED = "CONFIG_STARTED"
    CONFIG_PROGRESS = "CONFIG_PROGRESS"
    CONFIG_COMPLETED = "CONFIG_COMPLETED"
    RESULT_WRITE_STARTED = "RESULT_WRITE_STARTED"
    RESULT_WRITE_COMPLETED = "RESULT_WRITE_COMPLETED"
    CHECKPOINT_WRITTEN = "CHECKPOINT_WRITTEN"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    RUN_FINALIZING = "RUN_FINALIZING"
    INTEGRITY_CHECK_STARTED = "INTEGRITY_CHECK_STARTED"
    INTEGRITY_FILE_CHECKED = "INTEGRITY_FILE_CHECKED"
    INTEGRITY_CHECK_COMPLETED = "INTEGRITY_CHECK_COMPLETED"
    RUN_COMPLETED = "RUN_COMPLETED"
    RUN_FAILED = "RUN_FAILED"
    RUN_CANCELLED = "RUN_CANCELLED"
    RUN_RESUMED = "RUN_RESUMED"


@dataclass(frozen=True, slots=True)
class SweepEvent:
    type: EventType
    run_id: str
    payload: Mapping[str, Any]
    occurred_at: str

    @classmethod
    def create(
        cls, event_type: EventType, run_id: str, **payload: Any,
    ) -> "SweepEvent":
        return cls(
            type=event_type,
            run_id=run_id,
            payload=payload,
            occurred_at=datetime.now(timezone.utc).isoformat(),
        )

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["type"] = self.type.value
        return value
