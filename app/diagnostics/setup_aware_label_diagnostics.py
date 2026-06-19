from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from app.diagnostics.label_mode_comparison_audit import LabelModeComparisonAudit
from app.labels.label_models import LABEL_DOWN, LABEL_FLAT, LABEL_UP


class SetupAwareLabelDiagnostics:
    diagnostic_name = "setup_aware_label_diagnostics"
    diagnostic_version = "ml38_9_9"

    def __init__(self) -> None:
        self._comparison_audit = LabelModeComparisonAudit()

    def evaluate(self, rows: Sequence[Any]) -> dict[str, Any]:
        normalized = [self._normalize_row(row) for row in rows]
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in normalized:
            grouped[row["setup_type"]].append(row)

        label_distribution_by_setup_type: dict[str, dict[str, dict[str, int]]] = {}
        first_touch_edge_by_setup_type: dict[str, float] = {}
        future_close_edge_by_setup_type: dict[str, float] = {}
        ambiguous_ratio_by_setup_type: dict[str, float] = {}
        recommended_label_mode_by_setup_type: dict[str, str] = {}
        row_count_by_setup_type: dict[str, int] = {}

        for setup_type, group_rows in grouped.items():
            label_distribution_by_setup_type[setup_type] = {
                "future_close_atr": self._counts(group_rows, "future_close_atr_label"),
                "first_touch_tp_sl": self._counts(group_rows, "first_touch_tp_sl_label"),
                "setup_aware_first_touch": self._counts(group_rows, "setup_aware_first_touch_label"),
            }
            first_touch_edge_by_setup_type[setup_type] = self._average_edge(group_rows, "first_touch_tp_sl_label")
            future_close_edge_by_setup_type[setup_type] = self._average_edge(group_rows, "future_close_atr_label")
            comparison = self._comparison_audit.evaluate(group_rows)
            ambiguous_ratio_by_setup_type[setup_type] = float(comparison["first_touch_ambiguous_ratio"])
            recommended_label_mode_by_setup_type[setup_type] = str(comparison["label_mode_recommendation"])
            row_count_by_setup_type[setup_type] = len(group_rows)

        return {
            "diagnostic_name": self.diagnostic_name,
            "diagnostic_version": self.diagnostic_version,
            "row_count": len(normalized),
            "row_count_by_setup_type": row_count_by_setup_type,
            "label_distribution_by_setup_type": label_distribution_by_setup_type,
            "first_touch_edge_by_setup_type": first_touch_edge_by_setup_type,
            "future_close_edge_by_setup_type": future_close_edge_by_setup_type,
            "ambiguous_ratio_by_setup_type": ambiguous_ratio_by_setup_type,
            "recommended_label_mode_by_setup_type": recommended_label_mode_by_setup_type,
        }

    @staticmethod
    def _normalize_row(row: Any) -> dict[str, Any]:
        if isinstance(row, Mapping):
            payload = dict(row)
        else:
            payload = dict(getattr(row, "__dict__", {}))
        return {
            "setup_type": str(payload.get("setup_type") or "no_setup"),
            "future_close_atr_label": str(payload.get("future_close_atr_label") or LABEL_FLAT),
            "first_touch_tp_sl_label": str(payload.get("first_touch_tp_sl_label") or LABEL_FLAT),
            "setup_aware_first_touch_label": str(payload.get("setup_aware_first_touch_label") or LABEL_FLAT),
            "future_move_atr": float(payload.get("future_move_atr") or 0.0),
            "first_touch_ambiguous": bool(payload.get("first_touch_ambiguous", False)),
            "has_setup_context": bool(payload.get("has_setup_context", False)),
        }

    @staticmethod
    def _counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
        counts = Counter(str(row[key]) for row in rows)
        return {
            LABEL_UP: counts.get(LABEL_UP, 0),
            LABEL_DOWN: counts.get(LABEL_DOWN, 0),
            LABEL_FLAT: counts.get(LABEL_FLAT, 0),
        }

    @staticmethod
    def _average_edge(rows: list[dict[str, Any]], label_key: str) -> float:
        if not rows:
            return 0.0
        total = 0.0
        for row in rows:
            label = row[label_key]
            future_move_atr = float(row["future_move_atr"])
            if label == LABEL_UP:
                total += future_move_atr
            elif label == LABEL_DOWN:
                total += -future_move_atr
        return total / len(rows)
