from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import sessionmaker

from app.engine_orchestrator.orchestrator_config import OrchestratorConfig
from app.engine_orchestrator.orchestrator_models import OnlinePipelineResultRow, OnlinePipelineRun
from app.engine_orchestrator.pipeline_result import PipelineResult
from app.engine_orchestrator.pipeline_result_store import PipelineResultStore


BASE = datetime(2026, 7, 17, 20, 0, 21, tzinfo=timezone.utc)
BOUNDARY = int(datetime(2026, 7, 17, 20, 0, tzinfo=timezone.utc).timestamp() * 1000)


class Clock:
    def __init__(self, value=BASE): self.value = value
    def __call__(self): return self.value


def database(url="sqlite+pysqlite:///:memory:"):
    engine = create_engine(url, connect_args={"check_same_thread": False} if ":memory:" not in url else {})
    OnlinePipelineRun.__table__.create(engine)
    OnlinePipelineResultRow.__table__.create(engine)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)


def waiting(store, *, owner="one", deadline=BASE + timedelta(seconds=159)):
    run_id = store.reserve(
        "BTCUSDT", "15m", BOUNDARY, daemon_instance_id=owner,
        trigger_source="test", freshness_deadline_at=deadline,
    )
    claim = store.get_claim(run_id)
    assert store.mark_waiting(
        claim, daemon_instance_id=owner, checked_at=BASE,
        next_retry_at=BASE + timedelta(seconds=5), reason_code="1h:BOUNDARY_NOT_READY",
        missing_timeframes=("1h",), payload={"status": "WAITING"},
    )
    return run_id


def test_waiting_is_durable_same_run_and_has_no_result_or_early_claim():
    _, sessions = database()
    clock = Clock()
    store = PipelineResultStore(sessions, clock=clock)
    run_id = waiting(store)
    with sessions() as session:
        row = session.scalar(select(OnlinePipelineRun))
        assert row.run_id == run_id
        assert (row.symbol, row.primary_timeframe, row.closed_until_ms) == ("BTCUSDT", "15m", BOUNDARY)
        assert row.status == "WAITING_FOR_REQUIRED_BOUNDARY"
        assert row.freshness_attempt_count == 1
        assert session.scalar(select(OnlinePipelineResultRow)) is None
    assert store.claim_due_waiting(daemon_instance_id="two", limit=100, now=BASE + timedelta(seconds=4)) == []
    assert store.has_window("BTCUSDT", "15m", BOUNDARY)


def test_restart_store_claims_due_row_and_preserves_original_deadline():
    _, sessions = database()
    run_id = waiting(PipelineResultStore(sessions))
    restarted = PipelineResultStore(sessions)
    claims = restarted.claim_due_waiting(
        daemon_instance_id="after-restart", limit=100, now=BASE + timedelta(seconds=5))
    assert [item.run_id for item in claims] == [run_id]
    assert claims[0].freshness_deadline_at == BASE + timedelta(seconds=159)


def test_ready_recovery_creates_exactly_one_result_and_completed_never_reruns():
    _, sessions = database()
    store = PipelineResultStore(sessions)
    run_id = waiting(store)
    claim = store.claim_due_waiting(
        daemon_instance_id="two", limit=1, now=BASE + timedelta(seconds=5))[0]
    assert store.mark_running(claim, daemon_instance_id="two", checked_at=BASE + timedelta(seconds=5), payload={})
    result = PipelineResult("BTCUSDT", "15m", BOUNDARY)
    assert store.finish(run_id, result, freshness_status="READY")
    assert not store.finish(run_id, result, freshness_status="READY")
    assert store.claim_due_waiting(
        daemon_instance_id="three", limit=1, now=BASE + timedelta(hours=1)) == []
    with sessions() as session:
        assert len(list(session.scalars(select(OnlinePipelineResultRow)))) == 1


def test_timeout_is_terminal_has_no_pipeline_result_and_never_reruns():
    _, sessions = database()
    store = PipelineResultStore(sessions)
    run_id = waiting(store)
    claim = store.claim_due_waiting(
        daemon_instance_id="two", limit=1, now=BASE + timedelta(seconds=5))[0]
    assert store.mark_terminal_freshness(
        claim, daemon_instance_id="two", checked_at=BASE + timedelta(seconds=159),
        status="SKIPPED_FRESHNESS_TIMEOUT", reason_code="FRESHNESS_TIMEOUT",
        missing_timeframes=("1h",), payload={"last": "boundary"},
    )
    assert store.claim_due_waiting(
        daemon_instance_id="three", limit=1, now=BASE + timedelta(hours=1)) == []
    with sessions() as session:
        row = session.scalar(select(OnlinePipelineRun).where(OnlinePipelineRun.run_id == run_id))
        assert row.first_wait_at and row.freshness_deadline_at and row.freshness_attempt_count == 2
        assert session.scalar(select(OnlinePipelineResultRow)) is None


def test_stale_active_claim_is_reclaimed_with_same_run_id():
    _, sessions = database()
    clock = Clock()
    store = PipelineResultStore(sessions, stale_run_after_seconds=10, clock=clock)
    run_id = store.reserve("BTCUSDT", "15m", BOUNDARY, daemon_instance_id="dead", trigger_source="test",
                           freshness_deadline_at=BASE + timedelta(seconds=180))
    claims = store.claim_due_waiting(
        daemon_instance_id="replacement", limit=1, now=BASE + timedelta(seconds=11))
    assert claims[0].run_id == run_id


def test_legacy_pending_without_started_at_keeps_stale_reclaim_semantics():
    _, sessions = database()
    with sessions() as session:
        session.add(OnlinePipelineRun(
            run_id="legacy-pending", symbol="BTCUSDT", primary_timeframe="15m",
            closed_until_ms=BOUNDARY, closed_until_utc=BASE,
            status="PENDING", trigger_source="legacy", daemon_instance_id="legacy",
        ))
        session.commit()
    claims = PipelineResultStore(sessions).claim_due_waiting(
        daemon_instance_id="replacement", limit=1, now=BASE)
    assert claims[0].run_id == "legacy-pending"


def test_two_workers_have_one_atomic_claim(tmp_path):
    path = (tmp_path / "claims.sqlite").as_posix()
    _, sessions = database(f"sqlite+pysqlite:///{path}")
    waiting(PipelineResultStore(sessions))

    def claim(owner):
        return PipelineResultStore(sessions).claim_due_waiting(
            daemon_instance_id=owner, limit=1, now=BASE + timedelta(seconds=5))

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(claim, ("worker-a", "worker-b")))
    assert sum(len(value) for value in results) == 1


@pytest.mark.parametrize("changes", [
    {"freshness_retry_interval_seconds": 0},
    {"freshness_grace_seconds": 0},
    {"freshness_max_attempts": 0},
    {"waiting_batch_size": 0},
])
def test_invalid_retry_config_rejected(changes):
    with pytest.raises(ValueError):
        OrchestratorConfig(**changes)


def test_due_query_index_is_composite():
    engine, _ = database()
    indexes = {item["name"]: item["column_names"] for item in inspect(engine).get_indexes("online_pipeline_runs")}
    assert indexes["ix_online_pipeline_runs_status_next_retry"] == ["status", "next_retry_at"]


def test_migration_chain_and_nullable_retry_contract():
    from pathlib import Path
    source = Path("alembic/versions/0008_engine_orchestrator_freshness_retry.py").read_text(encoding="utf-8")
    assert 'down_revision = "0007_engine_orchestrator_online_pipeline"' in source
    assert "WAITING_FOR_REQUIRED_BOUNDARY" in source
