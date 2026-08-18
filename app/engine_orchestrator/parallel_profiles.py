"""Bounded concurrent coordinator with profile-level failure isolation."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from time import monotonic
from typing import Mapping

from app.engine_orchestrator.trade_profile import TradeProfileId


@dataclass(frozen=True, slots=True)
class ProfileCycleObservation:
    trade_profile_id: str
    healthy: bool
    duration_ms: int
    batch_size: int
    error_code: str | None = None


class ParallelTradeProfileCoordinator:
    """Run exactly two independent profile cycles without unbounded fan-out."""

    def __init__(self, daemons: Mapping[str, object]) -> None:
        required = {item.value for item in TradeProfileId}
        if set(daemons) != required:
            raise ValueError("parallel coordinator requires exactly the 15m and 5m profiles")
        self._daemons = dict(daemons)

    @staticmethod
    def _run(profile_id: str, daemon: object) -> ProfileCycleObservation:
        started = monotonic()
        try:
            items = daemon.run_cycle()
            return ProfileCycleObservation(
                profile_id, True, int((monotonic() - started) * 1000), len(items)
            )
        except Exception as exc:  # profile boundary intentionally contains failures
            return ProfileCycleObservation(
                profile_id, False, int((monotonic() - started) * 1000), 0,
                f"{type(exc).__name__}: {exc}",
            )

    def run_cycle(self) -> dict[str, ProfileCycleObservation]:
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="trade-profile") as executor:
            futures = {
                profile_id: executor.submit(self._run, profile_id, daemon)
                for profile_id, daemon in self._daemons.items()
            }
            return {profile_id: future.result() for profile_id, future in futures.items()}
