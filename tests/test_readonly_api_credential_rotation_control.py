from __future__ import annotations

import subprocess

import pytest

from scripts.readonly_api_credential_rotation_control import (
    ControlClassification,
    MutationState,
    classify_control_outcome,
    execute_controlled_operation,
    normalize_process_exit,
    render_safe_control_report,
)


class UnexpectedControlInterruption(BaseException):
    pass


def _classification(value: object) -> ControlClassification:
    return normalize_process_exit(value).classification


def test_normal_return_is_success() -> None:
    assert _classification(object()) is ControlClassification.SUCCESS


def test_none_return_is_success() -> None:
    assert _classification(None) is ControlClassification.SUCCESS


def test_return_code_zero_is_success() -> None:
    assert _classification(0) is ControlClassification.SUCCESS


def test_system_exit_zero_is_success() -> None:
    assert _classification(SystemExit(0)) is ControlClassification.SUCCESS


def test_system_exit_none_is_success() -> None:
    assert _classification(SystemExit(None)) is ControlClassification.SUCCESS


def test_system_exit_false_is_success() -> None:
    assert _classification(SystemExit(False)) is ControlClassification.SUCCESS


@pytest.mark.parametrize("code", (1, 2))
def test_system_exit_nonzero_integer_is_failure(code: int) -> None:
    outcome = normalize_process_exit(SystemExit(code))
    assert outcome.classification is ControlClassification.FAILURE
    assert outcome.exit_code == code


def test_system_exit_error_value_is_failure_without_rendering_value() -> None:
    outcome = normalize_process_exit(SystemExit("unsafe error value"))
    assert outcome.classification is ControlClassification.FAILURE
    assert outcome.exit_code == 1


def test_ordinary_exception_is_failure() -> None:
    outcome = classify_control_outcome(raised=RuntimeError("unsafe detail"))
    assert outcome.classification is ControlClassification.FAILURE


def test_unexpected_base_exception_is_hard_stop() -> None:
    outcome = classify_control_outcome(
        raised=UnexpectedControlInterruption("unsafe detail")
    )
    assert outcome.classification is ControlClassification.FAILURE_HARD_STOP
    assert outcome.exit_code == 2


@pytest.mark.parametrize(
    ("returncode", "expected"),
    (
        (0, ControlClassification.SUCCESS),
        (1, ControlClassification.FAILURE),
    ),
)
def test_subprocess_exit_classification(
    returncode: int,
    expected: ControlClassification,
) -> None:
    completed = subprocess.CompletedProcess(["safe-command"], returncode)
    assert _classification(completed) is expected


def test_success_after_mutation_never_rolls_back() -> None:
    rollback_calls = 0

    def operation(state: MutationState) -> None:
        state.started = True
        raise SystemExit(0)

    def rollback() -> None:
        nonlocal rollback_calls
        rollback_calls += 1

    execution = execute_controlled_operation(operation, rollback=rollback)
    assert execution.outcome.classification is ControlClassification.SUCCESS
    assert execution.rollback_calls == 0
    assert rollback_calls == 0


def test_post_mutation_failure_rolls_back_exactly_once() -> None:
    rollback_calls = 0

    def operation(state: MutationState) -> None:
        state.started = True
        raise SystemExit(1)

    def rollback() -> None:
        nonlocal rollback_calls
        rollback_calls += 1

    execution = execute_controlled_operation(operation, rollback=rollback)
    assert execution.outcome.classification is ControlClassification.FAILURE
    assert execution.rollback_calls == 1
    assert rollback_calls == 1


def test_pre_mutation_failure_does_not_roll_back() -> None:
    rollback_calls = 0

    def operation(_state: MutationState) -> None:
        raise RuntimeError("unsafe detail")

    def rollback() -> None:
        nonlocal rollback_calls
        rollback_calls += 1

    execution = execute_controlled_operation(operation, rollback=rollback)
    assert execution.outcome.classification is ControlClassification.FAILURE
    assert execution.rollback_calls == 0
    assert rollback_calls == 0


def test_rollback_failure_is_surfaced_as_hard_stop() -> None:
    def operation(state: MutationState) -> int:
        state.started = True
        return 1

    def rollback() -> None:
        raise RuntimeError("unsafe rollback detail")

    execution = execute_controlled_operation(operation, rollback=rollback)
    assert execution.outcome.classification is ControlClassification.FAILURE_HARD_STOP
    assert execution.outcome.exit_code == 2
    assert execution.rollback_calls == 1
    assert execution.rollback_succeeded is False


def test_finalizer_return_cannot_overwrite_success_or_trigger_rollback() -> None:
    rollback_calls = 0

    def operation(state: MutationState) -> int:
        state.started = True
        return 0

    def rollback() -> None:
        nonlocal rollback_calls
        rollback_calls += 1

    execution = execute_controlled_operation(
        operation,
        rollback=rollback,
        finalizer=lambda: 99,
    )
    assert execution.outcome.classification is ControlClassification.SUCCESS
    assert execution.rollback_calls == 0
    assert rollback_calls == 0
    assert execution.finalizer_succeeded is True


def test_successful_system_exit_finalizer_cannot_trigger_rollback() -> None:
    def operation(state: MutationState) -> int:
        state.started = True
        return 0

    def finalizer() -> None:
        raise SystemExit(0)

    execution = execute_controlled_operation(
        operation,
        rollback=lambda: pytest.fail("rollback must not run"),
        finalizer=finalizer,
    )
    assert execution.outcome.classification is ControlClassification.SUCCESS
    assert execution.rollback_calls == 0
    assert execution.finalizer_succeeded is True


def test_safe_report_excludes_secret_uri_exception_text_and_traceback() -> None:
    prohibited_value = "unsafe synthetic " + "credential"
    render_target = "postgresql" + "://" + "role:unsafe@database.example/app"

    def operation(state: MutationState) -> None:
        state.started = True
        raise RuntimeError(f"{prohibited_value} {render_target}")

    execution = execute_controlled_operation(
        operation,
        rollback=lambda: None,
    )
    rendered = render_safe_control_report(execution)
    for prohibited in (
        prohibited_value,
        render_target,
        "RuntimeError",
        "Traceback",
        "password",
        "fingerprint",
        "sha256",
    ):
        assert prohibited not in rendered
