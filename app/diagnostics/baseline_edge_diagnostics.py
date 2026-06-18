from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class BaselineEdgeDiagnosticsResult:
    diagnostic_name: str
    diagnostic_version: str
    symbol: str | None
    config_id: str | None
    accuracy: float | None
    baseline_accuracy: float | None
    baseline_edge: float | None
    baseline_edge_status: str
    baseline_edge_gate_failed: bool
    baseline_edge_gate_min: float
    recommendations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BaselineEdgeDiagnostics:
    """Diagnostics for model accuracy versus baseline accuracy.

    This does not accept a model by itself. It only classifies whether the
    candidate has measurable edge over the baseline. Final acceptance must
    still depend on all gates: gap, baseline, collapse, profit-aware,
    walk-forward and safety gates.
    """

    diagnostic_version = "ml38_9_2"

    def evaluate(
        self,
        *,
        accuracy: float | None,
        baseline_accuracy: float | None,
        symbol: str | None = None,
        config_id: str | None = None,
        min_positive_edge: float = 0.0,
        min_strong_edge: float = 0.02,
    ) -> BaselineEdgeDiagnosticsResult:
        edge = self._safe_edge(accuracy, baseline_accuracy)
        status = self._status(edge, min_positive_edge, min_strong_edge)
        failed = status in {"UNKNOWN", "NEGATIVE_EDGE", "NO_EDGE"}
        recommendations = self._recommendations(status, edge)

        return BaselineEdgeDiagnosticsResult(
            diagnostic_name="baseline_edge_diagnostics",
            diagnostic_version=self.diagnostic_version,
            symbol=symbol,
            config_id=config_id,
            accuracy=accuracy,
            baseline_accuracy=baseline_accuracy,
            baseline_edge=edge,
            baseline_edge_status=status,
            baseline_edge_gate_failed=failed,
            baseline_edge_gate_min=min_positive_edge,
            recommendations=recommendations,
        )

    @staticmethod
    def _safe_edge(accuracy: float | None, baseline_accuracy: float | None) -> float | None:
        if accuracy is None or baseline_accuracy is None:
            return None
        try:
            return float(accuracy) - float(baseline_accuracy)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _status(edge: float | None, min_positive_edge: float, min_strong_edge: float) -> str:
        if edge is None:
            return "UNKNOWN"
        if edge < 0:
            return "NEGATIVE_EDGE"
        if edge <= min_positive_edge:
            return "NO_EDGE"
        if edge >= min_strong_edge:
            return "STRONG_EDGE"
        return "WEAK_EDGE"

    @staticmethod
    def _recommendations(status: str, edge: float | None) -> list[str]:
        if status == "UNKNOWN":
            return ["Baseline edge is unknown; inspect baseline comparison outputs."]
        if status == "NEGATIVE_EDGE":
            return [
                "Model is below baseline; improve label/objective before wider runtime.",
                "Inspect class distribution and confidence/profit-aware thresholds.",
            ]
        if status == "NO_EDGE":
            return [
                "Model is not above baseline; do not run full 3-symbol validation yet.",
                "Try baseline-edge-aware configs or stricter candidate filtering.",
            ]
        if status == "WEAK_EDGE":
            return [
                "Weak positive baseline edge; keep candidate rejected unless other gates are strong.",
                "Validate with walk-forward before considering wider runs.",
            ]
        return ["Positive baseline edge detected; continue gate-based validation."]


def extract_baseline_edge_fields(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Small helper for rankers/analyzers that receive dict-like candidates."""
    accuracy = payload.get("accuracy", payload.get("model_accuracy"))
    baseline_accuracy = payload.get("baseline_accuracy", payload.get("best_baseline_accuracy"))
    diagnostics = BaselineEdgeDiagnostics().evaluate(
        accuracy=accuracy,
        baseline_accuracy=baseline_accuracy,
        symbol=payload.get("symbol"),
        config_id=payload.get("config_id", payload.get("candidate_id")),
    )
    return diagnostics.to_dict()
