"""UTC-day research-flow limits, unrelated to account exposure."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from threading import RLock

from app.engine_risk.risk_config import RiskConfig
from app.engine_risk.risk_context import RiskContext


class ResearchRiskLimits:
    def __init__(self) -> None:
        self._symbol: Counter[tuple[str, str]] = Counter()
        self._total: Counter[str] = Counter()
        self._direction: Counter[tuple[str, str]] = Counter()
        self._reserved: set[str] = set()
        self._lock = RLock()

    @staticmethod
    def utc_day(closed_until_ms: int) -> str:
        return datetime.fromtimestamp(int(closed_until_ms) / 1000, tz=timezone.utc).date().isoformat()

    def check_and_reserve(self, *, identity: str, symbol: str, direction: str,
                          closed_until_ms: int, config: RiskConfig) -> tuple[bool, RiskContext]:
        day = self.utc_day(closed_until_ms)
        symbol_key = (day, symbol.upper())
        direction_key = (day, direction)
        with self._lock:
            context = RiskContext(
                utc_day=day,
                symbol_preapprovals_before=self._symbol[symbol_key],
                total_preapprovals_before=self._total[day],
                direction_preapprovals_before=self._direction[direction_key],
            )
            if identity in self._reserved:
                return True, context
            allowed = (
                context.symbol_preapprovals_before < config.max_research_preapprovals_per_symbol_per_day
                and context.total_preapprovals_before < config.max_research_preapprovals_total_per_day
                and context.direction_preapprovals_before
                < config.max_research_preapprovals_per_direction_per_day
            )
            if allowed:
                self._symbol[symbol_key] += 1
                self._total[day] += 1
                self._direction[direction_key] += 1
                self._reserved.add(identity)
            return allowed, context
