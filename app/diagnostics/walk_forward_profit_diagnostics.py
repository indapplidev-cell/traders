from __future__ import annotations

from typing import Any

from app.diagnostics.directional_side_signal_recovery_diagnostics import (
    DirectionalSideSignalRecoveryDiagnostics,
)
from app.diagnostics.walk_forward_validation_candidate_board import (
    WalkForwardValidationCandidateBoard,
)


class WalkForwardProfitDiagnostics:
    DIAGNOSTIC_NAME = "walk_forward_profit_diagnostics"
    DIAGNOSTIC_VERSION = "ml38.10.25"

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
        fold_snapshots = [
            snapshot
            for snapshot in (self._fold_snapshot(fold) for fold in folds)
            if snapshot is not None
        ]
        resolved_signal_counts = [
            int(snapshot.get("resolved_signal_count", 0) or 0)
            for snapshot in fold_snapshots
        ]
        zero_signal_fold_count = sum(int(value == 0) for value in resolved_signal_counts)
        low_signal_fold_count = sum(int(value < 5) for value in resolved_signal_counts)
        min_resolved_signal_count = min(resolved_signal_counts) if resolved_signal_counts else 0
        max_resolved_signal_count = max(resolved_signal_counts) if resolved_signal_counts else 0
        median_resolved_signal_count = self._median_int(resolved_signal_counts)
        total_resolved_signal_count = sum(resolved_signal_counts)
        fold_signal_summary = {
            "fold_count": fold_count,
            "folds_with_gate": folds_with_gate,
            "fold_snapshot_count": len(fold_snapshots),
            "total_resolved_signal_count": total_resolved_signal_count,
            "zero_signal_fold_count": zero_signal_fold_count,
            "low_signal_fold_count": low_signal_fold_count,
            "min_resolved_signal_count": min_resolved_signal_count,
            "median_resolved_signal_count": median_resolved_signal_count,
            "max_resolved_signal_count": max_resolved_signal_count,
        }
        unprofitable_fold_count = max(folds_with_gate - profitable_fold_count, 0)
        profitable_fold_rate = (
            profitable_fold_count / folds_with_gate if folds_with_gate else 0.0
        )
        walk_forward_stability_payload = self._walk_forward_stability_payload(
            walk_forward_profit_factor=self._safe_float(walk_summary.get("global_profit_factor")),
            walk_forward_total_r=self._safe_float(walk_summary.get("global_total_r")),
            fold_count=fold_count,
            folds_with_gate=folds_with_gate,
            profitable_fold_count=profitable_fold_count,
            profitable_fold_rate=profitable_fold_rate,
            total_resolved_signal_count=total_resolved_signal_count,
            zero_signal_fold_count=zero_signal_fold_count,
            low_signal_fold_count=low_signal_fold_count,
            min_resolved_signal_count=min_resolved_signal_count,
            median_resolved_signal_count=median_resolved_signal_count,
        )
        best_fold = self._fold_snapshot(
            max(
                (fold for fold in folds if fold.get("test_result") is not None),
                key=lambda fold: float(
                    self._normalize_mapping(fold.get("test_result")).get("total_r", 0.0)
                ),
                default=None,
            )
        )
        worst_fold = self._fold_snapshot(
            min(
                (fold for fold in folds if fold.get("test_result") is not None),
                key=lambda fold: float(
                    self._normalize_mapping(fold.get("test_result")).get("total_r", 0.0)
                ),
                default=None,
            )
        )
        low_signal_folds = [
            self._fold_snapshot(fold)
            for fold in folds
            if int(
                self._normalize_mapping(fold.get("test_result")).get("signal_count", 0)
                or 0
            )
            < 5
        ]
        regime_related_failures = sorted(
            {
                str(warning)
                for fold in folds
                for warning in self._normalize_sequence(
                    self._normalize_mapping(fold.get("direction_bias")).get("warnings")
                )
                if "regime" in str(warning)
            }
        )
        profit_aware_diagnostics = self.build_profit_aware_diagnostics(
            profit_aware_summary=profit_aware_summary
        )
        walk_forward_exit_root_cause_summary = self._summarize_walk_forward_exit_audits(
            folds=folds
        )
        directional_side_signal_recovery_diagnostics = (
            DirectionalSideSignalRecoveryDiagnostics().analyze(
                walk_forward_summary=walk_forward_summary,
                side_profile=walk_forward_summary.get("directional_side_filter_profile"),
            )
        )
        walk_forward_validation_candidate_board = (
            WalkForwardValidationCandidateBoard().analyze(
                walk_forward_summary=walk_forward_summary,
            )
        )
        recommendations = self._recommendations(
            walk_forward_profit_factor=self._safe_float(walk_summary.get("global_profit_factor")),
            walk_forward_total_r=self._safe_float(walk_summary.get("global_total_r")),
            fold_count=fold_count,
            profitable_fold_count=profitable_fold_count,
            low_signal_folds=low_signal_folds,
            profit_aware_diagnostics=profit_aware_diagnostics,
        )
        recommendations.extend(
            [
                "inspect_walk_forward_validation_candidate_board",
                "if_total_r_repair_probe_is_used_keep_research_only",
                "reject_total_r_repair_if_fold_drawdown_or_side_mismatch_remains_primary_blocker",
            ]
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
            "fold_snapshots": fold_snapshots,
            "fold_signal_summary": fold_signal_summary,
            "fold_profit_summary": {
                "profitable_fold_count": profitable_fold_count,
                "unprofitable_fold_count": unprofitable_fold_count,
                "profitable_fold_rate": profitable_fold_rate,
            },
            "zero_signal_fold_count": zero_signal_fold_count,
            "low_signal_fold_count": low_signal_fold_count,
            "min_resolved_signal_count": min_resolved_signal_count,
            "median_resolved_signal_count": median_resolved_signal_count,
            "max_resolved_signal_count": max_resolved_signal_count,
            "total_resolved_signal_count": total_resolved_signal_count,
            "walk_forward_stability_status": walk_forward_stability_payload["walk_forward_stability_status"],
            "walk_forward_stability_verdict": walk_forward_stability_payload["walk_forward_stability_verdict"],
            "walk_forward_stability_warnings": walk_forward_stability_payload["walk_forward_stability_warnings"],
            "regime_related_failures": regime_related_failures,
            "profit_aware_profit_factor": profit_aware_diagnostics.get("profit_aware_profit_factor"),
            "profit_aware_total_r": profit_aware_diagnostics.get("profit_aware_total_r"),
            "profit_aware_threshold_used": profit_aware_diagnostics.get("profit_aware_threshold_used"),
            "profit_exit_root_cause_audit": profit_aware_diagnostics.get("profit_exit_root_cause_audit"),
            "walk_forward_profit_exit_root_cause_summary": walk_forward_exit_root_cause_summary,
            "directional_side_signal_recovery_diagnostics": directional_side_signal_recovery_diagnostics,
            "directional_side_signal_recovery_status": directional_side_signal_recovery_diagnostics.get("diagnostic_status"),
            "directional_side_signal_recovery_verdict": directional_side_signal_recovery_diagnostics.get("verdict"),
            "primary_signal_loss_reason_counts": directional_side_signal_recovery_diagnostics.get("primary_signal_loss_reason_counts"),
            "walk_forward_validation_candidate_board": walk_forward_validation_candidate_board,
            "walk_forward_validation_candidate_board_status": walk_forward_validation_candidate_board.get("diagnostic_status"),
            "walk_forward_validation_candidate_board_verdict": walk_forward_validation_candidate_board.get("verdict"),
            "recommended_validation_repair_profile": walk_forward_validation_candidate_board.get(
                "recommended_validation_repair_profile"
            ),
            "total_r_below_min_fold_count": walk_forward_validation_candidate_board.get(
                "total_r_below_min_fold_count"
            ),
            "total_r_repair_candidate_fold_count": walk_forward_validation_candidate_board.get(
                "total_r_repair_candidate_fold_count"
            ),
            "median_best_total_r_deficit": walk_forward_validation_candidate_board.get(
                "median_best_total_r_deficit"
            ),
            "max_best_total_r_deficit": walk_forward_validation_candidate_board.get(
                "max_best_total_r_deficit"
            ),
            "best_failed_total_r_by_fold": walk_forward_validation_candidate_board.get(
                "best_failed_total_r_by_fold"
            ),
            "validation_gate_failure_reason_counts": directional_side_signal_recovery_diagnostics.get(
                "validation_gate_failure_reason_counts"
            ),
            "side_aware_relaxed_fold_count": directional_side_signal_recovery_diagnostics.get(
                "side_aware_relaxed_fold_count"
            ),
            "side_filter_removed_all_fold_count": directional_side_signal_recovery_diagnostics.get("side_filter_removed_all_fold_count"),
            "raw_signal_available_but_filtered_out_count": directional_side_signal_recovery_diagnostics.get("raw_signal_available_but_filtered_out_count"),
            "threshold_too_strict_fold_count": directional_side_signal_recovery_diagnostics.get("threshold_too_strict_fold_count"),
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
        profit_exit_root_cause_audit = self._normalize_mapping(
            profit_aware_summary.get("profit_exit_root_cause_audit")
            or summary.get("profit_exit_root_cause_audit")
        )
        entry_path_prediction_filter_summary = self._normalize_mapping(
            profit_aware_summary.get("entry_path_prediction_filter_summary")
            or summary.get("entry_path_prediction_filter_summary")
        )
        stop_pressure_effectiveness_audit = self._normalize_mapping(
            profit_aware_summary.get("stop_pressure_effectiveness_audit")
            or summary.get("stop_pressure_effectiveness_audit")
            or entry_path_prediction_filter_summary.get("stop_pressure_effectiveness_audit")
        )
        if best_gate is not None:
            if profit_factor is None:
                profit_factor = self._safe_float(best_gate.get("profit_factor"))
            if total_r is None:
                total_r = self._safe_float(best_gate.get("total_r"))
            if threshold_used is None:
                threshold_used = best_gate.get("threshold")
            if gate_type is None:
                gate_type = best_gate.get("gate_type")
            if not profit_exit_root_cause_audit:
                profit_exit_root_cause_audit = self._normalize_mapping(
                    best_gate.get("profit_exit_root_cause_audit")
                )
            if not entry_path_prediction_filter_summary:
                entry_path_prediction_filter_summary = self._normalize_mapping(
                    best_gate.get("entry_path_prediction_filter_summary")
                )
            if not stop_pressure_effectiveness_audit:
                stop_pressure_effectiveness_audit = self._normalize_mapping(
                    best_gate.get("stop_pressure_effectiveness_audit")
                    or entry_path_prediction_filter_summary.get("stop_pressure_effectiveness_audit")
                )
        return {
            "profit_aware_profit_factor": profit_factor,
            "profit_aware_total_r": total_r,
            "profit_aware_threshold_used": self._safe_float(threshold_used),
            "profit_aware_gate_type": gate_type,
            "best_gate": self._gate_snapshot(best_gate),
            "profit_exit_root_cause_audit": profit_exit_root_cause_audit,
            "entry_path_prediction_filter_summary": entry_path_prediction_filter_summary,
            "stop_pressure_effectiveness_audit": stop_pressure_effectiveness_audit,
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

    def _summarize_walk_forward_exit_audits(
        self,
        *,
        folds: list[dict[str, Any]],
    ) -> dict[str, Any]:
        audits: list[dict[str, Any]] = []
        for fold in folds:
            test_result = self._normalize_mapping(fold.get("test_result"))
            audit = self._normalize_mapping(test_result.get("profit_exit_root_cause_audit"))
            if audit:
                audits.append(audit)

        if not audits:
            return {
                "diagnostic_name": "walk_forward_profit_exit_root_cause_summary",
                "diagnostic_version": "ml38.10.13",
                "audit_status": "NO_FOLD_EXIT_AUDITS",
                "fold_audit_count": 0,
                "primary_root_cause_counts": {},
                "dominant_primary_root_cause": None,
            }

        primary_counts: dict[str, int] = {}
        status_counts: dict[str, int] = {}
        total_resolved = 0
        total_r = 0.0
        for audit in audits:
            primary = str(audit.get("primary_root_cause") or "unknown")
            status = str(audit.get("root_cause_status") or "unknown")
            primary_counts[primary] = primary_counts.get(primary, 0) + 1
            status_counts[status] = status_counts.get(status, 0) + 1
            total_resolved += int(audit.get("resolved_signal_count", 0) or 0)
            total_r += float(audit.get("total_r", 0.0) or 0.0)

        dominant_primary = max(
            primary_counts.items(),
            key=lambda item: (item[1], item[0]),
        )[0]
        return {
            "diagnostic_name": "walk_forward_profit_exit_root_cause_summary",
            "diagnostic_version": "ml38.10.13",
            "audit_status": "COMPLETED",
            "fold_audit_count": len(audits),
            "primary_root_cause_counts": primary_counts,
            "root_cause_status_counts": status_counts,
            "dominant_primary_root_cause": dominant_primary,
            "resolved_signal_count": total_resolved,
            "total_r_from_fold_audits": total_r,
        }

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
        test_result = self._normalize_mapping(fold.get("test_result"))
        selected_gate = self._normalize_mapping(fold.get("selected_gate"))
        side_summary = self._normalize_mapping(test_result.get("directional_side_filter_summary"))
        return {
            "fold_index": fold.get("fold_index"),
            "train_start": fold.get("train_start"),
            "train_end": fold.get("train_end"),
            "validation_start": fold.get("validation_start"),
            "validation_end": fold.get("validation_end"),
            "test_start": fold.get("test_start"),
            "test_end": fold.get("test_end"),
            "gate_type": selected_gate.get("gate_type"),
            "threshold": self._safe_float(selected_gate.get("threshold")),
            "gate_reject_reason": fold.get("gate_reject_reason"),
            "directional_side_filter_profile": test_result.get("directional_side_filter_profile") or side_summary.get("profile"),
            "allowed_signal_directions": list(side_summary.get("allowed_signal_directions") or []),
            "original_signal_count_before_side_filter": int(side_summary.get("original_signal_count", test_result.get("signal_count", 0)) or 0),
            "filtered_signal_count_after_side_filter": int(side_summary.get("filtered_signal_count", test_result.get("signal_count", 0)) or 0),
            "removed_signal_count_by_side_filter": int(side_summary.get("removed_signal_count", 0) or 0),
            "removed_long_count_by_side_filter": int(side_summary.get("removed_long_count", 0) or 0),
            "removed_short_count_by_side_filter": int(side_summary.get("removed_short_count", 0) or 0),
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
    def _median_int(values: list[int]) -> int | None:
        if not values:
            return None
        ordered = sorted(int(value) for value in values)
        middle = len(ordered) // 2
        if len(ordered) % 2:
            return ordered[middle]
        return int((ordered[middle - 1] + ordered[middle]) / 2)

    @staticmethod
    def _walk_forward_stability_payload(
        *,
        walk_forward_profit_factor: float | None,
        walk_forward_total_r: float | None,
        fold_count: int,
        folds_with_gate: int,
        profitable_fold_count: int,
        profitable_fold_rate: float,
        total_resolved_signal_count: int,
        zero_signal_fold_count: int,
        low_signal_fold_count: int,
        min_resolved_signal_count: int,
        median_resolved_signal_count: int | None,
    ) -> dict[str, Any]:
        warnings: list[str] = []
        if fold_count <= 0:
            warnings.append("walk_forward_has_no_folds")
        if folds_with_gate <= 0:
            warnings.append("walk_forward_has_no_selected_gate_folds")
        if zero_signal_fold_count > 0:
            warnings.append("walk_forward_has_zero_signal_folds")
        if low_signal_fold_count > 0:
            warnings.append("walk_forward_has_low_signal_folds")
        if total_resolved_signal_count < 20:
            warnings.append("walk_forward_total_signal_count_too_low")
        if min_resolved_signal_count < 3:
            warnings.append("walk_forward_min_fold_signal_count_too_low")
        if median_resolved_signal_count is not None and median_resolved_signal_count < 5:
            warnings.append("walk_forward_median_fold_signal_count_too_low")
        if walk_forward_profit_factor is None:
            warnings.append("walk_forward_profit_factor_missing")
        elif walk_forward_profit_factor <= 1.0:
            warnings.append("walk_forward_profit_factor_not_profitable")
        if walk_forward_total_r is None:
            warnings.append("walk_forward_total_r_missing")
        elif walk_forward_total_r <= 0.0:
            warnings.append("walk_forward_total_r_not_positive")
        if profitable_fold_rate < 0.50:
            warnings.append("walk_forward_profitable_fold_rate_too_low")

        if fold_count <= 0 or folds_with_gate <= 0:
            verdict = "REJECT_NO_WALK_FORWARD_EVIDENCE"
            status = "NO_WALK_FORWARD_EVIDENCE"
        elif zero_signal_fold_count > 0 or low_signal_fold_count > 0 or total_resolved_signal_count < 20:
            verdict = "REJECT_LOW_SIGNAL_WALK_FORWARD"
            status = "LOW_SIGNAL_WALK_FORWARD"
        elif (
            walk_forward_profit_factor is not None
            and walk_forward_profit_factor > 1.0
            and walk_forward_total_r is not None
            and walk_forward_total_r > 0.0
            and profitable_fold_rate >= 0.50
        ):
            verdict = "CANDIDATE_FOR_NEXT_GRID_RESEARCH_ONLY"
            status = "STABLE_ENOUGH_FOR_RESEARCH"
        else:
            verdict = "REJECT_WALK_FORWARD_UNSTABLE"
            status = "WALK_FORWARD_UNSTABLE"

        return {
            "walk_forward_stability_status": status,
            "walk_forward_stability_verdict": verdict,
            "walk_forward_stability_warnings": list(dict.fromkeys(warnings)),
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
