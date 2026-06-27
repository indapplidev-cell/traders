from __future__ import annotations

from collections import Counter
from statistics import median
from typing import Any


class GateSelector:
    diagnostic_name = "walk_forward_validation_gate_selection_diagnostics"
    diagnostic_version = "ml38.10.25"
    MAX_DIAGNOSTIC_GATE_PROBES = 6
    MAX_DIAGNOSTIC_PASSED_GATES = 6

    DEFAULT_MIN_SIGNAL_COUNT = 30
    DEFAULT_MIN_PROFIT_FACTOR = 1.0
    DEFAULT_MIN_TOTAL_R = 0.0
    DEFAULT_MIN_EXPECTANCY_R = 0.0

    def select(
        self,
        gate_results: list[dict[str, Any]],
        *,
        directional_side_filter_profile: str | None = None,
        allowed_signal_directions: tuple[str, ...] | list[str] | None = None,
        side_aware_validation_relaxation_enabled: bool = False,
        side_aware_min_validation_signal_count: int | None = None,
        side_aware_min_validation_profit_factor: float | None = None,
        side_aware_min_validation_total_r: float | None = None,
        side_aware_min_validation_expectancy_r: float | None = None,
        side_aware_allow_single_direction_validation: bool = False,
    ) -> dict[str, Any]:
        context = self._selection_context(
            directional_side_filter_profile=directional_side_filter_profile,
            allowed_signal_directions=allowed_signal_directions,
            side_aware_validation_relaxation_enabled=side_aware_validation_relaxation_enabled,
            side_aware_min_validation_signal_count=side_aware_min_validation_signal_count,
            side_aware_min_validation_profit_factor=side_aware_min_validation_profit_factor,
            side_aware_min_validation_total_r=side_aware_min_validation_total_r,
            side_aware_min_validation_expectancy_r=side_aware_min_validation_expectancy_r,
            side_aware_allow_single_direction_validation=side_aware_allow_single_direction_validation,
        )
        passed: list[dict[str, Any]] = []
        probes: list[dict[str, Any]] = []
        for row in gate_results:
            probe = self._probe_gate(row=row, context=context)
            probes.append(probe)
            if probe["passed"]:
                item = {
                    "gate_type": row["gate_type"],
                    "threshold": row["threshold"],
                    "validation_signal_count": row["signal_count"],
                    "validation_profit_factor": row["profit_factor"],
                    "validation_total_r": row["total_r"],
                    "validation_expectancy_r": row["expectancy_r"],
                    "validation_long_count": row["long_count"],
                    "validation_short_count": row["short_count"],
                    "validation_max_drawdown_r": row["max_drawdown_r"],
                    "warnings": list(probe["warnings"]),
                    "validation_gate_selection_mode": context["selection_mode"],
                    "side_aware_validation_relaxation_used": bool(context["relaxation_active"]),
                }
                passed.append(item)

        diagnostics = self._diagnostics(context=context, probes=probes, passed=passed)
        if not passed:
            return {
                "selected_gate": None,
                "reject_reason": "no_validation_gate_passed",
                "diagnostics": diagnostics,
                "validation_gate_selection_diagnostics": diagnostics,
            }

        best = max(
            passed,
            key=lambda item: (
                float(item["validation_profit_factor"]),
                float(item["validation_total_r"]),
                float(item["validation_expectancy_r"]),
                int(item["validation_signal_count"]),
            ),
        )
        return {
            "selected_gate": best,
            "reject_reason": None,
            "diagnostics": diagnostics,
            "validation_gate_selection_diagnostics": diagnostics,
        }

    def _selection_context(
        self,
        *,
        directional_side_filter_profile: str | None,
        allowed_signal_directions: tuple[str, ...] | list[str] | None,
        side_aware_validation_relaxation_enabled: bool,
        side_aware_min_validation_signal_count: int | None,
        side_aware_min_validation_profit_factor: float | None,
        side_aware_min_validation_total_r: float | None,
        side_aware_min_validation_expectancy_r: float | None,
        side_aware_allow_single_direction_validation: bool,
    ) -> dict[str, Any]:
        normalized_directions = self._normalize_allowed_signal_directions(
            allowed_signal_directions=allowed_signal_directions,
            directional_side_filter_profile=directional_side_filter_profile,
        )
        profile = str(directional_side_filter_profile or "both_directions")
        side_profile_active = set(normalized_directions) != {"LONG", "SHORT"}
        relaxation_active = bool(side_aware_validation_relaxation_enabled and side_profile_active)
        return {
            "selection_mode": "side_aware_research_relaxed" if relaxation_active else "classic",
            "directional_side_filter_profile": profile,
            "allowed_signal_directions": normalized_directions,
            "side_profile_active": side_profile_active,
            "relaxation_active": relaxation_active,
            "allow_single_direction_validation": bool(
                side_aware_allow_single_direction_validation and side_profile_active
            ),
            "min_signal_count": int(
                side_aware_min_validation_signal_count
                if relaxation_active and side_aware_min_validation_signal_count is not None
                else self.DEFAULT_MIN_SIGNAL_COUNT
            ),
            "min_profit_factor": float(
                side_aware_min_validation_profit_factor
                if relaxation_active and side_aware_min_validation_profit_factor is not None
                else self.DEFAULT_MIN_PROFIT_FACTOR
            ),
            "min_total_r": float(
                side_aware_min_validation_total_r
                if relaxation_active and side_aware_min_validation_total_r is not None
                else self.DEFAULT_MIN_TOTAL_R
            ),
            "min_expectancy_r": float(
                side_aware_min_validation_expectancy_r
                if relaxation_active and side_aware_min_validation_expectancy_r is not None
                else self.DEFAULT_MIN_EXPECTANCY_R
            ),
        }

    def _probe_gate(self, *, row: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        reasons: list[str] = []
        warnings: list[str] = []
        signal_count = int(row.get("signal_count", 0) or 0)
        long_count = int(row.get("long_count", 0) or 0)
        short_count = int(row.get("short_count", 0) or 0)
        profit_factor = self._float_or_none(row.get("profit_factor"))
        total_r = self._float_or_none(row.get("total_r"))
        expectancy_r = self._float_or_none(row.get("expectancy_r"))
        max_drawdown_r = float(row.get("max_drawdown_r", 0.0) or 0.0)

        if signal_count < int(context["min_signal_count"]):
            reasons.append("signal_count_below_min")
        if profit_factor is None or profit_factor <= float(context["min_profit_factor"]):
            reasons.append("profit_factor_below_min")
        if total_r is None or total_r <= float(context["min_total_r"]):
            reasons.append("total_r_below_min")
        if expectancy_r is None or expectancy_r <= float(context["min_expectancy_r"]):
            reasons.append("expectancy_below_min")

        allowed = set(context["allowed_signal_directions"])
        if context["allow_single_direction_validation"]:
            if "LONG" in allowed and long_count <= 0:
                reasons.append("required_long_signal_missing")
            if "SHORT" in allowed and short_count <= 0:
                reasons.append("required_short_signal_missing")
            if "LONG" not in allowed and long_count > 0:
                warnings.append("validation_has_long_signals_outside_allowed_side")
            if "SHORT" not in allowed and short_count > 0:
                warnings.append("validation_has_short_signals_outside_allowed_side")
        else:
            if long_count <= 0:
                reasons.append("required_long_signal_missing")
            if short_count <= 0:
                warnings.append("no_short_signals")

        if long_count == 0:
            warnings.append("no_long_signals")
        if short_count == 0:
            warnings.append("no_short_signals")

        if total_r is not None and total_r > 0 and max_drawdown_r > abs(total_r) * 2:
            reasons.append("max_drawdown_too_high")

        threshold_deficits = self._threshold_deficits(
            signal_count=signal_count,
            profit_factor=profit_factor,
            total_r=total_r,
            expectancy_r=expectancy_r,
            max_drawdown_r=max_drawdown_r,
            context=context,
            fail_reasons=reasons,
        )
        primary_blocker = self._primary_blocker(reasons)
        repair_hint = self._repair_hint(
            primary_blocker=primary_blocker,
            total_r=total_r,
            context=context,
            fail_reasons=reasons,
        )
        distance_to_pass_score = self._distance_to_pass_score(
            threshold_deficits=threshold_deficits,
            fail_reasons=reasons,
        )

        return {
            "gate_type": row.get("gate_type"),
            "threshold": row.get("threshold"),
            "signal_count": signal_count,
            "long_count": long_count,
            "short_count": short_count,
            "profit_factor": profit_factor,
            "total_r": total_r,
            "expectancy_r": expectancy_r,
            "max_drawdown_r": max_drawdown_r,
            "passed": not reasons,
            "fail_reasons": reasons,
            "warnings": sorted(set(warnings)),
            "selection_mode": context["selection_mode"],
            "threshold_deficits": threshold_deficits,
            "primary_blocker": primary_blocker,
            "repair_hint": repair_hint,
            "distance_to_pass_score": distance_to_pass_score,
            "failed_check_count": len(reasons),
            "effective_min_signal_count": int(context["min_signal_count"]),
            "effective_min_profit_factor": float(context["min_profit_factor"]),
            "effective_min_total_r": float(context["min_total_r"]),
            "effective_min_expectancy_r": float(context["min_expectancy_r"]),
            "side_aware_validation_relaxation_enabled": bool(context["relaxation_active"]),
            "side_aware_allow_single_direction_validation": bool(
                context["allow_single_direction_validation"]
            ),
            "allowed_signal_directions": list(context["allowed_signal_directions"]),
            "directional_side_filter_profile": context["directional_side_filter_profile"],
        }

    def _diagnostics(
        self,
        *,
        context: dict[str, Any],
        probes: list[dict[str, Any]],
        passed: list[dict[str, Any]],
    ) -> dict[str, Any]:
        reason_counts: Counter[str] = Counter(
            reason for probe in probes for reason in probe.get("fail_reasons", [])
        )
        failed = [probe for probe in probes if not probe.get("passed")]
        best_failed_candidates = self._rank_failed_candidates(failed, limit=5)
        total_r_board = self._total_r_failure_board(failed=failed, context=context)
        passed_preview = passed[: self.MAX_DIAGNOSTIC_PASSED_GATES]
        probes_preview = probes[: self.MAX_DIAGNOSTIC_GATE_PROBES]
        return {
            "diagnostic_name": self.diagnostic_name,
            "diagnostic_version": self.diagnostic_version,
            "diagnostic_status": "PASSED_GATE_FOUND" if passed else "NO_GATE_PASSED",
            "selection_mode": context["selection_mode"],
            "directional_side_filter_profile": context["directional_side_filter_profile"],
            "allowed_signal_directions": list(context["allowed_signal_directions"]),
            "side_aware_validation_relaxation_enabled": bool(context["relaxation_active"]),
            "side_aware_allow_single_direction_validation": bool(
                context["allow_single_direction_validation"]
            ),
            "effective_min_signal_count": int(context["min_signal_count"]),
            "effective_min_profit_factor": float(context["min_profit_factor"]),
            "effective_min_total_r": float(context["min_total_r"]),
            "effective_min_expectancy_r": float(context["min_expectancy_r"]),
            "gate_probe_count": len(probes),
            "passed_gate_count": len(passed),
            "failed_gate_count": len(failed),
            "failure_reason_counts": dict(reason_counts),
            "best_failed_gate_by_signal_count": self._best_probe(failed, "signal_count"),
            "best_failed_gate_by_total_r": self._best_probe(failed, "total_r"),
            "best_failed_gate_by_profit_factor": self._best_probe(failed, "profit_factor"),
            "best_failed_gate_candidates": best_failed_candidates,
            "best_failed_gate_by_distance_to_pass": (
                best_failed_candidates[0] if best_failed_candidates else None
            ),
            "total_r_failure_candidate_board": total_r_board,
            "recommended_validation_repair_profile": total_r_board.get(
                "recommended_validation_repair_profile"
            ),
            "total_r_repair_candidate_count": total_r_board.get(
                "total_r_repair_candidate_count",
                0,
            ),
            "total_r_repair_verdict": total_r_board.get("verdict"),
            "passed_gates_total_count": len(passed),
            "passed_gates_truncated": len(passed) > len(passed_preview),
            "passed_gates": passed_preview,
            "gate_probes_total_count": len(probes),
            "gate_probes_truncated": len(probes) > len(probes_preview),
            "gate_probes": probes_preview,
        }

    def _threshold_deficits(
        self,
        *,
        signal_count: int,
        profit_factor: float | None,
        total_r: float | None,
        expectancy_r: float | None,
        max_drawdown_r: float,
        context: dict[str, Any],
        fail_reasons: list[str],
    ) -> dict[str, Any]:
        min_signal_count = int(context["min_signal_count"])
        min_profit_factor = float(context["min_profit_factor"])
        min_total_r = float(context["min_total_r"])
        min_expectancy_r = float(context["min_expectancy_r"])
        signal_count_deficit = max(min_signal_count - signal_count, 0)
        profit_factor_deficit = (
            None if profit_factor is None else max(min_profit_factor - profit_factor, 0.0)
        )
        total_r_deficit = None if total_r is None else max(min_total_r - total_r, 0.0)
        expectancy_r_deficit = (
            None if expectancy_r is None else max(min_expectancy_r - expectancy_r, 0.0)
        )
        max_drawdown_excess = 0.0
        if (
            "max_drawdown_too_high" in fail_reasons
            and total_r is not None
            and total_r > 0
        ):
            max_drawdown_excess = max(max_drawdown_r - abs(total_r) * 2, 0.0)
        return {
            "min_signal_count": min_signal_count,
            "min_profit_factor": min_profit_factor,
            "min_total_r": min_total_r,
            "min_expectancy_r": min_expectancy_r,
            "signal_count_deficit": signal_count_deficit,
            "profit_factor_deficit": profit_factor_deficit,
            "total_r_deficit": total_r_deficit,
            "expectancy_r_deficit": expectancy_r_deficit,
            "max_drawdown_excess": max_drawdown_excess,
            "has_total_r_blocker": "total_r_below_min" in fail_reasons,
            "has_profit_factor_blocker": "profit_factor_below_min" in fail_reasons,
            "has_expectancy_blocker": "expectancy_below_min" in fail_reasons,
            "has_signal_count_blocker": "signal_count_below_min" in fail_reasons,
            "has_drawdown_blocker": "max_drawdown_too_high" in fail_reasons,
        }

    def _primary_blocker(self, fail_reasons: list[str]) -> str | None:
        priority = (
            "required_long_signal_missing",
            "required_short_signal_missing",
            "max_drawdown_too_high",
            "total_r_below_min",
            "profit_factor_below_min",
            "expectancy_below_min",
            "signal_count_below_min",
        )
        for item in priority:
            if item in fail_reasons:
                return item
        return fail_reasons[0] if fail_reasons else None

    def _repair_hint(
        self,
        *,
        primary_blocker: str | None,
        total_r: float | None,
        context: dict[str, Any],
        fail_reasons: list[str],
    ) -> str:
        if not fail_reasons:
            return "gate_passed_no_repair_needed"
        if primary_blocker in {"required_long_signal_missing", "required_short_signal_missing"}:
            return "side_mismatch_not_total_r_repair"
        if primary_blocker == "max_drawdown_too_high":
            return "drawdown_repair_needed_not_threshold_relaxation"
        if primary_blocker == "signal_count_below_min":
            return "signal_count_repair_needed"
        if "total_r_below_min" in fail_reasons:
            if total_r is None:
                return "total_r_missing_not_repairable"
            min_total_r = float(context["min_total_r"])
            deficit = min_total_r - float(total_r)
            if deficit <= 0.75:
                return "total_r_relax_minus_1_25_probe_possible"
            if deficit <= 2.25:
                return "total_r_relax_minus_2_50_probe_possible"
            return "total_r_deficit_too_large_feature_repair_needed"
        if primary_blocker in {"profit_factor_below_min", "expectancy_below_min"}:
            return "pf_expectancy_repair_needed"
        return "unknown_repair_needed"

    def _distance_to_pass_score(
        self,
        *,
        threshold_deficits: dict[str, Any],
        fail_reasons: list[str],
    ) -> float:
        profit_factor_deficit = threshold_deficits.get("profit_factor_deficit")
        total_r_deficit = threshold_deficits.get("total_r_deficit")
        expectancy_r_deficit = threshold_deficits.get("expectancy_r_deficit")
        max_drawdown_excess = threshold_deficits.get("max_drawdown_excess", 0.0)
        score = float(len(fail_reasons) * 10)
        score += float(threshold_deficits.get("signal_count_deficit", 0) or 0) / 10.0
        score += (
            float(profit_factor_deficit) * 10.0
            if profit_factor_deficit is not None
            else 5.0
        )
        score += float(total_r_deficit) if total_r_deficit is not None else 5.0
        score += (
            float(expectancy_r_deficit) * 20.0
            if expectancy_r_deficit is not None
            else 5.0
        )
        score += float(max_drawdown_excess or 0.0)
        return score

    def _rank_failed_candidates(
        self,
        probes: list[dict[str, Any]],
        *,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        failed = [dict(probe) for probe in probes if not probe.get("passed")]
        failed.sort(
            key=lambda row: (
                float(row.get("distance_to_pass_score", 999999.0) or 999999.0),
                -float(row.get("total_r", -999999.0) or -999999.0),
                -float(row.get("profit_factor", -999999.0) or -999999.0),
                -int(row.get("signal_count", 0) or 0),
            )
        )
        return failed[:limit]

    def _total_r_failure_board(
        self,
        *,
        failed: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        total_r_below_min = [
            dict(item)
            for item in failed
            if "total_r_below_min" in self._as_list(item.get("fail_reasons"))
        ]
        repair_candidates = [
            dict(item)
            for item in total_r_below_min
            if item.get("repair_hint")
            in {
                "total_r_relax_minus_1_25_probe_possible",
                "total_r_relax_minus_2_50_probe_possible",
            }
        ]
        best_total_r_gate = self._best_probe(total_r_below_min, "total_r")
        best_distance_to_pass_gate = (
            self._rank_failed_candidates(total_r_below_min, limit=1)[0]
            if total_r_below_min
            else None
        )
        deficits = [
            float(item["threshold_deficits"]["total_r_deficit"])
            for item in total_r_below_min
            if self._as_dict(item.get("threshold_deficits")).get("total_r_deficit") is not None
        ]

        recommended_profile = "NO_TOTAL_R_REPAIR_NEEDED"
        verdict = "NO_TOTAL_R_BLOCKER"
        warnings: list[str] = []
        if total_r_below_min:
            blocker = None if best_distance_to_pass_gate is None else best_distance_to_pass_gate.get(
                "primary_blocker"
            )
            best_total_r_value = self._float_or_none(
                None if best_distance_to_pass_gate is None else best_distance_to_pass_gate.get("total_r")
            )
            if blocker in {
                "required_long_signal_missing",
                "required_short_signal_missing",
                "max_drawdown_too_high",
                "signal_count_below_min",
            }:
                recommended_profile = "NO_THRESHOLD_REPAIR_RECOMMENDED"
                verdict = "NOT_REPAIRABLE_BY_TOTAL_R_RELAXATION"
            elif best_total_r_value is not None and best_total_r_value >= -1.25:
                recommended_profile = "TOTAL_R_RELAX_MINUS_1_25_RESEARCH_ONLY"
                verdict = "TOTAL_R_REPAIR_PROBE_WORTH_TESTING"
            elif best_total_r_value is not None and best_total_r_value >= -2.50:
                recommended_profile = "TOTAL_R_RELAX_MINUS_2_50_RESEARCH_ONLY"
                verdict = "TOTAL_R_REPAIR_PROBE_WORTH_TESTING"
            elif best_total_r_value is not None and best_total_r_value < -2.50:
                recommended_profile = "NO_THRESHOLD_REPAIR_RECOMMENDED"
                verdict = "TOTAL_R_DEFICIT_TOO_LARGE_FEATURE_REPAIR_NEEDED"
            else:
                recommended_profile = "NO_THRESHOLD_REPAIR_RECOMMENDED"
                verdict = "NOT_REPAIRABLE_BY_TOTAL_R_RELAXATION"

        if recommended_profile == "NO_THRESHOLD_REPAIR_RECOMMENDED" and total_r_below_min:
            warnings.append("best_failed_gate_primary_blocker_is_not_total_r_only")
        if verdict == "TOTAL_R_DEFICIT_TOO_LARGE_FEATURE_REPAIR_NEEDED":
            warnings.append("total_r_deficit_too_large_for_threshold_repair")

        return {
            "diagnostic_name": "validation_total_r_failure_board",
            "diagnostic_version": self.diagnostic_version,
            "effective_min_total_r": float(context["min_total_r"]),
            "failed_gate_count": len(failed),
            "total_r_below_min_count": len(total_r_below_min),
            "total_r_repair_candidate_count": len(repair_candidates),
            "best_total_r_gate": best_total_r_gate,
            "best_distance_to_pass_gate": best_distance_to_pass_gate,
            "min_total_r_deficit": min(deficits) if deficits else None,
            "median_total_r_deficit": median(deficits) if deficits else None,
            "max_total_r_deficit": max(deficits) if deficits else None,
            "recommended_validation_repair_profile": recommended_profile,
            "verdict": verdict,
            "warnings": warnings,
        }

    @staticmethod
    def _best_probe(probes: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
        if not probes:
            return None
        return max(
            (dict(probe) for probe in probes),
            key=lambda row: (
                float(row.get(key, 0.0) or 0.0),
                float(row.get("total_r", 0.0) or 0.0),
                int(row.get("signal_count", 0) or 0),
            ),
        )

    @staticmethod
    def _normalize_allowed_signal_directions(
        *,
        allowed_signal_directions: tuple[str, ...] | list[str] | None,
        directional_side_filter_profile: str | None,
    ) -> tuple[str, ...]:
        if allowed_signal_directions:
            normalized = tuple(
                direction
                for direction in (
                    str(item or "").upper().strip() for item in allowed_signal_directions
                )
                if direction in {"LONG", "SHORT"}
            )
            if normalized:
                return tuple(dict.fromkeys(normalized))
        profile = str(directional_side_filter_profile or "").lower().strip()
        if profile in {"long_only_research", "suppress_short_research"}:
            return ("LONG",)
        if profile == "short_only_research":
            return ("SHORT",)
        return ("LONG", "SHORT")

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        try:
            return None if value is None else float(value)
        except (TypeError, ValueError):
            return None

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
    def _as_dict(value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, dict) else {}
