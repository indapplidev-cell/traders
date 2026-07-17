"""CLI for the read-only ONLINE-PIPELINE-OBSERVATION-01 audit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

from app.engine_market_data.db.session import create_market_data_session_factory
from app.engine_observation.observation_config import ObservationConfig, parse_utc
from app.engine_observation.observation_errors import ObservationDatabaseError, ObservationSchemaError
from app.engine_observation.observation_repository import ObservationRepository
from app.engine_observation.observation_runner import ObservationRunner


def csv_symbols(value: str) -> tuple[str, ...]:
    values = tuple(item.strip().upper() for item in value.split(",") if item.strip())
    if not values: raise argparse.ArgumentTypeError("symbols must not be empty")
    return values


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only 24-hour online pipeline operational audit")
    parser.add_argument("--symbols", type=csv_symbols, default=csv_symbols("BTCUSDT,ETHUSDT,SOLUSDT"))
    parser.add_argument("--primary-timeframe", default="15m")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--last-hours", type=float)
    mode.add_argument("--start-utc", type=parse_utc)
    parser.add_argument("--end-utc", type=parse_utc)
    parser.add_argument("--minimum-window-hours", type=float, default=24)
    parser.add_argument("--output-dir", type=Path, default=Path("reports/engine_observation/online_pipeline_observation_01"))
    parser.add_argument("--report-json", default="ONLINE_PIPELINE_OBSERVATION_01_SUMMARY.json")
    parser.add_argument("--report-md", default="ONLINE_PIPELINE_OBSERVATION_01_REPORT.md")
    parser.add_argument("--fail-on-warning", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.start_utc and not args.end_utc: raise SystemExit("--end-utc is required with --start-utc")
    if args.last_hours and args.end_utc: raise SystemExit("--end-utc is only valid with --start-utc")
    config = ObservationConfig(symbols=args.symbols, primary_timeframe=args.primary_timeframe,
        start_utc=args.start_utc, end_utc=args.end_utc, last_hours=args.last_hours,
        minimum_window_hours=args.minimum_window_hours, output_dir=args.output_dir,
        report_json=args.report_json, report_md=args.report_md, fail_on_warning=args.fail_on_warning)
    try:
        report = ObservationRunner(config, ObservationRepository(create_market_data_session_factory())).run(dry_run=args.dry_run)
    except ObservationSchemaError as exc:
        print(json.dumps({"verdict": "BLOCKED_SCHEMA", "error": str(exc)})); return 3
    except ObservationDatabaseError as exc:
        print(json.dumps({"verdict": "BLOCKED_DATABASE", "error": str(exc)})); return 3
    summary = report.get("summary", report)
    print(json.dumps({"dry_run": report.get("dry_run", False), "verdict": summary.get("verdict"),
                      "interval": [summary.get("start_utc"), summary.get("end_utc")],
                      "artifacts": report.get("artifact_paths", [])}, indent=2))
    verdict = summary.get("verdict", "")
    return 1 if verdict == "OBSERVATION_FAILED" else (2 if str(verdict).startswith("BLOCKED_") else 0)


if __name__ == "__main__": raise SystemExit(main())
