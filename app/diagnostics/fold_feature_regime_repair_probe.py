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
        aggregate_conditional_regime_rule_counts_by_primary_regime: dict[str, int] = {}
        aggregate_conditional_regime_rule_counts_by_active_flag: dict[str, int] = {}
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

        if aggregate_conditional_regime_rule_counts:
            conditional_regime_filter_status = "CONDITIONAL_REGIME_FILTER_ACTIVE"
        elif aggregate_removed_by_regime:
            conditional_regime_filter_status = "HARD_REGIME_FILTER_OR_NON_CONDITIONAL_ONLY"
        else:
            conditional_regime_filter_status = "NO_REGIME_FILTER_REMOVALS"

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
            "aggregate_conditional_regime_rule_counts_by_primary_regime": (
                aggregate_conditional_regime_rule_counts_by_primary_regime
            ),
            "aggregate_conditional_regime_rule_counts_by_active_flag": (
                aggregate_conditional_regime_rule_counts_by_active_flag
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
