from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from app.config.settings import PROJECT_ROOT
from app.meta_label.meta_label_models import EMA_DIRECTION_LONG, EMA_DIRECTION_SHORT
from app.validation.walk_forward_splitter import WalkForwardConfig, WalkForwardSplitter


class MetaBaselineEvaluator:
    BASELINE_NAMES = [
        "take_all_ema_signals",
        "take_only_long_ema",
        "take_only_short_ema",
        "take_ema_only_trend_up",
        "take_ema_only_trend_down",
        "take_ema_only_high_volatility",
        "take_ema_only_low_volatility",
    ]

    def __init__(
        self,
        reports_dir: Path | None = None,
        walk_forward_splitter: WalkForwardSplitter | None = None,
    ) -> None:
        self._reports_dir = reports_dir or (PROJECT_ROOT / "reports")
        self._reports_dir.mkdir(parents=True, exist_ok=True)
        self._walk_forward_splitter = walk_forward_splitter or WalkForwardSplitter()

    def evaluate(
        self,
        symbol: str,
        interval: str,
        feature_version: str,
        label_version: str,
        dataset_rows: list[Any],
        config: WalkForwardConfig,
    ) -> dict[str, Any]:
        plan = self._walk_forward_splitter.build_plan(dataset_rows, config)
        baseline_folds: dict[str, list[dict[str, Any]]] = {name: [] for name in self.BASELINE_NAMES}

        for fold in plan:
            split_rows = self._walk_forward_splitter.apply_fold(dataset_rows, fold)
            for baseline_name in self.BASELINE_NAMES:
                filtered = [row for row in split_rows["test"] if self._include_row(baseline_name, row)]
                summary = self.summarize_trade_rows(filtered)
                baseline_folds[baseline_name].append(
                    {
                        "fold_index": fold["fold_index"],
                        "test_start": fold["test_start"],
                        "test_end": fold["test_end"],
                        "test_result": summary,
                    }
                )

        baselines = {
            name: self._summarize_baseline_folds(name, fold_reports)
            for name, fold_reports in baseline_folds.items()
        }
        best_baseline_name = max(
            baselines,
            key=lambda name: (
                float(baselines[name]["summary"].get("total_r", 0.0)),
                float(baselines[name]["summary"].get("global_profit_factor", 0.0) or 0.0),
                int(baselines[name]["summary"].get("signal_count", 0)),
            ),
        ) if baselines else None
        report = {
            "symbol": symbol,
            "interval": interval,
            "feature_version": feature_version,
            "label_version": label_version,
            "fold_count": len(plan),
            "baselines": baselines,
            "best_baseline_overall": best_baseline_name,
        }
        output_path = self._reports_dir / f"meta_baselines_{symbol}_{interval}_{label_version}.json"
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["report_path"] = str(output_path)
        return report

    @staticmethod
    def summarize_trade_rows(rows: list[Any]) -> dict[str, Any]:
        signal_count = len(rows)
        long_rows = [row for row in rows if row.ema_signal_direction == EMA_DIRECTION_LONG]
        short_rows = [row for row in rows if row.ema_signal_direction == EMA_DIRECTION_SHORT]
        net_values = [float(row.meta_trade_r) for row in rows]
        gross_profit = sum(value for value in net_values if value > 0)
        gross_loss = abs(sum(value for value in net_values if value < 0))
        profit_factor = None
        if signal_count > 0:
            if gross_loss > 0:
                profit_factor = gross_profit / gross_loss
            elif gross_profit > 0:
                profit_factor = float("inf")
            else:
                profit_factor = 0.0
        win_count = sum(int(row.meta_target_win == 1) for row in rows)
        total_r = sum(net_values)
        return {
            "signal_count": signal_count,
            "long_count": len(long_rows),
            "short_count": len(short_rows),
            "total_r": total_r,
            "global_profit_factor": profit_factor,
            "expectancy_r": (total_r / signal_count) if signal_count else None,
            "win_rate": (win_count / signal_count) if signal_count else None,
            "max_drawdown_r": MetaBaselineEvaluator._max_drawdown(net_values),
            "avg_r_per_trade": (total_r / signal_count) if signal_count else None,
        }

    @classmethod
    def _summarize_baseline_folds(cls, baseline_name: str, fold_reports: list[dict[str, Any]]) -> dict[str, Any]:
        signal_count = sum(int(fold["test_result"].get("signal_count", 0)) for fold in fold_reports)
        long_count = sum(int(fold["test_result"].get("long_count", 0)) for fold in fold_reports)
        short_count = sum(int(fold["test_result"].get("short_count", 0)) for fold in fold_reports)
        total_r = sum(float(fold["test_result"].get("total_r", 0.0)) for fold in fold_reports)
        win_rows = sum(
            float(fold["test_result"].get("win_rate", 0.0) or 0.0) * int(fold["test_result"].get("signal_count", 0))
            for fold in fold_reports
        )
        profitable_fold_ratio = (
            sum(1 for fold in fold_reports if float(fold["test_result"].get("total_r", 0.0)) > 0.0) / len(fold_reports)
            if fold_reports
            else 0.0
        )
        gross_profit = sum(max(0.0, float(fold["test_result"].get("total_r", 0.0))) for fold in fold_reports)
        gross_loss = abs(sum(min(0.0, float(fold["test_result"].get("total_r", 0.0))) for fold in fold_reports))
        if signal_count > 0:
            if gross_loss > 0:
                global_profit_factor = gross_profit / gross_loss
            elif gross_profit > 0:
                global_profit_factor = float("inf")
            else:
                global_profit_factor = 0.0
        else:
            global_profit_factor = None
        summary = {
            "signal_count": signal_count,
            "long_count": long_count,
            "short_count": short_count,
            "total_r": total_r,
            "global_profit_factor": global_profit_factor,
            "expectancy_r": (total_r / signal_count) if signal_count else None,
            "win_rate": (win_rows / signal_count) if signal_count else None,
            "max_drawdown_r": max((float(fold["test_result"].get("max_drawdown_r", 0.0)) for fold in fold_reports), default=0.0),
            "profitable_fold_ratio": profitable_fold_ratio,
            "avg_r_per_trade": (total_r / signal_count) if signal_count else None,
        }
        return {"baseline_name": baseline_name, "folds": fold_reports, "summary": summary}

    @staticmethod
    def _include_row(baseline_name: str, row: Any) -> bool:
        if baseline_name == "take_all_ema_signals":
            return True
        if baseline_name == "take_only_long_ema":
            return row.ema_signal_direction == EMA_DIRECTION_LONG
        if baseline_name == "take_only_short_ema":
            return row.ema_signal_direction == EMA_DIRECTION_SHORT
        if baseline_name == "take_ema_only_trend_up":
            return float(row.features_json.get("regime_trend_up", 0.0) or 0.0) == 1.0
        if baseline_name == "take_ema_only_trend_down":
            return float(row.features_json.get("regime_trend_down", 0.0) or 0.0) == 1.0
        if baseline_name == "take_ema_only_high_volatility":
            return float(row.features_json.get("regime_high_volatility", 0.0) or 0.0) == 1.0
        if baseline_name == "take_ema_only_low_volatility":
            return float(row.features_json.get("regime_low_volatility", 0.0) or 0.0) == 1.0
        raise ValueError(f"Unsupported meta baseline: {baseline_name}")

    @staticmethod
    def _max_drawdown(values: list[float]) -> float:
        equity = 0.0
        peak = 0.0
        max_drawdown = 0.0
        for value in values:
            equity += value
            peak = max(peak, equity)
            max_drawdown = min(max_drawdown, equity - peak)
        return abs(max_drawdown)
