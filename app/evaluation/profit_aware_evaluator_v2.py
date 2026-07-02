from __future__ import annotations

import json
from datetime import date as date_type
from datetime import datetime
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

    @staticmethod
    def _as_list(value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return list(value)
        if isinstance(value, (tuple, set)):
            return list(value)
        return [value]

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
        research_only_fold_repair_probe_enabled: bool = False,
        fold_repair_probe_profile: str | None = None,
        fold_repair_target_dates: tuple[str, ...] | list[str] | None = None,
        fold_repair_time_slice_blackout_enabled: bool = False,
        fold_repair_blackout_dates: tuple[str, ...] | list[str] | None = None,
        fold_repair_feature_filter_enabled: bool = False,
        fold_repair_feature_filter_profile: str | None = None,
        fold_repair_feature_filter_rules: dict[str, Any] | None = None,
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
            research_only_fold_repair_probe_enabled=research_only_fold_repair_probe_enabled,
            fold_repair_probe_profile=fold_repair_probe_profile,
            fold_repair_target_dates=fold_repair_target_dates,
            fold_repair_time_slice_blackout_enabled=fold_repair_time_slice_blackout_enabled,
            fold_repair_blackout_dates=fold_repair_blackout_dates,
            fold_repair_feature_filter_enabled=fold_repair_feature_filter_enabled,
            fold_repair_feature_filter_profile=fold_repair_feature_filter_profile,
            fold_repair_feature_filter_rules=fold_repair_feature_filter_rules,
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
            "research_only_fold_repair_probe_enabled": research_only_fold_repair_probe_enabled,
            "fold_repair_probe_profile": fold_repair_probe_profile,
            "fold_repair_target_dates": list(fold_repair_target_dates or []),
            "fold_repair_time_slice_blackout_enabled": fold_repair_time_slice_blackout_enabled,
            "fold_repair_blackout_dates": list(fold_repair_blackout_dates or []),
            "fold_repair_feature_filter_enabled": fold_repair_feature_filter_enabled,
            "fold_repair_feature_filter_profile": fold_repair_feature_filter_profile,
            "fold_repair_feature_filter_rules": dict(fold_repair_feature_filter_rules or {}),
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
        research_only_fold_repair_probe_enabled: bool = False,
        fold_repair_probe_profile: str | None = None,
        fold_repair_target_dates: tuple[str, ...] | list[str] | None = None,
        fold_repair_time_slice_blackout_enabled: bool = False,
        fold_repair_blackout_dates: tuple[str, ...] | list[str] | None = None,
        fold_repair_feature_filter_enabled: bool = False,
        fold_repair_feature_filter_profile: str | None = None,
        fold_repair_feature_filter_rules: dict[str, Any] | None = None,
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
                    research_only_fold_repair_probe_enabled=research_only_fold_repair_probe_enabled,
                    fold_repair_probe_profile=fold_repair_probe_profile,
                    fold_repair_target_dates=fold_repair_target_dates,
                    fold_repair_time_slice_blackout_enabled=fold_repair_time_slice_blackout_enabled,
                    fold_repair_blackout_dates=fold_repair_blackout_dates,
                    fold_repair_feature_filter_enabled=fold_repair_feature_filter_enabled,
                    fold_repair_feature_filter_profile=fold_repair_feature_filter_profile,
                    fold_repair_feature_filter_rules=fold_repair_feature_filter_rules,
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
        research_only_fold_repair_probe_enabled: bool = False,
        fold_repair_probe_profile: str | None = None,
        fold_repair_target_dates: tuple[str, ...] | list[str] | None = None,
        fold_repair_time_slice_blackout_enabled: bool = False,
        fold_repair_blackout_dates: tuple[str, ...] | list[str] | None = None,
        fold_repair_feature_filter_enabled: bool = False,
        fold_repair_feature_filter_profile: str | None = None,
        fold_repair_feature_filter_rules: dict[str, Any] | None = None,
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
        signal_rows, fold_time_slice_blackout_summary = self._apply_fold_time_slice_blackout_filter(
            signal_rows=signal_rows,
            enabled=fold_repair_time_slice_blackout_enabled,
            blackout_dates=fold_repair_blackout_dates,
            target_dates=fold_repair_target_dates,
            profile=fold_repair_probe_profile,
        )
        signal_rows, fold_feature_regime_filter_summary = self._apply_fold_feature_regime_filter(
            signal_rows=signal_rows,
            enabled=fold_repair_feature_filter_enabled,
            profile=fold_repair_feature_filter_profile,
            rules=fold_repair_feature_filter_rules,
            target_dates=fold_repair_target_dates,
            date_blackout_used=fold_repair_time_slice_blackout_enabled,
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
            summary["fold_time_slice_blackout_summary"] = fold_time_slice_blackout_summary
            summary["fold_feature_regime_filter_summary"] = fold_feature_regime_filter_summary
            summary["research_only_fold_repair_probe_enabled"] = research_only_fold_repair_probe_enabled
            summary["fold_repair_probe_profile"] = fold_repair_probe_profile
            summary["fold_repair_target_dates"] = list(fold_repair_target_dates or [])
            summary["fold_repair_time_slice_blackout_enabled"] = fold_repair_time_slice_blackout_enabled
            summary["fold_repair_blackout_dates"] = list(fold_repair_blackout_dates or [])
            summary["fold_repair_feature_filter_enabled"] = fold_repair_feature_filter_enabled
            summary["fold_repair_feature_filter_profile"] = fold_repair_feature_filter_profile
            summary["fold_repair_feature_filter_rules"] = dict(fold_repair_feature_filter_rules or {})
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
        summary["fold_time_slice_blackout_summary"] = fold_time_slice_blackout_summary
        summary["fold_feature_regime_filter_summary"] = fold_feature_regime_filter_summary
        summary["research_only_fold_repair_probe_enabled"] = research_only_fold_repair_probe_enabled
        summary["fold_repair_probe_profile"] = fold_repair_probe_profile
        summary["fold_repair_target_dates"] = list(fold_repair_target_dates or [])
        summary["fold_repair_time_slice_blackout_enabled"] = fold_repair_time_slice_blackout_enabled
        summary["fold_repair_blackout_dates"] = list(fold_repair_blackout_dates or [])
        summary["fold_repair_feature_filter_enabled"] = fold_repair_feature_filter_enabled
        summary["fold_repair_feature_filter_profile"] = fold_repair_feature_filter_profile
        summary["fold_repair_feature_filter_rules"] = dict(fold_repair_feature_filter_rules or {})
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
    def _extract_signal_date_static(row: dict[str, Any]) -> str | None:
        for key in (
            "signal_date",
            "date",
            "timestamp",
            "datetime",
            "open_time",
            "time",
            "candle_open_time",
            "signal_time",
            "entry_time",
        ):
            value = row.get(key)
            if value is None:
                continue
            if isinstance(value, datetime):
                return value.date().isoformat()
            if isinstance(value, date_type):
                return value.isoformat()
            text = str(value).strip()
            if not text:
                continue
            if len(text) >= 10 and text[4] == "-" and text[7] == "-":
                return text[:10]
            try:
                return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
            except ValueError:
                continue
        return None

    @staticmethod
    def _extract_signal_date(row: dict[str, Any]) -> str | None:
        return ProfitAwareEvaluatorV2._extract_signal_date_static(row)

    def _apply_fold_time_slice_blackout_filter(
        self,
        *,
        signal_rows: list[dict[str, Any]],
        enabled: bool,
        blackout_dates: tuple[str, ...] | list[str] | None,
        target_dates: tuple[str, ...] | list[str] | None,
        profile: str | None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        normalized_blackout_dates = tuple(
            dict.fromkeys(
                date_text
                for date_text in (str(item).strip() for item in (blackout_dates or []))
                if date_text
            )
        )
        normalized_target_dates = tuple(
            dict.fromkeys(
                date_text
                for date_text in (str(item).strip() for item in (target_dates or []))
                if date_text
            )
        )
        if not enabled or not normalized_blackout_dates:
            summary = {
                "diagnostic_name": "fold_time_slice_blackout_summary",
                "diagnostic_version": "ml38.10.27",
                "enabled": False,
                "profile": profile,
                "target_dates": list(normalized_target_dates),
                "blackout_dates": list(normalized_blackout_dates),
                "input_signal_count": len(signal_rows),
                "output_signal_count": len(signal_rows),
                "removed_signal_count": 0,
                "removed_ratio": 0.0 if signal_rows else None,
                "removed_counts_by_date": {},
            }
            return list(signal_rows), summary

        blackout_set = set(normalized_blackout_dates)
        filtered_rows: list[dict[str, Any]] = []
        removed_counts_by_date: dict[str, int] = {}
        for row in signal_rows:
            signal_date = self._extract_signal_date(row)
            if signal_date is not None and signal_date in blackout_set:
                removed_counts_by_date[signal_date] = removed_counts_by_date.get(signal_date, 0) + 1
                continue
            filtered_rows.append(row)

        removed_signal_count = max(0, len(signal_rows) - len(filtered_rows))
        summary = {
            "diagnostic_name": "fold_time_slice_blackout_summary",
            "diagnostic_version": "ml38.10.27",
            "enabled": True,
            "profile": profile,
            "target_dates": list(normalized_target_dates),
            "blackout_dates": list(normalized_blackout_dates),
            "input_signal_count": len(signal_rows),
            "output_signal_count": len(filtered_rows),
            "removed_signal_count": removed_signal_count,
            "removed_ratio": (removed_signal_count / len(signal_rows)) if signal_rows else None,
            "removed_counts_by_date": removed_counts_by_date,
        }
        return filtered_rows, summary

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _row_metric_float(cls, row: dict[str, Any], *keys: str) -> float | None:
        for key in keys:
            if key in row and row.get(key) is not None:
                return cls._float_or_none(row.get(key))
        return None

    @staticmethod
    def _feature_flag_active(features_json: dict[str, Any], key: str) -> bool:
        try:
            return float(features_json.get(key, 0.0) or 0.0) >= 0.5
        except (TypeError, ValueError):
            return False

    @classmethod
    def _row_regime_value(cls, row: dict[str, Any]) -> str | None:
        for key in ("market_regime", "regime_bucket", "feature_regime_bucket"):
            value = row.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text

        features_json = row.get("features_json")
        if isinstance(features_json, dict):
            for feature_key, regime_name in (
                ("regime_trend_up", "trend_up"),
                ("regime_trend_down", "trend_down"),
                ("regime_range", "range"),
                ("regime_high_volatility", "high_volatility"),
                ("regime_low_volatility", "low_volatility"),
                ("regime_unknown", "unknown"),
            ):
                if cls._feature_flag_active(features_json, feature_key):
                    return regime_name

        return None

    @classmethod
    def _row_regime_values(cls, row: dict[str, Any]) -> tuple[str, ...]:
        values: list[str] = []
        primary = cls._row_regime_value(row)
        if primary:
            values.append(primary)

        raw_flags = row.get("active_regime_flags") or ()
        if isinstance(raw_flags, str):
            raw_flags = [raw_flags]
        for item in raw_flags:
            text = str(item).strip()
            if text:
                values.append(text)

        features_json = row.get("features_json")
        if isinstance(features_json, dict):
            for feature_key, regime_name in (
                ("regime_trend_up", "trend_up"),
                ("regime_trend_down", "trend_down"),
                ("regime_range", "range"),
                ("regime_high_volatility", "high_volatility"),
                ("regime_low_volatility", "low_volatility"),
                ("regime_unknown", "unknown"),
                ("regime_volatility_expanding", "volatility_expanding"),
                ("regime_volatility_contracting", "volatility_contracting"),
            ):
                if cls._feature_flag_active(features_json, feature_key):
                    values.append(regime_name)

        return tuple(dict.fromkeys(values))

    @staticmethod
    def _bucket_numeric(value: float | None) -> str:
        if value is None:
            return "missing"
        if value < 0.40:
            return "<0.40"
        if value < 0.50:
            return "0.40-0.49"
        if value < 0.60:
            return "0.50-0.59"
        if value < 0.70:
            return "0.60-0.69"
        if value < 0.80:
            return "0.70-0.79"
        return ">=0.80"

    @classmethod
    def _feature_filter_bucket_snapshot(cls, row: dict[str, Any]) -> dict[str, Any]:
        entry_quality = cls._row_metric_float(
            row,
            "entry_path_quality_score",
            "entry_path_score",
            "entry_quality_score",
        )
        setup_quality = cls._row_metric_float(
            row,
            "setup_quality_score",
            "setup_quality",
        )
        stop_pressure = cls._row_metric_float(
            row,
            "stop_pressure_risk_score",
            "stop_pressure_score",
            "stop_pressure",
        )
        mae_pressure = cls._row_metric_float(
            row,
            "mae_pressure_risk_score",
            "mae_pressure_score",
            "mae_pressure",
            "mae_adverse_excursion_score",
        )
        regime = cls._row_regime_value(row) or "missing"
        active_regime_flags = list(cls._row_regime_values(row))
        return {
            "signal_date": cls._extract_signal_date_static(row),
            "signal_direction": str(row.get("signal_direction") or "").upper() or None,
            "regime": regime,
            "market_regime": regime,
            "regime_bucket": row.get("regime_bucket") or regime,
            "feature_regime_bucket": row.get("feature_regime_bucket") or regime,
            "market_regime_source": row.get("market_regime_source"),
            "active_regime_flags": active_regime_flags,
            "entry_path_quality_score": entry_quality,
            "setup_quality_score": setup_quality,
            "stop_pressure_risk_score": stop_pressure,
            "mae_pressure_risk_score": mae_pressure,
            "entry_path_quality_bucket": cls._bucket_numeric(entry_quality),
            "setup_quality_bucket": cls._bucket_numeric(setup_quality),
            "stop_pressure_bucket": cls._bucket_numeric(stop_pressure),
            "mae_pressure_bucket": cls._bucket_numeric(mae_pressure),
        }

    @staticmethod
    def _increment_count(target: dict[str, int], key: Any) -> None:
        normalized_key = str(key).strip() if key is not None else ""
        bucket = normalized_key or "missing"
        target[bucket] = target.get(bucket, 0) + 1

    @staticmethod
    def _limited_append(target: list[dict[str, Any]], value: dict[str, Any], *, limit: int) -> None:
        if len(target) < limit:
            target.append(dict(value))

    def _apply_fold_feature_regime_filter(
        self,
        *,
        signal_rows: list[dict[str, Any]],
        enabled: bool,
        profile: str | None,
        rules: dict[str, Any] | None,
        target_dates: tuple[str, ...] | list[str] | None,
        date_blackout_used: bool,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        normalized_rules = dict(rules or {})
        normalized_target_dates = [
            str(item).strip() for item in (target_dates or []) if str(item).strip()
        ]
        target_date_set = set(normalized_target_dates)

        blocked_regime_values = {
            str(item).strip().lower()
            for item in self._as_list(normalized_rules.get("blocked_regime_values"))
            if str(item).strip()
        }
        missing_feature_policy = str(
            normalized_rules.get("missing_feature_policy") or "pass_with_warning"
        ).strip().lower()
        base_summary = {
            "diagnostic_name": "fold_feature_regime_filter_summary",
            "diagnostic_version": "ml38.10.29",
            "enabled": bool(enabled),
            "profile": profile,
            "rules": normalized_rules,
            "target_dates": normalized_target_dates,
            "date_blackout_used": bool(date_blackout_used),
            "input_signal_count": len(signal_rows),
        }

        if not enabled or not normalized_rules:
            summary = {
                **base_summary,
                "output_signal_count": len(signal_rows),
                "removed_signal_count": 0,
                "removed_ratio": 0.0 if signal_rows else None,
                "target_date_input_count": 0,
                "target_date_removed_count": 0,
                "target_date_passed_count": 0,
                "primary_removed_counts_by_reason": {},
                "matched_removed_counts_by_reason": {},
                "removed_counts_by_date": {},
                "passed_counts_by_date": {},
                "removed_counts_by_regime": {},
                "passed_counts_by_regime": {},
                "removed_counts_by_active_regime_flag": {},
                "passed_counts_by_active_regime_flag": {},
                "regime_source_counts": {},
                "market_regime_present_count": len(signal_rows),
                "market_regime_missing_count": 0,
                "removed_counts_by_entry_path_quality_bucket": {},
                "removed_counts_by_setup_quality_bucket": {},
                "removed_counts_by_stop_pressure_bucket": {},
                "removed_counts_by_mae_pressure_bucket": {},
                "missing_feature_counts": {},
                "removed_signal_examples": [],
                "passed_target_date_signal_examples": [],
                "warnings": [],
            }
            return list(signal_rows), summary

        filtered_rows: list[dict[str, Any]] = []
        primary_removed_counts_by_reason: dict[str, int] = {}
        matched_removed_counts_by_reason: dict[str, int] = {}
        removed_counts_by_date: dict[str, int] = {}
        passed_counts_by_date: dict[str, int] = {}
        removed_counts_by_regime: dict[str, int] = {}
        passed_counts_by_regime: dict[str, int] = {}
        removed_counts_by_active_regime_flag: dict[str, int] = {}
        passed_counts_by_active_regime_flag: dict[str, int] = {}
        regime_source_counts: dict[str, int] = {}
        removed_counts_by_entry_path_quality_bucket: dict[str, int] = {}
        removed_counts_by_setup_quality_bucket: dict[str, int] = {}
        removed_counts_by_stop_pressure_bucket: dict[str, int] = {}
        removed_counts_by_mae_pressure_bucket: dict[str, int] = {}
        missing_feature_counts: dict[str, int] = {}
        removed_signal_examples: list[dict[str, Any]] = []
        passed_target_date_signal_examples: list[dict[str, Any]] = []

        def record_missing(name: str) -> None:
            missing_feature_counts[name] = missing_feature_counts.get(name, 0) + 1

        def metric_value(
            row: dict[str, Any],
            keys: tuple[str, ...],
            missing_name: str,
        ) -> float | None:
            value = self._row_metric_float(row, *keys)
            if value is None:
                record_missing(missing_name)
            return value

        def collect_block_reasons(row: dict[str, Any]) -> list[str]:
            reasons: list[str] = []

            entry_quality = metric_value(
                row,
                ("entry_path_quality_score", "entry_path_score", "entry_quality_score"),
                "entry_path_quality_score",
            )
            min_entry_quality = self._float_or_none(
                normalized_rules.get("min_entry_path_quality_score")
            )
            if min_entry_quality is not None and entry_quality is not None and entry_quality < min_entry_quality:
                reasons.append("low_entry_path_quality")

            setup_quality = metric_value(
                row,
                ("setup_quality_score", "setup_quality"),
                "setup_quality_score",
            )
            min_setup_quality = self._float_or_none(
                normalized_rules.get("min_setup_quality_score")
            )
            if min_setup_quality is not None and setup_quality is not None and setup_quality < min_setup_quality:
                reasons.append("low_setup_quality")

            stop_pressure = metric_value(
                row,
                ("stop_pressure_risk_score", "stop_pressure_score", "stop_pressure"),
                "stop_pressure_risk_score",
            )
            max_stop_pressure = self._float_or_none(
                normalized_rules.get("max_stop_pressure_risk_score")
            )
            if max_stop_pressure is not None and stop_pressure is not None and stop_pressure > max_stop_pressure:
                reasons.append("high_stop_pressure")

            mae_pressure = metric_value(
                row,
                (
                    "mae_pressure_risk_score",
                    "mae_pressure_score",
                    "mae_pressure",
                    "mae_adverse_excursion_score",
                ),
                "mae_pressure_risk_score",
            )
            max_mae_pressure = self._float_or_none(
                normalized_rules.get("max_mae_pressure_risk_score")
            )
            if max_mae_pressure is not None and mae_pressure is not None and mae_pressure > max_mae_pressure:
                reasons.append("high_mae_pressure")

            regime_values = self._row_regime_values(row)
            if not regime_values:
                record_missing("market_regime")
            elif blocked_regime_values:
                normalized_regime_values = {
                    str(value).strip().lower()
                    for value in regime_values
                    if str(value).strip()
                }
                if normalized_regime_values.intersection(blocked_regime_values):
                    reasons.append("blocked_regime")

            return list(dict.fromkeys(reasons))

        target_date_input_count = 0
        target_date_removed_count = 0
        target_date_passed_count = 0

        for row in signal_rows:
            signal_date = self._extract_signal_date(row)
            if signal_date in target_date_set:
                target_date_input_count += 1

            bucket_snapshot = self._feature_filter_bucket_snapshot(row)
            block_reasons = collect_block_reasons(row)
            self._increment_count(
                regime_source_counts,
                bucket_snapshot.get("market_regime_source") or "missing",
            )
            active_flags = bucket_snapshot.get("active_regime_flags") or []

            if block_reasons:
                primary_reason = block_reasons[0]
                self._increment_count(primary_removed_counts_by_reason, primary_reason)
                for reason in block_reasons:
                    self._increment_count(matched_removed_counts_by_reason, reason)

                self._increment_count(removed_counts_by_date, signal_date or "missing")
                self._increment_count(removed_counts_by_regime, bucket_snapshot.get("regime"))
                for flag in active_flags:
                    self._increment_count(removed_counts_by_active_regime_flag, flag)
                self._increment_count(
                    removed_counts_by_entry_path_quality_bucket,
                    bucket_snapshot.get("entry_path_quality_bucket"),
                )
                self._increment_count(
                    removed_counts_by_setup_quality_bucket,
                    bucket_snapshot.get("setup_quality_bucket"),
                )
                self._increment_count(
                    removed_counts_by_stop_pressure_bucket,
                    bucket_snapshot.get("stop_pressure_bucket"),
                )
                self._increment_count(
                    removed_counts_by_mae_pressure_bucket,
                    bucket_snapshot.get("mae_pressure_bucket"),
                )

                if signal_date in target_date_set:
                    target_date_removed_count += 1

                self._limited_append(
                    removed_signal_examples,
                    {
                        **bucket_snapshot,
                        "primary_reason": primary_reason,
                        "matched_reasons": block_reasons,
                    },
                    limit=20,
                )
                continue

            filtered_rows.append(row)
            self._increment_count(passed_counts_by_date, signal_date or "missing")
            self._increment_count(passed_counts_by_regime, bucket_snapshot.get("regime"))
            for flag in active_flags:
                self._increment_count(passed_counts_by_active_regime_flag, flag)

            if signal_date in target_date_set:
                target_date_passed_count += 1
                self._limited_append(
                    passed_target_date_signal_examples,
                    bucket_snapshot,
                    limit=20,
                )

        warnings: list[str] = []
        if missing_feature_counts:
            warnings.append("feature_filter_missing_features_passed_with_warning")
        if missing_feature_policy != "pass_with_warning":
            warnings.append("unsupported_missing_feature_policy_fell_back_to_pass_with_warning")

        removed_signal_count = max(0, len(signal_rows) - len(filtered_rows))
        summary = {
            **base_summary,
            "output_signal_count": len(filtered_rows),
            "removed_signal_count": removed_signal_count,
            "removed_ratio": (removed_signal_count / len(signal_rows)) if signal_rows else None,
            "target_date_input_count": target_date_input_count,
            "target_date_removed_count": target_date_removed_count,
            "target_date_passed_count": target_date_passed_count,
            "primary_removed_counts_by_reason": primary_removed_counts_by_reason,
            "matched_removed_counts_by_reason": matched_removed_counts_by_reason,
            "removed_counts_by_reason": primary_removed_counts_by_reason,
            "removed_counts_by_date": removed_counts_by_date,
            "passed_counts_by_date": passed_counts_by_date,
            "removed_counts_by_regime": removed_counts_by_regime,
            "passed_counts_by_regime": passed_counts_by_regime,
            "removed_counts_by_active_regime_flag": removed_counts_by_active_regime_flag,
            "passed_counts_by_active_regime_flag": passed_counts_by_active_regime_flag,
            "regime_source_counts": regime_source_counts,
            "market_regime_present_count": (
                len(signal_rows) - missing_feature_counts.get("market_regime", 0)
            ),
            "market_regime_missing_count": missing_feature_counts.get("market_regime", 0),
            "removed_counts_by_entry_path_quality_bucket": removed_counts_by_entry_path_quality_bucket,
            "removed_counts_by_setup_quality_bucket": removed_counts_by_setup_quality_bucket,
            "removed_counts_by_stop_pressure_bucket": removed_counts_by_stop_pressure_bucket,
            "removed_counts_by_mae_pressure_bucket": removed_counts_by_mae_pressure_bucket,
            "missing_feature_counts": missing_feature_counts,
            "removed_signal_examples": removed_signal_examples,
            "passed_target_date_signal_examples": passed_target_date_signal_examples,
            "warnings": warnings,
        }
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
