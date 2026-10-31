from __future__ import annotations

import importlib.util
from decimal import Decimal
from pathlib import Path

from app.db import paper_models
from app.engine_paper.production_preparation import (
    PaperProductionAccountIdentityBinding,
)


ROOT = Path(__file__).resolve().parents[2]


def test_0039_is_linear_and_covers_every_session_owned_economic_table():
    path = ROOT / "alembic/versions/0039_paper_accounting_session_v2.py"
    spec = importlib.util.spec_from_file_location("migration_0039", path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert migration.revision == "0039_paper_accounting_session_v2"
    assert migration.down_revision == "0038_plan_outcome_pre_selector_terminal"
    expected = {
        "paper_first_canary_sessions",
        "paper_continuous_control_events",
        "paper_execution_commands",
        "paper_plan_execution_outcomes",
        "paper_orders",
        "paper_order_events",
        "paper_fills",
        "paper_positions",
        "paper_exit_evaluation_cursors",
        "paper_exit_decisions",
        "paper_journal_entries",
    }
    assert set(migration.SESSION_TABLES) == expected


def test_all_session_owned_models_expose_non_nullable_session_identity():
    models = (
        paper_models.PaperFirstCanarySessionRecord,
        paper_models.PaperContinuousControlEventRecord,
        paper_models.PaperExecutionCommandRecord,
        paper_models.PaperPlanExecutionOutcomeRecord,
        paper_models.PaperOrderRecord,
        paper_models.PaperOrderEventRecord,
        paper_models.PaperFillRecord,
        paper_models.PaperPositionRecord,
        paper_models.PaperExitEvaluationCursorRecord,
        paper_models.PaperExitDecisionRecord,
        paper_models.PaperJournalEntryRecord,
    )
    for model in models:
        column = model.__table__.c.accounting_session_id
        assert column.nullable is False
        assert "TRADERS_PAPER_SESSION_02" in str(column.server_default.arg)


def test_real_production_identity_versions_resolve_expected_immutable_baselines():
    first = PaperProductionAccountIdentityBinding(
        "TRADERS_PAPER_MAIN", "TRADERS_PAPER_SESSION_01"
    )
    second = PaperProductionAccountIdentityBinding(
        "TRADERS_PAPER_MAIN", "TRADERS_PAPER_SESSION_02"
    )
    assert first.baseline_contract() == (
        "baseline:production-paper-v1", Decimal("100.00")
    )
    assert second.baseline_contract() == (
        "baseline:production-paper-v2", Decimal("1000.00")
    )
