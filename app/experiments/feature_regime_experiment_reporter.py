from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.diagnostics.directional_side_ablation_comparator import (
    DirectionalSideAblationComparator,
)
from app.diagnostics.directional_side_walk_forward_stability import (
    DirectionalSideWalkForwardStabilityAnalyzer,
)


class FeatureRegimeExperimentReporter:
    """Serialize and export feature/regime experiment results."""

    SUMMARY_PAYLOAD_MODE = "compact_capped_ml38_10_25_1"
    SUMMARY_CANDIDATE_RESULT_LIMIT = 128
    SUMMARY_CONFIGS_RANKED_LIMIT = 128
    SUMMARY_VALIDATION_BOARD_ROW_LIMIT = 6
    SUMMARY_BEST_FAILED_TOTAL_R_FOLD_LIMIT = 6
    SUMMARY_FAILED_GATE_CANDIDATE_LIMIT = 3
    SUMMARY_GATE_PROBE_LIMIT = 6
    SUMMARY_PASSED_GATE_LIMIT = 6
    SUMMARY_JSON_SOFT_MAX_BYTES = 15 * 1024 * 1024

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

    @staticmethod
    def _result_value(result: object, key: str, default: Any = None) -> Any:
        if isinstance(result, dict):
            return result.get(key, default)
        return getattr(result, key, default)

    @staticmethod
    def _object_to_dict_shallow(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return dict(value)
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            return dict(to_dict())
        if value is None:
            return {}
        return {
            name: getattr(value, name)
            for name in dir(value)
            if not name.startswith("_")
            and not callable(getattr(value, name, None))
        }

    @classmethod
    def _compact_preview_value(
        cls,
        value: Any,
        *,
        depth: int = 0,
        max_depth: int = 2,
        max_dict_keys: int = 16,
        max_list_items: int = 6,
    ) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, dict):
            items = list(value.items())
            preview: dict[str, Any] = {}
            for key, item in items[:max_dict_keys]:
                if depth + 1 >= max_depth and isinstance(item, (dict, list, tuple, set)):
                    preview[key] = cls._collection_preview(item)
                else:
                    preview[key] = cls._compact_preview_value(
                        item,
                        depth=depth + 1,
                        max_depth=max_depth,
                        max_dict_keys=max_dict_keys,
                        max_list_items=max_list_items,
                    )
            preview["_key_count"] = len(items)
            preview["_keys_truncated"] = len(items) > max_dict_keys
            return preview

        if isinstance(value, (list, tuple, set)):
            items = list(value)
            if depth + 1 >= max_depth:
                return cls._collection_preview(items)
            preview = [
                cls._compact_preview_value(
                    item,
                    depth=depth + 1,
                    max_depth=max_depth,
                    max_dict_keys=max_dict_keys,
                    max_list_items=max_list_items,
                )
                for item in items[:max_list_items]
            ]
            if len(items) > max_list_items:
                preview.append(
                    {
                        "_item_count": len(items),
                        "_items_truncated": True,
                    }
                )
            return preview

        return str(value)

    @classmethod
    def _collection_preview(cls, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return {
                "_type": "dict",
                "_key_count": len(value),
            }
        items = cls._as_list(value)
        return {
            "_type": "list",
            "_item_count": len(items),
        }

    @classmethod
    def _compact_preview_dict(cls, value: Any) -> dict[str, Any]:
        preview = cls._compact_preview_value(value)
        return preview if isinstance(preview, dict) else {}

    @classmethod
    def _compact_fold_feature_summary(cls, summary: dict[str, Any]) -> dict[str, Any]:
        payload = dict(summary or {})
        removed_examples = payload.get("removed_signal_examples")
        if isinstance(removed_examples, list):
            payload["removed_signal_examples"] = removed_examples[:5]
            payload["removed_signal_examples_truncated"] = len(removed_examples) > 5
        passed_examples = payload.get("passed_target_date_signal_examples")
        if isinstance(passed_examples, list):
            payload["passed_target_date_signal_examples"] = passed_examples[:5]
            payload["passed_target_date_signal_examples_truncated"] = len(passed_examples) > 5
        return cls._compact_preview_dict(payload)

    def result_to_dict(self, result: object) -> dict[str, Any]:
        if isinstance(result, dict):
            return dict(result)
        to_dict = getattr(result, "to_dict", None)
        if callable(to_dict):
            return dict(to_dict())
        raise TypeError("result must be a dict or provide to_dict()")

    def _compact_gate_probe(self, value: Any) -> dict[str, Any]:
        gate = self._as_dict(value)
        if not gate:
            return {}
        return {
            "gate_type": gate.get("gate_type"),
            "threshold": gate.get("threshold"),
            "signal_count": gate.get("signal_count"),
            "resolved_signal_count": gate.get("resolved_signal_count"),
            "long_count": gate.get("long_count"),
            "short_count": gate.get("short_count"),
            "profit_factor": gate.get("profit_factor"),
            "total_r": gate.get("total_r"),
            "expectancy_r": gate.get("expectancy_r"),
            "max_drawdown_r": gate.get("max_drawdown_r"),
            "passed": gate.get("passed"),
            "fail_reasons": self._as_list(gate.get("fail_reasons")),
            "warnings": self._as_list(gate.get("warnings")),
            "primary_blocker": gate.get("primary_blocker"),
            "repair_hint": gate.get("repair_hint"),
            "distance_to_pass_score": gate.get("distance_to_pass_score"),
            "threshold_deficits": self._as_dict(gate.get("threshold_deficits")),
            "effective_min_signal_count": gate.get("effective_min_signal_count"),
            "effective_min_profit_factor": gate.get("effective_min_profit_factor"),
            "effective_min_total_r": gate.get("effective_min_total_r"),
            "effective_min_expectancy_r": gate.get("effective_min_expectancy_r"),
            "directional_side_filter_profile": gate.get("directional_side_filter_profile"),
            "allowed_signal_directions": self._as_list(gate.get("allowed_signal_directions")),
        }

    def _compact_validation_candidate_board(self, value: Any) -> dict[str, Any]:
        board = self._as_dict(value)
        if not board:
            return {}

        rows = self._as_list(board.get("candidate_board_rows"))
        best_failed = self._as_list(board.get("best_failed_total_r_by_fold"))
        compact_rows: list[dict[str, Any]] = []
        for row in rows[: self.SUMMARY_VALIDATION_BOARD_ROW_LIMIT]:
            row = self._as_dict(row)
            compact_rows.append(
                {
                    "fold_index": row.get("fold_index"),
                    "train_start": row.get("train_start"),
                    "train_end": row.get("train_end"),
                    "validation_start": row.get("validation_start"),
                    "validation_end": row.get("validation_end"),
                    "test_start": row.get("test_start"),
                    "test_end": row.get("test_end"),
                    "selected_gate_present": row.get("selected_gate_present"),
                    "gate_reject_reason": row.get("gate_reject_reason"),
                    "selection_mode": row.get("selection_mode"),
                    "directional_side_filter_profile": row.get("directional_side_filter_profile"),
                    "allowed_signal_directions": self._as_list(row.get("allowed_signal_directions")),
                    "side_aware_validation_relaxation_enabled": row.get(
                        "side_aware_validation_relaxation_enabled"
                    ),
                    "effective_min_signal_count": row.get("effective_min_signal_count"),
                    "effective_min_profit_factor": row.get("effective_min_profit_factor"),
                    "effective_min_total_r": row.get("effective_min_total_r"),
                    "effective_min_expectancy_r": row.get("effective_min_expectancy_r"),
                    "primary_failure_reason": row.get("primary_failure_reason"),
                    "has_total_r_below_min_blocker": row.get("has_total_r_below_min_blocker"),
                    "recommended_validation_repair_profile": row.get(
                        "recommended_validation_repair_profile"
                    ),
                    "total_r_repair_verdict": row.get("total_r_repair_verdict"),
                    "total_r_repair_candidate_count": row.get("total_r_repair_candidate_count"),
                    "min_total_r_deficit": row.get("min_total_r_deficit"),
                    "median_total_r_deficit": row.get("median_total_r_deficit"),
                    "max_total_r_deficit": row.get("max_total_r_deficit"),
                    "best_failed_gate_by_distance_to_pass": self._compact_gate_probe(
                        row.get("best_failed_gate_by_distance_to_pass")
                    ),
                    "best_failed_gate_candidate_count": len(
                        self._as_list(row.get("best_failed_gate_candidates"))
                    ),
                    "best_failed_gate_candidates": [
                        self._compact_gate_probe(item)
                        for item in self._as_list(row.get("best_failed_gate_candidates"))[
                            : self.SUMMARY_FAILED_GATE_CANDIDATE_LIMIT
                        ]
                    ],
                }
            )

        return {
            "diagnostic_name": board.get("diagnostic_name"),
            "diagnostic_version": board.get("diagnostic_version"),
            "diagnostic_status": board.get("diagnostic_status"),
            "fold_count": board.get("fold_count"),
            "folds_with_selected_gate": board.get("folds_with_selected_gate"),
            "no_gate_fold_count": board.get("no_gate_fold_count"),
            "candidate_board_rows_total_count": len(rows),
            "candidate_board_rows_truncated": len(rows) > len(compact_rows),
            "candidate_board_rows": compact_rows,
            "total_r_below_min_fold_count": board.get("total_r_below_min_fold_count"),
            "total_r_repair_candidate_fold_count": board.get(
                "total_r_repair_candidate_fold_count"
            ),
            "best_failed_total_r_by_fold_total_count": len(best_failed),
            "best_failed_total_r_by_fold_truncated": len(best_failed)
            > self.SUMMARY_BEST_FAILED_TOTAL_R_FOLD_LIMIT,
            "best_failed_total_r_by_fold": [
                self._as_dict(item)
                for item in best_failed[: self.SUMMARY_BEST_FAILED_TOTAL_R_FOLD_LIMIT]
            ],
            "fold_root_cause_count": board.get("fold_root_cause_count"),
            "worst_fold_root_cause": self._compact_worst_fold_root_cause(
                board.get("worst_fold_root_cause")
            ),
            "median_best_total_r_deficit": board.get("median_best_total_r_deficit"),
            "max_best_total_r_deficit": board.get("max_best_total_r_deficit"),
            "recommended_validation_repair_profile": board.get(
                "recommended_validation_repair_profile"
            ),
            "repair_profile_counts": self._as_dict(board.get("repair_profile_counts")),
            "verdict": board.get("verdict"),
            "warnings": self._as_list(board.get("warnings")),
            "recommendations": self._as_list(board.get("recommendations")),
        }

    def _compact_directional_side_signal_recovery(self, value: Any) -> dict[str, Any]:
        payload = self._as_dict(value)
        if not payload:
            return {}
        fold_rows = self._as_list(payload.get("fold_signal_recovery_rows"))
        preview = [self._as_dict(item) for item in fold_rows[:3]]
        return {
            "diagnostic_name": payload.get("diagnostic_name"),
            "diagnostic_version": payload.get("diagnostic_version"),
            "diagnostic_status": payload.get("diagnostic_status"),
            "verdict": payload.get("verdict"),
            "fold_count": payload.get("fold_count"),
            "side_profile": payload.get("side_profile"),
            "zero_signal_fold_count": payload.get("zero_signal_fold_count"),
            "low_signal_fold_count": payload.get("low_signal_fold_count"),
            "side_filter_removed_all_fold_count": payload.get("side_filter_removed_all_fold_count"),
            "raw_signal_available_but_filtered_out_count": payload.get(
                "raw_signal_available_but_filtered_out_count"
            ),
            "threshold_too_strict_fold_count": payload.get("threshold_too_strict_fold_count"),
            "side_aware_relaxed_fold_count": payload.get("side_aware_relaxed_fold_count"),
            "total_original_signal_count": payload.get("total_original_signal_count"),
            "total_filtered_signal_count": payload.get("total_filtered_signal_count"),
            "total_removed_signal_count": payload.get("total_removed_signal_count"),
            "primary_signal_loss_reason_counts": self._as_dict(
                payload.get("primary_signal_loss_reason_counts")
            ),
            "validation_gate_failure_reason_counts": self._as_dict(
                payload.get("validation_gate_failure_reason_counts")
            ),
            "fold_signal_recovery_row_count": len(fold_rows),
            "fold_signal_recovery_rows_truncated": len(fold_rows) > len(preview),
            "fold_signal_recovery_rows": preview,
            "warnings": self._as_list(payload.get("warnings")),
            "recommendations": self._as_list(payload.get("recommendations")),
        }

    def _compact_worst_fold_root_cause(self, value: Any) -> dict[str, Any]:
        payload = self._as_dict(value)
        if not payload:
            return {}
        return self._cap_root_cause_payload(
            {
                "diagnostic_name": payload.get("diagnostic_name"),
                "diagnostic_version": payload.get("diagnostic_version"),
                "diagnostic_status": payload.get("diagnostic_status"),
                "fold_index": payload.get("fold_index"),
                "train_start": payload.get("train_start"),
                "train_end": payload.get("train_end"),
                "validation_start": payload.get("validation_start"),
                "validation_end": payload.get("validation_end"),
                "test_start": payload.get("test_start"),
                "test_end": payload.get("test_end"),
                "gate_type": payload.get("gate_type"),
                "threshold": payload.get("threshold"),
                "validation_signal_count": payload.get("validation_signal_count"),
                "validation_total_r": payload.get("validation_total_r"),
                "validation_win_count": payload.get("validation_win_count"),
                "validation_loss_count": payload.get("validation_loss_count"),
                "validation_loss_rate": payload.get("validation_loss_rate"),
                "outcome_counts": self._as_dict(payload.get("outcome_counts")),
                "direction_summary": [
                    self._as_dict(item)
                    for item in self._as_list(payload.get("direction_summary"))
                ],
                "outcome_summary": [
                    self._as_dict(item)
                    for item in self._as_list(payload.get("outcome_summary"))
                ],
                "time_slice_summary": [
                    self._as_dict(item)
                    for item in self._as_list(payload.get("time_slice_summary"))
                ],
                "regime_summary": [
                    self._as_dict(item)
                    for item in self._as_list(payload.get("regime_summary"))
                ],
                "entry_path_summary": [
                    self._as_dict(item)
                    for item in self._as_list(payload.get("entry_path_summary"))
                ],
                "setup_quality_summary": [
                    self._as_dict(item)
                    for item in self._as_list(payload.get("setup_quality_summary"))
                ],
                "stop_pressure_summary": [
                    self._as_dict(item)
                    for item in self._as_list(payload.get("stop_pressure_summary"))
                ],
                "mae_pressure_summary": [
                    self._as_dict(item)
                    for item in self._as_list(payload.get("mae_pressure_summary"))
                ],
                "root_cause_flags": self._as_list(payload.get("root_cause_flags")),
                "primary_root_cause": payload.get("primary_root_cause"),
                "sample_losing_trades": [
                    self._as_dict(item)
                    for item in self._as_list(payload.get("sample_losing_trades"))
                ],
                "recommendations": self._as_list(payload.get("recommendations")),
            }
        )

    @classmethod
    def _cap_root_cause_payload(cls, payload: Any) -> dict[str, Any]:
        root = cls._as_dict(payload)
        if not root:
            return {}
        capped = dict(root)
        for key, limit in {
            "time_slice_summary": 8,
            "outcome_summary": 8,
            "stop_pressure_summary": 5,
            "mae_pressure_summary": 5,
            "setup_quality_summary": 5,
            "direction_summary": 5,
            "entry_path_summary": 5,
            "regime_summary": 5,
            "sample_losing_trades": 3,
        }.items():
            rows = cls._as_list(capped.get(key))
            capped[f"{key}_total_count"] = len(rows)
            capped[f"{key}_truncated"] = len(rows) > limit
            capped[key] = rows[:limit]
        return capped

    def _compact_walk_forward_profit_diagnostics(self, value: Any) -> dict[str, Any]:
        payload = self._as_dict(value)
        if not payload:
            return {}

        fold_snapshots_source = self._as_list(payload.get("fold_snapshots"))
        low_signal_folds_source = self._as_list(payload.get("low_signal_folds"))
        gate_probes_source = self._as_list(payload.get("gate_probes"))
        passed_gates_source = self._as_list(payload.get("passed_gates"))
        best_failed_total_r_by_fold_source = self._as_list(
            payload.get("best_failed_total_r_by_fold")
        )
        validation_board = self._compact_validation_candidate_board(
            payload.get("walk_forward_validation_candidate_board")
        )

        return {
            "diagnostic_name": payload.get("diagnostic_name"),
            "diagnostic_version": payload.get("diagnostic_version"),
            "symbol": payload.get("symbol"),
            "feature_version": payload.get("feature_version"),
            "model_version": payload.get("model_version"),
            "walk_forward_profit_factor": payload.get("walk_forward_profit_factor"),
            "walk_forward_total_r": payload.get("walk_forward_total_r"),
            "fold_count": payload.get("fold_count"),
            "profitable_fold_count": payload.get("profitable_fold_count"),
            "unprofitable_fold_count": payload.get("unprofitable_fold_count"),
            "worst_fold": self._as_dict(payload.get("worst_fold")),
            "best_fold": self._as_dict(payload.get("best_fold")),
            "fold_snapshots": [
                self._as_dict(item) for item in fold_snapshots_source[:6]
            ],
            "fold_snapshots_total_count": len(fold_snapshots_source),
            "fold_snapshots_truncated": len(fold_snapshots_source) > 6,
            "low_signal_folds": [
                self._as_dict(item) for item in low_signal_folds_source[:6]
            ],
            "low_signal_folds_total_count": len(low_signal_folds_source),
            "low_signal_folds_truncated": len(low_signal_folds_source) > 6,
            "fold_signal_summary": self._as_dict(payload.get("fold_signal_summary")),
            "fold_profit_summary": self._as_dict(payload.get("fold_profit_summary")),
            "zero_signal_fold_count": payload.get("zero_signal_fold_count"),
            "low_signal_fold_count": payload.get("low_signal_fold_count"),
            "min_resolved_signal_count": payload.get("min_resolved_signal_count"),
            "median_resolved_signal_count": payload.get("median_resolved_signal_count"),
            "max_resolved_signal_count": payload.get("max_resolved_signal_count"),
            "total_resolved_signal_count": payload.get("total_resolved_signal_count"),
            "walk_forward_stability_status": payload.get("walk_forward_stability_status"),
            "walk_forward_stability_verdict": payload.get("walk_forward_stability_verdict"),
            "walk_forward_stability_warnings": self._as_list(
                payload.get("walk_forward_stability_warnings")
            ),
            "walk_forward_stability_recommendations": self._as_list(
                payload.get("walk_forward_stability_recommendations")
            ),
            "validation_gate_failure_reason_counts": self._as_dict(
                payload.get("validation_gate_failure_reason_counts")
            ),
            "side_aware_relaxed_fold_count": payload.get("side_aware_relaxed_fold_count"),
            "walk_forward_validation_candidate_board_status": payload.get(
                "walk_forward_validation_candidate_board_status"
            ),
            "walk_forward_validation_candidate_board_verdict": payload.get(
                "walk_forward_validation_candidate_board_verdict"
            ),
            "validation_fold_root_cause_summary": self._as_dict(
                payload.get("validation_fold_root_cause_summary")
            ),
            "worst_fold_root_cause": self._compact_worst_fold_root_cause(
                payload.get("worst_fold_root_cause")
            ),
            "primary_validation_root_cause_counts": self._as_dict(
                payload.get("primary_validation_root_cause_counts")
            ),
            "recommended_validation_repair_profile": payload.get(
                "recommended_validation_repair_profile"
            ),
            "total_r_below_min_fold_count": payload.get("total_r_below_min_fold_count"),
            "total_r_repair_candidate_fold_count": payload.get(
                "total_r_repair_candidate_fold_count"
            ),
            "median_best_total_r_deficit": payload.get("median_best_total_r_deficit"),
            "max_best_total_r_deficit": payload.get("max_best_total_r_deficit"),
            "best_failed_total_r_by_fold_total_count": (
                len(best_failed_total_r_by_fold_source)
                if best_failed_total_r_by_fold_source
                else validation_board.get("best_failed_total_r_by_fold_total_count")
            ),
            "best_failed_total_r_by_fold_truncated": (
                len(best_failed_total_r_by_fold_source) > self.SUMMARY_BEST_FAILED_TOTAL_R_FOLD_LIMIT
                if best_failed_total_r_by_fold_source
                else validation_board.get("best_failed_total_r_by_fold_truncated")
            ),
            "best_failed_total_r_by_fold": [
                self._as_dict(item)
                for item in best_failed_total_r_by_fold_source[
                    : self.SUMMARY_BEST_FAILED_TOTAL_R_FOLD_LIMIT
                ]
            ] if best_failed_total_r_by_fold_source else self._as_list(
                validation_board.get("best_failed_total_r_by_fold")
            ),
            "fold_root_cause_count": (
                payload.get("fold_root_cause_count")
                if payload.get("fold_root_cause_count") is not None
                else validation_board.get("fold_root_cause_count")
            ),
            "gate_probes_total_count": len(gate_probes_source),
            "gate_probes_truncated": len(gate_probes_source) > self.SUMMARY_GATE_PROBE_LIMIT,
            "gate_probes": [
                self._compact_gate_probe(item)
                for item in gate_probes_source[: self.SUMMARY_GATE_PROBE_LIMIT]
            ],
            "passed_gates_total_count": len(passed_gates_source),
            "passed_gates_truncated": len(passed_gates_source) > self.SUMMARY_PASSED_GATE_LIMIT,
            "passed_gates": [
                self._compact_gate_probe(item)
                for item in passed_gates_source[: self.SUMMARY_PASSED_GATE_LIMIT]
            ],
            "walk_forward_validation_candidate_board": validation_board,
            "directional_side_signal_recovery_diagnostics": (
                self._compact_directional_side_signal_recovery(
                    payload.get("directional_side_signal_recovery_diagnostics")
                )
            ),
        }

    def _compact_candidate_result(self, value: Any) -> dict[str, Any]:
        candidate = self._object_to_dict_shallow(value)
        if not candidate:
            return {}

        candidate["label_config"] = self._as_dict(candidate.get("label_config"))
        candidate["failed_gates"] = self._as_list(candidate.get("failed_gates"))
        candidate["passed_gates"] = self._as_list(candidate.get("passed_gates"))
        candidate["warnings"] = self._as_list(candidate.get("warnings"))
        candidate["recommendations"] = self._as_list(candidate.get("recommendations"))
        for key in (
            "prediction_root_cause_audit",
            "book_driven_forensic_audit",
            "label_mode_comparison_audit",
            "flat_subtype_audit",
            "setup_aware_label_diagnostics",
            "schwager_slice_robustness",
            "schwager_robustness_decision_board",
            "class_margin_objective_decision",
            "directional_edge_bias_audit",
            "directional_side_filter_summary",
            "profit_aware_diagnostics",
            "collapse_diagnostics_v2",
            "real_feature_diagnostics",
            "regime_label_builder_status",
            "two_stage_trade_diagnostics",
        ):
            candidate[key] = self._compact_preview_dict(candidate.get(key))

        walk_forward = self._compact_walk_forward_profit_diagnostics(
            candidate.get("walk_forward_profit_diagnostics")
        )
        candidate["walk_forward_profit_diagnostics"] = walk_forward
        candidate["directional_side_signal_recovery_diagnostics"] = self._as_dict(
            walk_forward.get("directional_side_signal_recovery_diagnostics")
        )
        candidate["directional_side_signal_recovery_status"] = walk_forward.get(
            "directional_side_signal_recovery_diagnostics",
            {},
        ).get("diagnostic_status") or candidate.get("directional_side_signal_recovery_status")
        candidate["directional_side_signal_recovery_verdict"] = walk_forward.get(
            "directional_side_signal_recovery_diagnostics",
            {},
        ).get("verdict") or candidate.get("directional_side_signal_recovery_verdict")
        candidate["primary_signal_loss_reason_counts"] = self._as_dict(
            walk_forward.get("directional_side_signal_recovery_diagnostics", {}).get(
                "primary_signal_loss_reason_counts"
            )
            or candidate.get("primary_signal_loss_reason_counts")
        )
        candidate["validation_gate_failure_reason_counts"] = self._as_dict(
            walk_forward.get("validation_gate_failure_reason_counts")
            or candidate.get("validation_gate_failure_reason_counts")
        )
        candidate["validation_fold_root_cause_summary"] = self._as_dict(
            walk_forward.get("validation_fold_root_cause_summary")
            or candidate.get("validation_fold_root_cause_summary")
        )
        candidate["worst_fold_root_cause"] = self._compact_worst_fold_root_cause(
            walk_forward.get("worst_fold_root_cause")
            or candidate.get("worst_fold_root_cause")
        )
        candidate["primary_validation_root_cause_counts"] = self._as_dict(
            walk_forward.get("primary_validation_root_cause_counts")
            or candidate.get("primary_validation_root_cause_counts")
        )
        candidate["fold_root_cause_count"] = (
            walk_forward.get("walk_forward_validation_candidate_board", {}).get(
                "fold_root_cause_count"
            )
            if self._as_dict(walk_forward.get("walk_forward_validation_candidate_board"))
            else candidate.get("fold_root_cause_count")
        )
        if candidate["fold_root_cause_count"] is None:
            candidate["fold_root_cause_count"] = candidate.get("fold_root_cause_count")
        candidate["walk_forward_validation_candidate_board_status"] = (
            walk_forward.get("walk_forward_validation_candidate_board_status")
            or candidate.get("walk_forward_validation_candidate_board_status")
        )
        candidate["walk_forward_validation_candidate_board_verdict"] = (
            walk_forward.get("walk_forward_validation_candidate_board_verdict")
            or candidate.get("walk_forward_validation_candidate_board_verdict")
        )
        candidate["recommended_validation_repair_profile"] = (
            walk_forward.get("recommended_validation_repair_profile")
            or candidate.get("recommended_validation_repair_profile")
        )
        candidate["total_r_below_min_fold_count"] = (
            walk_forward.get("total_r_below_min_fold_count")
            if walk_forward.get("total_r_below_min_fold_count") is not None
            else candidate.get("total_r_below_min_fold_count")
        )
        candidate["total_r_repair_candidate_fold_count"] = (
            walk_forward.get("total_r_repair_candidate_fold_count")
            if walk_forward.get("total_r_repair_candidate_fold_count") is not None
            else candidate.get("total_r_repair_candidate_fold_count")
        )
        candidate["median_best_total_r_deficit"] = (
            walk_forward.get("median_best_total_r_deficit")
            if walk_forward.get("median_best_total_r_deficit") is not None
            else candidate.get("median_best_total_r_deficit")
        )
        candidate["max_best_total_r_deficit"] = (
            walk_forward.get("max_best_total_r_deficit")
            if walk_forward.get("max_best_total_r_deficit") is not None
            else candidate.get("max_best_total_r_deficit")
        )
        candidate["best_failed_total_r_by_fold"] = self._as_list(
            walk_forward.get("best_failed_total_r_by_fold")
            or candidate.get("best_failed_total_r_by_fold")
        )[: self.SUMMARY_BEST_FAILED_TOTAL_R_FOLD_LIMIT]
        candidate["best_failed_total_r_by_fold_total_count"] = (
            walk_forward.get("best_failed_total_r_by_fold_total_count")
            if walk_forward.get("best_failed_total_r_by_fold_total_count") is not None
            else candidate.get("best_failed_total_r_by_fold_total_count")
        )
        candidate["best_failed_total_r_by_fold_truncated"] = (
            walk_forward.get("best_failed_total_r_by_fold_truncated")
            if walk_forward.get("best_failed_total_r_by_fold_truncated") is not None
            else candidate.get("best_failed_total_r_by_fold_truncated")
        )
        validation_board = self._as_dict(
            walk_forward.get("walk_forward_validation_candidate_board")
            or candidate.get("walk_forward_validation_candidate_board")
        )
        candidate["walk_forward_validation_candidate_board"] = validation_board
        candidate["validation_candidate_board_rows"] = self._as_list(
            validation_board.get("candidate_board_rows")
            or candidate.get("validation_candidate_board_rows")
        )
        candidate["validation_candidate_board_rows_total_count"] = (
            validation_board.get("candidate_board_rows_total_count")
            if validation_board.get("candidate_board_rows_total_count") is not None
            else candidate.get("validation_candidate_board_rows_total_count")
        )
        candidate["validation_candidate_board_rows_truncated"] = (
            validation_board.get("candidate_board_rows_truncated")
            if validation_board.get("candidate_board_rows_truncated") is not None
            else candidate.get("validation_candidate_board_rows_truncated")
        )
        candidate["fold_time_slice_blackout_summary"] = self._compact_preview_dict(
            candidate.get("fold_repair_probe_diagnostics")
            or self._as_dict(candidate.get("profit_aware_diagnostics")).get(
                "fold_time_slice_blackout_summary"
            )
        )
        candidate["fold_feature_regime_filter_summary"] = self._compact_fold_feature_summary(
            self._as_dict(
                candidate.get("fold_feature_regime_filter_summary")
                or self._as_dict(candidate.get("profit_aware_diagnostics")).get(
                    "fold_feature_regime_filter_summary"
                )
            )
        )
        return candidate

    def _compact_ranked_result(self, value: Any) -> dict[str, Any]:
        row = self._object_to_dict_shallow(value)
        if not row:
            return {}

        walk_forward = self._compact_walk_forward_profit_diagnostics(
            row.get("walk_forward_profit_diagnostics")
        )
        payload = {
            "rank": row.get("rank"),
            "candidate_id": row.get("candidate_id"),
            "config_id": row.get("config_id"),
            "score": row.get("score"),
            "status": row.get("status"),
            "quality_status": row.get("quality_status"),
            "candidate_status": row.get("candidate_status"),
            "failed_gates": self._as_list(row.get("failed_gates")),
            "passed_gates": self._as_list(row.get("passed_gates")),
            "warnings": self._as_list(row.get("warnings")),
            "recommendations": self._as_list(row.get("recommendations")),
            "label_config": self._as_dict(row.get("label_config")),
            "directional_side_filter_profile": row.get("directional_side_filter_profile"),
            "allowed_signal_directions": self._as_list(row.get("allowed_signal_directions")),
            "profit_factor": row.get("profit_factor"),
            "profit_total_r": row.get("profit_total_r"),
            "walk_forward_profit_factor": row.get("walk_forward_profit_factor"),
            "walk_forward_total_r": row.get("walk_forward_total_r"),
            "walk_forward_global_total_r": row.get("walk_forward_global_total_r"),
            "walk_forward_profit_diagnostics": walk_forward,
            "walk_forward_validation_candidate_board_status": (
                walk_forward.get("walk_forward_validation_candidate_board_status")
                or row.get("walk_forward_validation_candidate_board_status")
            ),
            "walk_forward_validation_candidate_board_verdict": (
                walk_forward.get("walk_forward_validation_candidate_board_verdict")
                or row.get("walk_forward_validation_candidate_board_verdict")
            ),
            "validation_fold_root_cause_summary": self._as_dict(
                walk_forward.get("validation_fold_root_cause_summary")
                or row.get("validation_fold_root_cause_summary")
            ),
            "worst_fold_root_cause": self._compact_worst_fold_root_cause(
                walk_forward.get("worst_fold_root_cause")
                or row.get("worst_fold_root_cause")
            ),
            "primary_validation_root_cause_counts": self._as_dict(
                walk_forward.get("primary_validation_root_cause_counts")
                or row.get("primary_validation_root_cause_counts")
            ),
            "fold_root_cause_count": (
                self._as_dict(walk_forward.get("walk_forward_validation_candidate_board")).get(
                    "fold_root_cause_count"
                )
                or row.get("fold_root_cause_count")
            ),
            "recommended_validation_repair_profile": (
                walk_forward.get("recommended_validation_repair_profile")
                or row.get("recommended_validation_repair_profile")
            ),
            "total_r_below_min_fold_count": (
                walk_forward.get("total_r_below_min_fold_count")
                if walk_forward.get("total_r_below_min_fold_count") is not None
                else row.get("total_r_below_min_fold_count")
            ),
            "total_r_repair_candidate_fold_count": (
                walk_forward.get("total_r_repair_candidate_fold_count")
                if walk_forward.get("total_r_repair_candidate_fold_count") is not None
                else row.get("total_r_repair_candidate_fold_count")
            ),
            "median_best_total_r_deficit": (
                walk_forward.get("median_best_total_r_deficit")
                if walk_forward.get("median_best_total_r_deficit") is not None
                else row.get("median_best_total_r_deficit")
            ),
            "max_best_total_r_deficit": (
                walk_forward.get("max_best_total_r_deficit")
                if walk_forward.get("max_best_total_r_deficit") is not None
                else row.get("max_best_total_r_deficit")
            ),
            "best_failed_total_r_by_fold": self._as_list(
                walk_forward.get("best_failed_total_r_by_fold")
                or row.get("best_failed_total_r_by_fold")
            )[: self.SUMMARY_BEST_FAILED_TOTAL_R_FOLD_LIMIT],
            "best_failed_total_r_by_fold_total_count": (
                walk_forward.get("best_failed_total_r_by_fold_total_count")
                if walk_forward.get("best_failed_total_r_by_fold_total_count") is not None
                else row.get("best_failed_total_r_by_fold_total_count")
            ),
            "best_failed_total_r_by_fold_truncated": (
                walk_forward.get("best_failed_total_r_by_fold_truncated")
                if walk_forward.get("best_failed_total_r_by_fold_truncated") is not None
                else row.get("best_failed_total_r_by_fold_truncated")
            ),
            "walk_forward_validation_candidate_board": self._as_dict(
                walk_forward.get("walk_forward_validation_candidate_board")
                or row.get("walk_forward_validation_candidate_board")
            ),
            "validation_candidate_board_rows": self._as_list(
                self._as_dict(
                    walk_forward.get("walk_forward_validation_candidate_board")
                    or row.get("walk_forward_validation_candidate_board")
                ).get("candidate_board_rows")
                or row.get("validation_candidate_board_rows")
            ),
            "validation_candidate_board_rows_total_count": (
                self._as_dict(
                    walk_forward.get("walk_forward_validation_candidate_board")
                    or row.get("walk_forward_validation_candidate_board")
                ).get("candidate_board_rows_total_count")
                if self._as_dict(
                    walk_forward.get("walk_forward_validation_candidate_board")
                    or row.get("walk_forward_validation_candidate_board")
                ).get("candidate_board_rows_total_count") is not None
                else row.get("validation_candidate_board_rows_total_count")
            ),
            "validation_candidate_board_rows_truncated": (
                self._as_dict(
                    walk_forward.get("walk_forward_validation_candidate_board")
                    or row.get("walk_forward_validation_candidate_board")
                ).get("candidate_board_rows_truncated")
                if self._as_dict(
                    walk_forward.get("walk_forward_validation_candidate_board")
                    or row.get("walk_forward_validation_candidate_board")
                ).get("candidate_board_rows_truncated") is not None
                else row.get("validation_candidate_board_rows_truncated")
            ),
            "research_only_total_r_repair_enabled": row.get(
                "research_only_total_r_repair_enabled"
            ),
            "validation_total_r_repair_profile": row.get(
                "validation_total_r_repair_profile"
            ),
            "research_only_fold_repair_probe_enabled": row.get(
                "research_only_fold_repair_probe_enabled"
            ),
            "fold_repair_probe_profile": row.get("fold_repair_probe_profile"),
            "fold_repair_target_dates": self._as_list(row.get("fold_repair_target_dates")),
            "fold_repair_time_slice_blackout_enabled": row.get(
                "fold_repair_time_slice_blackout_enabled"
            ),
            "fold_repair_blackout_dates": self._as_list(row.get("fold_repair_blackout_dates")),
            "fold_repair_feature_filter_enabled": row.get(
                "fold_repair_feature_filter_enabled"
            ),
            "fold_repair_feature_filter_profile": row.get(
                "fold_repair_feature_filter_profile"
            ),
            "fold_repair_feature_filter_rules": self._as_dict(
                row.get("fold_repair_feature_filter_rules")
            ),
            "fold_feature_regime_filter_summary": self._compact_fold_feature_summary(
                row.get("fold_feature_regime_filter_summary")
                or self._as_dict(row.get("profit_aware_diagnostics")).get(
                    "fold_feature_regime_filter_summary"
                )
            ),
            "fold_time_slice_blackout_summary": self._as_dict(
                row.get("fold_repair_probe_diagnostics")
                or self._as_dict(row.get("profit_aware_diagnostics")).get(
                    "fold_time_slice_blackout_summary"
                )
            ),
            "prediction_root_cause_audit": self._as_dict(
                row.get("prediction_root_cause_audit")
            ),
            "book_driven_forensic_audit": self._as_dict(
                row.get("book_driven_forensic_audit")
            ),
            "label_mode_comparison_audit": self._as_dict(
                row.get("label_mode_comparison_audit")
            ),
            "flat_subtype_audit": self._as_dict(row.get("flat_subtype_audit")),
            "setup_aware_label_diagnostics": self._as_dict(
                row.get("setup_aware_label_diagnostics")
            ),
            "schwager_slice_robustness": self._as_dict(
                row.get("schwager_slice_robustness")
            ),
            "schwager_robustness_decision_board": self._as_dict(
                row.get("schwager_robustness_decision_board")
            ),
            "decision_policy_grid_diagnostics": self._as_dict(
                row.get("decision_policy_grid_diagnostics")
            ),
            "decision_policy_selected_policy_id": row.get(
                "decision_policy_selected_policy_id"
            ),
            "entry_path_quality_filter_enabled": row.get(
                "entry_path_quality_filter_enabled"
            ),
            "entry_path_quality_min_threshold": row.get(
                "entry_path_quality_min_threshold"
            ),
            "stop_pressure_max_risk_score": row.get("stop_pressure_max_risk_score"),
            "mae_pressure_max_risk_score": row.get("mae_pressure_max_risk_score"),
        }
        for key in (
            "fold_time_slice_blackout_summary",
            "prediction_root_cause_audit",
            "book_driven_forensic_audit",
            "label_mode_comparison_audit",
            "flat_subtype_audit",
            "setup_aware_label_diagnostics",
            "schwager_slice_robustness",
            "schwager_robustness_decision_board",
            "decision_policy_grid_diagnostics",
        ):
            payload[key] = self._compact_preview_dict(payload.get(key))
        return payload

    def _best_candidate_payload(
        self,
        candidates: list[dict[str, Any]],
        *,
        best_candidate_config_id: Any,
    ) -> dict[str, Any]:
        best_config_id = None if best_candidate_config_id is None else str(best_candidate_config_id)
        if best_config_id:
            for candidate in candidates:
                if str(candidate.get("config_id")) == best_config_id:
                    return candidate
        return candidates[0] if candidates else {}

    def _summary_json_text(self, payload: dict[str, Any]) -> str:
        text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        if len(text.encode("utf-8")) <= self.SUMMARY_JSON_SOFT_MAX_BYTES:
            return text
        return json.dumps(payload, ensure_ascii=False, indent=None, sort_keys=True)

    def _write_json_payload(
        self,
        payload: dict[str, Any],
        output_path: str | Path,
        *,
        indent: int | None,
    ) -> None:
        path = Path(output_path)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=indent, sort_keys=True)
            handle.write("\n")

    def result_to_json(self, result: object, *, indent: int | None = 2) -> str:
        return json.dumps(
            self.result_to_dict(result),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def compact_summary_to_dict(self, result: object) -> dict[str, Any]:
        direct_keys = (
            "status",
            "experiment_id",
            "experiment_status",
            "symbol",
            "interval",
            "start_date",
            "end_date",
            "config_count",
            "candidate_count",
            "evaluated_candidate_count",
            "failed_candidate_count",
            "accepted_candidate_count",
            "rejected_candidate_count",
            "best_candidate_id",
            "best_candidate_config_id",
            "best_candidate_score",
            "feature_quality_summary",
            "feature_group_quality_summary",
            "regime_feature_summary",
            "feature_leakage_summary",
            "regime_experiment_plan_summary",
            "failed_gates_summary",
            "warnings",
            "recommendations",
            "regime_training_applied",
            "real_feature_diagnostics_used",
            "real_feature_diagnostics_row_count",
            "feature_version_used",
            "regime_features_attached",
            "regime_feature_count",
            "regime_feature_source",
            "regime_specific_labeling_available",
            "regime_specific_training_applied",
            "missing_requirements",
            "effective_gap_count_for_training",
            "gap_severity_for_training",
            "gap_training_safe",
            "output_dir",
            "log_path",
            "events_path",
            "summary_json_path",
            "summary_markdown_path",
            "baseline_reference",
            "probability_diagnostics",
            "probability_diagnostics_missing_reason",
            "real_feature_diagnostics",
            "real_feature_diagnostics_missing_reason",
            "collapse_diagnostics_v2",
            "collapse_diagnostics_v2_missing_reason",
            "regime_label_builder_status",
            "regime_label_builder_status_missing_reason",
            "walk_forward_profit_diagnostics_missing_reason",
            "profit_aware_diagnostics",
            "profit_aware_diagnostics_missing_reason",
            "regime_label_builder_used_in_training_any",
            "regime_label_builder_used_in_training_all",
            "regime_specific_training_applied_any",
            "regime_specific_training_applied_all",
            "candle_ta_context_features_attached",
            "candle_ta_context_feature_count",
            "candle_ta_context_missing_reason",
            "book_setup_context_features_attached",
            "book_setup_context_feature_count",
            "book_setup_context_missing_reason",
            "fv4_feature_count",
            "nison_feature_count",
            "altunina_feature_count",
            "path_context_feature_count",
            "htf_context_feature_count",
            "missing_context_feature_count",
            "regime_features_missing_reason",
            "candidate_status",
            "model_quality_validation_status",
            "model_accepted",
            "reasons_why_best_still_rejected",
            "flat_bias_summary",
            "down_blindness_summary",
            "baseline_edge_summary",
            "label_mode_comparison_audit",
            "flat_subtype_audit",
            "setup_aware_label_diagnostics",
            "schwager_slice_robustness",
            "schwager_robustness_decision_board",
            "class_margin_objective_decision",
        )
        payload = {
            key: self._result_value(result, key)
            for key in direct_keys
        }
        for key in (
            "baseline_reference",
            "probability_diagnostics",
            "feature_quality_summary",
            "feature_group_quality_summary",
            "regime_feature_summary",
            "feature_leakage_summary",
            "regime_experiment_plan_summary",
            "real_feature_diagnostics",
            "collapse_diagnostics_v2",
            "regime_label_builder_status",
            "profit_aware_diagnostics",
            "flat_bias_summary",
            "down_blindness_summary",
            "baseline_edge_summary",
            "label_mode_comparison_audit",
            "flat_subtype_audit",
            "setup_aware_label_diagnostics",
            "schwager_slice_robustness",
            "schwager_robustness_decision_board",
            "class_margin_objective_decision",
        ):
            payload[key] = self._compact_preview_dict(payload.get(key))

        candidate_results_source = self._as_list(self._result_value(result, "candidate_results"))
        ranking_source = self._as_list(self._result_value(result, "ranking"))
        configs_ranked_source = self._as_list(
            self._result_value(result, "configs_ranked", ranking_source)
        ) or ranking_source

        compact_candidates = [
            self._compact_candidate_result(item)
            for item in candidate_results_source[: self.SUMMARY_CANDIDATE_RESULT_LIMIT]
        ]
        compact_ranking = [
            self._compact_ranked_result(item)
            for item in ranking_source[: self.SUMMARY_CONFIGS_RANKED_LIMIT]
        ]
        compact_configs_ranked = [
            self._compact_ranked_result(item)
            for item in configs_ranked_source[: self.SUMMARY_CONFIGS_RANKED_LIMIT]
        ]

        best_candidate = self._best_candidate_payload(
            compact_candidates,
            best_candidate_config_id=payload.get("best_candidate_config_id"),
        )

        walk_forward_diag = self._compact_walk_forward_profit_diagnostics(
            self._result_value(result, "walk_forward_profit_diagnostics")
            or best_candidate.get("walk_forward_profit_diagnostics")
        )
        recovery_diag = self._as_dict(
            best_candidate.get("directional_side_signal_recovery_diagnostics")
            or walk_forward_diag.get("directional_side_signal_recovery_diagnostics")
        )

        payload.update(
            {
                "summary_payload_mode": self.SUMMARY_PAYLOAD_MODE,
                "summary_payload_compacted": True,
                "candidate_results_total_count": len(candidate_results_source),
                "candidate_results_included_count": len(compact_candidates),
                "candidate_results_truncated": len(candidate_results_source)
                > len(compact_candidates),
                "candidate_results": compact_candidates,
                "ranking_total_count": len(ranking_source),
                "ranking_included_count": len(compact_ranking),
                "ranking_truncated": len(ranking_source) > len(compact_ranking),
                "ranking": compact_ranking,
                "configs_ranked_total_count": len(configs_ranked_source),
                "configs_ranked_included_count": len(compact_configs_ranked),
                "configs_ranked_truncated": len(configs_ranked_source)
                > len(compact_configs_ranked),
                "configs_ranked": compact_configs_ranked,
                "feature_weak_signal_detected": self._as_dict(
                    payload.get("feature_quality_summary")
                ).get("weak_signal_detected"),
                "regime_data_available": self._as_dict(
                    payload.get("regime_feature_summary")
                ).get("regime_data_available"),
                "feature_leakage_risk_detected": self._as_dict(
                    payload.get("feature_leakage_summary")
                ).get("leakage_risk_detected"),
                "walk_forward_profit_diagnostics": walk_forward_diag,
                "directional_side_signal_recovery_diagnostics": recovery_diag,
                "directional_side_signal_recovery_status": (
                    recovery_diag.get("diagnostic_status")
                    or payload.get("directional_side_signal_recovery_status")
                ),
                "directional_side_signal_recovery_verdict": (
                    recovery_diag.get("verdict")
                    or payload.get("directional_side_signal_recovery_verdict")
                ),
                "primary_signal_loss_reason_counts": self._as_dict(
                    recovery_diag.get("primary_signal_loss_reason_counts")
                    or best_candidate.get("primary_signal_loss_reason_counts")
                ),
                "validation_gate_failure_reason_counts": self._as_dict(
                    walk_forward_diag.get("validation_gate_failure_reason_counts")
                    or best_candidate.get("validation_gate_failure_reason_counts")
                ),
                "side_aware_relaxed_fold_count": walk_forward_diag.get(
                    "side_aware_relaxed_fold_count",
                    best_candidate.get("side_aware_relaxed_fold_count"),
                ),
                "walk_forward_validation_candidate_board_status": (
                    walk_forward_diag.get("walk_forward_validation_candidate_board_status")
                    or best_candidate.get("walk_forward_validation_candidate_board_status")
                ),
                "walk_forward_validation_candidate_board_verdict": (
                    walk_forward_diag.get("walk_forward_validation_candidate_board_verdict")
                    or best_candidate.get("walk_forward_validation_candidate_board_verdict")
                ),
                "recommended_validation_repair_profile": (
                    walk_forward_diag.get("recommended_validation_repair_profile")
                    or best_candidate.get("recommended_validation_repair_profile")
                ),
                "total_r_below_min_fold_count": (
                    walk_forward_diag.get("total_r_below_min_fold_count")
                    if walk_forward_diag.get("total_r_below_min_fold_count") is not None
                    else best_candidate.get("total_r_below_min_fold_count")
                ),
                "total_r_repair_candidate_fold_count": (
                    walk_forward_diag.get("total_r_repair_candidate_fold_count")
                    if walk_forward_diag.get("total_r_repair_candidate_fold_count") is not None
                    else best_candidate.get("total_r_repair_candidate_fold_count")
                ),
                "median_best_total_r_deficit": (
                    walk_forward_diag.get("median_best_total_r_deficit")
                    if walk_forward_diag.get("median_best_total_r_deficit") is not None
                    else best_candidate.get("median_best_total_r_deficit")
                ),
                "max_best_total_r_deficit": (
                    walk_forward_diag.get("max_best_total_r_deficit")
                    if walk_forward_diag.get("max_best_total_r_deficit") is not None
                    else best_candidate.get("max_best_total_r_deficit")
                ),
                "research_only_total_r_repair_enabled": best_candidate.get(
                    "research_only_total_r_repair_enabled"
                ),
                "validation_total_r_repair_profile": best_candidate.get(
                    "validation_total_r_repair_profile"
                ),
                "research_only_fold_repair_probe_enabled": best_candidate.get(
                    "research_only_fold_repair_probe_enabled"
                ),
                "fold_repair_probe_profile": best_candidate.get(
                    "fold_repair_probe_profile"
                ),
                "fold_repair_target_dates": self._as_list(
                    best_candidate.get("fold_repair_target_dates")
                ),
                "fold_repair_time_slice_blackout_enabled": best_candidate.get(
                    "fold_repair_time_slice_blackout_enabled"
                ),
                "fold_repair_blackout_dates": self._as_list(
                    best_candidate.get("fold_repair_blackout_dates")
                ),
                "fold_repair_feature_filter_enabled": best_candidate.get(
                    "fold_repair_feature_filter_enabled"
                ),
                "fold_repair_feature_filter_profile": best_candidate.get(
                    "fold_repair_feature_filter_profile"
                ),
                "fold_repair_feature_filter_rules": self._as_dict(
                    best_candidate.get("fold_repair_feature_filter_rules")
                ),
                "fold_feature_regime_filter_summary": self._compact_fold_feature_summary(
                    best_candidate.get("fold_feature_regime_filter_summary")
                    or self._as_dict(best_candidate.get("profit_aware_diagnostics")).get(
                        "fold_feature_regime_filter_summary"
                    )
                ),
                "fold_time_slice_blackout_summary": self._as_dict(
                    best_candidate.get("fold_repair_probe_diagnostics")
                    or self._as_dict(best_candidate.get("profit_aware_diagnostics")).get(
                        "fold_time_slice_blackout_summary"
                    )
                ),
                "directional_edge_bias_audit": self._as_dict(
                    best_candidate.get("directional_edge_bias_audit")
                ),
                "directional_side_filter_summary": self._as_dict(
                    best_candidate.get("directional_side_filter_summary")
                ),
                "directional_side_filter_profile": best_candidate.get(
                    "directional_side_filter_profile"
                ),
                "allowed_signal_directions": self._as_list(
                    best_candidate.get("allowed_signal_directions")
                ),
                "profit_exit_root_cause_audit": self._as_dict(
                    best_candidate.get("profit_exit_root_cause_audit")
                    or self._as_dict(best_candidate.get("profit_aware_diagnostics")).get(
                        "profit_exit_root_cause_audit"
                    )
                ),
                "walk_forward_profit_exit_root_cause_summary": self._as_dict(
                    best_candidate.get("walk_forward_profit_exit_root_cause_summary")
                    or walk_forward_diag.get("walk_forward_profit_exit_root_cause_summary")
                ),
                "opportunity_probability_threshold": best_candidate.get(
                    "opportunity_probability_threshold"
                ),
                "setup_quality_min_threshold": best_candidate.get(
                    "setup_quality_min_threshold"
                ),
                "setup_quality_decision_mask_enabled": best_candidate.get(
                    "setup_quality_decision_mask_enabled"
                ),
                "setup_quality_decision_mask_min_threshold": best_candidate.get(
                    "setup_quality_decision_mask_min_threshold"
                ),
                "selected_opportunity_threshold": best_candidate.get(
                    "selected_opportunity_threshold"
                ),
                "opportunity_threshold_selection": self._as_dict(
                    best_candidate.get("opportunity_threshold_selection")
                ),
                "opportunity_threshold_sweep": self._as_dict(
                    best_candidate.get("opportunity_threshold_sweep")
                ),
                "setup_quality_filter_passed": best_candidate.get(
                    "setup_quality_filter_passed"
                ),
                "setup_quality_bucket_metrics": self._as_dict(
                    best_candidate.get("setup_quality_bucket_metrics")
                ),
                "setup_quality_bucket_metrics_raw": self._as_dict(
                    best_candidate.get("setup_quality_bucket_metrics_raw")
                ),
                "setup_quality_bucket_metrics_after_mask": self._as_dict(
                    best_candidate.get("setup_quality_bucket_metrics_after_mask")
                ),
                "setup_quality_filter_summary": self._as_dict(
                    best_candidate.get("setup_quality_filter_summary")
                ),
                "setup_quality_decision_mask_summary": self._as_dict(
                    best_candidate.get("setup_quality_decision_mask_summary")
                ),
                "entry_path_quality_filter_enabled": best_candidate.get(
                    "entry_path_quality_filter_enabled"
                ),
                "entry_path_quality_min_threshold": best_candidate.get(
                    "entry_path_quality_min_threshold"
                ),
                "stop_pressure_max_risk_score": best_candidate.get(
                    "stop_pressure_max_risk_score"
                ),
                "mae_pressure_max_risk_score": best_candidate.get(
                    "mae_pressure_max_risk_score"
                ),
                "entry_path_quality_masked_row_count": best_candidate.get(
                    "entry_path_quality_masked_row_count"
                ),
                "entry_path_quality_forced_no_trade_count": best_candidate.get(
                    "entry_path_quality_forced_no_trade_count"
                ),
                "entry_path_quality_mask_trade_prediction_removed_count": best_candidate.get(
                    "entry_path_quality_mask_trade_prediction_removed_count"
                ),
                "entry_path_quality_mask_false_positive_removed_count": best_candidate.get(
                    "entry_path_quality_mask_false_positive_removed_count"
                ),
                "entry_path_quality_filter_summary": self._as_dict(
                    best_candidate.get("entry_path_quality_filter_summary")
                ),
                "entry_path_quality_filter_diagnostics": self._as_dict(
                    best_candidate.get("entry_path_quality_filter_diagnostics")
                ),
                "entry_path_prediction_filter_summary": self._as_dict(
                    best_candidate.get("entry_path_prediction_filter_summary")
                ),
                "stop_pressure_effectiveness_audit": self._as_dict(
                    best_candidate.get("stop_pressure_effectiveness_audit")
                ),
                "predicted_to_actual_trade_rate_ratio": best_candidate.get(
                    "predicted_to_actual_trade_rate_ratio"
                ),
                "predicted_trade_rate": best_candidate.get("predicted_trade_rate"),
                "raw_predicted_trade_rate": best_candidate.get("raw_predicted_trade_rate"),
                "masked_predicted_trade_rate": best_candidate.get(
                    "masked_predicted_trade_rate"
                ),
                "actual_trade_rate": best_candidate.get("actual_trade_rate"),
                "opportunity_precision": best_candidate.get("opportunity_precision"),
                "opportunity_recall": best_candidate.get("opportunity_recall"),
                "opportunity_f1": best_candidate.get("opportunity_f1"),
                "raw_opportunity_precision": best_candidate.get("raw_opportunity_precision"),
                "raw_opportunity_recall": best_candidate.get("raw_opportunity_recall"),
                "raw_opportunity_f1": best_candidate.get("raw_opportunity_f1"),
                "opportunity_false_positive_rate": best_candidate.get(
                    "opportunity_false_positive_rate"
                ),
                "two_stage_trade_diagnostics": self._as_dict(
                    best_candidate.get("two_stage_trade_diagnostics")
                ),
                "trap_invalidation_feature_impact_audit": self._as_dict(
                    self._as_dict(best_candidate.get("two_stage_trade_diagnostics")).get(
                        "trap_invalidation_feature_impact_audit"
                    )
                    or best_candidate.get("trap_invalidation_feature_impact_audit")
                ),
                "approved_for_live_trading": False,
                "approved_for_auto_activation": False,
                "orders_enabled": False,
                "traders_core_connected": False,
            }
        )
        payload["directional_side_ablation_comparator"] = (
            self._directional_side_ablation_comparator(payload)
        )
        payload["directional_side_walk_forward_stability"] = (
            self._directional_side_walk_forward_stability(payload)
        )
        return payload

    def compact_summary_to_json(self, result: object, *, indent: int | None = 2) -> str:
        return json.dumps(
            self.compact_summary_to_dict(result),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def write_summary_json(self, result: object, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = self.compact_summary_to_dict(result)
        self._write_json_payload(payload, path, indent=2)
        if path.stat().st_size > self.SUMMARY_JSON_SOFT_MAX_BYTES:
            self._write_json_payload(payload, path, indent=None)
        return path

    def write_summary_markdown(self, result: object, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            self._summary_markdown(self.compact_summary_to_dict(result)),
            encoding="utf-8",
        )
        return path

    def write_diagnostics_json(self, diagnostics: dict[str, Any], output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(diagnostics, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def write_candidate_json(self, candidate: object, output_path: str | Path) -> Path:
        payload = self._candidate_to_dict(candidate)
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def write_candidate_markdown(self, candidate: object, output_path: str | Path) -> Path:
        payload = self._candidate_to_dict(candidate)
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._candidate_markdown(payload), encoding="utf-8")
        return path

    @staticmethod
    def _candidate_to_dict(candidate: object) -> dict[str, Any]:
        if isinstance(candidate, dict):
            return dict(candidate)
        to_dict = getattr(candidate, "to_dict", None)
        if callable(to_dict):
            return dict(to_dict())
        raise TypeError("candidate must be a dict or provide to_dict()")

    def _directional_side_ablation_comparator(self, payload: dict[str, Any]) -> dict[str, Any]:
        existing = payload.get("directional_side_ablation_comparator")
        if isinstance(existing, dict) and existing:
            return dict(existing)
        candidates = [
            item
            for item in self._as_list(payload.get("candidate_results") or payload.get("configs_ranked"))
            if isinstance(item, dict)
        ]
        return DirectionalSideAblationComparator().compare(candidates)

    def _directional_side_walk_forward_stability(self, payload: dict[str, Any]) -> dict[str, Any]:
        existing = payload.get("directional_side_walk_forward_stability")
        if isinstance(existing, dict) and existing:
            return dict(existing)
        candidates = [
            item
            for item in self._as_list(payload.get("candidate_results") or payload.get("configs_ranked"))
            if isinstance(item, dict)
        ]
        return DirectionalSideWalkForwardStabilityAnalyzer().analyze(candidates)

    def _summary_markdown(self, payload: dict[str, Any]) -> str:
        comparator = self._directional_side_ablation_comparator(payload)
        stability = self._directional_side_walk_forward_stability(payload)
        walk_forward_diag = self._as_dict(payload.get("walk_forward_profit_diagnostics"))
        worst_fold_root_cause = self._as_dict(payload.get("worst_fold_root_cause"))
        lines = [
            f"# Feature/Regime Experiment Summary - {payload.get('experiment_id')}",
            "",
            "## Run",
            "",
            f"- experiment id: `{payload.get('experiment_id')}`",
            f"- symbol: `{payload.get('symbol')}`",
            f"- interval: `{payload.get('interval')}`",
            f"- start_date: `{payload.get('start_date')}`",
            f"- end_date: `{payload.get('end_date')}`",
            f"- status: `{payload.get('status')}`",
            f"- experiment_status: `{payload.get('experiment_status')}`",
            f"- evaluated_candidate_count: `{payload.get('evaluated_candidate_count')}`",
            f"- failed_candidate_count: `{payload.get('failed_candidate_count')}`",
            f"- feature_version_used: `{payload.get('feature_version_used')}`",
            f"- regime_training_applied: `{payload.get('regime_training_applied')}`",
            f"- regime_specific_training_applied: `{payload.get('regime_specific_training_applied')}`",
            f"- regime_label_builder_used_in_training_any: `{payload.get('regime_label_builder_used_in_training_any')}`",
            f"- regime_label_builder_used_in_training_all: `{payload.get('regime_label_builder_used_in_training_all')}`",
            f"- regime_specific_training_applied_any: `{payload.get('regime_specific_training_applied_any')}`",
            f"- regime_specific_training_applied_all: `{payload.get('regime_specific_training_applied_all')}`",
            f"- real_feature_diagnostics_used: `{payload.get('real_feature_diagnostics_used')}`",
            f"- real_feature_diagnostics_row_count: `{payload.get('real_feature_diagnostics_row_count')}`",
            f"- regime_label_builder_status: `{payload.get('regime_label_builder_status')}`",
            f"- effective_gap_count_for_training: `{payload.get('effective_gap_count_for_training')}`",
            f"- gap_severity_for_training: `{payload.get('gap_severity_for_training')}`",
            "",
            "## Feature Diagnostics Summary",
            "",
            f"- feature diagnostics summary: `{payload.get('feature_quality_summary')}`",
            f"- feature group diagnostics summary: `{payload.get('feature_group_quality_summary')}`",
            "",
            "## Regime Diagnostics Summary",
            "",
            f"- regime diagnostics summary: `{payload.get('regime_feature_summary')}`",
            f"- regime_features_attached: `{payload.get('regime_features_attached')}`",
            f"- regime_feature_count: `{payload.get('regime_feature_count')}`",
            f"- book_setup_context_features_attached: `{payload.get('book_setup_context_features_attached')}`",
            f"- book_setup_context_feature_count: `{payload.get('book_setup_context_feature_count')}`",
            f"- fv4_feature_count: `{payload.get('fv4_feature_count')}`",
            f"- nison_feature_count: `{payload.get('nison_feature_count')}`",
            f"- altunina_feature_count: `{payload.get('altunina_feature_count')}`",
            f"- path_context_feature_count: `{payload.get('path_context_feature_count')}`",
            f"- htf_context_feature_count: `{payload.get('htf_context_feature_count')}`",
            f"- missing_context_feature_count: `{payload.get('missing_context_feature_count')}`",
            f"- regime plan readiness: `{self._as_dict(payload.get('regime_experiment_plan_summary')).get('ready_for_real_regime_training')}`",
            f"- missing_requirements: `{payload.get('missing_requirements')}`",
            "",
            "## Feature Leakage Summary",
            "",
            f"- feature leakage summary: `{payload.get('feature_leakage_summary')}`",
            "",
            "## Candidate Ranking",
            "",
            "| Rank | Candidate | Config | Score | Candidate Status | Failed Gates | Repair Profile | Total-R Folds | Median Deficit | Research Only |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for row in self._as_list(payload.get("ranking")):
            lines.append(
                "| `{rank}` | `{candidate_id}` | `{config_id}` | `{score}` | `{candidate_status}` | `{failed_gates}` | `{repair}` | `{folds}` | `{median}` | `{research_only}` |".format(
                    rank=row.get("rank"),
                    candidate_id=row.get("candidate_id"),
                    config_id=row.get("config_id"),
                    score=row.get("score"),
                    candidate_status=row.get("candidate_status"),
                    failed_gates=",".join(self._as_list(row.get("failed_gates"))),
                    repair=row.get("recommended_validation_repair_profile"),
                    folds=row.get("total_r_below_min_fold_count"),
                    median=row.get("median_best_total_r_deficit"),
                    research_only=row.get("research_only_total_r_repair_enabled"),
                )
            )
        if not self._as_list(payload.get("ranking")):
            lines.append("| `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` |")
        lines.extend(
            [
                "",
                "## Best Candidate",
                "",
                f"- best candidate: `{payload.get('best_candidate_id')}`",
                f"- best_candidate_config_id: `{payload.get('best_candidate_config_id')}`",
            f"- best_candidate_score: `{payload.get('best_candidate_score')}`",
            f"- why accepted/rejected: `{payload.get('experiment_status')}`",
            f"- collapse_diagnostics_v2: `{payload.get('collapse_diagnostics_v2')}`",
            f"- flat_bias_summary: `{payload.get('flat_bias_summary')}`",
            f"- down_blindness_summary: `{payload.get('down_blindness_summary')}`",
            f"- baseline_edge_summary: `{payload.get('baseline_edge_summary')}`",
            f"- reasons_why_best_still_rejected: `{payload.get('reasons_why_best_still_rejected')}`",
            f"- walk_forward_profit_diagnostics: `{payload.get('walk_forward_profit_diagnostics')}`",
            f"- directional_side_signal_recovery_status: `{payload.get('directional_side_signal_recovery_status')}`",
            f"- directional_side_signal_recovery_verdict: `{payload.get('directional_side_signal_recovery_verdict')}`",
            f"- primary_signal_loss_reason_counts: `{payload.get('primary_signal_loss_reason_counts')}`",
            f"- validation_gate_failure_reason_counts: `{payload.get('validation_gate_failure_reason_counts')}`",
            f"- side_aware_relaxed_fold_count: `{payload.get('side_aware_relaxed_fold_count')}`",
            f"- walk_forward_validation_candidate_board_status: `{payload.get('walk_forward_validation_candidate_board_status', walk_forward_diag.get('walk_forward_validation_candidate_board_status'))}`",
            f"- walk_forward_validation_candidate_board_verdict: `{payload.get('walk_forward_validation_candidate_board_verdict', walk_forward_diag.get('walk_forward_validation_candidate_board_verdict'))}`",
            f"- recommended_validation_repair_profile: `{payload.get('recommended_validation_repair_profile', walk_forward_diag.get('recommended_validation_repair_profile'))}`",
            f"- total_r_below_min_fold_count: `{payload.get('total_r_below_min_fold_count', walk_forward_diag.get('total_r_below_min_fold_count'))}`",
            f"- total_r_repair_candidate_fold_count: `{payload.get('total_r_repair_candidate_fold_count', walk_forward_diag.get('total_r_repair_candidate_fold_count'))}`",
            f"- median_best_total_r_deficit: `{payload.get('median_best_total_r_deficit', walk_forward_diag.get('median_best_total_r_deficit'))}`",
            f"- max_best_total_r_deficit: `{payload.get('max_best_total_r_deficit', walk_forward_diag.get('max_best_total_r_deficit'))}`",
            f"- research_only_total_r_repair_enabled: `{payload.get('research_only_total_r_repair_enabled')}`",
            f"- validation_total_r_repair_profile: `{payload.get('validation_total_r_repair_profile')}`",
            f"- profit_aware_diagnostics: `{payload.get('profit_aware_diagnostics')}`",
            f"- profit_exit_root_cause_audit: `{payload.get('profit_exit_root_cause_audit')}`",
            f"- walk_forward_profit_exit_root_cause_summary: `{payload.get('walk_forward_profit_exit_root_cause_summary')}`",
            f"- confidence_profitability_diagnostics: `{payload.get('confidence_profitability_diagnostics')}`",
            f"- selected_opportunity_threshold: `{payload.get('selected_opportunity_threshold')}`",
            f"- setup_quality_min_threshold: `{payload.get('setup_quality_min_threshold')}`",
            f"- setup_quality_decision_mask_enabled: `{payload.get('setup_quality_decision_mask_enabled')}`",
            f"- setup_quality_decision_mask_min_threshold: `{payload.get('setup_quality_decision_mask_min_threshold')}`",
            f"- setup_quality_filter_passed: `{payload.get('setup_quality_filter_passed')}`",
            f"- opportunity_precision: `{payload.get('opportunity_precision')}`",
            f"- opportunity_recall: `{payload.get('opportunity_recall')}`",
            f"- opportunity_f1: `{payload.get('opportunity_f1')}`",
            f"- entry_path_quality_filter_enabled: `{payload.get('entry_path_quality_filter_enabled')}`",
            f"- entry_path_quality_min_threshold: `{payload.get('entry_path_quality_min_threshold')}`",
            f"- stop_pressure_max_risk_score: `{payload.get('stop_pressure_max_risk_score')}`",
            f"- mae_pressure_max_risk_score: `{payload.get('mae_pressure_max_risk_score')}`",
            f"- directional_side_filter_profile: `{payload.get('directional_side_filter_profile')}`",
            f"- allowed_signal_directions: `{payload.get('allowed_signal_directions')}`",
            f"- directional_side_filter_summary: `{payload.get('directional_side_filter_summary')}`",
            f"- directional_edge_bias_audit: `{payload.get('directional_edge_bias_audit')}`",
            f"- entry_path_prediction_filter_summary: `{payload.get('entry_path_prediction_filter_summary')}`",
            f"- stop_pressure_effectiveness_audit: `{payload.get('stop_pressure_effectiveness_audit')}`",
            "",
            "## ML38.10.26 Validation fold root cause",
            "",
            (
                f"- status: `{worst_fold_root_cause.get('diagnostic_status')}`"
                if worst_fold_root_cause
                else "No validation fold root-cause diagnostics available."
            ),
            (
                f"- worst fold: `{worst_fold_root_cause.get('fold_index')}`"
                if worst_fold_root_cause
                else ""
            ),
            (
                f"- validation_total_r: `{worst_fold_root_cause.get('validation_total_r')}`"
                if worst_fold_root_cause
                else ""
            ),
            (
                f"- primary_root_cause: `{worst_fold_root_cause.get('primary_root_cause')}`"
                if worst_fold_root_cause
                else ""
            ),
            (
                f"- root_cause_flags: `{worst_fold_root_cause.get('root_cause_flags')}`"
                if worst_fold_root_cause
                else ""
            ),
            (
                f"- recommended repair: `{worst_fold_root_cause.get('recommendations')}`"
                if worst_fold_root_cause
                else ""
            ),
            "",
            "## Directional Side Ablation Comparator",
            "",
            f"- diagnostic_status: `{comparator.get('diagnostic_status')}`",
            f"- side_profile_counts: `{comparator.get('side_profile_counts')}`",
            f"- best_by_side_profile: `{comparator.get('best_by_side_profile')}`",
            f"- long_only_vs_both_delta: `{comparator.get('long_only_vs_both_delta')}`",
            f"- suppress_short_vs_both_delta: `{comparator.get('suppress_short_vs_both_delta')}`",
            f"- short_only_vs_both_delta: `{comparator.get('short_only_vs_both_delta')}`",
            f"- warnings: `{comparator.get('warnings')}`",
            f"- recommendations: `{comparator.get('recommendations')}`",
            "",
            "| Side profile | Config | PF | Total R | WF PF | WF R | Signals | Long R | Short R |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        comparison_board = self._as_list(comparator.get("comparison_board"))
        for row in comparison_board:
            lines.append(
                "| `{side}` | `{config}` | `{pf}` | `{total_r}` | `{wf_pf}` | `{wf_r}` | `{signals}` | `{long_r}` | `{short_r}` |".format(
                    side=self._as_dict(row).get("side_profile"),
                    config=self._as_dict(row).get("config_id"),
                    pf=self._as_dict(row).get("profit_factor"),
                    total_r=self._as_dict(row).get("profit_total_r"),
                    wf_pf=self._as_dict(row).get("walk_forward_profit_factor"),
                    wf_r=self._as_dict(row).get("walk_forward_total_r"),
                    signals=self._as_dict(row).get("resolved_signal_count"),
                    long_r=self._as_dict(row).get("long_total_r"),
                    short_r=self._as_dict(row).get("short_total_r"),
                )
            )
        if not comparison_board:
            lines.append("| `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` |")
        lines.extend(
            [
                "",
                "## Directional side walk-forward stability",
                "",
                f"- diagnostic_status: `{stability.get('diagnostic_status')}`",
                f"- best_research_side_profile: `{stability.get('best_research_side_profile')}`",
                f"- best_research_verdict: `{stability.get('best_research_verdict')}`",
                f"- warnings: `{stability.get('warnings')}`",
                f"- recommendations: `{stability.get('recommendations')}`",
                "",
                "## Label Mode Audits",
                "",
                f"- label_mode_comparison_audit: `{payload.get('label_mode_comparison_audit')}`",
                f"- flat_subtype_audit: `{payload.get('flat_subtype_audit')}`",
                f"- setup_aware_label_diagnostics: `{payload.get('setup_aware_label_diagnostics')}`",
                f"- schwager_slice_robustness: `{payload.get('schwager_slice_robustness')}`",
                f"- schwager_robustness_decision_board: `{payload.get('schwager_robustness_decision_board')}`",
                f"- class_margin_objective_decision: `{payload.get('class_margin_objective_decision')}`",
                "",
                "## Recommendations",
                "",
            ]
        )
        for item in self._as_list(payload.get("recommendations")):
            lines.append(f"- {item}")
        lines.extend(
            [
                "",
                "## Safety",
                "",
                "- no traders-core integration",
                "- no live trading",
                "- no orders",
                "- no auto activation",
                "",
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _candidate_markdown(payload: dict[str, Any]) -> str:
        root_cause_audit = dict(payload.get("prediction_root_cause_audit", {}))
        forensic_audit = dict(payload.get("book_driven_forensic_audit", {}))
        robustness_board = dict(payload.get("schwager_robustness_decision_board", {}))
        class_margin_decision = dict(payload.get("class_margin_objective_decision", {}))
        walk_forward_diag = dict(payload.get("walk_forward_profit_diagnostics", {}))
        trap_feature_audit = dict(
            dict(payload.get("two_stage_trade_diagnostics", {})).get(
                "trap_invalidation_feature_impact_audit",
                payload.get("trap_invalidation_feature_impact_audit", {}),
            )
        )
        collapse_signature = dict(root_cause_audit.get("up_collapse_signature", {}))
        warnings = root_cause_audit.get("warnings") or []
        recommendations = root_cause_audit.get("recommendations") or []
        lines = [
            f"# Feature/Regime Candidate - {payload.get('candidate_id')}",
            "",
            f"- candidate_id: `{payload.get('candidate_id')}`",
            f"- config_id: `{payload.get('config_id')}`",
            f"- status: `{payload.get('status')}`",
            f"- candidate_status: `{payload.get('candidate_status')}`",
            f"- raw_candidate_status: `{payload.get('raw_candidate_status')}`",
            f"- quality_status: `{payload.get('quality_status')}`",
            f"- score: `{payload.get('score')}`",
            f"- regime_specific_training_applied: `{payload.get('regime_specific_training_applied')}`",
            f"- failed_gates: `{payload.get('failed_gates')}`",
            f"- probability_diagnostics_missing_reason: `{payload.get('probability_diagnostics_missing_reason')}`",
            f"- real_feature_diagnostics_missing_reason: `{payload.get('real_feature_diagnostics_missing_reason')}`",
            f"- collapse_diagnostics_v2_missing_reason: `{payload.get('collapse_diagnostics_v2_missing_reason')}`",
            f"- walk_forward_profit_diagnostics_missing_reason: `{payload.get('walk_forward_profit_diagnostics_missing_reason')}`",
            f"- profit_aware_diagnostics_missing_reason: `{payload.get('profit_aware_diagnostics_missing_reason')}`",
            f"- profit_exit_root_cause_audit_missing_reason: `{payload.get('profit_exit_root_cause_audit_missing_reason')}`",
            f"- selected_opportunity_threshold: `{payload.get('selected_opportunity_threshold')}`",
            f"- opportunity_probability_threshold: `{payload.get('opportunity_probability_threshold')}`",
            f"- setup_quality_min_threshold: `{payload.get('setup_quality_min_threshold')}`",
            f"- setup_quality_decision_mask_enabled: `{payload.get('setup_quality_decision_mask_enabled')}`",
            f"- setup_quality_decision_mask_min_threshold: `{payload.get('setup_quality_decision_mask_min_threshold')}`",
            f"- setup_quality_filter_passed: `{payload.get('setup_quality_filter_passed')}`",
            f"- predicted_to_actual_trade_rate_ratio: `{payload.get('predicted_to_actual_trade_rate_ratio')}`",
            f"- predicted_trade_rate: `{payload.get('predicted_trade_rate')}`",
            f"- raw_predicted_trade_rate: `{payload.get('raw_predicted_trade_rate')}`",
            f"- masked_predicted_trade_rate: `{payload.get('masked_predicted_trade_rate')}`",
            f"- actual_trade_rate: `{payload.get('actual_trade_rate')}`",
            f"- opportunity_precision: `{payload.get('opportunity_precision')}`",
            f"- opportunity_recall: `{payload.get('opportunity_recall')}`",
            f"- opportunity_f1: `{payload.get('opportunity_f1')}`",
            f"- raw_opportunity_precision: `{payload.get('raw_opportunity_precision')}`",
            f"- raw_opportunity_recall: `{payload.get('raw_opportunity_recall')}`",
            f"- raw_opportunity_f1: `{payload.get('raw_opportunity_f1')}`",
            f"- opportunity_false_positive_rate: `{payload.get('opportunity_false_positive_rate')}`",
            f"- setup_quality_decision_mask_summary: `{payload.get('setup_quality_decision_mask_summary')}`",
            f"- entry_path_quality_filter_enabled: `{payload.get('entry_path_quality_filter_enabled')}`",
            f"- entry_path_quality_min_threshold: `{payload.get('entry_path_quality_min_threshold')}`",
            f"- stop_pressure_max_risk_score: `{payload.get('stop_pressure_max_risk_score')}`",
            f"- mae_pressure_max_risk_score: `{payload.get('mae_pressure_max_risk_score')}`",
            f"- entry_path_prediction_filter_summary: `{payload.get('entry_path_prediction_filter_summary')}`",
            f"- stop_pressure_effectiveness_audit: `{payload.get('stop_pressure_effectiveness_audit')}`",
            f"- directional_side_signal_recovery_status: `{payload.get('directional_side_signal_recovery_status')}`",
            f"- directional_side_signal_recovery_verdict: `{payload.get('directional_side_signal_recovery_verdict')}`",
            f"- primary_signal_loss_reason_counts: `{payload.get('primary_signal_loss_reason_counts')}`",
            f"- walk_forward_validation_candidate_board_status: `{payload.get('walk_forward_validation_candidate_board_status', walk_forward_diag.get('walk_forward_validation_candidate_board_status'))}`",
            f"- walk_forward_validation_candidate_board_verdict: `{payload.get('walk_forward_validation_candidate_board_verdict', walk_forward_diag.get('walk_forward_validation_candidate_board_verdict'))}`",
            f"- recommended_validation_repair_profile: `{payload.get('recommended_validation_repair_profile', walk_forward_diag.get('recommended_validation_repair_profile'))}`",
            f"- total_r_below_min_fold_count: `{payload.get('total_r_below_min_fold_count', walk_forward_diag.get('total_r_below_min_fold_count'))}`",
            f"- total_r_repair_candidate_fold_count: `{payload.get('total_r_repair_candidate_fold_count', walk_forward_diag.get('total_r_repair_candidate_fold_count'))}`",
            f"- median_best_total_r_deficit: `{payload.get('median_best_total_r_deficit', walk_forward_diag.get('median_best_total_r_deficit'))}`",
            f"- max_best_total_r_deficit: `{payload.get('max_best_total_r_deficit', walk_forward_diag.get('max_best_total_r_deficit'))}`",
            f"- research_only_total_r_repair_enabled: `{payload.get('research_only_total_r_repair_enabled')}`",
            f"- validation_total_r_repair_profile: `{payload.get('validation_total_r_repair_profile')}`",
            f"- two_stage_trade_diagnostics: `{payload.get('two_stage_trade_diagnostics')}`",
            f"- trap_invalidation_feature_impact_status: `{trap_feature_audit.get('feature_impact_status')}`",
            f"- trap_invalidation_recommendation: `{trap_feature_audit.get('recommendation')}`",
            f"- trap_invalidation_top_features: `{trap_feature_audit.get('top_separating_features')}`",
            "",
            "## Safety",
            "",
            f"- approved_for_live_trading: `{payload.get('approved_for_live_trading')}`",
            f"- approved_for_auto_activation: `{payload.get('approved_for_auto_activation')}`",
            f"- orders_enabled: `{payload.get('orders_enabled')}`",
            f"- traders_core_connected: `{payload.get('traders_core_connected')}`",
            "",
            "## Prediction root-cause audit",
            "",
            f"- warnings: `{warnings}`",
            f"- actual_down_predicted_up_ratio: `{collapse_signature.get('actual_down_predicted_up_ratio')}`",
            f"- actual_flat_predicted_up_ratio: `{collapse_signature.get('actual_flat_predicted_up_ratio')}`",
            f"- predicted_up_actual_down_or_flat_share: `{collapse_signature.get('predicted_up_actual_down_or_flat_share')}`",
            f"- recommendation: `{recommendations[0] if recommendations else None}`",
            "",
            "## Book-driven forensic audit",
            "",
            f"- final_diagnosis: `{forensic_audit.get('final_diagnosis')}`",
            f"- next_action_recommendation: `{forensic_audit.get('next_action_recommendation')}`",
            "",
            "## Label mode audits",
            "",
            f"- label_mode_recommendation: `{dict(payload.get('label_mode_comparison_audit', {})).get('label_mode_recommendation')}`",
            f"- dominant_flat_subtype: `{dict(payload.get('flat_subtype_audit', {})).get('dominant_flat_subtype')}`",
            f"- recommended_label_mode_by_setup_type: `{dict(payload.get('setup_aware_label_diagnostics', {})).get('recommended_label_mode_by_setup_type')}`",
            "",
            "## Schwager Decision Board",
            "",
            f"- final_research_decision: `{robustness_board.get('final_research_decision')}`",
            f"- primary_failure: `{robustness_board.get('primary_failure')}`",
            f"- secondary_failures: `{robustness_board.get('secondary_failures')}`",
            f"- what_not_to_do_next: `{robustness_board.get('what_not_to_do_next')}`",
            f"- what_to_do_next: `{robustness_board.get('what_to_do_next')}`",
            "",
            "## Class-Margin Objective Decision",
            "",
            f"- class_margin_objective_allowed: `{class_margin_decision.get('class_margin_objective_allowed')}`",
            f"- reason: `{class_margin_decision.get('reason')}`",
            f"- missing_diagnostics: `{class_margin_decision.get('missing_diagnostics')}`",
            "",
        ]
        return "\n".join(lines)
