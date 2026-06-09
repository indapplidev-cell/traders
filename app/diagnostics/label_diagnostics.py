from __future__ import annotations

from collections import Counter
from statistics import median
from typing import Any


class LabelDiagnostics:
    LABELS = ["UP", "DOWN", "FLAT"]

    def build_report(
        self,
        labels: list[Any],
        symbol: str,
        interval: str,
        horizon_candles: int,
        label_version: str,
    ) -> dict[str, Any]:
        direction_counts = Counter(label.direction_label for label in labels)
        total_labels = len(labels)
        future_returns = [float(label.future_return) for label in labels]
        future_moves = [float(label.future_move_atr) for label in labels]
        favorable_moves = [float(label.max_favorable_move_atr) for label in labels]
        adverse_moves = [float(label.max_adverse_move_atr) for label in labels]
        tp_values = [label.tp_before_sl for label in labels]

        return {
            "symbol": symbol,
            "interval": interval,
            "horizon_candles": horizon_candles,
            "label_version": label_version,
            "total_labels": total_labels,
            "direction_counts": {label: direction_counts.get(label, 0) for label in self.LABELS},
            "direction_ratios": {
                label: (direction_counts.get(label, 0) / total_labels) if total_labels else 0.0 for label in self.LABELS
            },
            "tp_before_sl_true_count": sum(int(value is True) for value in tp_values),
            "tp_before_sl_false_count": sum(int(value is False) for value in tp_values),
            "tp_before_sl_null_count": sum(int(value is None) for value in tp_values),
            "future_return_min": min(future_returns) if future_returns else None,
            "future_return_max": max(future_returns) if future_returns else None,
            "future_return_mean": (sum(future_returns) / len(future_returns)) if future_returns else None,
            "future_return_median": median(future_returns) if future_returns else None,
            "future_move_atr_min": min(future_moves) if future_moves else None,
            "future_move_atr_max": max(future_moves) if future_moves else None,
            "future_move_atr_mean": (sum(future_moves) / len(future_moves)) if future_moves else None,
            "future_move_atr_median": median(future_moves) if future_moves else None,
            "max_favorable_move_atr_mean": (sum(favorable_moves) / len(favorable_moves)) if favorable_moves else None,
            "max_adverse_move_atr_mean": (sum(adverse_moves) / len(adverse_moves)) if adverse_moves else None,
        }
