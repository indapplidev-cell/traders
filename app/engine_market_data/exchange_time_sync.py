"""Public exchange time drift measurement."""

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from app.engine_market_data.market_data_health import MarketDataHealth


class ServerTimeClient(Protocol):
    def fetch_server_time_ms(self) -> int: ...


@dataclass(frozen=True, slots=True)
class TimeSyncResult:
    local_time_ms: int
    server_time_ms: int
    drift_ms: int
    within_threshold: bool


class ExchangeTimeSync:
    def __init__(
        self,
        rest_client: ServerTimeClient,
        *,
        health: MarketDataHealth | None = None,
        max_drift_ms: int = 1_000,
        clock_ms: Callable[[], int] = lambda: int(time.time() * 1000),
    ) -> None:
        self.rest_client = rest_client
        self.health = health or MarketDataHealth()
        self.max_drift_ms = max_drift_ms
        self._clock_ms = clock_ms
        self.drift_ms = 0
        self.last_sync: TimeSyncResult | None = None

    def sync(self) -> TimeSyncResult:
        before = self._clock_ms()
        server = self.rest_client.fetch_server_time_ms()
        after = self._clock_ms()
        local_midpoint = (before + after) // 2
        self.drift_ms = server - local_midpoint
        within = abs(self.drift_ms) <= self.max_drift_ms
        self.last_sync = TimeSyncResult(local_midpoint, server, self.drift_ms, within)
        if within:
            self.health.ok()
        else:
            self.health.degraded("time drift too high")
        return self.last_sync

    def now_ms_exchange_adjusted(self) -> int:
        return self._clock_ms() + self.drift_ms
