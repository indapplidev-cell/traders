from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.engine_orchestrator.orchestrator_models import OnlinePipelineResultRow, OnlinePipelineRun
from app.engine_orchestrator.pipeline_result import PipelineResult
from app.engine_orchestrator.pipeline_result_store import PipelineResultStore


def test_store_finishes_run_and_payload():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    OnlinePipelineRun.__table__.create(engine)
    OnlinePipelineResultRow.__table__.create(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    store = PipelineResultStore(sessions)
    run_id = store.reserve("BTCUSDT", "15m", 900000, daemon_instance_id="test", trigger_source="test")
    claim = store.get_claim(run_id)
    from datetime import datetime, timezone
    store.mark_running(claim, daemon_instance_id="test", checked_at=datetime.now(timezone.utc), payload={})
    store.finish(run_id, PipelineResult("BTCUSDT", "15m", 900000), freshness_status="OK")
    with sessions() as session:
        assert session.scalar(select(OnlinePipelineRun)).status == "COMPLETED"
        assert session.scalar(select(OnlinePipelineResultRow)).safety_counters_json["future_bars_used_count"] == 0
