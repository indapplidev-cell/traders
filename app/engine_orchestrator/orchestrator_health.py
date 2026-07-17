"""Atomic operational health report writer."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.engine_orchestrator.orchestrator_status import OrchestratorHealthStatus


def iso_utc_from_ms(value: int) -> str:
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")


class OrchestratorHealthReporter:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def build(self, *, daemon_instance_id: str, symbols: tuple[str, ...], primary_timeframe: str,
              state: object, overall_status: str | None = None) -> dict[str, Any]:
        if overall_status is None:
            if getattr(state, "last_error", None):
                overall_status = OrchestratorHealthStatus.ERROR.value
            elif getattr(state, "completed_windows", 0):
                overall_status = OrchestratorHealthStatus.OK.value
            elif getattr(state, "skipped_windows", 0):
                overall_status = OrchestratorHealthStatus.WAITING_FOR_FRESH_DATA.value
            else:
                overall_status = OrchestratorHealthStatus.OK.value
        last = []
        for symbol in symbols:
            item = dict(getattr(state, "last_processed", {}).get(symbol, {}))
            if item:
                item.setdefault("symbol", symbol)
                if item.get("closed_until_ms") is not None:
                    item["closed_until_utc"] = iso_utc_from_ms(item["closed_until_ms"])
                last.append(item)
        safety = dict(getattr(state, "safety_totals", {}))
        safety.setdefault("future_bars_used_count", 0)
        safety.setdefault("trade_signal_count", 0)
        safety.setdefault("is_executable_count", 0)
        safety["orders_created"] = safety.get("order_approved_count", 0)
        safety["positions_created"] = safety.get("position_opened_count", 0)
        safety["pnl_records_created"] = safety.get("outcome_pnl_used", 0)
        return {
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "daemon_instance_id": daemon_instance_id,
            "overall_status": overall_status,
            "symbols": list(symbols),
            "primary_timeframe": primary_timeframe,
            "cycles": getattr(state, "cycles", 0),
            "last_processed": last,
            "safety": safety,
            "last_error": getattr(state, "last_error", None),
        }

    def write(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(self.path)
