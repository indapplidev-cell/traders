from __future__ import annotations

from dataclasses import dataclass
from typing import Any


LABELS = ("UP", "DOWN", "FLAT")


@dataclass(frozen=True)
class DecisionCalibrationConfig:
    enabled: bool = False
    flat_if_max_prob_below: float = 0.42
    flat_if_margin_below: float = 0.06
    min_direction_prob: float = 0.40
    min_up_down_margin: float = 0.03
    down_boost: float = 0.0
    up_penalty: float = 0.0
    flat_boost: float = 0.0

    @classmethod
    def from_label_config(cls, label_config: dict[str, Any] | None) -> "DecisionCalibrationConfig":
        payload = dict(label_config or {})
        return cls(
            enabled=bool(payload.get("decision_calibration_enabled", False)),
            flat_if_max_prob_below=float(payload.get("decision_flat_if_max_prob_below", 0.42)),
            flat_if_margin_below=float(payload.get("decision_flat_if_margin_below", 0.06)),
            min_direction_prob=float(payload.get("decision_min_direction_prob", 0.40)),
            min_up_down_margin=float(payload.get("decision_min_up_down_margin", 0.03)),
            down_boost=float(payload.get("decision_down_boost", 0.0)),
            up_penalty=float(payload.get("decision_up_penalty", 0.0)),
            flat_boost=float(payload.get("decision_flat_boost", 0.0)),
        )


