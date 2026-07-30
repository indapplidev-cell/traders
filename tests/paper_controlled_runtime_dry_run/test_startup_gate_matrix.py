from __future__ import annotations

from dataclasses import replace
from itertools import product

import pytest

from app.engine_paper.controlled_runtime import (
    PaperControlledRuntimeAction,
    PaperControlledRuntimeConfiguration,
    PaperControlledRuntimeOutcome,
    PaperControlledRuntimeTarget,
    PaperDatabaseAccessMode,
    evaluate_controlled_runtime_startup_gate,
)
from app.engine_paper.controlled_worker import PaperLifecycleCycleScope
from app.engine_safety import ExecutionMode


def _paper(**changes):
    values = {
        "runtime_action": PaperControlledRuntimeAction.DRY_RUN_PLAN,
        "target": PaperControlledRuntimeTarget.ISOLATED_POSTGRESQL,
        "execution_mode": ExecutionMode.PAPER,
        "runtime_enabled": True,
        "dry_run_enabled": True,
        "explicit_paper_authorization": True,
        "allowed_symbols": ("BTCUSDT",),
        "database_access_mode": PaperDatabaseAccessMode.ISOLATED_READ_ONLY,
    }
    values.update(changes)
    return PaperControlledRuntimeConfiguration(**values)


@pytest.mark.parametrize(
    ("field", "expected"),
    (
        ("network_access_allowed", PaperControlledRuntimeOutcome.NETWORK_ACCESS_FORBIDDEN),
        ("polling_allowed", PaperControlledRuntimeOutcome.POLLING_FORBIDDEN),
        ("scheduler_allowed", PaperControlledRuntimeOutcome.SCHEDULER_FORBIDDEN),
        ("daemon_allowed", PaperControlledRuntimeOutcome.DAEMON_FORBIDDEN),
    ),
)
def test_each_ambient_runtime_capability_fails_closed(field, expected):
    result = evaluate_controlled_runtime_startup_gate(_paper(**{field: True}))
    assert result.outcome is expected
    assert result.ready is False


@pytest.mark.parametrize(
    "action",
    (
        PaperControlledRuntimeAction.EXECUTE,
        PaperControlledRuntimeAction.START,
        PaperControlledRuntimeAction.RUN_CONTINUOUS,
        PaperControlledRuntimeAction.DAEMON,
        PaperControlledRuntimeAction.SCHEDULE,
        PaperControlledRuntimeAction.LIVE,
    ),
)
def test_every_executable_action_is_not_implemented(action):
    assert (
        evaluate_controlled_runtime_startup_gate(_paper(runtime_action=action)).outcome
        is PaperControlledRuntimeOutcome.RUNTIME_EXECUTION_NOT_IMPLEMENTED
    )


@pytest.mark.parametrize(
    ("changes", "expected"),
    (
        ({"execution_mode": ExecutionMode.LIVE}, PaperControlledRuntimeOutcome.LIVE_FORBIDDEN),
        (
            {"target": PaperControlledRuntimeTarget.PRODUCTION_MUTATING},
            PaperControlledRuntimeOutcome.PRODUCTION_MUTATION_FORBIDDEN,
        ),
        ({"runtime_action": "UNKNOWN"}, PaperControlledRuntimeOutcome.UNSUPPORTED_RUNTIME_ACTION),
        ({"target": "UNKNOWN"}, PaperControlledRuntimeOutcome.INVALID_TARGET),
        ({"cycle_scope": "UNKNOWN"}, PaperControlledRuntimeOutcome.INVALID_SCOPE),
        ({"max_stages_per_cycle": 0}, PaperControlledRuntimeOutcome.MAX_STAGES_EXCEEDED),
        ({"max_stages_per_cycle": 5}, PaperControlledRuntimeOutcome.MAX_STAGES_EXCEEDED),
        ({"runtime_enabled": False}, PaperControlledRuntimeOutcome.RUNTIME_DISABLED),
        ({"dry_run_enabled": False}, PaperControlledRuntimeOutcome.RUNTIME_DISABLED),
        (
            {"explicit_paper_authorization": False},
            PaperControlledRuntimeOutcome.PAPER_AUTHORIZATION_MISSING,
        ),
        ({"allowed_symbols": ()}, PaperControlledRuntimeOutcome.SYMBOL_ALLOWLIST_EMPTY),
    ),
)
def test_primary_startup_denials(changes, expected):
    assert evaluate_controlled_runtime_startup_gate(_paper(**changes)).outcome is expected


MATRIX = tuple(
    product(
        (ExecutionMode.OFF, ExecutionMode.PAPER, ExecutionMode.LIVE),
        (
            PaperControlledRuntimeAction.VALIDATE_CONFIGURATION,
            PaperControlledRuntimeAction.DRY_RUN_PLAN,
        ),
        (
            PaperControlledRuntimeTarget.CONFIGURATION_ONLY,
            PaperControlledRuntimeTarget.ISOLATED_POSTGRESQL,
            PaperControlledRuntimeTarget.PRODUCTION_READONLY_METADATA,
            PaperControlledRuntimeTarget.PRODUCTION_MUTATING,
        ),
        (False, True),
        (False, True),
    )
)


@pytest.mark.parametrize(
    ("mode", "action", "target", "runtime_enabled", "authorized"), MATRIX
)
def test_all_mode_action_target_enablement_authorization_combinations_are_deterministic(
    mode, action, target, runtime_enabled, authorized
):
    database_mode = (
        PaperDatabaseAccessMode.ISOLATED_READ_ONLY
        if target is PaperControlledRuntimeTarget.ISOLATED_POSTGRESQL
        else PaperDatabaseAccessMode.NONE
    )
    configuration = PaperControlledRuntimeConfiguration(
        runtime_action=action,
        target=target,
        execution_mode=mode,
        runtime_enabled=runtime_enabled,
        dry_run_enabled=True,
        explicit_paper_authorization=authorized,
        allowed_symbols=("BTCUSDT",),
        database_access_mode=database_mode,
    )
    first = evaluate_controlled_runtime_startup_gate(configuration)
    second = evaluate_controlled_runtime_startup_gate(configuration)
    assert first == second
    if mode is ExecutionMode.LIVE:
        assert first.outcome in {
            PaperControlledRuntimeOutcome.LIVE_FORBIDDEN,
            PaperControlledRuntimeOutcome.PRODUCTION_MUTATION_FORBIDDEN,
        }
    if target is PaperControlledRuntimeTarget.PRODUCTION_MUTATING:
        assert first.outcome is PaperControlledRuntimeOutcome.PRODUCTION_MUTATION_FORBIDDEN


@pytest.mark.parametrize("max_stages", (2, 3, 4))
def test_bounded_multistage_configuration_is_ready(max_stages):
    configuration = _paper(
        cycle_scope=PaperLifecycleCycleScope.ADVANCE_UNTIL_BLOCKED_WITHIN_REQUEST,
        max_stages_per_cycle=max_stages,
    )
    assert (
        evaluate_controlled_runtime_startup_gate(configuration).outcome
        is PaperControlledRuntimeOutcome.DRY_RUN_READY
    )


@pytest.mark.parametrize("max_stages", (2, 3, 4))
def test_one_step_scope_rejects_every_non_one_bound(max_stages):
    assert (
        evaluate_controlled_runtime_startup_gate(_paper(max_stages_per_cycle=max_stages)).outcome
        is PaperControlledRuntimeOutcome.INVALID_SCOPE
    )
