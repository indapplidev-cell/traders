"""Offline JSON CLI for ENGINE-EXECUTION-01."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine_execution import (  # noqa: E402
    DryRunExecutionGateway, ExecutionIntentBuilder, ExecutionMode,
)


class CliContractError(ValueError):
    pass


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise CliContractError(message)


def parser() -> argparse.ArgumentParser:
    result = JsonArgumentParser(description="Build a local execution intent from JSON")
    result.add_argument("input", type=Path)
    result.add_argument("--mode", required=True)
    return result


def _error(reason: str, detail: str, exit_code: int = 1) -> int:
    print(detail, file=sys.stderr)
    print(json.dumps({"status": "REJECTED", "reason_codes": [reason]},
                     sort_keys=True, separators=(",", ":")))
    return exit_code


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        if args.mode == ExecutionMode.LIVE.value:
            print(json.dumps({"status": "DISABLED", "reason_codes": ["LIVE_EXECUTION_DISABLED"]},
                             sort_keys=True, separators=(",", ":")))
            return 2
        try:
            mode = ExecutionMode(args.mode)
        except ValueError:
            return _error("CONTRACT_MISMATCH", f"unsupported execution mode: {args.mode}", 2)
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        intent = ExecutionIntentBuilder().build(
            payload["strategy_decision"], payload["risk_decision"],
            payload.get("setup_context", payload.get("plan_context")),
            mode, payload["source_window"],
        )
        result: dict[str, object] = {"intent": intent.to_dict()}
        if args.mode == ExecutionMode.DRY_RUN.value:
            result["acknowledgement"] = DryRunExecutionGateway().submit(intent).to_dict()
        print(json.dumps(result, ensure_ascii=False, allow_nan=False,
                         sort_keys=True, separators=(",", ":")))
        return 0 if intent.status.value == "READY" else 1
    except json.JSONDecodeError as exc:
        return _error("CONTRACT_MISMATCH", f"invalid JSON: {exc.msg}")
    except (KeyError, TypeError, ValueError, OSError, CliContractError) as exc:
        return _error("CONTRACT_MISMATCH", f"invalid execution input: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())
