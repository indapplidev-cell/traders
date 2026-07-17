"""Market-data health policy for online analysis."""

from __future__ import annotations

from dataclasses import dataclass

from app.engine_market_data.market_data_health import MarketDataHealthStatus


@dataclass(frozen=True, slots=True)
class OnlineHealthDecision:
    allowed: bool
    degraded: bool
    reason: str | None


def evaluate_market_data_health(
    health_status: str,
    *,
    has_gaps: bool,
    allow_degraded_market_data: bool,
) -> OnlineHealthDecision:
    try:
        status = MarketDataHealthStatus(health_status)
    except ValueError:
        return OnlineHealthDecision(False, False, "INVALID_SNAPSHOT")
    if status is MarketDataHealthStatus.OK and not has_gaps:
        return OnlineHealthDecision(True, False, None)
    if status in (MarketDataHealthStatus.OK, MarketDataHealthStatus.DEGRADED):
        if allow_degraded_market_data:
            return OnlineHealthDecision(True, True, None)
        return OnlineHealthDecision(False, True, "MARKET_DATA_DEGRADED")
    return OnlineHealthDecision(False, False, f"MARKET_DATA_{status.value}")
