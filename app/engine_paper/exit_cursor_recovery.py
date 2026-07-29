"""Fresh-session bounded recovery for uncertain cursor commits."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy.orm import Session, sessionmaker

from app.db.paper_mappings import orm_values_to_paper_exit_cursor
from app.db.paper_models import PaperExitEvaluationCursorRecord
from app.engine_paper.exit_evaluation_cursor import PaperExitEvaluationCursor


class PaperExitCursorRecoveryOutcome(StrEnum):
    RESOLVED_COMMITTED = "RESOLVED_COMMITTED"
    RESOLVED_NOT_COMMITTED = "RESOLVED_NOT_COMMITTED"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True, slots=True)
class PaperExitCursorRecoveryResult:
    outcome: PaperExitCursorRecoveryOutcome
    cursor: PaperExitEvaluationCursor | None = None
    attempts_used: int = 0
    reason_code: str = "PAPER_EXIT_CURSOR_RECOVERY_OK"


def recover_uncertain_cursor_commit(
    session_factory: sessionmaker[Session] | Callable[[], Session],
    expected: PaperExitEvaluationCursor,
    *,
    attempts: int = 3,
) -> PaperExitCursorRecoveryResult:
    """Resolve commit state without reusing a failed Session or replaying writes."""

    if attempts < 1 or attempts > 3:
        raise ValueError("attempts must be between 1 and 3")
    for attempt in range(1, attempts + 1):
        try:
            with session_factory() as fresh_session:
                row = fresh_session.get(
                    PaperExitEvaluationCursorRecord, expected.cursor_id
                )
                found = orm_values_to_paper_exit_cursor(row) if row else None
        except Exception:
            if attempt == attempts:
                return PaperExitCursorRecoveryResult(
                    PaperExitCursorRecoveryOutcome.UNRESOLVED,
                    attempts_used=attempt,
                    reason_code="PAPER_EXIT_CURSOR_RECOVERY_LOOKUP_UNAVAILABLE",
                )
            continue
        if found is not None:
            if found == expected:
                return PaperExitCursorRecoveryResult(
                    PaperExitCursorRecoveryOutcome.RESOLVED_COMMITTED,
                    found,
                    attempt,
                )
            return PaperExitCursorRecoveryResult(
                PaperExitCursorRecoveryOutcome.IDEMPOTENCY_CONFLICT,
                found,
                attempt,
                "PAPER_EXIT_CURSOR_RECOVERY_CONFLICT",
            )
        if attempt == attempts:
            return PaperExitCursorRecoveryResult(
                PaperExitCursorRecoveryOutcome.RESOLVED_NOT_COMMITTED,
                attempts_used=attempt,
                reason_code="PAPER_EXIT_CURSOR_RECOVERY_ABSENT",
            )
    raise AssertionError("bounded cursor recovery loop exhausted")
