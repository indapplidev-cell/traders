"""Durable one-execution-per-causal-opportunity admission."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from threading import RLock

DEFAULT_STATE_PATH = Path("reports/runtime/scalping_opportunities.json")


@dataclass(frozen=True, slots=True)
class OpportunityClaim:
    causal_opportunity_id: str
    admitted: bool
    causal_parent_id: str | None
    reset_reason: str | None
    reset_evidence: str | None
    prior_execution_position_id: str | None
    duplicate_block_reason: str | None
    observation_count: int


class ScalpingOpportunityRegistry:
    def __init__(self, path: Path | None = None) -> None:
        configured = os.environ.get("TRADERS_SCALPING_OPPORTUNITY_REGISTRY_PATH")
        self.path = Path(configured) if configured else (path or DEFAULT_STATE_PATH)
        self._lock = RLock()
        self._state = self._load()

    def _load(self) -> dict[str, dict[str, object]]:
        if not self.path.exists():
            return {}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("registry root must be an object")
            return {str(key): dict(row) for key, row in value.items()}
        except Exception as exc:
            raise RuntimeError("causal opportunity registry is unreadable") from exc

    def _persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(
            self._state, sort_keys=True, separators=(",", ":")
        ), encoding="utf-8")
        temporary.replace(self.path)

    @staticmethod
    def _validate(opportunity_id: str) -> str:
        key = str(opportunity_id)
        if not key.startswith("opportunity:"):
            raise ValueError("causal opportunity identity is required")
        return key

    def claim(self, opportunity_id: str) -> OpportunityClaim:
        key = self._validate(opportunity_id)
        with self._lock:
            row = self._state.setdefault(key, {
                "admitted": False, "observation_count": 0,
                "causal_parent_id": None, "reset_reason": None,
                "reset_evidence": None, "prior_execution_position_id": None,
            })
            row["observation_count"] = int(row["observation_count"]) + 1
            duplicate = bool(row["admitted"])
            if not duplicate:
                row["admitted"] = True
            self._persist()
            return OpportunityClaim(
                key, not duplicate, row.get("causal_parent_id"), row.get("reset_reason"),
                row.get("reset_evidence"), row.get("prior_execution_position_id"),
                "CAUSAL_OPPORTUNITY_ALREADY_EXECUTED" if duplicate else None,
                int(row["observation_count"]),
            )

    def observe_and_claim(self, opportunity_id: str, *, reentry_enabled: bool = False) -> bool:
        if reentry_enabled:
            raise ValueError("boundary-based reentry is retired; use structural_reset")
        return self.claim(opportunity_id).admitted

    def record_execution(self, opportunity_id: str, position_id: str) -> None:
        key = self._validate(opportunity_id)
        if not str(position_id).strip():
            raise ValueError("position identity is required")
        with self._lock:
            row = self._state.get(key)
            if row is None or not row.get("admitted"):
                raise ValueError("opportunity must be admitted before execution")
            row["prior_execution_position_id"] = str(position_id)
            self._persist()

    def structural_reset(self, opportunity_id: str, new_opportunity_id: str, *, reason: str, evidence: str) -> None:
        parent = self._validate(opportunity_id)
        child = self._validate(new_opportunity_id)
        if parent == child or not reason.strip() or not evidence.strip():
            raise ValueError("structural reset requires a new identity and evidence")
        with self._lock:
            if parent not in self._state:
                raise ValueError("causal parent is unknown")
            self._state[child] = {
                "admitted": False, "observation_count": 0,
                "causal_parent_id": parent, "reset_reason": reason,
                "reset_evidence": evidence, "prior_execution_position_id": None,
            }
            self._persist()

    def observation_count(self, opportunity_id: str) -> int:
        with self._lock:
            return int(self._state.get(str(opportunity_id), {}).get("observation_count", 0))


__all__ = ("OpportunityClaim", "ScalpingOpportunityRegistry")
