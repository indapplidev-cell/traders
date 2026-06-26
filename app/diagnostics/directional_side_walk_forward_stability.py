from __future__ import annotations

from typing import Any

from app.diagnostics.directional_side_ablation_comparator import (
    DirectionalSideAblationComparator,
)


class DirectionalSideWalkForwardStabilityAnalyzer:
    diagnostic_name = "directional_side_walk_forward_stability"
    diagnostic_version = "ml38.10.22"
    SIDE_PROFILES = DirectionalSideAblationComparator.SIDE_PROFILES

    def analyze(self, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        rows = [
            self._candidate_row(candidate)
            for candidate in candidates
            if isinstance(candidate, dict)
        ]
        if not rows:
            return {
                "diagnostic_name": self.diagnostic_name,
                "diagnostic_version": self.diagnostic_version,
                "diagnostic_status": "NO_CANDIDATES",
                "candidate_count": 0,
                "side_profile_counts": self._empty_counts(),
                "stability_by_side_profile": self._empty_best_by_side_profile(),
                "comparison_board": [],
                "long_only_vs_both_stability_delta": self._empty_delta("LONG_ONLY", "BOTH_DIRECTIONS"),
                "suppress_short_vs_both_stability_delta": self._empty_delta("SUPPRESS_SHORT", "BOTH_DIRECTIONS"),
                "short_only_vs_both_stability_delta": self._empty_delta("SHORT_ONLY", "BOTH_DIRECTIONS"),
                "best_research_side_profile": None,
                "best_research_verdict": None,
                "warnings": [],
                "recommendations": [],
            }

        counts = self._empty_counts()
        grouped = {profile: [] for profile in self.SIDE_PROFILES}
        for row in rows:
            counts[row["side_profile"]] += 1
            grouped[row["side_profile"]].append(row)

        best_by_profile = {
            profile: self._best_row(grouped[profile]) for profile in self.SIDE_PROFILES
        }
        both = best_by_profile["BOTH_DIRECTIONS"]
        long_only = best_by_profile["LONG_ONLY"]
        short_only = best_by_profile["SHORT_ONLY"]
        suppress_short = best_by_profile["SUPPRESS_SHORT"]

        research_rows = [row for row in (long_only, short_only, suppress_short) if row]
        best_research = self._best_row(research_rows)
        has_side_candidates = any(
            counts[profile] > 0 for profile in ("LONG_ONLY", "SHORT_ONLY", "SUPPRESS_SHORT")
        )
        warnings: list[str] = []
        recommendations: list[str] = [
            "do_not_accept_side_ablation_without_walk_forward_stability",
            "compare_long_only_and_suppress_short_against_both_direction_baseline",
            "keep_short_side_repair_as_separate_research_track_if_short_only_remains_negative",
        ]
        if has_side_candidates:
            warnings.append("directional_side_ablation_is_research_only")
        if (
            best_research
            and best_research.get("walk_forward_stability_verdict")
            != "CANDIDATE_FOR_NEXT_GRID_RESEARCH_ONLY"
        ):
            warnings.append("best_research_side_profile_not_walk_forward_stable")
        if (
            best_research
            and best_research.get("profit_factor", 0.0)
            and best_research.get("profit_factor", 0.0) > 1.0
        ):
            if (
                best_research.get("walk_forward_stability_verdict")
                != "CANDIDATE_FOR_NEXT_GRID_RESEARCH_ONLY"
            ):
                warnings.append("test_window_profitable_but_walk_forward_unstable")
                recommendations.append("do_not_promote_profitable_test_window_without_fold_signal_stability")
        if (
            short_only
            and self._float_or_none(short_only.get("profit_total_r")) is not None
            and float(short_only["profit_total_r"]) < 0
        ):
            recommendations.append("short_side_is_negative_keep_suppression_research_but_do_not_live_enable")

        status = "COMPLETED" if has_side_candidates else "NO_SIDE_ABLATION_CANDIDATES"
        return {
            "diagnostic_name": self.diagnostic_name,
            "diagnostic_version": self.diagnostic_version,
            "diagnostic_status": status,
            "candidate_count": len(rows),
            "side_profile_counts": counts,
            "stability_by_side_profile": best_by_profile,
            "comparison_board": rows,
            "long_only_vs_both_stability_delta": self._delta(long_only, both, "LONG_ONLY", "BOTH_DIRECTIONS"),
            "suppress_short_vs_both_stability_delta": self._delta(
                suppress_short,
                both,
                "SUPPRESS_SHORT",
                "BOTH_DIRECTIONS",
            ),
            "short_only_vs_both_stability_delta": self._delta(short_only, both, "SHORT_ONLY", "BOTH_DIRECTIONS"),
            "best_research_side_profile": None if best_research is None else best_research.get("side_profile"),
            "best_research_config_id": None if best_research is None else best_research.get("config_id"),
            "best_research_verdict": None
            if best_research is None
            else best_research.get("walk_forward_stability_verdict"),
            "warnings": list(dict.fromkeys(warnings)),
            "recommendations": list(dict.fromkeys(recommendations)),
        }

    def _candidate_row(self, candidate: dict[str, Any]) -> dict[str, Any]:
        comparator_row = DirectionalSideAblationComparator._candidate_row(candidate)
        wf_diag = self._as_dict(candidate.get("walk_forward_profit_diagnostics"))
        wf_signal_summary = self._as_dict(wf_diag.get("fold_signal_summary"))
        wf_profit_summary = self._as_dict(wf_diag.get("fold_profit_summary"))
        fold_snapshots = self._as_list(wf_diag.get("fold_snapshots"))
        fold_count = self._int_or_zero(
            self._first_present(
                wf_diag.get("fold_count"),
                wf_signal_summary.get("fold_count"),
                comparator_row.get("walk_forward_fold_count"),
            )
        )
        folds_with_gate = self._int_or_zero(
            self._first_present(
                wf_signal_summary.get("folds_with_gate"),
                wf_diag.get("folds_with_selected_gate"),
                fold_count,
            )
        )
        total_signal_count = self._int_or_zero(
            self._first_present(
                wf_signal_summary.get("total_resolved_signal_count"),
                comparator_row.get("resolved_signal_count"),
            )
        )
        low_signal_fold_count = self._int_or_zero(
            self._first_present(
                wf_diag.get("low_signal_fold_count"),
                len(self._as_list(wf_diag.get("low_signal_folds"))),
            )
        )
        zero_signal_fold_count = self._int_or_zero(wf_diag.get("zero_signal_fold_count"))
        profitable_fold_count = self._int_or_zero(
            self._first_present(
                wf_diag.get("profitable_fold_count"),
                wf_profit_summary.get("profitable_fold_count"),
            )
        )
        profitable_fold_rate = self._float_or_none(
            self._first_present(
                wf_profit_summary.get("profitable_fold_rate"),
                profitable_fold_count / folds_with_gate if folds_with_gate else None,
            )
        )
        verdict_payload = self._verdict(
            walk_forward_profit_factor=comparator_row.get("walk_forward_profit_factor"),
            walk_forward_total_r=comparator_row.get("walk_forward_total_r"),
            fold_count=fold_count,
            folds_with_gate=folds_with_gate,
            total_resolved_signal_count=total_signal_count,
            low_signal_fold_count=low_signal_fold_count,
            zero_signal_fold_count=zero_signal_fold_count,
            profitable_fold_rate=profitable_fold_rate,
        )
        return {
            **comparator_row,
            "fold_count": fold_count,
            "folds_with_gate": folds_with_gate,
            "total_walk_forward_resolved_signal_count": total_signal_count,
            "zero_signal_fold_count": zero_signal_fold_count,
            "low_signal_fold_count": low_signal_fold_count,
            "min_resolved_signal_count": self._int_or_zero(wf_diag.get("min_resolved_signal_count")),
            "median_resolved_signal_count": self._int_or_none(wf_diag.get("median_resolved_signal_count")),
            "max_resolved_signal_count": self._int_or_zero(wf_diag.get("max_resolved_signal_count")),
            "profitable_fold_count": profitable_fold_count,
            "profitable_fold_rate": profitable_fold_rate,
            "fold_snapshots": fold_snapshots,
            "walk_forward_stability_status": wf_diag.get("walk_forward_stability_status")
            or verdict_payload["status"],
            "walk_forward_stability_verdict": wf_diag.get("walk_forward_stability_verdict")
            or verdict_payload["verdict"],
            "walk_forward_stability_warnings": list(
                dict.fromkeys(
                    self._as_list(wf_diag.get("walk_forward_stability_warnings"))
                    + verdict_payload["warnings"]
                )
            ),
        }

    @staticmethod
    def _verdict(
        *,
        walk_forward_profit_factor: Any,
        walk_forward_total_r: Any,
        fold_count: int,
        folds_with_gate: int,
        total_resolved_signal_count: int,
        low_signal_fold_count: int,
        zero_signal_fold_count: int,
        profitable_fold_rate: float | None,
    ) -> dict[str, Any]:
        pf = DirectionalSideWalkForwardStabilityAnalyzer._float_or_none(walk_forward_profit_factor)
        total_r = DirectionalSideWalkForwardStabilityAnalyzer._float_or_none(walk_forward_total_r)
        warnings: list[str] = []
        if fold_count <= 0 or folds_with_gate <= 0:
            warnings.append("no_walk_forward_gate_evidence")
        if zero_signal_fold_count > 0:
            warnings.append("zero_signal_fold_detected")
        if low_signal_fold_count > 0:
            warnings.append("low_signal_fold_detected")
        if total_resolved_signal_count < 20:
            warnings.append("walk_forward_signal_count_too_low")
        if pf is None:
            warnings.append("walk_forward_profit_factor_missing")
        elif pf <= 1.0:
            warnings.append("walk_forward_profit_factor_not_profitable")
        if total_r is None:
            warnings.append("walk_forward_total_r_missing")
        elif total_r <= 0.0:
            warnings.append("walk_forward_total_r_not_positive")
        if profitable_fold_rate is None or profitable_fold_rate < 0.50:
            warnings.append("profitable_fold_rate_too_low")

        if fold_count <= 0 or folds_with_gate <= 0:
            return {
                "status": "NO_WALK_FORWARD_EVIDENCE",
                "verdict": "REJECT_NO_WALK_FORWARD_EVIDENCE",
                "warnings": warnings,
            }
        if zero_signal_fold_count > 0 or low_signal_fold_count > 0 or total_resolved_signal_count < 20:
            return {
                "status": "LOW_SIGNAL_WALK_FORWARD",
                "verdict": "REJECT_LOW_SIGNAL_WALK_FORWARD",
                "warnings": warnings,
            }
        if (
            pf is not None
            and pf > 1.0
            and total_r is not None
            and total_r > 0.0
            and (profitable_fold_rate or 0.0) >= 0.50
        ):
            return {
                "status": "STABLE_ENOUGH_FOR_RESEARCH",
                "verdict": "CANDIDATE_FOR_NEXT_GRID_RESEARCH_ONLY",
                "warnings": warnings,
            }
        return {
            "status": "WALK_FORWARD_UNSTABLE",
            "verdict": "REJECT_WALK_FORWARD_UNSTABLE",
            "warnings": warnings,
        }

    @classmethod
    def _delta(
        cls,
        left: dict[str, Any] | None,
        right: dict[str, Any] | None,
        left_side_profile: str,
        right_side_profile: str,
    ) -> dict[str, Any]:
        payload = {
            "available": bool(left and right),
            "left_side_profile": left_side_profile,
            "right_side_profile": right_side_profile,
            "left_config_id": left.get("config_id") if left else None,
            "right_config_id": right.get("config_id") if right else None,
            "profit_factor_delta": None,
            "profit_total_r_delta": None,
            "walk_forward_profit_factor_delta": None,
            "walk_forward_total_r_delta": None,
            "total_walk_forward_resolved_signal_count_delta": None,
            "low_signal_fold_count_delta": None,
            "profitable_fold_rate_delta": None,
            "left_verdict": left.get("walk_forward_stability_verdict") if left else None,
            "right_verdict": right.get("walk_forward_stability_verdict") if right else None,
        }
        if not left or not right:
            return payload
        for key, delta_key in (
            ("profit_factor", "profit_factor_delta"),
            ("profit_total_r", "profit_total_r_delta"),
            ("walk_forward_profit_factor", "walk_forward_profit_factor_delta"),
            ("walk_forward_total_r", "walk_forward_total_r_delta"),
            ("total_walk_forward_resolved_signal_count", "total_walk_forward_resolved_signal_count_delta"),
            ("low_signal_fold_count", "low_signal_fold_count_delta"),
            ("profitable_fold_rate", "profitable_fold_rate_delta"),
        ):
            left_value = left.get(key)
            right_value = right.get(key)
            if isinstance(left_value, (int, float)) and isinstance(right_value, (int, float)):
                payload[delta_key] = float(left_value) - float(right_value)
        return payload

    @staticmethod
    def _empty_delta(left_side_profile: str, right_side_profile: str) -> dict[str, Any]:
        return {
            "available": False,
            "left_side_profile": left_side_profile,
            "right_side_profile": right_side_profile,
            "left_config_id": None,
            "right_config_id": None,
            "profit_factor_delta": None,
            "profit_total_r_delta": None,
            "walk_forward_profit_factor_delta": None,
            "walk_forward_total_r_delta": None,
            "total_walk_forward_resolved_signal_count_delta": None,
            "low_signal_fold_count_delta": None,
            "profitable_fold_rate_delta": None,
            "left_verdict": None,
            "right_verdict": None,
        }

    @classmethod
    def _best_row(cls, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not rows:
            return None
        return dict(max(rows, key=cls._row_score))

    @staticmethod
    def _row_score(row: dict[str, Any]) -> float:
        score = 0.0
        verdict = row.get("walk_forward_stability_verdict")
        if verdict == "CANDIDATE_FOR_NEXT_GRID_RESEARCH_ONLY":
            score += 100.0
        elif verdict == "KEEP_FOR_RESEARCH_ONLY":
            score += 50.0
        pf = row.get("walk_forward_profit_factor")
        total_r = row.get("walk_forward_total_r")
        test_pf = row.get("profit_factor")
        test_total_r = row.get("profit_total_r")
        signals = row.get("total_walk_forward_resolved_signal_count") or row.get("resolved_signal_count") or 0
        if isinstance(test_pf, (int, float)) and float(test_pf) > 1.0:
            score += 40.0
        if isinstance(test_total_r, (int, float)):
            if float(test_total_r) > 0.0:
                score += 20.0 + float(test_total_r)
            else:
                score -= 20.0
        for value, weight in ((pf, 20.0), (total_r, 0.5), (test_pf, 5.0), (test_total_r, 0.1)):
            if isinstance(value, (int, float)):
                score += float(value) * weight
        score += min(float(signals), 200.0) * 0.02
        score -= float(row.get("low_signal_fold_count") or 0) * 10.0
        score -= float(row.get("zero_signal_fold_count") or 0) * 20.0
        return score

    @classmethod
    def _empty_counts(cls) -> dict[str, int]:
        return {profile: 0 for profile in cls.SIDE_PROFILES}

    @classmethod
    def _empty_best_by_side_profile(cls) -> dict[str, Any]:
        return {profile: None for profile in cls.SIDE_PROFILES}

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
    def _first_present(*values: Any) -> Any:
        for value in values:
            if value is not None:
                return value
        return None

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _int_or_zero(value: Any) -> int:
        if value is None:
            return 0
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _int_or_none(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
