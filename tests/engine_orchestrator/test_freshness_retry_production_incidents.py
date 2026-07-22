import json
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.engine_market_data.timeframe import timeframe_to_milliseconds
from app.engine_orchestrator.freshness_gate import FreshnessClassification, FreshnessGate
from app.engine_orchestrator.orchestrator_config import OrchestratorConfig
from app.engine_orchestrator.orchestrator_daemon import OrchestratorDaemon
from app.engine_orchestrator.orchestrator_models import OnlinePipelineResultRow, OnlinePipelineRun
from app.engine_orchestrator.pipeline_result import PipelineResult
from app.engine_orchestrator.pipeline_result_store import PipelineResultStore


FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures" / "freshness_retry_incidents.json").read_text(encoding="utf-8")
)


def utc(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class Clock:
    def __init__(self, value):
        self.value = value

    def __call__(self):
        return self.value


class IncidentRepo:
    def __init__(self, fixture):
        self.fixture = fixture
        self.recovered = False

    def list_for(self, symbols, timeframes):
        rows = []
        for timeframe in timeframes:
            duration = timeframe_to_milliseconds(timeframe)
            required = self.fixture["closed_until_ms"] // duration * duration
            blocking = timeframe == self.fixture["blocking_timeframe"] and not self.recovered
            available = not blocking or self.fixture["required_boundary_available"]
            close = required if available else required - duration
            rows.append(SimpleNamespace(
                timeframe=timeframe,
                status=self.fixture["health_status"] if blocking else "OK",
                last_stored_close_boundary_ms=close,
                last_stored_open_time_ms=close - duration,
            ))
        return rows


class Detector:
    def __init__(self, fixture):
        self.fixture = fixture
        self.used = False

    def get_unprocessed_closed_windows(self, symbol):
        if self.used:
            return []
        self.used = True
        return [SimpleNamespace(timeframe="15m", closed_until_ms=self.fixture["closed_until_ms"])]


class NoWindows:
    def get_unprocessed_closed_windows(self, symbol):
        return []


class Runner:
    def __init__(self):
        self.calls = 0

    def run(self, symbol, boundary):
        self.calls += 1
        return PipelineResult(symbol, "15m", boundary)


def runtime(tmp_path, fixture):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    OnlinePipelineRun.__table__.create(engine)
    OnlinePipelineResultRow.__table__.create(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    clock = Clock(utc(fixture["decision_at"]))
    repo = IncidentRepo(fixture)
    timeframes = tuple(dict.fromkeys(("15m", fixture["blocking_timeframe"])))
    config = OrchestratorConfig(
        symbols=(fixture["symbol"],), required_timeframes=timeframes,
        minimum_windows={timeframe: 1 for timeframe in timeframes},
        freshness_retry_interval_seconds=5, freshness_grace_seconds=180,
        freshness_max_attempts=1, health_report_interval_seconds=1,
        health_report_path=tmp_path / "health.json",
    )
    store = PipelineResultStore(sessions, clock=clock)
    gate = FreshnessGate(repo, timeframes, clock=clock)
    return sessions, clock, repo, config, store, gate, Runner()


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda value: value["run_id"].split(":", 1)[1])
def test_four_audit_incidents_wait_then_complete_same_run_once(tmp_path, monkeypatch, fixture):
    run_suffix = fixture["run_id"].split(":", 1)[1]
    monkeypatch.setattr(
        "app.engine_orchestrator.pipeline_result_store.uuid4",
        lambda: SimpleNamespace(hex=run_suffix),
    )
    sessions, clock, repo, config, store, gate, runner = runtime(tmp_path, fixture)
    initial = gate.check(
        fixture["symbol"], fixture["closed_until_ms"],
        deadline_at=utc(fixture["deadline_at"]), now=clock.value,
    )
    assert initial.classification == FreshnessClassification.WAITING_RETRYABLE
    assert initial.waiting_timeframes == (fixture["blocking_timeframe"],)
    blocking_availability = next(
        value for value in initial.availability
        if value.timeframe == fixture["blocking_timeframe"]
    )
    assert blocking_availability.required_boundary_available is fixture["required_boundary_available"]
    if fixture["required_boundary_available"]:
        assert blocking_availability.lag_seconds == 0

    first = OrchestratorDaemon(config, Detector(fixture), gate, runner, store, clock=clock)
    observation = first.run_cycle()[0]
    assert observation["freshness_classification"] == FreshnessClassification.WAITING_RETRYABLE
    assert observation["pipeline_status"] == "WAITING_FOR_REQUIRED_BOUNDARY"

    with sessions() as session:
        row = session.scalar(select(OnlinePipelineRun))
        assert row.run_id == fixture["run_id"]
        assert row.waiting_timeframes == [fixture["blocking_timeframe"]]
        assert row.finished_at is None
        assert session.scalar(select(func.count()).select_from(OnlinePipelineResultRow)) == 0

    repo.recovered = True
    clock.value += timedelta(seconds=5)
    recovered = gate.check(
        fixture["symbol"], fixture["closed_until_ms"],
        deadline_at=utc(fixture["deadline_at"]), now=clock.value,
    )
    assert recovered.classification == FreshnessClassification.READY
    restarted = OrchestratorDaemon(config, NoWindows(), gate, runner, store, clock=clock)
    assert restarted.run_cycle()[0]["pipeline_status"] == "COMPLETED"
    assert restarted.run_cycle() == []

    with sessions() as session:
        row = session.scalar(select(OnlinePipelineRun))
        assert row.run_id == fixture["run_id"]
        assert row.status == "COMPLETED"
        assert runner.calls == 1
        assert session.scalar(select(func.count()).select_from(OnlinePipelineResultRow)) == 1


def test_incident_blocker_at_deadline_skips_once_and_preserves_diagnostics(tmp_path, monkeypatch):
    fixture = FIXTURES[3]
    run_suffix = fixture["run_id"].split(":", 1)[1]
    monkeypatch.setattr(
        "app.engine_orchestrator.pipeline_result_store.uuid4",
        lambda: SimpleNamespace(hex=run_suffix),
    )
    sessions, clock, _, config, store, gate, runner = runtime(tmp_path, fixture)
    OrchestratorDaemon(config, Detector(fixture), gate, runner, store, clock=clock).run_cycle()
    clock.value = utc(fixture["deadline_at"])
    daemon = OrchestratorDaemon(config, NoWindows(), gate, runner, store, clock=clock)
    assert daemon.run_cycle()[0]["pipeline_status"] == "SKIPPED_FRESHNESS_NOT_OK"
    assert daemon.run_cycle() == []

    with sessions() as session:
        row = session.scalar(select(OnlinePipelineRun))
        assert row.run_id == fixture["run_id"]
        assert row.status == "SKIPPED_FRESHNESS_NOT_OK"
        assert row.final_reason == "FRESHNESS_DEADLINE_EXCEEDED"
        assert row.waiting_timeframes == ["1h"]
        assert row.last_freshness_payload["reasons"] == [
            "1h:BOUNDARY_NOT_READY", "1h:STATUS_GAP_DETECTED",
        ]
        assert session.scalar(select(func.count()).select_from(OnlinePipelineResultRow)) == 0


def test_attempt_budget_is_diagnostic_and_does_not_defer_retry_to_deadline(tmp_path):
    fixture = FIXTURES[3]
    sessions, clock, _, config, store, gate, runner = runtime(tmp_path, fixture)
    OrchestratorDaemon(config, Detector(fixture), gate, runner, store, clock=clock).run_cycle()

    with sessions() as session:
        row = session.scalar(select(OnlinePipelineRun))
        assert row.freshness_attempt_count == config.freshness_max_attempts == 1
        assert row.next_retry_at == clock.value.replace(tzinfo=None) + timedelta(seconds=5)
        assert row.next_retry_at < utc(fixture["deadline_at"]).replace(tzinfo=None)
        assert row.finished_at is None
        assert runner.calls == 0
