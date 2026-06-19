from __future__ import annotations

from typing import Any

__all__ = [
    "DiagnosticsService",
    "AntiCollapseDiagnostics",
    "AntiCollapseDiagnosticsResult",
    "BaselineEdgeDiagnostics",
    "BaselineEdgeDiagnosticsResult",
    "BoundedDecisionCalibrationConfig",
    "CalibratedPredictionDecisions",
    "DecisionCalibrationConfig",
    "choose_bounded_calibrated_decisions",
    "evaluate_decision_distribution",
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

    if name in {
        "BoundedDecisionCalibrationConfig",
        "CalibratedPredictionDecisions",
        "DecisionCalibrationConfig",
        "choose_bounded_calibrated_decisions",
        "evaluate_decision_distribution",
    }:
        from app.diagnostics.calibrated_prediction_decisions import (
            BoundedDecisionCalibrationConfig,
            CalibratedPredictionDecisions,
            DecisionCalibrationConfig,
            choose_bounded_calibrated_decisions,
            evaluate_decision_distribution,
        )

        return {
            "BoundedDecisionCalibrationConfig": BoundedDecisionCalibrationConfig,
            "CalibratedPredictionDecisions": CalibratedPredictionDecisions,
            "DecisionCalibrationConfig": DecisionCalibrationConfig,
            "choose_bounded_calibrated_decisions": choose_bounded_calibrated_decisions,
            "evaluate_decision_distribution": evaluate_decision_distribution,
        }[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
