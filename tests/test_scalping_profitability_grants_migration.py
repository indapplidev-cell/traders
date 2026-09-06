from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "alembic/versions/0028_scalping_profitability_grants.py"
)


def test_profitability_grants_are_conditional_and_least_privilege():
    text = MIGRATION.read_text(encoding="utf-8")

    assert "0027_scalping_profitability_integration" in text
    assert "IF EXISTS (SELECT 1 FROM pg_roles" in text
    assert "GRANT SELECT, INSERT, UPDATE ON TABLE scalping_opportunities" in text
    assert "GRANT SELECT, INSERT ON TABLE scalping_outcome_diagnostics" in text
    assert "GRANT SELECT ON TABLE scalping_opportunities, scalping_outcome_diagnostics" in text
    assert "DELETE" not in text
