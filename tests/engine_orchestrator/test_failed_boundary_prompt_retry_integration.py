from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.engine_market_data.continuous_sync_config import ContinuousSyncConfig
from app.engine_market_data.continuous_sync_daemon import (
    ContinuousSyncDaemon,
    DueSyncTask,
)
from app.engine_market_data.errors import PublicMarketDataError
from app.engine_market_data.freshness_monitor import close_boundary_ms
from app.engine_orchestrator.freshness_gate import FreshnessGate
from app.engine_orchestrator.orchestrator_config import OrchestratorConfig
from app.engine_orchestrator.orchestrator_daemon import OrchestratorDaemon
from app.engine_orchestrator.orchestrator_models import (
    OnlinePipelineResultRow,
    OnlinePipelineRun,
)
from app.engine_orchestrator.pipeline_result import PipelineResult
from app.engine_orchestrator.pipeline_result_store import PipelineResultStore
from tests.engine_market_data_04_helpers import FakeRepository, FakeRest, candle


BOUNDARY_DT = datetime(2026, 7, 17, 20, 0, tzinfo=timezone.utc)
BOUNDARY_MS = int(BOUNDARY_DT.timestamp() * 1000)
HOUR_OPEN_MS = BOUNDARY_MS - 60 * 60_000


class Clock:
    def __init__(self, value):
        self.value = value

    def __call__(self):
        return self.value


class Detector:
    def __init__(self, duplicates=1):
        self.used = False
        self.duplicates = duplicates

    def get_unprocessed_closed_windows(self, _symbol):
        if self.used:
            return []
        self.used = True
        return [
            SimpleNamespace(timeframe="15m", closed_until_ms=BOUNDARY_MS)
            for _ in range(self.duplicates)
        ]


class NoWindows:
    def get_unprocessed_closed_windows(self, _symbol):
        return []


class Runner:
    def __init__(self):
        self.calls = 0

    def run(self, symbol, boundary):
        self.calls += 1
        return PipelineResult(symbol, "15m", boundary)


class FailThenSucceedRest(FakeRest):
    def __init__(self, now_ms, failures):
        super().__init__(now_ms)
        self.failures = failures

    def fetch_klines(self, **kwargs):
        if self.failures > 0:
            self.failures -= 1
            try:
                raise OSError("connection reset")
            except OSError as cause:
                raise PublicMarketDataError(
                    "Binance public REST request failed") from cause
        return super().fetch_klines(**kwargs)


class DaemonStateRows:
    def __init__(self, daemon, now_ms):
        self.daemon = daemon
        self.now_ms = now_ms

    def list_for(self, symbols, timeframes):
        report = self.daemon.build_health_report(self.now_ms)
        by_pair = {(row.symbol, row.timeframe): row for row in report.snapshots}
        rows = []
        for symbol in symbols:
            for timeframe in timeframes:
                snapshot = by_pair[(symbol, timeframe)]
                latest = self.daemon.repository.get_latest_closed_candle(
                    symbol, timeframe)
                rows.append(SimpleNamespace(
                    timeframe=timeframe,
                    status=snapshot.status,
                    last_stored_open_time_ms=(
                        latest.open_time_ms if latest else None),
                    last_stored_close_boundary_ms=(
                        close_boundary_ms(latest.open_time_ms, timeframe)
                        if latest else None),
                ))
        return rows


def runtime(tmp_path, *, market_failures=1, duplicates=1):
    repository = FakeRepository([
        candle("BTCUSDT", "15m", BOUNDARY_MS - 15 * 60_000),
    ])
    market_now = BOUNDARY_MS + 21_000
    rest = FailThenSucceedRest(market_now, market_failures)
    market = ContinuousSyncDaemon(
        ContinuousSyncConfig(
            symbols=["BTCUSDT"],
            timeframes=["15m", "1h"],
            warmup=False,
            continuous=True,
            gap_check=False,
        ),
        repository,
        rest,
    )
    failed = market.sync_scheduled_boundary(
        DueSyncTask("BTCUSDT", "1h", HOUR_OPEN_MS), market_now)
    assert failed.missing_after == 1

    engine = create_engine("sqlite+pysqlite:///:memory:")
    OnlinePipelineRun.__table__.create(engine)
    OnlinePipelineResultRow.__table__.create(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    clock = Clock(BOUNDARY_DT + timedelta(seconds=21))
    store = PipelineResultStore(sessions, clock=clock)
    state_rows = DaemonStateRows(market, market_now)
    gate = FreshnessGate(state_rows, ("15m", "1h"), clock=clock)
    runner = Runner()
    config = OrchestratorConfig(
        symbols=("BTCUSDT",),
        required_timeframes=("15m", "1h"),
        minimum_windows={"15m": 1, "1h": 1},
        freshness_retry_interval_seconds=5,
        freshness_grace_seconds=180,
        health_report_interval_seconds=1,
        health_report_path=tmp_path / "health.json",
    )
    detector = Detector(duplicates)
    return (
        sessions,
        clock,
        store,
        gate,
        runner,
        config,
        detector,
        market,
        state_rows,
    )


def test_failure_prompt_retry_recovers_same_run_ready_exactly_once(tmp_path):
    sessions, clock, store, gate, runner, config, detector, market, rows = (
        runtime(tmp_path))
    first = OrchestratorDaemon(
        config, detector, gate, runner, store, clock=clock).run_cycle()[0]
    run_id = first["run_id"]

    record = next(iter(market._failed_boundary_retries.values()))
    rows.now_ms = record.next_retry_at_ms
    recovered = market.run_prompt_retries(record.next_retry_at_ms)
    clock.value += timedelta(seconds=5)
    second_daemon = OrchestratorDaemon(
        config, NoWindows(), gate, runner, store, clock=clock)
    second = second_daemon.run_cycle()[0]
    second_daemon.run_cycle()

    assert first["pipeline_status"] == "WAITING_FOR_REQUIRED_BOUNDARY"
    assert recovered[0].missing_after == 0
    assert second["run_id"] == run_id
    assert second["pipeline_status"] == "COMPLETED"
    assert runner.calls == 1
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(
            OnlinePipelineRun)) == 1
        assert session.scalar(select(func.count()).select_from(
            OnlinePipelineResultRow)) == 1


