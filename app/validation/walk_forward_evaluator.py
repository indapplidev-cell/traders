from __future__ import annotations

import json
from pathlib import Path
from statistics import median
from typing import Any

from app.config.settings import PROJECT_ROOT
from app.diagnostics.direction_bias_diagnostics import DirectionBiasDiagnostics
from app.diagnostics.walk_forward_fold_root_cause_diagnostics import (
    WalkForwardFoldRootCauseDiagnostics,
)
from app.evaluation.profit_aware_evaluator_v2 import ProfitAwareEvaluatorV2
from app.validation.gate_selector import GateSelector
from app.validation.walk_forward_splitter import WalkForwardConfig, WalkForwardSplitter


class WalkForwardEvaluator:
    def __init__(
        self,
        reports_dir: Path | None = None,
        walk_forward_splitter: WalkForwardSplitter | None = None,
        gate_selector: GateSelector | None = None,
        profit_evaluator_v2: ProfitAwareEvaluatorV2 | None = None,
        direction_bias_diagnostics: DirectionBiasDiagnostics | None = None,
        fold_root_cause_diagnostics: WalkForwardFoldRootCauseDiagnostics | None = None,
    ) -> None:
        self._reports_dir = reports_dir or (PROJECT_ROOT / "reports")
        self._reports_dir.mkdir(parents=True, exist_ok=True)
        self._walk_forward_splitter = walk_forward_splitter or WalkForwardSplitter()
        self._gate_selector = gate_selector or GateSelector()
        self._profit_evaluator_v2 = profit_evaluator_v2 or ProfitAwareEvaluatorV2(reports_dir=self._reports_dir)
        self._direction_bias_diagnostics = direction_bias_diagnostics or DirectionBiasDiagnostics()
        self._fold_root_cause_diagnostics = (
            fold_root_cause_diagnostics or WalkForwardFoldRootCauseDiagnostics()
        )

    def build_plan(self, dataset_rows: list[Any], config: WalkForwardConfig) -> dict[str, Any]:
        folds = self._walk_forward_splitter.build_plan(dataset_rows, config)
        return {"mode": config.mode, "folds": folds}

    def evaluate(
        self,
        model_version: str,
        label_version: str,
        dataset_rows: list[Any],
        prediction_builder,
        config: WalkForwardConfig,
        take_profit_atr: float,
        stop_loss_atr: float,
        fee_r: float,
        slippage_r: float,
        same_candle_policy: str,
        exit_policy_profile: str | None = None,
        exit_timeout_bars: int | None = None,
        exit_mitigation_loss_r: float | None = None,
        exit_neutral_abs_r: float | None = None,
        directional_side_filter_profile: str | None = None,
        allowed_signal_directions: tuple[str, ...] | list[str] | None = None,
        research_only_fold_repair_probe_enabled: bool = False,
        fold_repair_probe_profile: str | None = None,
        fold_repair_target_dates: tuple[str, ...] | list[str] | None = None,
        fold_repair_time_slice_blackout_enabled: bool = False,
        fold_repair_blackout_dates: tuple[str, ...] | list[str] | None = None,
        fold_repair_feature_filter_enabled: bool = False,
        fold_repair_feature_filter_profile: str | None = None,
        fold_repair_feature_filter_rules: dict[str, Any] | None = None,
        side_aware_validation_relaxation_enabled: bool = False,
        side_aware_min_validation_signal_count: int | None = None,
        side_aware_min_validation_profit_factor: float | None = None,
        side_aware_min_validation_total_r: float | None = None,
        side_aware_min_validation_expectancy_r: float | None = None,
        side_aware_allow_single_direction_validation: bool = False,
    ) -> dict[str, Any]:
        plan = self._walk_forward_splitter.build_plan(dataset_rows, config)
        fold_reports: list[dict[str, Any]] = []

        for fold in plan:
            split_rows = self._walk_forward_splitter.apply_fold(dataset_rows, fold)
            validation_predictions = prediction_builder(split_rows["validation"])
            validation_profit = self._profit_evaluator_v2.evaluate_predictions(
                predictions=validation_predictions,
                take_profit_atr=take_profit_atr,
                stop_loss_atr=stop_loss_atr,
                fee_r=fee_r,
                slippage_r=slippage_r,
                same_candle_policy=same_candle_policy,
                exit_policy_profile=exit_policy_profile,
                exit_timeout_bars=exit_timeout_bars,
                exit_mitigation_loss_r=exit_mitigation_loss_r,
                exit_neutral_abs_r=exit_neutral_abs_r,
                directional_side_filter_profile=directional_side_filter_profile,
                allowed_signal_directions=allowed_signal_directions,
                research_only_fold_repair_probe_enabled=research_only_fold_repair_probe_enabled,
                fold_repair_probe_profile=fold_repair_probe_profile,
                fold_repair_target_dates=fold_repair_target_dates,
                fold_repair_time_slice_blackout_enabled=fold_repair_time_slice_blackout_enabled,
                fold_repair_blackout_dates=fold_repair_blackout_dates,
                fold_repair_feature_filter_enabled=fold_repair_feature_filter_enabled,
                fold_repair_feature_filter_profile=fold_repair_feature_filter_profile,
                fold_repair_feature_filter_rules=fold_repair_feature_filter_rules,
            )
            selected_gate_payload = self._gate_selector.select(
                validation_profit["gate_results"],
                directional_side_filter_profile=directional_side_filter_profile,
                allowed_signal_directions=allowed_signal_directions,
                side_aware_validation_relaxation_enabled=side_aware_validation_relaxation_enabled,
                side_aware_min_validation_signal_count=side_aware_min_validation_signal_count,
                side_aware_min_validation_profit_factor=side_aware_min_validation_profit_factor,
                side_aware_min_validation_total_r=side_aware_min_validation_total_r,
                side_aware_min_validation_expectancy_r=side_aware_min_validation_expectancy_r,
                side_aware_allow_single_direction_validation=side_aware_allow_single_direction_validation,
            )
            selected_gate = selected_gate_payload["selected_gate"]
            validation_fold_root_cause = None

            if selected_gate is None:
                validation_fold_root_cause = self._build_validation_fold_root_cause(
                    fold=fold,
                    validation_predictions=validation_predictions,
                    selected_gate_payload=selected_gate_payload,
                    take_profit_atr=take_profit_atr,
                    stop_loss_atr=stop_loss_atr,
                    fee_r=fee_r,
                    slippage_r=slippage_r,
                    same_candle_policy=same_candle_policy,
                    exit_policy_profile=exit_policy_profile,
                    exit_timeout_bars=exit_timeout_bars,
                    exit_mitigation_loss_r=exit_mitigation_loss_r,
                    exit_neutral_abs_r=exit_neutral_abs_r,
                    directional_side_filter_profile=directional_side_filter_profile,
                    allowed_signal_directions=allowed_signal_directions,
                    research_only_fold_repair_probe_enabled=research_only_fold_repair_probe_enabled,
                    fold_repair_probe_profile=fold_repair_probe_profile,
                    fold_repair_target_dates=fold_repair_target_dates,
                    fold_repair_time_slice_blackout_enabled=fold_repair_time_slice_blackout_enabled,
                    fold_repair_blackout_dates=fold_repair_blackout_dates,
                    fold_repair_feature_filter_enabled=fold_repair_feature_filter_enabled,
                    fold_repair_feature_filter_profile=fold_repair_feature_filter_profile,
                    fold_repair_feature_filter_rules=fold_repair_feature_filter_rules,
                )

            test_result = None
            bias_report = None
            if selected_gate is not None:
                test_predictions = prediction_builder(split_rows["test"])
                test_result = self._profit_evaluator_v2.evaluate_single_gate(
                    predictions=test_predictions,
                    gate_type=selected_gate["gate_type"],
                    threshold=float(selected_gate["threshold"]),
                    take_profit_atr=take_profit_atr,
                    stop_loss_atr=stop_loss_atr,
                    fee_r=fee_r,
                    slippage_r=slippage_r,
                    same_candle_policy=same_candle_policy,
                    exit_policy_profile=exit_policy_profile,
                    exit_timeout_bars=exit_timeout_bars,
                    exit_mitigation_loss_r=exit_mitigation_loss_r,
                    exit_neutral_abs_r=exit_neutral_abs_r,
                    directional_side_filter_profile=directional_side_filter_profile,
                    allowed_signal_directions=allowed_signal_directions,
                    research_only_fold_repair_probe_enabled=research_only_fold_repair_probe_enabled,
                    fold_repair_probe_profile=fold_repair_probe_profile,
                    fold_repair_target_dates=fold_repair_target_dates,
                    fold_repair_time_slice_blackout_enabled=fold_repair_time_slice_blackout_enabled,
                    fold_repair_blackout_dates=fold_repair_blackout_dates,
                    fold_repair_feature_filter_enabled=fold_repair_feature_filter_enabled,
                    fold_repair_feature_filter_profile=fold_repair_feature_filter_profile,
                    fold_repair_feature_filter_rules=fold_repair_feature_filter_rules,
                )
                bias_report = self._direction_bias_diagnostics.build_report(
                    predictions=test_predictions,
                    signal_rows=test_result["signal_rows"],
                )

            fold_reports.append(
                {
                    **fold,
                    "selected_gate": selected_gate,
                    "gate_reject_reason": selected_gate_payload["reject_reason"],
                    "validation_gate_results": validation_profit["gate_results"],
                    "validation_gate_selection_diagnostics": selected_gate_payload.get("diagnostics", {}),
                    "validation_fold_root_cause": validation_fold_root_cause,
                    "test_result": test_result["summary"] if test_result is not None else None,
                    "direction_bias": bias_report,
                    "_test_outcomes": test_result["outcomes"] if test_result is not None else [],
                }
            )

        summary = self._summarize_folds(fold_reports)
        public_folds = [{key: value for key, value in fold.items() if not key.startswith("_")} for fold in fold_reports]
        report = {
            "model_version": model_version,
            "label_version": label_version,
            "exit_policy_profile": exit_policy_profile or "classic_tp_sl",
            "exit_timeout_bars": exit_timeout_bars,
            "exit_mitigation_loss_r": exit_mitigation_loss_r,
            "exit_neutral_abs_r": exit_neutral_abs_r,
            "directional_side_filter_profile": directional_side_filter_profile,
            "allowed_signal_directions": list(allowed_signal_directions or []),
            "research_only_fold_repair_probe_enabled": research_only_fold_repair_probe_enabled,
            "fold_repair_probe_profile": fold_repair_probe_profile,
            "fold_repair_target_dates": list(fold_repair_target_dates or []),
            "fold_repair_time_slice_blackout_enabled": fold_repair_time_slice_blackout_enabled,
            "fold_repair_blackout_dates": list(fold_repair_blackout_dates or []),
            "fold_repair_feature_filter_enabled": fold_repair_feature_filter_enabled,
            "fold_repair_feature_filter_profile": fold_repair_feature_filter_profile,
            "fold_repair_feature_filter_rules": dict(fold_repair_feature_filter_rules or {}),
            "side_aware_validation_relaxation_enabled": side_aware_validation_relaxation_enabled,
            "side_aware_min_validation_signal_count": side_aware_min_validation_signal_count,
            "side_aware_min_validation_profit_factor": side_aware_min_validation_profit_factor,
            "side_aware_min_validation_total_r": side_aware_min_validation_total_r,
            "side_aware_min_validation_expectancy_r": side_aware_min_validation_expectancy_r,
            "side_aware_allow_single_direction_validation": side_aware_allow_single_direction_validation,
            "folds": public_folds,
            "summary": summary,
        }
        output_path = self._reports_dir / f"walk_forward_eval_{model_version}.json"
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["report_path"] = str(output_path)
        return report

    def write_plan_report(self, symbol: str, interval: str, label_version: str, plan: dict[str, Any]) -> dict[str, Any]:
        output_path = self._reports_dir / f"walk_forward_plan_{symbol.lower()}_{interval}_{label_version}.json"
        output_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
        payload = dict(plan)
        payload["report_path"] = str(output_path)
        return payload

    def _build_validation_fold_root_cause(
        self,
        *,
        fold: dict[str, Any],
        validation_predictions: list[dict[str, Any]],
        selected_gate_payload: dict[str, Any],
        take_profit_atr: float,
        stop_loss_atr: float,
        fee_r: float,
        slippage_r: float,
        same_candle_policy: str,
        exit_policy_profile: str | None,
        exit_timeout_bars: int | None,
        exit_mitigation_loss_r: float | None,
        exit_neutral_abs_r: float | None,
        directional_side_filter_profile: str | None,
        allowed_signal_directions: tuple[str, ...] | list[str] | None,
        research_only_fold_repair_probe_enabled: bool,
        fold_repair_probe_profile: str | None,
        fold_repair_target_dates: tuple[str, ...] | list[str] | None,
        fold_repair_time_slice_blackout_enabled: bool,
        fold_repair_blackout_dates: tuple[str, ...] | list[str] | None,
        fold_repair_feature_filter_enabled: bool,
        fold_repair_feature_filter_profile: str | None,
        fold_repair_feature_filter_rules: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        diagnostics = dict(
            selected_gate_payload.get("diagnostics")
            or selected_gate_payload.get("validation_gate_selection_diagnostics")
            or {}
        )
        gate = (
            diagnostics.get("best_failed_gate_by_distance_to_pass")
            or diagnostics.get("best_failed_gate_by_total_r")
            or diagnostics.get("best_failed_gate_by_profit_factor")
            or diagnostics.get("best_failed_gate_by_signal_count")
        )
        if not isinstance(gate, dict):
            return {
                "diagnostic_name": "walk_forward_fold_total_r_root_cause",
                "diagnostic_version": "ml38.10.26",
                "diagnostic_status": "NO_BEST_FAILED_GATE",
                "fold_index": fold.get("fold_index"),
                "recommendations": ["inspect_gate_selector_diagnostics_payload"],
            }

        gate_type = gate.get("gate_type")
        threshold = gate.get("threshold")
        if gate_type is None or threshold is None:
            return {
                "diagnostic_name": "walk_forward_fold_total_r_root_cause",
                "diagnostic_version": "ml38.10.26",
                "diagnostic_status": "BEST_FAILED_GATE_INCOMPLETE",
                "fold_index": fold.get("fold_index"),
                "gate": gate,
                "recommendations": ["inspect_best_failed_gate_payload"],
            }

        evaluated = self._profit_evaluator_v2.evaluate_single_gate(
            predictions=validation_predictions,
            gate_type=str(gate_type),
            threshold=float(threshold),
            take_profit_atr=take_profit_atr,
            stop_loss_atr=stop_loss_atr,
            fee_r=fee_r,
            slippage_r=slippage_r,
            same_candle_policy=same_candle_policy,
            exit_policy_profile=exit_policy_profile,
            exit_timeout_bars=exit_timeout_bars,
            exit_mitigation_loss_r=exit_mitigation_loss_r,
            exit_neutral_abs_r=exit_neutral_abs_r,
            directional_side_filter_profile=directional_side_filter_profile,
            allowed_signal_directions=allowed_signal_directions,
            research_only_fold_repair_probe_enabled=research_only_fold_repair_probe_enabled,
            fold_repair_probe_profile=fold_repair_probe_profile,
            fold_repair_target_dates=fold_repair_target_dates,
            fold_repair_time_slice_blackout_enabled=fold_repair_time_slice_blackout_enabled,
            fold_repair_blackout_dates=fold_repair_blackout_dates,
            fold_repair_feature_filter_enabled=fold_repair_feature_filter_enabled,
            fold_repair_feature_filter_profile=fold_repair_feature_filter_profile,
            fold_repair_feature_filter_rules=fold_repair_feature_filter_rules,
        )
        return self._fold_root_cause_diagnostics.analyze(
            fold=fold,
            gate=gate,
            signal_rows=list(evaluated.get("signal_rows") or []),
            outcomes=list(evaluated.get("outcomes") or []),
        )

    @staticmethod
    def _summarize_folds(folds: list[dict[str, Any]]) -> dict[str, Any]:
        folds_with_gate = [fold for fold in folds if fold.get("selected_gate") is not None]
        profitable_folds = [
            fold
            for fold in folds_with_gate
            if fold.get("test_result") is not None and float(fold["test_result"].get("total_r", 0.0)) > 0.0
        ]
        test_results = [fold["test_result"] for fold in folds_with_gate if fold.get("test_result") is not None]
        profit_factors = [row["profit_factor"] for row in test_results if row.get("profit_factor") is not None]
        expectancies = [row["expectancy_r"] for row in test_results if row.get("expectancy_r") is not None]
        stable_gate_types: dict[str, int] = {}
        long_total_count = 0
        short_total_count = 0
        bias_warnings: list[str] = []
        dominant_class_ratio_max = 0.0
        global_gross_profit_r = 0.0
        global_gross_loss_r = 0.0
        global_win_count = 0
        global_resolved_signal_count = 0
        global_net_values: list[float] = []
        validation_gate_failure_reason_counts: dict[str, int] = {}
        validation_gate_passed_probe_count = 0
        validation_gate_probe_count = 0
        side_aware_relaxed_fold_count = 0
        for fold in folds_with_gate:
            gate_type = fold["selected_gate"]["gate_type"]
            stable_gate_types[gate_type] = stable_gate_types.get(gate_type, 0) + 1
            if fold.get("test_result") is not None:
                long_total_count += int(fold["test_result"].get("long_count", 0))
                short_total_count += int(fold["test_result"].get("short_count", 0))
                global_gross_profit_r += float(fold["test_result"].get("gross_profit_r", 0.0))
                global_gross_loss_r += float(fold["test_result"].get("gross_loss_r", 0.0))
                global_win_count += int(fold["test_result"].get("win_count", 0))
                global_resolved_signal_count += int(fold["test_result"].get("resolved_signal_count", 0))
                global_net_values.extend(
                    float(item["net_r"]) for item in fold.get("_test_outcomes", []) if item["result"] != "AMBIGUOUS"
                )
            if fold.get("direction_bias"):
                bias_warnings.extend(fold["direction_bias"].get("warnings", []))
                dominant_class_ratio_max = max(
                    dominant_class_ratio_max,
                    float(fold["direction_bias"].get("predicted_up_ratio", 0.0)),
                    float(fold["direction_bias"].get("predicted_down_ratio", 0.0)),
                    float(fold["direction_bias"].get("predicted_flat_ratio", 0.0)),
                )
        for fold in folds:
            diagnostics = fold.get("validation_gate_selection_diagnostics") or {}
            if diagnostics.get("side_aware_validation_relaxation_enabled"):
                side_aware_relaxed_fold_count += 1
            validation_gate_probe_count += int(diagnostics.get("gate_probe_count", 0) or 0)
            validation_gate_passed_probe_count += int(diagnostics.get("passed_gate_count", 0) or 0)
            for reason, count in dict(diagnostics.get("failure_reason_counts") or {}).items():
                validation_gate_failure_reason_counts[str(reason)] = (
                    validation_gate_failure_reason_counts.get(str(reason), 0) + int(count or 0)
                )
        validation_root_causes = [
            dict(fold.get("validation_fold_root_cause") or {})
            for fold in folds
            if fold.get("validation_fold_root_cause") is not None
        ]
        validation_root_cause_summary = WalkForwardFoldRootCauseDiagnostics().summarize_many(
            validation_root_causes
        )
        total_test_signal_count = sum(int(row.get("signal_count", 0)) for row in test_results)
        total_test_r = sum(float(row.get("total_r", 0.0)) for row in test_results)
        global_profit_factor = None
        if global_resolved_signal_count > 0:
            if global_gross_loss_r > 0:
                global_profit_factor = global_gross_profit_r / global_gross_loss_r
            elif global_gross_profit_r > 0:
                global_profit_factor = float("inf")
            else:
                global_profit_factor = 0.0
        return {
            "fold_count": len(folds),
            "folds_with_selected_gate": len(folds_with_gate),
            "validation_gate_probe_count": validation_gate_probe_count,
            "validation_gate_passed_probe_count": validation_gate_passed_probe_count,
            "validation_gate_failure_reason_counts": validation_gate_failure_reason_counts,
            "validation_fold_root_cause_count": len(validation_root_causes),
            "validation_fold_root_cause_summary": validation_root_cause_summary,
            "side_aware_relaxed_fold_count": side_aware_relaxed_fold_count,
            "folds_profitable_on_test": len(profitable_folds),
            "total_test_signal_count": total_test_signal_count,
            "total_test_r": total_test_r,
            "avg_test_profit_factor": (sum(profit_factors) / len(profit_factors)) if profit_factors else None,
            "median_test_profit_factor": median(profit_factors) if profit_factors else None,
            "avg_test_expectancy_r": (sum(expectancies) / len(expectancies)) if expectancies else None,
            "profitable_fold_ratio": (len(profitable_folds) / len(folds_with_gate)) if folds_with_gate else 0.0,
            "stable_gate_types": stable_gate_types,
            "long_total_count": long_total_count,
            "short_total_count": short_total_count,
            "long_short_balance_warning": (long_total_count == 0 or short_total_count == 0),
            "bias_warnings": sorted(set(bias_warnings)),
            "dominant_class_ratio_max": dominant_class_ratio_max,
            "global_gross_profit_r": global_gross_profit_r,
            "global_gross_loss_r": global_gross_loss_r,
            "global_profit_factor": global_profit_factor,
            "global_total_r": total_test_r,
            "global_expectancy_r": (total_test_r / global_resolved_signal_count) if global_resolved_signal_count else None,
            "global_win_rate": (global_win_count / global_resolved_signal_count) if global_resolved_signal_count else None,
            "global_max_drawdown_r": ProfitAwareEvaluatorV2._max_drawdown(global_net_values),
        }
