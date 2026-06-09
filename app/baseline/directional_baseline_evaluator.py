from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from app.baseline.baseline_models import BaselineModels
from app.config.settings import PROJECT_ROOT
from app.evaluation.profit_aware_evaluator_v2 import ProfitAwareEvaluatorV2
from app.validation.walk_forward_splitter import WalkForwardConfig, WalkForwardSplitter


class DirectionalBaselineEvaluator:
    def __init__(
        self,
        reports_dir: Path | None = None,
        walk_forward_splitter: WalkForwardSplitter | None = None,
        profit_evaluator_v2: ProfitAwareEvaluatorV2 | None = None,
    ) -> None:
        self._reports_dir = reports_dir or (PROJECT_ROOT / "reports")
        self._reports_dir.mkdir(parents=True, exist_ok=True)
        self._walk_forward_splitter = walk_forward_splitter or WalkForwardSplitter()
        self._profit_evaluator_v2 = profit_evaluator_v2 or ProfitAwareEvaluatorV2(reports_dir=self._reports_dir)

    def evaluate(
        self,
        symbol: str,
        interval: str,
        feature_version: str,
        label_version: str,
        dataset_rows: list[Any],
        config: WalkForwardConfig,
        take_profit_atr: float,
        stop_loss_atr: float,
        fee_r: float,
        slippage_r: float,
        same_candle_policy: str,
        prediction_row_builder: Callable[[list[Any], list[str]], list[dict[str, Any]]],
        require_both_directions: bool = True,
    ) -> dict[str, Any]:
        plan = self._walk_forward_splitter.build_plan(dataset_rows, config)
        baseline_folds: dict[str, list[dict[str, Any]]] = {name: [] for name in self._baseline_names()}

        for fold in plan:
            split_rows = self._walk_forward_splitter.apply_fold(dataset_rows, fold)
            for baseline_name in baseline_folds:
                labels = self._predicted_labels_for_baseline(baseline_name, split_rows["train"], split_rows["test"], fold["fold_index"])
                predictions = prediction_row_builder(split_rows["test"], labels)
                evaluation = self._profit_evaluator_v2.evaluate_single_gate(
                    predictions=predictions,
                    gate_type="directional_edge",
                    threshold=0.0,
                    take_profit_atr=take_profit_atr,
                    stop_loss_atr=stop_loss_atr,
                    fee_r=fee_r,
                    slippage_r=slippage_r,
                    same_candle_policy=same_candle_policy,
                )
                baseline_folds[baseline_name].append(
                    {
                        "fold_index": fold["fold_index"],
                        "test_start": fold["test_start"],
                        "test_end": fold["test_end"],
                        "test_result": evaluation["summary"],
                        "_outcomes": evaluation["outcomes"],
                    }
                )

        baseline_results = {
            name: self._summarize_baseline(name, fold_reports, require_both_directions)
            for name, fold_reports in baseline_folds.items()
        }
        best_baseline_name = self._best_baseline_name(baseline_results)
        report = {
            "symbol": symbol,
            "interval": interval,
            "feature_version": feature_version,
            "label_version": label_version,
            "fold_count": len(plan),
            "require_both_directions": require_both_directions,
            "baselines": baseline_results,
            "best_baseline": {
                "name": best_baseline_name,
                "summary": baseline_results[best_baseline_name]["summary"] if best_baseline_name is not None else None,
            },
        }
        output_path = self._reports_dir / f"directional_baselines_{label_version}.json"
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["report_path"] = str(output_path)
        return report

    @staticmethod
    def _baseline_names() -> list[str]:
        return [
            "always_long",
            "always_short",
            "always_flat",
            "random_long_short",
            "label_majority_per_train_fold",
            "previous_candle_direction",
            "ema_9_21_direction",
        ]

    def _predicted_labels_for_baseline(
        self,
        baseline_name: str,
        train_rows: list[Any],
        test_rows: list[Any],
        fold_index: int,
    ) -> list[str]:
        if baseline_name == "always_long":
            return ["UP"] * len(test_rows)
        if baseline_name == "always_short":
            return ["DOWN"] * len(test_rows)
        if baseline_name == "always_flat":
            return ["FLAT"] * len(test_rows)
        if baseline_name == "random_long_short":
            rng = random.Random(42 + fold_index)
            return ["UP" if rng.random() >= 0.5 else "DOWN" for _ in test_rows]
        if baseline_name == "label_majority_per_train_fold":
            label, predictions = BaselineModels.majority_class(train_rows, test_rows)
            return [label] * len(predictions)
        if baseline_name == "previous_candle_direction":
            return [
                "UP" if float(row.features_json["return_1"]) > 0 else ("DOWN" if float(row.features_json["return_1"]) < 0 else "FLAT")
                for row in test_rows
            ]
        if baseline_name == "ema_9_21_direction":
            return [
                "UP" if float(row.features_json["ema_9"]) > float(row.features_json["ema_21"])
                else ("DOWN" if float(row.features_json["ema_9"]) < float(row.features_json["ema_21"]) else "FLAT")
                for row in test_rows
            ]
        raise ValueError(f"Unsupported baseline: {baseline_name}")

    def _summarize_baseline(self, baseline_name: str, fold_reports: list[dict[str, Any]], require_both_directions: bool) -> dict[str, Any]:
        global_profit = 0.0
        global_loss = 0.0
        global_total_r = 0.0
        long_total_count = 0
        short_total_count = 0
        total_resolved = 0
        total_wins = 0
        net_values: list[float] = []
        public_folds: list[dict[str, Any]] = []

        for fold in fold_reports:
            summary = fold["test_result"]
            global_profit += float(summary.get("gross_profit_r", 0.0))
            global_loss += float(summary.get("gross_loss_r", 0.0))
            global_total_r += float(summary.get("total_r", 0.0))
            long_total_count += int(summary.get("long_count", 0))
            short_total_count += int(summary.get("short_count", 0))
            total_wins += int(summary.get("win_count", 0))
            total_resolved += (
                int(summary.get("win_count", 0))
                + int(summary.get("loss_count", 0))
                + int(summary.get("neither_count", 0))
            )
            net_values.extend(float(item["net_r"]) for item in fold["_outcomes"] if item["result"] != "AMBIGUOUS")
            public_folds.append({key: value for key, value in fold.items() if not key.startswith("_")})

        global_profit_factor = None
        if total_resolved > 0:
            if global_loss > 0:
                global_profit_factor = global_profit / global_loss
            elif global_profit > 0:
                global_profit_factor = float("inf")
            else:
                global_profit_factor = 0.0

        warnings: list[str] = []
        if require_both_directions and long_total_count == 0:
            warnings.append("no_long_signals")
        if require_both_directions and short_total_count == 0:
            warnings.append("no_short_signals")

        summary = {
            "baseline_name": baseline_name,
            "fold_count": len(fold_reports),
            "global_gross_profit_r": global_profit,
            "global_gross_loss_r": global_loss,
            "global_profit_factor": global_profit_factor,
            "global_total_r": global_total_r,
            "global_expectancy_r": (global_total_r / total_resolved) if total_resolved else None,
            "global_win_rate": (total_wins / total_resolved) if total_resolved else None,
            "global_max_drawdown_r": ProfitAwareEvaluatorV2._max_drawdown(net_values),
            "total_signal_count": total_resolved,
            "long_total_count": long_total_count,
            "short_total_count": short_total_count,
            "warnings": warnings,
        }
        return {"folds": public_folds, "summary": summary}

    @staticmethod
    def _best_baseline_name(baseline_results: dict[str, dict[str, Any]]) -> str | None:
        if not baseline_results:
            return None
        return max(
            baseline_results,
            key=lambda name: (
                float(baseline_results[name]["summary"].get("global_total_r", 0.0)),
                float(
                    baseline_results[name]["summary"].get("global_profit_factor", 0.0)
                    if baseline_results[name]["summary"].get("global_profit_factor") is not None
                    else 0.0
                ),
                int(baseline_results[name]["summary"].get("total_signal_count", 0)),
            ),
        )
