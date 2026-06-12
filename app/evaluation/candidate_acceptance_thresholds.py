from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class CandidateAcceptanceThresholds:
    min_accuracy_edge: float = 0.005
    max_predicted_class_share: float = 0.70
    min_down_prediction_share: float = 0.15
    min_profit_factor: float = 1.05
    min_profit_total_r: float = 0.0
    min_walk_forward_profit_factor: float = 1.02
    min_walk_forward_total_r: float = 0.0
    max_allowed_gap_severity: str = "MODERATE"

    def to_dict(self) -> dict[str, Any]:
        return {
            "min_accuracy_edge": self.min_accuracy_edge,
            "max_predicted_class_share": self.max_predicted_class_share,
            "min_down_prediction_share": self.min_down_prediction_share,
            "min_profit_factor": self.min_profit_factor,
            "min_profit_total_r": self.min_profit_total_r,
            "min_walk_forward_profit_factor": self.min_walk_forward_profit_factor,
            "min_walk_forward_total_r": self.min_walk_forward_total_r,
            "max_allowed_gap_severity": self.max_allowed_gap_severity,
        }

    def gap_severity_allowed(self, gap_severity: str | None) -> bool:
        current = self._gap_rank(gap_severity or "OK")
        allowed = self._gap_rank(self.max_allowed_gap_severity)
        return current <= allowed

    @staticmethod
    def _gap_rank(gap_severity: str) -> int:
        normalized = str(gap_severity).upper()
        mapping = {
            "OK": 0,
            "LOW": 1,
            "MINOR": 1,
            "MODERATE": 2,
            "HIGH": 3,
            "CRITICAL": 4,
        }
        return mapping.get(normalized, 99)


def default_candidate_acceptance_thresholds() -> CandidateAcceptanceThresholds:
    return CandidateAcceptanceThresholds()
