from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.engine_market_data.continuous_sync_config import ContinuousSyncConfig
from app.engine_market_data.continuous_sync_daemon import ContinuousSyncDaemon
from app.engine_market_data.freshness_monitor import close_boundary_ms
from app.engine_orchestrator.freshness_gate import FreshnessGate
from app.engine_orchestrator.orchestrator_config import OrchestratorConfig
from app.engine_orchestrator.orchestrator_daemon import OrchestratorDaemon
from app.engine_orchestrator.orchestrator_models import OnlinePipelineResultRow, OnlinePipelineRun
from app.engine_orchestrator.pipeline_result import PipelineResult
from app.engine_orchestrator.pipeline_result_store import PipelineResultStore
from tests.engine_market_data_04_helpers import FakeRepository, FakeRest, candle


BOUNDARY_DT = datetime(2026, 7, 17, 20, 0, tzinfo=timezone.utc)
BOUNDARY_MS = int(BOUNDARY_DT.timestamp() * 1000)


class Clock:
    def __init__(self, value): self.value = value
    def __call__(self): return self.value


class Detector:
    def __init__(self): self.used = False
    def get_unprocessed_closed_windows(self, _symbol):
        if self.used: return []
        self.used = True
        return [SimpleNamespace(timeframe="15m", closed_until_ms=BOUNDARY_MS)]


class NoWindows:
    def get_unprocessed_closed_windows(self, _symbol): return []


class Runner:
    def __init__(self): self.calls = 0
    def run(self, symbol, boundary):
        self.calls += 1
        return PipelineResult(symbol, "15m", boundary)


class DaemonStateRows:
    def __init__(self, daemon): self.daemon = daemon
    def list_for(self, symbols, timeframes):
        report = self.daemon.build_health_report(BOUNDARY_MS + 21_000)
        by_pair = {(row.symbol, row.timeframe): row for row in report.snapshots}
        rows = []
        for symbol in symbols:
            for timeframe in timeframes:
                snapshot = by_pair[(symbol, timeframe)]
                latest = self.daemon.repository.get_latest_closed_candle(symbol, timeframe)
                rows.append(SimpleNamespace(
                    timeframe=timeframe,
                    status=snapshot.status,
                    last_stored_open_time_ms=(latest.open_time_ms if latest else None),
                    last_stored_close_boundary_ms=(
                        close_boundary_ms(latest.open_time_ms, timeframe) if latest else None),
                ))
        return rows


