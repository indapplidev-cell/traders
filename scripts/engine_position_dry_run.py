"""JSON-only local CLI for ENGINE-POSITION-01."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import Any
from app.engine_execution import ExecutionAcknowledgement, ExecutionIntent, ExecutionMode
from app.engine_position import (InMemoryPositionStore, PositionCancelEvent, PositionCloseEvent,
                                 PositionEvent, PositionFillEvent, PositionLifecycleService,
                                 PositionMarkEvent)
from app.engine_position.exceptions import PositionError


def output(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("input", type=Path)
    parser.add_argument("--mode", required=True)
    parser.add_argument("--synthetic-local-fill", action="store_true")
    try:
        args = parser.parse_args(argv)
        if args.mode == ExecutionMode.LIVE.value:
            output({"ok": False, "reason_codes": ["LIVE_POSITION_MANAGEMENT_DISABLED"]}); return 2
        if args.mode not in {ExecutionMode.PAPER.value, ExecutionMode.DRY_RUN.value}:
            output({"ok": False, "reason_codes": ["MODE_MISMATCH"]}); return 2
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        intent = ExecutionIntent.from_dict(payload["execution_intent"])
        acknowledgement = ExecutionAcknowledgement.from_dict(payload["execution_acknowledgement"])
        if intent.execution_mode.value != args.mode:
            output({"ok": False, "reason_codes": ["MODE_MISMATCH"]}); return 2
        events = [PositionEvent.from_dict(item) for item in payload.get("events", [])]
        initial = events.pop(0) if events and isinstance(events[0], PositionFillEvent) else None
        store = InMemoryPositionStore(); service = PositionLifecycleService(store)
        now = acknowledgement.accepted_at_utc or intent.created_at_utc
        position = service.create_position(intent, acknowledgement, current_timestamp=now,
                                           initial_fill=initial,
                                           synthetic_local_fill=args.synthetic_local_fill)
        results = []
        for event in events:
            result = store.apply_event(position.position_id, event); results.append(result.to_dict())
        final = store.get(position.position_id)
        output({"ok": True, "position": final.to_dict(), "results": results}); return 0
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError, PositionError) as exc:
        reasons = list(getattr(exc, "reason_codes", ())) or ["INVALID_POSITION_INPUT"]
        output({"ok": False, "reason_codes": reasons, "error_type": type(exc).__name__}); return 2


if __name__ == "__main__":
    raise SystemExit(main())
