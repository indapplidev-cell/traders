import importlib.util
from pathlib import Path


def test_migration_is_in_existing_chain_and_lists_all_tables():
    path = Path(__file__).parents[1] / "alembic/versions/0005_engine_market_data_mtf_candles.py"
    spec = importlib.util.spec_from_file_location("engine_market_data_migration", path)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert migration.down_revision == "0004_opportunity_labels"
    assert set(migration.TABLES) == {"candles_1m", "candles_5m", "candles_15m", "candles_1h", "candles_4h", "candles_1d"}
