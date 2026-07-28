"""Deterministic control semantics for the readonly credential rotation.

The controller never renders exception values.  In particular, ``SystemExit``
is normalized by its code before rollback is considered.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ControlClassification(StrEnum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    FAILURE_HARD_STOP = "FAILURE_HARD_STOP"


@dataclass
class MutationState:
    started: bool = False


@dataclass(frozen=True)
class ControlOutcome:
    classification: ControlClassification
    exit_code: int


@dataclass(frozen=True)
class ControlExecution:
    outcome: ControlOutcome
    mutation_started: bool
    rollback_calls: int
    rollback_succeeded: bool | None
    finalizer_succeeded: bool | None

    def safe_report(self) -> dict[str, str | int]:
        return {
            "classification": self.outcome.classification.value,
            "exit_code": self.outcome.exit_code,
            "mutation_started": "YES" if self.mutation_started else "NO",
            "rollback_calls": self.rollback_calls,
            "rollback_succeeded": (
                "NOT_RUN"
                if self.rollback_succeeded is None
                else ("YES" if self.rollback_succeeded else "NO")
            ),
            "finalizer_succeeded": (
                "NOT_RUN"
                if self.finalizer_succeeded is None
                else ("YES" if self.finalizer_succeeded else "NO")
            ),
        }


def _exit_code_outcome(code: object) -> ControlOutcome:
    if code is None or code is False or code == 0:
        return ControlOutcome(ControlClassification.SUCCESS, 0)
    if isinstance(code, int):
        return ControlOutcome(ControlClassification.FAILURE, code)
    return ControlOutcome(ControlClassification.FAILURE, 1)


def normalize_process_exit(value: object = None) -> ControlOutcome:
    """Normalize return values, ``SystemExit``, and subprocess results."""

    if isinstance(value, SystemExit):
        return _exit_code_outcome(value.code)
    if isinstance(value, subprocess.CompletedProcess):
        return _exit_code_outcome(value.returncode)
    if value is None or value is False:
        return ControlOutcome(ControlClassification.SUCCESS, 0)
    if isinstance(value, int):
        return _exit_code_outcome(value)
    return ControlOutcome(ControlClassification.SUCCESS, 0)


def classify_control_outcome(
    *,
    returned: object = None,
    raised: BaseException | None = None,
) -> ControlOutcome:
    if raised is None:
        return normalize_process_exit(returned)
    if isinstance(raised, SystemExit):
        return normalize_process_exit(raised)
    if isinstance(raised, Exception):
        return ControlOutcome(ControlClassification.FAILURE, 1)
    return ControlOutcome(ControlClassification.FAILURE_HARD_STOP, 2)


def should_rollback(outcome: ControlOutcome, mutation_started: bool) -> bool:
    return (
        mutation_started
        and outcome.classification is not ControlClassification.SUCCESS
    )


def execute_controlled_operation(
    operation: Callable[[MutationState], Any],
    *,
    rollback: Callable[[], Any],
    finalizer: Callable[[], Any] | None = None,
) -> ControlExecution:
    """Execute once, rolling back exactly once only for a real failure."""

    state = MutationState()
    try:
        returned = operation(state)
    except SystemExit as raised:
        outcome = classify_control_outcome(raised=raised)
    except Exception as raised:
        outcome = classify_control_outcome(raised=raised)
    except BaseException as raised:
        outcome = classify_control_outcome(raised=raised)
    else:
        outcome = classify_control_outcome(returned=returned)

    rollback_calls = 0
    rollback_succeeded: bool | None = None
    if should_rollback(outcome, state.started):
        rollback_calls = 1
        try:
            rollback()
        except BaseException:
            rollback_succeeded = False
            outcome = ControlOutcome(
                ControlClassification.FAILURE_HARD_STOP,
                2,
            )
        else:
            rollback_succeeded = True

    finalizer_succeeded: bool | None = None
    if finalizer is not None:
        try:
            finalizer_result = finalizer()
        except SystemExit as raised:
            finalizer_outcome = normalize_process_exit(raised)
            finalizer_succeeded = (
                finalizer_outcome.classification
                is ControlClassification.SUCCESS
            )
        except BaseException:
            finalizer_succeeded = False
        else:
            # A finalizer return value is cleanup metadata, not process status.
            del finalizer_result
            finalizer_succeeded = True

        if finalizer_succeeded is False:
            outcome = ControlOutcome(
                ControlClassification.FAILURE_HARD_STOP,
                2,
            )

    return ControlExecution(
        outcome=outcome,
        mutation_started=state.started,
        rollback_calls=rollback_calls,
        rollback_succeeded=rollback_succeeded,
        finalizer_succeeded=finalizer_succeeded,
    )


def render_safe_control_report(execution: ControlExecution) -> str:
    return "\n".join(
        f"{key}={value}" for key, value in execution.safe_report().items()
    )


__all__ = [
    "ControlClassification",
    "ControlExecution",
    "ControlOutcome",
    "MutationState",
    "classify_control_outcome",
    "execute_controlled_operation",
    "normalize_process_exit",
    "render_safe_control_report",
    "should_rollback",
]
