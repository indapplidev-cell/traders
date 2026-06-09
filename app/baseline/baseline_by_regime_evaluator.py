from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config.settings import PROJECT_ROOT
from app.evaluation.profit_aware_evaluator_v2 import ProfitAwareEvaluatorV2
from app.validation.walk_forward_splitter import WalkForwardConfig, WalkForwardSplitter


class BaselineByRegimeEvaluator:
    BASELINE_NAMES = [
        "ema_9_21_direction",
        "ema_21_50_direction",
        "ema_stack_direction",
        "close_vs_ema_200_direction",
        "previous_candle_direction",
        "always_long",
        "always_short",
    ]
    SEGMENT_KEYS = [
        "regime_trend_up",
        "regime_trend_down",
        "regime_range",
        "regime_high_volatility",
        "regime_low_volatility",
        "regime_volatility_expanding",
        "regime_volatility_contracting",
        "ema_stack_bullish",
        "ema_stack_bearish",
        "close_above_ema_200",
        "close_below_ema_200",
    ]

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
        prediction_row_builder,
    ) -> dict[str, Any]:
        plan = self._walk_forward_splitter.build_plan(dataset_rows, config)
        segment_results: dict[str, dict[str, list[dict[str, Any]]]] = {
            segment: {baseline: [] for baseline in self.BASELINE_NAMES}
            for segment in self.SEGMENT_KEYS
        }
        overall_results: dict[str, list[dict[str, Any]]] = {baseline: [] for baseline in self.BASELINE_NAMES}

        for fold in plan:
            split_rows = self._walk_forward_splitter.apply_fold(dataset_rows, fold)
            for baseline_name in self.BASELINE_NAMES:
                predictions = prediction_row_builder(split_rows["test"], self._predicted_labels_for_baseline(baseline_name, split_rows["test"]))
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
                overall_results[baseline_name].append({"fold_index": fold["fold_index"], "test_result": evaluation["summary"]})

                for segment in self.SEGMENT_KEYS:
                    segment_rows = [row for row in split_rows["test"] if self._match_segment(row, segment)]
                    segment_predictions = prediction_row_builder(segment_rows, self._predicted_labels_for_baseline(baseline_name, segment_rows))
                    segment_eval = self._profit_evaluator_v2.evaluate_single_gate(
                        predictions=segment_predictions,
                        gate_type="directional_edge",
                        threshold=0.0,
                        take_profit_atr=take_profit_atr,
                        stop_loss_atr=stop_loss_atr,
                        fee_r=fee_r,
                        slippage_r=slippage_r,
                        same_candle_policy=same_candle_policy,
                    )
                    segment_results[segment][baseline_name].append(
                        {"fold_index": fold["fold_index"], "test_result": segment_eval["summary"]}
                    )

        overall_summary = {name: self._summarize_folds(name, fold_reports) for name, fold_reports in overall_results.items()}
        by_regime_summary = {
            segment: {name: self._summarize_folds(name, fold_reports) for name, fold_reports in baselines.items()}
            for segment, baselines in segment_results.items()
        }
        best_baseline_overall = self._best_baseline(overall_summary)
        best_baseline_by_regime = {
            segment: self._best_baseline(rows)
            for segment, rows in by_regime_summary.items()
        }
        ema_by_regime = {segment: rows["ema_9_21_direction"]["summary"] for segment, rows in by_regime_summary.items()}
        report = {
            "symbol": symbol,
            "interval": interval,
            "feature_version": feature_version,
            "label_version": label_version,
            "best_baseline_overall": best_baseline_overall,
            "best_baseline_by_regime": best_baseline_by_regime,
            "baselines_overall": overall_summary,
            "baselines_by_regime": by_regime_summary,
            "regimes_where_ema_9_21_works": [
                segment for segment, summary in ema_by_regime.items()
                if float(summary.get("total_r", 0.0)) > 0.0 and float(summary.get("global_profit_factor", 0.0) or 0.0) > 1.0
            ],
            "regimes_where_ema_9_21_fails": [
                segment for segment, summary in ema_by_regime.items()
                if int(summary.get("signal_count", 0)) > 0
                and (float(summary.get("total_r", 0.0)) <= 0.0 or float(summary.get("global_profit_factor", 0.0) or 0.0) <= 1.0)
            ],
            "regimes_with_short_edge": [
                segment for segment, summary in ema_by_regime.items()
                if float(summary.get("short_total_r", 0.0)) > max(0.0, float(summary.get("long_total_r", 0.0)))
            ],
            "regimes_with_long_edge": [
                segment for segment, summary in ema_by_regime.items()
                if float(summary.get("long_total_r", 0.0)) > max(0.0, float(summary.get("short_total_r", 0.0)))
            ],
        }
        output_path = self._reports_dir / f"baseline_by_regime_{symbol}_{interval}_{feature_version}.json"
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["report_path"] = str(output_path)
        return report

    @classmethod
    def _predicted_labels_for_baseline(cls, baseline_name: str, rows: list[Any]) -> list[str]:
        if baseline_name == "always_long":
            return ["UP"] * len(rows)
        if baseline_name == "always_short":
            return ["DOWN"] * len(rows)
        if baseline_name == "previous_candle_direction":
            return [
                "UP" if float(row.features_json["return_1"]) > 0 else ("DOWN" if float(row.features_json["return_1"]) < 0 else "FLAT")
                for row in rows
            ]
        if baseline_name == "ema_9_21_direction":
            return cls._ema_direction(rows, "ema_9", "ema_21")
        if baseline_name == "ema_21_50_direction":
            return cls._ema_direction(rows, "ema_21", "ema_50")
        if baseline_name == "ema_stack_direction":
            return [
                "UP" if float(row.features_json.get("ema_stack_bullish", 0.0) or 0.0) == 1.0
                else ("DOWN" if float(row.features_json.get("ema_stack_bearish", 0.0) or 0.0) == 1.0 else "FLAT")
                for row in rows
            ]
        if baseline_name == "close_vs_ema_200_direction":
            return [
                "UP" if float(row.features_json.get("close_above_ema_200", 0.0) or 0.0) == 1.0
                else ("DOWN" if float(row.features_json.get("close_above_ema_200", 0.0) or 0.0) == 0.0 else "FLAT")
                for row in rows
            ]
        raise ValueError(f"Unsupported baseline: {baseline_name}")

    @staticmethod
    def _ema_direction(rows: list[Any], left_key: str, right_key: str) -> list[str]:
        result = []
        for row in rows:
            left = row.features_json.get(left_key)
            right = row.features_json.get(right_key)
            if left is None or right is None:
                result.append("FLAT")
            elif float(left) > float(right):
                result.append("UP")
            elif float(left) < float(right):
                result.append("DOWN")
            else:
                result.append("FLAT")
        return result

    @staticmethod
    def _match_segment(row: Any, segment_key: str) -> bool:
        if segment_key == "close_below_ema_200":
            value = row.features_json.get("close_above_ema_200")
            return value is not None and float(value) == 0.0
        value = row.features_json.get(segment_key)
        return value is not None and float(value) == 1.0

    @staticmethod
    def _summarize_folds(baseline_name: str, fold_reports: list[dict[str, Any]]) -> dict[str, Any]:
        signal_count = sum(int(fold["test_result"].get("signal_count", 0)) for fold in fold_reports)
        long_count = sum(int(fold["test_result"].get("long_count", 0)) for fold in fold_reports)
        short_count = sum(int(fold["test_result"].get("short_count", 0)) for fold in fold_reports)
        total_r = sum(float(fold["test_result"].get("total_r", 0.0)) for fold in fold_reports)
        long_total_r = sum(float(fold["test_result"].get("long_total_r", 0.0)) for fold in fold_reports)
        short_total_r = sum(float(fold["test_result"].get("short_total_r", 0.0)) for fold in fold_reports)
        wins = sum(int(fold["test_result"].get("win_count", 0)) for fold in fold_reports)
        resolved = sum(int(fold["test_result"].get("resolved_signal_count", 0)) for fold in fold_reports)
        gross_profit = sum(float(fold["test_result"].get("gross_profit_r", 0.0)) for fold in fold_reports)
        gross_loss = sum(float(fold["test_result"].get("gross_loss_r", 0.0)) for fold in fold_reports)
        if resolved > 0:
            if gross_loss > 0:
                profit_factor = gross_profit / gross_loss
            elif gross_profit > 0:
                profit_factor = float("inf")
            else:
                profit_factor = 0.0
        else:
            profit_factor = None
        profitable_fold_ratio = (
            sum(1 for fold in fold_reports if float(fold["test_result"].get("total_r", 0.0)) > 0.0) / len(fold_reports)
            if fold_reports
            else 0.0
        )
        return {
            "baseline_name": baseline_name,
            "summary": {
                "signal_count": signal_count,
                "long_count": long_count,
                "short_count": short_count,
                "total_r": total_r,
                "global_profit_factor": profit_factor,
                "expectancy_r": (total_r / resolved) if resolved else None,
                "win_rate": (wins / resolved) if resolved else None,
                "max_drawdown_r": max((float(fold["test_result"].get("max_drawdown_r", 0.0)) for fold in fold_reports), default=0.0),
                "profitable_fold_ratio": profitable_fold_ratio,
                "avg_r_per_trade": (total_r / resolved) if resolved else None,
                "long_total_r": long_total_r,
                "short_total_r": short_total_r,
            },
            "folds": fold_reports,
        }

    @staticmethod
    def _best_baseline(rows: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
        if not rows:
            return None
        best_name = max(
            rows,
            key=lambda name: (
                float(rows[name]["summary"].get("total_r", 0.0)),
                float(rows[name]["summary"].get("global_profit_factor", 0.0) or 0.0),
                int(rows[name]["summary"].get("signal_count", 0)),
            ),
        )
        return {
            "baseline_name": best_name,
            **rows[best_name]["summary"],
        }
