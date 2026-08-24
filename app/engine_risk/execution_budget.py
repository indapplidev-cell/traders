"""Idempotent account-level risk reservations made only for valid plans."""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock


@dataclass(frozen=True, slots=True)
class BudgetState:
    committed_count: int
    reserved_count: int
    committed_risk_bps: float
    reserved_risk_bps: float


class SharedAccountExecutionBudget:
    """Shared authority across profiles; research attempts never enter this class."""

    def __init__(self, *, max_approved_plans: int, max_risk_bps: float) -> None:
        if max_approved_plans <= 0 or max_risk_bps <= 0:
            raise ValueError("execution budget limits must be positive")
        self.max_approved_plans = int(max_approved_plans)
        self.max_risk_bps = float(max_risk_bps)
        self._reservations: dict[str, float] = {}
        self._committed: dict[str, float] = {}
        self._lock = RLock()

    @property
    def state(self) -> BudgetState:
        with self._lock:
            return BudgetState(
                committed_count=len(self._committed),
                reserved_count=len(self._reservations),
                committed_risk_bps=round(sum(self._committed.values()), 8),
                reserved_risk_bps=round(sum(self._reservations.values()), 8),
            )

    def reserve(self, plan_id: str, risk_bps: float) -> bool:
        """Reserve once after plan validation; duplicate retries are idempotent."""
        key, risk = str(plan_id), float(risk_bps)
        if not key or risk <= 0:
            raise ValueError("plan identity and positive risk are required")
        with self._lock:
            if key in self._committed or key in self._reservations:
                return True
            count = len(self._committed) + len(self._reservations)
            total_risk = sum(self._committed.values()) + sum(self._reservations.values())
            if count >= self.max_approved_plans or total_risk + risk > self.max_risk_bps:
                return False
            self._reservations[key] = risk
            return True

    def commit(self, plan_id: str) -> bool:
        key = str(plan_id)
        with self._lock:
            if key in self._committed:
                return True
            risk = self._reservations.pop(key, None)
            if risk is None:
                return False
            self._committed[key] = risk
            return True

    def release(self, plan_id: str) -> bool:
        with self._lock:
            return self._reservations.pop(str(plan_id), None) is not None
