from __future__ import annotations

from typing import Any


class DirectionalSideSignalRecoveryDiagnostics:
    diagnostic_name = "directional_side_signal_recovery_diagnostics"
    diagnostic_version = "ml38.10.23"

    LOW_SIGNAL_THRESHOLD = 5

    def analyze(
        self,
        *,
        walk_forward_summary: dict[str, Any],
        side_profile: str | None = None,
    ) -> dict[str, Any]:
        """Return fold-level reasons for missing/low side-aware WF signals."""
        from app.diagnostics.walk_forward_validation_candidate_board import (
            WalkForwardValidationCandidateBoard,
        )

        folds = [
            dict(item)
            for item in self._as_list(walk_forward_summary.get("folds"))
            if isinstance(item, dict)
        ]
        summary = self._as_dict(walk_forward_summary.get("summary"))
        validation_candidate_board = WalkForwardValidationCandidateBoard().analyze(
            walk_forward_summary=walk_forward_summary,
        )
        profile = side_profile or str(
            walk_forward_summary.get("directional_side_filter_profile") or "both_directions"
        )

        fold_rows = [self._fold_row(fold) for fold in folds]
        zero_signal_folds = [row for row in fold_rows if row["resolved_signal_count"] == 0]
        low_signal_folds = [
            row for row in fold_rows if row["resolved_signal_count"] < self.LOW_SIGNAL_THRESHOLD
        ]

        reason_counts: dict[str, int] = {}
        for row in fold_rows:
            reason = row["primary_signal_loss_reason"]
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

        selected_gate_count = sum(int(row["selected_gate_present"]) for row in fold_rows)
        side_filter_active_fold_count = sum(int(row["side_filter_active"]) for row in fold_rows)
        side_filter_removed_all_fold_count = sum(
            int(row["side_filter_removed_all_signals"]) for row in fold_rows
        )
        raw_signal_available_but_filtered_out_count = sum(
            int(row["raw_signal_available_but_filtered_out"]) for row in fold_rows
        )
        threshold_too_strict_fold_count = sum(
            int(row["threshold_too_strict_after_side_filter"]) for row in fold_rows
        )

        total_original_signal_count = sum(row["test_original_signal_count"] for row in fold_rows)
        total_filtered_signal_count = sum(row["test_filtered_signal_count"] for row in fold_rows)
        total_removed_signal_count = sum(row["test_removed_signal_count"] for row in fold_rows)
        total_removed_short_count = sum(row["test_removed_short_count"] for row in fold_rows)
        total_removed_long_count = sum(row["test_removed_long_count"] for row in fold_rows)
        resolved_counts = [row["resolved_signal_count"] for row in fold_rows]

        if not folds:
            status = "NO_WALK_FORWARD_FOLDS"
            verdict = "NO_EVIDENCE"
            recommendations = ["run_walk_forward_before_side_signal_recovery_review"]
        elif raw_signal_available_but_filtered_out_count > 0:
            status = "SIDE_FILTER_REMOVED_SIGNAL_EVIDENCE"
            verdict = "CHECK_SIDE_FILTER_STRICTNESS"
            recommendations = ["inspect_side_filter_removed_all_or_removed_short_counts"]
        elif threshold_too_strict_fold_count > 0:
            status = "THRESHOLD_TOO_STRICT_EVIDENCE"
            verdict = "CHECK_GATE_THRESHOLDS"
            recommendations = ["inspect_gate_threshold_scan_for_lower_threshold_candidates"]
        elif zero_signal_folds:
            status = "ZERO_SIGNAL_WALK_FORWARD"
            verdict = "REJECT_NO_WALK_FORWARD_SIGNAL_RECOVERY"
            recommendations = ["do_not_accept_side_profile_until_zero_signal_folds_are_resolved"]
        elif low_signal_folds:
            status = "LOW_SIGNAL_WALK_FORWARD"
            verdict = "REJECT_LOW_SIGNAL_WALK_FORWARD"
            recommendations = ["increase_fold_signal_count_or_relax_research_thresholds"]
        else:
            status = "SIGNAL_RECOVERY_OK"
            verdict = "KEEP_FOR_PROFIT_STABILITY_REVIEW"
            recommendations = ["compare_pf_total_r_and_fold_profitability_after_signal_recovery"]

        return {
            "diagnostic_name": self.diagnostic_name,
            "diagnostic_version": self.diagnostic_version,
            "diagnostic_status": status,
            "verdict": verdict,
            "side_profile": profile,
            "fold_count": len(fold_rows),
            "selected_gate_fold_count": selected_gate_count,
            "zero_signal_fold_count": len(zero_signal_folds),
            "low_signal_fold_count": len(low_signal_folds),
            "side_filter_active_fold_count": side_filter_active_fold_count,
            "side_filter_removed_all_fold_count": side_filter_removed_all_fold_count,
            "raw_signal_available_but_filtered_out_count": raw_signal_available_but_filtered_out_count,
            "threshold_too_strict_fold_count": threshold_too_strict_fold_count,
            "primary_signal_loss_reason_counts": reason_counts,
            "validation_gate_failure_reason_counts": self._merge_reason_counts(
                row.get("validation_gate_failure_reason_counts") for row in fold_rows
            ),
            "side_aware_relaxed_fold_count": sum(
                int(row.get("side_aware_validation_relaxation_enabled", False))
                for row in fold_rows
            ),
            "walk_forward_validation_candidate_board_status": validation_candidate_board.get(
                "diagnostic_status"
            ),
            "walk_forward_validation_candidate_board_verdict": validation_candidate_board.get(
                "verdict"
            ),
            "recommended_validation_repair_profile": validation_candidate_board.get(
                "recommended_validation_repair_profile"
            ),
            "total_r_below_min_fold_count": validation_candidate_board.get(
                "total_r_below_min_fold_count"
            ),
            "total_r_repair_candidate_fold_count": validation_candidate_board.get(
                "total_r_repair_candidate_fold_count"
            ),
            "median_best_total_r_deficit": validation_candidate_board.get(
                "median_best_total_r_deficit"
            ),
            "max_best_total_r_deficit": validation_candidate_board.get(
                "max_best_total_r_deficit"
            ),
            "validation_candidate_board_rows": validation_candidate_board.get(
                "candidate_board_rows",
                [],
            ),
            "total_original_signal_count": total_original_signal_count,
            "total_filtered_signal_count": total_filtered_signal_count,
            "total_removed_signal_count": total_removed_signal_count,
            "total_removed_short_count": total_removed_short_count,
            "total_removed_long_count": total_removed_long_count,
            "min_resolved_signal_count": min(resolved_counts) if resolved_counts else 0,
            "median_resolved_signal_count": self._median_int(resolved_counts),
            "max_resolved_signal_count": max(resolved_counts) if resolved_counts else 0,
            "fold_rows": fold_rows,
            "walk_forward_summary_signal_count": int(summary.get("total_test_signal_count", 0) or 0),
            "recommendations": list(dict.fromkeys(recommendations)),
        }

    def _fold_row(self, fold: dict[str, Any]) -> dict[str, Any]:
        selected_gate = self._as_dict(fold.get("selected_gate"))
        test_result = self._as_dict(fold.get("test_result"))
        gate_selection_diagnostics = self._as_dict(
            fold.get("validation_gate_selection_diagnostics")
        )
        gate_failure_reason_counts = self._as_dict(
            gate_selection_diagnostics.get("failure_reason_counts")
        )
        side_summary = self._as_dict(test_result.get("directional_side_filter_summary"))
        gate_reject_reason = fold.get("gate_reject_reason")
        validation_gates = [
            self._gate_probe(row)
            for row in self._as_list(fold.get("validation_gate_results"))
            if isinstance(row, dict)
        ]
        best_validation_by_filtered_count = self._best_gate_by(validation_gates, "filtered_signal_count")
        best_validation_by_original_count = self._best_gate_by(validation_gates, "original_signal_count")

        resolved = int(test_result.get("resolved_signal_count", test_result.get("signal_count", 0)) or 0)
        original_signal_count = int(
            side_summary.get("original_signal_count", test_result.get("signal_count", 0)) or 0
        )
        filtered_signal_count = int(
            side_summary.get("filtered_signal_count", test_result.get("signal_count", 0)) or 0
        )
        removed_signal_count = int(side_summary.get("removed_signal_count", 0) or 0)
        removed_long_count = int(side_summary.get("removed_long_count", 0) or 0)
        removed_short_count = int(side_summary.get("removed_short_count", 0) or 0)
        side_active = bool(side_summary.get("active", False))
        selected_gate_present = bool(selected_gate)
        side_removed_all = bool(original_signal_count > 0 and filtered_signal_count == 0 and side_active)
        raw_available_but_filtered = bool(original_signal_count > 0 and filtered_signal_count == 0)
        threshold_too_strict = bool(
            selected_gate_present
            and original_signal_count == 0
            and (best_validation_by_original_count or {}).get("original_signal_count", 0) > 0
        )
        primary_reason = self._primary_reason(
            selected_gate_present=selected_gate_present,
            gate_reject_reason=gate_reject_reason,
            original_signal_count=original_signal_count,
            filtered_signal_count=filtered_signal_count,
            resolved_signal_count=resolved,
            side_filter_active=side_active,
            side_filter_removed_all=side_removed_all,
            threshold_too_strict=threshold_too_strict,
            validation_gate_failure_reason_counts=gate_failure_reason_counts,
        )
        return {
            "fold_index": fold.get("fold_index"),
            "train_start": fold.get("train_start"),
            "train_end": fold.get("train_end"),
            "validation_start": fold.get("validation_start"),
            "validation_end": fold.get("validation_end"),
            "test_start": fold.get("test_start"),
            "test_end": fold.get("test_end"),
            "selected_gate_present": selected_gate_present,
            "gate_reject_reason": gate_reject_reason,
            "selected_gate_type": selected_gate.get("gate_type"),
            "selected_gate_threshold": self._float_or_none(selected_gate.get("threshold")),
            "resolved_signal_count": resolved,
            "test_signal_count": int(test_result.get("signal_count", 0) or 0),
            "test_original_signal_count": original_signal_count,
            "test_filtered_signal_count": filtered_signal_count,
            "test_removed_signal_count": removed_signal_count,
            "test_removed_long_count": removed_long_count,
            "test_removed_short_count": removed_short_count,
            "side_filter_active": side_active,
            "side_filter_profile": side_summary.get("profile"),
            "allowed_signal_directions": list(side_summary.get("allowed_signal_directions") or []),
            "side_filter_removed_all_signals": side_removed_all,
            "raw_signal_available_but_filtered_out": raw_available_but_filtered,
            "threshold_too_strict_after_side_filter": threshold_too_strict,
            "primary_signal_loss_reason": primary_reason,
            "validation_gate_probe_count": len(validation_gates),
            "validation_gate_selection_mode": gate_selection_diagnostics.get("selection_mode"),
            "side_aware_validation_relaxation_enabled": bool(
                gate_selection_diagnostics.get(
                    "side_aware_validation_relaxation_enabled",
                    False,
                )
            ),
            "effective_min_signal_count": gate_selection_diagnostics.get(
                "effective_min_signal_count"
            ),
            "effective_min_profit_factor": self._float_or_none(
                gate_selection_diagnostics.get("effective_min_profit_factor")
            ),
            "effective_min_total_r": self._float_or_none(
                gate_selection_diagnostics.get("effective_min_total_r")
            ),
            "effective_min_expectancy_r": self._float_or_none(
                gate_selection_diagnostics.get("effective_min_expectancy_r")
            ),
            "validation_gate_failure_reason_counts": gate_failure_reason_counts,
            "best_failed_gate_by_signal_count": self._as_dict(
                gate_selection_diagnostics.get("best_failed_gate_by_signal_count")
            ),
            "best_failed_gate_by_total_r": self._as_dict(
                gate_selection_diagnostics.get("best_failed_gate_by_total_r")
            ),
            "best_failed_gate_by_profit_factor": self._as_dict(
                gate_selection_diagnostics.get("best_failed_gate_by_profit_factor")
            ),
            "best_validation_by_filtered_count": best_validation_by_filtered_count,
            "best_validation_by_original_count": best_validation_by_original_count,
        }

    @classmethod
    def _gate_probe(cls, row: dict[str, Any]) -> dict[str, Any]:
        side_summary = cls._as_dict(row.get("directional_side_filter_summary"))
        return {
            "gate_type": row.get("gate_type"),
            "threshold": cls._float_or_none(row.get("threshold")),
            "signal_count": int(row.get("signal_count", 0) or 0),
            "resolved_signal_count": int(row.get("resolved_signal_count", 0) or 0),
            "profit_factor": cls._float_or_none(row.get("profit_factor")),
            "total_r": cls._float_or_none(row.get("total_r")),
            "original_signal_count": int(
                side_summary.get("original_signal_count", row.get("signal_count", 0)) or 0
            ),
            "filtered_signal_count": int(
                side_summary.get("filtered_signal_count", row.get("signal_count", 0)) or 0
            ),
            "removed_signal_count": int(side_summary.get("removed_signal_count", 0) or 0),
            "removed_long_count": int(side_summary.get("removed_long_count", 0) or 0),
            "removed_short_count": int(side_summary.get("removed_short_count", 0) or 0),
        }

    @staticmethod
    def _best_gate_by(gates: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
        if not gates:
            return None
        return max(
            gates,
            key=lambda row: (
                int(row.get(key, 0) or 0),
                float(row.get("total_r", 0.0) or 0.0),
            ),
        )

    @staticmethod
    def _primary_reason(
        *,
        selected_gate_present: bool,
        gate_reject_reason: Any,
        original_signal_count: int,
        filtered_signal_count: int,
        resolved_signal_count: int,
        side_filter_active: bool,
        side_filter_removed_all: bool,
        threshold_too_strict: bool,
        validation_gate_failure_reason_counts: dict[str, Any] | None = None,
    ) -> str:
        if not selected_gate_present:
            reason_counts = (
                dict(validation_gate_failure_reason_counts)
                if isinstance(validation_gate_failure_reason_counts, dict)
                else {}
            )
            if reason_counts:
                primary_reason = max(
                    reason_counts.items(),
                    key=lambda item: (int(item[1] or 0), str(item[0])),
                )[0]
                return f"no_selected_gate:{primary_reason}"
            return f"no_selected_gate:{gate_reject_reason or 'unknown'}"
        if side_filter_removed_all:
            return "side_filter_removed_all_signals"
        if side_filter_active and original_signal_count > filtered_signal_count and resolved_signal_count == 0:
            return "side_filter_removed_signals_then_zero_resolved"
        if threshold_too_strict:
            return "threshold_too_strict_after_side_filter"
        if resolved_signal_count == 0:
            return "selected_gate_zero_resolved_signals"
        if resolved_signal_count < DirectionalSideSignalRecoveryDiagnostics.LOW_SIGNAL_THRESHOLD:
            return "selected_gate_low_resolved_signals"
        return "signal_count_ok"

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, dict) else {}

    @staticmethod
    def _as_list(value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return list(value)
        if isinstance(value, (tuple, set)):
            return list(value)
        return [value]

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        try:
            return None if value is None else float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _merge_reason_counts(cls, items: Any) -> dict[str, int]:
        merged: dict[str, int] = {}
        for item in items:
            counts = cls._as_dict(item)
            for reason, count in counts.items():
                merged[str(reason)] = merged.get(str(reason), 0) + int(count or 0)
        return merged

    @staticmethod
    def _median_int(values: list[int]) -> int | None:
        if not values:
            return None
        ordered = sorted(int(value) for value in values)
        middle = len(ordered) // 2
        if len(ordered) % 2:
            return ordered[middle]
        return int((ordered[middle - 1] + ordered[middle]) / 2)
