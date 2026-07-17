"""In-memory idempotent persistence for setup-layer outputs."""

from __future__ import annotations

from threading import RLock

from app.engine_setup.setup_candidate import SetupCandidate


class SetupStore:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str, int, str], SetupCandidate] = {}
        self._lock = RLock()

    @staticmethod
    def _scope(symbol: str, timeframe: str) -> tuple[str, str]:
        return symbol.upper(), timeframe

    def save(self, candidate: SetupCandidate) -> None:
        if not isinstance(candidate, SetupCandidate):
            raise TypeError("candidate must be a SetupCandidate")
        key = (*self._scope(candidate.symbol, candidate.timeframe),
               candidate.closed_until_ms, candidate.setup_type)
        with self._lock:
            self._items[key] = candidate

    def get_latest(self, symbol: str, timeframe: str) -> SetupCandidate | None:
        recent = self.list_recent(symbol, timeframe, limit=1)
        return recent[0] if recent else None

    def get_by_window(self, symbol: str, timeframe: str,
                      closed_until_ms: int) -> SetupCandidate | None:
        scope = self._scope(symbol, timeframe)
        with self._lock:
            matches = [item for key, item in self._items.items()
                       if key[:2] == scope and key[2] == int(closed_until_ms)]
        return max(matches, key=lambda item: item.created_at_ms, default=None)

    def list_recent(self, symbol: str, timeframe: str,
                    limit: int = 100) -> list[SetupCandidate]:
        if limit < 0:
            raise ValueError("limit must be non-negative")
        scope = self._scope(symbol, timeframe)
        with self._lock:
            matches = [item for key, item in self._items.items() if key[:2] == scope]
        return sorted(matches, key=lambda item: (item.closed_until_ms, item.created_at_ms), reverse=True)[:limit]

    def count(self, symbol: str, timeframe: str) -> int:
        scope = self._scope(symbol, timeframe)
        with self._lock:
            return sum(key[:2] == scope for key in self._items)
