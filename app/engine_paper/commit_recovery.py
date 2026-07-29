"""Bounded uncertain-COMMIT resolution using a fresh clean Session."""

from __future__ import annotations

from collections.abc import Callable
from time import sleep
from typing import TypeVar

from sqlalchemy.orm import Session, sessionmaker

from app.engine_paper.repository_results import RepositoryOutcome, RepositoryResult, result


T = TypeVar("T")


def recover_uncertain_commit(
    session_factory: sessionmaker[Session] | Callable[[], Session],
    lookup: Callable[[Session], T | None],
    expected: T,
    semantic_equal: Callable[[T, T], bool],
    *,
    attempts: int = 3,
    backoff_seconds: tuple[float, ...] = (0.0, 0.01, 0.02),
) -> RepositoryResult[T]:
    if attempts < 1 or attempts > 3:
        raise ValueError("attempts must be between 1 and 3")
    for attempt in range(attempts):
        try:
            with session_factory() as fresh_session:
                found = lookup(fresh_session)
        except Exception:
            if attempt + 1 == attempts:
                return result(
                    RepositoryOutcome.UNCERTAIN_COMMIT_UNRESOLVED,
                    reason_code="PAPER_DB_UNCERTAIN_COMMIT_LOOKUP_UNAVAILABLE",
                )
        else:
            if found is not None:
                if semantic_equal(found, expected):
                    return result(
                        RepositoryOutcome.UNCERTAIN_COMMIT_RESOLVED_COMMITTED,
                        found,
                        reason_code="PAPER_DB_UNCERTAIN_COMMIT_MATCH",
                    )
                return result(
                    RepositoryOutcome.IDEMPOTENCY_CONFLICT,
                    found,
                    reason_code="PAPER_IDEMPOTENCY_IDENTITY_COLLISION",
                )
            if attempt + 1 == attempts:
                return result(
                    RepositoryOutcome.UNCERTAIN_COMMIT_RESOLVED_NOT_COMMITTED,
                    reason_code="PAPER_DB_UNCERTAIN_COMMIT_ABSENT",
                )
        delay = backoff_seconds[min(attempt, len(backoff_seconds) - 1)]
        if delay > 0:
            sleep(delay)
    raise AssertionError("bounded recovery loop exhausted")
