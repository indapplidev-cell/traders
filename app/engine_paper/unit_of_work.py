"""Single-owner transaction boundary for PAPER repositories."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import DBAPIError

from app.db.session import get_session_factory
from app.engine_paper.db_failures import classify_database_failure
from app.engine_paper.repository_results import RepositoryOutcome, RepositoryResult, result


class PaperUnitOfWork:
    """Own exactly one Session and one explicit outer transaction."""

    def __init__(
        self,
        session_factory: sessionmaker[Session] | Callable[[], Session] | None = None,
    ) -> None:
        self._factory = session_factory or get_session_factory()
        self.session: Session | None = None
        self._transaction = None
        self._committed = False
        self._entered = False
        self.repositories = None

    def __enter__(self) -> "PaperUnitOfWork":
        if self._entered:
            raise RuntimeError("PAPER_UOW_NESTED_MISUSE")
        self._entered = True
        self.session = self._factory()
        self._transaction = self.session.begin()
        from app.engine_paper.repositories import PaperRepositories
        self.repositories = PaperRepositories(self.session)
        return self

    def commit(self) -> RepositoryResult[None]:
        if not self._entered or self.session is None or self._transaction is None:
            raise RuntimeError("PAPER_UOW_NOT_ENTERED")
        if self._committed:
            raise RuntimeError("PAPER_UOW_ALREADY_COMMITTED")
        try:
            self._transaction.commit()
        except Exception as exception:
            failure = classify_database_failure(exception)
            if self.session.is_active:
                self.session.rollback()
            if isinstance(exception, DBAPIError) and exception.connection_invalidated:
                return result(
                    RepositoryOutcome.UNCERTAIN_COMMIT_UNRESOLVED,
                    reason_code="PAPER_DB_COMMIT_OUTCOME_UNKNOWN",
                )
            return result(failure.outcome, reason_code=failure.reason_code)
        self._committed = True
        return result(RepositoryOutcome.UPDATED, message="transaction committed")

    def rollback(self) -> None:
        if self.session is not None and self.session.is_active:
            self.session.rollback()

    def __exit__(self, exc_type, exc, traceback) -> None:
        assert self.session is not None
        try:
            if exc_type is not None or not self._committed:
                self.rollback()
        finally:
            self.session.close()
            self._entered = False
