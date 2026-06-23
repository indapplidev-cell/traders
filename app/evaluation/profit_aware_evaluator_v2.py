from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config.settings import PROJECT_ROOT
from app.diagnostics.profit_exit_root_cause_audit import ProfitExitRootCauseAudit
from app.evaluation.signal_gate_evaluator import SignalGateEvaluator


class ProfitAwareEvaluatorV2:
    def __init__(
        self,
        reports_dir: Path | None = None,
        signal_gate_evaluator: SignalGateEvaluator | None = None,
        profit_exit_root_cause_audit: ProfitExitRootCauseAudit | None = None,
    ) -> None:
        self._reports_dir = reports_dir or (PROJECT_ROOT / "reports")
        self._reports_dir.mkdir(parents=True, exist_ok=True)
        self._signal_gate_evaluator = signal_gate_evaluator or SignalGateEvaluator(reports_dir=self._reports_dir)
        self._profit_exit_root_cause_audit = (
            profit_exit_root_cause_audit or ProfitExitRootCauseAudit()
        )

    def evaluate(
        self,
        model_version: str,
        predictions: list[dict[str, Any]],
        take_profit_atr: float,
        stop_loss_atr: float,
        fee_r: float = 0.0,
        slippage_r: float = 0.0,
        same_candle_policy: str = "conservative",
    ) -> dict[str, Any]:
        evaluation = self.evaluate_predictions(
            predictions=predictions,
            take_profit_atr=take_profit_atr,
            stop_loss_atr=stop_loss_atr,
            fee_r=fee_r,
            slippage_r=slippage_r,
            same_candle_policy=same_candle_policy,
        )
        gate_results = evaluation["gate_results"]

        report = {
            "model_version": model_version,
            "take_profit_atr": take_profit_atr,
            "stop_loss_atr": stop_loss_atr,
            "fee_r": fee_r,
            "slippage_r": slippage_r,
            "same_candle_policy": same_candle_policy,
            "gate_results": gate_results,
        }
        output_path = self._reports_dir / f"profit_eval_v2_{model_version}.json"
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        report["report_path"] = str(output_path)
        return report

    def evaluate_predictions(
        self,
        predictions: list[dict[str, Any]],
        take_profit_atr: float,
        stop_loss_atr: float,
        fee_r: float = 0.0,
        slippage_r: float = 0.0,
        same_candle_policy: str = "conservative",
    ) -> dict[str, Any]:
        gate_results: list[dict[str, Any]] = []
        for gate_type, thresholds in self._signal_gate_evaluator.GATE_THRESHOLDS.items():
            for threshold in thresholds:
                single = self.evaluate_single_gate(
                    predictions=predictions,
                    gate_type=gate_type,
                    threshold=threshold,
                    take_profit_atr=take_profit_atr,
                    stop_loss_atr=stop_loss_atr,
                    fee_r=fee_r,
                    slippage_r=slippage_r,
                    same_candle_policy=same_candle_policy,
                )
                gate_results.append(single["summary"])

        best_gate = self._best_gate_summary(gate_results)
        summary = dict(best_gate or {})
        profit_exit_root_cause_audit = dict(
            summary.get("profit_exit_root_cause_audit") or {}
        )
        entry_path_filter_summary = dict(
            summary.get("entry_path_prediction_filter_summary")
            or self._entry_path_prediction_filter_summary(predictions)
        )
        stop_pressure_effectiveness_audit = dict(
            summary.get("stop_pressure_effectiveness_audit")
            or entry_path_filter_summary.get("stop_pressure_effectiveness_audit")
            or {}
        )
        summary["entry_path_prediction_filter_summary"] = entry_path_filter_summary
        summary["stop_pressure_effectiveness_audit"] = stop_pressure_effectiveness_audit
        return {
            "gate_results": gate_results,
            "summary": summary,
            "profit_exit_root_cause_audit": profit_exit_root_cause_audit,
            "entry_path_prediction_filter_summary": entry_path_filter_summary,
            "stop_pressure_effectiveness_audit": stop_pressure_effectiveness_audit,
        }

    def evaluate_single_gate(
        self,
        predictions: list[dict[str, Any]],
        gate_type: str,
        threshold: float,
        take_profit_atr: float,
        stop_loss_atr: float,
        fee_r: float = 0.0,
        slippage_r: float = 0.0,
        same_candle_policy: str = "conservative",
    ) -> dict[str, Any]:
        original_selection = self._signal_gate_evaluator.select_signals(
            predictions,
            gate_type,
            threshold,
            apply_entry_path_filter=False,
        )
        selection = self._signal_gate_evaluator.select_signals(
            predictions,
            gate_type,
            threshold,
            apply_entry_path_filter=True,
        )
        signal_rows = selection["signal_rows"]
        entry_path_filter_summary = self._entry_path_final_decision_filter_summary(
            predictions=predictions,
            original_selection=original_selection,
            filtered_selection=selection,
            gate_type=gate_type,
            threshold=threshold,
        )
        stop_pressure_effectiveness_audit = dict(
            entry_path_filter_summary.get("stop_pressure_effectiveness_audit") or {}
        )
        if not signal_rows:
            summary = self._empty_gate_report(selection, same_candle_policy)
            summary["profit_exit_root_cause_audit"] = self._profit_exit_root_cause_audit.analyze(
                signal_rows=[],
                outcomes=[],
                take_profit_atr=take_profit_atr,
                stop_loss_atr=stop_loss_atr,
                fee_r=fee_r,
                slippage_r=slippage_r,
                same_candle_policy=same_candle_policy,
                gate_type=gate_type,
                threshold=threshold,
            )
            summary["entry_path_prediction_filter_summary"] = entry_path_filter_summary
            summary["stop_pressure_effectiveness_audit"] = stop_pressure_effectiveness_audit
            return {"summary": summary, "signal_rows": [], "outcomes": []}

        outcomes = [
            self._simulate_trade(
                row=row,
                take_profit_atr=take_profit_atr,
                stop_loss_atr=stop_loss_atr,
                fee_r=fee_r,
                slippage_r=slippage_r,
                same_candle_policy=same_candle_policy,
            )
            for row in signal_rows
        ]
        summary = self._build_gate_report(selection, signal_rows, outcomes, same_candle_policy)
        summary["profit_exit_root_cause_audit"] = self._profit_exit_root_cause_audit.analyze(
            signal_rows=signal_rows,
            outcomes=outcomes,
            take_profit_atr=take_profit_atr,
            stop_loss_atr=stop_loss_atr,
            fee_r=fee_r,
            slippage_r=slippage_r,
            same_candle_policy=same_candle_policy,
            gate_type=gate_type,
            threshold=threshold,
        )
        summary["entry_path_prediction_filter_summary"] = entry_path_filter_summary
        summary["stop_pressure_effectiveness_audit"] = stop_pressure_effectiveness_audit
        return {
            "summary": summary,
            "signal_rows": signal_rows,
            "outcomes": outcomes,
        }

    def _simulate_trade(
        self,
        row: dict[str, Any],
        take_profit_atr: float,
        stop_loss_atr: float,
        fee_r: float,
        slippage_r: float,
        same_candle_policy: str,
    ) -> dict[str, Any]:
        current_close = float(row["current_close"])
        atr_value = float(row["atr_14"])
        future_candles = row["future_candles"]
        if row["signal_direction"] == "LONG":
            take_profit = current_close + (take_profit_atr * atr_value)
            stop_loss = current_close - (stop_loss_atr * atr_value)
            for candle in future_candles:
                tp_hit = float(candle["high"]) >= take_profit
                sl_hit = float(candle["low"]) <= stop_loss
                if tp_hit and sl_hit:
                    return self._resolve_ambiguous(take_profit_atr, stop_loss_atr, fee_r, slippage_r, same_candle_policy)
                if tp_hit:
                    return self._with_costs("TP", take_profit_atr / stop_loss_atr, fee_r, slippage_r)
                if sl_hit:
                    return self._with_costs("SL", -1.0, fee_r, slippage_r)
            raw_r = max(-1.0, min(take_profit_atr / stop_loss_atr, float(row["future_move_atr"]) / stop_loss_atr))
            return self._with_costs("NEITHER", raw_r, fee_r, slippage_r)

        take_profit = current_close - (take_profit_atr * atr_value)
        stop_loss = current_close + (stop_loss_atr * atr_value)
        for candle in future_candles:
            tp_hit = float(candle["low"]) <= take_profit
            sl_hit = float(candle["high"]) >= stop_loss
            if tp_hit and sl_hit:
                return self._resolve_ambiguous(take_profit_atr, stop_loss_atr, fee_r, slippage_r, same_candle_policy)
            if tp_hit:
                return self._with_costs("TP", take_profit_atr / stop_loss_atr, fee_r, slippage_r)
            if sl_hit:
                return self._with_costs("SL", -1.0, fee_r, slippage_r)
        raw_r = max(-1.0, min(take_profit_atr / stop_loss_atr, (-float(row["future_move_atr"])) / stop_loss_atr))
        return self._with_costs("NEITHER", raw_r, fee_r, slippage_r)

    @staticmethod
    def _best_gate_summary(gate_results: list[dict[str, Any]]) -> dict[str, Any] | None:
        eligible = [
            dict(row)
            for row in gate_results
            if int(row.get("resolved_signal_count", 0) or 0) > 0
        ]
        if not eligible:
            return None
        return max(
            eligible,
            key=lambda row: (
                float(row.get("total_r", 0.0) or 0.0),
                float(row.get("profit_factor", 0.0) or 0.0),
                int(row.get("resolved_signal_count", 0) or 0),
            ),
        )

    @staticmethod
    def _with_costs(result: str, raw_r: float, fee_r: float, slippage_r: float) -> dict[str, Any]:
        return {"result": result, "raw_r": raw_r, "net_r": raw_r - fee_r - slippage_r}

    @staticmethod
    def _build_gate_report(
        selection: dict[str, Any],
        signal_rows: list[dict[str, Any]],
        outcomes: list[dict[str, Any]],
        same_candle_policy: str,
    ) -> dict[str, Any]:
        signal_count = len(signal_rows)
        included = [(row, item) for row, item in zip(signal_rows, outcomes) if item["result"] != "AMBIGUOUS"]
        resolved_rows = [row for row, _ in included]
        resolved_outcomes = [item for _, item in included]
        net_values = [float(item["net_r"]) for item in resolved_outcomes]
        long_outcomes = [item for row, item in included if row["signal_direction"] == "LONG"]
        short_outcomes = [item for row, item in included if row["signal_direction"] == "SHORT"]
        win_count = sum(int(item["result"] == "TP") for item in resolved_outcomes)
        loss_count = sum(int(item["result"] == "SL") for item in resolved_outcomes)
        neither_count = sum(int(item["result"] == "NEITHER") for item in resolved_outcomes)
        ambiguous_count = sum(int(item["result"] == "AMBIGUOUS") for item in outcomes)
        gross_profit_r = sum(value for value in net_values if value > 0)
        gross_loss_r = abs(sum(value for value in net_values if value < 0))
        profit_factor = gross_profit_r / gross_loss_r if gross_loss_r > 0 else (float("inf") if gross_profit_r > 0 else 0.0)
        total_r = sum(net_values)
        resolved_count = len(resolved_outcomes)
        avg_r = (total_r / resolved_count) if resolved_count else None
        long_rows = [row for row in resolved_rows if row["signal_direction"] == "LONG"]
        short_rows = [row for row in resolved_rows if row["signal_direction"] == "SHORT"]
        return {
            "gate_type": selection["gate_type"],
            "threshold": selection["threshold"],
            "total_rows": selection["total_rows"],
            "signal_count": signal_count,
            "resolved_signal_count": resolved_count,
            "skipped_flat_count": selection["skipped_flat_count"],
            "skipped_entry_path_filter_count": int(
                selection.get("skipped_entry_path_filter_count", 0) or 0
            ),
            "coverage": (signal_count / selection["total_rows"]) if selection["total_rows"] else 0.0,
            "win_count": win_count,
            "loss_count": loss_count,
            "neither_count": neither_count,
            "ambiguous_count": ambiguous_count,
            "gross_profit_r": gross_profit_r,
            "gross_loss_r": gross_loss_r,
            "profit_factor": profit_factor if resolved_count else None,
            "total_r": total_r,
            "avg_r": avg_r,
            "expectancy_r": avg_r,
            "win_rate": (win_count / resolved_count) if resolved_count else None,
            "loss_rate": (loss_count / resolved_count) if resolved_count else None,
            "max_win_r": max(net_values) if net_values else None,
            "max_loss_r": min(net_values) if net_values else None,
            "long_count": len(long_rows),
            "short_count": len(short_rows),
            "long_total_r": sum(item["net_r"] for item in long_outcomes),
            "short_total_r": sum(item["net_r"] for item in short_outcomes),
            "long_win_rate": ProfitAwareEvaluatorV2._win_rate(long_outcomes),
            "short_win_rate": ProfitAwareEvaluatorV2._win_rate(short_outcomes),
            "avg_confidence_on_signals": (sum(float(row["confidence"]) for row in resolved_rows) / resolved_count) if resolved_count else None,
            "avg_margin_on_signals": (sum(float(row["margin"]) for row in resolved_rows) / resolved_count) if resolved_count else None,
            "avg_directional_edge_on_signals": (
                sum(float(row["directional_edge"]) for row in resolved_rows) / resolved_count
            ) if resolved_count else None,
            "max_drawdown_r": ProfitAwareEvaluatorV2._max_drawdown(net_values),
            "same_candle_policy": same_candle_policy,
            "reject_reason": None if resolved_count else "no_resolved_signals",
        }

    @staticmethod
    def _empty_gate_report(selection: dict[str, Any], same_candle_policy: str) -> dict[str, Any]:
        return {
            "gate_type": selection["gate_type"],
            "threshold": selection["threshold"],
            "total_rows": selection["total_rows"],
            "signal_count": 0,
            "resolved_signal_count": 0,
            "skipped_flat_count": selection["skipped_flat_count"],
            "skipped_entry_path_filter_count": int(
                selection.get("skipped_entry_path_filter_count", 0) or 0
            ),
            "coverage": 0.0,
            "win_count": 0,
            "loss_count": 0,
            "neither_count": 0,
            "ambiguous_count": 0,
            "gross_profit_r": 0.0,
            "gross_loss_r": 0.0,
            "profit_factor": None,
            "total_r": 0.0,
            "avg_r": None,
            "expectancy_r": None,
            "win_rate": None,
            "loss_rate": None,
            "max_win_r": None,
            "max_loss_r": None,
            "long_count": 0,
            "short_count": 0,
            "long_total_r": 0.0,
            "short_total_r": 0.0,
            "long_win_rate": None,
            "short_win_rate": None,
            "avg_confidence_on_signals": None,
            "avg_margin_on_signals": None,
            "avg_directional_edge_on_signals": None,
            "max_drawdown_r": 0.0,
            "same_candle_policy": same_candle_policy,
            "reject_reason": "no_signals",
        }

    @staticmethod
    def _entry_path_prediction_filter_summary(predictions: list[dict[str, Any]]) -> dict[str, Any]:
        total = len(predictions)
        blocked_rows = [row for row in predictions if bool(row.get("entry_path_filter_blocked", False))]
        passed_rows = [row for row in predictions if not bool(row.get("entry_path_filter_blocked", False))]

        def _mean(rows: list[dict[str, Any]], key: str) -> float | None:
            values = [float(row.get(key, 0.0) or 0.0) for row in rows if row.get(key) is not None]
            return (sum(values) / len(values)) if values else None

        def _label(row: dict[str, Any], key: str, fallback: str = "") -> str:
            value = row.get(key, fallback)
            return str(value or fallback).upper()

        def _original_label(row: dict[str, Any]) -> str:
            return _label(row, "entry_path_original_predicted_label", _label(row, "predicted_label", ""))

        def _is_original_trade(row: dict[str, Any]) -> bool:
            return _original_label(row) in {"UP", "DOWN"}

        def _is_actual_trade(row: dict[str, Any]) -> bool:
            return _label(row, "actual_label", _label(row, "target_label", "")) in {"UP", "DOWN"}

        def _is_false_positive_removed(row: dict[str, Any]) -> bool:
            return bool(row.get("entry_path_filter_blocked", False)) and _is_original_trade(row) and not _is_actual_trade(row)

        def _is_true_positive_removed(row: dict[str, Any]) -> bool:
            return bool(row.get("entry_path_filter_blocked", False)) and _is_original_trade(row) and _is_actual_trade(row)

        def _quality_blocked(row: dict[str, Any]) -> bool:
            reason = str(row.get("entry_path_filter_block_reason") or "")
            if reason == "low_entry_quality":
                return True
            threshold = row.get("entry_path_filter_threshold")
            if threshold is None:
                return False
            return float(row.get("entry_path_quality_score", 0.0) or 0.0) < float(threshold)

        def _stop_blocked(row: dict[str, Any]) -> bool:
            reason = str(row.get("entry_path_filter_block_reason") or "")
            if reason == "high_stop_pressure":
                return True
            threshold = row.get("entry_path_filter_stop_threshold")
            if threshold is None:
                return False
            return float(row.get("stop_pressure_risk_score", 0.0) or 0.0) > float(threshold)
        
        def _mae_blocked(row: dict[str, Any]) -> bool:
            reason = str(row.get("entry_path_filter_block_reason") or "")
            if reason == "high_mae_pressure":
                return True
            threshold = row.get("entry_path_filter_mae_threshold")
            if threshold is None:
                return False
            return float(row.get("mae_pressure_risk_score", 0.0) or 0.0) > float(threshold)

        predicted_trade_rows = [row for row in predictions if _is_original_trade(row)]
        blocked_predicted_trade_rows = [row for row in blocked_rows if _is_original_trade(row)]
        blocked_by_quality_rows = [row for row in blocked_rows if _quality_blocked(row)]
        blocked_by_stop_rows = [row for row in blocked_rows if _stop_blocked(row)]
        blocked_by_mae_rows = [row for row in blocked_rows if _mae_blocked(row)]
        blocked_by_both_rows = [row for row in blocked_rows if _quality_blocked(row) and _stop_blocked(row)]
        blocked_false_positive_rows = [row for row in blocked_rows if _is_false_positive_removed(row)]
        blocked_true_positive_rows = [row for row in blocked_rows if _is_true_positive_removed(row)]
        stop_blocked_false_positive_rows = [row for row in blocked_by_stop_rows if _is_false_positive_removed(row)]
        stop_blocked_true_positive_rows = [row for row in blocked_by_stop_rows if _is_true_positive_removed(row)]
        quality_blocked_false_positive_rows = [row for row in blocked_by_quality_rows if _is_false_positive_removed(row)]
        quality_blocked_true_positive_rows = [row for row in blocked_by_quality_rows if _is_true_positive_removed(row)]

        stop_pressure_effectiveness_status = "NO_ENTRY_PATH_FILTER"
        if any(bool(row.get("entry_path_filter_enabled", False)) for row in predictions):
            if not blocked_by_stop_rows:
                stop_pressure_effectiveness_status = "NO_STOP_PRESSURE_BLOCKS"
            elif stop_blocked_false_positive_rows and stop_blocked_true_positive_rows:
                stop_pressure_effectiveness_status = "STOP_PRESSURE_MIXED_TRUE_AND_FALSE_POSITIVE_BLOCKS"
            elif stop_blocked_false_positive_rows:
                stop_pressure_effectiveness_status = "STOP_PRESSURE_REMOVED_FALSE_POSITIVES"
            elif stop_blocked_true_positive_rows:
                stop_pressure_effectiveness_status = "STOP_PRESSURE_REMOVED_ONLY_TRUE_POSITIVES"
            else:
                stop_pressure_effectiveness_status = "STOP_PRESSURE_BLOCKED_ONLY_NON_TRADE_ROWS"

        stop_pressure_effectiveness_audit = {
            "diagnostic_name": "stop_pressure_effectiveness_audit",
            "diagnostic_version": "ml38.10.16",
            "entry_path_filter_enabled": any(
                bool(row.get("entry_path_filter_enabled", False)) for row in predictions
            ),
            "entry_path_quality_threshold": next(
                (row.get("entry_path_filter_threshold") for row in predictions if row.get("entry_path_filter_threshold") is not None),
                None,
            ),
            "stop_pressure_threshold": next(
                (row.get("entry_path_filter_stop_threshold") for row in predictions if row.get("entry_path_filter_stop_threshold") is not None),
                None,
            ),
            "mae_pressure_threshold": next(
                (
                    row.get("entry_path_filter_mae_threshold")
                    for row in predictions
                    if row.get("entry_path_filter_mae_threshold") is not None
                ),
                None,
            ),
            "mae_pressure_threshold": next(
                (row.get("entry_path_filter_mae_threshold") for row in predictions if row.get("entry_path_filter_mae_threshold") is not None),
                None,
            ),
            "status": stop_pressure_effectiveness_status,
            "total_prediction_rows": int(total),
            "original_predicted_trade_rows": int(len(predicted_trade_rows)),
            "blocked_prediction_rows": int(len(blocked_rows)),
            "blocked_original_predicted_trade_rows": int(len(blocked_predicted_trade_rows)),
            "blocked_by_low_entry_quality_count": int(len(blocked_by_quality_rows)),
            "blocked_by_high_stop_pressure_count": int(len(blocked_by_stop_rows)),
            "blocked_by_high_mae_pressure_count": int(len(blocked_by_mae_rows)),
            "blocked_by_high_mae_pressure_count": int(len(blocked_by_mae_rows)),
            "blocked_by_both_count": int(len(blocked_by_both_rows)),
            "removed_false_positive_count": int(len(blocked_false_positive_rows)),
            "removed_true_positive_count": int(len(blocked_true_positive_rows)),
            "low_entry_quality_removed_false_positive_count": int(len(quality_blocked_false_positive_rows)),
            "low_entry_quality_removed_true_positive_count": int(len(quality_blocked_true_positive_rows)),
            "high_stop_pressure_removed_false_positive_count": int(len(stop_blocked_false_positive_rows)),
            "high_stop_pressure_removed_true_positive_count": int(len(stop_blocked_true_positive_rows)),
            "stop_pressure_effective_for_false_positive_reduction": bool(len(stop_blocked_false_positive_rows) > 0),
            "stop_pressure_blocked_trade_rows_rate": (
                len([row for row in blocked_by_stop_rows if _is_original_trade(row)]) / len(predicted_trade_rows)
                if predicted_trade_rows
                else 0.0
            ),
            "false_positive_removed_rate_among_blocked_trades": (
                len(blocked_false_positive_rows) / len(blocked_predicted_trade_rows)
                if blocked_predicted_trade_rows
                else 0.0
            ),
        }

        return {
            "entry_path_filter_enabled": any(
                bool(row.get("entry_path_filter_enabled", False)) for row in predictions
            ),
            "total_prediction_rows": int(total),
            "blocked_prediction_rows": int(len(blocked_rows)),
            "passed_prediction_rows": int(len(passed_rows)),
            "blocked_prediction_rate": (len(blocked_rows) / total) if total else 0.0,
            "original_predicted_trade_rows": int(len(predicted_trade_rows)),
            "blocked_original_predicted_trade_rows": int(len(blocked_predicted_trade_rows)),
            "blocked_by_low_entry_quality_count": int(len(blocked_by_quality_rows)),
            "blocked_by_high_stop_pressure_count": int(len(blocked_by_stop_rows)),
            "blocked_by_high_mae_pressure_count": int(len(blocked_by_mae_rows)),
            "blocked_by_high_mae_pressure_count": int(len(blocked_by_mae_rows)),
            "blocked_by_both_count": int(len(blocked_by_both_rows)),
            "removed_false_positive_count": int(len(blocked_false_positive_rows)),
            "removed_true_positive_count": int(len(blocked_true_positive_rows)),
            "avg_blocked_entry_path_quality_score": _mean(blocked_rows, "entry_path_quality_score"),
            "avg_passed_entry_path_quality_score": _mean(passed_rows, "entry_path_quality_score"),
            "avg_blocked_stop_pressure_risk_score": _mean(blocked_rows, "stop_pressure_risk_score"),
            "avg_passed_stop_pressure_risk_score": _mean(passed_rows, "stop_pressure_risk_score"),
            "avg_blocked_mae_pressure_risk_score": _mean(blocked_rows, "mae_pressure_risk_score"),
            "avg_passed_mae_pressure_risk_score": _mean(passed_rows, "mae_pressure_risk_score"),
            "blocked_original_label_counts": {
                label: sum(
                    int(_original_label(row) == label)
                    for row in blocked_rows
                )
                for label in ("UP", "DOWN", "FLAT")
            },
            "block_reason_counts": {
                "low_entry_quality": int(len([row for row in blocked_rows if str(row.get("entry_path_filter_block_reason") or "") == "low_entry_quality"])),
                "high_stop_pressure": int(len([row for row in blocked_rows if str(row.get("entry_path_filter_block_reason") or "") == "high_stop_pressure"])),
                "high_mae_pressure": int(len([row for row in blocked_rows if str(row.get("entry_path_filter_block_reason") or "") == "high_mae_pressure"])),
                "unknown": int(len([row for row in blocked_rows if not str(row.get("entry_path_filter_block_reason") or "")])),
            },
            "stop_pressure_effectiveness_audit": stop_pressure_effectiveness_audit,
        }

    @staticmethod
    def _entry_path_final_decision_filter_summary(
        *,
        predictions: list[dict[str, Any]],
        original_selection: dict[str, Any],
        filtered_selection: dict[str, Any],
        gate_type: str,
        threshold: float,
    ) -> dict[str, Any]:
        """Entry-path audit aligned with the final profit-aware gate decision stream.

        ML38.10.14.3:
        - old audit counted all prediction rows;
        - this audit counts only rows that the selected profit gate would turn into
          LONG/SHORT signals before entry-path filtering.
        """

        original_signal_rows = [
            dict(row) for row in original_selection.get("signal_rows", [])
        ]
        filtered_signal_rows = [
            dict(row) for row in filtered_selection.get("signal_rows", [])
        ]

        def _label(row: dict[str, Any], key: str, fallback: str = "") -> str:
            value = row.get(key, fallback)
            return str(value or fallback).upper()

        def _is_actual_trade(row: dict[str, Any]) -> bool:
            return _label(row, "actual_label", _label(row, "target_label", "")) in {"UP", "DOWN"}

        def _is_signal_correct(row: dict[str, Any]) -> bool:
            direction = str(row.get("signal_direction") or "").upper()
            actual = _label(row, "actual_label", _label(row, "target_label", ""))
            return (direction == "LONG" and actual == "UP") or (
                direction == "SHORT" and actual == "DOWN"
            )

        def _mean(rows: list[dict[str, Any]], key: str) -> float | None:
            values = [
                float(row.get(key, 0.0) or 0.0)
                for row in rows
                if row.get(key) is not None
            ]
            return (sum(values) / len(values)) if values else None

        original_signal_count = len(original_signal_rows)
        filtered_signal_count = len(filtered_signal_rows)

        blocked_signal_rows = [
            row for row in original_signal_rows
            if bool(row.get("entry_path_filter_blocked", False))
        ]

        blocked_by_quality_rows = [
            row for row in blocked_signal_rows
            if str(row.get("entry_path_filter_block_reason") or "") == "low_entry_quality"
            or (
                row.get("entry_path_filter_threshold") is not None
                and float(row.get("entry_path_quality_score", 0.0) or 0.0)
                < float(row.get("entry_path_filter_threshold"))
            )
        ]

        blocked_by_stop_rows = [
            row for row in blocked_signal_rows
            if str(row.get("entry_path_filter_block_reason") or "") == "high_stop_pressure"
            or (
                row.get("entry_path_filter_stop_threshold") is not None
                and float(row.get("stop_pressure_risk_score", 0.0) or 0.0)
                > float(row.get("entry_path_filter_stop_threshold"))
            )
        ]

        blocked_by_mae_rows = [
            row for row in blocked_signal_rows
            if str(row.get("entry_path_filter_block_reason") or "") == "high_mae_pressure"
            or (
                row.get("entry_path_filter_mae_threshold") is not None
                and float(row.get("mae_pressure_risk_score", 0.0) or 0.0)
                > float(row.get("entry_path_filter_mae_threshold"))
            )
        ]

        removed_non_opportunity_rows = [
            row for row in blocked_signal_rows if not _is_actual_trade(row)
        ]
        removed_wrong_direction_rows = [
            row for row in blocked_signal_rows
            if _is_actual_trade(row) and not _is_signal_correct(row)
        ]
        removed_correct_direction_rows = [
            row for row in blocked_signal_rows if _is_signal_correct(row)
        ]

        stop_blocked_false_rows = [
            row for row in blocked_by_stop_rows
            if (not _is_actual_trade(row)) or (_is_actual_trade(row) and not _is_signal_correct(row))
        ]
        stop_blocked_correct_rows = [
            row for row in blocked_by_stop_rows if _is_signal_correct(row)
        ]

        consistency_delta = original_signal_count - filtered_signal_count - len(blocked_signal_rows)
        consistency_ok = consistency_delta == 0

        if not any(bool(row.get("entry_path_filter_enabled", False)) for row in predictions):
            status = "NO_ENTRY_PATH_FILTER"
        elif not blocked_signal_rows:
            status = "NO_FINAL_SIGNAL_BLOCKS"
        elif stop_blocked_false_rows and stop_blocked_correct_rows:
            status = "STOP_PRESSURE_MIXED_TRUE_AND_FALSE_SIGNAL_BLOCKS"
        elif stop_blocked_false_rows:
            status = "STOP_PRESSURE_REMOVED_FALSE_SIGNALS"
        elif stop_blocked_correct_rows:
            status = "STOP_PRESSURE_REMOVED_ONLY_CORRECT_SIGNALS"
        elif removed_non_opportunity_rows or removed_wrong_direction_rows:
            status = "ENTRY_PATH_REMOVED_FALSE_SIGNALS"
        else:
            status = "ENTRY_PATH_REMOVED_ONLY_CORRECT_SIGNALS"

        stop_pressure_effectiveness_audit = {
            "diagnostic_name": "stop_pressure_effectiveness_audit",
            "diagnostic_version": "ml38.10.16",
            "audit_stream": "final_profit_aware_gate_signal_stream",
            "gate_type": str(gate_type),
            "threshold": float(threshold),
            "entry_path_filter_enabled": any(
                bool(row.get("entry_path_filter_enabled", False)) for row in predictions
            ),
            "entry_path_quality_threshold": next(
                (
                    row.get("entry_path_filter_threshold")
                    for row in predictions
                    if row.get("entry_path_filter_threshold") is not None
                ),
                None,
            ),
            "stop_pressure_threshold": next(
                (
                    row.get("entry_path_filter_stop_threshold")
                    for row in predictions
                    if row.get("entry_path_filter_stop_threshold") is not None
                ),
                None,
            ),
            "status": status,
            "original_final_signal_count": int(original_signal_count),
            "filtered_final_signal_count": int(filtered_signal_count),
            "blocked_final_signal_count": int(len(blocked_signal_rows)),
            "blocked_by_low_entry_quality_count": int(len(blocked_by_quality_rows)),
            "blocked_by_high_stop_pressure_count": int(len(blocked_by_stop_rows)),
            "removed_non_opportunity_signal_count": int(len(removed_non_opportunity_rows)),
            "removed_wrong_direction_signal_count": int(len(removed_wrong_direction_rows)),
            "removed_correct_direction_signal_count": int(len(removed_correct_direction_rows)),
            "high_stop_pressure_removed_false_signal_count": int(len(stop_blocked_false_rows)),
            "high_stop_pressure_removed_correct_signal_count": int(len(stop_blocked_correct_rows)),
            "stop_pressure_effective_for_false_signal_reduction": bool(len(stop_blocked_false_rows) > 0),
            "stop_pressure_false_signal_precision": (
                len(stop_blocked_false_rows) / len(blocked_by_stop_rows)
                if blocked_by_stop_rows
                else 0.0
            ),
            "filter_false_signal_precision": (
                (len(removed_non_opportunity_rows) + len(removed_wrong_direction_rows))
                / len(blocked_signal_rows)
                if blocked_signal_rows
                else 0.0
            ),
            "correct_signal_retention_rate": (
                (len(original_signal_rows) - len(removed_correct_direction_rows))
                / len(original_signal_rows)
                if original_signal_rows
                else 0.0
            ),
            "entry_path_effectiveness_score": (
                (
                    (len(removed_non_opportunity_rows) + len(removed_wrong_direction_rows))
                    / len(blocked_signal_rows)
                )
                - (len(removed_correct_direction_rows) / len(original_signal_rows))
                if blocked_signal_rows and original_signal_rows
                else 0.0
            ),
            "stream_consistency_ok": bool(consistency_ok),
            "stream_consistency_delta": int(consistency_delta),
        }

        return {
            "diagnostic_name": "entry_path_prediction_filter_summary",
            "diagnostic_version": "ml38.10.16",
            "audit_stream": "final_profit_aware_gate_signal_stream",
            "gate_type": str(gate_type),
            "threshold": float(threshold),
            "entry_path_filter_enabled": any(
                bool(row.get("entry_path_filter_enabled", False)) for row in predictions
            ),
            "total_prediction_rows": int(len(predictions)),
            "original_final_signal_count": int(original_signal_count),
            "filtered_final_signal_count": int(filtered_signal_count),
            "blocked_final_signal_count": int(len(blocked_signal_rows)),
            "blocked_prediction_rows": int(len(blocked_signal_rows)),
            "passed_prediction_rows": int(filtered_signal_count),
            "blocked_prediction_rate": (
                len(blocked_signal_rows) / original_signal_count
                if original_signal_count
                else 0.0
            ),
            "blocked_by_low_entry_quality_count": int(len(blocked_by_quality_rows)),
            "blocked_by_high_stop_pressure_count": int(len(blocked_by_stop_rows)),
            "removed_false_positive_count": int(
                len(removed_non_opportunity_rows) + len(removed_wrong_direction_rows)
            ),
            "removed_true_positive_count": int(len(removed_correct_direction_rows)),
            "filter_false_signal_precision": stop_pressure_effectiveness_audit["filter_false_signal_precision"],
            "stop_pressure_false_signal_precision": stop_pressure_effectiveness_audit["stop_pressure_false_signal_precision"],
            "correct_signal_retention_rate": stop_pressure_effectiveness_audit["correct_signal_retention_rate"],
            "entry_path_effectiveness_score": stop_pressure_effectiveness_audit["entry_path_effectiveness_score"],
            "removed_non_opportunity_signal_count": int(len(removed_non_opportunity_rows)),
            "removed_wrong_direction_signal_count": int(len(removed_wrong_direction_rows)),
            "removed_correct_direction_signal_count": int(len(removed_correct_direction_rows)),
            "avg_blocked_entry_path_quality_score": _mean(blocked_signal_rows, "entry_path_quality_score"),
            "avg_passed_entry_path_quality_score": _mean(filtered_signal_rows, "entry_path_quality_score"),
            "avg_blocked_stop_pressure_risk_score": _mean(blocked_signal_rows, "stop_pressure_risk_score"),
            "avg_passed_stop_pressure_risk_score": _mean(filtered_signal_rows, "stop_pressure_risk_score"),
            "avg_blocked_mae_pressure_risk_score": _mean(blocked_signal_rows, "mae_pressure_risk_score"),
            "avg_passed_mae_pressure_risk_score": _mean(filtered_signal_rows, "mae_pressure_risk_score"),
            "stream_consistency_ok": bool(consistency_ok),
            "stream_consistency_delta": int(consistency_delta),
            "stop_pressure_effectiveness_audit": stop_pressure_effectiveness_audit,
        }

    @staticmethod
    def _resolve_ambiguous(
        take_profit_atr: float,
        stop_loss_atr: float,
        fee_r: float,
        slippage_r: float,
        same_candle_policy: str,
    ) -> dict[str, Any]:
        if same_candle_policy == "conservative":
            return ProfitAwareEvaluatorV2._with_costs("SL", -1.0, fee_r, slippage_r)
        if same_candle_policy == "optimistic":
            return ProfitAwareEvaluatorV2._with_costs("TP", take_profit_atr / stop_loss_atr, fee_r, slippage_r)
        if same_candle_policy == "skip":
            return {"result": "AMBIGUOUS", "raw_r": None, "net_r": 0.0}
        raise ValueError(f"Unsupported same_candle_policy: {same_candle_policy}")

    @staticmethod
    def _win_rate(outcomes: list[dict[str, Any]]) -> float | None:
        if not outcomes:
            return None
        return sum(int(item["result"] == "TP") for item in outcomes) / len(outcomes)

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
