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
        exit_policy_profile: str | None = None,
        exit_timeout_bars: int | None = None,
        exit_mitigation_loss_r: float | None = None,
        exit_neutral_abs_r: float | None = None,
        directional_side_filter_profile: str | None = None,
        allowed_signal_directions: tuple[str, ...] | list[str] | None = None,
    ) -> dict[str, Any]:
        evaluation = self.evaluate_predictions(
            predictions=predictions,
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
        gate_results = evaluation["gate_results"]

        report = {
            "model_version": model_version,
            "take_profit_atr": take_profit_atr,
            "stop_loss_atr": stop_loss_atr,
            "fee_r": fee_r,
            "slippage_r": slippage_r,
            "same_candle_policy": same_candle_policy,
            "exit_policy_profile": exit_policy_profile or "classic_tp_sl",
            "exit_timeout_bars": exit_timeout_bars,
            "exit_mitigation_loss_r": exit_mitigation_loss_r,
            "exit_neutral_abs_r": exit_neutral_abs_r,
            "directional_side_filter_profile": directional_side_filter_profile,
            "allowed_signal_directions": list(allowed_signal_directions or []),
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
        exit_policy_profile: str | None = None,
        exit_timeout_bars: int | None = None,
        exit_mitigation_loss_r: float | None = None,
        exit_neutral_abs_r: float | None = None,
        directional_side_filter_profile: str | None = None,
        allowed_signal_directions: tuple[str, ...] | list[str] | None = None,
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
                    exit_policy_profile=exit_policy_profile,
                    exit_timeout_bars=exit_timeout_bars,
                    exit_mitigation_loss_r=exit_mitigation_loss_r,
                    exit_neutral_abs_r=exit_neutral_abs_r,
                    directional_side_filter_profile=directional_side_filter_profile,
                    allowed_signal_directions=allowed_signal_directions,
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
        exit_policy_profile: str | None = None,
        exit_timeout_bars: int | None = None,
        exit_mitigation_loss_r: float | None = None,
        exit_neutral_abs_r: float | None = None,
        directional_side_filter_profile: str | None = None,
        allowed_signal_directions: tuple[str, ...] | list[str] | None = None,
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
        original_side_signal_rows = list(selection["signal_rows"])
        signal_rows, directional_side_filter_summary = self._apply_directional_side_filter(
            signal_rows=original_side_signal_rows,
            directional_side_filter_profile=directional_side_filter_profile,
            allowed_signal_directions=allowed_signal_directions,
        )
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
                exit_policy_profile=exit_policy_profile or "classic_tp_sl",
                exit_timeout_bars=exit_timeout_bars,
                exit_mitigation_loss_r=exit_mitigation_loss_r,
                exit_neutral_abs_r=exit_neutral_abs_r,
            )
            summary["entry_path_prediction_filter_summary"] = entry_path_filter_summary
            summary["stop_pressure_effectiveness_audit"] = stop_pressure_effectiveness_audit
            summary["directional_side_filter_summary"] = directional_side_filter_summary
            summary["directional_side_filter_profile"] = directional_side_filter_summary.get("profile")
            summary["allowed_signal_directions"] = directional_side_filter_summary.get("allowed_signal_directions")
            return {"summary": summary, "signal_rows": [], "outcomes": []}

        outcomes = [
            self._simulate_trade(
                row=row,
                take_profit_atr=take_profit_atr,
                stop_loss_atr=stop_loss_atr,
                fee_r=fee_r,
                slippage_r=slippage_r,
                same_candle_policy=same_candle_policy,
                exit_policy_profile=exit_policy_profile,
                exit_timeout_bars=exit_timeout_bars,
                exit_mitigation_loss_r=exit_mitigation_loss_r,
                exit_neutral_abs_r=exit_neutral_abs_r,
            )
            for row in signal_rows
        ]
        summary = self._build_gate_report(
            selection,
            signal_rows,
            outcomes,
            same_candle_policy,
            directional_side_filter_summary=directional_side_filter_summary,
        )
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
            exit_policy_profile=exit_policy_profile or "classic_tp_sl",
            exit_timeout_bars=exit_timeout_bars,
            exit_mitigation_loss_r=exit_mitigation_loss_r,
            exit_neutral_abs_r=exit_neutral_abs_r,
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
        exit_policy_profile: str | None = None,
        exit_timeout_bars: int | None = None,
        exit_mitigation_loss_r: float | None = None,
        exit_neutral_abs_r: float | None = None,
    ) -> dict[str, Any]:
        policy = str(exit_policy_profile or "classic_tp_sl")
        mitigation_enabled = policy in {
            "stop_loss_mitigation_v1",
            "stop_loss_mitigation_recovery_guard_v1",
        } and exit_mitigation_loss_r is not None
        recovery_guard_enabled = policy == "stop_loss_mitigation_recovery_guard_v1"
        timeout_bars = int(exit_timeout_bars or 0)
        neutral_abs_r = None if exit_neutral_abs_r is None else abs(float(exit_neutral_abs_r))
        mitigation_loss_r = None if exit_mitigation_loss_r is None else abs(float(exit_mitigation_loss_r))

        current_close = float(row["current_close"])
        atr_value = float(row["atr_14"])
        future_candles = list(row["future_candles"])
        if timeout_bars > 0:
            future_candles = future_candles[:timeout_bars]

        if row["signal_direction"] == "LONG":
            take_profit = current_close + (take_profit_atr * atr_value)
            stop_loss = current_close - (stop_loss_atr * atr_value)
            mitigation_price = (
                current_close - (mitigation_loss_r * stop_loss_atr * atr_value)
                if mitigation_enabled and mitigation_loss_r is not None
                else None
            )
            for index, candle in enumerate(future_candles):
                high = float(candle["high"])
                low = float(candle["low"])
                tp_hit = high >= take_profit
                sl_hit = low <= stop_loss
                mitigation_hit = mitigation_price is not None and low <= mitigation_price
                if tp_hit and sl_hit:
                    return self._resolve_ambiguous(
                        take_profit_atr,
                        stop_loss_atr,
                        fee_r,
                        slippage_r,
                        same_candle_policy,
                    )
                if sl_hit:
                    return self._with_costs("SL", -1.0, fee_r, slippage_r)
                if tp_hit and mitigation_hit:
                    if same_candle_policy == "optimistic":
                        return self._with_costs("TP", take_profit_atr / stop_loss_atr, fee_r, slippage_r)
                    audit = self._exit_mitigation_path_audit(
                        signal_direction="LONG",
                        remaining_candles=future_candles[index + 1:],
                        current_close=current_close,
                        atr_value=atr_value,
                        take_profit_price=take_profit,
                        stop_loss_price=stop_loss,
                        take_profit_atr=take_profit_atr,
                        stop_loss_atr=stop_loss_atr,
                    )
                    if recovery_guard_enabled and audit["exit_mitigation_path_class"].startswith("PREMATURE"):
                        continue
                    return self._with_costs("EXIT_MITIGATED", -float(mitigation_loss_r), fee_r, slippage_r, **audit)
                if tp_hit:
                    return self._with_costs("TP", take_profit_atr / stop_loss_atr, fee_r, slippage_r)
                if mitigation_hit:
                    audit = self._exit_mitigation_path_audit(
                        signal_direction="LONG",
                        remaining_candles=future_candles[index + 1:],
                        current_close=current_close,
                        atr_value=atr_value,
                        take_profit_price=take_profit,
                        stop_loss_price=stop_loss,
                        take_profit_atr=take_profit_atr,
                        stop_loss_atr=stop_loss_atr,
                    )
                    if recovery_guard_enabled and audit["exit_mitigation_path_class"].startswith("PREMATURE"):
                        continue
                    return self._with_costs("EXIT_MITIGATED", -float(mitigation_loss_r), fee_r, slippage_r, **audit)
            raw_r = self._timeout_or_horizon_raw_r(
                row=row,
                future_candles=future_candles,
                current_close=current_close,
                atr_value=atr_value,
                signal_direction="LONG",
                take_profit_atr=take_profit_atr,
                stop_loss_atr=stop_loss_atr,
            )
            if neutral_abs_r is not None and abs(raw_r) <= neutral_abs_r:
                return self._with_costs("TIMEOUT_NEUTRAL", 0.0, fee_r, slippage_r)
            return self._with_costs("NEITHER", raw_r, fee_r, slippage_r)

        take_profit = current_close - (take_profit_atr * atr_value)
        stop_loss = current_close + (stop_loss_atr * atr_value)
        mitigation_price = (
            current_close + (mitigation_loss_r * stop_loss_atr * atr_value)
            if mitigation_enabled and mitigation_loss_r is not None
            else None
        )
        for index, candle in enumerate(future_candles):
            high = float(candle["high"])
            low = float(candle["low"])
            tp_hit = low <= take_profit
            sl_hit = high >= stop_loss
            mitigation_hit = mitigation_price is not None and high >= mitigation_price
            if tp_hit and sl_hit:
                return self._resolve_ambiguous(
                    take_profit_atr,
                    stop_loss_atr,
                    fee_r,
                    slippage_r,
                    same_candle_policy,
                )
            if sl_hit:
                return self._with_costs("SL", -1.0, fee_r, slippage_r)
            if tp_hit and mitigation_hit:
                if same_candle_policy == "optimistic":
                    return self._with_costs("TP", take_profit_atr / stop_loss_atr, fee_r, slippage_r)
                audit = self._exit_mitigation_path_audit(
                    signal_direction="SHORT",
                    remaining_candles=future_candles[index + 1:],
                    current_close=current_close,
                    atr_value=atr_value,
                    take_profit_price=take_profit,
                    stop_loss_price=stop_loss,
                    take_profit_atr=take_profit_atr,
                    stop_loss_atr=stop_loss_atr,
                )
                if recovery_guard_enabled and audit["exit_mitigation_path_class"].startswith("PREMATURE"):
                    continue
                return self._with_costs("EXIT_MITIGATED", -float(mitigation_loss_r), fee_r, slippage_r, **audit)
            if tp_hit:
                return self._with_costs("TP", take_profit_atr / stop_loss_atr, fee_r, slippage_r)
            if mitigation_hit:
                audit = self._exit_mitigation_path_audit(
                    signal_direction="SHORT",
                    remaining_candles=future_candles[index + 1:],
                    current_close=current_close,
                    atr_value=atr_value,
                    take_profit_price=take_profit,
                    stop_loss_price=stop_loss,
                    take_profit_atr=take_profit_atr,
                    stop_loss_atr=stop_loss_atr,
                )
                if recovery_guard_enabled and audit["exit_mitigation_path_class"].startswith("PREMATURE"):
                    continue
                return self._with_costs("EXIT_MITIGATED", -float(mitigation_loss_r), fee_r, slippage_r, **audit)
        raw_r = self._timeout_or_horizon_raw_r(
            row=row,
            future_candles=future_candles,
            current_close=current_close,
            atr_value=atr_value,
            signal_direction="SHORT",
            take_profit_atr=take_profit_atr,
            stop_loss_atr=stop_loss_atr,
        )
        if neutral_abs_r is not None and abs(raw_r) <= neutral_abs_r:
            return self._with_costs("TIMEOUT_NEUTRAL", 0.0, fee_r, slippage_r)
        return self._with_costs("NEITHER", raw_r, fee_r, slippage_r)

    @staticmethod
    def _exit_mitigation_path_audit(
        *,
        signal_direction: str,
        remaining_candles: list[dict[str, Any]],
        current_close: float,
        atr_value: float,
        take_profit_price: float,
        stop_loss_price: float,
        take_profit_atr: float,
        stop_loss_atr: float,
    ) -> dict[str, Any]:
        max_recovery_r = 0.0
        max_adverse_r = 0.0
        first_path_event = "NO_DECISIVE_RECOVERY_OR_SL"
        signal_direction = str(signal_direction or "").upper()
        for candle in remaining_candles:
            high = float(candle.get("high", current_close) or current_close)
            low = float(candle.get("low", current_close) or current_close)
            if signal_direction == "SHORT":
                favorable_atr = max(0.0, (current_close - low) / max(atr_value, 1e-9))
                adverse_atr = max(0.0, (high - current_close) / max(atr_value, 1e-9))
                tp_recovered = low <= take_profit_price
                breakeven_recovered = low <= current_close
                full_sl_hit = high >= stop_loss_price
            else:
                favorable_atr = max(0.0, (high - current_close) / max(atr_value, 1e-9))
                adverse_atr = max(0.0, (current_close - low) / max(atr_value, 1e-9))
                tp_recovered = high >= take_profit_price
                breakeven_recovered = high >= current_close
                full_sl_hit = low <= stop_loss_price
            max_recovery_r = max(max_recovery_r, favorable_atr / max(stop_loss_atr, 1e-9))
            max_adverse_r = max(max_adverse_r, adverse_atr / max(stop_loss_atr, 1e-9))
            if full_sl_hit:
                first_path_event = "FULL_SL_AFTER_MITIGATION"
                break
            if tp_recovered:
                first_path_event = "TAKE_PROFIT_RECOVERY_AFTER_MITIGATION"
                break
            if breakeven_recovered:
                first_path_event = "BREAKEVEN_RECOVERY_AFTER_MITIGATION"
                break
        would_hit_full_sl = first_path_event == "FULL_SL_AFTER_MITIGATION"
        would_recover_to_tp = first_path_event == "TAKE_PROFIT_RECOVERY_AFTER_MITIGATION"
        would_recover_to_breakeven = first_path_event in {
            "TAKE_PROFIT_RECOVERY_AFTER_MITIGATION",
            "BREAKEVEN_RECOVERY_AFTER_MITIGATION",
        }
        if would_hit_full_sl:
            path_class = "SAVED_FULL_SL"
            recovery_risk_score = 0.0
        elif would_recover_to_tp:
            path_class = "PREMATURE_CUT_TP_RECOVERY"
            recovery_risk_score = 1.0
        elif would_recover_to_breakeven:
            path_class = "PREMATURE_CUT_BREAKEVEN_RECOVERY"
            recovery_risk_score = 0.75
        else:
            path_class = "UNRESOLVED_AFTER_MITIGATION"
            recovery_risk_score = min(0.50, max_recovery_r)
        return {
            "mitigation_path_audit_status": "COMPLETED",
            "exit_mitigation_path_class": path_class,
            "exit_mitigation_first_path_event": first_path_event,
            "would_hit_full_sl_after_mitigation": bool(would_hit_full_sl),
            "would_recover_to_breakeven_after_mitigation": bool(would_recover_to_breakeven),
            "would_recover_to_take_profit_after_mitigation": bool(would_recover_to_tp),
            "max_recovery_r_after_mitigation": float(max_recovery_r),
            "max_adverse_r_after_mitigation": float(max_adverse_r),
            "exit_mitigation_recovery_risk_score": float(recovery_risk_score),
        }

    @staticmethod
    def _timeout_or_horizon_raw_r(
        *,
        row: dict[str, Any],
        future_candles: list[dict[str, Any]],
        current_close: float,
        atr_value: float,
        signal_direction: str,
        take_profit_atr: float,
        stop_loss_atr: float,
    ) -> float:
        if future_candles:
            last_close = float(future_candles[-1].get("close", current_close) or current_close)
            move_atr = (last_close - current_close) / max(atr_value, 1e-9)
            if signal_direction == "SHORT":
                move_atr = -move_atr
        else:
            move_atr = float(row.get("future_move_atr", 0.0) or 0.0)
            if signal_direction == "SHORT":
                move_atr = -move_atr
        return max(-1.0, min(take_profit_atr / stop_loss_atr, move_atr / stop_loss_atr))

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
    def _with_costs(result: str, raw_r: float, fee_r: float, slippage_r: float, **extra: Any) -> dict[str, Any]:
        payload = {"result": result, "raw_r": raw_r, "net_r": raw_r - fee_r - slippage_r}
        payload.update(extra)
        return payload

    @staticmethod
    def _normalize_allowed_signal_directions(
        *,
        directional_side_filter_profile: str | None,
        allowed_signal_directions: tuple[str, ...] | list[str] | None,
    ) -> tuple[str, ...]:
        if allowed_signal_directions:
            normalized = tuple(
                direction
                for direction in (
                    str(item or "").upper().strip()
                    for item in allowed_signal_directions
                )
                if direction in {"LONG", "SHORT"}
            )
            if normalized:
                return tuple(dict.fromkeys(normalized))

        profile = str(directional_side_filter_profile or "").lower().strip()
        if profile in {"long_only_research", "suppress_short_research"}:
            return ("LONG",)
        if profile == "short_only_research":
            return ("SHORT",)
        return ("LONG", "SHORT")

    @staticmethod
    def _directional_side_filter_summary(
        *,
        original_signal_rows: list[dict[str, Any]],
        filtered_signal_rows: list[dict[str, Any]],
        directional_side_filter_profile: str | None,
        allowed_signal_directions: tuple[str, ...],
    ) -> dict[str, Any]:
        def _count(rows: list[dict[str, Any]], direction: str) -> int:
            return sum(
                int(str(row.get("signal_direction") or "").upper() == direction)
                for row in rows
            )

        original_long_count = _count(original_signal_rows, "LONG")
        original_short_count = _count(original_signal_rows, "SHORT")
        filtered_long_count = _count(filtered_signal_rows, "LONG")
        filtered_short_count = _count(filtered_signal_rows, "SHORT")
        original_signal_count = len(original_signal_rows)
        filtered_signal_count = len(filtered_signal_rows)
        removed_signal_count = max(0, original_signal_count - filtered_signal_count)

        profile = directional_side_filter_profile or "both_directions"
        active = set(allowed_signal_directions) != {"LONG", "SHORT"}

        return {
            "diagnostic_name": "directional_side_filter_summary",
            "diagnostic_version": "ml38.10.20",
            "profile": profile,
            "active": bool(active),
            "research_only": bool(active),
            "allowed_signal_directions": list(allowed_signal_directions),
            "original_signal_count": original_signal_count,
            "filtered_signal_count": filtered_signal_count,
            "removed_signal_count": removed_signal_count,
            "original_long_count": original_long_count,
            "original_short_count": original_short_count,
            "filtered_long_count": filtered_long_count,
            "filtered_short_count": filtered_short_count,
            "removed_long_count": max(0, original_long_count - filtered_long_count),
            "removed_short_count": max(0, original_short_count - filtered_short_count),
            "removed_signal_rate": (
                removed_signal_count / original_signal_count
                if original_signal_count
                else None
            ),
        }

    @classmethod
    def _apply_directional_side_filter(
        cls,
        *,
        signal_rows: list[dict[str, Any]],
        directional_side_filter_profile: str | None,
        allowed_signal_directions: tuple[str, ...] | list[str] | None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        allowed = cls._normalize_allowed_signal_directions(
            directional_side_filter_profile=directional_side_filter_profile,
            allowed_signal_directions=allowed_signal_directions,
        )
        filtered_rows = [
            row
            for row in signal_rows
            if str(row.get("signal_direction") or "").upper() in set(allowed)
        ]
        summary = cls._directional_side_filter_summary(
            original_signal_rows=list(signal_rows),
            filtered_signal_rows=filtered_rows,
            directional_side_filter_profile=directional_side_filter_profile,
            allowed_signal_directions=allowed,
        )
        return filtered_rows, summary

    @staticmethod
    def _directional_side_metrics(outcomes: list[dict[str, Any]]) -> dict[str, Any]:
        net_values = [float(item.get("net_r", 0.0) or 0.0) for item in outcomes]
        resolved_count = len(net_values)
        win_count = sum(int(item.get("result") == "TP") for item in outcomes)
        loss_count = sum(int(item.get("result") == "SL") for item in outcomes)
        exit_mitigated_count = sum(int(item.get("result") == "EXIT_MITIGATED") for item in outcomes)
        timeout_neutral_count = sum(int(item.get("result") == "TIMEOUT_NEUTRAL") for item in outcomes)
        gross_profit_r = sum(value for value in net_values if value > 0)
        gross_loss_r = abs(sum(value for value in net_values if value < 0))
        profit_factor = (
            gross_profit_r / gross_loss_r
            if gross_loss_r > 0
            else (float("inf") if gross_profit_r > 0 else 0.0)
        )
        total_r = sum(net_values)
        return {
            "resolved_signal_count": resolved_count,
            "win_count": win_count,
            "loss_count": loss_count,
            "exit_mitigated_count": exit_mitigated_count,
            "timeout_neutral_count": timeout_neutral_count,
            "gross_profit_r": float(gross_profit_r),
            "gross_loss_r": float(gross_loss_r),
            "profit_factor": profit_factor if resolved_count else None,
            "total_r": float(total_r),
            "avg_r": (total_r / resolved_count) if resolved_count else None,
            "win_rate": (win_count / resolved_count) if resolved_count else None,
            "loss_rate": (loss_count / resolved_count) if resolved_count else None,
        }

    @staticmethod
    def _directional_edge_bias_audit(
        resolved_rows: list[dict[str, Any]],
        resolved_outcomes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        pairs = list(zip(resolved_rows, resolved_outcomes))
        long_outcomes = [
            outcome
            for row, outcome in pairs
            if str(row.get("signal_direction") or "").upper() == "LONG"
        ]
        short_outcomes = [
            outcome
            for row, outcome in pairs
            if str(row.get("signal_direction") or "").upper() == "SHORT"
        ]
        long_metrics = ProfitAwareEvaluatorV2._directional_side_metrics(long_outcomes)
        short_metrics = ProfitAwareEvaluatorV2._directional_side_metrics(short_outcomes)

        long_count = int(long_metrics["resolved_signal_count"])
        short_count = int(short_metrics["resolved_signal_count"])
        total_count = long_count + short_count
        max_count = max(long_count, short_count)
        min_count = min(long_count, short_count)

        if total_count <= 0:
            dominant_direction = None
            dominant_direction_ratio = None
            direction_balance_ratio = None
            direction_count_imbalance_ratio = None
        else:
            if long_count > short_count:
                dominant_direction = "LONG"
            elif short_count > long_count:
                dominant_direction = "SHORT"
            else:
                dominant_direction = "BALANCED"
            dominant_direction_ratio = max_count / total_count
            direction_balance_ratio = (min_count / max_count) if max_count else None
            direction_count_imbalance_ratio = (
                (max_count / min_count) if min_count else (999.0 if max_count else None)
            )

        long_avg_r = long_metrics.get("avg_r")
        short_avg_r = short_metrics.get("avg_r")
        long_total_r = float(long_metrics.get("total_r", 0.0) or 0.0)
        short_total_r = float(short_metrics.get("total_r", 0.0) or 0.0)
        total_r = long_total_r + short_total_r

        if long_avg_r is not None and short_avg_r is not None:
            directional_profit_skew_r = abs(float(long_avg_r) - float(short_avg_r))
        else:
            directional_profit_skew_r = None
        directional_profit_skew_ratio = (
            abs(long_total_r - short_total_r) / max(abs(total_r), 1e-9)
            if total_count
            else None
        )

        warnings: list[str] = []
        if direction_balance_ratio is not None and direction_balance_ratio < 0.40:
            warnings.append("DIRECTION_COUNT_IMBALANCE")
        if (
            directional_profit_skew_r is not None
            and directional_profit_skew_r > 0.25
            and long_count > 0
            and short_count > 0
        ):
            warnings.append("DIRECTIONAL_PROFIT_SKEW")
        if (
            dominant_direction == "LONG"
            and long_avg_r is not None
            and long_avg_r < 0
            and dominant_direction_ratio
            and dominant_direction_ratio >= 0.65
        ):
            warnings.append("DOMINANT_LONG_SIDE_LOSING")
        if (
            dominant_direction == "SHORT"
            and short_avg_r is not None
            and short_avg_r < 0
            and dominant_direction_ratio
            and dominant_direction_ratio >= 0.65
        ):
            warnings.append("DOMINANT_SHORT_SIDE_LOSING")

        if not total_count:
            status = "NO_RESOLVED_SIGNALS"
        elif warnings:
            status = "DIRECTIONAL_BIAS_RISK"
        else:
            status = "OK"

        return {
            "diagnostic_name": "directional_edge_bias_audit",
            "diagnostic_version": "ml38.10.19",
            "status": status,
            "warning_count": len(warnings),
            "warnings": warnings,
            "resolved_signal_count": total_count,
            "long": long_metrics,
            "short": short_metrics,
            "long_count": long_count,
            "short_count": short_count,
            "dominant_direction": dominant_direction,
            "dominant_direction_ratio": dominant_direction_ratio,
            "direction_balance_ratio": direction_balance_ratio,
            "direction_count_imbalance_ratio": direction_count_imbalance_ratio,
            "long_avg_r": long_avg_r,
            "short_avg_r": short_avg_r,
            "long_total_r": long_total_r,
            "short_total_r": short_total_r,
            "directional_profit_skew_r": directional_profit_skew_r,
            "directional_profit_skew_ratio": directional_profit_skew_ratio,
            "directional_edge_bias_warning": bool(warnings),
        }

    @staticmethod
    def _build_gate_report(
        selection: dict[str, Any],
        signal_rows: list[dict[str, Any]],
        outcomes: list[dict[str, Any]],
        same_candle_policy: str,
        directional_side_filter_summary: dict[str, Any] | None = None,
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
        exit_mitigated_count = sum(int(item["result"] == "EXIT_MITIGATED") for item in resolved_outcomes)
        timeout_neutral_count = sum(int(item["result"] == "TIMEOUT_NEUTRAL") for item in resolved_outcomes)
        exit_mitigation_saved_full_sl_count = sum(
            int(item.get("exit_mitigation_path_class") == "SAVED_FULL_SL") for item in resolved_outcomes
        )
        exit_mitigation_premature_recovery_count = sum(
            int(str(item.get("exit_mitigation_path_class") or "").startswith("PREMATURE"))
            for item in resolved_outcomes
        )
        exit_mitigation_unresolved_count = sum(
            int(item.get("exit_mitigation_path_class") == "UNRESOLVED_AFTER_MITIGATION")
            for item in resolved_outcomes
        )
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
        directional_edge_bias_audit = ProfitAwareEvaluatorV2._directional_edge_bias_audit(
            resolved_rows=resolved_rows,
            resolved_outcomes=resolved_outcomes,
        )
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
            "exit_mitigated_count": exit_mitigated_count,
            "timeout_neutral_count": timeout_neutral_count,
            "exit_mitigation_saved_full_sl_count": exit_mitigation_saved_full_sl_count,
            "exit_mitigation_premature_recovery_count": exit_mitigation_premature_recovery_count,
            "exit_mitigation_unresolved_count": exit_mitigation_unresolved_count,
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
            "exit_mitigated_rate": (exit_mitigated_count / resolved_count) if resolved_count else None,
            "timeout_neutral_rate": (timeout_neutral_count / resolved_count) if resolved_count else None,
            "exit_mitigation_saved_full_sl_rate": (exit_mitigation_saved_full_sl_count / exit_mitigated_count) if exit_mitigated_count else None,
            "exit_mitigation_premature_recovery_rate": (exit_mitigation_premature_recovery_count / exit_mitigated_count) if exit_mitigated_count else None,
            "max_win_r": max(net_values) if net_values else None,
            "max_loss_r": min(net_values) if net_values else None,
            "long_count": len(long_rows),
            "short_count": len(short_rows),
            "long_total_r": sum(item["net_r"] for item in long_outcomes),
            "short_total_r": sum(item["net_r"] for item in short_outcomes),
            "long_win_rate": ProfitAwareEvaluatorV2._win_rate(long_outcomes),
            "short_win_rate": ProfitAwareEvaluatorV2._win_rate(short_outcomes),
            "long_avg_r": directional_edge_bias_audit.get("long_avg_r"),
            "short_avg_r": directional_edge_bias_audit.get("short_avg_r"),
            "direction_balance_ratio": directional_edge_bias_audit.get("direction_balance_ratio"),
            "direction_count_imbalance_ratio": directional_edge_bias_audit.get("direction_count_imbalance_ratio"),
            "directional_profit_skew_r": directional_edge_bias_audit.get("directional_profit_skew_r"),
            "directional_profit_skew_ratio": directional_edge_bias_audit.get("directional_profit_skew_ratio"),
            "directional_edge_bias_warning": directional_edge_bias_audit.get("directional_edge_bias_warning"),
            "dominant_direction": directional_edge_bias_audit.get("dominant_direction"),
            "dominant_direction_ratio": directional_edge_bias_audit.get("dominant_direction_ratio"),
            "directional_edge_bias_audit": directional_edge_bias_audit,
            "directional_side_filter_summary": dict(directional_side_filter_summary or {}),
            "directional_side_filter_profile": (
                dict(directional_side_filter_summary or {}).get("profile")
            ),
            "allowed_signal_directions": (
                dict(directional_side_filter_summary or {}).get("allowed_signal_directions")
            ),
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
            "exit_mitigated_count": 0,
            "timeout_neutral_count": 0,
            "exit_mitigation_saved_full_sl_count": 0,
            "exit_mitigation_premature_recovery_count": 0,
            "exit_mitigation_unresolved_count": 0,
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
            "exit_mitigated_rate": None,
            "timeout_neutral_rate": None,
            "exit_mitigation_saved_full_sl_rate": None,
            "exit_mitigation_premature_recovery_rate": None,
            "max_win_r": None,
            "max_loss_r": None,
            "long_count": 0,
            "short_count": 0,
            "long_total_r": 0.0,
            "short_total_r": 0.0,
            "long_win_rate": None,
            "short_win_rate": None,
            "long_avg_r": None,
            "short_avg_r": None,
            "direction_balance_ratio": None,
            "direction_count_imbalance_ratio": None,
            "directional_profit_skew_r": None,
            "directional_profit_skew_ratio": None,
            "directional_edge_bias_warning": False,
            "dominant_direction": None,
            "dominant_direction_ratio": None,
            "directional_edge_bias_audit": {
                "diagnostic_name": "directional_edge_bias_audit",
                "diagnostic_version": "ml38.10.19",
                "status": "NO_RESOLVED_SIGNALS",
                "warning_count": 0,
                "warnings": [],
                "resolved_signal_count": 0,
                "long_count": 0,
                "short_count": 0,
                "directional_edge_bias_warning": False,
            },
            "directional_side_filter_summary": {},
            "directional_side_filter_profile": None,
            "allowed_signal_directions": None,
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
            "status": stop_pressure_effectiveness_status,
            "total_prediction_rows": int(total),
            "original_predicted_trade_rows": int(len(predicted_trade_rows)),
            "blocked_prediction_rows": int(len(blocked_rows)),
            "blocked_original_predicted_trade_rows": int(len(blocked_predicted_trade_rows)),
            "blocked_by_low_entry_quality_count": int(len(blocked_by_quality_rows)),
            "blocked_by_high_stop_pressure_count": int(len(blocked_by_stop_rows)),
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
            "mae_pressure_threshold": next(
                (
                    row.get("entry_path_filter_mae_threshold")
                    for row in predictions
                    if row.get("entry_path_filter_mae_threshold") is not None
                ),
                None,
            ),
            "status": status,
            "original_final_signal_count": int(original_signal_count),
            "filtered_final_signal_count": int(filtered_signal_count),
            "blocked_final_signal_count": int(len(blocked_signal_rows)),
            "blocked_by_low_entry_quality_count": int(len(blocked_by_quality_rows)),
            "blocked_by_high_stop_pressure_count": int(len(blocked_by_stop_rows)),
            "blocked_by_high_mae_pressure_count": int(len(blocked_by_mae_rows)),
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
            "blocked_by_high_mae_pressure_count": int(len(blocked_by_mae_rows)),
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
