"""Process-local idempotent admission for causal Scalping opportunities."""

from __future__ import annotations

from threading import RLock


class ScalpingOpportunityRegistry:
    def __init__(self) -> None:
        self._admitted: set[str] = set()
        self._observations: dict[str, int] = {}
        self._lock = RLock()

    def observe_and_claim(self, opportunity_id: str, *, reentry_enabled: bool = False) -> bool:
        key = str(opportunity_id)
        if not key.startswith("opportunity:"):
            raise ValueError("causal opportunity identity is required")
        with self._lock:
            self._observations[key] = self._observations.get(key, 0) + 1
            if key in self._admitted and not reentry_enabled:
                return False
            self._admitted.add(key)
            return True

    def observation_count(self, opportunity_id: str) -> int:
        with self._lock:
            return self._observations.get(str(opportunity_id), 0)
