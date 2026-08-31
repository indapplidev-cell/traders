"""CLI for the durable passive Scalping prospective calibration collector."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine_observation.scalping_prospective_collector import (
    CollectorConfig,
    PostgresCollectorOwner,
    PostgresRepository,
    ProspectiveCalibrationCollector,
)

DEFAULT_SYMBOLS = "BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT,LINKUSDT,DOGEUSDT,ADAUSDT,AVAXUSDT,SUIUSDT"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--symbols", default=DEFAULT_SYMBOLS)
    parser.add_argument("--parameter-set-id", required=True)
    parser.add_argument("--runtime-source-commit", required=True)
    parser.add_argument("--runtime-artifact-id", required=True)
    parser.add_argument("--schema-revision", default="0019_first_class_15m_domain")
    parser.add_argument("--poll-seconds", type=float, default=10.0)
    parser.add_argument("--boundary-wait-seconds", type=int, default=240)
    parser.add_argument("--max-part-bytes", type=int, default=64 * 1024 * 1024)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--status", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    health_path = args.output_dir / "health.json"
    if args.status:
        if not health_path.exists():
            print(json.dumps({"status": "NOT_STARTED", "health_path": str(health_path)}))
            return 2
        value = json.loads(health_path.read_text(encoding="utf-8"))
        print(json.dumps(value, sort_keys=True))
        return 0 if value.get("status") in {"RUNNING", "STOPPING"} and value.get("owner_active") else 2
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    config = CollectorConfig(
        output_directory=args.output_dir,
        symbols=tuple(item.strip().upper() for item in args.symbols.split(",") if item.strip()),
        parameter_set_id=args.parameter_set_id,
        runtime_source_commit=args.runtime_source_commit,
        runtime_artifact_id=args.runtime_artifact_id,
        schema_revision=args.schema_revision,
        poll_seconds=args.poll_seconds,
        boundary_wait_seconds=args.boundary_wait_seconds,
        max_part_bytes=args.max_part_bytes,
    )
    read_connection = psycopg.connect(database_url, autocommit=True, application_name="traders_scalping_calibration_reader")
    try:
        collector = ProspectiveCalibrationCollector(
            config, PostgresRepository(read_connection), PostgresCollectorOwner(database_url)
        )
        return collector.run(once=args.once)
    finally:
        read_connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
