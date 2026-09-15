"""Persistable recovery-only state transitions; no archiving or trading authority."""
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Literal
import logging

State = Literal["READY", "DEGRADED", "RECOVERING", "BLOCKED", "NOT_EVALUATED"]
LOGGER = logging.getLogger(__name__)

@dataclass(frozen=True, slots=True)
class RecoveryState:
    state: State = "NOT_EVALUATED"
    reason_code: str = "PITR_VERIFICATION_PENDING"
    last_success_at: str | None = None
    last_failure_at: str | None = None
    degraded_since: str | None = None
    recovered_at: str | None = None
    next_recheck_at: str | None = None
    heartbeat_at: str | None = None
    instance_id: str | None = None
    generation: int = 0
    started_at: str | None = None
    last_recheck_started_at: str | None = None
    last_recheck_finished_at: str | None = None
    snapshot_generated_at: str | None = None

    def advance(self, state: State, reason: str, now: datetime, cadence: float):
        stamp = now.isoformat()
        if state != self.state:
            LOGGER.info("recovery_transition %s -> %s reason=%s", self.state, state, reason)
        failed = state in {"DEGRADED", "BLOCKED"}
        recovered = state == "READY" and self.state in {"DEGRADED", "BLOCKED", "RECOVERING"}
        return RecoveryState(state, reason,
            stamp if state == "READY" else self.last_success_at,
            stamp if failed and (self.state != state or self.reason_code != reason) else self.last_failure_at,
            (self.degraded_since or stamp) if failed or state == "RECOVERING" else None,
            stamp if recovered else self.recovered_at,
            (now + timedelta(seconds=cadence)).isoformat(),
            stamp, self.instance_id, self.generation, self.started_at,
            self.last_recheck_started_at, stamp, stamp)

    def bind(self, instance_id: str, generation: int, now: datetime, cadence: float):
        """Bind persisted RUNNING state to one concrete worker incarnation."""
        stamp = now.isoformat()
        return RecoveryState(
            "RECOVERING", "RECOVERY_WORKER_STARTING", self.last_success_at,
            self.last_failure_at, self.degraded_since or stamp, self.recovered_at,
            (now + timedelta(seconds=cadence)).isoformat(), stamp, instance_id,
            generation, stamp, stamp, None, stamp,
        )

    def project(self):
        return asdict(self)
