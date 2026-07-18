import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.engine_market_data.timeframe import timeframe_to_milliseconds
from app.engine_orchestrator.freshness_gate import FreshnessGate
from app.engine_orchestrator.orchestrator_config import OrchestratorConfig
from app.engine_orchestrator.orchestrator_daemon import OrchestratorDaemon
from app.engine_orchestrator.orchestrator_models import OnlinePipelineResultRow, OnlinePipelineRun
from app.engine_orchestrator.pipeline_result import PipelineResult
from app.engine_orchestrator.pipeline_result_store import PipelineResultStore


BOUNDARY_DT = datetime(2026, 7, 17, 20, 0, tzinfo=timezone.utc)
BOUNDARY = int(BOUNDARY_DT.timestamp() * 1000)


class Clock:
    def __init__(self, value): self.value = value
    def __call__(self): return self.value


class Detector:
    def __init__(self): self.used = False
    def get_unprocessed_closed_windows(self, symbol):
        if self.used: return []
        self.used = True
        return [SimpleNamespace(timeframe="15m", closed_until_ms=BOUNDARY)]


class SyncRepo:
    def __init__(self, clock, hour_available_at):
        self.clock = clock
        self.hour_available_at = hour_available_at

    def list_for(self, symbols, timeframes):
        rows = []
        for timeframe in timeframes:
            duration = timeframe_to_milliseconds(timeframe)
            required = BOUNDARY // duration * duration
            available = timeframe != "1h" or self.clock() >= self.hour_available_at
            close = required if available else required - duration
            rows.append(SimpleNamespace(
                timeframe=timeframe, status="OK", last_stored_close_boundary_ms=close,
                last_stored_open_time_ms=close - duration,
            ))
        return rows


class Runner:
    def __init__(self):
        self.calls = 0
        self.snapshot_builds = 0
    def run(self, symbol, boundary):
        self.calls += 1
        self.snapshot_builds += 1
        return PipelineResult(symbol, "15m", boundary)


def runtime(tmp_path, *, available_offset=61):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    OnlinePipelineRun.__table__.create(engine)
    OnlinePipelineResultRow.__table__.create(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    clock = Clock(BOUNDARY_DT + timedelta(seconds=21))
    store = PipelineResultStore(sessions, clock=clock)
    gate = FreshnessGate(SyncRepo(clock, BOUNDARY_DT + timedelta(seconds=available_offset)),
                         ("15m", "1h"), clock=clock)
    runner = Runner()
    config = OrchestratorConfig(
        symbols=("BTCUSDT",), required_timeframes=("15m", "1h"),
        minimum_windows={"15m": 1, "1h": 1}, freshness_retry_interval_seconds=5,
        freshness_grace_seconds=180, health_report_interval_seconds=1,
        health_report_path=tmp_path / "health.json",
    )
    return sessions, clock, store, gate, runner, config


def test_waiting_builds_no_snapshot_or_downstream_then_restart_recovers_once(tmp_path):
    sessions, clock, store, gate, runner, config = runtime(tmp_path)
    first = OrchestratorDaemon(config, Detector(), gate, runner, store, daemon_instance_id="first", clock=clock)
    assert first.run_cycle()[0]["pipeline_status"] == "WAITING_FOR_REQUIRED_BOUNDARY"
    assert runner.calls == 0 and runner.snapshot_builds == 0
    health = json.loads((tmp_path / "health.json").read_text(encoding="utf-8"))
    assert health["waiting_windows"] == 1
    assert health["waiting_by_timeframe"] == {"1h": 1}
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(OnlinePipelineResultRow)) == 0
    clock.value = BOUNDARY_DT + timedelta(seconds=66)
    restarted = OrchestratorDaemon(config, DetectorWithNoWindows(), gate, runner, store,
                                   daemon_instance_id="restart", clock=clock)
    observations = restarted.run_cycle()
    assert observations[0]["pipeline_status"] == "COMPLETED"
    assert runner.calls == 1 and runner.snapshot_builds == 1
    restarted.run_cycle()
    assert runner.calls == 1 and runner.snapshot_builds == 1
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(OnlinePipelineResultRow)) == 1
        row = session.scalar(select(OnlinePipelineRun))
        assert row.freshness_attempt_count == 2 and row.freshness_recovered_at


class DetectorWithNoWindows:
    def get_unprocessed_closed_windows(self, symbol): return []


def test_not_due_waiting_is_not_claimed_and_processor_has_no_sleep(tmp_path):
    _, clock, store, gate, runner, config = runtime(tmp_path)
    daemon = OrchestratorDaemon(config, Detector(), gate, runner, store, clock=clock)
    daemon.run_cycle()
    clock.value += timedelta(seconds=4)
    assert OrchestratorDaemon(config, DetectorWithNoWindows(), gate, runner, store, clock=clock).run_cycle() == []
    assert runner.calls == 0
    import inspect
    from app.engine_orchestrator import orchestrator_daemon
    assert "sleep(" not in inspect.getsource(orchestrator_daemon.OrchestratorDaemon._process_claim)


def test_deadline_timeout_is_distinct_and_not_rerun(tmp_path):
    sessions, clock, store, gate, runner, config = runtime(tmp_path, available_offset=999)
    OrchestratorDaemon(config, Detector(), gate, runner, store, clock=clock).run_cycle()
    clock.value = BOUNDARY_DT + timedelta(seconds=180)
    daemon = OrchestratorDaemon(config, DetectorWithNoWindows(), gate, runner, store, clock=clock)
    assert daemon.run_cycle()[0]["pipeline_status"] == "SKIPPED_FRESHNESS_TIMEOUT"
    assert daemon.run_cycle() == [] and runner.calls == 0
    with sessions() as session:
        assert session.scalar(select(OnlinePipelineRun)).status == "SKIPPED_FRESHNESS_TIMEOUT"
        assert session.scalar(select(func.count()).select_from(OnlinePipelineResultRow)) == 0
