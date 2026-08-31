from pathlib import Path


def test_0019_is_forward_only_identity_enforcement_without_history_rewrite():
    source = Path("alembic/versions/0019_first_class_15m_domain.py").read_text(
        encoding="utf-8"
    )
    assert 'revision = "0019_first_class_15m_domain"' in source
    assert 'down_revision = "0018_promote_5m_production_search"' in source
    assert "BEFORE INSERT OR UPDATE" in source
    assert "trade_profile_id = NEW.trade_profile_id" in source
    assert "primary_timeframe = NEW.primary_timeframe" in source
    assert "closed_until_ms = NEW.closed_until_ms" in source
    assert "UPDATE online_pipeline_results" not in source
    assert "def downgrade" not in source
