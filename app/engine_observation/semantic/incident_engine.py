from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .contracts import IncidentState
from .models import Finding
from .serializer import append_canonical_jsonl


INCIDENT_SCHEMA = "OBSERVER_SEMANTIC_INCIDENT/1.0"


def incident_id(soak_id: str, finding: Finding) -> str:
    basis = "\0".join(str(value or "") for value in (
        soak_id, finding.incident_type, finding.symbol, finding.timeframe, finding.closed_until_ms,
        finding.run_id, finding.stable_sub_key,
    ))
    return "sem-" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:32]


class IncidentEngine:
    def __init__(self, path: Path, *, soak_id: str, observer_instance_id: str) -> None:
        self.path, self.soak_id, self.observer_instance_id = path, soak_id, observer_instance_id
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)

    @staticmethod
    def _iso(now: datetime) -> str:
        return now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    def reconcile(self, findings: Iterable[Finding], state: dict[str, Any], now: datetime, *, complete_snapshot: bool) -> list[dict[str, Any]]:
        current = {incident_id(self.soak_id, finding): finding for finding in findings}
        incidents: dict[str, Any] = state.setdefault("incidents", {})
        emitted: list[dict[str, Any]] = []
        now_text = self._iso(now)
        for identifier, finding in sorted(current.items()):
            prior = incidents.get(identifier)
            occurrence = int(prior.get("occurrence_count", 0)) + 1 if prior else 1
            record = {
                "schema_version": INCIDENT_SCHEMA, "incident_id": identifier,
                "incident_type": finding.incident_type, "state": IncidentState.UPDATED if prior and prior.get("state") != IncidentState.RESOLVED else IncidentState.OPEN,
                "severity": finding.severity, "acceptance_impact": finding.acceptance_impact,
                "first_seen_at_utc": prior.get("first_seen_at_utc", now_text) if prior else now_text,
                "last_seen_at_utc": now_text, "resolved_at_utc": None, "observer_instance_id": self.observer_instance_id,
                "soak_id": self.soak_id, "symbol": finding.symbol, "timeframe": finding.timeframe,
                "closed_until_ms": finding.closed_until_ms, "run_id": finding.run_id, "reason_code": finding.reason_code,
                "evidence": finding.evidence, "occurrence_count": occurrence,
            }
            incidents[identifier] = record
            append_canonical_jsonl(self.path, record)
            emitted.append(record)
        if complete_snapshot:
            for identifier, prior in list(incidents.items()):
                if identifier in current or prior.get("state") == IncidentState.RESOLVED:
                    continue
                record = {**prior, "state": IncidentState.RESOLVED, "last_seen_at_utc": now_text,
                          "resolved_at_utc": now_text, "observer_instance_id": self.observer_instance_id}
                incidents[identifier] = record
                append_canonical_jsonl(self.path, record)
                emitted.append(record)
        state["open_incident_ids"] = sorted(key for key, value in incidents.items() if value.get("state") != IncidentState.RESOLVED)
        state["resolved_incident_ids"] = sorted(key for key, value in incidents.items() if value.get("state") == IncidentState.RESOLVED)
        return emitted
