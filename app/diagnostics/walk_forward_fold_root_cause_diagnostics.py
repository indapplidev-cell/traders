from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any


class WalkForwardFoldRootCauseDiagnostics:
    diagnostic_name = "walk_forward_fold_total_r_root_cause"
    diagnostic_version = "ml38.10.26"

    MAX_GROUP_ROWS = 8
    MAX_SAMPLE_LOSSES = 8

    def analyze(
        self,
        *,
        fold: dict[str, Any],
        gate: dict[str, Any],
        signal_rows: list[dict[str, Any]],
        outcomes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        combined = self._combined_rows(signal_rows=signal_rows, outcomes=outcomes)
        total_r = sum(self._float(row.get("net_r"), 0.0) for row in combined)
        loss_rows = [row for row in combined if self._float(row.get("net_r"), 0.0) < 0.0]
        win_rows = [row for row in combined if self._float(row.get("net_r"), 0.0) > 0.0]

        outcome_counts = Counter(str(row.get("result") or "UNKNOWN") for row in combined)
        direction_summary = self._group_summary(combined, key_name="signal_direction")
        outcome_summary = self._group_summary(combined, key_name="result")
        time_slice_summary = self._time_slice_summary(combined)
        regime_summary = self._first_existing_group_summary(
            combined,
            keys=(
                "market_regime",
                "regime",
                "regime_label",
                "runtime_regime_label",
                "trend_regime",
            ),
            fallback_key="UNKNOWN_REGIME",
        )
        entry_path_summary = self._first_existing_group_summary(
            combined,
            keys=(
                "entry_path",
                "entry_path_bucket",
                "entry_path_type",
                "entry_path_quality_bucket",
                "entry_path_final_decision",
                "entry_path_filter_reason",
            ),
            fallback_key="UNKNOWN_ENTRY_PATH",
        )
        setup_quality_summary = self._numeric_bucket_summary(
            combined,
            keys=(
                "setup_quality_score",
                "setup_quality",
                "setup_quality_decision_score",
                "entry_path_quality_score",
            ),
            bucket_name="setup_quality_bucket",
        )
        stop_pressure_summary = self._numeric_bucket_summary(
            combined,
            keys=(
                "stop_pressure_risk_score",
                "stop_pressure_score",
                "stop_pressure_effectiveness_score",
            ),
            bucket_name="stop_pressure_bucket",
        )
        mae_pressure_summary = self._numeric_bucket_summary(
            combined,
            keys=(
                "mae_pressure_risk_score",
                "mae_pressure_score",
                "entry_path_filter_mae_pressure_risk_score",
            ),
            bucket_name="mae_pressure_bucket",
        )

        root_cause_flags = self._root_cause_flags(
            total_r=total_r,
            signal_count=len(combined),
            loss_rows=loss_rows,
            win_rows=win_rows,
            outcome_counts=outcome_counts,
            time_slice_summary=time_slice_summary,
            regime_summary=regime_summary,
            entry_path_summary=entry_path_summary,
            setup_quality_summary=setup_quality_summary,
            stop_pressure_summary=stop_pressure_summary,
            mae_pressure_summary=mae_pressure_summary,
        )

        return {
            "diagnostic_name": self.diagnostic_name,
            "diagnostic_version": self.diagnostic_version,
            "diagnostic_status": "COMPLETED" if combined else "NO_SIGNAL_ROWS",
            "fold_index": fold.get("fold_index"),
            "train_start": fold.get("train_start"),
            "train_end": fold.get("train_end"),
            "validation_start": fold.get("validation_start"),
            "validation_end": fold.get("validation_end"),
            "test_start": fold.get("test_start"),
            "test_end": fold.get("test_end"),
            "gate_type": gate.get("gate_type"),
            "threshold": gate.get("threshold"),
            "validation_signal_count": len(combined),
            "validation_total_r": total_r,
            "validation_win_count": len(win_rows),
            "validation_loss_count": len(loss_rows),
            "validation_loss_rate": (len(loss_rows) / len(combined)) if combined else 0.0,
            "outcome_counts": dict(outcome_counts),
            "direction_summary": direction_summary,
            "outcome_summary": outcome_summary,
            "time_slice_summary": time_slice_summary,
            "regime_summary": regime_summary,
            "entry_path_summary": entry_path_summary,
            "setup_quality_summary": setup_quality_summary,
            "stop_pressure_summary": stop_pressure_summary,
            "mae_pressure_summary": mae_pressure_summary,
            "root_cause_flags": root_cause_flags,
            "primary_root_cause": root_cause_flags[0] if root_cause_flags else None,
            "sample_losing_trades": self._sample_losses(loss_rows),
            "recommendations": self._recommendations(root_cause_flags),
        }

    def summarize_many(self, diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
        items = [dict(item) for item in diagnostics if isinstance(item, dict)]
        status_counts = Counter(str(item.get("diagnostic_status") or "UNKNOWN") for item in items)
        primary_counts = Counter(
            str(item.get("primary_root_cause") or "UNKNOWN")
            for item in items
        )
        worst = min(
            items,
            key=lambda item: self._float(item.get("validation_total_r"), 0.0),
            default=None,
        )
        return {
            "diagnostic_name": "walk_forward_fold_total_r_root_cause_summary",
            "diagnostic_version": self.diagnostic_version,
            "diagnostic_status": "COMPLETED" if items else "NO_ROOT_CAUSE_DIAGNOSTICS",
            "root_cause_fold_count": len(items),
            "status_counts": dict(status_counts),
            "primary_root_cause_counts": dict(primary_counts),
            "worst_fold_root_cause": worst,
            "recommendations": self._summary_recommendations(primary_counts),
        }

    def _combined_rows(
        self,
        *,
        signal_rows: list[dict[str, Any]],
        outcomes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for index, row in enumerate(signal_rows):
            signal = dict(row) if isinstance(row, dict) else {}
            outcome = dict(outcomes[index]) if index < len(outcomes) and isinstance(outcomes[index], dict) else {}
            merged = {**signal, **outcome}
            merged["_signal_index"] = index
            result.append(merged)
        return result

    def _group_summary(self, rows: list[dict[str, Any]], *, key_name: str) -> list[dict[str, Any]]:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            groups[str(row.get(key_name) or "UNKNOWN")].append(row)
        return self._rows_from_groups(groups, group_key_name=key_name)

    def _first_existing_group_summary(
        self,
        rows: list[dict[str, Any]],
        *,
        keys: tuple[str, ...],
        fallback_key: str,
    ) -> list[dict[str, Any]]:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        selected_key = fallback_key
        for row in rows:
            selected_value = None
            for key in keys:
                value = row.get(key)
                if value not in (None, ""):
                    selected_key = key
                    selected_value = value
                    break
            groups[str(selected_value or "UNKNOWN")].append(row)
        return self._rows_from_groups(groups, group_key_name=selected_key)

    def _numeric_bucket_summary(
        self,
        rows: list[dict[str, Any]],
        *,
        keys: tuple[str, ...],
        bucket_name: str,
    ) -> list[dict[str, Any]]:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            value = None
            for key in keys:
                if row.get(key) is not None:
                    value = self._float(row.get(key), None)
                    break
            groups[self._numeric_bucket(value)].append(row)
        return self._rows_from_groups(groups, group_key_name=bucket_name)

    def _time_slice_summary(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not rows:
            return []
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        count = len(rows)
        for index, row in enumerate(rows):
            timestamp = self._timestamp_value(row)
            if timestamp:
                bucket = timestamp[:10]
            else:
                ratio = index / max(count - 1, 1)
                if ratio < 1 / 3:
                    bucket = "EARLY_VALIDATION"
                elif ratio < 2 / 3:
                    bucket = "MID_VALIDATION"
                else:
                    bucket = "LATE_VALIDATION"
            groups[bucket].append(row)
        return self._rows_from_groups(groups, group_key_name="time_slice")

    def _rows_from_groups(
        self,
        groups: dict[str, list[dict[str, Any]]],
        *,
        group_key_name: str,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for key, items in groups.items():
            total_r = sum(self._float(item.get("net_r"), 0.0) for item in items)
            loss_count = sum(1 for item in items if self._float(item.get("net_r"), 0.0) < 0.0)
            win_count = sum(1 for item in items if self._float(item.get("net_r"), 0.0) > 0.0)
            rows.append(
                {
                    group_key_name: key,
                    "signal_count": len(items),
                    "total_r": total_r,
                    "avg_r": total_r / len(items) if items else None,
                    "win_count": win_count,
                    "loss_count": loss_count,
                    "loss_rate": loss_count / len(items) if items else 0.0,
                    "outcome_counts": dict(Counter(str(item.get("result") or "UNKNOWN") for item in items)),
                }
            )
        return sorted(rows, key=lambda item: (self._float(item.get("total_r"), 0.0), -int(item.get("signal_count", 0))))[: self.MAX_GROUP_ROWS]

    def _root_cause_flags(
        self,
        *,
        total_r: float,
        signal_count: int,
        loss_rows: list[dict[str, Any]],
        win_rows: list[dict[str, Any]],
        outcome_counts: Counter[str],
        time_slice_summary: list[dict[str, Any]],
        regime_summary: list[dict[str, Any]],
        entry_path_summary: list[dict[str, Any]],
        setup_quality_summary: list[dict[str, Any]],
        stop_pressure_summary: list[dict[str, Any]],
        mae_pressure_summary: list[dict[str, Any]],
    ) -> list[str]:
        flags: list[str] = []
        if signal_count == 0:
            flags.append("no_validation_signals_for_best_failed_gate")
        if total_r < -3.0:
            flags.append("large_negative_validation_total_r")
        if loss_rows and len(loss_rows) > len(win_rows):
            flags.append("loss_count_exceeds_win_count")
        if outcome_counts.get("SL", 0) + outcome_counts.get("EXIT_MITIGATED", 0) >= max(len(loss_rows), 1) * 0.6:
            flags.append("stop_or_mitigation_loss_dominates")
        if self._worst_bucket_total_r(time_slice_summary) <= min(total_r * 0.5, -1.0):
            flags.append("losses_concentrated_in_time_slice")
        if self._worst_bucket_total_r(regime_summary) <= min(total_r * 0.5, -1.0):
            flags.append("losses_concentrated_in_regime_bucket")
        if self._worst_bucket_total_r(entry_path_summary) <= min(total_r * 0.5, -1.0):
            flags.append("losses_concentrated_in_entry_path_bucket")
        if self._bucket_has_negative(setup_quality_summary, "LOW"):
            flags.append("low_setup_quality_bucket_negative")
        if self._bucket_has_negative(stop_pressure_summary, "HIGH"):
            flags.append("high_stop_pressure_bucket_negative")
        if self._bucket_has_negative(mae_pressure_summary, "HIGH"):
            flags.append("high_mae_pressure_bucket_negative")
        if not flags and total_r < 0:
            flags.append("negative_total_r_without_metadata_concentration")
        return list(dict.fromkeys(flags))

    def _sample_losses(self, loss_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        sample = sorted(loss_rows, key=lambda row: self._float(row.get("net_r"), 0.0))[: self.MAX_SAMPLE_LOSSES]
        keys = (
            "_signal_index",
            "result",
            "net_r",
            "signal_direction",
            "current_close",
            "atr_14",
            "entry_path",
            "entry_path_bucket",
            "entry_path_filter_reason",
            "setup_quality_score",
            "stop_pressure_risk_score",
            "mae_pressure_risk_score",
            "market_regime",
            "regime",
            "regime_label",
        )
        return [
            {key: row.get(key) for key in keys if key in row}
            for row in sample
        ]

    def _recommendations(self, flags: list[str]) -> list[str]:
        recommendations = ["keep_total_r_repair_research_only_until_fold_root_cause_is_fixed"]
        if "losses_concentrated_in_time_slice" in flags:
            recommendations.append("inspect_validation_time_slice_for_regime_shift_or_event_cluster")
        if "losses_concentrated_in_regime_bucket" in flags:
            recommendations.append("add_regime_specific_filter_or_regime_aware_threshold_probe")
        if "losses_concentrated_in_entry_path_bucket" in flags:
            recommendations.append("add_entry_path_bucket_repair_or_entry_path_exclusion_probe")
        if "low_setup_quality_bucket_negative" in flags:
            recommendations.append("raise_setup_quality_threshold_for_side_filtered_research")
        if "high_stop_pressure_bucket_negative" in flags or "high_mae_pressure_bucket_negative" in flags:
            recommendations.append("tighten_stop_or_mae_pressure_filter_for_validation_fold")
        if "stop_or_mitigation_loss_dominates" in flags:
            recommendations.append("inspect_exit_mitigation_and_stop_pressure_interaction")
        return list(dict.fromkeys(recommendations))

    def _summary_recommendations(self, primary_counts: Counter[str]) -> list[str]:
        recommendations = ["inspect_worst_fold_root_cause_before_more_threshold_relaxation"]
        if primary_counts.get("large_negative_validation_total_r", 0):
            recommendations.append("do_not_fix_large_negative_fold_by_threshold_only")
        if primary_counts.get("losses_concentrated_in_regime_bucket", 0):
            recommendations.append("consider_regime_time_slice_repair_stage")
        return list(dict.fromkeys(recommendations))

    def _timestamp_value(self, row: dict[str, Any]) -> str | None:
        for key in ("open_time", "candle_open_time", "current_open_time", "timestamp", "time"):
            value = row.get(key)
            if value is None:
                continue
            if isinstance(value, datetime):
                return value.isoformat()
            return str(value)
        return None

    def _numeric_bucket(self, value: float | None) -> str:
        if value is None:
            return "UNKNOWN"
        if value < 0.33:
            return "LOW"
        if value < 0.66:
            return "MEDIUM"
        return "HIGH"

    def _worst_bucket_total_r(self, rows: list[dict[str, Any]]) -> float:
        if not rows:
            return 0.0
        return min(self._float(row.get("total_r"), 0.0) for row in rows)

    def _bucket_has_negative(self, rows: list[dict[str, Any]], bucket: str) -> bool:
        for row in rows:
            values = set(str(value) for value in row.values())
            if bucket in values and self._float(row.get("total_r"), 0.0) < 0.0:
                return True
        return False

    def _float(self, value: Any, default: float | None = 0.0) -> float:
        try:
            if value is None:
                if default is None:
                    return None  # type: ignore[return-value]
                return float(default)
            return float(value)
        except (TypeError, ValueError):
            if default is None:
                return None  # type: ignore[return-value]
            return float(default)
