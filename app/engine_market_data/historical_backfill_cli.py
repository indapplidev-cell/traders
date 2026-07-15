"""Command-line entry point for ENGINE-MARKET-DATA-03 historical backfill."""

import argparse
import time
from collections.abc import Sequence

from app.engine_market_data.binance_public_rest import BinancePublicRestClient
from app.engine_market_data.db.candle_repository import CandleRepository
from app.engine_market_data.db.session import create_market_data_session_factory
from app.engine_market_data.historical_backfill_config import (
    DEFAULT_BACKFILL_LIMITS,
    HistoricalBackfillConfig,
)
from app.engine_market_data.historical_backfill_planner import HistoricalBackfillPlanner
from app.engine_market_data.historical_backfill_report import (
    BackfillStatus,
    BackfillTaskReport,
    HistoricalBackfillReport,
)
from app.engine_market_data.historical_backfill_runner import HistoricalBackfillRunner
from app.engine_market_data.historical_backfill_verifier import HistoricalBackfillVerifier


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", default="BTCUSDT,ETHUSDT,SOLUSDT")
    parser.add_argument("--timeframes", default=",".join(DEFAULT_BACKFILL_LIMITS))
    for timeframe, limit in DEFAULT_BACKFILL_LIMITS.items():
        parser.add_argument(f"--limit-{timeframe}", type=int, default=limit)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--report-json")
    parser.add_argument("--report-md")
    return parser


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _config(args: argparse.Namespace) -> HistoricalBackfillConfig:
    limits = {timeframe: getattr(args, f"limit_{timeframe}") for timeframe in DEFAULT_BACKFILL_LIMITS}
    return HistoricalBackfillConfig(symbols=_csv(args.symbols), timeframes=_csv(args.timeframes),
                                    backfill_limits=limits)


def build_dry_run_report(config: HistoricalBackfillConfig, now_ms: int) -> HistoricalBackfillReport:
    plan = HistoricalBackfillPlanner().build_plan(config.symbols, config.timeframes, now_ms,
                                                   config.backfill_limits)
    report = HistoricalBackfillReport(symbols=list(config.symbols), timeframes=list(config.timeframes))
    for task in plan.tasks:
        report.task_reports.append(BackfillTaskReport(
            task.symbol, task.timeframe, task.limit, task.start_open_time_ms,
            task.end_open_time_ms, task.limit, status=BackfillStatus.SUCCESS,
        ))
    return report.finish()


def run(
    argv: Sequence[str] | None = None,
    *,
    repository: object | None = None,
    rest_client: object | None = None,
    now_ms: int | None = None,
) -> HistoricalBackfillReport:
    args = build_parser().parse_args(argv)
    if args.dry_run and args.verify_only:
        raise ValueError("--dry-run and --verify-only are mutually exclusive")
    config = _config(args)
    if args.dry_run:
        report = build_dry_run_report(config, now_ms if now_ms is not None else int(time.time() * 1000))
    else:
        client = rest_client or BinancePublicRestClient(
            max_retries=config.rest_retry_attempts,
            backoff_seconds=config.rest_backoff_seconds,
        )
        repo = repository or CandleRepository(create_market_data_session_factory())
        verifier = HistoricalBackfillVerifier(repo)
        runner = HistoricalBackfillRunner(repo, client, HistoricalBackfillPlanner(), verifier,
                                          config, now_ms=now_ms)
        report = runner.verify_all() if args.verify_only else runner.backfill_all()
    if args.report_json:
        report.write_json(args.report_json)
    if args.report_md:
        report.write_markdown(args.report_md)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    report = run(argv)
    print(report.to_json())
    return 1 if report.tasks_error else 0


if __name__ == "__main__":
    raise SystemExit(main())

