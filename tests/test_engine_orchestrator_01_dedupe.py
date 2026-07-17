from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.engine_orchestrator.orchestrator_models import OnlinePipelineResultRow, OnlinePipelineRun
from app.engine_orchestrator.pipeline_result_store import PipelineResultStore
from tests.engine_orchestrator_01_helpers import BOUNDARY


def test_reservation_is_unique():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    OnlinePipelineRun.__table__.create(engine)
    OnlinePipelineResultRow.__table__.create(engine)
    store = PipelineResultStore(sessionmaker(bind=engine, expire_on_commit=False))
    assert store.reserve("BTCUSDT", "15m", BOUNDARY, daemon_instance_id="one", trigger_source="test")
    assert store.reserve("BTCUSDT", "15m", BOUNDARY, daemon_instance_id="two", trigger_source="test") is None
