"""CLI for ENGINE-ORCHESTRATOR-01."""

from __future__ import annotations

import argparse
import json
import os
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
from app.engine_paper.scalping_paper_runner import BinancePublicScalpingCostSource
from app.engine_orchestrator.profile_owner import (
    OwnerAlreadyActiveError,
    PostgresProfileOwner,
)
from sqlalchemy import text
from app.engine_orchestrator.trade_profile import (
    ACTIVE_RUNTIME_PROFILE_IDS,
    DEFAULT_TRADE_PROFILE_ID,
    TRADE_5M_CONTEXT_MINIMUM_WINDOWS,
    SCALPING_PROFILE_IDS,
    resolve_trade_profile,
)


def csv_values(value: str) -> tuple[str, ...]:
    values = tuple(item.strip() for item in value.split(",") if item.strip())
    if not values:
        raise argparse.ArgumentTypeError("comma-separated value must not be empty")
    return values


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Online closed-candle safe pipeline orchestrator")
    parser.add_argument("--symbols", type=csv_values, default=csv_values("BTCUSDT,ETHUSDT,SOLUSDT"))
    parser.add_argument(
        "--trade-profile", choices=tuple(sorted(ACTIVE_RUNTIME_PROFILE_IDS)),
        default=DEFAULT_TRADE_PROFILE_ID,
    )
    parser.add_argument("--primary-timeframe")
    parser.add_argument("--required-timeframes", type=csv_values)
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
    parser.add_argument("--strategy-cap-shadow-economic-capture", action="store_true")
    parser.add_argument("--require-all-timeframes-ok", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--allow-stale-higher-timeframes", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument(
        "--freshness-retry-interval-seconds", type=float,
        default=float(os.getenv("ORCHESTRATOR_FRESHNESS_RETRY_INTERVAL_SECONDS", "5")),
    )
    parser.add_argument(
        "--freshness-grace-seconds", type=float,
        default=float(os.getenv("ORCHESTRATOR_FRESHNESS_GRACE_SECONDS", "180")),
    )
    parser.add_argument(
        "--freshness-max-attempts", type=int,
        default=int(os.getenv("ORCHESTRATOR_FRESHNESS_MAX_ATTEMPTS", "60")),
    )
    parser.add_argument(
        "--waiting-batch-size", type=int,
        default=int(os.getenv("ORCHESTRATOR_WAITING_BATCH_SIZE", "100")),
    )
    return parser


