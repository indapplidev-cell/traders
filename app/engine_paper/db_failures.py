"""PostgreSQL failure normalization using structured SQLSTATE/constraint data."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.exc import DBAPIError, IntegrityError

from app.engine_paper.repository_results import RepositoryOutcome


@dataclass(frozen=True, slots=True)
class ClassifiedDatabaseFailure:
    outcome: RepositoryOutcome
    reason_code: str
    retryable: bool


_TRANSIENT = {"40001", "40P01", "57014", "08000", "08001", "08003", "08004", "08006", "08007", "08P01"}
_CONSTRAINT_OUTCOMES = {
    "uq_paper_positions_active_mode_symbol": RepositoryOutcome.ACTIVE_POSITION_CONFLICT,
}


def _structured(exception: BaseException, name: str) -> str | None:
    current: BaseException | None = exception
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        value = getattr(current, name, None)
        if value:
            return str(value)
        diagnostic = getattr(current, "diag", None)
        if diagnostic is not None:
            value = getattr(diagnostic, name, None)
            if value:
                return str(value)
        current = current.__cause__ or current.__context__
    return None


def sqlstate(exception: BaseException) -> str | None:
    return _structured(exception, "sqlstate") or _structured(exception, "pgcode")


def constraint_name(exception: BaseException) -> str | None:
    return _structured(exception, "constraint_name")


def classify_database_failure(exception: BaseException) -> ClassifiedDatabaseFailure:
    state = sqlstate(exception)
    constraint = constraint_name(exception)
    if constraint in _CONSTRAINT_OUTCOMES:
        return ClassifiedDatabaseFailure(
            _CONSTRAINT_OUTCOMES[constraint],
            "PAPER_DB_ACTIVE_POSITION_CONFLICT",
            False,
        )
    if state in _TRANSIENT:
        suffix = {
            "40001": "SERIALIZATION_FAILURE",
            "40P01": "DEADLOCK_DETECTED",
            "57014": "STATEMENT_TIMEOUT",
        }.get(state, "CONNECTION_FAILURE")
        return ClassifiedDatabaseFailure(
            RepositoryOutcome.TRANSIENT_DB_FAILURE,
            f"PAPER_DB_{suffix}",
            True,
        )
    if state == "23505":
        return ClassifiedDatabaseFailure(
            RepositoryOutcome.IDEMPOTENCY_CONFLICT,
            "PAPER_DB_UNIQUE_VIOLATION",
            False,
        )
    if state in {"23503", "23514", "23502", "22003"}:
        suffix = {
            "23503": "FOREIGN_KEY_VIOLATION",
            "23514": "CHECK_VIOLATION",
            "23502": "NOT_NULL_VIOLATION",
            "22003": "NUMERIC_RANGE_VIOLATION",
        }[state]
        return ClassifiedDatabaseFailure(
            RepositoryOutcome.CONSTRAINT_VIOLATION,
            f"PAPER_DB_{suffix}",
            False,
        )
    if isinstance(exception, IntegrityError):
        return ClassifiedDatabaseFailure(
            RepositoryOutcome.CONSTRAINT_VIOLATION,
            "PAPER_DB_CONSTRAINT_VIOLATION",
            False,
        )
    if isinstance(exception, DBAPIError) and exception.connection_invalidated:
        return ClassifiedDatabaseFailure(
            RepositoryOutcome.TRANSIENT_DB_FAILURE,
            "PAPER_DB_CONNECTION_FAILURE",
            True,
        )
    return ClassifiedDatabaseFailure(
        RepositoryOutcome.INTERNAL_INVARIANT_FAILURE,
        "PAPER_DB_UNEXPECTED",
        False,
    )