class CalibratedPredictionDecisions:
    DIAGNOSTIC_NAME = "calibrated_prediction_decisions"
    DIAGNOSTIC_VERSION = "ml38_9_3"

    def build_report(
        self,
        *,
        predictions: list[dict[str, Any]],
        label_config: dict[str, Any] | None,
        symbol: str | None = None,
        config_id: str | None = None,
    ) -> dict[str, Any]:
        config = DecisionCalibrationConfig.from_label_config(label_config)
        raw_rows = [dict(row) for row in predictions]
        calibrated_rows = [
            self._calibrate_row(row=dict(row), config=config)
            for row in raw_rows
        ]

        raw_counts = self._counts(raw_rows, key="predicted_label")
        calibrated_counts = self._counts(calibrated_rows, key="predicted_label")
        actual_counts = self._counts(raw_rows, key="actual_label")

        total_rows = len(raw_rows)
        raw_accuracy = self._accuracy(raw_rows)
        calibrated_accuracy = self._accuracy(calibrated_rows)
        baseline_accuracy = self._baseline_accuracy(actual_counts, total_rows)

        return {
            "diagnostic_name": self.DIAGNOSTIC_NAME,
            "diagnostic_version": self.DIAGNOSTIC_VERSION,
            "symbol": symbol,
            "config_id": config_id,
            "enabled": config.enabled,
            "config": {
                "flat_if_max_prob_below": config.flat_if_max_prob_below,
                "flat_if_margin_below": config.flat_if_margin_below,
                "min_direction_prob": config.min_direction_prob,
                "min_up_down_margin": config.min_up_down_margin,
                "down_boost": config.down_boost,
                "up_penalty": config.up_penalty,
                "flat_boost": config.flat_boost,
            },
            "total_rows": total_rows,
            "raw_predicted_counts": raw_counts,
            "raw_predicted_ratios": self._ratios(raw_counts, total_rows),
            "calibrated_predicted_counts": calibrated_counts,
            "calibrated_predicted_ratios": self._ratios(calibrated_counts, total_rows),
            "actual_counts": actual_counts,
            "actual_ratios": self._ratios(actual_counts, total_rows),
            "raw_accuracy": raw_accuracy,
            "calibrated_accuracy": calibrated_accuracy,
            "baseline_accuracy": baseline_accuracy,
            "raw_baseline_edge": self._edge(raw_accuracy, baseline_accuracy),
            "calibrated_baseline_edge": self._edge(calibrated_accuracy, baseline_accuracy),
            "changed_prediction_count": self._changed_count(raw_rows, calibrated_rows),
            "changed_prediction_ratio": self._safe_ratio(self._changed_count(raw_rows, calibrated_rows), total_rows),
            "calibrated_rows": calibrated_rows,
        }

    def _calibrate_row(
        self,
        *,
        row: dict[str, Any],
        config: DecisionCalibrationConfig,
    ) -> dict[str, Any]:
        if not config.enabled:
            row["raw_predicted_label"] = row.get("predicted_label")
            row["calibrated_decision_applied"] = False
            return row

        prob_up = self._safe_float(row.get("prob_up"))
        prob_down = self._safe_float(row.get("prob_down"))
        prob_flat = self._safe_float(row.get("prob_flat"))

        adjusted = {
            "UP": prob_up - config.up_penalty,
            "DOWN": prob_down + config.down_boost,
            "FLAT": prob_flat + config.flat_boost,
        }

        raw_probs = {
            "UP": prob_up,
            "DOWN": prob_down,
            "FLAT": prob_flat,
        }

        raw_sorted = sorted(raw_probs.items(), key=lambda item: item[1], reverse=True)
        adjusted_sorted = sorted(adjusted.items(), key=lambda item: item[1], reverse=True)

        raw_top_label, raw_top_prob = raw_sorted[0]
        raw_second_prob = raw_sorted[1][1]
        adjusted_top_label, adjusted_top_prob = adjusted_sorted[0]
        adjusted_second_prob = adjusted_sorted[1][1]

        raw_margin = raw_top_prob - raw_second_prob
        adjusted_margin = adjusted_top_prob - adjusted_second_prob
        up_down_margin = abs(adjusted["UP"] - adjusted["DOWN"])

        predicted_label = adjusted_top_label
        reason = "direction_selected"

        if raw_top_prob < config.flat_if_max_prob_below:
            predicted_label = "FLAT"
            reason = "max_prob_below_threshold"
        elif raw_margin < config.flat_if_margin_below:
            predicted_label = "FLAT"
            reason = "margin_below_threshold"
        elif adjusted_top_label in {"UP", "DOWN"}:
            raw_direction_prob = raw_probs[adjusted_top_label]
            if raw_direction_prob < config.min_direction_prob:
                predicted_label = "FLAT"
                reason = "direction_prob_below_threshold"
            elif up_down_margin < config.min_up_down_margin:
                predicted_label = "FLAT"
                reason = "up_down_margin_below_threshold"

        row["raw_predicted_label"] = row.get("predicted_label")
        row["predicted_label"] = predicted_label
        row["calibrated_decision_applied"] = True
        row["calibrated_decision_reason"] = reason
        row["raw_max_prob"] = raw_top_prob
        row["raw_margin"] = raw_margin
        row["adjusted_top_label"] = adjusted_top_label
        row["adjusted_top_prob"] = adjusted_top_prob
        row["adjusted_margin"] = adjusted_margin
        row["adjusted_prob_up"] = adjusted["UP"]
        row["adjusted_prob_down"] = adjusted["DOWN"]
        row["adjusted_prob_flat"] = adjusted["FLAT"]
        return row

    def _counts(self, rows: list[dict[str, Any]], *, key: str) -> dict[str, int]:
        counts = {label: 0 for label in LABELS}
        for row in rows:
            label = str(row.get(key, "FLAT")).upper()
            if label not in counts:
                label = "FLAT"
            counts[label] += 1
        return counts

    def _accuracy(self, rows: list[dict[str, Any]]) -> float | None:
        if not rows:
            return None
        correct = sum(
            1
            for row in rows
            if str(row.get("predicted_label")).upper() == str(row.get("actual_label")).upper()
        )
        return correct / len(rows)

    def _baseline_accuracy(self, actual_counts: dict[str, int], total_rows: int) -> float | None:
        if total_rows <= 0:
            return None
        return max(actual_counts.values(), default=0) / total_rows

    def _edge(self, accuracy: float | None, baseline_accuracy: float | None) -> float | None:
        if accuracy is None or baseline_accuracy is None:
            return None
        return accuracy - baseline_accuracy

    def _changed_count(
        self,
        raw_rows: list[dict[str, Any]],
        calibrated_rows: list[dict[str, Any]],
    ) -> int:
        count = 0
        for raw, calibrated in zip(raw_rows, calibrated_rows):
            if str(raw.get("predicted_label")).upper() != str(calibrated.get("predicted_label")).upper():
                count += 1
        return count

    def _ratios(self, counts: dict[str, int], total_rows: int) -> dict[str, float]:
        if total_rows <= 0:
            return {label: 0.0 for label in LABELS}
        return {label: counts.get(label, 0) / total_rows for label in LABELS}

    def _safe_ratio(self, numerator: int | float, denominator: int | float) -> float:
        if denominator <= 0:
            return 0.0
        return float(numerator) / float(denominator)

    def _safe_float(self, value: Any) -> float:
        if value is None:
            return 0.0
        numeric = float(value)
        if numeric != numeric or numeric in {float("inf"), float("-inf")}:
            return 0.0
        return numeric
