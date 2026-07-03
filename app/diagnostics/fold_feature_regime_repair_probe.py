from __future__ import annotations

from typing import Any


class FoldFeatureRegimeRepairProbe:
    diagnostic_name = "fold_feature_regime_repair_probe"
    diagnostic_version = "ml38.10.29"

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, dict) else {}

    @classmethod
    def _count_map(cls, value: Any) -> dict[str, int]:
        mapping = cls._as_dict(value)
        cleaned: dict[str, int] = {}
        for key, raw_count in mapping.items():
            text_key = str(key)
            if not text_key or text_key.startswith("_"):
                continue
            try:
                count = int(raw_count)
            except (TypeError, ValueError):
                continue
            cleaned[text_key] = cleaned.get(text_key, 0) + count
        return cleaned

    @classmethod
    def _summary_or_row_counts(
        cls,
        row: dict[str, Any],
        summary: dict[str, Any],
        *keys: str,
    ) -> dict[str, int]:
        for key in keys:
            counts = cls._count_map(summary.get(key))
            if counts:
                return counts
        for key in keys:
            counts = cls._count_map(row.get(key))
            if counts:
                return counts
        return {}

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

    @staticmethod
    def _empty_contribution_stats() -> dict[str, Any]:
        return {
            "signal_count": 0,
            "total_r": 0.0,
            "positive_r": 0.0,
            "negative_r": 0.0,
            "win_count": 0,
            "loss_count": 0,
            "neutral_count": 0,
            "avg_r": None,
            "win_rate": None,
        }

    @classmethod
    def _contribution_stats(cls, value: Any) -> dict[str, Any]:
        payload = cls._as_dict(value)
        stats = dict(cls._empty_contribution_stats())
        stats["signal_count"] = int(payload.get("signal_count", 0) or 0)
        stats["total_r"] = float(payload.get("total_r", 0.0) or 0.0)
        stats["positive_r"] = float(payload.get("positive_r", 0.0) or 0.0)
        stats["negative_r"] = float(payload.get("negative_r", 0.0) or 0.0)
        stats["win_count"] = int(payload.get("win_count", 0) or 0)
        stats["loss_count"] = int(payload.get("loss_count", 0) or 0)
        stats["neutral_count"] = int(payload.get("neutral_count", 0) or 0)
        if stats["signal_count"] > 0:
            stats["avg_r"] = stats["total_r"] / stats["signal_count"]
            stats["win_rate"] = stats["win_count"] / stats["signal_count"]
        return stats

    @classmethod
    def _merge_contribution_stats(
        cls,
        target: dict[str, dict[str, Any]],
        source: dict[str, Any],
    ) -> None:
        for key, raw_stats in cls._as_dict(source).items():
            text_key = str(key)
            if not text_key or text_key.startswith("_"):
                continue
            normalized = cls._contribution_stats(raw_stats)
            slot = target.setdefault(text_key, cls._empty_contribution_stats())
            slot["signal_count"] = int(slot.get("signal_count", 0) or 0) + int(
                normalized.get("signal_count", 0) or 0
            )
            slot["total_r"] = float(slot.get("total_r", 0.0) or 0.0) + float(
                normalized.get("total_r", 0.0) or 0.0
            )
            slot["positive_r"] = float(slot.get("positive_r", 0.0) or 0.0) + float(
                normalized.get("positive_r", 0.0) or 0.0
            )
            slot["negative_r"] = float(slot.get("negative_r", 0.0) or 0.0) + float(
                normalized.get("negative_r", 0.0) or 0.0
            )
            slot["win_count"] = int(slot.get("win_count", 0) or 0) + int(
                normalized.get("win_count", 0) or 0
            )
            slot["loss_count"] = int(slot.get("loss_count", 0) or 0) + int(
                normalized.get("loss_count", 0) or 0
            )
            slot["neutral_count"] = int(slot.get("neutral_count", 0) or 0) + int(
                normalized.get("neutral_count", 0) or 0
            )

    @classmethod
    def _merge_nested_count_map(
        cls,
        target: dict[str, dict[str, int]],
        source: Any,
    ) -> None:
        for outer_key, raw_inner in cls._as_dict(source).items():
            text_outer = str(outer_key)
            if not text_outer or text_outer.startswith("_"):
                continue
            inner_counts = cls._count_map(raw_inner)
            if not inner_counts:
                continue
            slot = target.setdefault(text_outer, {})
            for inner_key, count in inner_counts.items():
                slot[inner_key] = slot.get(inner_key, 0) + count

    @classmethod
    def _merge_rule_metadata_map(
        cls,
        target: dict[str, Any],
        source: Any,
    ) -> None:
        for key, value in cls._as_dict(source).items():
            text_key = str(key)
            if not text_key or text_key.startswith("_"):
                continue
            target.setdefault(text_key, value)

    @classmethod
    def _merge_nested_contribution_stats_map(
        cls,
        target: dict[str, dict[str, dict[str, Any]]],
        source: Any,
    ) -> None:
        for outer_key, raw_inner in cls._as_dict(source).items():
            text_outer = str(outer_key)
            if not text_outer or text_outer.startswith("_"):
                continue
            slot = target.setdefault(text_outer, {})
            for inner_key, raw_stats in cls._as_dict(raw_inner).items():
                text_inner = str(inner_key)
                if not text_inner or text_inner.startswith("_"):
                    continue
                normalized = cls._contribution_stats(raw_stats)
                inner_slot = slot.setdefault(text_inner, cls._empty_contribution_stats())
                inner_slot["signal_count"] = int(
                    inner_slot.get("signal_count", 0) or 0
                ) + int(normalized.get("signal_count", 0) or 0)
                inner_slot["total_r"] = float(
                    inner_slot.get("total_r", 0.0) or 0.0
                ) + float(normalized.get("total_r", 0.0) or 0.0)
                inner_slot["positive_r"] = float(
                    inner_slot.get("positive_r", 0.0) or 0.0
                ) + float(normalized.get("positive_r", 0.0) or 0.0)
                inner_slot["negative_r"] = float(
                    inner_slot.get("negative_r", 0.0) or 0.0
                ) + float(normalized.get("negative_r", 0.0) or 0.0)
                inner_slot["win_count"] = int(
                    inner_slot.get("win_count", 0) or 0
                ) + int(normalized.get("win_count", 0) or 0)
                inner_slot["loss_count"] = int(
                    inner_slot.get("loss_count", 0) or 0
                ) + int(normalized.get("loss_count", 0) or 0)
                inner_slot["neutral_count"] = int(
                    inner_slot.get("neutral_count", 0) or 0
                ) + int(normalized.get("neutral_count", 0) or 0)

    @classmethod
    def _finalize_contribution_stats(cls, value: Any) -> dict[str, Any]:
        stats = cls._contribution_stats(value)
        if stats["signal_count"] <= 0:
            stats["avg_r"] = None
            stats["win_rate"] = None
        return stats

    @classmethod
    def _finalize_contribution_stats_map(
        cls,
        mapping: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        return {
            key: cls._finalize_contribution_stats(value)
            for key, value in sorted(mapping.items())
            if int(value.get("signal_count", 0) or 0) > 0
        }

    @classmethod
    def _finalize_nested_contribution_stats_map(
        cls,
        mapping: dict[str, dict[str, dict[str, Any]]],
    ) -> dict[str, dict[str, dict[str, Any]]]:
        finalized: dict[str, dict[str, dict[str, Any]]] = {}
        for outer_key, inner_map in sorted(mapping.items()):
            cleaned: dict[str, dict[str, Any]] = {}
            for inner_key, stats in sorted(inner_map.items()):
                cleaned[inner_key] = cls._finalize_contribution_stats(stats)
            if cleaned:
                finalized[outer_key] = cleaned
        return finalized

    @classmethod
    def _contribution_effect_label(
        cls,
        removed_outcome: dict[str, Any],
        passed_outcome: dict[str, Any],
        *,
        removed_count: int,
    ) -> str:
        if removed_count <= 0:
            return "NO_REMOVALS"
        if (
            int(removed_outcome.get("signal_count", 0) or 0) <= 0
            and int(passed_outcome.get("signal_count", 0) or 0) <= 0
        ):
            return "OUTCOME_UNAVAILABLE"
        removed_total_r = float(removed_outcome.get("total_r", 0.0) or 0.0)
        if removed_total_r < 0:
            return "REMOVAL_HELPFUL"
        if removed_total_r > 0:
            return "REMOVAL_HARMFUL"
        return "REMOVAL_NEUTRAL"

    @classmethod
    def _conditional_regime_ablation_board(
        cls,
        *,
        eligible_counts: dict[str, int],
        blocked_counts: dict[str, int],
        passed_counts: dict[str, int],
        metric_failure_counts_by_rule: dict[str, dict[str, int]],
        removed_outcome_by_rule: dict[str, dict[str, Any]],
        passed_outcome_by_rule: dict[str, dict[str, Any]],
        metric_logic_by_rule: dict[str, str] | None = None,
        required_metric_failure_count_by_rule: dict[str, int] | None = None,
        metric_condition_count_by_rule: dict[str, int] | None = None,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        rule_ids = sorted(
            set(eligible_counts)
            | set(blocked_counts)
            | set(passed_counts)
            | set(metric_failure_counts_by_rule)
            | set(removed_outcome_by_rule)
            | set(passed_outcome_by_rule)
        )
        for rule_id in rule_ids:
            eligible_count = int(eligible_counts.get(rule_id, 0) or 0)
            removed_count = int(blocked_counts.get(rule_id, 0) or 0)
            passed_count = int(passed_counts.get(rule_id, 0) or 0)
            removed_outcome = cls._finalize_contribution_stats(
                removed_outcome_by_rule.get(rule_id)
            )
            passed_outcome = cls._finalize_contribution_stats(
                passed_outcome_by_rule.get(rule_id)
            )
            rows.append(
                {
                    "rule_id": rule_id,
                    "metric_logic": (metric_logic_by_rule or {}).get(rule_id),
                    "eligible_count": eligible_count,
                    "removed_count": removed_count,
                    "passed_count": passed_count,
                    "removal_rate": (
                        removed_count / eligible_count if eligible_count > 0 else None
                    ),
                    "required_metric_failure_count": (
                        required_metric_failure_count_by_rule or {}
                    ).get(rule_id),
                    "metric_condition_count": (
                        metric_condition_count_by_rule or {}
                    ).get(rule_id),
                    "removed_outcome": removed_outcome,
                    "passed_outcome": passed_outcome,
                    "removed_total_r": removed_outcome.get("total_r"),
                    "passed_total_r": passed_outcome.get("total_r"),
                    "metric_failure_counts": cls._count_map(
                        metric_failure_counts_by_rule.get(rule_id)
                    ),
                    "effect_label": cls._contribution_effect_label(
                        removed_outcome,
                        passed_outcome,
                        removed_count=removed_count,
                    ),
                }
            )
        return sorted(
            rows,
            key=lambda row: (
                -int(row.get("removed_count", 0) or 0),
                -int(row.get("eligible_count", 0) or 0),
                str(row.get("rule_id") or ""),
            ),
        )

    @classmethod
    def _conditional_regime_metric_overlap_board(
        cls,
        *,
        eligible_counts: dict[str, int],
        blocked_counts: dict[str, int],
        failure_count_distribution_by_rule: dict[str, dict[str, int]],
        observed_metric_failure_counts_by_rule: dict[str, dict[str, int]],
        metric_pair_failure_counts_by_rule: dict[str, dict[str, int]],
        outcome_by_failure_count: dict[str, dict[str, dict[str, Any]]],
        metric_logic_by_rule: dict[str, str] | None = None,
        required_metric_failure_count_by_rule: dict[str, int] | None = None,
        metric_condition_count_by_rule: dict[str, int] | None = None,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        rule_ids = sorted(
            set(eligible_counts)
            | set(blocked_counts)
            | set(failure_count_distribution_by_rule)
            | set(observed_metric_failure_counts_by_rule)
            | set(metric_pair_failure_counts_by_rule)
            | set(outcome_by_failure_count)
        )

        for rule_id in rule_ids:
            eligible_count = int(eligible_counts.get(rule_id, 0) or 0)
            actual_removed_count = int(blocked_counts.get(rule_id, 0) or 0)
            distribution = {
                str(key): int(value or 0)
                for key, value in cls._count_map(
                    failure_count_distribution_by_rule.get(rule_id)
                ).items()
            }
            failed_0_count = int(distribution.get("failed_0", 0) or 0)
            failed_1_count = int(distribution.get("failed_1", 0) or 0)
            failed_2_plus_count = int(distribution.get("failed_2_plus", 0) or 0)
            required = int(
                (required_metric_failure_count_by_rule or {}).get(rule_id, 0) or 0
            )
            metric_condition_count = int(
                (metric_condition_count_by_rule or {}).get(rule_id, 0) or 0
            )
            metric_logic = (metric_logic_by_rule or {}).get(rule_id)

            if eligible_count <= 0:
                overlap_status = "NO_ELIGIBLE_SIGNALS"
                bottleneck_label = "regime_context_not_seen"
            elif actual_removed_count > 0:
                overlap_status = "REMOVALS_ACTIVE"
                bottleneck_label = "rule_removed_signals"
            elif failed_2_plus_count > 0:
                overlap_status = "TWO_METRIC_OVERLAP_WITHOUT_REMOVAL"
                bottleneck_label = "check_metric_logic_or_required_count"
            elif failed_1_count > 0:
                overlap_status = "ONLY_ONE_METRIC_FAILURES"
                bottleneck_label = "conditions_too_strict_or_metrics_do_not_overlap"
            else:
                overlap_status = "NO_METRIC_FAILURES"
                bottleneck_label = "thresholds_too_loose_or_features_do_not_cross_thresholds"

            rows.append(
                {
                    "rule_id": rule_id,
                    "eligible_count": eligible_count,
                    "actual_removed_count": actual_removed_count,
                    "metric_logic": metric_logic,
                    "required_metric_failure_count": required,
                    "metric_condition_count": metric_condition_count,
                    "failed_0_count": failed_0_count,
                    "failed_1_count": failed_1_count,
                    "failed_2_plus_count": failed_2_plus_count,
                    "failure_count_distribution": distribution,
                    "observed_metric_failure_counts": cls._count_map(
                        observed_metric_failure_counts_by_rule.get(rule_id)
                    ),
                    "metric_pair_failure_counts": cls._count_map(
                        metric_pair_failure_counts_by_rule.get(rule_id)
                    ),
                    "outcome_by_failure_count": cls._as_dict(
                        outcome_by_failure_count.get(rule_id)
                    ),
                    "metric_overlap_status": overlap_status,
                    "bottleneck_label": bottleneck_label,
                }
            )

        return sorted(
            rows,
            key=lambda row: (
                -int(row.get("eligible_count", 0) or 0),
                str(row.get("rule_id") or ""),
            ),
        )

    @classmethod
    def _per_regime_contribution_board(
        cls,
        *,
        removed_outcome_by_primary_regime: dict[str, dict[str, Any]],
        passed_outcome_by_primary_regime: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        regime_keys = sorted(
            set(removed_outcome_by_primary_regime) | set(passed_outcome_by_primary_regime)
        )
        for regime in regime_keys:
            removed_outcome = cls._finalize_contribution_stats(
                removed_outcome_by_primary_regime.get(regime)
            )
            passed_outcome = cls._finalize_contribution_stats(
                passed_outcome_by_primary_regime.get(regime)
            )
            rows.append(
                {
                    "market_regime": regime,
                    "removed_outcome": removed_outcome,
                    "passed_outcome": passed_outcome,
                    "removed_signal_count": removed_outcome.get("signal_count"),
                    "removed_total_r": removed_outcome.get("total_r"),
                    "passed_signal_count": passed_outcome.get("signal_count"),
                    "passed_total_r": passed_outcome.get("total_r"),
                    "effect_label": cls._contribution_effect_label(
                        removed_outcome,
                        passed_outcome,
                        removed_count=int(removed_outcome.get("signal_count", 0) or 0),
                    ),
                }
            )
        return sorted(
            rows,
            key=lambda row: (
                -(
                    int(row.get("removed_signal_count", 0) or 0)
                    + int(row.get("passed_signal_count", 0) or 0)
                ),
                str(row.get("market_regime") or ""),
            ),
        )

    def analyze(self, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        rows = [self._candidate_row(item) for item in candidates]
        feature_rows = [
            row
            for row in rows
            if row.get("fold_repair_feature_filter_enabled")
            or str(row.get("config_id") or "").lower().startswith(("lv32_", "lv33_"))
        ]
        date_rows = [
            row
            for row in rows
            if row.get("fold_repair_time_slice_blackout_enabled")
            or str(row.get("config_id") or "").lower().startswith("lv31_")
        ]
        feature_compact = self._top_rows(feature_rows, limit=5)
        date_compact = self._top_rows(date_rows, limit=5)
        best_feature = feature_compact[0] if feature_compact else {}
        best_date = date_compact[0] if date_compact else {}
        verdict = self._verdict(best_feature=best_feature, best_date=best_date)
        feature_filter_diagnostics = self._feature_filter_diagnostics(feature_rows)
        verdict_detail = self._verdict_detail(
            best_feature=best_feature,
            best_date=best_date,
            feature_filter_diagnostics=feature_filter_diagnostics,
        )

        return {
            "diagnostic_name": self.diagnostic_name,
            "diagnostic_version": self.diagnostic_version,
            "diagnostic_status": (
                "OK"
                if feature_rows or date_rows
                else "NO_FOLD_REPAIR_PROBE_CANDIDATES"
            ),
            "candidate_count": len(rows),
            "feature_regime_probe_candidate_count": len(feature_rows),
            "date_blackout_probe_candidate_count": len(date_rows),
            "best_feature_regime_probe": best_feature,
            "best_date_blackout_probe": best_date,
            "best_feature_regime_by_walk_forward_total_r": feature_compact,
            "best_date_blackout_by_walk_forward_total_r": date_compact,
            "verdict": verdict,
            "verdict_detail": verdict_detail,
            "feature_filter_diagnostics": feature_filter_diagnostics,
            "warnings": [
                "research_only_probe_not_live_ready",
                "do_not_accept_lv32",
                "date_blackout_replacement_must_be_validated_out_of_sample",
            ],
            "recommended_next_stage": (
                "validate_feature_regime_repair_on_longer_history_and_multi_symbol"
            ),
        }

    def _candidate_row(self, candidate: dict[str, Any]) -> dict[str, Any]:
        profit_diag = self._as_dict(candidate.get("profit_aware_diagnostics"))
        profit_summary = self._as_dict(profit_diag.get("summary"))
        profit_best_gate = self._as_dict(profit_diag.get("best_gate"))
        feature_summary = self._as_dict(
            candidate.get("fold_feature_regime_filter_summary")
            or profit_diag.get("fold_feature_regime_filter_summary")
            or profit_summary.get("fold_feature_regime_filter_summary")
            or profit_best_gate.get("fold_feature_regime_filter_summary")
        )
        primary_removed_counts = self._count_map(
            feature_summary.get("primary_removed_counts_by_reason")
            or feature_summary.get("removed_counts_by_reason")
        )
        matched_removed_counts = self._count_map(
            feature_summary.get("matched_removed_counts_by_reason")
        )
        removed_counts_by_date = self._count_map(
            feature_summary.get("removed_counts_by_date")
        )
        passed_counts_by_date = self._count_map(
            feature_summary.get("passed_counts_by_date")
        )
        removed_counts_by_regime = self._count_map(
            feature_summary.get("removed_counts_by_regime")
        )
        passed_counts_by_regime = self._count_map(
            feature_summary.get("passed_counts_by_regime")
        )
        missing_feature_counts = self._count_map(
            feature_summary.get("missing_feature_counts")
        )
        blackout_summary = self._as_dict(
            candidate.get("fold_repair_probe_diagnostics")
            or candidate.get("fold_time_slice_blackout_summary")
            or profit_diag.get("fold_time_slice_blackout_summary")
            or profit_summary.get("fold_time_slice_blackout_summary")
            or profit_best_gate.get("fold_time_slice_blackout_summary")
        )
        removed_count = self._float_or_none(feature_summary.get("removed_signal_count"))
        input_count = self._float_or_none(feature_summary.get("input_signal_count"))
        target_input_count = self._float_or_none(feature_summary.get("target_date_input_count"))
        target_removed_count = self._float_or_none(feature_summary.get("target_date_removed_count"))
        target_passed_count = self._float_or_none(feature_summary.get("target_date_passed_count"))
        return {
            "symbol": candidate.get("symbol"),
            "config_id": candidate.get("config_id"),
            "candidate_id": candidate.get("candidate_id"),
            "candidate_status": candidate.get("candidate_status"),
            "fold_repair_probe_profile": candidate.get("fold_repair_probe_profile"),
            "fold_repair_feature_filter_enabled": bool(
                candidate.get("fold_repair_feature_filter_enabled", False)
            ),
            "fold_repair_feature_filter_profile": candidate.get(
                "fold_repair_feature_filter_profile"
            ),
            "fold_repair_feature_filter_rules": self._as_dict(
                candidate.get("fold_repair_feature_filter_rules")
            ),
            "fold_feature_regime_filter_summary": feature_summary,
            "feature_filter_removed_signal_count": removed_count,
            "feature_filter_input_signal_count": input_count,
            "feature_filter_removed_ratio": self._float_or_none(
                feature_summary.get("removed_ratio")
            ),
            "target_date_input_count": target_input_count,
            "target_date_removed_count": target_removed_count,
            "target_date_passed_count": target_passed_count,
            "primary_removed_counts_by_reason": primary_removed_counts,
            "matched_removed_counts_by_reason": matched_removed_counts,
            "removed_counts_by_date": removed_counts_by_date,
            "passed_counts_by_date": passed_counts_by_date,
            "removed_counts_by_regime": removed_counts_by_regime,
            "passed_counts_by_regime": passed_counts_by_regime,
            "missing_feature_counts": missing_feature_counts,
            "feature_filter_warnings": self._as_list(feature_summary.get("warnings")),
            "fold_repair_time_slice_blackout_enabled": bool(
                candidate.get("fold_repair_time_slice_blackout_enabled", False)
            ),
            "fold_time_slice_blackout_summary": blackout_summary,
            "profit_factor": self._float_or_none(candidate.get("profit_factor")),
            "profit_total_r": self._float_or_none(candidate.get("profit_total_r")),
            "walk_forward_profit_factor": self._float_or_none(
                candidate.get("walk_forward_profit_factor")
            ),
            "walk_forward_total_r": self._float_or_none(
                candidate.get("walk_forward_total_r", candidate.get("walk_forward_global_total_r"))
            ),
            "failed_gates": self._as_list(candidate.get("failed_gates")),
        }

    def _top_rows(self, rows: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
        ranked = sorted(
            rows,
            key=lambda row: (
                self._float_or_none(row.get("walk_forward_total_r")) is not None,
                self._float_or_none(row.get("walk_forward_total_r")) or float("-inf"),
                self._float_or_none(row.get("profit_total_r")) or float("-inf"),
            ),
            reverse=True,
        )
        compact: list[dict[str, Any]] = []
        for row in ranked[:limit]:
            compact.append(
                {
                    "symbol": row.get("symbol"),
                    "config_id": row.get("config_id"),
                    "candidate_id": row.get("candidate_id"),
                    "candidate_status": row.get("candidate_status"),
                    "fold_repair_probe_profile": row.get("fold_repair_probe_profile"),
                    "fold_repair_feature_filter_enabled": row.get(
                        "fold_repair_feature_filter_enabled"
                    ),
                    "fold_repair_feature_filter_profile": row.get(
                        "fold_repair_feature_filter_profile"
                    ),
                    "fold_repair_feature_filter_rules": self._as_dict(
                        row.get("fold_repair_feature_filter_rules")
                    ),
                    "fold_feature_regime_filter_summary": self._as_dict(
                        row.get("fold_feature_regime_filter_summary")
                    ),
                    "feature_filter_removed_signal_count": row.get(
                        "feature_filter_removed_signal_count"
                    ),
                    "feature_filter_removed_ratio": row.get("feature_filter_removed_ratio"),
                    "target_date_input_count": row.get("target_date_input_count"),
                    "target_date_removed_count": row.get("target_date_removed_count"),
                    "target_date_passed_count": row.get("target_date_passed_count"),
                    "primary_removed_counts_by_reason": self._as_dict(
                        row.get("primary_removed_counts_by_reason")
                    ),
                    "matched_removed_counts_by_reason": self._as_dict(
                        row.get("matched_removed_counts_by_reason")
                    ),
                    "removed_counts_by_date": self._as_dict(row.get("removed_counts_by_date")),
                    "passed_counts_by_date": self._as_dict(row.get("passed_counts_by_date")),
                    "removed_counts_by_regime": self._as_dict(
                        row.get("removed_counts_by_regime")
                    ),
                    "passed_counts_by_regime": self._as_dict(
                        row.get("passed_counts_by_regime")
                    ),
                    "missing_feature_counts": self._as_dict(
                        row.get("missing_feature_counts")
                    ),
                    "feature_filter_warnings": self._as_list(
                        row.get("feature_filter_warnings")
                    ),
                    "fold_repair_time_slice_blackout_enabled": row.get(
                        "fold_repair_time_slice_blackout_enabled"
                    ),
                    "fold_time_slice_blackout_summary": self._as_dict(
                        row.get("fold_time_slice_blackout_summary")
                    ),
                    "profit_factor": row.get("profit_factor"),
                    "profit_total_r": row.get("profit_total_r"),
                    "walk_forward_profit_factor": row.get("walk_forward_profit_factor"),
                    "walk_forward_total_r": row.get("walk_forward_total_r"),
                    "failed_gates": self._as_list(row.get("failed_gates")),
                }
            )
        return compact

    def _feature_filter_diagnostics(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        aggregate_primary_reasons: dict[str, int] = {}
        aggregate_matched_reasons: dict[str, int] = {}
        aggregate_removed_by_date: dict[str, int] = {}
        aggregate_passed_by_date: dict[str, int] = {}
        aggregate_removed_by_regime: dict[str, int] = {}
        aggregate_passed_by_regime: dict[str, int] = {}
        aggregate_removed_by_active_regime_flag: dict[str, int] = {}
        aggregate_passed_by_active_regime_flag: dict[str, int] = {}
        aggregate_regime_source_counts: dict[str, int] = {}
        aggregate_conditional_regime_rule_counts: dict[str, int] = {}
        aggregate_conditional_regime_rule_eligible_counts: dict[str, int] = {}
        aggregate_conditional_regime_rule_passed_counts: dict[str, int] = {}
        aggregate_conditional_regime_rule_blocked_counts: dict[str, int] = {}
        aggregate_conditional_regime_rule_counts_by_primary_regime: dict[str, int] = {}
        aggregate_conditional_regime_rule_counts_by_active_flag: dict[str, int] = {}
        aggregate_conditional_regime_rule_metric_failure_counts: dict[str, int] = {}
        aggregate_conditional_regime_rule_metric_failure_counts_by_rule: dict[str, dict[str, Any]] = {}
        aggregate_conditional_regime_rule_metric_logic: dict[str, str] = {}
        aggregate_conditional_regime_rule_required_metric_failure_count: dict[str, int] = {}
        aggregate_conditional_regime_rule_metric_condition_count: dict[str, int] = {}
        aggregate_conditional_regime_rule_metric_failure_count_distribution_by_rule: dict[str, dict[str, int]] = {}
        aggregate_conditional_regime_rule_observed_metric_failure_counts_by_rule: dict[str, dict[str, int]] = {}
        aggregate_conditional_regime_rule_metric_pair_failure_counts_by_rule: dict[str, dict[str, int]] = {}
        aggregate_conditional_regime_rule_outcome_by_failure_count: dict[str, dict[str, dict[str, Any]]] = {}
        aggregate_removed_outcome_by_rule: dict[str, dict[str, Any]] = {}
        aggregate_passed_outcome_by_rule: dict[str, dict[str, Any]] = {}
        aggregate_removed_outcome_by_primary_regime: dict[str, dict[str, Any]] = {}
        aggregate_passed_outcome_by_primary_regime: dict[str, dict[str, Any]] = {}
        aggregate_removed_outcome_by_active_regime_flag: dict[str, dict[str, Any]] = {}
        aggregate_passed_outcome_by_active_regime_flag: dict[str, dict[str, Any]] = {}
        aggregate_missing_features: dict[str, int] = {}

        def merge_counts(target: dict[str, int], source: dict[str, Any]) -> None:
            for key, count in self._count_map(source).items():
                target[key] = target.get(key, 0) + count

        active_rows = []
        zero_removal_rows = []
        missing_summary_rows = []

        for row in rows:
            feature_summary = self._as_dict(row.get("fold_feature_regime_filter_summary"))
            if not feature_summary:
                missing_summary_rows.append(row.get("config_id"))
                continue

            removed = self._float_or_none(feature_summary.get("removed_signal_count")) or 0.0
            if removed > 0:
                active_rows.append(row.get("config_id"))
            else:
                zero_removal_rows.append(row.get("config_id"))

            merge_counts(
                aggregate_primary_reasons,
                self._summary_or_row_counts(
                    row,
                    feature_summary,
                    "primary_removed_counts_by_reason",
                    "removed_counts_by_reason",
                ),
            )
            merge_counts(
                aggregate_matched_reasons,
                self._summary_or_row_counts(
                    row,
                    feature_summary,
                    "matched_removed_counts_by_reason",
                ),
            )
            merge_counts(
                aggregate_removed_by_date,
                self._summary_or_row_counts(
                    row,
                    feature_summary,
                    "removed_counts_by_date",
                ),
            )
            merge_counts(
                aggregate_passed_by_date,
                self._summary_or_row_counts(
                    row,
                    feature_summary,
                    "passed_counts_by_date",
                ),
            )
            merge_counts(
                aggregate_removed_by_regime,
                self._summary_or_row_counts(
                    row,
                    feature_summary,
                    "removed_counts_by_regime",
                ),
            )
            merge_counts(
                aggregate_passed_by_regime,
                self._summary_or_row_counts(
                    row,
                    feature_summary,
                    "passed_counts_by_regime",
                ),
            )
            merge_counts(
                aggregate_removed_by_active_regime_flag,
                self._summary_or_row_counts(
                    row,
                    feature_summary,
                    "removed_counts_by_active_regime_flag",
                ),
            )
            merge_counts(
                aggregate_passed_by_active_regime_flag,
                self._summary_or_row_counts(
                    row,
                    feature_summary,
                    "passed_counts_by_active_regime_flag",
                ),
            )
            merge_counts(
                aggregate_regime_source_counts,
                self._summary_or_row_counts(
                    row,
                    feature_summary,
                    "regime_source_counts",
                ),
            )
            merge_counts(
                aggregate_conditional_regime_rule_counts,
                self._summary_or_row_counts(
                    row,
                    feature_summary,
                    "conditional_regime_rule_counts",
                    "conditional_regime_rule_blocked_counts",
                ),
            )
            merge_counts(
                aggregate_conditional_regime_rule_eligible_counts,
                self._summary_or_row_counts(
                    row,
                    feature_summary,
                    "conditional_regime_rule_eligible_counts",
                ),
            )
            merge_counts(
                aggregate_conditional_regime_rule_passed_counts,
                self._summary_or_row_counts(
                    row,
                    feature_summary,
                    "conditional_regime_rule_passed_counts",
                ),
            )
            merge_counts(
                aggregate_conditional_regime_rule_blocked_counts,
                self._summary_or_row_counts(
                    row,
                    feature_summary,
                    "conditional_regime_rule_blocked_counts",
                    "conditional_regime_rule_counts",
                ),
            )
            merge_counts(
                aggregate_conditional_regime_rule_counts_by_primary_regime,
                self._summary_or_row_counts(
                    row,
                    feature_summary,
                    "conditional_regime_rule_counts_by_primary_regime",
                ),
            )
            merge_counts(
                aggregate_conditional_regime_rule_counts_by_active_flag,
                self._summary_or_row_counts(
                    row,
                    feature_summary,
                    "conditional_regime_rule_counts_by_active_flag",
                ),
            )
            merge_counts(
                aggregate_conditional_regime_rule_metric_failure_counts,
                self._summary_or_row_counts(
                    row,
                    feature_summary,
                    "conditional_regime_rule_metric_failure_counts",
                ),
            )
            self._merge_nested_count_map(
                aggregate_conditional_regime_rule_metric_failure_counts_by_rule,
                feature_summary.get("conditional_regime_rule_metric_failure_counts_by_rule"),
            )
            self._merge_nested_count_map(
                aggregate_conditional_regime_rule_metric_failure_count_distribution_by_rule,
                feature_summary.get(
                    "conditional_regime_rule_metric_failure_count_distribution_by_rule"
                )
                or row.get(
                    "conditional_regime_rule_metric_failure_count_distribution_by_rule"
                ),
            )
            self._merge_nested_count_map(
                aggregate_conditional_regime_rule_observed_metric_failure_counts_by_rule,
                feature_summary.get(
                    "conditional_regime_rule_observed_metric_failure_counts_by_rule"
                )
                or row.get(
                    "conditional_regime_rule_observed_metric_failure_counts_by_rule"
                ),
            )
            self._merge_nested_count_map(
                aggregate_conditional_regime_rule_metric_pair_failure_counts_by_rule,
                feature_summary.get(
                    "conditional_regime_rule_metric_pair_failure_counts_by_rule"
                )
                or row.get(
                    "conditional_regime_rule_metric_pair_failure_counts_by_rule"
                ),
            )
            self._merge_rule_metadata_map(
                aggregate_conditional_regime_rule_metric_logic,
                feature_summary.get("conditional_regime_rule_metric_logic")
                or row.get("conditional_regime_rule_metric_logic"),
            )
            self._merge_rule_metadata_map(
                aggregate_conditional_regime_rule_required_metric_failure_count,
                feature_summary.get(
                    "conditional_regime_rule_required_metric_failure_count"
                )
                or row.get("conditional_regime_rule_required_metric_failure_count"),
            )
            self._merge_rule_metadata_map(
                aggregate_conditional_regime_rule_metric_condition_count,
                feature_summary.get("conditional_regime_rule_metric_condition_count")
                or row.get("conditional_regime_rule_metric_condition_count"),
            )
            self._merge_contribution_stats(
                aggregate_removed_outcome_by_rule,
                feature_summary.get("conditional_regime_rule_removed_outcome_by_rule"),
            )
            self._merge_contribution_stats(
                aggregate_passed_outcome_by_rule,
                feature_summary.get("conditional_regime_rule_passed_outcome_by_rule"),
            )
            self._merge_nested_contribution_stats_map(
                aggregate_conditional_regime_rule_outcome_by_failure_count,
                feature_summary.get("conditional_regime_rule_outcome_by_failure_count")
                or row.get("conditional_regime_rule_outcome_by_failure_count"),
            )
            self._merge_contribution_stats(
                aggregate_removed_outcome_by_primary_regime,
                feature_summary.get("removed_outcome_by_primary_regime"),
            )
            self._merge_contribution_stats(
                aggregate_passed_outcome_by_primary_regime,
                feature_summary.get("passed_outcome_by_primary_regime"),
            )
            self._merge_contribution_stats(
                aggregate_removed_outcome_by_active_regime_flag,
                feature_summary.get("removed_outcome_by_active_regime_flag"),
            )
            self._merge_contribution_stats(
                aggregate_passed_outcome_by_active_regime_flag,
                feature_summary.get("passed_outcome_by_active_regime_flag"),
            )
            merge_counts(
                aggregate_missing_features,
                self._summary_or_row_counts(
                    row,
                    feature_summary,
                    "missing_feature_counts",
                ),
            )

        if missing_summary_rows:
            readiness = "DIAGNOSTICS_INCOMPLETE"
        elif not active_rows:
            readiness = "FILTER_DID_NOT_REMOVE_SIGNALS"
        else:
            readiness = "DIAGNOSTICS_READY"

        missing_market_regime_count = aggregate_missing_features.get("market_regime", 0)
        if aggregate_regime_source_counts and missing_market_regime_count == 0:
            regime_propagation_status = "MARKET_REGIME_PROPAGATED"
        elif aggregate_regime_source_counts and missing_market_regime_count > 0:
            regime_propagation_status = "MARKET_REGIME_PARTIALLY_PROPAGATED"
        else:
            regime_propagation_status = "MARKET_REGIME_MISSING"

        if aggregate_conditional_regime_rule_counts or aggregate_conditional_regime_rule_blocked_counts:
            conditional_regime_filter_status = "CONDITIONAL_REGIME_FILTER_ACTIVE"
        elif aggregate_removed_by_regime:
            conditional_regime_filter_status = "HARD_REGIME_FILTER_OR_NON_CONDITIONAL_ONLY"
        else:
            conditional_regime_filter_status = "NO_REGIME_FILTER_REMOVALS"

        aggregate_conditional_regime_rule_metric_failure_counts_by_rule = {
            key: self._count_map(value)
            for key, value in sorted(
                aggregate_conditional_regime_rule_metric_failure_counts_by_rule.items()
            )
            if self._count_map(value)
        }
        aggregate_removed_outcome_by_rule = self._finalize_contribution_stats_map(
            aggregate_removed_outcome_by_rule
        )
        aggregate_passed_outcome_by_rule = self._finalize_contribution_stats_map(
            aggregate_passed_outcome_by_rule
        )
        aggregate_removed_outcome_by_primary_regime = self._finalize_contribution_stats_map(
            aggregate_removed_outcome_by_primary_regime
        )
        aggregate_passed_outcome_by_primary_regime = self._finalize_contribution_stats_map(
            aggregate_passed_outcome_by_primary_regime
        )
        aggregate_removed_outcome_by_active_regime_flag = self._finalize_contribution_stats_map(
            aggregate_removed_outcome_by_active_regime_flag
        )
        aggregate_passed_outcome_by_active_regime_flag = self._finalize_contribution_stats_map(
            aggregate_passed_outcome_by_active_regime_flag
        )
        aggregate_conditional_regime_rule_metric_failure_count_distribution_by_rule = {
            key: dict(sorted(value.items()))
            for key, value in sorted(
                aggregate_conditional_regime_rule_metric_failure_count_distribution_by_rule.items()
            )
        }
        aggregate_conditional_regime_rule_observed_metric_failure_counts_by_rule = {
            key: dict(sorted(value.items()))
            for key, value in sorted(
                aggregate_conditional_regime_rule_observed_metric_failure_counts_by_rule.items()
            )
        }
        aggregate_conditional_regime_rule_metric_pair_failure_counts_by_rule = {
            key: dict(sorted(value.items()))
            for key, value in sorted(
                aggregate_conditional_regime_rule_metric_pair_failure_counts_by_rule.items()
            )
        }
        aggregate_conditional_regime_rule_outcome_by_failure_count = (
            self._finalize_nested_contribution_stats_map(
                aggregate_conditional_regime_rule_outcome_by_failure_count
            )
        )
        aggregate_conditional_regime_ablation_board = self._conditional_regime_ablation_board(
            eligible_counts=aggregate_conditional_regime_rule_eligible_counts,
            blocked_counts=aggregate_conditional_regime_rule_blocked_counts,
            passed_counts=aggregate_conditional_regime_rule_passed_counts,
            metric_failure_counts_by_rule=aggregate_conditional_regime_rule_metric_failure_counts_by_rule,
            removed_outcome_by_rule=aggregate_removed_outcome_by_rule,
            passed_outcome_by_rule=aggregate_passed_outcome_by_rule,
            metric_logic_by_rule=aggregate_conditional_regime_rule_metric_logic,
            required_metric_failure_count_by_rule=(
                aggregate_conditional_regime_rule_required_metric_failure_count
            ),
            metric_condition_count_by_rule=(
                aggregate_conditional_regime_rule_metric_condition_count
            ),
        )
        aggregate_conditional_regime_metric_overlap_board = (
            self._conditional_regime_metric_overlap_board(
                eligible_counts=aggregate_conditional_regime_rule_eligible_counts,
                blocked_counts=aggregate_conditional_regime_rule_blocked_counts,
                failure_count_distribution_by_rule=(
                    aggregate_conditional_regime_rule_metric_failure_count_distribution_by_rule
                ),
                observed_metric_failure_counts_by_rule=(
                    aggregate_conditional_regime_rule_observed_metric_failure_counts_by_rule
                ),
                metric_pair_failure_counts_by_rule=(
                    aggregate_conditional_regime_rule_metric_pair_failure_counts_by_rule
                ),
                outcome_by_failure_count=(
                    aggregate_conditional_regime_rule_outcome_by_failure_count
                ),
                metric_logic_by_rule=aggregate_conditional_regime_rule_metric_logic,
                required_metric_failure_count_by_rule=(
                    aggregate_conditional_regime_rule_required_metric_failure_count
                ),
                metric_condition_count_by_rule=(
                    aggregate_conditional_regime_rule_metric_condition_count
                ),
            )
        )
        aggregate_per_regime_contribution_board = self._per_regime_contribution_board(
            removed_outcome_by_primary_regime=aggregate_removed_outcome_by_primary_regime,
            passed_outcome_by_primary_regime=aggregate_passed_outcome_by_primary_regime,
        )

        return {
            "diagnostic_name": "fold_feature_regime_filter_diagnostics",
            "diagnostic_version": self.diagnostic_version,
            "readiness": readiness,
            "feature_probe_count": len(rows),
            "active_filter_candidate_count": len(active_rows),
            "zero_removal_candidate_count": len(zero_removal_rows),
            "missing_summary_candidate_count": len(missing_summary_rows),
            "active_filter_config_ids": active_rows[:20],
            "zero_removal_config_ids": zero_removal_rows[:20],
            "missing_summary_config_ids": missing_summary_rows[:20],
            "aggregate_primary_removed_counts_by_reason": aggregate_primary_reasons,
            "aggregate_matched_removed_counts_by_reason": aggregate_matched_reasons,
            "aggregate_removed_counts_by_date": aggregate_removed_by_date,
            "aggregate_passed_counts_by_date": aggregate_passed_by_date,
            "aggregate_removed_counts_by_regime": aggregate_removed_by_regime,
            "aggregate_passed_counts_by_regime": aggregate_passed_by_regime,
            "aggregate_removed_counts_by_active_regime_flag": aggregate_removed_by_active_regime_flag,
            "aggregate_passed_counts_by_active_regime_flag": aggregate_passed_by_active_regime_flag,
            "aggregate_regime_source_counts": aggregate_regime_source_counts,
            "aggregate_conditional_regime_rule_counts": (
                aggregate_conditional_regime_rule_counts
            ),
            "aggregate_conditional_regime_rule_eligible_counts": (
                aggregate_conditional_regime_rule_eligible_counts
            ),
            "aggregate_conditional_regime_rule_passed_counts": (
                aggregate_conditional_regime_rule_passed_counts
            ),
            "aggregate_conditional_regime_rule_blocked_counts": (
                aggregate_conditional_regime_rule_blocked_counts
            ),
            "aggregate_conditional_regime_rule_counts_by_primary_regime": (
                aggregate_conditional_regime_rule_counts_by_primary_regime
            ),
            "aggregate_conditional_regime_rule_counts_by_active_flag": (
                aggregate_conditional_regime_rule_counts_by_active_flag
            ),
            "aggregate_conditional_regime_rule_metric_failure_counts": (
                aggregate_conditional_regime_rule_metric_failure_counts
            ),
            "aggregate_conditional_regime_rule_metric_failure_counts_by_rule": (
                aggregate_conditional_regime_rule_metric_failure_counts_by_rule
            ),
            "aggregate_conditional_regime_rule_metric_logic": (
                aggregate_conditional_regime_rule_metric_logic
            ),
            "aggregate_conditional_regime_rule_required_metric_failure_count": (
                aggregate_conditional_regime_rule_required_metric_failure_count
            ),
            "aggregate_conditional_regime_rule_metric_condition_count": (
                aggregate_conditional_regime_rule_metric_condition_count
            ),
            "aggregate_conditional_regime_rule_metric_failure_count_distribution_by_rule": (
                aggregate_conditional_regime_rule_metric_failure_count_distribution_by_rule
            ),
            "aggregate_conditional_regime_rule_observed_metric_failure_counts_by_rule": (
                aggregate_conditional_regime_rule_observed_metric_failure_counts_by_rule
            ),
            "aggregate_conditional_regime_rule_metric_pair_failure_counts_by_rule": (
                aggregate_conditional_regime_rule_metric_pair_failure_counts_by_rule
            ),
            "aggregate_conditional_regime_rule_outcome_by_failure_count": (
                aggregate_conditional_regime_rule_outcome_by_failure_count
            ),
            "aggregate_conditional_regime_rule_removed_outcome_by_rule": (
                aggregate_removed_outcome_by_rule
            ),
            "aggregate_conditional_regime_rule_passed_outcome_by_rule": (
                aggregate_passed_outcome_by_rule
            ),
            "aggregate_removed_outcome_by_primary_regime": (
                aggregate_removed_outcome_by_primary_regime
            ),
            "aggregate_passed_outcome_by_primary_regime": (
                aggregate_passed_outcome_by_primary_regime
            ),
            "aggregate_removed_outcome_by_active_regime_flag": (
                aggregate_removed_outcome_by_active_regime_flag
            ),
            "aggregate_passed_outcome_by_active_regime_flag": (
                aggregate_passed_outcome_by_active_regime_flag
            ),
            "aggregate_conditional_regime_ablation_board": (
                aggregate_conditional_regime_ablation_board
            ),
            "aggregate_conditional_regime_metric_overlap_board": (
                aggregate_conditional_regime_metric_overlap_board
            ),
            "aggregate_per_regime_contribution_board": (
                aggregate_per_regime_contribution_board
            ),
            "aggregate_missing_feature_counts": aggregate_missing_features,
            "regime_propagation_status": regime_propagation_status,
            "missing_market_regime_count": missing_market_regime_count,
            "conditional_regime_filter_status": conditional_regime_filter_status,
        }

    def _verdict(self, *, best_feature: dict[str, Any], best_date: dict[str, Any]) -> str:
        if not best_feature and not best_date:
            return "NO_REPAIR_PROBES_AVAILABLE"
        if best_feature and not best_date:
            return "FEATURE_REGIME_PROBE_ONLY_BASELINE_MISSING"
        if best_date and not best_feature:
            return "DATE_BLACKOUT_BASELINE_ONLY_FEATURE_REGIME_MISSING"

        feature_wf = self._float_or_none(best_feature.get("walk_forward_total_r")) or float("-inf")
        date_wf = self._float_or_none(best_date.get("walk_forward_total_r")) or float("-inf")
        if feature_wf >= date_wf and feature_wf > 0.0:
            return "FEATURE_REGIME_FILTER_MATCHES_OR_BEATS_DATE_BLACKOUT"
        if feature_wf > 0.0:
            return "FEATURE_REGIME_FILTER_POSITIVE_BUT_BELOW_DATE_BLACKOUT"
        return "FEATURE_REGIME_FILTER_NOT_YET_A_REPLACEMENT"

    def _verdict_detail(
        self,
        *,
        best_feature: dict[str, Any],
        best_date: dict[str, Any],
        feature_filter_diagnostics: dict[str, Any],
    ) -> dict[str, Any]:
        feature_wf = self._float_or_none(best_feature.get("walk_forward_total_r"))
        date_wf = self._float_or_none(best_date.get("walk_forward_total_r"))
        if not best_feature:
            reason = "no_feature_regime_probe"
        elif feature_filter_diagnostics.get("readiness") == "DIAGNOSTICS_INCOMPLETE":
            reason = "feature_filter_diagnostics_incomplete"
        elif feature_filter_diagnostics.get("readiness") == "FILTER_DID_NOT_REMOVE_SIGNALS":
            reason = "feature_filter_not_active_enough"
        elif feature_wf is None or feature_wf <= 0:
            reason = "feature_filter_failed_walk_forward"
        elif date_wf is not None and feature_wf < date_wf:
            reason = "feature_filter_positive_but_weaker_than_date_blackout"
        else:
            reason = "feature_filter_matches_or_beats_date_blackout"
        return {
            "reason": reason,
            "feature_walk_forward_total_r": feature_wf,
            "date_walk_forward_total_r": date_wf,
            "wf_total_r_gap_vs_date_blackout": (
                None if feature_wf is None or date_wf is None else feature_wf - date_wf
            ),
        }
