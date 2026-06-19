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
    "DecisionPolicyConfig",
    "DecisionPolicyGrid",
    "DecisionPolicyResult",
    "PredictionRootCauseAuditor",
    "RootCauseThresholds",
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

    if name in {"DecisionPolicyConfig", "DecisionPolicyGrid", "DecisionPolicyResult"}:
        from app.diagnostics.decision_policy_grid import (
            DecisionPolicyConfig,
            DecisionPolicyGrid,
            DecisionPolicyResult,
        )

        return {
            "DecisionPolicyConfig": DecisionPolicyConfig,
            "DecisionPolicyGrid": DecisionPolicyGrid,
            "DecisionPolicyResult": DecisionPolicyResult,
        }[name]

    if name in {"PredictionRootCauseAuditor", "RootCauseThresholds"}:
        from app.diagnostics.prediction_root_cause_audit import (
            PredictionRootCauseAuditor,
            RootCauseThresholds,
        )

        return {
            "PredictionRootCauseAuditor": PredictionRootCauseAuditor,
            "RootCauseThresholds": RootCauseThresholds,
        }[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
