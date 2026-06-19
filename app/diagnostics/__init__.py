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
    "BookDrivenForensicAudit",
    "FeatureClassStats",
    "FeatureLabelSeparabilityAudit",
    "LabelAmbiguityAudit",
    "SchwagerNegativeResultAnalyzer",
    "SchwagerRobustnessDecisionBoard",
    "SetupContextAudit",
    "DecisionCalibrationConfig",
    "evaluate_class_margin_objective_decision",
    "load_latest_class_margin_runtime_evidence",
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

    if name in {"BookDrivenForensicAudit"}:
        from app.diagnostics.book_driven_forensic_audit import BookDrivenForensicAudit

        return {"BookDrivenForensicAudit": BookDrivenForensicAudit}[name]

    if name in {
        "evaluate_class_margin_objective_decision",
        "load_latest_class_margin_runtime_evidence",
    }:
        from app.diagnostics.class_margin_objective_decision import (
            evaluate_class_margin_objective_decision,
            load_latest_class_margin_runtime_evidence,
        )

        return {
            "evaluate_class_margin_objective_decision": evaluate_class_margin_objective_decision,
            "load_latest_class_margin_runtime_evidence": load_latest_class_margin_runtime_evidence,
        }[name]

    if name in {"FeatureClassStats", "FeatureLabelSeparabilityAudit"}:
        from app.diagnostics.feature_label_separability_audit import (
            FeatureClassStats,
            FeatureLabelSeparabilityAudit,
        )

        return {
            "FeatureClassStats": FeatureClassStats,
            "FeatureLabelSeparabilityAudit": FeatureLabelSeparabilityAudit,
        }[name]

    if name in {"LabelAmbiguityAudit"}:
        from app.diagnostics.label_ambiguity_audit import LabelAmbiguityAudit

        return {"LabelAmbiguityAudit": LabelAmbiguityAudit}[name]

    if name in {"SchwagerNegativeResultAnalyzer"}:
        from app.diagnostics.schwager_negative_result_analyzer import SchwagerNegativeResultAnalyzer

        return {"SchwagerNegativeResultAnalyzer": SchwagerNegativeResultAnalyzer}[name]

    if name in {"SchwagerRobustnessDecisionBoard"}:
        from app.diagnostics.schwager_robustness_decision_board import SchwagerRobustnessDecisionBoard

        return {"SchwagerRobustnessDecisionBoard": SchwagerRobustnessDecisionBoard}[name]

    if name in {"SetupContextAudit"}:
        from app.diagnostics.setup_context_audit import SetupContextAudit

        return {"SetupContextAudit": SetupContextAudit}[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
