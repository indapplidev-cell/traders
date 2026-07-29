"""Stable, sanitized outcomes for the PAPER persistence boundary."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Generic, TypeVar


class RepositoryOutcome(StrEnum):
    CREATED = "CREATED"
    EXISTING_IDEMPOTENT = "EXISTING_IDEMPOTENT"
    UPDATED = "UPDATED"
    NOT_FOUND = "NOT_FOUND"
    STALE_VERSION = "STALE_VERSION"
    INVALID_STATE = "INVALID_STATE"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    ACTIVE_POSITION_CONFLICT = "ACTIVE_POSITION_CONFLICT"
    CONSTRAINT_VIOLATION = "CONSTRAINT_VIOLATION"
    TRANSIENT_DB_FAILURE = "TRANSIENT_DB_FAILURE"
    UNCERTAIN_COMMIT_RESOLVED_COMMITTED = "UNCERTAIN_COMMIT_RESOLVED_COMMITTED"
    UNCERTAIN_COMMIT_RESOLVED_NOT_COMMITTED = "UNCERTAIN_COMMIT_RESOLVED_NOT_COMMITTED"
    UNCERTAIN_COMMIT_UNRESOLVED = "UNCERTAIN_COMMIT_UNRESOLVED"
    INTERNAL_INVARIANT_FAILURE = "INTERNAL_INVARIANT_FAILURE"


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class RepositoryResult(Generic[T]):
    outcome: RepositoryOutcome
    value: T | None = None
    reason_code: str = "PAPER_REPOSITORY_OK"
    message: str = "repository operation completed"

    @property
    def successful(self) -> bool:
        return self.outcome in {
            RepositoryOutcome.CREATED,
            RepositoryOutcome.EXISTING_IDEMPOTENT,
            RepositoryOutcome.UPDATED,
            RepositoryOutcome.UNCERTAIN_COMMIT_RESOLVED_COMMITTED,
            RepositoryOutcome.UNCERTAIN_COMMIT_RESOLVED_NOT_COMMITTED,
        }


def result(
    outcome: RepositoryOutcome,
    value: T | None = None,
    *,
    reason_code: str | None = None,
    message: str | None = None,
) -> RepositoryResult[T]:
    """Create a bounded result without incorporating exception text."""
    code = reason_code or f"PAPER_REPOSITORY_{outcome.value}"
    safe_message = (message or outcome.value.lower().replace("_", " "))[:160]
    return RepositoryResult(outcome, value, code[:96], safe_message)
