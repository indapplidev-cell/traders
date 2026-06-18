from __future__ import annotations

from typing import Any

__all__ = [
    "DiagnosticsService",
    "AntiCollapseDiagnostics",
    "AntiCollapseDiagnosticsResult",
    "BaselineEdgeDiagnostics",
    "BaselineEdgeDiagnosticsResult",
    "CalibratedPredictionDecisions",
    "DecisionCalibrationConfig",
]


def __getattr__(name: str) -> Any:
    if name == "DiagnosticsService":
        from app.diagnostics.diagnostics_service import DiagnosticsService

        return DiagnosticsService

    if name in {"AntiCollapseDiagnostics", "AntiCollapseDiagnosticsResult"}:
        from app.diagnostics.anti_collapse_diagnostics import (
            AntiCollapseDiagnostics,
            AntiCollapseDiagnosticsResult,
        )

        return {
            "AntiCollapseDiagnostics": AntiCollapseDiagnostics,
            "AntiCollapseDiagnosticsResult": AntiCollapseDiagnosticsResult,
        }[name]

    if name in {"BaselineEdgeDiagnostics", "BaselineEdgeDiagnosticsResult"}:
        from app.diagnostics.baseline_edge_diagnostics import (
            BaselineEdgeDiagnostics,
            BaselineEdgeDiagnosticsResult,
        )

        return {
            "BaselineEdgeDiagnostics": BaselineEdgeDiagnostics,
            "BaselineEdgeDiagnosticsResult": BaselineEdgeDiagnosticsResult,
        }[name]

    if name in {"CalibratedPredictionDecisions", "DecisionCalibrationConfig"}:
        from app.diagnostics.calibrated_prediction_decisions import (
            CalibratedPredictionDecisions,
            DecisionCalibrationConfig,
        )

        return {
            "CalibratedPredictionDecisions": CalibratedPredictionDecisions,
            "DecisionCalibrationConfig": DecisionCalibrationConfig,
        }[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
