"""In-memory persistence for online analysis outputs only."""

from __future__ import annotations

from threading import RLock

from app.engine_analysis.analysis_snapshot import AnalysisSnapshot


class AnalysisSnapshotStore:
    """Thread-safe, idempotent store keyed by the closed analysis window."""

    def __init__(self) -> None:
        self._items: dict[tuple[str, str, int], AnalysisSnapshot] = {}
        self._lock = RLock()

    @staticmethod
    def _key(symbol: str, timeframe: str, closed_until_ms: int) -> tuple[str, str, int]:
        return symbol.upper(), timeframe, int(closed_until_ms)

    def save(self, snapshot: AnalysisSnapshot) -> None:
        key = self._key(snapshot.symbol, snapshot.timeframe, snapshot.closed_until_ms)
        with self._lock:
            self._items.setdefault(key, snapshot)

    def get_latest(self, symbol: str, timeframe: str) -> AnalysisSnapshot | None:
        items = self.list_recent(symbol, timeframe, limit=1)
        return items[0] if items else None

    def get_by_window(self, symbol: str, timeframe: str, closed_until_ms: int) -> AnalysisSnapshot | None:
        with self._lock:
            return self._items.get(self._key(symbol, timeframe, closed_until_ms))

    def list_recent(self, symbol: str, timeframe: str, limit: int = 100) -> list[AnalysisSnapshot]:
        if limit < 0:
            raise ValueError("limit must be non-negative")
        identity = symbol.upper(), timeframe
        with self._lock:
            matches = [item for key, item in self._items.items() if key[:2] == identity]
        return sorted(matches, key=lambda item: item.closed_until_ms, reverse=True)[:limit]

    def count(self, symbol: str, timeframe: str) -> int:
        identity = symbol.upper(), timeframe
        with self._lock:
            return sum(key[:2] == identity for key in self._items)
