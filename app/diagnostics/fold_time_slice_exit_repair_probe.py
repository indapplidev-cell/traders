from __future__ import annotations

from collections import Counter
from typing import Any


class FoldTimeSliceExitRepairProbe:
    diagnostic_name = "fold_time_slice_exit_repair_probe"
    diagnostic_version = "ml38.10.27"

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
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def analyze(self, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        candidate_rows = [self._candidate_row(item) for item in candidates]
        probe_rows = [
            row
            for row in candidate_rows
            if "lv31" in str(row.get("config_id") or "").lower()
            or bool(row.get("research_only_fold_repair_probe_enabled", False))
        ]

        profile_counts = Counter(
            str(row.get("fold_repair_probe_profile") or "UNSPECIFIED")
            for row in probe_rows
        )
        side_profile_counts = Counter(
            str(row.get("directional_side_filter_profile") or "BOTH_DIRECTIONS")
            for row in probe_rows
        )
        target_date_counts = Counter()
        for row in probe_rows:
            for date_text in self._as_list(row.get("fold_repair_target_dates")):
                target_date_counts[str(date_text)] += 1

        best_by_profit_total_r = self._top_rows(
            probe_rows,
            metric_key="profit_total_r",
            limit=8,
        )
        best_by_walk_forward_total_r = self._top_rows(
            probe_rows,
            metric_key="walk_forward_total_r",
            limit=8,
        )
        blackout_effectiveness_rows = self._top_rows(
            [row for row in probe_rows if row.get("fold_repair_time_slice_blackout_enabled")],
            metric_key="walk_forward_total_r",
            limit=10,
        )
        exit_mitigation_effectiveness_rows = self._top_rows(
            [
                row
                for row in probe_rows
                if "EXIT45" in str(row.get("fold_repair_probe_profile") or "")
                or "EXIT75" in str(row.get("fold_repair_probe_profile") or "")
            ],
            metric_key="walk_forward_total_r",
            limit=10,
        )

        verdict = self._build_verdict(
            probe_rows=probe_rows,
            blackout_effectiveness_rows=blackout_effectiveness_rows,
            exit_mitigation_effectiveness_rows=exit_mitigation_effectiveness_rows,
        )
        warnings = self._build_warnings(
            probe_rows=probe_rows,
            verdict=verdict,
        )
        recommendations = self._build_recommendations(verdict=verdict)

        return {
            "diagnostic_name": self.diagnostic_name,
            "diagnostic_version": self.diagnostic_version,
            "candidate_count": len(candidate_rows),
            "probe_candidate_count": len(probe_rows),
            "profile_counts": dict(profile_counts),
            "side_profile_counts": dict(side_profile_counts),
            "target_date_counts": dict(target_date_counts),
            "best_by_profit_total_r": best_by_profit_total_r,
            "best_by_walk_forward_total_r": best_by_walk_forward_total_r,
            "blackout_effectiveness_rows": blackout_effectiveness_rows,
            "exit_mitigation_effectiveness_rows": exit_mitigation_effectiveness_rows,
            "verdict": verdict,
            "warnings": warnings,
            "recommendations": recommendations,
        }

    def _candidate_row(self, candidate: dict[str, Any]) -> dict[str, Any]:
        worst_fold_root_cause = self._as_dict(candidate.get("worst_fold_root_cause"))
        profit_aware_diagnostics = self._as_dict(candidate.get("profit_aware_diagnostics"))
        fold_time_slice_blackout_summary = self._as_dict(
            candidate.get("fold_repair_probe_diagnostics")
            or profit_aware_diagnostics.get("fold_time_slice_blackout_summary")
        )
        failed_gates = self._as_list(candidate.get("failed_gates"))
        return {
            "symbol": candidate.get("symbol"),
            "config_id": candidate.get("config_id"),
            "candidate_id": candidate.get("candidate_id"),
            "candidate_status": candidate.get("candidate_status"),
            "fold_repair_probe_profile": candidate.get("fold_repair_probe_profile"),
            "research_only_fold_repair_probe_enabled": bool(
                candidate.get("research_only_fold_repair_probe_enabled", False)
            ),
            "fold_repair_target_dates": self._as_list(candidate.get("fold_repair_target_dates")),
            "fold_repair_time_slice_blackout_enabled": bool(
                candidate.get("fold_repair_time_slice_blackout_enabled", False)
            ),
            "fold_repair_blackout_dates": self._as_list(candidate.get("fold_repair_blackout_dates")),
            "directional_side_filter_profile": candidate.get("directional_side_filter_profile"),
            "allowed_signal_directions": self._as_list(candidate.get("allowed_signal_directions")),
            "profit_factor": self._float_or_none(candidate.get("profit_factor")),
            "profit_total_r": self._float_or_none(candidate.get("profit_total_r")),
            "walk_forward_profit_factor": self._float_or_none(
                candidate.get("walk_forward_profit_factor")
            ),
            "walk_forward_total_r": self._float_or_none(
                candidate.get("walk_forward_total_r", candidate.get("walk_forward_global_total_r"))
            ),
            "walk_forward_gate_passed": "walk_forward_gate" not in failed_gates,
            "failed_gates": failed_gates,
            "fold_time_slice_blackout_summary": fold_time_slice_blackout_summary,
            "worst_fold_root_cause": worst_fold_root_cause,
            "validation_total_r": self._float_or_none(
                worst_fold_root_cause.get("validation_total_r")
            ),
            "primary_root_cause": worst_fold_root_cause.get("primary_root_cause"),
            "outcome_counts": self._as_dict(worst_fold_root_cause.get("outcome_counts")),
            "top_bad_time_slices": self._as_list(worst_fold_root_cause.get("top_bad_time_slices")),
        }

    def _top_rows(
        self,
        rows: list[dict[str, Any]],
        *,
        metric_key: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        ranked = sorted(
            rows,
            key=lambda row: (
                self._float_or_none(row.get(metric_key)) is not None,
                self._float_or_none(row.get(metric_key)) or float("-inf"),
                self._float_or_none(row.get("profit_total_r")) or float("-inf"),
            ),
            reverse=True,
        )
        compact_rows: list[dict[str, Any]] = []
        for row in ranked[:limit]:
            blackout_summary = self._as_dict(row.get("fold_time_slice_blackout_summary"))
            compact_rows.append(
                {
                    "symbol": row.get("symbol"),
                    "config_id": row.get("config_id"),
                    "candidate_id": row.get("candidate_id"),
                    "candidate_status": row.get("candidate_status"),
                    "fold_repair_probe_profile": row.get("fold_repair_probe_profile"),
                    "fold_repair_target_dates": self._as_list(row.get("fold_repair_target_dates")),
                    "fold_repair_time_slice_blackout_enabled": row.get(
                        "fold_repair_time_slice_blackout_enabled"
                    ),
                    "fold_repair_blackout_dates": self._as_list(row.get("fold_repair_blackout_dates")),
                    "directional_side_filter_profile": row.get("directional_side_filter_profile"),
                    "allowed_signal_directions": self._as_list(row.get("allowed_signal_directions")),
                    "profit_factor": row.get("profit_factor"),
                    "profit_total_r": row.get("profit_total_r"),
                    "walk_forward_profit_factor": row.get("walk_forward_profit_factor"),
                    "walk_forward_total_r": row.get("walk_forward_total_r"),
                    "walk_forward_gate_passed": row.get("walk_forward_gate_passed"),
                    "failed_gates": self._as_list(row.get("failed_gates")),
                    "removed_signal_count": blackout_summary.get("removed_signal_count"),
                    "removed_ratio": blackout_summary.get("removed_ratio"),
                    "validation_total_r": row.get("validation_total_r"),
                    "primary_root_cause": row.get("primary_root_cause"),
                    "outcome_counts": self._as_dict(row.get("outcome_counts")),
                    "top_bad_time_slices": self._as_list(row.get("top_bad_time_slices"))[:5],
                }
            )
        return compact_rows

    def _build_verdict(
        self,
        *,
        probe_rows: list[dict[str, Any]],
        blackout_effectiveness_rows: list[dict[str, Any]],
        exit_mitigation_effectiveness_rows: list[dict[str, Any]],
    ) -> str:
        if not probe_rows:
            return "NO_PROBE_CANDIDATES"
        if not any(
            row.get("walk_forward_gate_passed")
            and (self._float_or_none(row.get("walk_forward_total_r")) or 0.0) > 0.0
            for row in probe_rows
        ):
            return "PROBE_HAS_NO_WALK_FORWARD_CONFIRMATION"

        best_blackout = max(
            (
                self._float_or_none(row.get("walk_forward_total_r")) or float("-inf")
                for row in blackout_effectiveness_rows
            ),
            default=float("-inf"),
        )
        best_non_blackout = max(
            (
                self._float_or_none(row.get("walk_forward_total_r")) or float("-inf")
                for row in probe_rows
                if not row.get("fold_repair_time_slice_blackout_enabled")
            ),
            default=float("-inf"),
        )
        if best_blackout > best_non_blackout:
            return "TIME_SLICE_BLACKOUT_IMPROVES_FINAL_ONLY_RESEARCH_OVERFIT_RISK"

        best_exit_variant = max(
            (
                self._float_or_none(row.get("walk_forward_total_r")) or float("-inf")
                for row in exit_mitigation_effectiveness_rows
            ),
            default=float("-inf"),
        )
        if best_exit_variant > 0.0:
            return "EXIT_MITIGATION_VARIANT_IMPROVES_WF_RESEARCH_ONLY"
        return "NO_REPAIR_IMPROVEMENT"

    def _build_warnings(
        self,
        *,
        probe_rows: list[dict[str, Any]],
        verdict: str,
    ) -> list[str]:
        warnings = ["research_only_probe_not_live_ready", "do_not_accept_lv31"]
        if any(row.get("fold_repair_time_slice_blackout_enabled") for row in probe_rows):
            warnings.append("date_blackout_can_overfit_known_bad_dates")
        if verdict in {
            "PROBE_HAS_NO_WALK_FORWARD_CONFIRMATION",
            "TIME_SLICE_BLACKOUT_IMPROVES_FINAL_ONLY_RESEARCH_OVERFIT_RISK",
        }:
            warnings.append("wf_still_unconfirmed")
        return list(dict.fromkeys(warnings))

    @staticmethod
    def _build_recommendations(*, verdict: str) -> list[str]:
        recommendations = [
            "compare_lv31_against_lv28_lv30_same_side_profile",
        ]
        if verdict == "TIME_SLICE_BLACKOUT_IMPROVES_FINAL_ONLY_RESEARCH_OVERFIT_RISK":
            recommendations.append("if_blackout_works_replace_with_feature/regime_filter_not_date_filter")
        if verdict == "EXIT_MITIGATION_VARIANT_IMPROVES_WF_RESEARCH_ONLY":
            recommendations.append("if_exit45_works_test_generalized_exit_mitigation_profile")
        if verdict in {
            "NO_REPAIR_IMPROVEMENT",
            "PROBE_HAS_NO_WALK_FORWARD_CONFIRMATION",
        }:
            recommendations.append("if_no_lv31_wf_improvement_stop_threshold_relaxation")
        return list(dict.fromkeys(recommendations))