def runtime(tmp_path):
    repository = FakeRepository([
        candle("BTCUSDT", "15m", BOUNDARY_MS - 15 * 60_000),
        candle("BTCUSDT", "1h", BOUNDARY_MS - 60 * 60_000),
    ])
    market_daemon = ContinuousSyncDaemon(
        ContinuousSyncConfig(
            symbols=["BTCUSDT"], timeframes=["15m", "1h"],
            warmup=False, continuous=False, gap_check=False,
        ),
        repository, FakeRest(BOUNDARY_MS + 21_000),
    )
    market_daemon._pair_status[("BTCUSDT", "15m")] = "OK"
    market_daemon._pair_status[("BTCUSDT", "1h")] = "DEGRADED"
    market_daemon._pair_errors[("BTCUSDT", "1h")] = "historical transient failure"
    market_daemon._pair_missing[("BTCUSDT", "15m")] = 0
    market_daemon._pair_missing[("BTCUSDT", "1h")] = 0

    engine = create_engine("sqlite+pysqlite:///:memory:")
    OnlinePipelineRun.__table__.create(engine)
    OnlinePipelineResultRow.__table__.create(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    clock = Clock(BOUNDARY_DT + timedelta(seconds=21))
    store = PipelineResultStore(sessions, clock=clock)
    gate = FreshnessGate(DaemonStateRows(market_daemon), ("15m", "1h"), clock=clock)
    runner = Runner()
    config = OrchestratorConfig(
        symbols=("BTCUSDT",), required_timeframes=("15m", "1h"),
        minimum_windows={"15m": 1, "1h": 1}, freshness_retry_interval_seconds=5,
        freshness_grace_seconds=180, health_report_interval_seconds=1,
        health_report_path=tmp_path / "health.json",
    )
    return sessions, clock, store, gate, runner, config, market_daemon


def test_status_only_waiting_recovers_same_run_exactly_once(tmp_path):
    sessions, clock, store, gate, runner, config, market_daemon = runtime(tmp_path)
    first = OrchestratorDaemon(config, Detector(), gate, runner, store, clock=clock).run_cycle()[0]
    run_id = first["run_id"]
    assert first["pipeline_status"] == "WAITING_FOR_REQUIRED_BOUNDARY"
    assert first["freshness_reasons"] == ["1h:STATUS_DEGRADED"]

    expected_open = BOUNDARY_MS - 60 * 60_000
    market_daemon.sync_expected("BTCUSDT", "1h", [expected_open], expected_open, BOUNDARY_MS + 21_000)
    clock.value += timedelta(seconds=5)
    recovered = OrchestratorDaemon(config, NoWindows(), gate, runner, store, clock=clock)
    second = recovered.run_cycle()[0]
    recovered.run_cycle()

    assert second["run_id"] == run_id
    assert second["pipeline_status"] == "COMPLETED"
    assert runner.calls == 1
    with sessions() as session:
        run = session.scalar(select(OnlinePipelineRun))
        assert run.run_id == run_id and run.status == "COMPLETED"
        assert run.freshness_attempt_count == 2
        assert session.scalar(select(func.count()).select_from(OnlinePipelineResultRow)) == 1


def test_clearing_error_without_required_candle_still_skips_at_deadline(tmp_path):
    sessions, clock, store, gate, runner, config, market_daemon = runtime(tmp_path)
    market_daemon.repository.values.pop(("BTCUSDT", "1h", BOUNDARY_MS - 60 * 60_000))
    first = OrchestratorDaemon(config, Detector(), gate, runner, store, clock=clock).run_cycle()[0]
    run_id = first["run_id"]
    market_daemon._pair_errors.pop(("BTCUSDT", "1h"), None)
    market_daemon._pair_status[("BTCUSDT", "1h")] = "OK"
    clock.value = BOUNDARY_DT + timedelta(seconds=180)
    final = OrchestratorDaemon(config, NoWindows(), gate, runner, store, clock=clock).run_cycle()[0]

    assert final["run_id"] == run_id
    assert final["pipeline_status"] == "SKIPPED_FRESHNESS_NOT_OK"
    assert runner.calls == 0
    with sessions() as session:
        run = session.scalar(select(OnlinePipelineRun))
        assert run.final_reason == "FRESHNESS_DEADLINE_EXCEEDED"
        assert session.scalar(select(func.count()).select_from(OnlinePipelineResultRow)) == 0


def test_current_pair_error_with_candle_still_skips_at_deadline(tmp_path):
    sessions, clock, store, gate, runner, config, market_daemon = runtime(tmp_path)
    market_daemon._pair_status[("BTCUSDT", "1h")] = "ERROR"
    first = OrchestratorDaemon(config, Detector(), gate, runner, store, clock=clock).run_cycle()[0]
    run_id = first["run_id"]
    assert first["freshness_reasons"] == ["1h:STATUS_ERROR"]

    clock.value = BOUNDARY_DT + timedelta(seconds=180)
    final = OrchestratorDaemon(config, NoWindows(), gate, runner, store, clock=clock).run_cycle()[0]

    assert final["run_id"] == run_id
    assert final["pipeline_status"] == "SKIPPED_FRESHNESS_NOT_OK"
    assert runner.calls == 0
    with sessions() as session:
        run = session.scalar(select(OnlinePipelineRun))
        assert run.final_reason == "FRESHNESS_DEADLINE_EXCEEDED"
        assert session.scalar(select(func.count()).select_from(OnlinePipelineResultRow)) == 0