def validate_5m_schema_capabilities(sessions: object) -> None:
    """Fail before owner election unless the deployed profile schema is exact 0017."""
    with sessions() as session:
        revision = session.scalar(text("SELECT version_num FROM alembic_version"))
        if revision not in {
            "0020_paper_plan_execution_outcomes",
            "0021_independent_scalping_profile_v2",
            "0022_scalping_v2_paper_simulation_policy",
        }:
            raise RuntimeError("online runtime requires schema 0020, 0021, or 0022")
        columns = set(session.scalars(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = current_schema() "
            "AND table_name = 'online_pipeline_runs'"
        )))
        required = {"trade_profile_id", "profile_mode"}
        if not required.issubset(columns):
            raise RuntimeError("5m runtime profile provenance columns are incomplete")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    profile = resolve_trade_profile(args.trade_profile)
    primary_timeframe = args.primary_timeframe or profile.trigger_timeframe
    required_timeframes = args.required_timeframes or (
        tuple(TRADE_5M_CONTEXT_MINIMUM_WINDOWS)
        if profile.trade_profile_id in SCALPING_PROFILE_IDS
        else csv_values("1m,5m,15m,1h,4h,1d")
    )
    minimum_windows = (
        dict(TRADE_5M_CONTEXT_MINIMUM_WINDOWS)
        if profile.trade_profile_id in SCALPING_PROFILE_IDS
        else {timeframe: DEFAULT_MINIMUM_WINDOWS[timeframe] for timeframe in required_timeframes}
    )
    health_report = args.health_report
    if profile.trade_profile_id in SCALPING_PROFILE_IDS and health_report == Path("reports/engine_orchestrator/latest_health.json"):
        health_report = Path("reports/engine_orchestrator/latest_health_trade_5m.json")
    config = OrchestratorConfig(
        symbols=args.symbols, trade_profile_id=profile.trade_profile_id,
        primary_timeframe=primary_timeframe,
        required_timeframes=required_timeframes,
        minimum_windows=minimum_windows,
        poll_interval_seconds=args.poll_interval_seconds,
        health_report_interval_seconds=args.health_report_interval_seconds,
        health_report_path=health_report, max_catchup_windows=args.max_catchup_windows,
        process_latest_only=args.process_latest_only,
        require_all_timeframes_ok=args.require_all_timeframes_ok,
        allow_stale_higher_timeframes=args.allow_stale_higher_timeframes,
        freshness_retry_interval_seconds=args.freshness_retry_interval_seconds,
        freshness_grace_seconds=args.freshness_grace_seconds,
        freshness_max_attempts=args.freshness_max_attempts,
        waiting_batch_size=args.waiting_batch_size,
    )
    # Accessing the immutable object validates the complete parameter schema
    # before any boundary detection or owner election.
    runtime_parameters = config.runtime_parameters
    sessions = create_market_data_session_factory()
    owner = None
    if profile.trade_profile_id in SCALPING_PROFILE_IDS:
        validate_5m_schema_capabilities(sessions)
        owner = PostgresProfileOwner(sessions, profile.trade_profile_id)
        try:
            owner.acquire()
        except OwnerAlreadyActiveError:
            print(json.dumps({
                "trade_profile_id": profile.trade_profile_id,
                "runtime_parameter_set_id": runtime_parameters.parameter_set_id,
                "owner_state": "OWNER_ALREADY_ACTIVE",
                "evaluated_windows": 0,
            }, sort_keys=True))
            return 3
    candle_repository = CandleRepository(sessions)
    store = PipelineResultStore(
        owner.session if owner is not None else sessions,
        owner_guard=owner,
    )
    detector = ClosedWindowDetector(
        candle_repository, store, primary_timeframe=config.primary_timeframe,
        trade_profile_id=config.trade_profile_id,
        max_catchup_windows=config.max_catchup_windows,
        process_latest_only=config.process_latest_only,
    )
    gate = FreshnessGate(
        SyncStateRepository(sessions), config.required_timeframes,
        require_all_timeframes_ok=config.require_all_timeframes_ok,
        allow_stale_higher_timeframes=config.allow_stale_higher_timeframes,
    )
    calibration_cost_source = (
        BinancePublicScalpingCostSource(
            reference_notional=runtime_parameters.vwap_reference_notional,
            depth_limit=runtime_parameters.bounded_book_depth_limit,
            maximum_age_ms=runtime_parameters.microstructure_max_age_ms,
            entry_fee_bps=runtime_parameters.economics_entry_fee_bps,
            exit_fee_bps=runtime_parameters.economics_exit_fee_bps,
            entry_slippage_bps=runtime_parameters.economics_entry_slippage_bps,
            exit_slippage_bps=runtime_parameters.economics_exit_slippage_bps,
        )
        if args.strategy_cap_shadow_economic_capture and profile.trade_profile_id in SCALPING_PROFILE_IDS
        else None
    )
    daemon = OrchestratorDaemon(
        config, detector, gate, PipelineRunner(
            config, candle_repository, strategy_cap_cost_source=calibration_cost_source,
        ), store,
        owner_guard=owner,
    )
    daemon.install_signal_handlers()
    try:
        observations = daemon.run(
            continuous=bool(args.continuous), dry_run=bool(args.dry_run),
            stop_after_cycles=args.stop_after_cycles,
        )
    finally:
        if owner is not None:
            owner.close()
    print(json.dumps({
        "daemon_instance_id": daemon.daemon_instance_id,
        "effective_config": {
            "symbols": list(config.symbols),
            "trade_profile_id": config.trade_profile_id,
            "profile_mode": config.trade_profile.mode,
            "runtime_parameter_set_id": runtime_parameters.parameter_set_id,
            "primary_timeframe": config.primary_timeframe,
            "required_timeframes": list(config.required_timeframes),
            "freshness_retry_interval_seconds": config.freshness_retry_interval_seconds,
            "freshness_grace_seconds": config.freshness_grace_seconds,
            "freshness_max_attempts": config.freshness_max_attempts,
            "waiting_batch_size": config.waiting_batch_size,
            "strategy_cap_shadow_economic_capture": bool(calibration_cost_source),
        },
        "cycles": daemon.state.cycles,
        "observations": observations,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
