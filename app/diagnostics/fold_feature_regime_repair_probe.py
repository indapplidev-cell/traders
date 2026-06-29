from __future__ import annotations

from typing import Any


class FoldFeatureRegimeRepairProbe:
    diagnostic_name = "fold_feature_regime_repair_probe"
    diagnostic_version = "ml38.10.28"

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
        rows = [self._candidate_row(item) for item in candidates]
        feature_rows = [
            row
            for row in rows
            if row.get("fold_repair_feature_filter_enabled")
            or str(row.get("config_id") or "").lower().startswith("lv32_")
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
        feature_summary = self._as_dict(
            candidate.get("fold_feature_regime_filter_summary")
            or profit_diag.get("fold_feature_regime_filter_summary")
        )
        blackout_summary = self._as_dict(
            candidate.get("fold_time_slice_blackout_summary")
            or candidate.get("fold_repair_probe_diagnostics")
            or profit_diag.get("fold_time_slice_blackout_summary")
        )
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
