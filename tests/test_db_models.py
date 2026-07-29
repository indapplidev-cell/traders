from sqlalchemy import create_engine, inspect

from app.db.base import Base
import app.db.models  # noqa: F401
import app.engine_market_data.db.candle_tables  # noqa: F401
import app.engine_market_data.continuous_sync_state  # noqa: F401
import app.engine_orchestrator.orchestrator_models  # noqa: F401
import app.db.paper_models  # noqa: F401


def test_db_models_create_expected_tables() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    Base.metadata.create_all(engine)
    inspector = inspect(engine)

    assert set(inspector.get_table_names()) == {
        "market_candles",
        "ml_features",
        "ml_labels",
        "ml_model_versions",
        "ml_predictions",
        "ml_replay_results",
        "ml_replay_sessions",
        "ml_training_runs",
        "candles_1m",
        "candles_5m",
        "candles_15m",
        "candles_1h",
        "candles_4h",
        "candles_1d",
        "market_data_sync_state",
        "online_pipeline_runs",
        "online_pipeline_results",
        "paper_simulation_policies",
        "paper_execution_commands",
        "paper_orders",
        "paper_order_events",
        "paper_fills",
        "paper_positions",
        "paper_exit_decisions",
        "paper_journal_entries",
    }
