"""Canonical SHA-256 identity and a focused in-memory registry."""

from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
from threading import RLock
from typing import Any

from app.engine_execution.serialization import canonical_json


IDEMPOTENCY_FIELDS = (
    "symbol", "source_timeframe", "source_closed_until_ms", "setup_id",
    "strategy_decision_id", "risk_decision_id", "execution_mode",
)


def build_idempotency_key(values: Mapping[str, Any] | None = None, **fields: Any) -> str:
    source = dict(values or {})
    source.update(fields)
    payload = {name: source.get(name) for name in IDEMPOTENCY_FIELDS}
    if any(value is None or value == "" for value in payload.values()):
        return ""
    payload["symbol"] = str(payload["symbol"]).upper()
    mode = payload["execution_mode"]
    payload["execution_mode"] = getattr(mode, "value", mode)
    digest = sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    return f"execution:v1:{digest}"


class InMemoryIdempotencyRegistry:
    def __init__(self) -> None:
        self._keys: set[str] = set()
        self._lock = RLock()

    def register(self, key: str) -> bool:
        with self._lock:
            if key in self._keys:
                return False
            self._keys.add(key)
            return True

    def contains(self, key: str) -> bool:
        with self._lock:
            return key in self._keys

    def clear(self) -> None:
        with self._lock:
            self._keys.clear()
