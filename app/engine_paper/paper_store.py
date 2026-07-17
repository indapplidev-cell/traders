"""In-memory idempotent PaperTradePlan store; it is not an execution journal."""

from threading import RLock

from app.engine_paper.paper_trade_plan import PaperTradePlan


class PaperStore:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str, int, str | None], PaperTradePlan] = {}
        self._lock = RLock()

    @staticmethod
    def _scope(symbol: str, timeframe: str) -> tuple[str, str]:
        return symbol.upper(), timeframe

    def save(self, plan: PaperTradePlan) -> None:
        if not isinstance(plan, PaperTradePlan):
            raise TypeError("plan must be a PaperTradePlan")
        key = (*self._scope(plan.symbol, plan.timeframe), plan.closed_until_ms,
               plan.source_risk_decision_id)
        with self._lock:
            self._items[key] = plan

    def get_latest(self, symbol: str, timeframe: str) -> PaperTradePlan | None:
        rows = self.list_recent(symbol, timeframe, 1)
        return rows[0] if rows else None

    def get_by_window(self, symbol: str, timeframe: str,
                      closed_until_ms: int) -> PaperTradePlan | None:
        scope = self._scope(symbol, timeframe)
        with self._lock:
            rows = [row for key, row in self._items.items()
                    if key[:2] == scope and key[2] == int(closed_until_ms)]
        return max(rows, key=lambda row: row.created_at_ms, default=None)

    def list_recent(self, symbol: str, timeframe: str, limit: int = 100) -> list[PaperTradePlan]:
        if limit < 0:
            raise ValueError("limit must be non-negative")
        scope = self._scope(symbol, timeframe)
        with self._lock:
            rows = [row for key, row in self._items.items() if key[:2] == scope]
        return sorted(rows, key=lambda row: (row.closed_until_ms, row.created_at_ms),
                      reverse=True)[:limit]

    def count(self, symbol: str, timeframe: str) -> int:
        scope = self._scope(symbol, timeframe)
        with self._lock:
            return sum(key[:2] == scope for key in self._items)
