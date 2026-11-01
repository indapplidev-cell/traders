"""PostgreSQL LISTEN bridge from committed 1m candles to PAPER lifecycle."""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable

from sqlalchemy.engine import Engine


CLOSED_1M_CHANNEL = "traders_closed_candle_1m"
LOGGER = logging.getLogger("uvicorn.error")


class PostgresClosedCandleListener:
    def __init__(self, engine: Engine, callback: Callable[[], None]) -> None:
        self.engine = engine
        self.callback = callback
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def active(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.active:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="closed-candle-listener", daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._thread = None

    def _run(self) -> None:
        raw = self.engine.raw_connection()
        try:
            driver = raw.driver_connection
            driver.autocommit = True
            with driver.cursor() as cursor:
                cursor.execute(f"LISTEN {CLOSED_1M_CHANNEL}")
            while not self._stop.is_set():
                for notification in driver.notifies(timeout=1.0, stop_after=1):
                    try:
                        payload = json.loads(notification.payload)
                    except (TypeError, ValueError):
                        continue
                    if payload.get("timeframe") == "1m":
                        LOGGER.info(
                            "closed_candle_wakeup symbol=%s closed_until_ms=%s",
                            payload.get("symbol"), payload.get("closed_until_ms"),
                        )
                        self.callback()
        finally:
            raw.close()


__all__ = ("CLOSED_1M_CHANNEL", "PostgresClosedCandleListener")
