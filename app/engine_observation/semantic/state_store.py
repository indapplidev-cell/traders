from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.engine_observation.observer_reliability import atomic_write_json


STATE_SCHEMA = "OBSERVER_SEMANTIC_STATE/1.0"


class SemanticStateError(RuntimeError):
    pass


class SemanticStateStore:
    def __init__(self, path: Path, *, soak_id: str, contract_hash: str) -> None:
        self.path, self.soak_id, self.contract_hash = path, soak_id, contract_hash

    def empty(self) -> dict[str, Any]:
        return {"schema_version": STATE_SCHEMA, "soak_id": self.soak_id, "contract_hash": self.contract_hash,
                "last_successful_db_clock": None, "last_processed_closed_until_ms": None,
                "last_processed_run_updated_at": None, "known_window_states": {}, "known_window_run_ids": {},
                "incidents": {}, "open_incident_ids": [], "resolved_incident_ids": [], "last_sample_sequence": 0,
                "updated_at_utc": None}

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self.empty()
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise SemanticStateError(f"corrupt semantic state: {type(exc).__name__}") from exc
        if value.get("schema_version") != STATE_SCHEMA or value.get("soak_id") != self.soak_id or value.get("contract_hash") != self.contract_hash:
            raise SemanticStateError("semantic state contract mismatch")
        return value

    def save(self, state: dict[str, Any]) -> None:
        atomic_write_json(self.path, state)
