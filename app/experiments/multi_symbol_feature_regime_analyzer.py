from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any, Iterable

from app.diagnostics.decision_policy_grid import apply_selected_decision_policy_metrics
from app.diagnostics.directional_side_ablation_comparator import DirectionalSideAblationComparator
from app.diagnostics.directional_side_walk_forward_stability import (
    DirectionalSideWalkForwardStabilityAnalyzer,
)
from app.diagnostics.fold_time_slice_exit_repair_probe import (
    FoldTimeSliceExitRepairProbe,
)
from app.evaluation.gap_quality_gate_normalizer import normalize_gap_quality_gate


MULTI_SYMBOL_FEATURE_REGIME_ANALYZER_NAME = "multi_symbol_feature_regime_analyzer"
MULTI_SYMBOL_FEATURE_REGIME_ANALYZER_VERSION = "ml35"


class MultiSymbolFeatureRegimeAnalyzer:
    """Aggregate multiple feature/regime experiment summaries into one report."""

    def __init__(
        self,
        directional_side_ablation_comparator: DirectionalSideAblationComparator | None = None,
        directional_side_walk_forward_stability_analyzer: DirectionalSideWalkForwardStabilityAnalyzer | None = None,
        fold_time_slice_exit_repair_probe: FoldTimeSliceExitRepairProbe | None = None,
    ) -> None:
        self._directional_side_ablation_comparator = (
            directional_side_ablation_comparator or DirectionalSideAblationComparator()
        )
        self._directional_side_walk_forward_stability_analyzer = (
            directional_side_walk_forward_stability_analyzer
            or DirectionalSideWalkForwardStabilityAnalyzer()
        )
        self._fold_time_slice_exit_repair_probe = (
            fold_time_slice_exit_repair_probe or FoldTimeSliceExitRepairProbe()
        )

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

    def analyze(
        self,
        summary_sources: Iterable[str | Path],
    ) -> dict[str, Any]:
        summaries = [self.load_summary(source) for source in summary_sources]
        if not summaries:
            raise ValueError("No feature/regime experiment summaries were provided.")

        symbol_results = [self._symbol_result(summary) for summary in summaries]
        gate_failure_counts = self._gate_failure_counts(symbol_results)
        top_failed_gate = self._top_failed_gate(gate_failure_counts)
        best_result = self._best_result(symbol_results)
        symbols_missing_real_diagnostics = [
            item["symbol"] for item in symbol_results if not item["real_feature_diagnostics_used"]
        ]
        symbols_missing_regime_features = [
            item["symbol"] for item in symbol_results if not item["regime_features_attached"]
        ]
        symbols_missing_candle_ta_context = [
            item["symbol"] for item in symbol_results if not item["candle_ta_context_features_attached"]
        ]
        all_feature_version_fv2 = all(item["feature_version_used"] == "fv2" for item in symbol_results)
        all_feature_version_fv3_candle_ta_context = all(
            item["feature_version_used"] == "fv3_candle_ta_context" for item in symbol_results
        )
        all_feature_version_fv4_book_setup_context = all(
            item["feature_version_used"] == "fv4_book_setup_context" for item in symbol_results
        )
        all_gap_training_safe = all(
            item["gap_training_safe"]
            and item["effective_gap_count_for_training"] == 0
            and item["gap_severity_for_training"] in {"OK", "MINOR"}
            for item in symbol_results
        )
        all_real_feature_diagnostics_used = all(
            item["real_feature_diagnostics_used"] for item in symbol_results
        )
        any_accepted_candidate = any(
            item["accepted_candidate_count"] > 0 for item in symbol_results
        )
        positive_edges = [
            item for item in symbol_results if item["baseline_edge"] is not None and item["baseline_edge"] > 0.0
        ]
        regime_training_applied_by_symbol = {
            item["symbol"]: bool(item["regime_specific_training_applied"]) for item in symbol_results
        }
        collapse_failed_count = gate_failure_counts.get("collapse_gate", 0)
        walk_forward_failed_count = gate_failure_counts.get("walk_forward_gate", 0)
        profit_aware_failed_count = gate_failure_counts.get("profit_aware_gate", 0)
        configs_ranked = self._configs_ranked(symbol_results)
        full_candidate_payloads = self._full_candidate_payloads(summaries)
        anti_collapse_summary = self._anti_collapse_summary(symbol_results)
        confidence_profitability_summary = self._confidence_profitability_summary(symbol_results)
        prediction_root_cause_summary = self._prediction_root_cause_summary(configs_ranked)
        book_driven_forensic_summary = self._book_driven_forensic_summary(configs_ranked)
        schwager_robustness_summary = self._schwager_robustness_summary(configs_ranked)
        label_mode_audit_summary = self._label_mode_audit_summary(symbol_results)
        flat_subtype_summary = self._flat_subtype_summary(symbol_results)
        setup_aware_label_summary = self._setup_aware_label_summary(symbol_results)
        decision_policy_summary = {
            "candidates_with_decision_policy": sum(
                int(item.get("decision_policy_selected_policy_id") is not None)
                for item in symbol_results
            ),
            "selected_policy_by_symbol": {
                item["symbol"]: item.get("decision_policy_selected_policy_id")
                for item in symbol_results
                if item.get("decision_policy_selected_policy_id") is not None
            },
            "positive_policy_edge_symbols": [
                item["symbol"]
                for item in symbol_results
                if (
                    self._as_dict(item.get("decision_policy_grid_diagnostics")).get("selected_policy", {}).get(
                        "baseline_edge"
                    )
                    is not None
                    and float(
                        self._as_dict(item.get("decision_policy_grid_diagnostics")).get(
                            "selected_policy",
                            {},
                        ).get("baseline_edge")
                    )
                    > 0.0
                )
            ],
        }
        directional_side_ablation_comparator = self._directional_side_ablation_comparator.compare(
            full_candidate_payloads
        )
        directional_side_walk_forward_stability = (
            self._directional_side_walk_forward_stability_analyzer.analyze(
                full_candidate_payloads
            )
        )
        directional_side_signal_recovery_summary = self._directional_side_signal_recovery_summary(
            full_candidate_payloads
        )
        walk_forward_validation_candidate_board_summary = (
            self._walk_forward_validation_candidate_board_summary(full_candidate_payloads)
        )
        walk_forward_fold_root_cause_board = self._walk_forward_fold_root_cause_board(
            full_candidate_payloads
        )
        fold_1_repair_target_selection = self._fold_repair_target_selection(
            full_candidate_payloads,
            target_fold_index=1,
        )
        fold_time_slice_exit_repair_probe = self._fold_time_slice_exit_repair_probe.analyze(
            full_candidate_payloads
        )

        return {
            "analyzer_name": MULTI_SYMBOL_FEATURE_REGIME_ANALYZER_NAME,
            "analyzer_version": MULTI_SYMBOL_FEATURE_REGIME_ANALYZER_VERSION,
            "symbols": [item["symbol"] for item in symbol_results],
            "interval": self._common_value(summaries, "interval"),
            "start_date": self._common_value(summaries, "start_date"),
            "experiment_count": len(summaries),
            "candidate_count": sum(item["candidate_count"] for item in symbol_results),
            "evaluated_candidate_count": sum(item["evaluated_candidate_count"] for item in symbol_results),
            "failed_candidate_count": sum(item["failed_candidate_count"] for item in symbol_results),
            "accepted_candidate_count": sum(item["accepted_candidate_count"] for item in symbol_results),
            "rejected_candidate_count": sum(item["rejected_candidate_count"] for item in symbol_results),
            "best_symbol": None if best_result is None else best_result["symbol"],
            "best_candidate_config_id": None if best_result is None else best_result["best_candidate_config_id"],
            "best_candidate_score": None if best_result is None else best_result["best_candidate_score"],
            "directional_edge_bias_audit": None if best_result is None else self._as_dict(best_result.get("directional_edge_bias_audit")),
            "directional_side_filter_summary": None if best_result is None else self._as_dict(best_result.get("directional_side_filter_summary")),
            "directional_side_filter_profile": None if best_result is None else best_result.get("directional_side_filter_profile"),
            "allowed_signal_directions": [] if best_result is None else list(best_result.get("allowed_signal_directions") or []),
            "validation_gate_failure_reason_counts": None if best_result is None else self._as_dict(best_result.get("validation_gate_failure_reason_counts")),
            "side_aware_relaxed_fold_count": 0 if best_result is None else int(best_result.get("side_aware_relaxed_fold_count", 0) or 0),
            "side_aware_validation_relaxation_enabled": False if best_result is None else bool(best_result.get("side_aware_validation_relaxation_enabled", False)),
            "side_aware_min_validation_signal_count": None if best_result is None else best_result.get("side_aware_min_validation_signal_count"),
            "side_aware_min_validation_profit_factor": None if best_result is None else self._float_or_none(best_result.get("side_aware_min_validation_profit_factor")),
            "side_aware_min_validation_total_r": None if best_result is None else self._float_or_none(best_result.get("side_aware_min_validation_total_r")),
            "side_aware_min_validation_expectancy_r": None if best_result is None else self._float_or_none(best_result.get("side_aware_min_validation_expectancy_r")),
            "side_aware_allow_single_direction_validation": False if best_result is None else bool(best_result.get("side_aware_allow_single_direction_validation", False)),
            "direction_balance_ratio": None if best_result is None else self._float_or_none(best_result.get("direction_balance_ratio")),
            "directional_profit_skew_r": None if best_result is None else self._float_or_none(best_result.get("directional_profit_skew_r")),
            "directional_profit_skew_ratio": None if best_result is None else self._float_or_none(best_result.get("directional_profit_skew_ratio")),
            "long_total_r": None if best_result is None else self._float_or_none(best_result.get("long_total_r")),
            "short_total_r": None if best_result is None else self._float_or_none(best_result.get("short_total_r")),
            "long_avg_r": None if best_result is None else self._float_or_none(best_result.get("long_avg_r")),
            "short_avg_r": None if best_result is None else self._float_or_none(best_result.get("short_avg_r")),
            "dominant_direction": None if best_result is None else best_result.get("dominant_direction"),
            "best_config_by_symbol": {
                item["symbol"]: item["best_candidate_config_id"] for item in symbol_results
            },
            "best_global_config": None if best_result is None else best_result["best_candidate_config_id"],
            "configs_ranked": configs_ranked,
            "symbol_results": symbol_results,
            "directional_side_ablation_comparator": directional_side_ablation_comparator,
            "directional_side_walk_forward_stability": directional_side_walk_forward_stability,
            "directional_side_signal_recovery_summary": directional_side_signal_recovery_summary,
            "walk_forward_validation_candidate_board_summary": (
                walk_forward_validation_candidate_board_summary
            ),
            "walk_forward_fold_root_cause_board": walk_forward_fold_root_cause_board,
            "fold_1_repair_target_selection": fold_1_repair_target_selection,
            "fold_time_slice_exit_repair_probe": fold_time_slice_exit_repair_probe,
            "anti_collapse_summary": anti_collapse_summary,
            "confidence_profitability_summary": confidence_profitability_summary,
            "prediction_root_cause_summary": prediction_root_cause_summary,
            "book_driven_forensic_summary": book_driven_forensic_summary,
            "schwager_robustness_summary": schwager_robustness_summary,
            "label_mode_audit_summary": label_mode_audit_summary,
            "flat_subtype_summary": flat_subtype_summary,
            "setup_aware_label_summary": setup_aware_label_summary,
            "decision_policy_summary": decision_policy_summary,
            "gate_failure_counts": gate_failure_counts,
            "feature_version_summary": {
                "all_feature_version_fv2": all_feature_version_fv2,
                "feature_versions_by_symbol": {
                    item["symbol"]: item["feature_version_used"] for item in symbol_results
                },
                "all_feature_version_fv3_candle_ta_context": all_feature_version_fv3_candle_ta_context,
                "all_feature_version_fv4_book_setup_context": all_feature_version_fv4_book_setup_context,
            },
            "gap_training_safety_summary": {
                "all_gap_training_safe": all_gap_training_safe,
                "gap_severity_by_symbol": {
                    item["symbol"]: item["gap_severity_for_training"] for item in symbol_results
                },
                "effective_gap_count_by_symbol": {
                    item["symbol"]: item["effective_gap_count_for_training"] for item in symbol_results
                },
            },
            "real_feature_diagnostics_summary": {
                "all_real_feature_diagnostics_used": all_real_feature_diagnostics_used,
                "row_count_by_symbol": {
                    item["symbol"]: item["real_feature_diagnostics_row_count"] for item in symbol_results
                },
                "missing_reason_by_symbol": {
                    item["symbol"]: item["real_feature_diagnostics_missing_reason"] for item in symbol_results
                },
                "symbols_missing_real_diagnostics": symbols_missing_real_diagnostics,
            },
            "regime_integration_summary": {
                "regime_training_applied_by_symbol": regime_training_applied_by_symbol,
                "regime_specific_training_applied_any": any(regime_training_applied_by_symbol.values()),
                "regime_features_attached_by_symbol": {
                    item["symbol"]: item["regime_features_attached"] for item in symbol_results
                },
                "regime_feature_count_by_symbol": {
                    item["symbol"]: item["regime_feature_count"] for item in symbol_results
                },
                "regime_features_missing_reason_by_symbol": {
                    item["symbol"]: item["regime_features_missing_reason"] for item in symbol_results
                },
                "symbols_missing_regime_features": symbols_missing_regime_features,
                "candle_ta_context_features_attached_by_symbol": {
                    item["symbol"]: item["candle_ta_context_features_attached"] for item in symbol_results
                },
                "candle_ta_context_feature_count_by_symbol": {
                    item["symbol"]: item["candle_ta_context_feature_count"] for item in symbol_results
                },
                "candle_ta_context_missing_reason_by_symbol": {
                    item["symbol"]: item["candle_ta_context_missing_reason"] for item in symbol_results
                },
                "book_setup_context_features_attached_by_symbol": {
                    item["symbol"]: item.get("book_setup_context_features_attached", False)
                    for item in symbol_results
                },
                "book_setup_context_feature_count_by_symbol": {
                    item["symbol"]: item.get("book_setup_context_feature_count", 0)
                    for item in symbol_results
                },
                "nison_feature_count_by_symbol": {
                    item["symbol"]: item.get("nison_feature_count", 0)
                    for item in symbol_results
                },
                "altunina_feature_count_by_symbol": {
                    item["symbol"]: item.get("altunina_feature_count", 0)
                    for item in symbol_results
                },
                "path_context_feature_count_by_symbol": {
                    item["symbol"]: item.get("path_context_feature_count", 0)
                    for item in symbol_results
                },
                "htf_context_feature_count_by_symbol": {
                    item["symbol"]: item.get("htf_context_feature_count", 0)
                    for item in symbol_results
                },
                "missing_context_feature_count_by_symbol": {
                    item["symbol"]: item.get("missing_context_feature_count", 0)
                    for item in symbol_results
                },
                "symbols_missing_candle_ta_context_features": symbols_missing_candle_ta_context,
            },
            "walk_forward_summary": {
                "walk_forward_failed_count": walk_forward_failed_count,
                "all_failed": walk_forward_failed_count == len(symbol_results),
                "profit_factor_by_symbol": {
                    item["symbol"]: item["walk_forward_profit_factor"] for item in symbol_results
                },
                "total_r_by_symbol": {
                    item["symbol"]: item["walk_forward_total_r"] for item in symbol_results
                },
            },
            "profit_aware_summary": {
                "profit_aware_failed_count": profit_aware_failed_count,
                "profit_factor_by_symbol": {
                    item["symbol"]: item["profit_factor"] for item in symbol_results
                },
                "total_r_by_symbol": {
                    item["symbol"]: item["profit_total_r"] for item in symbol_results
                },
            },
            "collapse_summary": {
                "collapse_failed_count": collapse_failed_count,
                "all_failed": collapse_failed_count == len(symbol_results),
                "collapse_detected_by_symbol": {
                    item["symbol"]: item["collapse_detected"] for item in symbol_results
                },
                "collapse_type_by_symbol": {
                    item["symbol"]: (
                        item["collapse_tuning_summary"].get("collapse_type") or item["collapse_type"]
                    )
                    for item in symbol_results
                },
            },
            "flat_bias_summary": {
                "flat_bias_detected_by_symbol": {
                    item["symbol"]: item["flat_bias_detected"] for item in symbol_results
                },
                "symbol_bias_severity_by_symbol": {
                    item["symbol"]: item["symbol_bias_severity"] for item in symbol_results
                },
            },
            "down_blindness_summary": {
                "down_blindness_detected_by_symbol": {
                    item["symbol"]: item["down_blindness_detected"] for item in symbol_results
                },
            },
            "baseline_edge_summary": {
                "baseline_edge_by_symbol": {
                    item["symbol"]: item["baseline_edge"] for item in symbol_results
                },
                "positive_baseline_edge_symbols": [
                    item["symbol"] for item in symbol_results if (item["baseline_edge"] or 0.0) > 0.0
                ],
            },
            "all_feature_version_fv2": all_feature_version_fv2,
            "all_gap_training_safe": all_gap_training_safe,
            "all_real_feature_diagnostics_used": all_real_feature_diagnostics_used,
            "any_accepted_candidate": any_accepted_candidate,
            "any_positive_baseline_edge": bool(positive_edges),
            "all_positive_baseline_edge": len(positive_edges) == len(symbol_results),
            "best_score": None if best_result is None else best_result["best_candidate_score"],
            "top_failed_gate": top_failed_gate,
            "collapse_failed_count": collapse_failed_count,
            "walk_forward_failed_count": walk_forward_failed_count,
            "profit_aware_failed_count": profit_aware_failed_count,
            "symbols_missing_real_diagnostics": symbols_missing_real_diagnostics,
            "symbols_missing_regime_features": symbols_missing_regime_features,
            "symbols_missing_candle_ta_context_features": symbols_missing_candle_ta_context,
            "recommendations": self._recommendations(
                any_accepted_candidate=any_accepted_candidate,
                collapse_failed_count=collapse_failed_count,
                walk_forward_failed_count=walk_forward_failed_count,
                profit_aware_failed_count=profit_aware_failed_count,
                symbol_count=len(symbol_results),
                symbols_missing_real_diagnostics=symbols_missing_real_diagnostics,
                symbols_missing_candle_ta_context=symbols_missing_candle_ta_context,
                regime_specific_training_applied_any=any(regime_training_applied_by_symbol.values()),
            ),
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "orders_enabled": False,
            "traders_core_connected": False,
        }

    @staticmethod
    def load_summary(summary_source: str | Path) -> dict[str, Any]:
        path = Path(summary_source)
        if path.is_dir():
            path = path / "feature_regime_experiment_summary.json"
        if not path.exists():
            raise ValueError(f"feature/regime experiment summary not found: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    @classmethod
    def latest_summary_paths_by_symbol(
        cls,
        *,
        root_dir: str | Path = Path("reports/feature_regime_experiments"),
        symbols: Iterable[str],
    ) -> list[Path]:
        root = Path(root_dir)
        if not root.exists():
            raise ValueError("reports/feature_regime_experiments is missing; run feature-regime-experiment-run first.")
        resolved_paths: list[Path] = []
        for symbol in symbols:
            candidates: list[Path] = []
            for directory in root.iterdir():
                if not directory.is_dir():
                    continue
                summary_path = directory / "feature_regime_experiment_summary.json"
                if not summary_path.exists():
                    continue
                payload = cls.load_summary(summary_path)
                if str(payload.get("symbol")) == symbol:
                    candidates.append(summary_path)
            if not candidates:
                existing_summaries = sorted(root.rglob("feature_regime_experiment_summary.json"))
                sample = [str(item) for item in existing_summaries[:10]]
                raise ValueError(
                    f"No feature/regime experiment summaries found for symbol: {symbol}. "
                    f"root_dir={root}; summary_file_count={len(existing_summaries)}; sample={sample}"
                )
            resolved_paths.append(max(candidates, key=lambda item: item.stat().st_mtime))
        return resolved_paths

    @classmethod
    def summary_paths_from_root(
        cls,
        *,
        root_dir: str | Path = Path("reports/feature_regime_experiments"),
        symbols: Iterable[str] | None = None,
    ) -> list[Path]:
        root = Path(root_dir)
        if not root.exists():
            raise ValueError("reports/feature_regime_experiments is missing; run feature-regime-experiment-run first.")

        symbol_filter = None if symbols is None else {item for item in symbols}
        resolved_paths: list[Path] = []
        for directory in root.iterdir():
            if not directory.is_dir():
                continue
            summary_path = directory / "feature_regime_experiment_summary.json"
            if not summary_path.exists():
                continue
            payload = cls.load_summary(summary_path)
            if symbol_filter is not None and str(payload.get("symbol")) not in symbol_filter:
                continue
            resolved_paths.append(summary_path)
        if not resolved_paths:
            raise ValueError("No feature/regime experiment summaries matched the requested symbols.")
        return sorted(resolved_paths, key=lambda item: item.stat().st_mtime)

    @staticmethod
    def _common_value(summaries: list[dict[str, Any]], key: str) -> Any:
        values = {summary.get(key) for summary in summaries}
        if len(values) == 1:
            return next(iter(values))
        return "MULTIPLE"

    @classmethod
    def _entry_path_audit_payload(cls, candidate: dict[str, Any]) -> dict[str, Any]:
        profit_aware = cls._as_dict(candidate.get("profit_aware_diagnostics"))
        best_gate = cls._as_dict(profit_aware.get("best_gate"))

        entry_summary = cls._as_dict(
            candidate.get("entry_path_prediction_filter_summary")
            or profit_aware.get("entry_path_prediction_filter_summary")
            or best_gate.get("entry_path_prediction_filter_summary")
        )
        stop_audit = cls._as_dict(
            candidate.get("stop_pressure_effectiveness_audit")
            or profit_aware.get("stop_pressure_effectiveness_audit")
            or best_gate.get("stop_pressure_effectiveness_audit")
            or entry_summary.get("stop_pressure_effectiveness_audit")
        )

        return {
            "entry_path_quality_filter_enabled": bool(
                candidate.get("entry_path_quality_filter_enabled")
                or entry_summary.get("entry_path_filter_enabled")
                or stop_audit.get("entry_path_filter_enabled")
            ),
            "entry_path_quality_min_threshold": cls._float_or_none(
                candidate.get("entry_path_quality_min_threshold")
                or entry_summary.get("entry_path_quality_threshold")
                or stop_audit.get("entry_path_quality_threshold")
            ),
            "stop_pressure_max_risk_score": cls._float_or_none(
                candidate.get("stop_pressure_max_risk_score")
                or entry_summary.get("stop_pressure_threshold")
                or stop_audit.get("stop_pressure_threshold")
            ),
            "mae_pressure_max_risk_score": cls._float_or_none(
                candidate.get("mae_pressure_max_risk_score")
                or entry_summary.get("mae_pressure_threshold")
                or stop_audit.get("mae_pressure_threshold")
            ),
            "entry_path_prediction_filter_summary": entry_summary,
            "stop_pressure_effectiveness_audit": stop_audit,
            "entry_path_final_signal_original_count": int(
                entry_summary.get("original_final_signal_count", 0) or 0
            ),
            "entry_path_final_signal_filtered_count": int(
                entry_summary.get("filtered_final_signal_count", 0) or 0
            ),
            "entry_path_final_signal_blocked_count": int(
                entry_summary.get("blocked_final_signal_count", 0) or 0
            ),
            "entry_path_stream_consistency_ok": bool(
                entry_summary.get("stream_consistency_ok", True)
            ),
        }

    @classmethod
    def _directional_side_audit_payload(cls, candidate: dict[str, Any]) -> dict[str, Any]:
        directional_audit = cls._as_dict(candidate.get("directional_edge_bias_audit"))
        side_filter_summary = cls._as_dict(candidate.get("directional_side_filter_summary"))
        return {
            "directional_edge_bias_audit": directional_audit,
            "directional_side_filter_summary": side_filter_summary,
            "directional_side_filter_profile": candidate.get("directional_side_filter_profile"),
            "allowed_signal_directions": list(candidate.get("allowed_signal_directions") or []),
            "direction_balance_ratio": cls._float_or_none(directional_audit.get("direction_balance_ratio")),
            "directional_profit_skew_r": cls._float_or_none(directional_audit.get("directional_profit_skew_r")),
            "directional_profit_skew_ratio": cls._float_or_none(directional_audit.get("directional_profit_skew_ratio")),
            "long_total_r": cls._float_or_none(directional_audit.get("long_total_r")),
            "short_total_r": cls._float_or_none(directional_audit.get("short_total_r")),
            "long_avg_r": cls._float_or_none(directional_audit.get("long_avg_r")),
            "short_avg_r": cls._float_or_none(directional_audit.get("short_avg_r")),
            "dominant_direction": directional_audit.get("dominant_direction"),
        }

    @classmethod
    def _walk_forward_stability_payload(cls, candidate: dict[str, Any]) -> dict[str, Any]:
        walk_diag = cls._as_dict(candidate.get("walk_forward_profit_diagnostics"))
        fold_signal_summary = cls._as_dict(walk_diag.get("fold_signal_summary"))
        return {
            "walk_forward_stability_status": walk_diag.get("walk_forward_stability_status"),
            "walk_forward_stability_verdict": walk_diag.get("walk_forward_stability_verdict"),
            "walk_forward_stability_warnings": list(
                cls._as_list(walk_diag.get("walk_forward_stability_warnings"))
            ),
            "walk_forward_low_signal_fold_count": int(
                walk_diag.get("low_signal_fold_count", 0) or 0
            ),
            "walk_forward_zero_signal_fold_count": int(
                walk_diag.get("zero_signal_fold_count", 0) or 0
            ),
            "walk_forward_total_resolved_signal_count": int(
                walk_diag.get(
                    "total_resolved_signal_count",
                    fold_signal_summary.get("total_resolved_signal_count", 0),
                )
                or 0
            ),
            "walk_forward_min_resolved_signal_count": cls._float_or_none(
                walk_diag.get("min_resolved_signal_count")
            ),
            "walk_forward_median_resolved_signal_count": cls._float_or_none(
                walk_diag.get("median_resolved_signal_count")
            ),
            "walk_forward_max_resolved_signal_count": cls._float_or_none(
                walk_diag.get("max_resolved_signal_count")
            ),
        }

    @classmethod
    def _directional_side_signal_recovery_payload(cls, candidate: dict[str, Any]) -> dict[str, Any]:
        walk_diag = cls._as_dict(candidate.get("walk_forward_profit_diagnostics"))
        recovery = cls._as_dict(walk_diag.get("directional_side_signal_recovery_diagnostics"))
        return {
            "directional_side_signal_recovery_diagnostics": recovery,
            "directional_side_signal_recovery_status": recovery.get("diagnostic_status"),
            "directional_side_signal_recovery_verdict": recovery.get("verdict"),
            "primary_signal_loss_reason_counts": cls._as_dict(
                recovery.get("primary_signal_loss_reason_counts")
            ),
            "side_filter_removed_all_fold_count": int(
                recovery.get("side_filter_removed_all_fold_count", 0) or 0
            ),
            "raw_signal_available_but_filtered_out_count": int(
                recovery.get("raw_signal_available_but_filtered_out_count", 0) or 0
            ),
            "threshold_too_strict_fold_count": int(
                recovery.get("threshold_too_strict_fold_count", 0) or 0
            ),
            "signal_recovery_total_original_signal_count": int(
                recovery.get("total_original_signal_count", 0) or 0
            ),
            "signal_recovery_total_filtered_signal_count": int(
                recovery.get("total_filtered_signal_count", 0) or 0
            ),
            "signal_recovery_total_removed_signal_count": int(
                recovery.get("total_removed_signal_count", 0) or 0
            ),
        }

    @classmethod
    def _directional_side_validation_gate_payload(
        cls,
        candidate: dict[str, Any],
    ) -> dict[str, Any]:
        walk_diag = cls._as_dict(candidate.get("walk_forward_profit_diagnostics"))
        recovery = cls._as_dict(walk_diag.get("directional_side_signal_recovery_diagnostics"))
        label_config = cls._as_dict(candidate.get("label_config"))

        def first_present(*values: Any) -> Any:
            for value in values:
                if value is not None:
                    return value
            return None

        return {
            "validation_gate_failure_reason_counts": cls._as_dict(
                first_present(
                    candidate.get("validation_gate_failure_reason_counts"),
                    walk_diag.get("validation_gate_failure_reason_counts"),
                    recovery.get("validation_gate_failure_reason_counts"),
                )
            ),
            "side_aware_relaxed_fold_count": int(
                first_present(
                    candidate.get("side_aware_relaxed_fold_count"),
                    walk_diag.get("side_aware_relaxed_fold_count"),
                    recovery.get("side_aware_relaxed_fold_count"),
                    0,
                )
                or 0
            ),
            "side_aware_validation_relaxation_enabled": bool(
                first_present(
                    candidate.get("side_aware_validation_relaxation_enabled"),
                    walk_diag.get("side_aware_validation_relaxation_enabled"),
                    recovery.get("side_aware_validation_relaxation_enabled"),
                    label_config.get("side_aware_validation_relaxation_enabled"),
                    False,
                )
            ),
            "side_aware_min_validation_signal_count": first_present(
                candidate.get("side_aware_min_validation_signal_count"),
                walk_diag.get("side_aware_min_validation_signal_count"),
                recovery.get("side_aware_min_validation_signal_count"),
                label_config.get("side_aware_min_validation_signal_count"),
            ),
            "side_aware_min_validation_profit_factor": cls._float_or_none(
                first_present(
                    candidate.get("side_aware_min_validation_profit_factor"),
                    walk_diag.get("side_aware_min_validation_profit_factor"),
                    recovery.get("side_aware_min_validation_profit_factor"),
                    label_config.get("side_aware_min_validation_profit_factor"),
                )
            ),
            "side_aware_min_validation_total_r": cls._float_or_none(
                first_present(
                    candidate.get("side_aware_min_validation_total_r"),
                    walk_diag.get("side_aware_min_validation_total_r"),
                    recovery.get("side_aware_min_validation_total_r"),
                    label_config.get("side_aware_min_validation_total_r"),
                )
            ),
            "side_aware_min_validation_expectancy_r": cls._float_or_none(
                first_present(
                    candidate.get("side_aware_min_validation_expectancy_r"),
                    walk_diag.get("side_aware_min_validation_expectancy_r"),
                    recovery.get("side_aware_min_validation_expectancy_r"),
                    label_config.get("side_aware_min_validation_expectancy_r"),
                )
            ),
            "side_aware_allow_single_direction_validation": bool(
                first_present(
                    candidate.get("side_aware_allow_single_direction_validation"),
                    walk_diag.get("side_aware_allow_single_direction_validation"),
                    recovery.get("side_aware_allow_single_direction_validation"),
                    label_config.get("side_aware_allow_single_direction_validation"),
                    False,
                )
            ),
        }

    @classmethod
    def _walk_forward_validation_candidate_board_payload(
        cls,
        candidate: dict[str, Any],
    ) -> dict[str, Any]:
        walk_diag = cls._as_dict(candidate.get("walk_forward_profit_diagnostics"))
        board = cls._as_dict(
            candidate.get("walk_forward_validation_candidate_board")
            or walk_diag.get("walk_forward_validation_candidate_board")
        )
        best_failed_total_r = cls._as_list(
            candidate.get("best_failed_total_r_by_fold", board.get("best_failed_total_r_by_fold"))
        )
        board_rows = cls._as_list(
            candidate.get("validation_candidate_board_rows", board.get("candidate_board_rows"))
        )
        board_row_preview = board_rows[:3]
        best_failed_preview = best_failed_total_r[:3]
        return {
            "walk_forward_validation_candidate_board_status": (
                candidate.get("walk_forward_validation_candidate_board_status")
                or board.get("diagnostic_status")
            ),
            "walk_forward_validation_candidate_board_verdict": (
                candidate.get("walk_forward_validation_candidate_board_verdict")
                or board.get("verdict")
            ),
            "recommended_validation_repair_profile": (
                candidate.get("recommended_validation_repair_profile")
                or board.get("recommended_validation_repair_profile")
            ),
            "total_r_below_min_fold_count": cls._int_or_zero(
                candidate.get("total_r_below_min_fold_count", board.get("total_r_below_min_fold_count"))
            ),
            "total_r_repair_candidate_fold_count": cls._int_or_zero(
                candidate.get(
                    "total_r_repair_candidate_fold_count",
                    board.get("total_r_repair_candidate_fold_count"),
                )
            ),
            "median_best_total_r_deficit": cls._float_or_none(
                candidate.get("median_best_total_r_deficit", board.get("median_best_total_r_deficit"))
            ),
            "max_best_total_r_deficit": cls._float_or_none(
                candidate.get("max_best_total_r_deficit", board.get("max_best_total_r_deficit"))
            ),
            "best_failed_total_r_by_fold_total_count": int(
                candidate.get(
                    "best_failed_total_r_by_fold_total_count",
                    board.get("best_failed_total_r_by_fold_total_count", len(best_failed_total_r)),
                )
                or 0
            ),
            "best_failed_total_r_by_fold_truncated": bool(
                candidate.get(
                    "best_failed_total_r_by_fold_truncated",
                    board.get("best_failed_total_r_by_fold_truncated", len(best_failed_total_r) > len(best_failed_preview)),
                )
            ),
            "best_failed_total_r_by_fold": best_failed_preview,
            "validation_candidate_board_rows_total_count": int(
                candidate.get(
                    "validation_candidate_board_rows_total_count",
                    board.get("candidate_board_rows_total_count", len(board_rows)),
                )
                or 0
            ),
            "validation_candidate_board_rows_truncated": bool(
                candidate.get(
                    "validation_candidate_board_rows_truncated",
                    board.get("candidate_board_rows_truncated", len(board_rows) > len(board_row_preview)),
                )
            ),
            "validation_candidate_board_rows": board_row_preview,
            "worst_fold_root_cause": cls._as_dict(
                candidate.get("worst_fold_root_cause")
                or board.get("worst_fold_root_cause")
            ),
            "primary_validation_root_cause_counts": cls._as_dict(
                candidate.get("primary_validation_root_cause_counts")
                or board.get("primary_root_cause_counts")
            ),
            "fold_root_cause_count": cls._int_or_zero(
                candidate.get(
                    "fold_root_cause_count",
                    board.get("fold_root_cause_count"),
                )
            ),
            "validation_fold_root_cause_summary": cls._as_dict(
                candidate.get("validation_fold_root_cause_summary")
                or walk_diag.get("validation_fold_root_cause_summary")
            ),
        }

    @staticmethod
    def _candidate_status(candidate: dict[str, Any]) -> str:
        return str(candidate.get("candidate_status") or "").upper()

    @classmethod
    def _is_failed_candidate(cls, candidate: dict[str, Any]) -> bool:
        return cls._candidate_status(candidate) == "FAILED"

    @classmethod
    def _candidate_score(cls, candidate: dict[str, Any]) -> float | None:
        if cls._is_failed_candidate(candidate):
            return None

        score = candidate.get("score")
        if score is None:
            return None

        return float(score)

    @classmethod
    def _best_candidate(cls, summary: dict[str, Any]) -> dict[str, Any]:
        candidate_results = [
            cls._as_dict(item)
            for item in cls._as_list(summary.get("candidate_results"))
            if isinstance(item, dict)
        ]

        eligible_candidates = [
            candidate
            for candidate in candidate_results
            if not cls._is_failed_candidate(candidate)
        ]

        best_config_id = summary.get("best_candidate_config_id")
        if best_config_id is not None:
            for candidate in eligible_candidates:
                if candidate.get("config_id") == best_config_id:
                    return candidate

        scored = [
            candidate
            for candidate in eligible_candidates
            if cls._candidate_score(candidate) is not None
        ]

        if scored:
            return max(scored, key=lambda candidate: cls._candidate_score(candidate) or -9999.0)

        return eligible_candidates[0] if eligible_candidates else {}

    @classmethod
    def _symbol_result(cls, summary: dict[str, Any]) -> dict[str, Any]:
        best_candidate = dict(cls._best_candidate(summary))
        apply_selected_decision_policy_metrics(best_candidate)
        summary_warnings = [str(item) for item in cls._as_list(summary.get("warnings"))]
        candidate_warnings = [str(item) for item in cls._as_list(best_candidate.get("warnings"))]
        summary_regime_status = cls._as_dict(summary.get("regime_label_builder_status"))
        gap_severity_for_training = str(summary.get("gap_severity_for_training") or "UNKNOWN")
        gap_training_safe = bool(summary.get("gap_training_safe", False))
        failed_gates, passed_gates = normalize_gap_quality_gate(
            gap_severity_for_training=gap_severity_for_training,
            gap_training_safe=gap_training_safe,
            failed_gates=[str(item) for item in cls._as_list(best_candidate.get("failed_gates"))],
            passed_gates=[str(item) for item in cls._as_list(best_candidate.get("passed_gates"))],
        )
        candidate_results_by_config_id = {
            str(candidate.get("config_id")): candidate
            for candidate in [
                cls._as_dict(item)
                for item in cls._as_list(summary.get("candidate_results"))
                if isinstance(item, dict)
            ]
            if candidate.get("config_id") is not None
        }

        entry_path_candidate_payload_keys = (
            "profit_factor",
            "profit_total_r",
            "resolved_signal_count",
            "signal_count",
            "win_rate",
            "gross_profit_r",
            "gross_loss_r",
            "walk_forward_profit_factor",
            "walk_forward_total_r",
            "walk_forward_global_total_r",
            "walk_forward_fold_count",
            "entry_path_quality_filter_enabled",
            "entry_path_quality_min_threshold",
            "stop_pressure_max_risk_score",
            "mae_pressure_max_risk_score",
            "entry_path_quality_masked_row_count",
            "entry_path_quality_forced_no_trade_count",
            "entry_path_quality_mask_trade_prediction_removed_count",
            "entry_path_quality_mask_false_positive_removed_count",
            "entry_path_quality_filter_summary",
            "entry_path_quality_filter_diagnostics",
            "entry_path_prediction_filter_summary",
            "stop_pressure_effectiveness_audit",
            "walk_forward_profit_diagnostics",
            "directional_side_filter_summary",
            "directional_side_filter_profile",
            "allowed_signal_directions",
            "research_only_total_r_repair_enabled",
            "validation_total_r_repair_profile",
            "research_only_acceptance_block_reason",
            "walk_forward_validation_candidate_board",
            "walk_forward_validation_candidate_board_status",
            "walk_forward_validation_candidate_board_verdict",
            "recommended_validation_repair_profile",
            "total_r_below_min_fold_count",
            "total_r_repair_candidate_fold_count",
            "median_best_total_r_deficit",
            "max_best_total_r_deficit",
            "best_failed_total_r_by_fold",
            "best_failed_total_r_by_fold_total_count",
            "best_failed_total_r_by_fold_truncated",
            "validation_candidate_board_rows",
            "validation_candidate_board_rows_total_count",
            "validation_candidate_board_rows_truncated",
            "worst_fold_root_cause",
            "primary_validation_root_cause_counts",
            "fold_root_cause_count",
            "validation_fold_root_cause_summary",
        )

        configs_ranked: list[dict[str, Any]] = []
        for row in cls._as_list(summary.get("configs_ranked") or summary.get("ranking")):
            payload = dict(row)
            matching_candidate = candidate_results_by_config_id.get(str(payload.get("config_id")))
            if matching_candidate:
                for key in entry_path_candidate_payload_keys:
                    value = matching_candidate.get(key)
                    if value is None:
                        continue
                    if isinstance(value, dict) and not value:
                        continue
                    if key not in payload or payload.get(key) in (None, {}, []):
                        payload[key] = value
            apply_selected_decision_policy_metrics(payload)
            row_failed_gates, row_passed_gates = normalize_gap_quality_gate(
                gap_severity_for_training=payload.get("gap_severity_for_training", gap_severity_for_training),
                gap_training_safe=payload.get("gap_training_safe", gap_training_safe),
                failed_gates=[str(item) for item in cls._as_list(payload.get("failed_gates"))],
                passed_gates=[str(item) for item in cls._as_list(payload.get("passed_gates"))],
            )
            payload["failed_gates"] = row_failed_gates
            payload["passed_gates"] = row_passed_gates
            payload["prediction_root_cause_audit"] = cls._as_dict(
                payload.get("prediction_root_cause_audit")
            )
            payload["book_driven_forensic_audit"] = cls._as_dict(
                payload.get("book_driven_forensic_audit")
            )
            payload["label_mode_comparison_audit"] = cls._as_dict(
                payload.get("label_mode_comparison_audit")
            )
            payload["flat_subtype_audit"] = cls._as_dict(
                payload.get("flat_subtype_audit")
            )
            payload["setup_aware_label_diagnostics"] = cls._as_dict(
                payload.get("setup_aware_label_diagnostics")
            )
            payload["schwager_slice_robustness"] = cls._as_dict(
                payload.get("schwager_slice_robustness")
            )
            payload["schwager_robustness_decision_board"] = cls._as_dict(
                payload.get("schwager_robustness_decision_board")
            )
            payload.update(cls._entry_path_audit_payload(payload))
            payload.update(cls._directional_side_audit_payload(payload))
            payload.update(cls._walk_forward_stability_payload(payload))
            payload.update(cls._directional_side_signal_recovery_payload(payload))
            payload.update(cls._directional_side_validation_gate_payload(payload))
            payload.update(cls._walk_forward_validation_candidate_board_payload(payload))
            configs_ranked.append(payload)
        best_entry_path_audit = cls._entry_path_audit_payload(best_candidate)
        best_directional_side_audit = cls._directional_side_audit_payload(best_candidate)
        best_signal_recovery = cls._directional_side_signal_recovery_payload(best_candidate)
        best_validation_gate_diagnostics = cls._directional_side_validation_gate_payload(
            best_candidate
        )
        best_validation_candidate_board = cls._walk_forward_validation_candidate_board_payload(
            best_candidate
        )
        return {
            "symbol": str(summary.get("symbol")),
            "experiment_id": summary.get("experiment_id"),
            "experiment_status": summary.get("experiment_status"),
            "candidate_count": int(summary.get("candidate_count", 0) or 0),
            "evaluated_candidate_count": int(summary.get("evaluated_candidate_count", 0) or 0),
            "failed_candidate_count": int(summary.get("failed_candidate_count", 0) or 0),
            "accepted_candidate_count": int(summary.get("accepted_candidate_count", 0) or 0),
            "rejected_candidate_count": int(summary.get("rejected_candidate_count", 0) or 0),
            "best_candidate_config_id": best_candidate.get("config_id"),
            "best_candidate_score": cls._candidate_score(best_candidate),
            "candidate_status": best_candidate.get("candidate_status"),
            "feature_version_used": summary.get("feature_version_used"),
            "candle_ta_context_features_attached": bool(summary.get("candle_ta_context_features_attached", False)),
            "candle_ta_context_feature_count": int(summary.get("candle_ta_context_feature_count", 0) or 0),
            "candle_ta_context_missing_reason": summary.get("candle_ta_context_missing_reason"),
            "book_setup_context_features_attached": bool(
                summary.get("book_setup_context_features_attached", False)
            ),
            "book_setup_context_feature_count": int(
                summary.get("book_setup_context_feature_count", 0) or 0
            ),
            "fv4_feature_count": int(summary.get("fv4_feature_count", 0) or 0),
            "nison_feature_count": int(summary.get("nison_feature_count", 0) or 0),
            "altunina_feature_count": int(summary.get("altunina_feature_count", 0) or 0),
            "path_context_feature_count": int(summary.get("path_context_feature_count", 0) or 0),
            "htf_context_feature_count": int(summary.get("htf_context_feature_count", 0) or 0),
            "missing_context_feature_count": int(
                summary.get("missing_context_feature_count", 0) or 0
            ),
            "real_feature_diagnostics_used": bool(summary.get("real_feature_diagnostics_used", False)),
            "real_feature_diagnostics_row_count": int(summary.get("real_feature_diagnostics_row_count", 0) or 0),
            "real_feature_diagnostics_missing_reason": summary.get("real_feature_diagnostics_missing_reason"),
            "effective_gap_count_for_training": int(summary.get("effective_gap_count_for_training", 0) or 0),
            "gap_severity_for_training": gap_severity_for_training,
            "gap_training_safe": gap_training_safe,
            "baseline_edge": cls._float_or_none(
                best_candidate.get("baseline_edge", best_candidate.get("accuracy_edge"))
            ),
            "baseline_edge_status": best_candidate.get("baseline_edge_status"),
            "model_accuracy": cls._float_or_none(best_candidate.get("model_accuracy")),
            "baseline_accuracy": cls._float_or_none(best_candidate.get("baseline_accuracy")),
            "collapse_detected": bool(best_candidate.get("collapse_detected", False)),
            "collapse_type": best_candidate.get("collapse_type"),
            "collapse_severity": best_candidate.get("collapse_severity"),
            "collapse_gate_failed": bool(best_candidate.get("collapse_gate_failed", False)),
            "collapse_diagnostics_v2": cls._as_dict(
                summary.get("collapse_diagnostics_v2")
                or best_candidate.get("collapse_diagnostics_v2")
            ),
            "profit_factor": cls._float_or_none(best_candidate.get("profit_factor")),
            "profit_total_r": cls._float_or_none(best_candidate.get("profit_total_r")),
            "walk_forward_profit_factor": cls._float_or_none(best_candidate.get("walk_forward_profit_factor")),
            "walk_forward_total_r": cls._float_or_none(best_candidate.get("walk_forward_global_total_r")),
            "model_quality_validation_status": best_candidate.get(
                "model_quality_validation_status",
                summary.get("model_quality_validation_status"),
            ),
            "anti_collapse_diagnostics": cls._as_dict(best_candidate.get("anti_collapse_diagnostics")),
            "anti_collapse_score": cls._float_or_none(best_candidate.get("anti_collapse_score")),
            "anti_collapse_status": best_candidate.get("anti_collapse_status"),
            "flat_bias_diagnostics": cls._as_dict(best_candidate.get("flat_bias_diagnostics")),
            "flat_bias_detected": bool(best_candidate.get("flat_bias_detected", False)),
            "down_blindness_detected": bool(best_candidate.get("down_blindness_detected", False)),
            "symbol_bias_severity": best_candidate.get("symbol_bias_severity"),
            "collapse_tuning_summary": cls._as_dict(best_candidate.get("collapse_tuning_summary")),
            "score_components": cls._as_dict(best_candidate.get("score_components")),
            "walk_forward_profit_diagnostics": cls._as_dict(
                summary.get("walk_forward_profit_diagnostics")
                or best_candidate.get("walk_forward_profit_diagnostics")
            ),
            "profit_aware_diagnostics": cls._as_dict(
                summary.get("profit_aware_diagnostics")
                or best_candidate.get("profit_aware_diagnostics")
            ),
            "directional_edge_bias_audit": cls._as_dict(
                best_directional_side_audit.get("directional_edge_bias_audit")
            ),
            "directional_side_filter_summary": cls._as_dict(
                best_directional_side_audit.get("directional_side_filter_summary")
            ),
            "directional_side_filter_profile": best_directional_side_audit.get(
                "directional_side_filter_profile"
            ),
            "allowed_signal_directions": list(
                best_directional_side_audit.get("allowed_signal_directions") or []
            ),
            "direction_balance_ratio": cls._float_or_none(
                best_directional_side_audit.get("direction_balance_ratio")
            ),
            "directional_profit_skew_r": cls._float_or_none(
                best_directional_side_audit.get("directional_profit_skew_r")
            ),
            "directional_profit_skew_ratio": cls._float_or_none(
                best_directional_side_audit.get("directional_profit_skew_ratio")
            ),
            "long_total_r": cls._float_or_none(best_directional_side_audit.get("long_total_r")),
            "short_total_r": cls._float_or_none(best_directional_side_audit.get("short_total_r")),
            "long_avg_r": cls._float_or_none(best_directional_side_audit.get("long_avg_r")),
            "short_avg_r": cls._float_or_none(best_directional_side_audit.get("short_avg_r")),
            "dominant_direction": best_directional_side_audit.get("dominant_direction"),
            "profit_exit_root_cause_audit": cls._as_dict(
                summary.get("profit_exit_root_cause_audit")
                or best_candidate.get("profit_exit_root_cause_audit")
                or cls._as_dict(best_candidate.get("profit_aware_diagnostics")).get("profit_exit_root_cause_audit")
            ),
            "exit_policy_profile": best_candidate.get("exit_policy_profile") or cls._as_dict(best_candidate.get("label_config")).get("exit_policy_profile"),
            "exit_timeout_bars": best_candidate.get("exit_timeout_bars") or cls._as_dict(best_candidate.get("label_config")).get("exit_timeout_bars"),
            "exit_mitigation_loss_r": best_candidate.get("exit_mitigation_loss_r") or cls._as_dict(best_candidate.get("label_config")).get("exit_mitigation_loss_r"),
            "exit_neutral_abs_r": best_candidate.get("exit_neutral_abs_r") or cls._as_dict(best_candidate.get("label_config")).get("exit_neutral_abs_r"),
            "walk_forward_profit_exit_root_cause_summary": cls._as_dict(
                summary.get("walk_forward_profit_exit_root_cause_summary")
                or best_candidate.get("walk_forward_profit_exit_root_cause_summary")
                or cls._as_dict(best_candidate.get("walk_forward_profit_diagnostics")).get(
                    "walk_forward_profit_exit_root_cause_summary"
                )
            ),
            "directional_side_signal_recovery_diagnostics": best_signal_recovery.get("directional_side_signal_recovery_diagnostics"),
            "directional_side_signal_recovery_status": best_signal_recovery.get("directional_side_signal_recovery_status"),
            "directional_side_signal_recovery_verdict": best_signal_recovery.get("directional_side_signal_recovery_verdict"),
            "primary_signal_loss_reason_counts": best_signal_recovery.get("primary_signal_loss_reason_counts"),
            "validation_gate_failure_reason_counts": best_validation_gate_diagnostics.get("validation_gate_failure_reason_counts"),
            "side_aware_relaxed_fold_count": best_validation_gate_diagnostics.get("side_aware_relaxed_fold_count"),
            "side_aware_validation_relaxation_enabled": best_validation_gate_diagnostics.get("side_aware_validation_relaxation_enabled"),
            "side_aware_min_validation_signal_count": best_validation_gate_diagnostics.get("side_aware_min_validation_signal_count"),
            "side_aware_min_validation_profit_factor": best_validation_gate_diagnostics.get("side_aware_min_validation_profit_factor"),
            "side_aware_min_validation_total_r": best_validation_gate_diagnostics.get("side_aware_min_validation_total_r"),
            "side_aware_min_validation_expectancy_r": best_validation_gate_diagnostics.get("side_aware_min_validation_expectancy_r"),
            "side_aware_allow_single_direction_validation": best_validation_gate_diagnostics.get("side_aware_allow_single_direction_validation"),
            "walk_forward_validation_candidate_board_status": best_validation_candidate_board.get("walk_forward_validation_candidate_board_status"),
            "walk_forward_validation_candidate_board_verdict": best_validation_candidate_board.get("walk_forward_validation_candidate_board_verdict"),
            "recommended_validation_repair_profile": best_validation_candidate_board.get("recommended_validation_repair_profile"),
            "total_r_below_min_fold_count": best_validation_candidate_board.get("total_r_below_min_fold_count"),
            "total_r_repair_candidate_fold_count": best_validation_candidate_board.get("total_r_repair_candidate_fold_count"),
            "median_best_total_r_deficit": best_validation_candidate_board.get("median_best_total_r_deficit"),
            "max_best_total_r_deficit": best_validation_candidate_board.get("max_best_total_r_deficit"),
            "best_failed_total_r_by_fold": best_validation_candidate_board.get("best_failed_total_r_by_fold"),
            "validation_candidate_board_rows": best_validation_candidate_board.get("validation_candidate_board_rows"),
            "worst_fold_root_cause": best_validation_candidate_board.get("worst_fold_root_cause"),
            "primary_validation_root_cause_counts": best_validation_candidate_board.get("primary_validation_root_cause_counts"),
            "fold_root_cause_count": best_validation_candidate_board.get("fold_root_cause_count"),
            "validation_fold_root_cause_summary": best_validation_candidate_board.get("validation_fold_root_cause_summary"),
            "research_only_total_r_repair_enabled": bool(
                best_candidate.get(
                    "research_only_total_r_repair_enabled",
                    cls._as_dict(best_candidate.get("label_config")).get(
                        "research_only_total_r_repair_enabled",
                        False,
                    ),
                )
            ),
            "validation_total_r_repair_profile": (
                best_candidate.get("validation_total_r_repair_profile")
                or cls._as_dict(best_candidate.get("label_config")).get(
                    "validation_total_r_repair_profile"
                )
            ),
            "research_only_acceptance_block_reason": (
                best_candidate.get("research_only_acceptance_block_reason")
                or cls._as_dict(best_candidate.get("label_config")).get(
                    "research_only_acceptance_block_reason"
                )
            ),
            "side_filter_removed_all_fold_count": best_signal_recovery.get("side_filter_removed_all_fold_count"),
            "raw_signal_available_but_filtered_out_count": best_signal_recovery.get("raw_signal_available_but_filtered_out_count"),
            "threshold_too_strict_fold_count": best_signal_recovery.get("threshold_too_strict_fold_count"),
            "entry_path_quality_filter_enabled": bool(
                best_entry_path_audit.get("entry_path_quality_filter_enabled", False)
            ),
            "entry_path_quality_min_threshold": cls._float_or_none(
                best_entry_path_audit.get("entry_path_quality_min_threshold")
            ),
            "stop_pressure_max_risk_score": cls._float_or_none(
                best_entry_path_audit.get("stop_pressure_max_risk_score")
            ),
            "mae_pressure_max_risk_score": cls._float_or_none(
                best_entry_path_audit.get("mae_pressure_max_risk_score")
            ),
            "entry_path_quality_masked_row_count": int(
                summary.get(
                    "entry_path_quality_masked_row_count",
                    best_candidate.get("entry_path_quality_masked_row_count", 0),
                )
                or 0
            ),
            "entry_path_quality_forced_no_trade_count": int(
                summary.get(
                    "entry_path_quality_forced_no_trade_count",
                    best_candidate.get("entry_path_quality_forced_no_trade_count", 0),
                )
                or 0
            ),
            "entry_path_quality_mask_trade_prediction_removed_count": int(
                summary.get(
                    "entry_path_quality_mask_trade_prediction_removed_count",
                    best_candidate.get("entry_path_quality_mask_trade_prediction_removed_count", 0),
                )
                or 0
            ),
            "entry_path_quality_mask_false_positive_removed_count": int(
                summary.get(
                    "entry_path_quality_mask_false_positive_removed_count",
                    best_candidate.get("entry_path_quality_mask_false_positive_removed_count", 0),
                )
                or 0
            ),
            "entry_path_quality_filter_summary": cls._as_dict(
                summary.get("entry_path_quality_filter_summary")
                or best_candidate.get("entry_path_quality_filter_summary")
            ),
            "entry_path_prediction_filter_summary": cls._as_dict(
                best_entry_path_audit.get("entry_path_prediction_filter_summary")
            ),
            "stop_pressure_effectiveness_audit": cls._as_dict(
                best_entry_path_audit.get("stop_pressure_effectiveness_audit")
            ),
            "entry_path_final_signal_original_count": int(
                best_entry_path_audit.get("entry_path_final_signal_original_count", 0) or 0
            ),
            "entry_path_final_signal_filtered_count": int(
                best_entry_path_audit.get("entry_path_final_signal_filtered_count", 0) or 0
            ),
            "entry_path_final_signal_blocked_count": int(
                best_entry_path_audit.get("entry_path_final_signal_blocked_count", 0) or 0
            ),
            "entry_path_stream_consistency_ok": best_entry_path_audit["entry_path_stream_consistency_ok"],
            "failed_gates": failed_gates,
            "passed_gates": passed_gates,
            "regime_features_attached": bool(summary.get("regime_features_attached", False)),
            "regime_feature_count": int(summary.get("regime_feature_count", 0) or 0),
            "regime_features_missing_reason": summary.get("regime_features_missing_reason"),
            "regime_label_builder_used_in_training": bool(
                summary.get(
                    "regime_label_builder_used_in_training_any",
                    summary_regime_status.get("regime_label_builder_used_in_training", False),
                )
            ),
            "regime_specific_training_applied": bool(
                summary.get(
                    "regime_specific_training_applied_any",
                    summary.get("regime_specific_training_applied", False),
                )
            ),
            "regime_label_builder_status": cls._as_dict(
                summary.get("regime_label_builder_status")
                or best_candidate.get("regime_label_builder_status")
            ),
            "warnings": list(dict.fromkeys(summary_warnings + candidate_warnings)),
            "accuracy": cls._float_or_none(best_candidate.get("model_accuracy")),
            "best_baseline_accuracy": cls._float_or_none(best_candidate.get("baseline_accuracy")),
            "predicted_class_distribution": cls._as_dict(best_candidate.get("predicted_class_distribution")),
            "actual_class_distribution": cls._as_dict(best_candidate.get("actual_class_distribution")),
            "decision_policy_grid_diagnostics": cls._as_dict(
                best_candidate.get("decision_policy_grid_diagnostics")
            ),
            "decision_policy_selected_policy_id": best_candidate.get(
                "decision_policy_selected_policy_id"
            ) or cls._as_dict(best_candidate.get("decision_policy_grid_diagnostics")).get(
                "selected_policy_id"
            ),
            "prediction_root_cause_audit": cls._as_dict(
                best_candidate.get("prediction_root_cause_audit")
            ),
            "book_driven_forensic_audit": cls._as_dict(
                best_candidate.get("book_driven_forensic_audit")
            ),
            "label_mode_comparison_audit": cls._as_dict(
                summary.get("label_mode_comparison_audit")
                or best_candidate.get("label_mode_comparison_audit")
            ),
            "flat_subtype_audit": cls._as_dict(
                summary.get("flat_subtype_audit")
                or best_candidate.get("flat_subtype_audit")
            ),
            "setup_aware_label_diagnostics": cls._as_dict(
                summary.get("setup_aware_label_diagnostics")
                or best_candidate.get("setup_aware_label_diagnostics")
            ),
            "schwager_slice_robustness": cls._as_dict(
                summary.get("schwager_slice_robustness")
                or best_candidate.get("schwager_slice_robustness")
            ),
            "schwager_robustness_decision_board": cls._as_dict(
                summary.get("schwager_robustness_decision_board")
                or best_candidate.get("schwager_robustness_decision_board")
            ),
            "prediction_decision_source": best_candidate.get("prediction_decision_source"),
            "reasons_why_best_still_rejected": [
                str(item) for item in cls._as_list(summary.get("reasons_why_best_still_rejected"))
            ],
            "configs_ranked": configs_ranked,
        }

    @classmethod
    def _full_candidate_payloads(
        cls,
        summaries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Return compact full candidate payloads from per-symbol summaries.

        Source-of-truth for deep diagnostics is summary["candidate_results"].
        configs_ranked/ranking may be compact and may not contain top-level
        worst_fold_root_cause / validation candidate board details.
        """
        payloads: list[dict[str, Any]] = []
        for summary in summaries:
            symbol = str(summary.get("symbol") or "")
            source_items = cls._as_list(summary.get("candidate_results"))
            if not source_items:
                source_items = cls._as_list(summary.get("configs_ranked") or summary.get("ranking"))
            for item in source_items:
                if not isinstance(item, dict):
                    continue
                payload = dict(item)
                if symbol and payload.get("symbol") is None:
                    payload["symbol"] = symbol
                payload.update(cls._directional_side_audit_payload(payload))
                payload.update(cls._walk_forward_stability_payload(payload))
                payload.update(cls._directional_side_signal_recovery_payload(payload))
                payload.update(cls._directional_side_validation_gate_payload(payload))
                payload.update(cls._walk_forward_validation_candidate_board_payload(payload))
                payloads.append(payload)
        return payloads

    @classmethod
    def _directional_side_candidate_payloads(
        cls,
        summaries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return cls._full_candidate_payloads(summaries)

    @staticmethod
    def _prediction_root_cause_summary(candidates: list[dict[str, object]]) -> dict[str, object]:
        warning_counts: Counter[str] = Counter()
        recommendation_counts: Counter[str] = Counter()
        available_count = 0

        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            audit = candidate.get("prediction_root_cause_audit") or {}
            if not isinstance(audit, dict):
                continue
            if audit.get("diagnostic_name") != "prediction_root_cause_audit":
                continue
            available_count += 1
            for warning in audit.get("warnings") or []:
                warning_counts[str(warning)] += 1
            for recommendation in audit.get("recommendations") or []:
                recommendation_counts[str(recommendation)] += 1

        return {
            "diagnostic_name": "prediction_root_cause_summary",
            "diagnostic_version": "ml38_9_6",
            "available_candidate_count": available_count,
            "warning_counts": dict(warning_counts),
            "top_warnings": [warning for warning, _count in warning_counts.most_common(5)],
            "top_recommendations": [
                text for text, _count in recommendation_counts.most_common(5)
            ],
        }

    @staticmethod
    def _book_driven_forensic_summary(candidates: list[dict[str, object]]) -> dict[str, object]:
        diagnosis_counts: Counter[str] = Counter()
        recommendation_counts: Counter[str] = Counter()
        available_count = 0
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            audit = candidate.get("book_driven_forensic_audit") or {}
            if not isinstance(audit, dict):
                continue
            if audit.get("diagnostic_name") != "book_driven_forensic_audit":
                continue
            available_count += 1
            diagnosis = audit.get("final_diagnosis")
            recommendation = audit.get("next_action_recommendation")
            if diagnosis:
                diagnosis_counts[str(diagnosis)] += 1
            if recommendation:
                recommendation_counts[str(recommendation)] += 1
        return {
            "diagnostic_name": "book_driven_forensic_summary",
            "diagnostic_version": "ml38_9_7",
            "available_candidate_count": available_count,
            "final_diagnosis_counts": dict(diagnosis_counts),
            "top_final_diagnoses": [name for name, _count in diagnosis_counts.most_common(5)],
            "top_next_action_recommendations": [
                name for name, _count in recommendation_counts.most_common(5)
            ],
        }

    @staticmethod
    def _schwager_robustness_summary(candidates: list[dict[str, object]]) -> dict[str, object]:
        decision_counts: Counter[str] = Counter()
        primary_failure_counts: Counter[str] = Counter()
        available_count = 0
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            board = candidate.get("schwager_robustness_decision_board") or {}
            if not isinstance(board, dict):
                continue
            if board.get("diagnostic_name") != "schwager_robustness_decision_board":
                continue
            available_count += 1
            decision = board.get("final_research_decision")
            primary_failure = board.get("primary_failure")
            if decision:
                decision_counts[str(decision)] += 1
            if primary_failure:
                primary_failure_counts[str(primary_failure)] += 1
        return {
            "diagnostic_name": "schwager_robustness_multi_symbol_summary",
            "diagnostic_version": "ml38_10_2",
            "available_candidate_count": available_count,
            "final_research_decision_counts": dict(decision_counts),
            "primary_failure_counts": dict(primary_failure_counts),
            "top_final_research_decisions": [
                name for name, _count in decision_counts.most_common(5)
            ],
            "top_primary_failures": [
                name for name, _count in primary_failure_counts.most_common(5)
            ],
        }

    @staticmethod
    def _label_mode_audit_summary(symbol_results: list[dict[str, Any]]) -> dict[str, Any]:
        recommendation_by_symbol: dict[str, str | None] = {}
        conflict_ratio_by_symbol: dict[str, float | None] = {}
        ambiguous_ratio_by_symbol: dict[str, float | None] = {}
        for item in symbol_results:
            audit = dict(item.get("label_mode_comparison_audit", {}))
            symbol = str(item.get("symbol") or "UNKNOWN")
            recommendation_by_symbol[symbol] = audit.get("label_mode_recommendation")
            conflict_ratio_by_symbol[symbol] = (
                None
                if audit.get("future_close_vs_first_touch_conflict_ratio") is None
                else float(audit["future_close_vs_first_touch_conflict_ratio"])
            )
            ambiguous_ratio_by_symbol[symbol] = (
                None
                if audit.get("first_touch_ambiguous_ratio") is None
                else float(audit["first_touch_ambiguous_ratio"])
            )
        return {
            "diagnostic_name": "label_mode_audit_multi_symbol_summary",
            "diagnostic_version": "ml38_9_9",
            "recommendation_by_symbol": recommendation_by_symbol,
            "conflict_ratio_by_symbol": conflict_ratio_by_symbol,
            "ambiguous_ratio_by_symbol": ambiguous_ratio_by_symbol,
        }

    @staticmethod
    def _flat_subtype_summary(symbol_results: list[dict[str, Any]]) -> dict[str, Any]:
        dominant_by_symbol: dict[str, Any] = {}
        counts_by_symbol: dict[str, Any] = {}
        for item in symbol_results:
            audit = dict(item.get("flat_subtype_audit", {}))
            symbol = str(item.get("symbol") or "UNKNOWN")
            dominant_by_symbol[symbol] = audit.get("dominant_flat_subtype")
            counts_by_symbol[symbol] = dict(audit.get("flat_subtype_counts", {}))
        return {
            "diagnostic_name": "flat_subtype_multi_symbol_summary",
            "diagnostic_version": "ml38_9_9",
            "dominant_flat_subtype_by_symbol": dominant_by_symbol,
            "flat_subtype_counts_by_symbol": counts_by_symbol,
        }

    @staticmethod
    def _setup_aware_label_summary(symbol_results: list[dict[str, Any]]) -> dict[str, Any]:
        recommended_by_symbol: dict[str, Any] = {}
        ambiguous_ratio_by_symbol: dict[str, Any] = {}
        for item in symbol_results:
            audit = dict(item.get("setup_aware_label_diagnostics", {}))
            symbol = str(item.get("symbol") or "UNKNOWN")
            recommended_by_symbol[symbol] = dict(
                audit.get("recommended_label_mode_by_setup_type", {})
            )
            ambiguous_ratio_by_symbol[symbol] = dict(
                audit.get("ambiguous_ratio_by_setup_type", {})
            )
        return {
            "diagnostic_name": "setup_aware_label_multi_symbol_summary",
            "diagnostic_version": "ml38_9_9",
            "recommended_label_mode_by_symbol": recommended_by_symbol,
            "ambiguous_ratio_by_symbol": ambiguous_ratio_by_symbol,
        }

    @classmethod
    def _anti_collapse_summary(cls, symbol_results: list[dict[str, Any]]) -> dict[str, Any]:
        """Собирает ML38.5 anti-collapse summary по всем символам.

        Используется только для анализа качества.
        Не принимает модель автоматически.
        """
        best_by_symbol: dict[str, dict[str, Any]] = {}
        status_counts: dict[str, int] = {"GOOD": 0, "WATCH": 0, "WEAK": 0, "UNKNOWN": 0}

        for symbol_result in symbol_results:
            symbol = str(symbol_result.get("symbol") or "UNKNOWN")
            best_row: dict[str, Any] | None = None
            best_score: float | None = None

            for row in cls._as_list(symbol_result.get("configs_ranked")):
                if not isinstance(row, dict):
                    continue
                status = str(row.get("anti_collapse_status") or "UNKNOWN").upper()
                if status not in status_counts:
                    status_counts["UNKNOWN"] += 1
                else:
                    status_counts[status] += 1

                score = cls._float_or_none(row.get("anti_collapse_score"))
                if cls._is_failed_candidate(row):
                    continue

                score = cls._float_or_none(row.get("anti_collapse_score"))
                if score is None:
                    continue
                if best_score is None or score > best_score:
                    best_score = score
                    best_row = row

            if best_row is not None:
                best_by_symbol[symbol] = {
                    "config_id": best_row.get("config_id"),
                    "candidate_status": best_row.get("candidate_status"),
                    "anti_collapse_score": best_row.get("anti_collapse_score"),
                    "anti_collapse_status": best_row.get("anti_collapse_status"),
                    "collapse_type": best_row.get("collapse_type"),
                    "flat_bias_detected": best_row.get("flat_bias_detected"),
                    "down_blindness_detected": best_row.get("down_blindness_detected"),
                    "walk_forward_profit_factor": best_row.get("walk_forward_profit_factor"),
                    "walk_forward_total_r": best_row.get("walk_forward_total_r"),
                }

        return {
            "diagnostic_name": "anti_collapse_multi_symbol_summary",
            "diagnostic_version": "ml38_5",
            "best_by_symbol": best_by_symbol,
            "good_count": status_counts["GOOD"],
            "watch_count": status_counts["WATCH"],
            "weak_count": status_counts["WEAK"],
            "unknown_count": status_counts["UNKNOWN"],
        }
    

    @classmethod
    def _confidence_profitability_summary(cls, symbol_results: list[dict[str, Any]]) -> dict[str, Any]:
        """Сводка ML38.6 confidence/profitability по всем символам.
    
        Не принимает модель автоматически.
        Только помогает понять, какие configs уменьшают confidence collapse и дают PF/R.
        """
        best_by_symbol: dict[str, dict[str, Any]] = {}
        status_counts: dict[str, int] = {"GOOD": 0, "WATCH": 0, "WEAK": 0, "UNKNOWN": 0}
    
        for symbol_result in symbol_results:
            symbol = str(symbol_result.get("symbol") or "UNKNOWN")
            best_row: dict[str, Any] | None = None
            best_score: float | None = None
    
            for row in cls._as_list(symbol_result.get("configs_ranked")):
                if not isinstance(row, dict):
                    continue
                status = str(row.get("confidence_profitability_status") or "UNKNOWN").upper()
                if status not in status_counts:
                    status_counts["UNKNOWN"] += 1
                else:
                    status_counts[status] += 1
    
                if cls._is_failed_candidate(row):
                    continue
                
                score = cls._float_or_none(row.get("confidence_profitability_score"))
                if score is None:
                    continue
                if best_score is None or score > best_score:
                    best_score = score
                    best_row = row
    
            if best_row is not None:
                diagnostics = cls._as_dict(best_row.get("confidence_profitability_diagnostics"))
                best_by_symbol[symbol] = {
                    "config_id": best_row.get("config_id"),
                    "candidate_status": best_row.get("candidate_status"),
                    "confidence_profitability_score": best_row.get("confidence_profitability_score"),
                    "confidence_profitability_status": best_row.get("confidence_profitability_status"),
                    "margin_q50": diagnostics.get("margin_q50"),
                    "margin_q90": diagnostics.get("margin_q90"),
                    "max_prob_q90": diagnostics.get("max_prob_q90"),
                    "rows_above_045": diagnostics.get("rows_above_045"),
                    "walk_forward_profit_factor": best_row.get("walk_forward_profit_factor"),
                    "walk_forward_total_r": best_row.get("walk_forward_total_r"),
                    "collapse_type": best_row.get("collapse_type"),
                    "flat_bias_detected": best_row.get("flat_bias_detected"),
                    "down_blindness_detected": best_row.get("down_blindness_detected"),
                }
    
        return {
            "diagnostic_name": "confidence_profitability_multi_symbol_summary",
            "diagnostic_version": "ml38_6",
            "best_by_symbol": best_by_symbol,
            "good_count": status_counts["GOOD"],
            "watch_count": status_counts["WATCH"],
            "weak_count": status_counts["WEAK"],
            "unknown_count": status_counts["UNKNOWN"],
            "accepts_candidate": False,
            "softens_gates": False,
        }


    @classmethod
    def _configs_ranked(cls, symbol_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for symbol_result in symbol_results:
            for row in symbol_result.get("configs_ranked", []):
                payload = dict(row)
                apply_selected_decision_policy_metrics(payload)
                decision_policy_payload = cls._as_dict(payload.get("decision_policy_grid_diagnostics"))
                payload["decision_policy_grid_diagnostics"] = decision_policy_payload
                payload["decision_policy_selected_policy_id"] = payload.get(
                    "decision_policy_selected_policy_id",
                    decision_policy_payload.get("selected_policy_id"),
                )
                payload["prediction_root_cause_audit"] = cls._as_dict(
                    payload.get("prediction_root_cause_audit")
                )
                payload["book_driven_forensic_audit"] = cls._as_dict(
                    payload.get("book_driven_forensic_audit")
                )
                payload["label_mode_comparison_audit"] = cls._as_dict(
                    payload.get("label_mode_comparison_audit")
                )
                payload["flat_subtype_audit"] = cls._as_dict(
                    payload.get("flat_subtype_audit")
                )
                payload["setup_aware_label_diagnostics"] = cls._as_dict(
                    payload.get("setup_aware_label_diagnostics")
                )
                payload.update(cls._entry_path_audit_payload(payload))
                payload.update(cls._directional_side_audit_payload(payload))
                payload.update(cls._walk_forward_stability_payload(payload))
                payload.update(cls._directional_side_signal_recovery_payload(payload))
                payload.update(cls._directional_side_validation_gate_payload(payload))
                payload.update(cls._walk_forward_validation_candidate_board_payload(payload))
                payload["symbol"] = symbol_result["symbol"]
                payload["excluded_from_best_selection"] = cls._is_failed_candidate(payload)
                rows.append(payload)
        rows.sort(
            key=lambda item: (
                bool(item.get("excluded_from_best_selection", False)),
                -float(item.get("score") or 0.0),
                str(item.get("symbol") or ""),
                str(item.get("config_id") or ""),
            )
        )
        for index, row in enumerate(rows, start=1):
            row["global_rank"] = index
        return rows

    @staticmethod
    def _gate_failure_counts(symbol_results: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for symbol_result in symbol_results:
            for gate_name in symbol_result["failed_gates"]:
                counts[gate_name] = counts.get(gate_name, 0) + 1
        return counts

    @classmethod
    def _directional_side_signal_recovery_summary(cls, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        counts: dict[str, int] = {}
        verdict_counts: dict[str, int] = {}
        side_profiles: dict[str, int] = {}
        for candidate in candidates:
            payload = cls._directional_side_signal_recovery_payload(candidate)
            status = str(payload.get("directional_side_signal_recovery_status") or "UNKNOWN")
            verdict = str(payload.get("directional_side_signal_recovery_verdict") or "UNKNOWN")
            profile = str(candidate.get("directional_side_filter_profile") or "both_directions")
            counts[status] = counts.get(status, 0) + 1
            verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
            side_profiles[profile] = side_profiles.get(profile, 0) + 1
        return {
            "diagnostic_name": "directional_side_signal_recovery_summary",
            "diagnostic_version": "ml38.10.23",
            "candidate_count": len(candidates),
            "status_counts": counts,
            "verdict_counts": verdict_counts,
            "side_profile_counts": side_profiles,
        }

    @classmethod
    def _walk_forward_validation_candidate_board_summary(
        cls,
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        verdict_counts: Counter[str] = Counter()
        repair_profile_counts: Counter[str] = Counter()
        repair_candidates: list[dict[str, Any]] = []
        for candidate in candidates:
            payload = cls._walk_forward_validation_candidate_board_payload(candidate)
            verdict = str(payload.get("walk_forward_validation_candidate_board_verdict") or "UNKNOWN")
            profile = str(payload.get("recommended_validation_repair_profile") or "UNKNOWN")
            verdict_counts[verdict] += 1
            repair_profile_counts[profile] += 1
            if bool(
                candidate.get(
                    "research_only_total_r_repair_enabled",
                    cls._as_dict(candidate.get("label_config")).get(
                        "research_only_total_r_repair_enabled",
                        False,
                    ),
                )
            ):
                repair_candidates.append(candidate)

        best_total_r_repair_probe = None
        if repair_candidates:
            ranked = sorted(
                repair_candidates,
                key=lambda item: (
                    -(
                        cls._candidate_score(item)
                        if cls._candidate_score(item) is not None
                        else float("-inf")
                    ),
                    -(cls._float_or_none(item.get("profit_factor")) or float("-inf")),
                    -(cls._float_or_none(item.get("profit_total_r")) or float("-inf")),
                    str(item.get("symbol") or ""),
                    str(item.get("config_id") or ""),
                ),
            )
            best = ranked[0]
            best_total_r_repair_probe = {
                "symbol": best.get("symbol"),
                "config_id": best.get("config_id"),
                "candidate_status": best.get("candidate_status"),
                "score": cls._candidate_score(best),
                "profit_factor": cls._float_or_none(best.get("profit_factor")),
                "profit_total_r": cls._float_or_none(best.get("profit_total_r")),
                "walk_forward_profit_factor": cls._float_or_none(best.get("walk_forward_profit_factor")),
                "walk_forward_total_r": cls._float_or_none(
                    best.get("walk_forward_total_r", best.get("walk_forward_global_total_r"))
                ),
                "recommended_validation_repair_profile": (
                    best.get("recommended_validation_repair_profile")
                ),
            }

        warnings: list[str] = []
        recommendations: list[str] = []
        if repair_candidates:
            warnings.append("research_only_total_r_repair_candidates_present")
            recommendations.append("keep_total_r_repair_candidates_out_of_acceptance")

        return {
            "diagnostic_name": "walk_forward_validation_candidate_board_multi_symbol_summary",
            "diagnostic_version": "ml38.10.25",
            "candidate_count": len(candidates),
            "verdict_counts": dict(verdict_counts),
            "recommended_validation_repair_profile_counts": dict(repair_profile_counts),
            "research_only_total_r_repair_candidate_count": len(repair_candidates),
            "best_total_r_repair_probe": best_total_r_repair_probe,
            "warnings": warnings,
            "recommendations": recommendations,
        }

    @classmethod
    def _walk_forward_fold_root_cause_board(
        cls,
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        primary_counts: Counter[str] = Counter()
        worst_candidates: list[dict[str, Any]] = []
        candidate_count_with_root_cause = 0

        for candidate in candidates:
            walk_diag = cls._as_dict(candidate.get("walk_forward_profit_diagnostics"))
            board = cls._as_dict(
                candidate.get("walk_forward_validation_candidate_board")
                or walk_diag.get("walk_forward_validation_candidate_board")
            )
            worst = cls._as_dict(
                candidate.get("worst_fold_root_cause")
                or board.get("worst_fold_root_cause")
                or walk_diag.get("worst_fold_root_cause")
            )
            if not worst:
                continue
            candidate_count_with_root_cause += 1
            primary = str(worst.get("primary_root_cause") or "UNKNOWN")
            primary_counts[primary] += 1
            worst_candidates.append(
                {
                    "symbol": candidate.get("symbol"),
                    "config_id": candidate.get("config_id"),
                    "candidate_id": candidate.get("candidate_id"),
                    "fold_index": worst.get("fold_index"),
                    "validation_start": worst.get("validation_start"),
                    "validation_end": worst.get("validation_end"),
                    "test_start": worst.get("test_start"),
                    "test_end": worst.get("test_end"),
                    "gate_type": worst.get("gate_type"),
                    "threshold": cls._float_or_none(worst.get("threshold")),
                    "validation_signal_count": cls._int_or_zero(worst.get("validation_signal_count")),
                    "validation_loss_count": cls._int_or_zero(worst.get("validation_loss_count")),
                    "validation_loss_rate": cls._float_or_none(worst.get("validation_loss_rate")),
                    "outcome_counts": cls._as_dict(worst.get("outcome_counts")),
                    "validation_total_r": cls._float_or_none(
                        worst.get("validation_total_r")
                    ),
                    "primary_root_cause": worst.get("primary_root_cause"),
                    "root_cause_flags": cls._as_list(worst.get("root_cause_flags")),
                    "top_bad_time_slices": cls._as_list(worst.get("time_slice_summary"))[:3],
                    "outcome_summary": cls._as_list(worst.get("outcome_summary"))[:5],
                    "stop_pressure_summary": cls._as_list(worst.get("stop_pressure_summary"))[:3],
                    "mae_pressure_summary": cls._as_list(worst.get("mae_pressure_summary"))[:3],
                    "setup_quality_summary": cls._as_list(worst.get("setup_quality_summary"))[:3],
                    "direction_summary": cls._as_list(worst.get("direction_summary"))[:3],
                    "recommended_validation_repair_profile": candidate.get(
                        "recommended_validation_repair_profile"
                    ),
                    "profit_factor": cls._float_or_none(candidate.get("profit_factor")),
                    "profit_total_r": cls._float_or_none(candidate.get("profit_total_r")),
                    "walk_forward_profit_factor": cls._float_or_none(
                        candidate.get("walk_forward_profit_factor")
                    ),
                    "walk_forward_total_r": cls._float_or_none(
                        candidate.get("walk_forward_total_r")
                    ),
                }
            )

        worst_candidates.sort(
            key=lambda item: (
                cls._float_or_none(item.get("validation_total_r"))
                if cls._float_or_none(item.get("validation_total_r")) is not None
                else 999999.0,
                str(item.get("symbol") or ""),
                str(item.get("config_id") or ""),
            )
        )
        recommendations = ["inspect_worst_fold_root_cause_before_more_threshold_relaxation"]
        if primary_counts.get("large_negative_validation_total_r", 0):
            recommendations.append("do_not_fix_large_negative_fold_by_threshold_only")
        if primary_counts.get("losses_concentrated_in_regime_bucket", 0):
            recommendations.append("consider_regime_time_slice_repair_stage")
        return {
            "diagnostic_name": "walk_forward_fold_root_cause_board",
            "diagnostic_version": "ml38.10.26.3",
            "candidate_count_with_root_cause": candidate_count_with_root_cause,
            "primary_root_cause_counts": dict(primary_counts),
            "worst_candidates": worst_candidates[:10],
            "recommendations": list(dict.fromkeys(recommendations)),
        }

    @classmethod
    def _fold_repair_target_selection(
        cls,
        candidates: list[dict[str, Any]],
        *,
        target_fold_index: int,
    ) -> dict[str, Any]:
        targets: list[dict[str, Any]] = []
        profile_counts: Counter[str] = Counter()
        root_counts: Counter[str] = Counter()
        bad_time_slice_counts: Counter[str] = Counter()
        outcome_counts: Counter[str] = Counter()

        for candidate in candidates:
            config_id = str(candidate.get("config_id") or "")
            side_profile = str(candidate.get("directional_side_filter_profile") or "")
            if not any(token in config_id for token in ("lv28", "lv29", "lv30")):
                continue
            if side_profile not in {"long_only_research", "suppress_short_research"}:
                continue

            walk_diag = cls._as_dict(candidate.get("walk_forward_profit_diagnostics"))
            board = cls._as_dict(
                candidate.get("walk_forward_validation_candidate_board")
                or walk_diag.get("walk_forward_validation_candidate_board")
            )
            worst = cls._as_dict(
                candidate.get("worst_fold_root_cause")
                or board.get("worst_fold_root_cause")
                or walk_diag.get("worst_fold_root_cause")
            )
            if not worst:
                continue
            if int(worst.get("fold_index") or -1) != int(target_fold_index):
                continue

            primary = str(worst.get("primary_root_cause") or "UNKNOWN")
            profile_counts[side_profile] += 1
            root_counts[primary] += 1
            for item in cls._as_list(worst.get("time_slice_summary"))[:3]:
                if isinstance(item, dict):
                    time_slice = str(item.get("time_slice") or "UNKNOWN")
                    bad_time_slice_counts[time_slice] += 1
            for key, value in cls._as_dict(worst.get("outcome_counts")).items():
                outcome_counts[str(key)] += int(value or 0)

            repair_actions: list[str] = []
            flags = {str(item) for item in cls._as_list(worst.get("root_cause_flags"))}
            if "large_negative_validation_total_r" in flags:
                repair_actions.append("do_not_relax_threshold_only")
            if "losses_concentrated_in_time_slice" in flags:
                repair_actions.append("time_slice_blackout_or_event_cluster_probe")
            if "stop_or_mitigation_loss_dominates" in flags:
                repair_actions.append("exit_mitigation_or_stop_loss_repair_probe")
            if "losses_concentrated_in_regime_bucket" in flags:
                repair_actions.append("regime_aware_filter_probe")
            if "losses_concentrated_in_entry_path_bucket" in flags:
                repair_actions.append("entry_path_bucket_exclusion_probe")
            if not repair_actions:
                repair_actions.append("inspect_fold_manually_before_new_grid")

            targets.append(
                {
                    "symbol": candidate.get("symbol"),
                    "config_id": config_id,
                    "candidate_status": candidate.get("candidate_status"),
                    "side_profile": side_profile,
                    "allowed_signal_directions": cls._as_list(candidate.get("allowed_signal_directions")),
                    "profit_factor": cls._float_or_none(candidate.get("profit_factor")),
                    "profit_total_r": cls._float_or_none(candidate.get("profit_total_r")),
                    "walk_forward_profit_factor": cls._float_or_none(candidate.get("walk_forward_profit_factor")),
                    "walk_forward_total_r": cls._float_or_none(
                        candidate.get("walk_forward_total_r", candidate.get("walk_forward_global_total_r"))
                    ),
                    "fold_index": worst.get("fold_index"),
                    "validation_start": worst.get("validation_start"),
                    "validation_end": worst.get("validation_end"),
                    "test_start": worst.get("test_start"),
                    "test_end": worst.get("test_end"),
                    "validation_total_r": cls._float_or_none(worst.get("validation_total_r")),
                    "validation_signal_count": cls._int_or_zero(worst.get("validation_signal_count")),
                    "validation_loss_count": cls._int_or_zero(worst.get("validation_loss_count")),
                    "validation_loss_rate": cls._float_or_none(worst.get("validation_loss_rate")),
                    "primary_root_cause": primary,
                    "root_cause_flags": cls._as_list(worst.get("root_cause_flags")),
                    "outcome_counts": cls._as_dict(worst.get("outcome_counts")),
                    "top_bad_time_slices": cls._as_list(worst.get("time_slice_summary"))[:3],
                    "outcome_summary": cls._as_list(worst.get("outcome_summary"))[:5],
                    "stop_pressure_summary": cls._as_list(worst.get("stop_pressure_summary"))[:3],
                    "mae_pressure_summary": cls._as_list(worst.get("mae_pressure_summary"))[:3],
                    "setup_quality_summary": cls._as_list(worst.get("setup_quality_summary"))[:3],
                    "recommended_repair_actions": repair_actions,
                }
            )

        targets.sort(
            key=lambda item: (
                cls._float_or_none(item.get("validation_total_r"))
                if cls._float_or_none(item.get("validation_total_r")) is not None
                else 999999.0,
                str(item.get("symbol") or ""),
                str(item.get("config_id") or ""),
            )
        )

        recommended_next_stage = "no_fold_repair_target_found"
        if targets:
            recommended_next_stage = "fold_1_time_slice_exit_mitigation_repair_probe"

        warnings: list[str] = []
        recommendations: list[str] = []
        if targets:
            warnings.append("research_only_fold_1_repair_targets_present")
            recommendations.append("do_not_accept_side_only_candidate_before_fold_1_repair")
            recommendations.append("do_not_use_threshold_relaxation_only_for_large_negative_total_r")
            recommendations.append("test_time_slice_exit_mitigation_or_regime_filter_next")

        return {
            "diagnostic_name": "fold_1_repair_target_selection",
            "diagnostic_version": "ml38.10.26.3",
            "target_fold_index": int(target_fold_index),
            "candidate_count": len(candidates),
            "selected_target_count": len(targets),
            "side_profile_counts": dict(profile_counts),
            "primary_root_cause_counts": dict(root_counts),
            "bad_time_slice_counts": dict(bad_time_slice_counts),
            "outcome_counts": dict(outcome_counts),
            "selected_targets": targets[:10],
            "recommended_next_stage": recommended_next_stage,
            "warnings": warnings,
            "recommendations": list(dict.fromkeys(recommendations)),
        }

    @staticmethod
    def _top_failed_gate(gate_failure_counts: dict[str, int]) -> str | None:
        if not gate_failure_counts:
            return None
        return min(gate_failure_counts.items(), key=lambda item: (-item[1], item[0]))[0]

    @staticmethod
    def _best_result(symbol_results: list[dict[str, Any]]) -> dict[str, Any] | None:
        scored = [
            item
            for item in symbol_results
            if item["best_candidate_score"] is not None
            and str(item.get("candidate_status") or "").upper() != "FAILED"
        ]

        if not scored:
            return None

        return max(scored, key=lambda item: float(item["best_candidate_score"]))

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        return None if value is None else float(value)

    @staticmethod
    def _int_or_zero(value: Any) -> int:
        return int(value or 0)

    @staticmethod
    def _recommendations(
        *,
        any_accepted_candidate: bool,
        collapse_failed_count: int,
        walk_forward_failed_count: int,
        profit_aware_failed_count: int,
        symbol_count: int,
        symbols_missing_real_diagnostics: list[str],
        symbols_missing_candle_ta_context: list[str],
        regime_specific_training_applied_any: bool,
    ) -> list[str]:
        recommendations: list[str] = []
        if not any_accepted_candidate:
            recommendations.append("Do not activate model; no accepted candidates were produced.")
        if collapse_failed_count == symbol_count:
            recommendations.append("ML36 should focus on collapse/threshold/calibration/label distribution.")
        if walk_forward_failed_count == symbol_count:
            recommendations.append("ML36 should improve walk-forward stability before more grid expansion.")
        if profit_aware_failed_count > 0:
            recommendations.append("Review profit-aware gate thresholds before any broader multi-symbol expansion.")
        if symbols_missing_real_diagnostics:
            recommendations.append("Fix real diagnostics/regime attachment for non-BTC symbols.")
        if symbols_missing_candle_ta_context:
            recommendations.append("Ensure fv3 candle/TA context features are attached for every symbol before comparing quality.")
        if not regime_specific_training_applied_any:
            recommendations.append("Wire real regime-specific label builder into training pipeline.")
        recommendations.append("Keep traders-core, live trading, orders, and auto activation disabled.")
        return list(dict.fromkeys(recommendations))
