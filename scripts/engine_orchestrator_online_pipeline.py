"""CLI for ENGINE-ORCHESTRATOR-01."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine_market_data.db.candle_repository import CandleRepository
from app.engine_market_data.db.session import create_market_data_session_factory
from app.engine_market_data.sync_state_repository import SyncStateRepository
from app.engine_orchestrator.closed_window_detector import ClosedWindowDetector
from app.engine_orchestrator.freshness_gate import FreshnessGate
from app.engine_orchestrator.orchestrator_config import DEFAULT_MINIMUM_WINDOWS, OrchestratorConfig
from app.engine_orchestrator.orchestrator_daemon import OrchestratorDaemon
from app.engine_orchestrator.pipeline_result_store import PipelineResultStore
from app.engine_orchestrator.pipeline_runner import PipelineRunner


def csv_values(value: str) -> tuple[str, ...]:
    values = tuple(item.strip() for item in value.split(",") if item.strip())
    if not values:
        raise argparse.ArgumentTypeError("comma-separated value must not be empty")
    return values


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Online closed-candle safe pipeline orchestrator")
    parser.add_argument("--symbols", type=csv_values, default=csv_values("BTCUSDT,ETHUSDT,SOLUSDT"))
    parser.add_argument("--primary-timeframe", default="15m")
    parser.add_argument("--required-timeframes", type=csv_values, default=csv_values("1m,5m,15m,1h,4h,1d"))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--continuous", action="store_true")
    mode.add_argument("--once", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--process-latest-only", action="store_true")
    parser.add_argument("--max-catchup-windows", type=int, default=4)
    parser.add_argument("--poll-interval-seconds", type=float, default=10)
    parser.add_argument("--health-report", type=Path, default=Path("reports/engine_orchestrator/latest_health.json"))
    parser.add_argument("--health-report-interval-seconds", type=float, default=60)
    parser.add_argument("--stop-after-cycles", type=int)
    parser.add_argument("--require-all-timeframes-ok", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--allow-stale-higher-timeframes", action=argparse.BooleanOptionalAction, default=False)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = OrchestratorConfig(
        symbols=args.symbols, primary_timeframe=args.primary_timeframe,
        required_timeframes=args.required_timeframes,
        minimum_windows={timeframe: DEFAULT_MINIMUM_WINDOWS[timeframe] for timeframe in args.required_timeframes},
        poll_interval_seconds=args.poll_interval_seconds,
        health_report_interval_seconds=args.health_report_interval_seconds,
        health_report_path=args.health_report, max_catchup_windows=args.max_catchup_windows,
        process_latest_only=args.process_latest_only,
        require_all_timeframes_ok=args.require_all_timeframes_ok,
        allow_stale_higher_timeframes=args.allow_stale_higher_timeframes,
    )
    sessions = create_market_data_session_factory()
    candle_repository = CandleRepository(sessions)
    store = PipelineResultStore(sessions)
    detector = ClosedWindowDetector(
        candle_repository, store, primary_timeframe=config.primary_timeframe,
        max_catchup_windows=config.max_catchup_windows,
        process_latest_only=config.process_latest_only,
    )
    gate = FreshnessGate(
        SyncStateRepository(sessions), config.required_timeframes,
        require_all_timeframes_ok=config.require_all_timeframes_ok,
        allow_stale_higher_timeframes=config.allow_stale_higher_timeframes,
    )
    daemon = OrchestratorDaemon(config, detector, gate, PipelineRunner(config, candle_repository), store)
    daemon.install_signal_handlers()
    observations = daemon.run(
        continuous=bool(args.continuous), dry_run=bool(args.dry_run),
        stop_after_cycles=args.stop_after_cycles,
    )
    print(json.dumps({"daemon_instance_id": daemon.daemon_instance_id,
                      "cycles": daemon.state.cycles, "observations": observations}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
