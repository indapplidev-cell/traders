"""DB-independent interfaces exposed by the PAPER repository boundary."""

from __future__ import annotations

from typing import Protocol

from app.engine_execution.paper_models import PaperExecutionCommand, PaperOrder
from app.engine_journal.paper_events import PaperDomainEvent
from app.engine_paper.repositories import PaperCommandGraph
from app.engine_paper.repository_results import RepositoryResult


class CommandRepositoryProtocol(Protocol):
    def create_or_get_command(
        self, command: PaperExecutionCommand
    ) -> RepositoryResult[PaperExecutionCommand]: ...

    def get_command(self, command_id: str) -> PaperExecutionCommand | None: ...

    def get_command_by_idempotency_key(
        self, key: str
    ) -> PaperExecutionCommand | None: ...

    def get_command_graph(
        self, command_id: str, *, limit: int = 100
    ) -> RepositoryResult[PaperCommandGraph]: ...


class OrderRepositoryProtocol(Protocol):
    def get_order(self, order_id: str) -> PaperOrder | None: ...

    def get_order_by_idempotency_key(self, key: str) -> PaperOrder | None: ...


class JournalRepositoryProtocol(Protocol):
    def append_or_get_journal_entry(
        self, entry: PaperDomainEvent, **links: str | None
    ) -> RepositoryResult[PaperDomainEvent]: ...

    def list_journal_for_aggregate(
        self, aggregate_type: str, aggregate_id: str, *, limit: int = 100
    ) -> RepositoryResult[tuple[PaperDomainEvent, ...]]: ...
