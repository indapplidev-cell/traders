from sqlalchemy import create_engine, inspect

from app.db.base import Base
import app.db.models  # noqa: F401
import app.engine_market_data.db.candle_tables  # noqa: F401
import app.engine_market_data.continuous_sync_state  # noqa: F401
import app.engine_orchestrator.orchestrator_models  # noqa: F401
import app.db.paper_models  # noqa: F401


def test_db_models_create_all_registered_tables() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    Base.metadata.create_all(engine)
    inspector = inspect(engine)

    registered_tables = set(Base.metadata.tables)
    assert registered_tables
    assert set(inspector.get_table_names()) == registered_tables
