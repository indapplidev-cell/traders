from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from app.engine_paper.controlled_runtime import (
    PAPER_CONTROLLED_RUNTIME_DRY_RUN_CONTRACT_VERSION,
    PaperControlledRuntimeAction,
    PaperControlledRuntimeAvailableInputSummary,
    PaperControlledRuntimeConfiguration,
    PaperControlledRuntimeDryRunRequest,
    PaperControlledRuntimeTarget,
    PaperDatabaseAccessMode,
)
from app.engine_paper.controlled_worker import PaperLifecycleCycleScope
from app.engine_safety import ExecutionMode
from tests.paper_controlled_worker_retry.conftest import build_graphs
from tests.paper_repository.conftest import (  # noqa: F401
    paper_session_factory,
    repository_postgres_engine,
)


NOW = datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def lifecycle_graphs():
    return build_graphs()


@pytest.fixture
def paper_configuration():
    return PaperControlledRuntimeConfiguration(
        runtime_action=PaperControlledRuntimeAction.DRY_RUN_PLAN,
        target=PaperControlledRuntimeTarget.ISOLATED_POSTGRESQL,
        execution_mode=ExecutionMode.PAPER,
        runtime_enabled=True,
        dry_run_enabled=True,
        explicit_paper_authorization=True,
        cycle_scope=PaperLifecycleCycleScope.ADVANCE_ONE_LIFECYCLE_STEP,
        max_stages_per_cycle=1,
        allowed_symbols=("BTCUSDT",),
        database_access_mode=PaperDatabaseAccessMode.ISOLATED_READ_ONLY,
        created_at=NOW,
        configuration_id="runtime:config:test",
    )


@pytest.fixture
def make_request(paper_configuration):
    def factory(**changes):
        values = {
            "request_id": "runtime:request:test",
            "contract_version": PAPER_CONTROLLED_RUNTIME_DRY_RUN_CONTRACT_VERSION,
            "configuration": paper_configuration,
            "symbol": "BTCUSDT",
            "cycle_id": "runtime:cycle:test",
            "correlation_id": "runtime:correlation:test",
            "command_id": "command:service:1",
            "created_at": NOW,
            "available_inputs": PaperControlledRuntimeAvailableInputSummary(),
        }
        values.update(changes)
        return PaperControlledRuntimeDryRunRequest(**values)

    return factory


class StaticGraphLoader:
    def __init__(self, graph):
        self.graph = graph
        self.calls = 0
        self.last_database_read_only_transaction = True

    def load(self, command_id):
        self.calls += 1
        return self.graph
