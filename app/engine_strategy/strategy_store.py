"""In-memory idempotent storage for decisions; this is not a trade journal."""

from __future__ import annotations

from threading import RLock

from app.engine_strategy.strategy_decision import StrategyDecision


class StrategyStore:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str, int, str | None], StrategyDecision] = {}
        self._lock = RLock()

    @staticmethod
    def _scope(symbol: str, timeframe: str) -> tuple[str, str]:
        return symbol.upper(), timeframe

    def save(self, decision: StrategyDecision) -> None:
        if not isinstance(decision, StrategyDecision):
            raise TypeError("decision must be a StrategyDecision")
        key = (*self._scope(decision.symbol, decision.timeframe),
               decision.closed_until_ms, decision.source_setup_id)
        with self._lock:
            self._items[key] = decision

    def get_latest(self, symbol: str, timeframe: str) -> StrategyDecision | None:
        recent = self.list_recent(symbol, timeframe, limit=1)
        return recent[0] if recent else None

    def get_by_window(self, symbol: str, timeframe: str,
                      closed_until_ms: int) -> StrategyDecision | None:
        scope = self._scope(symbol, timeframe)
        with self._lock:
            matches = [item for key, item in self._items.items()
                       if key[:2] == scope and key[2] == int(closed_until_ms)]
        return max(matches, key=lambda item: item.created_at_ms, default=None)

    def list_recent(self, symbol: str, timeframe: str,
                    limit: int = 100) -> list[StrategyDecision]:
        if limit < 0:
            raise ValueError("limit must be non-negative")
        scope = self._scope(symbol, timeframe)
        with self._lock:
            matches = [item for key, item in self._items.items() if key[:2] == scope]
        return sorted(matches, key=lambda item: (item.closed_until_ms, item.created_at_ms),
                      reverse=True)[:limit]

    def count(self, symbol: str, timeframe: str) -> int:
        scope = self._scope(symbol, timeframe)
        with self._lock:
            return sum(key[:2] == scope for key in self._items)
