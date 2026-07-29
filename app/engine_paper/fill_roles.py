"""Shared immutable role vocabulary for PAPER fills."""

from enum import StrEnum


class PaperFillRole(StrEnum):
    ENTRY = "ENTRY"
    CLOSE = "CLOSE"

    @property
    def persistence_role(self) -> str:
        return "ENTRY" if self is PaperFillRole.ENTRY else "EXIT"
