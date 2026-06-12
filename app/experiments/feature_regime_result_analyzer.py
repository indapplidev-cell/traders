from __future__ import annotations

import json
from pathlib import Path
from typing import Any


FEATURE_REGIME_RESULT_ANALYZER_NAME = "feature_regime_result_analyzer"
FEATURE_REGIME_RESULT_ANALYZER_VERSION = "ml33"


class FeatureRegimeResultAnalyzer:
    """Compare a feature/regime experiment against an ML31-like baseline."""

    def analyze(
        self,
        *,
        current_result: dict[str, Any],
        baseline_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        current = dict(current_result)
        baseline = None if baseline_result is None else dict(baseline_result)
        if baseline is None:
            baseline = dict(current.get("baseline_reference", {})) or None

        current_best_score = self._float_or_none(current.get("best_candidate_score"))
        baseline_best_score = self._float_or_none(
            None if baseline is None else baseline.get("best_candidate_score")
        )
        score_delta = (
            None
            if current_best_score is None or baseline_best_score is None
            else round(current_best_score - baseline_best_score, 6)
        )
        collapse_gate_failures = self._failed_gate_count(current, "collapse_gate")
        baseline_edge_failures = self._failed_gate_count(current, "baseline_edge_gate")
        walk_forward_failures = self._failed_gate_count(current, "walk_forward_gate")
        profit_aware_failures = self._failed_gate_count(current, "profit_aware_gate")
        feature_weak_signal_detected = bool(
            dict(current.get("feature_quality_summary", {})).get("weak_signal_detected", False)
        )
        regime_data_available = bool(
            dict(current.get("regime_feature_summary", {})).get("regime_data_available", False)
        )
        regime_training_applied = bool(current.get("regime_training_applied", False))
        overall_status = self._overall_status(
            score_delta=score_delta,
            accepted_candidate_count=int(current.get("accepted_candidate_count", 0) or 0),
            baseline_available=baseline is not None,
        )
        return {
            "analyzer_name": FEATURE_REGIME_RESULT_ANALYZER_NAME,
            "analyzer_version": FEATURE_REGIME_RESULT_ANALYZER_VERSION,
            "current_experiment_id": current.get("experiment_id"),
            "baseline_experiment_id": None if baseline is None else baseline.get("experiment_id"),
            "current_best_candidate_score": current_best_score,
            "baseline_best_candidate_score": baseline_best_score,
            "score_delta": score_delta,
            "accepted_candidate_count": int(current.get("accepted_candidate_count", 0) or 0),
            "collapse_gate_failures": collapse_gate_failures,
            "baseline_edge_failures": baseline_edge_failures,
            "walk_forward_failures": walk_forward_failures,
            "profit_aware_failures": profit_aware_failures,
            "feature_weak_signal_detected": feature_weak_signal_detected,
            "regime_data_available": regime_data_available,
            "regime_training_applied": regime_training_applied,
            "overall_status": overall_status,
            "recommendations": self._recommendations(
                overall_status=overall_status,
                feature_weak_signal_detected=feature_weak_signal_detected,
                regime_training_applied=regime_training_applied,
            ),
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "orders_enabled": False,
            "traders_core_connected": False,
        }

    @staticmethod
    def load_summary(experiment_dir: str | Path) -> dict[str, Any]:
        path = Path(experiment_dir) / "feature_regime_experiment_summary.json"
        if not path.exists():
            raise ValueError(f"feature/regime experiment summary not found: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def latest_experiment_dir(root_dir: str | Path = Path("reports/feature_regime_experiments")) -> Path:
        root = Path(root_dir)
        if not root.exists():
            raise ValueError("reports/feature_regime_experiments is missing; run feature-regime-experiment-run first.")
        directories = [item for item in root.iterdir() if item.is_dir()]
        if not directories:
            raise ValueError("reports/feature_regime_experiments is empty; run feature-regime-experiment-run first.")
        return max(directories, key=lambda item: item.stat().st_mtime)

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        return None if value is None else float(value)

    @staticmethod
    def _failed_gate_count(current: dict[str, Any], gate_name: str) -> int:
        return int(dict(current.get("failed_gates_summary", {})).get(gate_name, 0) or 0)

    @staticmethod
    def _overall_status(
        *,
        score_delta: float | None,
        accepted_candidate_count: int,
        baseline_available: bool,
    ) -> str:
        if not baseline_available:
            return "INSUFFICIENT_DATA"
        if accepted_candidate_count > 0 or (score_delta is not None and score_delta >= 0.75):
            return "FEATURE_REGIME_IMPROVED"
        if score_delta is not None and score_delta > 0:
            return "FEATURE_REGIME_PARTIAL"
        if score_delta is not None and score_delta < 0:
            return "FEATURE_REGIME_DEGRADED"
        return "FEATURE_REGIME_NO_IMPROVEMENT"

    @staticmethod
    def _recommendations(
        *,
        overall_status: str,
        feature_weak_signal_detected: bool,
        regime_training_applied: bool,
    ) -> list[str]:
        recommendations: list[str] = []
        if overall_status == "INSUFFICIENT_DATA":
            recommendations.append("Baseline comparison is unavailable; keep this run as diagnostics-first evidence only.")
        if overall_status in {"FEATURE_REGIME_NO_IMPROVEMENT", "FEATURE_REGIME_DEGRADED"}:
            recommendations.append("Move ML34 toward actual feature builder additions and regime integration.")
        if overall_status in {"FEATURE_REGIME_IMPROVED", "FEATURE_REGIME_PARTIAL"}:
            recommendations.append("Validate the best feature/regime candidate on more symbols and timeframes in ML34.")
        if feature_weak_signal_detected:
            recommendations.append("Weak feature signal is still present; prioritize feature engineering before scale-up.")
        if not regime_training_applied:
            recommendations.append("Real regime-specific training is not yet wired into the label builder; keep the result degraded.")
        recommendations.append("Keep traders-core, live trading, orders, and auto activation disabled.")
        return list(dict.fromkeys(recommendations))