def test_persistent_failure_exhausts_prompt_policy_then_legitimately_skips(tmp_path):
    sessions, clock, store, gate, runner, config, detector, market, rows = (
        runtime(tmp_path, market_failures=99))
    first = OrchestratorDaemon(
        config, detector, gate, runner, store, clock=clock).run_cycle()[0]

    while True:
        record = next(iter(market._failed_boundary_retries.values()))
        if record.next_retry_at_ms is None:
            break
        rows.now_ms = record.next_retry_at_ms
        market.run_prompt_retries(record.next_retry_at_ms)
    clock.value = BOUNDARY_DT + timedelta(seconds=180)
    final = OrchestratorDaemon(
        config, NoWindows(), gate, runner, store, clock=clock).run_cycle()[0]

    assert final["run_id"] == first["run_id"]
    assert final["pipeline_status"] == "SKIPPED_FRESHNESS_NOT_OK"
    assert runner.calls == 0
    assert market.prompt_retry_metrics.executed == 4
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(
            OnlinePipelineResultRow)) == 0


def test_late_recovery_does_not_mutate_terminal_skipped_run(tmp_path):
    sessions, clock, store, gate, runner, config, detector, market, rows = (
        runtime(tmp_path, market_failures=99))
    first = OrchestratorDaemon(
        config, detector, gate, runner, store, clock=clock).run_cycle()[0]
    clock.value = BOUNDARY_DT + timedelta(seconds=180)
    terminal_daemon = OrchestratorDaemon(
        config, NoWindows(), gate, runner, store, clock=clock)
    terminal = terminal_daemon.run_cycle()[0]

    market.rest_client = FakeRest(BOUNDARY_MS + 181_000)
    rows.now_ms = BOUNDARY_MS + 181_000
    recovered = market.sync_expected(
        "BTCUSDT", "1h", [HOUR_OPEN_MS], HOUR_OPEN_MS, rows.now_ms)
    clock.value = BOUNDARY_DT + timedelta(seconds=181)
    after = OrchestratorDaemon(
        config, NoWindows(), gate, runner, store, clock=clock).run_cycle()

    assert terminal["run_id"] == first["run_id"]
    assert terminal["pipeline_status"] == "SKIPPED_FRESHNESS_NOT_OK"
    assert recovered.missing_after == 0
    assert gate.check("BTCUSDT", BOUNDARY_MS).allowed
    assert after == []
    assert runner.calls == 0
    with sessions() as session:
        row = session.scalar(select(OnlinePipelineRun))
        assert row.status == "SKIPPED_FRESHNESS_NOT_OK"
        assert session.scalar(select(func.count()).select_from(
            OnlinePipelineResultRow)) == 0


def test_duplicate_scheduler_window_plus_retry_has_one_run_and_result(tmp_path):
    sessions, clock, store, gate, runner, config, detector, market, rows = (
        runtime(tmp_path, duplicates=2))
    first_cycle = OrchestratorDaemon(
        config, detector, gate, runner, store, clock=clock).run_cycle()
    record = next(iter(market._failed_boundary_retries.values()))
    rows.now_ms = record.next_retry_at_ms
    market.run_prompt_retries(record.next_retry_at_ms)
    clock.value += timedelta(seconds=5)
    OrchestratorDaemon(
        config, NoWindows(), gate, runner, store, clock=clock).run_cycle()

    assert [item["pipeline_status"] for item in first_cycle] == [
        "WAITING_FOR_REQUIRED_BOUNDARY",
        "SKIPPED_DUPLICATE_WINDOW",
    ]
    assert runner.calls == 1
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(
            OnlinePipelineRun)) == 1
        assert session.scalar(select(func.count()).select_from(
            OnlinePipelineResultRow)) == 1
