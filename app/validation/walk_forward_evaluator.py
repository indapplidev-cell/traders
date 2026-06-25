from __future__ import annotations

import json
from pathlib import Path
from statistics import median
from typing import Any

from app.config.settings import PROJECT_ROOT
from app.diagnostics.direction_bias_diagnostics import DirectionBiasDiagnostics
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
    ) -> None:
        self._reports_dir = reports_dir or (PROJECT_ROOT / "reports")
        self._reports_dir.mkdir(parents=True, exist_ok=True)
        self._walk_forward_splitter = walk_forward_splitter or WalkForwardSplitter()
        self._gate_selector = gate_selector or GateSelector()
        self._profit_evaluator_v2 = profit_evaluator_v2 or ProfitAwareEvaluatorV2(reports_dir=self._reports_dir)
        self._direction_bias_diagnostics = direction_bias_diagnostics or DirectionBiasDiagnostics()

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
            )
            selected_gate_payload = self._gate_selector.select(validation_profit["gate_results"])
            selected_gate = selected_gate_payload["selected_gate"]

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
