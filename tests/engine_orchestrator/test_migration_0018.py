from __future__ import annotations

import importlib.util
from pathlib import Path


def test_0018_promotes_only_the_5m_profile_mode_and_is_reversible():
    path = Path("alembic/versions/0018_promote_5m_production_search.py")
    source = path.read_text(encoding="utf-8")
    assert 'revision = "0018_promote_5m_production_search"' in source
    assert 'down_revision = "0017_parallel_trade_profiles"' in source
    assert source.count("ck_online_pipeline_trade_profile") == 4
    assert "profile_mode IN ('SHADOW_SEARCH', 'PRODUCTION_SEARCH')" in source
    assert "UPDATE online_pipeline_runs SET profile_mode = 'SHADOW_SEARCH'" in source
    assert "UPDATE online_pipeline_results SET profile_mode = 'SHADOW_SEARCH'" in source


def test_0018_migration_module_imports():
    path = Path("alembic/versions/0018_promote_5m_production_search.py")
    spec = importlib.util.spec_from_file_location("migration_0018", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == "0018_promote_5m_production_search"
