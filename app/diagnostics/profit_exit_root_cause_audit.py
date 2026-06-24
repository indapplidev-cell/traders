from __future__ import annotations

from collections import Counter
from typing import Any


class ProfitExitRootCauseAudit:
    """Diagnoses why promising opportunity signals still lose money.

    ML38.10.13: this audit works on already selected signal rows and simulated
    trade outcomes. It does not change model decisions; it only explains
    profit-aware and walk-forward failures.
    """

    diagnostic_name = "profit_exit_root_cause_audit"
    diagnostic_version = "ml38.10.18"

    def analyze(
        self,
        *,
        signal_rows: list[dict[str, Any]],
        outcomes: list[dict[str, Any]],
        take_profit_atr: float,
        stop_loss_atr: float,
        fee_r: float,
        slippage_r: float,
        same_candle_policy: str,
        gate_type: str | None = None,
        threshold: float | None = None,
        exit_policy_profile: str | None = None,
        exit_timeout_bars: int | None = None,
        exit_mitigation_loss_r: float | None = None,
        exit_neutral_abs_r: float | None = None,
    ) -> dict[str, Any]:
        rows_and_outcomes = [
            (dict(row), dict(outcome))
            for row, outcome in zip(signal_rows, outcomes)
            if dict(outcome).get("result") != "AMBIGUOUS"
        ]
        ambiguous_count = sum(
            int(dict(outcome).get("result") == "AMBIGUOUS") for outcome in outcomes
        )
        if not rows_and_outcomes:
            return {
                "diagnostic_name": self.diagnostic_name,
                "diagnostic_version": self.diagnostic_version,
                "audit_status": "NO_RESOLVED_SIGNALS",
                "gate_type": gate_type,
                "threshold": self._safe_float(threshold),
                "take_profit_atr": float(take_profit_atr),
                "stop_loss_atr": float(stop_loss_atr),
                "fee_r": float(fee_r),
                "slippage_r": float(slippage_r),
                "same_candle_policy": same_candle_policy,
                "exit_policy_profile": exit_policy_profile or "classic_tp_sl",
                "exit_timeout_bars": exit_timeout_bars,
                "exit_mitigation_loss_r": exit_mitigation_loss_r,
                "exit_neutral_abs_r": exit_neutral_abs_r,
                "signal_count": int(len(signal_rows)),
                "resolved_signal_count": 0,
                "ambiguous_count": int(ambiguous_count),
                "root_cause_status": "NO_RESOLVED_SIGNALS",
                "primary_root_cause": "no_resolved_signals",
                "recommendations": ["collect_more_resolved_profit_events"],
            }

        enriched_rows: list[dict[str, Any]] = []
        root_cause_counts: Counter[str] = Counter()
        result_counts: Counter[str] = Counter()
        direction_counts: Counter[str] = Counter()
        net_values: list[float] = []
        raw_values: list[float] = []
        mfe_values: list[float] = []
        mae_values: list[float] = []
        mfe_to_tp_values: list[float] = []
        mae_to_sl_values: list[float] = []
        losing_rows: list[dict[str, Any]] = []
        winning_rows: list[dict[str, Any]] = []

        for row, outcome in rows_and_outcomes:
            result = str(outcome.get("result") or "UNKNOWN")
            result_counts[result] += 1
            signal_direction = str(row.get("signal_direction") or "UNKNOWN")
            direction_counts[signal_direction] += 1
            raw_r = self._safe_float(outcome.get("raw_r"))
            net_r = self._safe_float(outcome.get("net_r"))
            if raw_r is not None:
                raw_values.append(raw_r)
            if net_r is not None:
                net_values.append(net_r)

            mfe_atr, mae_atr = self._mfe_mae_atr(row)
            mfe_values.append(mfe_atr)
            mae_values.append(mae_atr)
            mfe_to_tp = mfe_atr / max(float(take_profit_atr), 1e-9)
            mae_to_sl = mae_atr / max(float(stop_loss_atr), 1e-9)
            mfe_to_tp_values.append(mfe_to_tp)
            mae_to_sl_values.append(mae_to_sl)

            row_causes = self._classify_row_causes(
                result=result,
                raw_r=raw_r,
                net_r=net_r,
                mfe_to_tp=mfe_to_tp,
                mae_to_sl=mae_to_sl,
            )
            if result == "EXIT_MITIGATED":
                path_class = str(outcome.get("exit_mitigation_path_class") or "UNKNOWN")
                if path_class == "SAVED_FULL_SL":
                    row_causes.append("exit_mitigation_saved_full_sl")
                elif path_class.startswith("PREMATURE"):
                    row_causes.append("exit_mitigation_premature_recovery_cut")
                elif path_class == "UNRESOLVED_AFTER_MITIGATION":
                    row_causes.append("exit_mitigation_unresolved_path")
            for cause in row_causes:
                root_cause_counts[cause] += 1

            enriched = {
                "result": result,
                "signal_direction": signal_direction,
                "raw_r": raw_r,
                "net_r": net_r,
                "mfe_atr": float(mfe_atr),
                "mae_atr": float(mae_atr),
                "mfe_to_take_profit": float(mfe_to_tp),
                "mae_to_stop_loss": float(mae_to_sl),
                "root_causes": row_causes,
                "confidence": self._safe_float(row.get("confidence")),
                "margin": self._safe_float(row.get("margin")),
                "directional_edge": self._safe_float(row.get("directional_edge")),
                "tp_before_sl_label": row.get("tp_before_sl"),
                "exit_mitigation_path_class": outcome.get("exit_mitigation_path_class"),
                "exit_mitigation_first_path_event": outcome.get("exit_mitigation_first_path_event"),
                "would_hit_full_sl_after_mitigation": outcome.get("would_hit_full_sl_after_mitigation"),
                "would_recover_to_breakeven_after_mitigation": outcome.get("would_recover_to_breakeven_after_mitigation"),
                "would_recover_to_take_profit_after_mitigation": outcome.get("would_recover_to_take_profit_after_mitigation"),
                "max_recovery_r_after_mitigation": self._safe_float(outcome.get("max_recovery_r_after_mitigation")),
                "max_adverse_r_after_mitigation": self._safe_float(outcome.get("max_adverse_r_after_mitigation")),
                "exit_mitigation_recovery_risk_score": self._safe_float(outcome.get("exit_mitigation_recovery_risk_score")),
            }
            enriched_rows.append(enriched)
            if net_r is not None and net_r > 0.0:
                winning_rows.append(enriched)
            elif net_r is not None and net_r < 0.0:
                losing_rows.append(enriched)

        resolved_count = len(enriched_rows)
        gross_profit_r = sum(value for value in net_values if value > 0.0)
        gross_loss_r = abs(sum(value for value in net_values if value < 0.0))
        total_r = sum(net_values)
        profit_factor = (
            gross_profit_r / gross_loss_r
            if gross_loss_r > 0.0
            else (float("inf") if gross_profit_r > 0.0 else 0.0)
        )
        win_count = len(winning_rows)
        loss_count = len(losing_rows)
        exit_mitigated_count = int(result_counts.get("EXIT_MITIGATED", 0))
        timeout_neutral_count = int(result_counts.get("TIMEOUT_NEUTRAL", 0))
        exit_mitigation_path_counts: Counter[str] = Counter(
            str(row.get("exit_mitigation_path_class") or "UNKNOWN")
            for row in enriched_rows
            if str(row.get("result") or "") == "EXIT_MITIGATED"
        )
        exit_mitigation_saved_full_sl_count = int(exit_mitigation_path_counts.get("SAVED_FULL_SL", 0))
        exit_mitigation_premature_recovery_count = int(
            sum(value for key, value in exit_mitigation_path_counts.items() if key.startswith("PREMATURE"))
        )
        exit_mitigation_unresolved_count = int(exit_mitigation_path_counts.get("UNRESOLVED_AFTER_MITIGATION", 0))
        root_cause_status, primary_root_cause = self._status_and_primary_cause(
            root_cause_counts=root_cause_counts,
            result_counts=result_counts,
            total_r=total_r,
            profit_factor=profit_factor,
            resolved_count=resolved_count,
        )

        return {
            "diagnostic_name": self.diagnostic_name,
            "diagnostic_version": self.diagnostic_version,
            "audit_status": "COMPLETED",
            "gate_type": gate_type,
            "threshold": self._safe_float(threshold),
            "take_profit_atr": float(take_profit_atr),
            "stop_loss_atr": float(stop_loss_atr),
            "fee_r": float(fee_r),
            "slippage_r": float(slippage_r),
            "same_candle_policy": same_candle_policy,
            "exit_policy_profile": exit_policy_profile or "classic_tp_sl",
            "exit_timeout_bars": exit_timeout_bars,
            "exit_mitigation_loss_r": exit_mitigation_loss_r,
            "exit_neutral_abs_r": exit_neutral_abs_r,
            "signal_count": int(len(signal_rows)),
            "resolved_signal_count": int(resolved_count),
            "ambiguous_count": int(ambiguous_count),
            "win_count": int(win_count),
            "loss_count": int(loss_count),
            "exit_mitigated_count": int(exit_mitigated_count),
            "timeout_neutral_count": int(timeout_neutral_count),
            "exit_mitigation_path_counts": dict(exit_mitigation_path_counts),
            "exit_mitigation_saved_full_sl_count": int(exit_mitigation_saved_full_sl_count),
            "exit_mitigation_premature_recovery_count": int(exit_mitigation_premature_recovery_count),
            "exit_mitigation_unresolved_count": int(exit_mitigation_unresolved_count),
            "exit_mitigated_rate": exit_mitigated_count / resolved_count if resolved_count else 0.0,
            "timeout_neutral_rate": timeout_neutral_count / resolved_count if resolved_count else 0.0,
            "exit_mitigation_saved_full_sl_rate": exit_mitigation_saved_full_sl_count / exit_mitigated_count if exit_mitigated_count else 0.0,
            "exit_mitigation_premature_recovery_rate": exit_mitigation_premature_recovery_count / exit_mitigated_count if exit_mitigated_count else 0.0,
            "win_rate": win_count / resolved_count if resolved_count else 0.0,
            "loss_rate": loss_count / resolved_count if resolved_count else 0.0,
            "result_counts": dict(result_counts),
            "direction_counts": dict(direction_counts),
            "gross_profit_r": float(gross_profit_r),
            "gross_loss_r": float(gross_loss_r),
            "total_r": float(total_r),
            "profit_factor": self._finite_or_none(profit_factor),
            "avg_net_r": self._mean(net_values),
            "avg_raw_r": self._mean(raw_values),
            "avg_mfe_atr": self._mean(mfe_values),
            "avg_mae_atr": self._mean(mae_values),
            "avg_mfe_to_take_profit": self._mean(mfe_to_tp_values),
            "avg_mae_to_stop_loss": self._mean(mae_to_sl_values),
            "losing_avg_mfe_to_take_profit": self._mean(
                [row["mfe_to_take_profit"] for row in losing_rows]
            ),
            "losing_avg_mae_to_stop_loss": self._mean(
                [row["mae_to_stop_loss"] for row in losing_rows]
            ),
            "winning_avg_mfe_to_take_profit": self._mean(
                [row["mfe_to_take_profit"] for row in winning_rows]
            ),
            "winning_avg_mae_to_stop_loss": self._mean(
                [row["mae_to_stop_loss"] for row in winning_rows]
            ),
            "root_cause_counts": dict(root_cause_counts),
            "root_cause_rates": {
                key: value / resolved_count for key, value in root_cause_counts.items()
            },
            "root_cause_status": root_cause_status,
            "primary_root_cause": primary_root_cause,
            "recommendations": self._recommendations(primary_root_cause, root_cause_counts),
            "sample_losing_rows": losing_rows[:5],
        }

    def _classify_row_causes(
        self,
        *,
        result: str,
        raw_r: float | None,
        net_r: float | None,
        mfe_to_tp: float,
        mae_to_sl: float,
    ) -> list[str]:
        causes: list[str] = []
        if result == "SL":
            causes.append("stop_loss_hit")
        if result == "EXIT_MITIGATED":
            causes.append("stop_loss_mitigated_before_full_sl")
        if result == "TIMEOUT_NEUTRAL":
            causes.append("timeout_neutral_exit")
        if result == "NEITHER":
            causes.append("target_not_reached_before_horizon")
        if mfe_to_tp < 0.70:
            causes.append("insufficient_mfe_to_target")
        elif mfe_to_tp >= 0.90 and result != "TP":
            causes.append("target_nearly_reached_but_not_captured")
        if mae_to_sl >= 0.90:
            causes.append("mae_near_or_beyond_stop")
        if raw_r is not None and net_r is not None and raw_r > 0.0 >= net_r:
            causes.append("costs_flipped_positive_raw_to_negative_net")
        if net_r is not None and net_r < 0.0 and mfe_to_tp >= 0.80 and mae_to_sl >= 0.80:
            causes.append("late_entry_or_bad_risk_reward_path")
        if net_r is not None and net_r < 0.0 and not causes:
            causes.append("negative_net_r_unclassified")
        if net_r is not None and net_r > 0.0:
            causes.append("profitable_trade")
        return list(dict.fromkeys(causes))

    def _status_and_primary_cause(
        self,
        *,
        root_cause_counts: Counter[str],
        result_counts: Counter[str],
        total_r: float,
        profit_factor: float,
        resolved_count: int,
    ) -> tuple[str, str]:
        if resolved_count <= 0:
            return "NO_RESOLVED_SIGNALS", "no_resolved_signals"
        if total_r > 0.0 and profit_factor > 1.0:
            return "PROFIT_CONFIRMED", "profit_confirmed"

        stop_pressure = root_cause_counts.get("stop_loss_hit", 0) / resolved_count
        insufficient_mfe = root_cause_counts.get("insufficient_mfe_to_target", 0) / resolved_count
        late_entry = root_cause_counts.get("late_entry_or_bad_risk_reward_path", 0) / resolved_count
        target_not_reached = root_cause_counts.get("target_not_reached_before_horizon", 0) / resolved_count
        cost_drag = root_cause_counts.get("costs_flipped_positive_raw_to_negative_net", 0) / resolved_count

        if stop_pressure >= 0.35:
            return "STOP_PRESSURE_DOMINANT", "stop_loss_hit"
        if insufficient_mfe >= 0.45:
            return "TARGET_TOO_AMBITIOUS_OR_ENTRY_TOO_LATE", "insufficient_mfe_to_target"
        if late_entry >= 0.25:
            return "LATE_ENTRY_OR_BAD_RISK_REWARD", "late_entry_or_bad_risk_reward_path"
        if target_not_reached >= 0.45:
            return "HORIZON_OR_EXIT_TARGET_MISMATCH", "target_not_reached_before_horizon"
        if cost_drag >= 0.15:
            return "COST_DRAG_DOMINANT", "costs_flipped_positive_raw_to_negative_net"
        if result_counts.get("SL", 0) > result_counts.get("TP", 0):
            return "LOSS_COUNT_DOMINANT", "stop_loss_hit"
        return "NEGATIVE_PNL_REQUIRES_REVIEW", "negative_pnl_unclassified"

    @staticmethod
    def _mfe_mae_atr(row: dict[str, Any]) -> tuple[float, float]:
        current_close = float(row.get("current_close", 0.0) or 0.0)
        atr_value = max(float(row.get("atr_14", 0.0) or 0.0), 1e-9)
        future_candles = list(row.get("future_candles") or [])
        signal_direction = str(row.get("signal_direction") or "").upper()
        if not future_candles or signal_direction not in {"LONG", "SHORT"}:
            return 0.0, 0.0

        highs = [float(candle.get("high", current_close) or current_close) for candle in future_candles]
        lows = [float(candle.get("low", current_close) or current_close) for candle in future_candles]
        if signal_direction == "LONG":
            mfe = max(0.0, max(highs) - current_close) / atr_value
            mae = max(0.0, current_close - min(lows)) / atr_value
            return float(mfe), float(mae)

        mfe = max(0.0, current_close - min(lows)) / atr_value
        mae = max(0.0, max(highs) - current_close) / atr_value
        return float(mfe), float(mae)

    @staticmethod
    def _recommendations(primary_root_cause: str, root_cause_counts: Counter[str]) -> list[str]:
        recommendations: list[str] = []
        if primary_root_cause == "stop_loss_hit":
            recommendations.extend(
                [
                    "audit_stop_loss_distance_and_mae_distribution",
                    "test_exit_grid_with_wider_stop_or_stricter_entry_filter",
                    "add_mae_pressure_filter_before_runtime_acceptance",
                ]
            )
        elif primary_root_cause == "insufficient_mfe_to_target":
            recommendations.extend(
                [
                    "audit_take_profit_distance_against_mfe_distribution",
                    "test_lower_take_profit_or_horizon_specific_exit_labels",
                    "separate_opportunity_label_from_profitability_label",
                ]
            )
        elif primary_root_cause == "late_entry_or_bad_risk_reward_path":
            recommendations.extend(
                [
                    "add_entry_timing_diagnostics",
                    "compare_signal_candle_against_previous_setup_candle",
                    "test_risk_reward_path_quality_filter",
                ]
            )
        elif primary_root_cause == "costs_flipped_positive_raw_to_negative_net":
            recommendations.extend(
                [
                    "raise_min_expected_r_after_costs",
                    "include_fee_slippage_buffer_in_label_gate",
                ]
            )
        elif primary_root_cause == "target_not_reached_before_horizon":
            recommendations.extend(
                [
                    "audit_horizon_vs_target_reachability",
                    "test_higher_horizon_or_lower_take_profit_for_same_setup",
                ]
            )
        else:
            recommendations.append("review_profit_exit_root_cause_samples_before_next_label_change")

        if root_cause_counts.get("target_nearly_reached_but_not_captured", 0) > 0:
            recommendations.append("inspect_partial_take_profit_or_trailing_exit_logic_in_research_only")
        if root_cause_counts.get("stop_loss_mitigated_before_full_sl", 0) > 0:
            recommendations.append("compare_exit_mitigated_rate_against_sl_rate_and_total_r")
        if root_cause_counts.get("timeout_neutral_exit", 0) > 0:
            recommendations.append("check_timeout_neutral_exit_does_not_hide_profitable_late_moves")
        if root_cause_counts.get("exit_mitigation_premature_recovery_cut", 0) > 0:
            recommendations.append("add_recovery_risk_guard_or_delay_exit_mitigation")
        if root_cause_counts.get("exit_mitigation_saved_full_sl", 0) > 0:
            recommendations.append("separate_saved_full_sl_exits_from_premature_recovery_cuts")
        return list(dict.fromkeys(recommendations))

    @staticmethod
    def _mean(values: list[float]) -> float | None:
        if not values:
            return None
        return float(sum(values) / len(values))

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        if numeric == float("inf") or numeric == float("-inf"):
            return None
        return numeric

    @staticmethod
    def _finite_or_none(value: float) -> float | None:
        if value == float("inf") or value == float("-inf"):
            return None
        return float(value)
