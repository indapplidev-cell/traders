from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from app.labels.label_models import LABEL_DOWN, LABEL_FLAT, LABEL_UP


class LabelModeComparisonAudit:
    diagnostic_name = "label_mode_comparison_audit"
    diagnostic_version = "ml38_9_9"

    def evaluate(self, rows: Sequence[Any]) -> dict[str, Any]:
        normalized = [self._normalize_row(row) for row in rows]
        row_count = len(normalized)
        if row_count == 0:
            return {
                "diagnostic_name": self.diagnostic_name,
                "diagnostic_version": self.diagnostic_version,
                "row_count": 0,
                "agreement_ratio": 0.0,
                "future_close_vs_first_touch_conflict_ratio": 0.0,
                "future_close_up_but_first_touch_down_count": 0,
                "future_close_down_but_first_touch_up_count": 0,
                "future_close_flat_but_touch_event_count": 0,
                "first_touch_ambiguous_ratio": 0.0,
                "edge_by_label_mode": {},
                "label_mode_recommendation": "INSUFFICIENT_DATA",
            }

        agreement_count = 0
        directional_conflict_count = 0
        future_close_up_but_first_touch_down_count = 0
        future_close_down_but_first_touch_up_count = 0
        future_close_flat_but_touch_event_count = 0
        ambiguous_count = 0

        for row in normalized:
            future_close_label = row["future_close_atr_label"]
            first_touch_label = row["first_touch_tp_sl_label"]
            if future_close_label == first_touch_label:
                agreement_count += 1
            if future_close_label == LABEL_UP and first_touch_label == LABEL_DOWN:
                directional_conflict_count += 1
                future_close_up_but_first_touch_down_count += 1
            elif future_close_label == LABEL_DOWN and first_touch_label == LABEL_UP:
                directional_conflict_count += 1
                future_close_down_but_first_touch_up_count += 1
            if future_close_label == LABEL_FLAT and (
                first_touch_label in {LABEL_UP, LABEL_DOWN} or bool(row["first_touch_ambiguous"])
            ):
                future_close_flat_but_touch_event_count += 1
            if bool(row["first_touch_ambiguous"]):
                ambiguous_count += 1

        edge_by_label_mode = {
            "future_close_atr": self._average_edge(normalized, "future_close_atr_label"),
            "first_touch_tp_sl": self._average_edge(normalized, "first_touch_tp_sl_label"),
            "mfe_mae_dominance": self._average_edge(normalized, "mfe_mae_dominance_label"),
            "setup_aware_first_touch": self._average_edge(normalized, "setup_aware_first_touch_label"),
        }
        conflict_ratio = directional_conflict_count / row_count
        ambiguous_ratio = ambiguous_count / row_count
        flat_touch_ratio = future_close_flat_but_touch_event_count / row_count
        return {
            "diagnostic_name": self.diagnostic_name,
            "diagnostic_version": self.diagnostic_version,
            "row_count": row_count,
            "agreement_ratio": agreement_count / row_count,
            "future_close_vs_first_touch_conflict_ratio": conflict_ratio,
            "future_close_up_but_first_touch_down_count": future_close_up_but_first_touch_down_count,
            "future_close_down_but_first_touch_up_count": future_close_down_but_first_touch_up_count,
            "future_close_flat_but_touch_event_count": future_close_flat_but_touch_event_count,
            "first_touch_ambiguous_ratio": ambiguous_ratio,
            "edge_by_label_mode": edge_by_label_mode,
            "label_mode_recommendation": self._recommendation(
                row_count=row_count,
                conflict_ratio=conflict_ratio,
                flat_touch_ratio=flat_touch_ratio,
                ambiguous_ratio=ambiguous_ratio,
                edge_by_label_mode=edge_by_label_mode,
                no_setup_ratio=sum(int(not row["has_setup_context"]) for row in normalized) / row_count,
            ),
        }

    @staticmethod
    def _normalize_row(row: Any) -> dict[str, Any]:
        if isinstance(row, Mapping):
            payload = dict(row)
        else:
            payload = dict(getattr(row, "__dict__", {}))
        return {
            "future_close_atr_label": str(payload.get("future_close_atr_label") or LABEL_FLAT),
            "first_touch_tp_sl_label": str(payload.get("first_touch_tp_sl_label") or LABEL_FLAT),
            "mfe_mae_dominance_label": str(payload.get("mfe_mae_dominance_label") or LABEL_FLAT),
            "setup_aware_first_touch_label": str(payload.get("setup_aware_first_touch_label") or LABEL_FLAT),
            "future_move_atr": float(payload.get("future_move_atr") or 0.0),
            "first_touch_ambiguous": bool(payload.get("first_touch_ambiguous", False)),
            "has_setup_context": bool(payload.get("has_setup_context", False)),
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

    @staticmethod
    def _recommendation(
        *,
        row_count: int,
        conflict_ratio: float,
        flat_touch_ratio: float,
        ambiguous_ratio: float,
        edge_by_label_mode: dict[str, float],
        no_setup_ratio: float,
    ) -> str:
        if row_count < 20:
            return "INSUFFICIENT_DATA"
        if ambiguous_ratio >= 0.20 or flat_touch_ratio >= 0.20:
            if no_setup_ratio >= 0.25 and (
                edge_by_label_mode["setup_aware_first_touch"] >= edge_by_label_mode["first_touch_tp_sl"] - 0.01
            ):
                return "TRY_SETUP_AWARE_FIRST_TOUCH"
            return "SPLIT_FLAT_NO_TRADE"
        if (
            edge_by_label_mode["setup_aware_first_touch"] >= edge_by_label_mode["future_close_atr"] + 0.02
            and no_setup_ratio >= 0.20
        ):
            return "TRY_SETUP_AWARE_FIRST_TOUCH"
        if (
            conflict_ratio >= 0.10
            or edge_by_label_mode["first_touch_tp_sl"] >= edge_by_label_mode["future_close_atr"] + 0.01
        ):
            return "TRY_FIRST_TOUCH"
        return "KEEP_FUTURE_CLOSE"
