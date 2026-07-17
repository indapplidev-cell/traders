"""Canonical position identity and a thread-safe creation registry."""
from __future__ import annotations
from hashlib import sha256
from threading import RLock
from typing import Any
from app.engine_position.serialization import canonical_json


def build_position_key(*, execution_intent_id: str, execution_idempotency_key: str,
                       symbol: str, mode: str, source_timeframe: str,
                       source_window_close_ms: int, setup_id: str,
                       strategy_decision_id: str, risk_decision_id: str) -> str:
    payload: dict[str, Any] = {
        "execution_intent_id": execution_intent_id,
        "execution_idempotency_key": execution_idempotency_key,
        "symbol": symbol,
        "mode": str(mode),
        "source_timeframe": source_timeframe,
        "source_window_close_ms": int(source_window_close_ms),
        "setup_id": setup_id,
        "strategy_decision_id": strategy_decision_id,
        "risk_decision_id": risk_decision_id,
    }
    return "position:v1:" + sha256(canonical_json(payload).encode("utf-8")).hexdigest()


class PositionIdempotencyRegistry:
    def __init__(self) -> None:
        self._keys: set[str] = set()
        self._lock = RLock()

    def register(self, key: str) -> bool:
        with self._lock:
            if key in self._keys:
                return False
            self._keys.add(key)
            return True
