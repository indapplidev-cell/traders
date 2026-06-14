from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


MULTI_SYMBOL_FEATURE_REGIME_ANALYZER_NAME = "multi_symbol_feature_regime_analyzer"
MULTI_SYMBOL_FEATURE_REGIME_ANALYZER_VERSION = "ml35"


class MultiSymbolFeatureRegimeAnalyzer:
    """Aggregate multiple feature/regime experiment summaries into one report."""

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
            "best_config_by_symbol": {
                item["symbol"]: item["best_candidate_config_id"] for item in symbol_results
            },
            "best_global_config": None if best_result is None else best_result["best_candidate_config_id"],
            "configs_ranked": configs_ranked,
            "symbol_results": symbol_results,
            "gate_failure_counts": gate_failure_counts,
            "feature_version_summary": {
                "all_feature_version_fv2": all_feature_version_fv2,
                "feature_versions_by_symbol": {
                    item["symbol"]: item["feature_version_used"] for item in symbol_results
                },
                "all_feature_version_fv3_candle_ta_context": all_feature_version_fv3_candle_ta_context,
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
                raise ValueError(f"No feature/regime experiment summaries found for symbol: {symbol}")
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

    @staticmethod
    def _best_candidate(summary: dict[str, Any]) -> dict[str, Any]:
        candidate_results = [
            MultiSymbolFeatureRegimeAnalyzer._as_dict(item)
            for item in MultiSymbolFeatureRegimeAnalyzer._as_list(summary.get("candidate_results"))
            if isinstance(item, dict)
        ]
        best_config_id = summary.get("best_candidate_config_id")
        if best_config_id is not None:
            for candidate in candidate_results:
                if candidate.get("config_id") == best_config_id:
                    return candidate
        scored = [item for item in candidate_results if item.get("score") is not None]
        if scored:
            return max(scored, key=lambda item: float(item["score"]))
        return candidate_results[0] if candidate_results else {}

    @classmethod
    def _symbol_result(cls, summary: dict[str, Any]) -> dict[str, Any]:
        best_candidate = cls._best_candidate(summary)
        summary_warnings = [str(item) for item in cls._as_list(summary.get("warnings"))]
        candidate_warnings = [str(item) for item in cls._as_list(best_candidate.get("warnings"))]
        summary_regime_status = cls._as_dict(summary.get("regime_label_builder_status"))
        return {
            "symbol": str(summary.get("symbol")),
            "experiment_id": summary.get("experiment_id"),
            "experiment_status": summary.get("experiment_status"),
            "candidate_count": int(summary.get("candidate_count", 0) or 0),
            "evaluated_candidate_count": int(summary.get("evaluated_candidate_count", 0) or 0),
            "failed_candidate_count": int(summary.get("failed_candidate_count", 0) or 0),
            "accepted_candidate_count": int(summary.get("accepted_candidate_count", 0) or 0),
            "rejected_candidate_count": int(summary.get("rejected_candidate_count", 0) or 0),
            "best_candidate_config_id": summary.get("best_candidate_config_id"),
            "best_candidate_score": cls._float_or_none(summary.get("best_candidate_score")),
            "candidate_status": best_candidate.get("candidate_status"),
            "feature_version_used": summary.get("feature_version_used"),
            "candle_ta_context_features_attached": bool(summary.get("candle_ta_context_features_attached", False)),
            "candle_ta_context_feature_count": int(summary.get("candle_ta_context_feature_count", 0) or 0),
            "candle_ta_context_missing_reason": summary.get("candle_ta_context_missing_reason"),
            "real_feature_diagnostics_used": bool(summary.get("real_feature_diagnostics_used", False)),
            "real_feature_diagnostics_row_count": int(summary.get("real_feature_diagnostics_row_count", 0) or 0),
            "real_feature_diagnostics_missing_reason": summary.get("real_feature_diagnostics_missing_reason"),
            "effective_gap_count_for_training": int(summary.get("effective_gap_count_for_training", 0) or 0),
            "gap_severity_for_training": str(summary.get("gap_severity_for_training") or "UNKNOWN"),
            "gap_training_safe": bool(summary.get("gap_training_safe", False)),
            "baseline_edge": cls._float_or_none(best_candidate.get("accuracy_edge")),
            "model_accuracy": cls._float_or_none(best_candidate.get("model_accuracy")),
            "baseline_accuracy": cls._float_or_none(best_candidate.get("baseline_accuracy")),
            "collapse_detected": bool(best_candidate.get("collapse_detected", False)),
            "collapse_type": best_candidate.get("collapse_type"),
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
            "failed_gates": [str(item) for item in cls._as_list(best_candidate.get("failed_gates"))],
            "passed_gates": [str(item) for item in cls._as_list(best_candidate.get("passed_gates"))],
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
            "reasons_why_best_still_rejected": [
                str(item) for item in cls._as_list(summary.get("reasons_why_best_still_rejected"))
            ],
            "configs_ranked": [
                dict(item) for item in cls._as_list(summary.get("configs_ranked") or summary.get("ranking"))
            ],
        }

    @staticmethod
    def _configs_ranked(symbol_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for symbol_result in symbol_results:
            for row in symbol_result.get("configs_ranked", []):
                payload = dict(row)
                payload["symbol"] = symbol_result["symbol"]
                rows.append(payload)
        rows.sort(
            key=lambda item: (
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

    @staticmethod
    def _top_failed_gate(gate_failure_counts: dict[str, int]) -> str | None:
        if not gate_failure_counts:
            return None
        return min(gate_failure_counts.items(), key=lambda item: (-item[1], item[0]))[0]

    @staticmethod
    def _best_result(symbol_results: list[dict[str, Any]]) -> dict[str, Any] | None:
        scored = [item for item in symbol_results if item["best_candidate_score"] is not None]
        if not scored:
            return None
        return max(scored, key=lambda item: float(item["best_candidate_score"]))

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        return None if value is None else float(value)

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
