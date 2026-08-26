"""UTC-day research-flow limits, unrelated to account exposure."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from threading import RLock

from app.engine_risk.risk_config import RiskConfig
from app.engine_risk.risk_context import RiskContext


class ResearchRiskLimits:
    def __init__(self) -> None:
        self._symbol: Counter[tuple[str, str, str]] = Counter()
        self._total: Counter[tuple[str, str]] = Counter()
        self._direction: Counter[tuple[str, str, str]] = Counter()
        self._reserved: set[tuple[str, str]] = set()
        self._lock = RLock()

    @staticmethod
    def utc_day(closed_until_ms: int) -> str:
        return datetime.fromtimestamp(int(closed_until_ms) / 1000, tz=timezone.utc).date().isoformat()

    def check_and_reserve(self, *, identity: str, symbol: str, direction: str,
                          trade_profile_id: str = "trade-15m-v1",
                          closed_until_ms: int, config: RiskConfig) -> tuple[bool, RiskContext]:
        day = self.utc_day(closed_until_ms)
        profile = str(trade_profile_id)
        reservation_key = (profile, str(identity))
        symbol_key = (profile, day, symbol.upper())
        total_key = (profile, day)
        direction_key = (profile, day, direction)
        with self._lock:
            context = RiskContext(
                utc_day=day,
                trade_profile_id=profile,
                symbol_preapprovals_before=self._symbol[symbol_key],
                total_preapprovals_before=self._total[total_key],
                direction_preapprovals_before=self._direction[direction_key],
            )
            if reservation_key in self._reserved:
                return True, context
            allowed = (
                context.symbol_preapprovals_before < config.max_research_preapprovals_per_symbol_per_day
                and context.total_preapprovals_before < config.max_research_preapprovals_total_per_day
                and context.direction_preapprovals_before
                < config.max_research_preapprovals_per_direction_per_day
            )
            if allowed:
                self._symbol[symbol_key] += 1
                self._total[total_key] += 1
                self._direction[direction_key] += 1
                self._reserved.add(reservation_key)
            return allowed, context

    def check_without_reservation(
        self, *, identity: str, symbol: str, direction: str,
        trade_profile_id: str = "trade-15m-v1", closed_until_ms: int,
        config: RiskConfig,
    ) -> tuple[bool, RiskContext]:
        """Evaluate research quota without changing any counter or reservation."""
        day = self.utc_day(closed_until_ms)
        profile = str(trade_profile_id)
        reservation_key = (profile, str(identity))
        symbol_key = (profile, day, symbol.upper())
        total_key = (profile, day)
        direction_key = (profile, day, direction)
        with self._lock:
            context = RiskContext(
                utc_day=day,
                trade_profile_id=profile,
                symbol_preapprovals_before=self._symbol[symbol_key],
                total_preapprovals_before=self._total[total_key],
                direction_preapprovals_before=self._direction[direction_key],
            )
            allowed = reservation_key in self._reserved or (
                context.symbol_preapprovals_before < config.max_research_preapprovals_per_symbol_per_day
                and context.total_preapprovals_before < config.max_research_preapprovals_total_per_day
                and context.direction_preapprovals_before
                < config.max_research_preapprovals_per_direction_per_day
            )
            return allowed, context

    def profile_attempts(self, trade_profile_id: str, closed_until_ms: int) -> int:
        """Return a diagnostic profile counter; it never represents account risk."""
        with self._lock:
            return self._total[(str(trade_profile_id), self.utc_day(closed_until_ms))]
