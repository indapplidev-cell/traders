from pathlib import Path


def test_repository_uses_postgres_conflict_upsert():
    source = (Path(__file__).parents[1] / "app/engine_market_data/sync_state_repository.py").read_text()
    assert "on_conflict_do_update" in source
