from __future__ import annotations

from statistics import median
from typing import Any


class WalkForwardValidationCandidateBoard:
    diagnostic_name = "walk_forward_validation_candidate_board"
    diagnostic_version = "ml38.10.26"

    def analyze(self, *, walk_forward_summary: dict[str, Any]) -> dict[str, Any]:
        walk_forward_summary = self._as_dict(walk_forward_summary)
        folds = [
            self._as_dict(item)
            for item in self._as_list(walk_forward_summary.get("folds"))
            if isinstance(item, dict)
        ]
        candidate_board_rows = [self._fold_row(fold) for fold in folds]
        no_gate_rows = [row for row in candidate_board_rows if not row["selected_gate_present"]]
        total_r_below_min_fold_count = sum(
            int(bool(row.get("has_total_r_below_min_blocker", False))) for row in no_gate_rows
        )
        total_r_repair_candidate_fold_count = sum(
            int(
                str(row.get("recommended_validation_repair_profile") or "").startswith(
                    "TOTAL_R_RELAX"
                )
            )
            for row in no_gate_rows
        )
        best_failed_total_r_by_fold = [
            {
                "fold_index": row.get("fold_index"),
                "gate_type": self._as_dict(row.get("best_failed_gate_by_distance_to_pass")).get(
                    "gate_type"
                ),
                "threshold": self._as_dict(row.get("best_failed_gate_by_distance_to_pass")).get(
                    "threshold"
                ),
                "validation_total_r": self._float_or_none(
                    self._as_dict(row.get("best_failed_gate_by_distance_to_pass")).get("total_r")
                ),
                "total_r_deficit": self._best_total_r_deficit(
                    self._as_dict(row.get("best_failed_gate_by_distance_to_pass"))
                ),
                "repair_hint": self._as_dict(row.get("best_failed_gate_by_distance_to_pass")).get(
                    "repair_hint"
                ),
                "primary_blocker": self._as_dict(
                    row.get("best_failed_gate_by_distance_to_pass")
                ).get("primary_blocker"),
            }
            for row in no_gate_rows
            if self._as_dict(row.get("best_failed_gate_by_distance_to_pass"))
        ]
        best_total_r_deficits = [
            deficit
            for deficit in (
                self._best_total_r_deficit(self._as_dict(row.get("best_failed_gate_by_distance_to_pass")))
                for row in no_gate_rows
            )
            if deficit is not None
        ]
        fold_root_causes = [
            self._as_dict(row.get("validation_fold_root_cause"))
            for row in candidate_board_rows
            if self._as_dict(row.get("validation_fold_root_cause"))
        ]
        primary_root_cause_counts: dict[str, int] = {}
        for item in fold_root_causes:
            root = str(item.get("primary_root_cause") or "UNKNOWN")
            primary_root_cause_counts[root] = primary_root_cause_counts.get(root, 0) + 1
        worst_root_cause = None
        if fold_root_causes:
            worst_root_cause = min(
                fold_root_causes,
                key=lambda item: float(item.get("validation_total_r", 0.0) or 0.0),
            )

        repair_profile_counts: dict[str, int] = {}
        for row in no_gate_rows:
            profile = str(row.get("recommended_validation_repair_profile") or "UNKNOWN")
            repair_profile_counts[profile] = repair_profile_counts.get(profile, 0) + 1

        warnings: list[str] = []
        recommendations: list[str] = []
        if not folds:
            diagnostic_status = "NO_FOLDS"
            verdict = "NO_FOLDS"
            recommended_validation_repair_profile = "NO_TOTAL_R_REPAIR_NEEDED"
            recommendations.append("run_walk_forward_before_validation_candidate_board_review")
        elif not no_gate_rows:
            diagnostic_status = "VALIDATION_GATES_ALREADY_SELECTED"
            verdict = "VALIDATION_GATES_ALREADY_SELECTED"
            recommended_validation_repair_profile = "NO_TOTAL_R_REPAIR_NEEDED"
        else:
            diagnostic_status = "COMPLETED"
            total_r_profiles = [
                profile
                for profile in repair_profile_counts
                if profile.startswith("TOTAL_R_RELAX")
            ]
            if total_r_profiles:
                recommended_validation_repair_profile = min(
                    total_r_profiles,
                    key=lambda item: (
                        0 if item == "TOTAL_R_RELAX_MINUS_1_25_RESEARCH_ONLY" else 1,
                        item,
                    ),
                )
                verdict = "TOTAL_R_REPAIR_PROBE_WORTH_TESTING"
                warnings.append("validation_total_r_repair_is_research_only")
                recommendations.append("run_total_r_repair_probe_only_as_research_not_acceptance")
            elif no_gate_rows and all(
                str(row.get("walk_forward_validation_candidate_board_verdict") or "") == ""
                for row in no_gate_rows
            ):
                recommended_validation_repair_profile = "NO_THRESHOLD_REPAIR_RECOMMENDED"
                verdict = "NOT_REPAIRABLE_BY_TOTAL_R_RELAXATION"
            elif total_r_below_min_fold_count == len(no_gate_rows) and best_total_r_deficits:
                recommended_validation_repair_profile = "NO_THRESHOLD_REPAIR_RECOMMENDED"
                verdict = "TOTAL_R_DEFICIT_TOO_LARGE_FEATURE_REPAIR_NEEDED"
                warnings.append("total_r_deficit_too_large_for_threshold_repair")
                recommendations.append(
                    "prefer_feature_or_exit_repair_over_more_threshold_relaxation"
                )
            else:
                recommended_validation_repair_profile = "NO_THRESHOLD_REPAIR_RECOMMENDED"
                verdict = "NOT_REPAIRABLE_BY_TOTAL_R_RELAXATION"

            recommendations.append("inspect_walk_forward_validation_candidate_board")
            recommendations.append(
                "reject_total_r_repair_if_fold_drawdown_or_side_mismatch_remains_primary_blocker"
            )
            if fold_root_causes:
                recommendations.append("inspect_worst_fold_root_cause_before_more_threshold_relaxation")

        return {
            "diagnostic_name": self.diagnostic_name,
            "diagnostic_version": self.diagnostic_version,
            "diagnostic_status": diagnostic_status,
            "fold_count": len(folds),
            "folds_with_selected_gate": sum(
                int(row.get("selected_gate_present", False)) for row in candidate_board_rows
            ),
            "no_gate_fold_count": len(no_gate_rows),
            "candidate_board_rows": candidate_board_rows,
            "total_r_below_min_fold_count": total_r_below_min_fold_count,
            "total_r_repair_candidate_fold_count": total_r_repair_candidate_fold_count,
            "best_failed_total_r_by_fold": best_failed_total_r_by_fold,
            "fold_root_cause_count": len(fold_root_causes),
            "primary_root_cause_counts": primary_root_cause_counts,
            "worst_fold_root_cause": worst_root_cause,
            "median_best_total_r_deficit": (
                median(best_total_r_deficits) if best_total_r_deficits else None
            ),
            "max_best_total_r_deficit": (
                max(best_total_r_deficits) if best_total_r_deficits else None
            ),
            "recommended_validation_repair_profile": recommended_validation_repair_profile,
            "repair_profile_counts": repair_profile_counts,
            "verdict": verdict,
            "warnings": list(dict.fromkeys(warnings)),
            "recommendations": list(dict.fromkeys(recommendations)),
        }

    def _fold_row(self, fold: dict[str, Any]) -> dict[str, Any]:
        diagnostics = self._as_dict(fold.get("validation_gate_selection_diagnostics"))
        total_r_board = self._as_dict(diagnostics.get("total_r_failure_candidate_board"))
        best_distance_gate = self._as_dict(diagnostics.get("best_failed_gate_by_distance_to_pass"))
        return {
            "fold_index": fold.get("fold_index"),
            "train_start": fold.get("train_start"),
            "train_end": fold.get("train_end"),
            "validation_start": fold.get("validation_start"),
            "validation_end": fold.get("validation_end"),
            "test_start": fold.get("test_start"),
            "test_end": fold.get("test_end"),
            "selected_gate_present": bool(fold.get("selected_gate")),
            "gate_reject_reason": fold.get("gate_reject_reason"),
            "selection_mode": diagnostics.get("selection_mode"),
            "directional_side_filter_profile": diagnostics.get(
                "directional_side_filter_profile"
            ),
            "allowed_signal_directions": self._as_list(
                diagnostics.get("allowed_signal_directions")
            ),
            "side_aware_validation_relaxation_enabled": bool(
                diagnostics.get("side_aware_validation_relaxation_enabled", False)
            ),
            "effective_min_signal_count": diagnostics.get("effective_min_signal_count"),
            "effective_min_profit_factor": self._float_or_none(
                diagnostics.get("effective_min_profit_factor")
            ),
            "effective_min_total_r": self._float_or_none(
                diagnostics.get("effective_min_total_r")
            ),
            "effective_min_expectancy_r": self._float_or_none(
                diagnostics.get("effective_min_expectancy_r")
            ),
            "best_failed_gate_candidates": self._as_list(
                diagnostics.get("best_failed_gate_candidates")
            ),
            "best_failed_gate_by_distance_to_pass": best_distance_gate,
            "validation_fold_root_cause": self._as_dict(
                fold.get("validation_fold_root_cause")
            ),
            "recommended_validation_repair_profile": total_r_board.get(
                "recommended_validation_repair_profile"
            ),
            "total_r_repair_verdict": total_r_board.get("verdict"),
            "total_r_repair_candidate_count": self._int_or_zero(
                total_r_board.get("total_r_repair_candidate_count")
            ),
            "best_total_r_gate": self._as_dict(total_r_board.get("best_total_r_gate")),
            "best_distance_to_pass_gate": self._as_dict(
                total_r_board.get("best_distance_to_pass_gate")
            ),
            "min_total_r_deficit": self._float_or_none(
                total_r_board.get("min_total_r_deficit")
            ),
            "median_total_r_deficit": self._float_or_none(
                total_r_board.get("median_total_r_deficit")
            ),
            "max_total_r_deficit": self._float_or_none(
                total_r_board.get("max_total_r_deficit")
            ),
            "primary_failure_reason": self._primary_reason(
                self._as_dict(diagnostics.get("failure_reason_counts"))
            ),
            "has_total_r_below_min_blocker": bool(
                self._as_dict(diagnostics.get("failure_reason_counts")).get(
                    "total_r_below_min",
                    0,
                )
            ),
        }

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

    @staticmethod
    def _int_or_zero(value: Any) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _primary_reason(reason_counts: dict[str, Any]) -> str | None:
        if not reason_counts:
            return None
        return max(
            reason_counts.items(),
            key=lambda item: (int(item[1] or 0), str(item[0])),
        )[0]

    @staticmethod
    def _best_total_r_deficit(gate: dict[str, Any]) -> float | None:
        deficits = dict(gate.get("threshold_deficits") or {})
        value = deficits.get("total_r_deficit")
        try:
            return None if value is None else float(value)
        except (TypeError, ValueError):
            return None
