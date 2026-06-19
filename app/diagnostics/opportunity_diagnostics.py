from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from app.baseline.baseline_models import BaselineModels


def _row_value(row: Any, key: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)


def _features_json(row: Any) -> dict[str, Any]:
    value = _row_value(row, "features_json", {})
    return dict(value or {})


class OpportunityDiagnostics:
    diagnostic_name = "opportunity_diagnostics"
    diagnostic_version = "ml38.10.1"

    def evaluate(
        self,
        rows: list[Any],
        *,
        train_rows: list[Any] | None = None,
    ) -> dict[str, Any]:
        if not rows:
            return {
                "diagnostic_name": self.diagnostic_name,
                "diagnostic_version": self.diagnostic_version,
                "row_count": 0,
                "opportunity_rate": 0.0,
                "no_trade_rate": 0.0,
                "opportunity_direction_distribution": {},
                "opportunity_precision_proxy": 0.0,
                "opportunity_first_touch_success_rate": 0.0,
                "opportunity_by_setup_type": {},
                "opportunity_by_regime": {},
                "no_trade_correctness_proxy": 0.0,
                "baseline_results": {},
                "opportunity_baseline_edge": 0.0,
                "opportunity_collapse_gate": {"passed": False, "opportunity_rate": 0.0},
                "no_trade_dominance_gate": {"passed": False, "no_trade_rate": 0.0},
                "setup_edge_gate": {"passed": False, "opportunity_first_touch_success_rate": 0.0},
            }

        actual_labels = [int(_row_value(row, "opportunity_label", 0) or 0) for row in rows]
        opportunity_rows = [row for row in rows if int(_row_value(row, "opportunity_label", 0) or 0) == 1]
        no_trade_rows = [row for row in rows if int(_row_value(row, "opportunity_label", 0) or 0) == 0]
        row_count = len(rows)
        opportunity_rate = len(opportunity_rows) / row_count
        no_trade_rate = len(no_trade_rows) / row_count

        direction_counts = Counter(
            str(_row_value(row, "opportunity_direction", "NONE"))
            for row in opportunity_rows
        )
        direction_distribution = {
            direction: count / len(opportunity_rows)
            for direction, count in sorted(direction_counts.items())
            if opportunity_rows
        }

        baseline_rows = train_rows if train_rows else rows
        baseline_results = self._baseline_results(
            train_rows=baseline_rows,
            target_rows=rows,
            actual_labels=actual_labels,
        )
        baseline_accuracies = [
            float(result.get("accuracy", 0.0))
            for result in baseline_results.values()
        ]
        best_baseline_accuracy = max(baseline_accuracies) if baseline_accuracies else 0.0
        always_no_trade_accuracy = float(
            baseline_results.get("always_no_trade_baseline", {}).get("accuracy", 0.0)
        )

        setup_groups: dict[str, dict[str, Any]] = {}
        regime_groups: dict[str, dict[str, Any]] = {}
        grouped_setup: dict[str, list[Any]] = defaultdict(list)
        grouped_regime: dict[str, list[Any]] = defaultdict(list)
        for row in rows:
            grouped_setup[str(_row_value(row, "setup_type", "no_setup"))].append(row)
            grouped_regime[self._resolve_regime(_features_json(row))].append(row)

        for setup_type, group_rows in grouped_setup.items():
            opportunity_count = sum(int(_row_value(row, "opportunity_label", 0) or 0) for row in group_rows)
            setup_groups[setup_type] = {
                "row_count": len(group_rows),
                "opportunity_count": opportunity_count,
                "opportunity_rate": opportunity_count / len(group_rows),
            }

        for regime, group_rows in grouped_regime.items():
            opportunity_count = sum(int(_row_value(row, "opportunity_label", 0) or 0) for row in group_rows)
            regime_groups[regime] = {
                "row_count": len(group_rows),
                "opportunity_count": opportunity_count,
                "opportunity_rate": opportunity_count / len(group_rows),
            }

        precision_proxy = self._precision_proxy(opportunity_rows)
        no_trade_correctness_proxy = self._no_trade_correctness_proxy(no_trade_rows)
        opportunity_collapse_gate_passed = 0.05 <= opportunity_rate <= 0.70
        no_trade_dominance_gate_passed = no_trade_rate <= 0.85
        setup_edge_gate_passed = precision_proxy >= 0.50

        return {
            "diagnostic_name": self.diagnostic_name,
            "diagnostic_version": self.diagnostic_version,
            "row_count": row_count,
            "opportunity_rate": opportunity_rate,
            "no_trade_rate": no_trade_rate,
            "opportunity_direction_distribution": direction_distribution,
            "opportunity_precision_proxy": precision_proxy,
            "opportunity_first_touch_success_rate": precision_proxy,
            "opportunity_by_setup_type": setup_groups,
            "opportunity_by_regime": regime_groups,
            "no_trade_correctness_proxy": no_trade_correctness_proxy,
            "baseline_results": baseline_results,
            "opportunity_baseline_edge": best_baseline_accuracy - always_no_trade_accuracy,
            "opportunity_collapse_gate": {
                "passed": opportunity_collapse_gate_passed,
                "opportunity_rate": opportunity_rate,
                "minimum": 0.05,
                "maximum": 0.70,
            },
            "no_trade_dominance_gate": {
                "passed": no_trade_dominance_gate_passed,
                "no_trade_rate": no_trade_rate,
                "maximum": 0.85,
            },
            "setup_edge_gate": {
                "passed": setup_edge_gate_passed,
                "opportunity_first_touch_success_rate": precision_proxy,
                "minimum": 0.50,
            },
        }

    def _baseline_results(
        self,
        *,
        train_rows: list[Any],
        target_rows: list[Any],
        actual_labels: list[int],
    ) -> dict[str, dict[str, Any]]:
        baseline_predictions = {
            "always_no_trade_baseline": BaselineModels.always_no_trade_baseline(target_rows),
            "setup_rule_baseline": BaselineModels.setup_rule_baseline(target_rows),
            "first_touch_setup_baseline": BaselineModels.first_touch_setup_baseline(target_rows),
        }
        _, majority_predictions = BaselineModels.majority_opportunity_baseline(train_rows, target_rows)
        baseline_predictions["majority_opportunity_baseline"] = majority_predictions
        results: dict[str, dict[str, Any]] = {}
        for name, predictions in baseline_predictions.items():
            correct = sum(int(predicted == actual) for predicted, actual in zip(predictions, actual_labels))
            results[name] = {
                "accuracy": correct / len(actual_labels) if actual_labels else 0.0,
                "positive_rate": sum(int(item) for item in predictions) / len(predictions) if predictions else 0.0,
            }
        return results

    @staticmethod
    def _precision_proxy(opportunity_rows: list[Any]) -> float:
        if not opportunity_rows:
            return 0.0
        success_count = 0
        for row in opportunity_rows:
            tp_before_sl = _row_value(row, "tp_before_sl")
            if tp_before_sl is True:
                success_count += 1
        return success_count / len(opportunity_rows)

    @staticmethod
    def _no_trade_correctness_proxy(no_trade_rows: list[Any]) -> float:
        if not no_trade_rows:
            return 0.0
        correct = 0
        for row in no_trade_rows:
            move = abs(float(_row_value(row, "future_move_atr", 0.0) or 0.0))
            adverse = float(_row_value(row, "max_adverse_move_atr", 0.0) or 0.0)
            if move < 0.45 or adverse >= move:
                correct += 1
        return correct / len(no_trade_rows)

    @staticmethod
    def _resolve_regime(features_json: dict[str, Any]) -> str:
        ordered_regimes = (
            "trend_up",
            "trend_down",
            "range",
            "high_volatility",
            "low_volatility",
        )
        for regime in ordered_regimes:
            value = features_json.get(f"regime_{regime}", 0.0)
            try:
                if float(value or 0.0) >= 0.5:
                    return regime
            except (TypeError, ValueError):
                continue
        return "unknown"
