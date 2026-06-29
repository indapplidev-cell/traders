from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class LabelGridExperimentReporter:
    """Serialize and export label-grid experiment results."""

    SUMMARY_PAYLOAD_MODE = "compact_capped_ml38_10_28_label_grid"
    SUMMARY_CANDIDATE_RESULT_LIMIT = 64
    SUMMARY_CANDIDATE_RANKING_LIMIT = 128
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
        if value is None:
            return {}
        return {
            name: getattr(value, name)
            for name in dir(value)
            if not name.startswith("_")
            and not callable(getattr(value, name, None))
        }

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
    def _compact_preview_dict(cls, value: Any) -> dict[str, Any]:
        preview = cls._compact_preview_value(value)
        return preview if isinstance(preview, dict) else {}

    def _compact_candidate_result(self, candidate: object) -> dict[str, Any]:
        row = self._object_to_dict_shallow(candidate)
        walk_forward_diag = self._as_dict(row.get("walk_forward_profit_diagnostics"))
        profit_aware_diag = self._as_dict(row.get("profit_aware_diagnostics"))
        return {
            "config_id": row.get("config_id"),
            "status": row.get("status"),
            "quality_status": row.get("quality_status"),
            "candidate_status": row.get("candidate_status"),
            "raw_candidate_status": row.get("raw_candidate_status"),
            "model_version": row.get("model_version"),
            "training_run_id": row.get("training_run_id"),
            "dataset_rows": row.get("dataset_rows"),
            "train_rows": row.get("train_rows"),
            "val_rows": row.get("val_rows"),
            "test_rows": row.get("test_rows"),
            "model_accuracy": row.get("model_accuracy"),
            "baseline_accuracy": row.get("baseline_accuracy"),
            "accuracy_edge": row.get("accuracy_edge"),
            "collapse_detected": row.get("collapse_detected"),
            "collapse_type": row.get("collapse_type"),
            "feature_version_used": row.get("feature_version_used"),
            "gap_severity": row.get("gap_severity"),
            "gap_count": row.get("gap_count"),
            "gap_severity_for_training": row.get("gap_severity_for_training"),
            "effective_gap_count_for_training": row.get("effective_gap_count_for_training"),
            "gap_training_safe": row.get("gap_training_safe"),
            "profit_total_r": row.get("profit_total_r"),
            "profit_factor": row.get("profit_factor"),
            "walk_forward_fold_count": row.get("walk_forward_fold_count"),
            "walk_forward_global_total_r": row.get("walk_forward_global_total_r"),
            "walk_forward_profit_factor": row.get("walk_forward_profit_factor"),
            "gate_policy_allowed_count": row.get("gate_policy_allowed_count"),
            "gate_policy_blocked_count": row.get("gate_policy_blocked_count"),
            "failed_gates": self._as_list(row.get("failed_gates")),
            "passed_gates": self._as_list(row.get("passed_gates")),
            "warnings": self._as_list(row.get("warnings")),
            "recommendations": self._as_list(row.get("recommendations")),
            "directional_side_filter_profile": row.get("directional_side_filter_profile"),
            "allowed_signal_directions": self._as_list(row.get("allowed_signal_directions")),
            "research_only_total_r_repair_enabled": row.get("research_only_total_r_repair_enabled"),
            "validation_total_r_repair_profile": row.get("validation_total_r_repair_profile"),
            "research_only_acceptance_block_reason": row.get(
                "research_only_acceptance_block_reason"
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
            "fold_repair_feature_filter_rules": self._compact_preview_dict(
                row.get("fold_repair_feature_filter_rules")
            ),
            "fold_repair_probe_diagnostics": self._compact_preview_dict(
                row.get("fold_repair_probe_diagnostics")
            ),
            "fold_feature_regime_filter_summary": self._compact_preview_dict(
                row.get("fold_feature_regime_filter_summary")
                or profit_aware_diag.get("fold_feature_regime_filter_summary")
            ),
            "opportunity_probability_threshold": row.get("opportunity_probability_threshold"),
            "setup_quality_min_threshold": row.get("setup_quality_min_threshold"),
            "setup_quality_decision_mask_enabled": row.get(
                "setup_quality_decision_mask_enabled"
            ),
            "setup_quality_decision_mask_min_threshold": row.get(
                "setup_quality_decision_mask_min_threshold"
            ),
            "selected_opportunity_threshold": row.get("selected_opportunity_threshold"),
            "entry_path_quality_filter_enabled": row.get(
                "entry_path_quality_filter_enabled"
            ),
            "entry_path_quality_min_threshold": row.get("entry_path_quality_min_threshold"),
            "stop_pressure_max_risk_score": row.get("stop_pressure_max_risk_score"),
            "mae_pressure_max_risk_score": row.get("mae_pressure_max_risk_score"),
            "walk_forward_validation_candidate_board_status": row.get(
                "walk_forward_validation_candidate_board_status",
                walk_forward_diag.get("walk_forward_validation_candidate_board_status"),
            ),
            "walk_forward_validation_candidate_board_verdict": row.get(
                "walk_forward_validation_candidate_board_verdict",
                walk_forward_diag.get("walk_forward_validation_candidate_board_verdict"),
            ),
            "label_config": self._compact_preview_dict(row.get("label_config")),
            "probability_diagnostics": self._compact_preview_dict(
                row.get("probability_diagnostics")
            ),
            "collapse_diagnostics_v2": self._compact_preview_dict(
                row.get("collapse_diagnostics_v2")
            ),
            "walk_forward_profit_diagnostics": self._compact_preview_dict(
                row.get("walk_forward_profit_diagnostics")
            ),
            "profit_aware_diagnostics": self._compact_preview_dict(
                row.get("profit_aware_diagnostics")
            ),
            "prediction_root_cause_audit": self._compact_preview_dict(
                row.get("prediction_root_cause_audit")
            ),
            "book_driven_forensic_audit": self._compact_preview_dict(
                row.get("book_driven_forensic_audit")
            ),
            "decision_policy_grid_diagnostics": self._compact_preview_dict(
                row.get("decision_policy_grid_diagnostics")
            ),
            "directional_side_filter_summary": self._compact_preview_dict(
                row.get("directional_side_filter_summary")
            ),
            "entry_path_prediction_filter_summary": self._compact_preview_dict(
                row.get("entry_path_prediction_filter_summary")
            ),
            "stop_pressure_effectiveness_audit": self._compact_preview_dict(
                row.get("stop_pressure_effectiveness_audit")
            ),
            "setup_quality_decision_mask_summary": self._compact_preview_dict(
                row.get("setup_quality_decision_mask_summary")
            ),
            "two_stage_trade_diagnostics": self._compact_preview_dict(
                row.get("two_stage_trade_diagnostics")
            ),
        }

    def result_to_dict(self, result: object) -> dict[str, Any]:
        if isinstance(result, dict):
            return dict(result)
        to_dict = getattr(result, "to_dict", None)
        if callable(to_dict):
            return dict(to_dict())
        raise TypeError("result must be a dict or provide to_dict()")

    def result_to_json(
        self,
        result: object,
        *,
        indent: int | None = 2,
    ) -> str:
        return json.dumps(
            self.result_to_dict(result),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def compact_summary_to_dict(self, result: object) -> dict[str, Any]:
        candidate_results_source = self._as_list(
            self._result_value(result, "candidate_results", [])
        )
        ranking_source = self._as_list(self._result_value(result, "candidate_ranking", []))
        return {
            "status": self._result_value(result, "status"),
            "experiment_status": self._result_value(result, "experiment_status"),
            "experiment_id": self._result_value(result, "experiment_id"),
            "symbol": self._result_value(result, "symbol"),
            "interval": self._result_value(result, "interval"),
            "start_date": self._result_value(result, "start_date"),
            "end_date": self._result_value(result, "end_date"),
            "dry_run": self._result_value(result, "dry_run"),
            "sample_mode": self._result_value(result, "sample_mode"),
            "config_count": self._result_value(result, "config_count"),
            "completed_candidate_count": self._result_value(
                result,
                "completed_candidate_count",
            ),
            "evaluated_candidate_count": self._result_value(
                result,
                "evaluated_candidate_count",
            ),
            "failed_candidate_count": self._result_value(result, "failed_candidate_count"),
            "accepted_candidate_count": self._result_value(
                result,
                "accepted_candidate_count",
            ),
            "rejected_candidate_count": self._result_value(
                result,
                "rejected_candidate_count",
            ),
            "best_candidate_config_id": self._result_value(result, "best_candidate_config_id"),
            "best_candidate_status": self._result_value(result, "best_candidate_status"),
            "best_candidate_score": self._result_value(result, "best_candidate_score"),
            "feature_version_used": self._result_value(result, "feature_version_used"),
            "output_dir": self._result_value(result, "output_dir"),
            "log_path": self._result_value(result, "log_path"),
            "events_path": self._result_value(result, "events_path"),
            "summary_json_path": self._result_value(result, "summary_json_path"),
            "summary_markdown_path": self._result_value(result, "summary_markdown_path"),
            "candidate_results_dir": self._result_value(result, "candidate_results_dir"),
            "failed_gates_summary": self._compact_preview_dict(
                self._result_value(result, "failed_gates_summary", {})
            ),
            "collapse_summary": self._compact_preview_dict(
                self._result_value(result, "collapse_summary", {})
            ),
            "profit_summary": self._compact_preview_dict(
                self._result_value(result, "profit_summary", {})
            ),
            "walk_forward_summary": self._compact_preview_dict(
                self._result_value(result, "walk_forward_summary", {})
            ),
            "gap_quality_summary": self._compact_preview_dict(
                self._result_value(result, "gap_quality_summary", {})
            ),
            "recommendations": self._as_list(self._result_value(result, "recommendations", [])),
            "summary_payload_mode": self.SUMMARY_PAYLOAD_MODE,
            "summary_payload_compacted": True,
            "candidate_results_total_count": len(candidate_results_source),
            "candidate_results_included_count": min(
                len(candidate_results_source),
                self.SUMMARY_CANDIDATE_RESULT_LIMIT,
            ),
            "candidate_results_truncated": len(candidate_results_source)
            > self.SUMMARY_CANDIDATE_RESULT_LIMIT,
            "candidate_results": [
                self._compact_candidate_result(item)
                for item in candidate_results_source[: self.SUMMARY_CANDIDATE_RESULT_LIMIT]
            ],
            "candidate_ranking_total_count": len(ranking_source),
            "candidate_ranking_included_count": min(
                len(ranking_source),
                self.SUMMARY_CANDIDATE_RANKING_LIMIT,
            ),
            "candidate_ranking_truncated": len(ranking_source)
            > self.SUMMARY_CANDIDATE_RANKING_LIMIT,
            "candidate_ranking": [
                self._object_to_dict_shallow(item)
                for item in ranking_source[: self.SUMMARY_CANDIDATE_RANKING_LIMIT]
            ],
            "approved_for_live_trading": self._result_value(
                result,
                "approved_for_live_trading",
                False,
            ),
            "approved_for_auto_activation": self._result_value(
                result,
                "approved_for_auto_activation",
                False,
            ),
            "orders_enabled": self._result_value(result, "orders_enabled", False),
            "traders_core_connected": self._result_value(
                result,
                "traders_core_connected",
                False,
            ),
        }

    def compact_summary_to_json(
        self,
        result: object,
        *,
        indent: int | None = 2,
    ) -> str:
        return json.dumps(
            self.compact_summary_to_dict(result),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def write_json_summary(self, result: object) -> Path:
        payload = self.compact_summary_to_dict(result)
        path = Path(str(payload["summary_json_path"]))
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        if path.stat().st_size > self.SUMMARY_JSON_SOFT_MAX_BYTES:
            with path.open("w", encoding="utf-8", newline="\n") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=None, sort_keys=True)
                handle.write("\n")
        return path

    def write_markdown_summary(self, result: object) -> Path:
        payload = self.result_to_dict(result)
        path = Path(str(payload["summary_markdown_path"]))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._summary_markdown(payload), encoding="utf-8")
        return path

    def write_candidate_json(self, candidate: object, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self._normalize_candidate(candidate), ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return path

    def write_candidate_markdown(
        self,
        candidate: object,
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            self._candidate_markdown(self._normalize_candidate(candidate)),
            encoding="utf-8",
        )
        return path

    @staticmethod
    def _normalize_candidate(candidate: object) -> dict[str, Any]:
        if isinstance(candidate, dict):
            return dict(candidate)
        to_dict = getattr(candidate, "to_dict", None)
        if callable(to_dict):
            return dict(to_dict())
        raise TypeError("candidate must be a dict or provide to_dict()")

    def _summary_markdown(self, payload: dict[str, Any]) -> str:
        ranking = payload.get("candidate_ranking", [])
        lines = [
            f"# Label Grid Experiment Summary - {payload.get('experiment_id')}",
            "",
            "## Run",
            "",
            f"- experiment_id: `{payload.get('experiment_id')}`",
            f"- status: `{payload.get('status')}`",
            f"- experiment_status: `{payload.get('experiment_status')}`",
            f"- symbol: `{payload.get('symbol')}`",
            f"- interval: `{payload.get('interval')}`",
            f"- start_date: `{payload.get('start_date')}`",
            f"- end_date: `{payload.get('end_date')}`",
            f"- configs_tested: `{payload.get('config_count')}`",
            "",
            "## Candidate Ranking",
            "",
            "| Rank | Config | Candidate | Quality | Score | Failed Gates | Research Only | Validation Repair | Recommended Repair |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for item in ranking:
            lines.append(
                "| `{rank}` | `{config_id}` | `{candidate_status}` | `{quality_status}` | `{score}` | `{failed_gates}` | `{research_only}` | `{validation_profile}` | `{recommended_profile}` |".format(
                    rank=item.get("rank"),
                    config_id=item.get("config_id"),
                    candidate_status=item.get("candidate_status"),
                    quality_status=item.get("quality_status"),
                    score=item.get("score"),
                    failed_gates=",".join(item.get("failed_gates", [])),
                    research_only=item.get("research_only_total_r_repair_enabled"),
                    validation_profile=item.get("validation_total_r_repair_profile"),
                    recommended_profile=(
                        item.get("recommended_validation_repair_profile")
                        or dict(item.get("walk_forward_profit_diagnostics", {})).get(
                            "recommended_validation_repair_profile"
                        )
                    ),
                )
            )
        if not ranking:
            lines.append("| `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` |")

        best_candidate_config_id = payload.get("best_candidate_config_id")
        accepted_count = int(payload.get("accepted_candidate_count") or 0)
        lines.extend(
            [
                "",
                "## Selection",
                "",
            ]
        )
        if accepted_count > 0 and best_candidate_config_id:
            lines.append(f"- accepted_candidate: `{best_candidate_config_id}`")
        elif best_candidate_config_id:
            lines.append(f"- best_rejected_candidate: `{best_candidate_config_id}`")
        else:
            lines.append("- no_scored_candidates")

        lines.extend(
            [
                f"- accepted_candidate_count: `{payload.get('accepted_candidate_count')}`",
                f"- rejected_candidate_count: `{payload.get('rejected_candidate_count')}`",
                "",
                "## Diagnostics",
                "",
                f"- anti-collapse: `{payload.get('collapse_summary')}`",
                f"- profit-aware: `{payload.get('profit_summary')}`",
                f"- walk-forward: `{payload.get('walk_forward_summary')}`",
                f"- gap quality: `{payload.get('gap_quality_summary')}`",
                f"- failed gates summary: `{payload.get('failed_gates_summary')}`",
                "",
                "## Recommendations",
                "",
            ]
        )
        for item in payload.get("recommendations", []):
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
    def _candidate_markdown(candidate: dict[str, Any]) -> str:
        root_cause_audit = dict(candidate.get("prediction_root_cause_audit", {}))
        forensic_audit = dict(candidate.get("book_driven_forensic_audit", {}))
        robustness_board = dict(candidate.get("schwager_robustness_decision_board", {}))
        class_margin_decision = dict(candidate.get("class_margin_objective_decision", {}))
        collapse_signature = dict(root_cause_audit.get("up_collapse_signature", {}))
        warnings = root_cause_audit.get("warnings") or []
        recommendations = root_cause_audit.get("recommendations") or []
        lines = [
            f"# Candidate Result - {candidate.get('config_id')}",
            "",
            "## Candidate",
            "",
            f"- config_id: `{candidate.get('config_id')}`",
            f"- status: `{candidate.get('status')}`",
            f"- quality_status: `{candidate.get('quality_status')}`",
            f"- candidate_status: `{candidate.get('candidate_status')}`",
            f"- model_version: `{candidate.get('model_version')}`",
            f"- training_run_id: `{candidate.get('training_run_id')}`",
            f"- accuracy_edge: `{candidate.get('accuracy_edge')}`",
            f"- collapse_detected: `{candidate.get('collapse_detected')}`",
            f"- profit_factor: `{candidate.get('profit_factor')}`",
            f"- walk_forward_profit_factor: `{candidate.get('walk_forward_profit_factor')}`",
            f"- failed_gates: `{candidate.get('failed_gates')}`",
            f"- research_only_total_r_repair_enabled: `{candidate.get('research_only_total_r_repair_enabled')}`",
            f"- validation_total_r_repair_profile: `{candidate.get('validation_total_r_repair_profile')}`",
            f"- recommended_validation_repair_profile: `{candidate.get('recommended_validation_repair_profile') or dict(candidate.get('walk_forward_profit_diagnostics', {})).get('recommended_validation_repair_profile')}`",
            f"- opportunity_probability_threshold: `{candidate.get('opportunity_probability_threshold')}`",
            f"- setup_quality_min_threshold: `{candidate.get('setup_quality_min_threshold')}`",
            f"- setup_quality_decision_mask_enabled: `{candidate.get('setup_quality_decision_mask_enabled')}`",
            f"- setup_quality_decision_mask_min_threshold: `{candidate.get('setup_quality_decision_mask_min_threshold')}`",
            f"- predicted_trade_rate: `{candidate.get('predicted_trade_rate')}`",
            f"- raw_predicted_trade_rate: `{candidate.get('raw_predicted_trade_rate')}`",
            f"- masked_predicted_trade_rate: `{candidate.get('masked_predicted_trade_rate')}`",
            f"- opportunity_precision: `{candidate.get('opportunity_precision')}`",
            f"- raw_opportunity_precision: `{candidate.get('raw_opportunity_precision')}`",
            f"- setup_quality_decision_mask_summary: `{candidate.get('setup_quality_decision_mask_summary')}`",
            "",
            "## Safety",
            "",
            f"- approved_for_traders_core_integration: `{candidate.get('approved_for_traders_core_integration')}`",
            f"- approved_for_live_trading: `{candidate.get('approved_for_live_trading')}`",
            f"- approved_for_auto_activation: `{candidate.get('approved_for_auto_activation')}`",
            f"- orders_enabled: `{candidate.get('orders_enabled')}`",
            f"- traders_core_connected: `{candidate.get('traders_core_connected')}`",
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
            "## Schwager Decision Board",
            "",
            f"- final_research_decision: `{robustness_board.get('final_research_decision')}`",
            f"- primary_failure: `{robustness_board.get('primary_failure')}`",
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
