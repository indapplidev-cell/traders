"""Adapter for already-redacted semantic incident snapshots.

The loader is injected and is not called by construction or application
startup. A controlled integration may point it at an accepted immutable state
snapshot; this implementation never discovers observer or soak paths.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from datetime import datetime, timezone
from typing import Any

from .records import IncidentQuery, IncidentRecord, RecordPage


def _timestamp(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("semantic incident timestamps must be timezone-aware")
    return parsed.astimezone(timezone.utc)


class SemanticIncidentReadAdapter:
    def __init__(self, loader: Callable[[], Iterable[Mapping[str, Any]]]) -> None:
        self._loader = loader

    @staticmethod
    def _record(value: Mapping[str, Any]) -> IncidentRecord:
        state = str(value.get("state") or "UNKNOWN")
        resolved = value.get("resolved_at_utc")
        return IncidentRecord(
            incident_id=str(value["incident_id"]),
            status=state,
            severity=str(value.get("severity") or "UNKNOWN"),
            source="semantic-observer",
            title=str(value.get("incident_type") or "Operational incident"),
            symbol=str(value["symbol"]).upper() if value.get("symbol") else None,
            opened_at=_timestamp(value["first_seen_at_utc"]),
            updated_at=_timestamp(value["last_seen_at_utc"]),
            resolved_at=_timestamp(resolved) if resolved else None,
            safe_description="A redacted semantic monitoring condition was recorded.",
            reason_code=str(value["reason_code"]) if value.get("reason_code") else None,
            timeframe=str(value["timeframe"]) if value.get("timeframe") else None,
            closed_until_ms=int(value["closed_until_ms"]) if value.get("closed_until_ms") is not None else None,
        )

    def _records(self) -> list[IncidentRecord]:
        return [self._record(value) for value in self._loader()]

    def list_incidents(self, query: IncidentQuery) -> RecordPage:
        records = self._records()
        if query.symbol:
            records = [item for item in records if item.symbol == query.symbol.upper()]
        if query.status:
            records = [item for item in records if item.status == query.status]
        if query.severity:
            records = [item for item in records if item.severity == query.severity]
        if query.from_at:
            records = [item for item in records if item.updated_at >= query.from_at]
        if query.to_at:
            records = [item for item in records if item.updated_at < query.to_at]
        records.sort(key=lambda item: (item.updated_at, item.incident_id), reverse=True)
        if query.cursor:
            anchor = (query.cursor.updated_at, query.cursor.identifier)
            records = [item for item in records if (item.updated_at, item.incident_id) < anchor]
        selected = records[: query.limit + 1]
        return RecordPage(tuple(selected[: query.limit]), len(selected) > query.limit)

    def get_incident(self, incident_id: str) -> IncidentRecord | None:
        return next((item for item in self._records() if item.incident_id == incident_id), None)

    def count_active_incidents(self) -> int:
        return sum(item.status != "RESOLVED" for item in self._records())
