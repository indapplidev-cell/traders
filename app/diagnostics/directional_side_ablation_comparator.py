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
            comparison_board.append(cls._comparison_row(candidate))

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

        side_ablation_available = any(
            side_profile_counts[profile] > 0
            for profile in ("LONG_ONLY", "SHORT_ONLY", "SUPPRESS_SHORT")
        )
        improving_research_only = any(
            cls._delta_is_profit_improving(delta)
            for delta in (long_only_vs_both_delta, suppress_short_vs_both_delta)
        )

        if side_ablation_available:
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

        if not side_ablation_available:
            diagnostic_status = "NO_SIDE_ABLATION_CANDIDATES"
        elif improving_research_only:
            diagnostic_status = "SIDE_ABLATION_IMPROVES_PROFIT_BUT_RESEARCH_ONLY"
        elif long_only_vs_both_delta["available"] or suppress_short_vs_both_delta["available"] or short_only_vs_both_delta["available"]:
            diagnostic_status = "SIDE_ABLATION_AVAILABLE"
        else:
            diagnostic_status = "SIDE_ABLATION_NOT_HELPFUL"

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
        side_filter_summary = cls._as_dict(candidate.get("directional_side_filter_summary"))
        directional_audit = cls._as_dict(candidate.get("directional_edge_bias_audit"))
        directional_side_filter_profile = candidate.get("directional_side_filter_profile")
        allowed_signal_directions = tuple(candidate.get("allowed_signal_directions") or ())
        walk_forward_total_r = cls._float_or_none(
            candidate.get("walk_forward_total_r", candidate.get("walk_forward_global_total_r"))
        )
        resolved_signal_count = cls._int_or_zero(
            candidate.get("resolved_signal_count", candidate.get("signal_count"))
        )
        return {
            "config_id": candidate.get("config_id"),
            "candidate_status": candidate.get("candidate_status"),
            "status": candidate.get("status"),
            "profit_factor": cls._float_or_none(candidate.get("profit_factor")),
            "profit_total_r": cls._float_or_none(candidate.get("profit_total_r")),
            "walk_forward_profit_factor": cls._float_or_none(candidate.get("walk_forward_profit_factor")),
            "walk_forward_total_r": walk_forward_total_r,
            "resolved_signal_count": resolved_signal_count,
            "signal_count": cls._int_or_zero(candidate.get("signal_count")),
            "directional_side_filter_profile": directional_side_filter_profile,
            "allowed_signal_directions": list(allowed_signal_directions),
            "directional_side_filter_summary": side_filter_summary,
            "directional_edge_bias_audit": directional_audit,
            "long_total_r": cls._float_or_none(candidate.get("long_total_r", directional_audit.get("long_total_r"))),
            "short_total_r": cls._float_or_none(candidate.get("short_total_r", directional_audit.get("short_total_r"))),
            "long_avg_r": cls._float_or_none(candidate.get("long_avg_r", directional_audit.get("long_avg_r"))),
            "short_avg_r": cls._float_or_none(candidate.get("short_avg_r", directional_audit.get("short_avg_r"))),
            "direction_balance_ratio": cls._float_or_none(
                candidate.get("direction_balance_ratio", directional_audit.get("direction_balance_ratio"))
            ),
            "directional_profit_skew_r": cls._float_or_none(
                candidate.get("directional_profit_skew_r", directional_audit.get("directional_profit_skew_r"))
            ),
            "directional_profit_skew_ratio": cls._float_or_none(
                candidate.get(
                    "directional_profit_skew_ratio",
                    directional_audit.get("directional_profit_skew_ratio"),
                )
            ),
            "side_filter_removed_signal_count": cls._int_or_zero(
                side_filter_summary.get("removed_signal_count")
            ),
            "side_filter_removed_signal_rate": cls._float_or_none(
                side_filter_summary.get("removed_signal_rate")
            ),
            "research_only": bool(side_filter_summary.get("research_only", False)),
            "side_profile": cls._side_profile(directional_side_filter_profile),
        }

    @staticmethod
    def _comparison_row(candidate: dict[str, Any]) -> dict[str, Any]:
        return {
            "config_id": candidate.get("config_id"),
            "side_profile": candidate.get("side_profile"),
            "candidate_status": candidate.get("candidate_status"),
            "profit_factor": candidate.get("profit_factor"),
            "profit_total_r": candidate.get("profit_total_r"),
            "walk_forward_profit_factor": candidate.get("walk_forward_profit_factor"),
            "walk_forward_total_r": candidate.get("walk_forward_total_r"),
            "resolved_signal_count": candidate.get("resolved_signal_count"),
            "direction_balance_ratio": candidate.get("direction_balance_ratio"),
            "long_total_r": candidate.get("long_total_r"),
            "short_total_r": candidate.get("short_total_r"),
            "long_avg_r": candidate.get("long_avg_r"),
            "short_avg_r": candidate.get("short_avg_r"),
            "directional_profit_skew_r": candidate.get("directional_profit_skew_r"),
            "directional_profit_skew_ratio": candidate.get("directional_profit_skew_ratio"),
            "side_filter_removed_signal_count": candidate.get("side_filter_removed_signal_count"),
            "side_filter_removed_signal_rate": candidate.get("side_filter_removed_signal_rate"),
            "research_only": candidate.get("research_only"),
        }

    @classmethod
    def _best_candidate_payload(cls, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not candidates:
            return None
        best = max(
            candidates,
            key=lambda item: (
                cls._sortable_float(item.get("profit_factor")),
                cls._sortable_float(item.get("profit_total_r")),
                cls._sortable_float(item.get("walk_forward_profit_factor")),
                cls._int_or_zero(item.get("resolved_signal_count")),
            ),
        )
        return {
            "config_id": best.get("config_id"),
            "candidate_status": best.get("candidate_status"),
            "profit_factor": best.get("profit_factor"),
            "profit_total_r": best.get("profit_total_r"),
            "walk_forward_profit_factor": best.get("walk_forward_profit_factor"),
            "walk_forward_total_r": best.get("walk_forward_total_r"),
            "resolved_signal_count": best.get("resolved_signal_count"),
            "signal_count": best.get("signal_count"),
            "directional_side_filter_profile": best.get("directional_side_filter_profile"),
            "allowed_signal_directions": list(best.get("allowed_signal_directions") or []),
            "direction_balance_ratio": best.get("direction_balance_ratio"),
            "long_total_r": best.get("long_total_r"),
            "short_total_r": best.get("short_total_r"),
            "long_avg_r": best.get("long_avg_r"),
            "short_avg_r": best.get("short_avg_r"),
            "directional_profit_skew_r": best.get("directional_profit_skew_r"),
            "directional_profit_skew_ratio": best.get("directional_profit_skew_ratio"),
            "side_filter_removed_signal_count": best.get("side_filter_removed_signal_count"),
            "side_filter_removed_signal_rate": best.get("side_filter_removed_signal_rate"),
            "research_only": best.get("research_only"),
            "side_profile": best.get("side_profile"),
        }

    @classmethod
    def _delta(
        cls,
        left: dict[str, Any] | None,
        right: dict[str, Any] | None,
        left_side_profile: str,
        right_side_profile: str,
    ) -> dict[str, Any]:
        if not left or not right:
            return cls._empty_delta(left_side_profile, right_side_profile)
        return {
            "available": True,
            "left_side_profile": left_side_profile,
            "right_side_profile": right_side_profile,
            "profit_factor_delta": cls._delta_value(left.get("profit_factor"), right.get("profit_factor")),
            "profit_total_r_delta": cls._delta_value(left.get("profit_total_r"), right.get("profit_total_r")),
            "walk_forward_profit_factor_delta": cls._delta_value(
                left.get("walk_forward_profit_factor"),
                right.get("walk_forward_profit_factor"),
            ),
            "walk_forward_total_r_delta": cls._delta_value(
                left.get("walk_forward_total_r"),
                right.get("walk_forward_total_r"),
            ),
            "resolved_signal_count_delta": cls._int_or_zero(left.get("resolved_signal_count")) - cls._int_or_zero(
                right.get("resolved_signal_count")
            ),
            "left_config_id": left.get("config_id"),
            "right_config_id": right.get("config_id"),
        }

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
    def _side_profile(cls, directional_side_filter_profile: Any) -> str:
        profile = str(directional_side_filter_profile or "").strip().lower()
        if profile == "long_only_research":
            return "LONG_ONLY"
        if profile == "short_only_research":
            return "SHORT_ONLY"
        if profile == "suppress_short_research":
            return "SUPPRESS_SHORT"
        return "BOTH_DIRECTIONS"

    @classmethod
    def _empty_side_profile_counts(cls) -> dict[str, int]:
        return {profile: 0 for profile in cls.SIDE_PROFILES}

    @classmethod
    def _empty_best_by_side_profile(cls) -> dict[str, Any]:
        return {profile: None for profile in cls.SIDE_PROFILES}

    @staticmethod
    def _sortable_float(value: Any) -> float:
        if value is None:
            return float("-inf")
        return float(value)

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        return None if value is None else float(value)

    @staticmethod
    def _int_or_zero(value: Any) -> int:
        return int(value or 0)

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, dict) else {}
