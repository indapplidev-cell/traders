from __future__ import annotations

import importlib.util
from pathlib import Path

from app.server_api.schemas.paper import PaperExecutionLifecycle


def test_0038_is_linear_and_readonly_contract_accepts_absent_selector_identity():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic" / "versions" / "0038_plan_outcome_pre_selector_terminal.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0038", path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert migration.revision == "0038_plan_outcome_pre_selector_terminal"
    assert migration.down_revision == "0037_continuous_two_lifecycle_slots"

    value = PaperExecutionLifecycle.model_validate({
        "source_run_id": "run:terminal",
        "symbol": "SOLUSDT",
        "trade_profile_id": "trade-5m-v2",
        "boundary_closed_at_ms": 1,
        "candidate_id": None,
        "approval_id": None,
        "plan_id": "plan:terminal",
        "approval_valid_until_ms": 2,
        "selector_state": "NOT_ELIGIBLE",
        "selected_at": "2030-01-01T00:00:00Z",
        "scheduler_last_observed_at": "2030-01-01T00:00:00Z",
        "lifecycle_state": "EXPIRED_BEFORE_EXECUTION",
        "command_status": "EXPIRED",
        "position_status": "NOT_REACHED",
        "attempt_count": 0,
    })
    assert value.candidate_id is None and value.approval_id is None
