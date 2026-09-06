"""Durable one-execution-per-causal-opportunity admission."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from threading import RLock
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db.paper_models import ScalpingOpportunityRecord

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

    def bind_plan(self, opportunity_id: str, paper_plan_id: str) -> None:
        # The file-backed implementation remains for isolated/offline callers.
        key = self._validate(opportunity_id)
        with self._lock:
            row = self._state[key]
            row["paper_plan_id"] = str(paper_plan_id)
            self._persist()


class PostgresScalpingOpportunityRegistry:
    """Atomic PostgreSQL authority used by production runtime."""

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _validate(value: str) -> str:
        return ScalpingOpportunityRegistry._validate(value)

    def claim(self, opportunity_id: str) -> OpportunityClaim:
        key = self._validate(opportunity_id)
        now = datetime.now(timezone.utc)
        with self._session_factory() as session, session.begin():
            inserted = session.scalar(insert(ScalpingOpportunityRecord).values(
                causal_opportunity_id=key, state="RESERVED", observation_count=1,
                created_at=now, updated_at=now,
            ).on_conflict_do_nothing(
                index_elements=["causal_opportunity_id"]
            ).returning(ScalpingOpportunityRecord.causal_opportunity_id))
            admitted = inserted is not None
            row = session.scalar(select(ScalpingOpportunityRecord).where(
                ScalpingOpportunityRecord.causal_opportunity_id == key
            ).with_for_update())
            if not admitted and row.state == "RESET_AVAILABLE":
                admitted = True
                row.state = "RESERVED"
                row.observation_count = 1
                row.updated_at = now
            elif not admitted:
                row.observation_count += 1
                row.updated_at = now
            return OpportunityClaim(
                key, admitted, row.causal_parent_id, row.reset_reason,
                row.reset_evidence, row.position_id,
                None if admitted else "CAUSAL_OPPORTUNITY_ALREADY_RESERVED_OR_EXECUTED",
                row.observation_count,
            )

    def bind_plan(self, opportunity_id: str, paper_plan_id: str) -> None:
        key = self._validate(opportunity_id)
        with self._session_factory() as session, session.begin():
            row = session.get(ScalpingOpportunityRecord, key)
            if row is None:
                raise ValueError("opportunity must be reserved before plan binding")
            row.paper_plan_id = str(paper_plan_id)
            row.updated_at = datetime.now(timezone.utc)

    def bind_command(self, opportunity_id: str, command_id: str) -> None:
        key = self._validate(opportunity_id)
        with self._session_factory() as session, session.begin():
            row = session.get(ScalpingOpportunityRecord, key)
            if row is None:
                raise ValueError("opportunity must be reserved before command binding")
            row.command_id = str(command_id)
            row.state = "COMMAND_CREATED"
            row.updated_at = datetime.now(timezone.utc)

    def bind_position_for_command(self, command_id: str, position_id: str) -> None:
        with self._session_factory() as session, session.begin():
            row = session.scalar(select(ScalpingOpportunityRecord).where(
                ScalpingOpportunityRecord.command_id == str(command_id)
            ).with_for_update())
            if row is None:
                raise ValueError("causal command binding is missing")
            row.position_id = str(position_id)
            row.state = "EXECUTED"
            row.updated_at = datetime.now(timezone.utc)

    def structural_reset(self, opportunity_id: str, new_opportunity_id: str, *, reason: str, evidence: str) -> None:
        parent, child = self._validate(opportunity_id), self._validate(new_opportunity_id)
        if parent == child or not reason.strip() or not evidence.strip():
            raise ValueError("structural reset requires a new identity and evidence")
        now = datetime.now(timezone.utc)
        with self._session_factory() as session, session.begin():
            if session.get(ScalpingOpportunityRecord, parent) is None:
                raise ValueError("causal parent is unknown")
            session.add(ScalpingOpportunityRecord(
                causal_opportunity_id=child, state="RESET_AVAILABLE", causal_parent_id=parent,
                reset_reason=reason, reset_evidence=evidence, observation_count=0,
                created_at=now, updated_at=now,
            ))


__all__ = (
    "OpportunityClaim", "PostgresScalpingOpportunityRegistry",
    "ScalpingOpportunityRegistry",
)
