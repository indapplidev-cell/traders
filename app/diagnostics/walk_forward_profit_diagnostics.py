from __future__ import annotations

from typing import Any


class WalkForwardProfitDiagnostics:
    DIAGNOSTIC_NAME = "walk_forward_profit_diagnostics"
    DIAGNOSTIC_VERSION = "ml36"

    def analyze(
        self,
        *,
        symbol: str | None,
        feature_version: str | None,
        model_version: str | None,
        walk_forward_summary: dict[str, Any],
        profit_aware_summary: dict[str, Any],
    ) -> dict[str, Any]:
        walk_forward_summary = self._normalize_mapping(walk_forward_summary)
        profit_aware_summary = self._normalize_mapping(profit_aware_summary)
        folds = [dict(item) for item in self._normalize_sequence(walk_forward_summary.get("folds"))]
        walk_summary = self._normalize_mapping(walk_forward_summary.get("summary"))
        fold_count = int(walk_summary.get("fold_count", len(folds)) or 0)
        profitable_fold_count = int(walk_summary.get("folds_profitable_on_test", 0) or 0)
        folds_with_gate = int(walk_summary.get("folds_with_selected_gate", fold_count) or 0)
        unprofitable_fold_count = max(folds_with_gate - profitable_fold_count, 0)
        best_fold = self._fold_snapshot(
            max(
                (fold for fold in folds if fold.get("test_result") is not None),
                key=lambda fold: float(dict(fold.get("test_result", {})).get("total_r", 0.0)),
                default=None,
            )
        )
        worst_fold = self._fold_snapshot(
            min(
                (fold for fold in folds if fold.get("test_result") is not None),
                key=lambda fold: float(dict(fold.get("test_result", {})).get("total_r", 0.0)),
                default=None,
            )
        )
        low_signal_folds = [
            self._fold_snapshot(fold)
            for fold in folds
            if int(dict(fold.get("test_result", {})).get("signal_count", 0) or 0) < 5
        ]
        regime_related_failures = sorted(
            {
                str(warning)
                for fold in folds
                for warning in dict(fold.get("direction_bias", {})).get("warnings", [])
                if "regime" in str(warning)
            }
        )
        profit_aware_diagnostics = self.build_profit_aware_diagnostics(
            profit_aware_summary=profit_aware_summary
        )
        recommendations = self._recommendations(
            walk_forward_profit_factor=self._safe_float(walk_summary.get("global_profit_factor")),
            walk_forward_total_r=self._safe_float(walk_summary.get("global_total_r")),
            fold_count=fold_count,
            profitable_fold_count=profitable_fold_count,
            low_signal_folds=low_signal_folds,
            profit_aware_diagnostics=profit_aware_diagnostics,
        )

        return {
            "diagnostic_name": self.DIAGNOSTIC_NAME,
            "diagnostic_version": self.DIAGNOSTIC_VERSION,
            "symbol": symbol,
            "feature_version": feature_version,
            "model_version": model_version,
            "walk_forward_profit_factor": self._safe_float(walk_summary.get("global_profit_factor")),
            "walk_forward_total_r": self._safe_float(walk_summary.get("global_total_r")),
            "fold_count": fold_count,
            "profitable_fold_count": profitable_fold_count,
            "unprofitable_fold_count": unprofitable_fold_count,
            "worst_fold": worst_fold,
            "best_fold": best_fold,
            "low_signal_folds": low_signal_folds,
            "regime_related_failures": regime_related_failures,
            "profit_aware_profit_factor": profit_aware_diagnostics.get("profit_aware_profit_factor"),
            "profit_aware_total_r": profit_aware_diagnostics.get("profit_aware_total_r"),
            "profit_aware_threshold_used": profit_aware_diagnostics.get("profit_aware_threshold_used"),
            "recommendations": recommendations,
        }

    def build_profit_aware_diagnostics(
        self,
        *,
        profit_aware_summary: dict[str, Any],
    ) -> dict[str, Any]:
        profit_aware_summary = self._normalize_mapping(profit_aware_summary)
        gate_results = [
            dict(item)
            for item in self._normalize_sequence(profit_aware_summary.get("gate_results"))
        ]
        best_gate = self._best_profit_gate(gate_results)
        summary = self._normalize_mapping(profit_aware_summary.get("summary"))
        profit_factor = self._safe_float(summary.get("profit_factor"))
        total_r = self._safe_float(summary.get("total_r"))
        threshold_used = summary.get("threshold")
        gate_type = summary.get("gate_type")
        if best_gate is not None:
            if profit_factor is None:
                profit_factor = self._safe_float(best_gate.get("profit_factor"))
            if total_r is None:
                total_r = self._safe_float(best_gate.get("total_r"))
            if threshold_used is None:
                threshold_used = best_gate.get("threshold")
            if gate_type is None:
                gate_type = best_gate.get("gate_type")
        return {
            "profit_aware_profit_factor": profit_factor,
            "profit_aware_total_r": total_r,
            "profit_aware_threshold_used": self._safe_float(threshold_used),
            "profit_aware_gate_type": gate_type,
            "best_gate": self._gate_snapshot(best_gate),
        }

    @staticmethod
    def _best_profit_gate(gate_results: list[dict[str, Any]]) -> dict[str, Any] | None:
        eligible = [
            row
            for row in gate_results
            if int(row.get("resolved_signal_count", 0) or 0) > 0
        ]
        if not eligible:
            return None
        return max(
            eligible,
            key=lambda row: (
                float(row.get("total_r", 0.0) or 0.0),
                float(row.get("profit_factor", 0.0) or 0.0),
                int(row.get("resolved_signal_count", 0) or 0),
            ),
        )

    def _recommendations(
        self,
        *,
        walk_forward_profit_factor: float | None,
        walk_forward_total_r: float | None,
        fold_count: int,
        profitable_fold_count: int,
        low_signal_folds: list[dict[str, Any]],
        profit_aware_diagnostics: dict[str, Any],
    ) -> list[str]:
        recommendations: list[str] = []
        if fold_count < 3:
            recommendations.append("Increase walk-forward coverage before treating stability metrics as reliable.")
        if walk_forward_profit_factor is not None and walk_forward_profit_factor <= 1.0:
            recommendations.append("Audit temporal stability because walk-forward profit factor is not yet above 1.0.")
        if walk_forward_total_r is not None and walk_forward_total_r <= 0.0:
            recommendations.append("Reduce unstable gates or thresholds because walk-forward total R is non-positive.")
        if profitable_fold_count <= max(fold_count // 2, 0):
            recommendations.append("Inspect fold-level instability because too few folds are profitable.")
        if low_signal_folds:
            recommendations.append("Review signal gating because some folds have too few test signals.")
        if (profit_aware_diagnostics.get("profit_aware_profit_factor") or 0.0) <= 1.0:
            recommendations.append("Review profit-aware threshold selection before wider grid expansion.")
        if not recommendations:
            recommendations.append("Walk-forward and profit-aware diagnostics look stable enough for research review.")
        return list(dict.fromkeys(recommendations))

    def _fold_snapshot(self, fold: dict[str, Any] | None) -> dict[str, Any] | None:
        if fold is None:
            return None
        test_result = dict(fold.get("test_result", {}))
        return {
            "fold_index": fold.get("fold_index"),
            "train_start": fold.get("train_start"),
            "train_end": fold.get("train_end"),
            "validation_start": fold.get("validation_start"),
            "validation_end": fold.get("validation_end"),
            "test_start": fold.get("test_start"),
            "test_end": fold.get("test_end"),
            "gate_type": dict(fold.get("selected_gate", {})).get("gate_type"),
            "threshold": self._safe_float(dict(fold.get("selected_gate", {})).get("threshold")),
            "signal_count": int(test_result.get("signal_count", 0) or 0),
            "resolved_signal_count": int(test_result.get("resolved_signal_count", 0) or 0),
            "profit_factor": self._safe_float(test_result.get("profit_factor")),
            "total_r": self._safe_float(test_result.get("total_r")),
        }

    def _gate_snapshot(self, gate: dict[str, Any] | None) -> dict[str, Any] | None:
        if gate is None:
            return None
        return {
            "gate_type": gate.get("gate_type"),
            "threshold": self._safe_float(gate.get("threshold")),
            "resolved_signal_count": int(gate.get("resolved_signal_count", 0) or 0),
            "profit_factor": self._safe_float(gate.get("profit_factor")),
            "total_r": self._safe_float(gate.get("total_r")),
        }

    @staticmethod
    def _normalize_mapping(payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            return dict(payload)
        return {}

    @staticmethod
    def _normalize_sequence(payload: Any) -> list[Any]:
        if isinstance(payload, (list, tuple)):
            return list(payload)
        return []

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        if value is None:
            return None
        numeric = float(value)
        if numeric == float("inf") or numeric == float("-inf"):
            return None
        return numeric
