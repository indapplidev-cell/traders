import importlib.util
from pathlib import Path


MIGRATION = Path(__file__).parents[1] / "alembic/versions/0006_engine_market_data_sync_state.py"


def load_migration():
    spec = importlib.util.spec_from_file_location("engine_market_data_04_migration", MIGRATION)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_fits_explicitly_widened_alembic_version_column():
    migration = load_migration()
    assert len(migration.revision) == 34
    assert migration.ALEMBIC_VERSION_LENGTH >= len(migration.revision)


def test_version_column_is_widened_before_sync_state_table_is_created():
    source = MIGRATION.read_text(encoding="utf-8")
    assert source.index('op.alter_column(\n        "alembic_version"') < source.index(
        'op.create_table(\n        "market_data_sync_state"'
    )


def test_downgrade_keeps_compatible_version_column_width():
    source = MIGRATION.read_text(encoding="utf-8")
    downgrade = source[source.index("def downgrade()") :]
    assert 'op.drop_table("market_data_sync_state")' in downgrade
    assert "op.alter_column" not in downgrade
