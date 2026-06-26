from __future__ import annotations

from typing import Any


class DirectionalSideAblationComparator:
    diagnostic_name = "directional_side_ablation_comparator"
    diagnostic_version = "ml38.10.21"
    SIDE_PROFILES = (
        "BOTH_DIRECTIONS",
        "LONG_ONLY",
        "SHORT_ONLY",
        "SUPPRESS_SHORT",
    )

    @classmethod
    def compare(cls, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        normalized_candidates = [
            cls._normalize_candidate(candidate)
            for candidate in candidates
            if isinstance(candidate, dict)
        ]
        if not normalized_candidates:
            return {
                "diagnostic_name": cls.diagnostic_name,
                "diagnostic_version": cls.diagnostic_version,
                "diagnostic_status": "NO_CANDIDATES",
                "candidate_count": 0,
                "side_profile_counts": cls._empty_side_profile_counts(),
                "best_by_side_profile": cls._empty_best_by_side_profile(),
                "comparison_board": [],
                "long_only_vs_both_delta": cls._empty_delta("LONG_ONLY", "BOTH_DIRECTIONS"),
                "suppress_short_vs_both_delta": cls._empty_delta("SUPPRESS_SHORT", "BOTH_DIRECTIONS"),
                "short_only_vs_both_delta": cls._empty_delta("SHORT_ONLY", "BOTH_DIRECTIONS"),
                "warnings": [],
                "recommendations": [],
            }

        side_profile_counts = cls._empty_side_profile_counts()
        grouped_candidates: dict[str, list[dict[str, Any]]] = {
            profile: [] for profile in cls.SIDE_PROFILES
        }
        comparison_board: list[dict[str, Any]] = []
        warnings: list[str] = []
        recommendations = [
            "compare_lv28_against_lv27_lv26_before_acceptance",
            "do_not_accept_long_only_without_multisymbol_confirmation",
            "inspect_short_side_failure_modes_before_live_use",
        ]

        for candidate in normalized_candidates:
            side_profile = candidate["side_profile"]
            side_profile_counts[side_profile] += 1
            grouped_candidates[side_profile].append(candidate)
            comparison_board.append(cls._candidate_row(candidate))

        best_by_side_profile = {
            profile: cls._best_candidate_payload(grouped_candidates[profile])
            for profile in cls.SIDE_PROFILES
        }

        both_best = best_by_side_profile["BOTH_DIRECTIONS"]
        long_best = best_by_side_profile["LONG_ONLY"]
        short_best = best_by_side_profile["SHORT_ONLY"]
        suppress_short_best = best_by_side_profile["SUPPRESS_SHORT"]

        long_only_vs_both_delta = cls._delta(long_best, both_best, "LONG_ONLY", "BOTH_DIRECTIONS")
        suppress_short_vs_both_delta = cls._delta(
            suppress_short_best,
            both_best,
            "SUPPRESS_SHORT",
            "BOTH_DIRECTIONS",
        )
        short_only_vs_both_delta = cls._delta(short_best, both_best, "SHORT_ONLY", "BOTH_DIRECTIONS")

        has_side_ablation = any(
            side_profile_counts[profile] > 0
            for profile in ("LONG_ONLY", "SHORT_ONLY", "SUPPRESS_SHORT")
        )
        improving_research_only = any(
            cls._delta_is_profit_improving(delta)
            for delta in (long_only_vs_both_delta, suppress_short_vs_both_delta)
        )

        if has_side_ablation:
            warnings.append("research_only_side_suppression_not_live_ready")
            recommendations.append("validate_side_filter_on_multi_symbol_before_acceptance")

        if not both_best:
            warnings.append("no_both_direction_comparator_found")

        if long_best and cls._int_or_zero(long_best.get("resolved_signal_count")) < 3:
            warnings.append("long_only_signal_count_too_low")
        if short_best and cls._int_or_zero(short_best.get("resolved_signal_count")) < 3:
            warnings.append("short_only_signal_count_too_low")
        if (
            suppress_short_best
            and cls._float_or_none(suppress_short_best.get("side_filter_removed_signal_rate")) is not None
            and float(suppress_short_best["side_filter_removed_signal_rate"]) >= 0.50
        ):
            warnings.append("suppress_short_removed_too_many_signals")

        if improving_research_only:
            warnings.append("side_ablation_improves_pf_but_may_overfit_symbol_window")
            recommendations.append("if_long_only_wins_add_future_stage_for_short_side_feature_repair")

        if short_best:
            recommendations.append("inspect_short_side_feature_failure_modes")

        diagnostic_status = "COMPLETED" if has_side_ablation else "NO_SIDE_ABLATION_CANDIDATES"

        return {
            "diagnostic_name": cls.diagnostic_name,
            "diagnostic_version": cls.diagnostic_version,
            "diagnostic_status": diagnostic_status,
            "candidate_count": len(normalized_candidates),
            "side_profile_counts": side_profile_counts,
            "best_by_side_profile": best_by_side_profile,
            "comparison_board": comparison_board,
            "long_only_vs_both_delta": long_only_vs_both_delta,
            "suppress_short_vs_both_delta": suppress_short_vs_both_delta,
            "short_only_vs_both_delta": short_only_vs_both_delta,
            "warnings": list(dict.fromkeys(warnings)),
            "recommendations": list(dict.fromkeys(recommendations)),
        }

    @classmethod
    def _normalize_candidate(cls, candidate: dict[str, Any]) -> dict[str, Any]:
        return cls._candidate_row(candidate)

    @classmethod
    def _candidate_row(cls, candidate: dict[str, Any]) -> dict[str, Any]:
        label_config = cls._as_dict(candidate.get("label_config"))
        profit_aware = cls._as_dict(candidate.get("profit_aware_diagnostics"))
        best_gate = cls._as_dict(profit_aware.get("best_gate"))
        walk_forward = cls._as_dict(candidate.get("walk_forward_profit_diagnostics"))
        directional_audit = cls._as_dict(candidate.get("directional_edge_bias_audit"))
        side_summary = cls._as_dict(candidate.get("directional_side_filter_summary"))

        side_profile = cls._side_profile(candidate)
        profit_factor = cls._float_or_none(
            cls._first_present(
                candidate.get("profit_factor"),
                profit_aware.get("profit_factor"),
                profit_aware.get("best_profit_factor"),
                best_gate.get("profit_factor"),
            )
        )
        profit_total_r = cls._float_or_none(
            cls._first_present(
                candidate.get("profit_total_r"),
                profit_aware.get("profit_total_r"),
                profit_aware.get("total_r"),
                best_gate.get("total_r"),
            )
        )
        walk_forward_profit_factor = cls._float_or_none(
            cls._first_present(
                candidate.get("walk_forward_profit_factor"),
                walk_forward.get("walk_forward_profit_factor"),
                walk_forward.get("profit_factor"),
            )
        )
        walk_forward_total_r = cls._float_or_none(
            cls._first_present(
                candidate.get("walk_forward_total_r"),
                candidate.get("walk_forward_global_total_r"),
                walk_forward.get("walk_forward_total_r"),
                walk_forward.get("walk_forward_global_total_r"),
                walk_forward.get("global_total_r"),
                walk_forward.get("total_r"),
            )
        )
        resolved_signal_count = cls._int_or_zero(
            cls._first_present(
                candidate.get("resolved_signal_count"),
                profit_aware.get("resolved_signal_count"),
                best_gate.get("resolved_signal_count"),
                side_summary.get("kept_signal_count"),
                side_summary.get("filtered_signal_count"),
            )
        )
        signal_count = cls._int_or_zero(
            cls._first_present(
                candidate.get("signal_count"),
                profit_aware.get("signal_count"),
                side_summary.get("original_signal_count"),
                resolved_signal_count,
            )
        )
        removed_signal_count = cls._int_or_zero(
            cls._first_present(
                side_summary.get("removed_signal_count"),
                side_summary.get("side_filter_removed_signal_count"),
                0,
            )
        )
        removed_signal_rate = cls._float_or_none(
            cls._first_present(
                side_summary.get("removed_signal_rate"),
                side_summary.get("side_filter_removed_signal_rate"),
            )
        )

        return {
            "config_id": str(candidate.get("config_id") or candidate.get("candidate_id") or ""),
            "candidate_status": candidate.get("candidate_status") or candidate.get("status"),
            "side_profile": side_profile,
            "directional_side_filter_profile": candidate.get("directional_side_filter_profile")
            or label_config.get("directional_side_filter_profile"),
            "allowed_signal_directions": candidate.get("allowed_signal_directions")
            or label_config.get("allowed_signal_directions")
            or [],
            "research_only": side_profile in {"LONG_ONLY", "SHORT_ONLY", "SUPPRESS_SHORT"},
            "profit_factor": profit_factor,
            "profit_total_r": profit_total_r,
            "walk_forward_profit_factor": walk_forward_profit_factor,
            "walk_forward_total_r": walk_forward_total_r,
            "walk_forward_stability_status": cls._as_dict(candidate.get("walk_forward_profit_diagnostics")).get("walk_forward_stability_status"),
            "walk_forward_stability_verdict": cls._as_dict(candidate.get("walk_forward_profit_diagnostics")).get("walk_forward_stability_verdict"),
            "walk_forward_stability_warnings": list(
                cls._as_list(
                    cls._as_dict(candidate.get("walk_forward_profit_diagnostics")).get("walk_forward_stability_warnings")
                )
            ),
            "walk_forward_low_signal_fold_count": cls._int_or_zero(
                cls._as_dict(candidate.get("walk_forward_profit_diagnostics")).get("low_signal_fold_count")
            ),
            "walk_forward_zero_signal_fold_count": cls._int_or_zero(
                cls._as_dict(candidate.get("walk_forward_profit_diagnostics")).get("zero_signal_fold_count")
            ),
            "walk_forward_total_resolved_signal_count": cls._int_or_zero(
                cls._as_dict(candidate.get("walk_forward_profit_diagnostics")).get("total_resolved_signal_count")
            ),
            "signal_count": signal_count,
            "resolved_signal_count": resolved_signal_count,
            "side_filter_removed_signal_count": removed_signal_count,
            "side_filter_removed_signal_rate": removed_signal_rate,
            "direction_balance_ratio": cls._float_or_none(
                cls._first_present(
                    candidate.get("direction_balance_ratio"),
                    directional_audit.get("direction_balance_ratio"),
                )
            ),
            "directional_profit_skew_r": cls._float_or_none(
                cls._first_present(
                    candidate.get("directional_profit_skew_r"),
                    directional_audit.get("directional_profit_skew_r"),
                )
            ),
            "directional_profit_skew_ratio": cls._float_or_none(
                cls._first_present(
                    candidate.get("directional_profit_skew_ratio"),
                    directional_audit.get("directional_profit_skew_ratio"),
                )
            ),
            "long_total_r": cls._float_or_none(
                cls._first_present(candidate.get("long_total_r"), directional_audit.get("long_total_r"))
            ),
            "short_total_r": cls._float_or_none(
                cls._first_present(candidate.get("short_total_r"), directional_audit.get("short_total_r"))
            ),
            "long_avg_r": cls._float_or_none(
                cls._first_present(candidate.get("long_avg_r"), directional_audit.get("long_avg_r"))
            ),
            "short_avg_r": cls._float_or_none(
                cls._first_present(candidate.get("short_avg_r"), directional_audit.get("short_avg_r"))
            ),
        }

    @classmethod
    def _best_candidate_payload(cls, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not candidates:
            return None
        return dict(max(candidates, key=cls._row_score))

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
            "resolved_signal_count_delta": None,
        }
        if not left or not right:
            return payload
        for key, delta_key in (
            ("profit_factor", "profit_factor_delta"),
            ("profit_total_r", "profit_total_r_delta"),
            ("walk_forward_profit_factor", "walk_forward_profit_factor_delta"),
            ("walk_forward_total_r", "walk_forward_total_r_delta"),
            ("resolved_signal_count", "resolved_signal_count_delta"),
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
            "profit_factor_delta": None,
            "profit_total_r_delta": None,
            "walk_forward_profit_factor_delta": None,
            "walk_forward_total_r_delta": None,
            "resolved_signal_count_delta": None,
            "left_config_id": None,
            "right_config_id": None,
        }

    @staticmethod
    def _delta_value(left: Any, right: Any) -> float | None:
        if left is None or right is None:
            return None
        return float(left) - float(right)

    @staticmethod
    def _delta_is_profit_improving(delta: dict[str, Any]) -> bool:
        return bool(
            delta.get("available")
            and delta.get("profit_factor_delta") is not None
            and delta.get("profit_total_r_delta") is not None
            and float(delta["profit_factor_delta"]) > 0.0
            and float(delta["profit_total_r_delta"]) > 0.0
        )

    @classmethod
    def _side_profile(cls, candidate: dict[str, Any]) -> str:
        label_config = cls._as_dict(candidate.get("label_config"))
        profile = cls._first_present(
            candidate.get("directional_side_filter_profile"),
            candidate.get("side_filter_profile"),
            label_config.get("directional_side_filter_profile"),
            label_config.get("side_filter_profile"),
        )
        profile_text = str(profile or "").strip().lower()
        if profile_text in {"long_only_research", "long_only", "long"}:
            return "LONG_ONLY"
        if profile_text in {"short_only_research", "short_only", "short"}:
            return "SHORT_ONLY"
        if profile_text in {"suppress_short_research", "suppress_short", "no_short", "long_no_short"}:
            return "SUPPRESS_SHORT"
        allowed = cls._first_present(
            candidate.get("allowed_signal_directions"),
            label_config.get("allowed_signal_directions"),
        )
        if isinstance(allowed, str):
            allowed_values = {allowed.upper()}
        elif isinstance(allowed, (list, tuple, set)):
            allowed_values = {str(item).upper() for item in allowed}
        else:
            allowed_values = set()
        if allowed_values == {"LONG"}:
            return "LONG_ONLY"
        if allowed_values == {"SHORT"}:
            return "SHORT_ONLY"
        return "BOTH_DIRECTIONS"

    @classmethod
    def _empty_side_profile_counts(cls) -> dict[str, int]:
        return {profile: 0 for profile in cls.SIDE_PROFILES}

    @classmethod
    def _empty_best_by_side_profile(cls) -> dict[str, Any]:
        return {profile: None for profile in cls.SIDE_PROFILES}

    @staticmethod
    def _row_score(row: dict[str, Any]) -> float:
        score = 0.0
        pf = row.get("profit_factor")
        total_r = row.get("profit_total_r")
        wf_pf = row.get("walk_forward_profit_factor")
        wf_r = row.get("walk_forward_total_r")
        resolved = row.get("resolved_signal_count") or 0
        if isinstance(pf, (int, float)):
            score += float(pf) * 10.0
        if isinstance(total_r, (int, float)):
            score += float(total_r) * 0.25
        if isinstance(wf_pf, (int, float)):
            score += float(wf_pf) * 10.0
        if isinstance(wf_r, (int, float)):
            score += float(wf_r) * 0.10
        score += min(float(resolved), 200.0) * 0.01
        return score

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
    def _as_dict(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

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
