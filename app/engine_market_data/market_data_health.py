"""Observable health state for the data pipeline."""

from dataclasses import dataclass, field
from enum import StrEnum


class MarketDataHealthStatus(StrEnum):
    OK = "OK"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    DISCONNECTED = "DISCONNECTED"
    RECOVERING = "RECOVERING"
    ERROR = "ERROR"


@dataclass(slots=True)
class MarketDataHealth:
    status: MarketDataHealthStatus = MarketDataHealthStatus.OK
    reasons: list[str] = field(default_factory=list)

    def set(self, status: MarketDataHealthStatus | str, reason: str | None = None) -> None:
        self.status = MarketDataHealthStatus(status)
        if reason and reason not in self.reasons:
            self.reasons.append(reason)

    def ok(self) -> None:
        self.status = MarketDataHealthStatus.OK
        self.reasons.clear()

    def degraded(self, reason: str) -> None:
        self.set(MarketDataHealthStatus.DEGRADED, reason)

    def stale(self, reason: str = "stale latest candle") -> None:
        self.set(MarketDataHealthStatus.STALE, reason)

    def disconnected(self, reason: str = "websocket disconnected") -> None:
        self.set(MarketDataHealthStatus.DISCONNECTED, reason)

    def recovering(self, reason: str = "missing candles") -> None:
        self.set(MarketDataHealthStatus.RECOVERING, reason)

    def error(self, reason: str) -> None:
        self.set(MarketDataHealthStatus.ERROR, reason)

    @property
    def is_healthy(self) -> bool:
        return self.status == MarketDataHealthStatus.OK
