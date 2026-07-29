"""Immutable PAPER journal event contracts; no event bus or persistence."""

from app.engine_journal.paper_events import PaperDomainEvent

__all__ = ["PaperDomainEvent"]
