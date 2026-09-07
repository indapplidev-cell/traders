"""CLI front-end over the same headless engine used by the GUI."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .engine import PROJECT_ROOT, ParameterSweepEngine, SweepExpectedError
from .events import SweepEvent
from .state import read_effective_status


DEFAULT_CONFIG = PROJECT_ROOT / "config/research/scalping_v2_parameter_sweep.yaml"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "artifacts/scalping_v2_parameter_sweep"


def render_event(event: SweepEvent) -> None:
    details = " ".join(f"{key}={value}" for key, value in event.payload.items() if key != "result")
    print(f"EVENT = {event.type.value}" + (f" {details}" if details else ""))


def status(run_id: str, output_root: Path = DEFAULT_OUTPUT_ROOT) -> int:
    path = output_root / run_id / "STATUS.json"
    try:
        value = read_effective_status(path)
    except (OSError, ValueError, KeyError):
        print(f"RUN_ID = {run_id}")
        print("STATE = NOT_FOUND")
        return 2
    print(f"RUN_ID = {run_id}")
    print(f"STATE = {value['state']}")
    print(f"PHASE = {value['phase']}")
    print(f"PROCESS_ALIVE = {'YES' if value['process_alive'] else 'NO'}")
    print(f"PLANNED = {value['planned_configs']}")
    print(f"COMPLETED = {value['completed_configs']}")
    current = value.get("current_config_index")
    print(f"CURRENT_CONFIG = {current if current is not None else 'NONE'}")
    print(f"FAILURE = {value.get('failure_code') or 'NONE'}")
    print(f"STARTED_AT = {value['started_at']}")
    print(f"UPDATED_AT = {value['updated_at']}")
    print(f"LAST_CHECKPOINT = {value['last_checkpoint_at']}")
    print(f"RESUME_AVAILABLE = {'YES' if value['resume_available'] else 'NO'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only Scalping v2 parameter sweep")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--run-id")
    parser.add_argument("--status", metavar="RUN_ID")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-configs", type=int)
    parser.add_argument("--max-rows", type=int)
    parser.add_argument("--from", dest="from_value")
    parser.add_argument("--to", dest="to_value")
    parser.add_argument("--database-url", help="Explicit dev/test/admin override only")
    parser.add_argument("--verbose", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.status:
        raise SystemExit(status(args.status, args.output_root))
    try:
        output = ParameterSweepEngine(render_event).run(
            args.config, run_id=args.run_id, max_configs=args.max_configs,
            max_rows=args.max_rows, from_value=args.from_value,
            to_value=args.to_value, database_url=args.database_url,
            preflight_only=args.preflight_only, verbose=args.verbose,
            resume=args.resume,
        )
    except SweepExpectedError as error:
        print("PARAMETER_SWEEP = FAILED")
        print(f"REASON = {error.reason}")
        raise SystemExit(2) from None
    report = output / "REPORT.md"
    print(report if report.exists() else output / "PREFLIGHT.json")
