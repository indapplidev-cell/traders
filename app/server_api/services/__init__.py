"""Service exports without eager cross-package imports."""

from __future__ import annotations

from typing import Any

__all__ = ["ApiQueryService", "PaperReadonlyReportingService", "PaperRuntimeObservation"]


def __getattr__(name: str) -> Any:
    if name == "ApiQueryService":
        from .query_service import ApiQueryService

        return ApiQueryService
    if name in {"PaperReadonlyReportingService", "PaperRuntimeObservation"}:
        from .paper_reporting import PaperReadonlyReportingService, PaperRuntimeObservation

        return {
            "PaperReadonlyReportingService": PaperReadonlyReportingService,
            "PaperRuntimeObservation": PaperRuntimeObservation,
        }[name]
    raise AttributeError(name)
