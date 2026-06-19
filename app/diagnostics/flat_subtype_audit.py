from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from app.labels.label_models import LABEL_FLAT


class FlatSubtypeAudit:
    diagnostic_name = "flat_subtype_audit"
    diagnostic_version = "ml38_9_9"

    def evaluate(self, rows: Sequence[Any]) -> dict[str, Any]:
        normalized = [self._normalize_row(row) for row in rows]
        flat_rows = [row for row in normalized if row["future_close_atr_label"] == LABEL_FLAT]
        counts = Counter(self._subtype(row) for row in flat_rows)
        flat_count = len(flat_rows)
        return {
            "diagnostic_name": self.diagnostic_name,
            "diagnostic_version": self.diagnostic_version,
            "row_count": len(normalized),
            "flat_row_count": flat_count,
            "flat_subtype_counts": {
                "clean_flat": counts.get("clean_flat", 0),
                "volatile_flat": counts.get("volatile_flat", 0),
                "range_chop_flat": counts.get("range_chop_flat", 0),
                "failed_breakout_flat": counts.get("failed_breakout_flat", 0),
                "ambiguous_touch_flat": counts.get("ambiguous_touch_flat", 0),
                "no_setup_flat": counts.get("no_setup_flat", 0),
            },
            "dominant_flat_subtype": counts.most_common(1)[0][0] if counts else None,
        }

    @staticmethod
    def _normalize_row(row: Any) -> dict[str, Any]:
        if isinstance(row, Mapping):
            payload = dict(row)
        else:
            payload = dict(getattr(row, "__dict__", {}))
        return {
            "future_close_atr_label": str(payload.get("future_close_atr_label") or LABEL_FLAT),
            "future_move_atr": float(payload.get("future_move_atr") or 0.0),
            "up_move_atr": float(payload.get("up_move_atr") or 0.0),
            "down_move_atr": float(payload.get("down_move_atr") or 0.0),
            "first_touch_ambiguous": bool(payload.get("first_touch_ambiguous", False)),
            "has_setup_context": bool(payload.get("has_setup_context", False)),
        }

    @staticmethod
    def _subtype(row: dict[str, Any]) -> str:
        up_move_atr = float(row["up_move_atr"])
        down_move_atr = float(row["down_move_atr"])
        future_move_atr = abs(float(row["future_move_atr"]))
        if bool(row["first_touch_ambiguous"]):
            return "ambiguous_touch_flat"
        if not bool(row["has_setup_context"]):
            return "no_setup_flat"
        if up_move_atr >= 0.8 and down_move_atr >= 0.8:
            if future_move_atr <= 0.25:
                return "range_chop_flat"
            return "volatile_flat"
        if max(up_move_atr, down_move_atr) >= 1.2:
            return "failed_breakout_flat"
        if max(up_move_atr, down_move_atr) >= 0.8:
            return "volatile_flat"
        return "clean_flat"
