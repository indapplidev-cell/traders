from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config.settings import PROJECT_ROOT


class ProfitAwareEvaluator:
    def __init__(self, reports_dir: Path | None = None) -> None:
        self._reports_dir = reports_dir or (PROJECT_ROOT / "reports")
        self._reports_dir.mkdir(parents=True, exist_ok=True)

    def evaluate(
        self,
        model_version: str,
        predictions: list[dict[str, Any]],
        take_profit_atr: float,
        stop_loss_atr: float,
        confidence_thresholds: list[float],
    ) -> dict[str, Any]:
        threshold_reports = []
        for threshold in confidence_thresholds:
            selected = [
                row
                for row in predictions
                if row["confidence"] >= threshold and row["predicted_label"] in {"UP", "DOWN"}
            ]
            trade_outcomes = [self._simulate_trade(row, take_profit_atr, stop_loss_atr) for row in selected]
            threshold_reports.append(self._build_threshold_report(threshold, selected, trade_outcomes, len(predictions)))

        report = {
            "model_version": model_version,
            "take_profit_atr": take_profit_atr,
            "stop_loss_atr": stop_loss_atr,
            "thresholds": threshold_reports,
        }
        output_path = self._reports_dir / f"profit_eval_{model_version}.json"
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["report_path"] = str(output_path)
        return report

    def _simulate_trade(self, row: dict[str, Any], take_profit_atr: float, stop_loss_atr: float) -> dict[str, Any]:
        current_close = row["current_close"]
        atr_value = row["atr_14"]
        future_candles = row["future_candles"]
        if row["predicted_label"] == "UP":
            take_profit = current_close + (take_profit_atr * atr_value)
            stop_loss = current_close - (stop_loss_atr * atr_value)
            for candle in future_candles:
                tp_hit = candle["high"] >= take_profit
                sl_hit = candle["low"] <= stop_loss
                if tp_hit and sl_hit:
                    break
                if tp_hit:
                    return {"result": "TP", "r": take_profit_atr / stop_loss_atr}
                if sl_hit:
                    return {"result": "SL", "r": -1.0}
            close_r = max(-1.0, min(take_profit_atr / stop_loss_atr, row["future_move_atr"] / stop_loss_atr))
            return {"result": "NEITHER", "r": close_r}

        take_profit = current_close - (take_profit_atr * atr_value)
        stop_loss = current_close + (stop_loss_atr * atr_value)
        for candle in future_candles:
            tp_hit = candle["low"] <= take_profit
            sl_hit = candle["high"] >= stop_loss
            if tp_hit and sl_hit:
                break
            if tp_hit:
                return {"result": "TP", "r": take_profit_atr / stop_loss_atr}
            if sl_hit:
                return {"result": "SL", "r": -1.0}
        close_r = max(-1.0, min(take_profit_atr / stop_loss_atr, (-row["future_move_atr"]) / stop_loss_atr))
        return {"result": "NEITHER", "r": close_r}

    @staticmethod
    def _build_threshold_report(threshold: float, selected: list[dict[str, Any]], outcomes: list[dict[str, Any]], total_rows: int) -> dict[str, Any]:
        signal_count = len(selected)
        win_count = sum(int(item["result"] == "TP") for item in outcomes)
        loss_count = sum(int(item["result"] == "SL") for item in outcomes)
        neither_count = sum(int(item["result"] == "NEITHER") for item in outcomes)
        avg_r = (sum(item["r"] for item in outcomes) / signal_count) if signal_count else 0.0
        total_r = sum(item["r"] for item in outcomes)
        gross_profit = sum(item["r"] for item in outcomes if item["r"] > 0)
        gross_loss = abs(sum(item["r"] for item in outcomes if item["r"] < 0))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)
        max_drawdown_r = ProfitAwareEvaluator._max_drawdown([item["r"] for item in outcomes])
        direction_counts = {
            "UP": sum(int(row["predicted_label"] == "UP") for row in selected),
            "DOWN": sum(int(row["predicted_label"] == "DOWN") for row in selected),
        }
        return {
            "threshold": threshold,
            "signal_count": signal_count,
            "coverage": (signal_count / total_rows) if total_rows else 0.0,
            "win_count": win_count,
            "loss_count": loss_count,
            "neither_count": neither_count,
            "win_rate": (win_count / signal_count) if signal_count else 0.0,
            "avg_r": avg_r,
            "total_r": total_r,
            "profit_factor": profit_factor,
            "max_drawdown_r": max_drawdown_r,
            "avg_confidence": (sum(row["confidence"] for row in selected) / signal_count) if signal_count else 0.0,
            "direction_counts": direction_counts,
        }

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
