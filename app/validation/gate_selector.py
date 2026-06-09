from __future__ import annotations

from typing import Any


class GateSelector:
    def select(self, gate_results: list[dict[str, Any]]) -> dict[str, Any]:
        passed: list[dict[str, Any]] = []
        for row in gate_results:
            if self._passes(row):
                item = {
                    "gate_type": row["gate_type"],
                    "threshold": row["threshold"],
                    "validation_signal_count": row["signal_count"],
                    "validation_profit_factor": row["profit_factor"],
                    "validation_total_r": row["total_r"],
                    "validation_expectancy_r": row["expectancy_r"],
                    "validation_long_count": row["long_count"],
                    "validation_short_count": row["short_count"],
                    "validation_max_drawdown_r": row["max_drawdown_r"],
                    "warnings": [],
                }
                if row.get("short_count", 0) == 0:
                    item["warnings"].append("no_short_signals")
                if row.get("long_count", 0) == 0:
                    item["warnings"].append("no_long_signals")
                passed.append(item)

        if not passed:
            return {"selected_gate": None, "reject_reason": "no_validation_gate_passed"}

        best = max(
            passed,
            key=lambda item: (
                float(item["validation_profit_factor"]),
                float(item["validation_total_r"]),
                float(item["validation_expectancy_r"]),
                int(item["validation_signal_count"]),
            ),
        )
        return {"selected_gate": best, "reject_reason": None}

    @staticmethod
    def _passes(row: dict[str, Any]) -> bool:
        if int(row.get("signal_count", 0)) < 30:
            return False
        if row.get("profit_factor") is None or float(row["profit_factor"]) <= 1.0:
            return False
        if float(row.get("total_r", 0.0)) <= 0.0:
            return False
        if row.get("expectancy_r") is None or float(row["expectancy_r"]) <= 0.0:
            return False
        if int(row.get("long_count", 0)) <= 0:
            return False
        max_drawdown_r = float(row.get("max_drawdown_r", 0.0))
        total_r = float(row.get("total_r", 0.0))
        if total_r > 0 and max_drawdown_r > abs(total_r) * 2:
            return False
        return True
