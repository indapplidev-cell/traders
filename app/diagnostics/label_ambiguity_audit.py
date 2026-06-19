from __future__ import annotations

from typing import Any, Sequence

from app.diagnostics._book_audit_utils import get_value, label_from_row, normalize_label, safe_float


class LabelAmbiguityAudit:
    diagnostic_name = "label_ambiguity_audit"
    diagnostic_version = "ml38_9_7"

    def evaluate(self, rows: Sequence[Any]) -> dict[str, Any]:
        if not rows:
            return self._empty_payload()

        ambiguous_row_count = 0
        volatile_flat_count = 0
        up_with_large_adverse_count = 0
        down_with_large_favorable_count = 0
        both_side_excursion_count = 0
        clean_flat_count = 0
        clean_directional_count = 0
        future_close_conflict_count = 0
        ambiguous_tp_sl_count = 0

        for row in rows:
            label = label_from_row(row) or "FLAT"
            favorable = abs(safe_float(get_value(row, "max_favorable_move_atr", "future_move_atr"), 0.0) or 0.0)
            adverse = abs(safe_float(get_value(row, "max_adverse_move_atr"), 0.0) or 0.0)
            future_close_direction = normalize_label(get_value(row, "future_close_direction"))
            tp_before_sl = get_value(row, "tp_before_sl")
            ambiguous_flags = set()

            if label == "FLAT" and max(favorable, adverse) >= 0.8:
                volatile_flat_count += 1
                ambiguous_flags.add("volatile_flat")
            if label == "UP" and adverse >= 0.8:
                up_with_large_adverse_count += 1
                ambiguous_flags.add("up_with_large_adverse")
            if label == "DOWN" and favorable >= 0.8:
                down_with_large_favorable_count += 1
                ambiguous_flags.add("down_with_large_favorable")
            if favorable >= 0.8 and adverse >= 0.8:
                both_side_excursion_count += 1
                ambiguous_flags.add("both_side_excursion")
            if future_close_direction not in {None, label} and label in {"UP", "DOWN"}:
                future_close_conflict_count += 1
                ambiguous_flags.add("future_close_conflict")
            if tp_before_sl is None and favorable >= 0.5 and adverse >= 0.5:
                ambiguous_tp_sl_count += 1
                ambiguous_flags.add("ambiguous_tp_sl")
            if abs(favorable - adverse) <= 0.1 and max(favorable, adverse) >= 0.7:
                ambiguous_tp_sl_count += 1
                ambiguous_flags.add("ambiguous_tp_sl")

            if ambiguous_flags:
                ambiguous_row_count += 1
            elif label == "FLAT" and max(favorable, adverse) <= 0.35:
                clean_flat_count += 1
            elif label in {"UP", "DOWN"} and favorable >= 0.5 and adverse <= 0.5:
                clean_directional_count += 1

        row_count = len(rows)
        ambiguous_ratio = ambiguous_row_count / row_count if row_count else 0.0
        volatile_flat_ratio = volatile_flat_count / row_count if row_count else 0.0
        if row_count == 0:
            noise_rating = "UNAVAILABLE"
        elif ambiguous_ratio >= 0.4:
            noise_rating = "HIGH_NOISE"
        elif ambiguous_ratio >= 0.2 or volatile_flat_ratio >= 0.15:
            noise_rating = "WATCH"
        else:
            noise_rating = "GOOD"

        recommendation = "keep_current_labels_for_now"
        if ambiguous_ratio >= 0.4:
            recommendation = "consider_first_touch_or_setup_aware_labels"
        elif volatile_flat_ratio >= 0.15:
            recommendation = "split_flat_subtypes_or_no_trade"
        elif up_with_large_adverse_count > 0 or down_with_large_favorable_count > 0 or future_close_conflict_count > 0:
            recommendation = "future_close_label_may_not_match_trade_outcome"

        return {
            "diagnostic_name": self.diagnostic_name,
            "diagnostic_version": self.diagnostic_version,
            "row_count": row_count,
            "ambiguous_row_count": ambiguous_row_count,
            "ambiguous_row_ratio": round(ambiguous_ratio, 6),
            "volatile_flat_count": volatile_flat_count,
            "volatile_flat_ratio": round(volatile_flat_ratio, 6),
            "up_with_large_adverse_count": up_with_large_adverse_count,
            "down_with_large_favorable_count": down_with_large_favorable_count,
            "both_side_excursion_count": both_side_excursion_count,
            "future_close_conflict_count": future_close_conflict_count,
            "ambiguous_tp_sl_count": ambiguous_tp_sl_count,
            "clean_flat_count": clean_flat_count,
            "clean_directional_count": clean_directional_count,
            "label_noise_rating": noise_rating,
            "recommendation": recommendation,
        }

    def _empty_payload(self) -> dict[str, Any]:
        return {
            "diagnostic_name": self.diagnostic_name,
            "diagnostic_version": self.diagnostic_version,
            "row_count": 0,
            "ambiguous_row_count": 0,
            "ambiguous_row_ratio": 0.0,
            "volatile_flat_count": 0,
            "volatile_flat_ratio": 0.0,
            "up_with_large_adverse_count": 0,
            "down_with_large_favorable_count": 0,
            "both_side_excursion_count": 0,
            "future_close_conflict_count": 0,
            "ambiguous_tp_sl_count": 0,
            "clean_flat_count": 0,
            "clean_directional_count": 0,
            "label_noise_rating": "UNAVAILABLE",
            "recommendation": "insufficient_rows_for_label_ambiguity_audit",
        }
