"""CLI for the independent ENGINE-MARKET-DATA-04 service."""

import argparse
from collections.abc import Sequence
import time

from app.engine_market_data.binance_public_rest import BinancePublicRestClient
from app.engine_market_data.continuous_sync_config import (
    ContinuousSyncConfig, DEFAULT_GAP_CHECK_WINDOWS, DEFAULT_WARMUP_DEPTHS,
)
from app.engine_market_data.continuous_sync_daemon import ContinuousSyncDaemon
from app.engine_market_data.db.candle_repository import CandleRepository
from app.engine_market_data.db.session import create_market_data_session_factory
from app.engine_market_data.sync_state_repository import SyncStateRepository


class _DryRunRepository:
    def get_latest_closed_candle(self, _symbol: str, _timeframe: str) -> None:
        return None

    def find_missing_open_times(self, _symbol: str, _timeframe: str, expected: Sequence[int]) -> list[int]:
        return list(expected)

    def upsert_candles(self, _candles: Sequence[object]) -> int:
        raise AssertionError("dry-run must never write candles")


class _DryRunRestClient:
    def fetch_server_time_ms(self) -> int:
        return int(time.time() * 1000)

    def fetch_klines(self, **_kwargs: object) -> list[object]:
        raise AssertionError("dry-run must never fetch klines")


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", default="BTCUSDT,ETHUSDT,SOLUSDT")
    parser.add_argument("--timeframes", default="1m,5m,15m,1h,4h,1d")
    warmup = parser.add_mutually_exclusive_group()
    warmup.add_argument("--warmup", dest="warmup", action="store_true")
    warmup.add_argument("--no-warmup", dest="warmup", action="store_false")
    parser.set_defaults(warmup=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--continuous", dest="continuous", action="store_true")
    mode.add_argument("--once", dest="continuous", action="store_false")
    parser.set_defaults(continuous=True)
    gaps = parser.add_mutually_exclusive_group()
    gaps.add_argument("--gap-check", dest="gap_check", action="store_true")
    gaps.add_argument("--no-gap-check", dest="gap_check", action="store_false")
    parser.set_defaults(gap_check=True)
    parser.add_argument("--health-report", default=None)
    parser.add_argument("--health-report-interval-seconds", type=float, default=60.0)
    parser.add_argument("--poll-interval-seconds", type=float, default=1.0)
    parser.add_argument("--max-rest-batch-size", type=int, default=1000)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--stop-after-cycles", type=int)
    parser.add_argument("--daemon-instance-id")
    for timeframe, depth in DEFAULT_WARMUP_DEPTHS.items():
        parser.add_argument(f"--warmup-depth-{timeframe}", type=int, default=depth)
    return parser


def config_from_args(args: argparse.Namespace) -> ContinuousSyncConfig:
    depths = {timeframe: getattr(args, f"warmup_depth_{timeframe}") for timeframe in DEFAULT_WARMUP_DEPTHS}
    return ContinuousSyncConfig(
        symbols=_csv(args.symbols), timeframes=_csv(args.timeframes), warmup=args.warmup,
        continuous=args.continuous, gap_check=args.gap_check, dry_run=args.dry_run,
        warmup_depths=depths, gap_check_windows=dict(DEFAULT_GAP_CHECK_WINDOWS),
        poll_interval_seconds=args.poll_interval_seconds,
        health_report_interval_seconds=args.health_report_interval_seconds,
        max_rest_batch_size=args.max_rest_batch_size, stop_after_cycles=args.stop_after_cycles,
        health_report_path=args.health_report, daemon_instance_id=args.daemon_instance_id,
    )


def run(argv: Sequence[str] | None = None, *, repository: object | None = None,
        rest_client: object | None = None, state_repository: object | None = None,
        clock_ms=None, sleep=None):
    args = build_parser().parse_args(argv)
    config = config_from_args(args)
    if repository is None and config.dry_run:
        repository = _DryRunRepository()
    if repository is None:
        factory = create_market_data_session_factory()
        repository = CandleRepository(factory)
        state_repository = state_repository or SyncStateRepository(factory)
    client = rest_client or (_DryRunRestClient() if config.dry_run else BinancePublicRestClient())
    kwargs = {}
    if clock_ms is not None:
        kwargs["clock_ms"] = clock_ms
    if sleep is not None:
        kwargs["sleep"] = sleep
    daemon = ContinuousSyncDaemon(config, repository, client,
                                  state_repository=state_repository, **kwargs)
    return daemon.run()


def main(argv: Sequence[str] | None = None) -> int:
    report = run(argv)
    print(report.to_json())
    return 1 if report.overall_status in {"ERROR", "DISCONNECTED"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
