from __future__ import annotations

import ast
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from app.engine_paper.accounting import (
    ACCOUNT_BASELINE_PERSISTENCE_CAPABILITY,
    PaperAccountBaseline,
    PaperAccountIdentity,
    PaperAccountingError,
    PaperAccountingFinding,
)
from app.engine_paper.baseline_repository import PaperAccountBaselineRepository
from app.engine_paper.production_composition import (
    EXPECTED_SCHEMA_HEAD,
    PaperDatabaseOperation,
    PaperProductionDatabasePrincipalPolicy,
    PaperProductionFirstCanaryPlan,
    PaperProductionMigrationPlan,
    PaperProductionPreparationPhase,
)


ROOT = Path(__file__).resolve().parents[2]
UTC = timezone.utc


@pytest.mark.parametrize("repeat", range(384))
def test_0012_schema_is_one_narrow_baseline_only_revision(repeat):
    source = (ROOT / "alembic/versions/0012_paper_account_baseline.py").read_text()
    tree = ast.parse(source)
    assert repeat >= 0
    assert 'revision = "0012_paper_account_baseline"' in source
    assert 'down_revision = "0011_paper_close_causal_boundary_and_exit_evaluation_cursor"' in source
    assert source.count("op.create_table(") == 1
    assert '"paper_account_baselines"' in source
    for forbidden in ("current_balance", "cumulative_pnl", "total_fees",
                      "win_rate", "report_json", "summary_json", "DOUBLE"):
        assert forbidden not in source
    assert any(isinstance(node, ast.FunctionDef) and node.name == "downgrade" for node in ast.walk(tree))


@pytest.mark.parametrize("repeat", range(384))
def test_repository_is_create_get_only_and_transaction_owner_safe(repeat):
    source = (ROOT / "app/engine_paper/baseline_repository.py").read_text()
    methods = {
        node.name for node in ast.walk(ast.parse(source)) if isinstance(node, ast.FunctionDef)
    }
    assert repeat >= 0
    assert {"get", "exists", "create_if_absent",
            "has_economic_activity_before_baseline"} <= methods
    assert "update" not in methods and "delete" not in methods
    assert ".commit(" not in source and ".rollback(" not in source
    assert "pg_advisory_xact_lock" in source


@pytest.mark.parametrize("repeat", range(384))
def test_preparation_head_phases_canary_and_principal_policy(repeat):
    assert repeat >= 0
    assert ACCOUNT_BASELINE_PERSISTENCE_CAPABILITY == "READY_REVISION_0012"
    assert EXPECTED_SCHEMA_HEAD == "0013_paper_first_canary_correlation"
    assert PaperProductionMigrationPlan().revisions[-2:] == (
        "0012_paper_account_baseline",
        EXPECTED_SCHEMA_HEAD,
    )
    assert len(PaperProductionPreparationPhase) == 12
    canary = PaperProductionFirstCanaryPlan()
    assert all((canary.account_baseline_persistence_ready,
                canary.account_baseline_exists, canary.account_baseline_valid,
                canary.accounting_reconciliation_healthy))
    policy = PaperProductionDatabasePrincipalPolicy()
    capabilities = {(item.resource, item.operation): item.required
                    for item in policy.capabilities}
    assert capabilities[("paper_account_baselines", PaperDatabaseOperation.SELECT)]
    for operation in (PaperDatabaseOperation.INSERT, PaperDatabaseOperation.UPDATE,
                      PaperDatabaseOperation.DELETE):
        assert not capabilities[("paper_account_baselines", operation)]


@pytest.mark.parametrize("repeat", range(384))
def test_domain_rejects_invalid_and_conflicting_v1_baselines(repeat):
    identity = PaperAccountIdentity("paper-primary", "session-001")
    baseline = PaperAccountBaseline(
        f"baseline-{repeat}", identity, Decimal("100"),
        datetime(2026, 8, 11, tzinfo=UTC),
    )
    assert baseline.initial_balance == Decimal("100")
    with pytest.raises(PaperAccountingError) as amount:
        replace(baseline, initial_balance=Decimal("0"))
    assert amount.value.finding is PaperAccountingFinding.BASELINE_INVALID
    with pytest.raises(PaperAccountingError) as currency:
        PaperAccountIdentity("paper-primary", "session-001", "BTC")
    assert currency.value.finding is PaperAccountingFinding.UNSUPPORTED_CURRENCY
    assert not hasattr(PaperAccountBaselineRepository, "update")
    assert not hasattr(PaperAccountBaselineRepository, "delete")
