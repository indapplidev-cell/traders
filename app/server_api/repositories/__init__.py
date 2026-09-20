"""Repository exports without importing concrete adapters eagerly."""

from __future__ import annotations

from typing import Any

__all__ = ["ApiRepositories", "SemanticIncidentReadAdapter", "SqlAlchemyReadAdapter"]


def __getattr__(name: str) -> Any:
    if name == "ApiRepositories":
        from .protocols import ApiRepositories

        return ApiRepositories
    if name == "SemanticIncidentReadAdapter":
        from .semantic_incidents import SemanticIncidentReadAdapter

        return SemanticIncidentReadAdapter
    if name == "SqlAlchemyReadAdapter":
        from .sqlalchemy_read import SqlAlchemyReadAdapter

        return SqlAlchemyReadAdapter
    raise AttributeError(name)
