from __future__ import annotations

from collections import Counter

from app.dataset.dataset_models import DatasetRow


def _row_value(row, key: str, default=None):
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)


class BaselineModels:
    LABEL_ORDER = ["UP", "DOWN", "FLAT"]

    @staticmethod
    def always_flat(rows: list[DatasetRow]) -> list[str]:
        return ["FLAT"] * len(rows)

    @classmethod
    def majority_class(cls, train_rows: list[DatasetRow], target_rows: list[DatasetRow]) -> tuple[str, list[str]]:
        counts = Counter(row.direction_label for row in train_rows)
        majority_label = max(cls.LABEL_ORDER, key=lambda label: (counts.get(label, 0), -cls.LABEL_ORDER.index(label)))
        return majority_label, [majority_label] * len(target_rows)

    @staticmethod
    def last_return_direction(rows: list[DatasetRow], threshold: float = 0.0005) -> list[str]:
        predictions: list[str] = []
        for row in rows:
            value = float(row.features_json["return_1"])
            if value > threshold:
                predictions.append("UP")
            elif value < -threshold:
                predictions.append("DOWN")
            else:
                predictions.append("FLAT")
        return predictions

    @staticmethod
    def simple_ema_trend(rows: list[DatasetRow]) -> list[str]:
        predictions: list[str] = []
        for row in rows:
            ema_9 = float(row.features_json["ema_9"])
            ema_21 = float(row.features_json["ema_21"])
            close_to_ema_21 = float(row.features_json["close_to_ema_21"])
            if ema_9 > ema_21 and close_to_ema_21 > 0:
                predictions.append("UP")
            elif ema_9 < ema_21 and close_to_ema_21 < 0:
                predictions.append("DOWN")
            else:
                predictions.append("FLAT")
        return predictions

    @staticmethod
    def always_no_trade_baseline(rows: list[DatasetRow]) -> list[int]:
        return [0] * len(rows)

    @classmethod
    def majority_opportunity_baseline(
        cls,
        train_rows: list[DatasetRow],
        target_rows: list[DatasetRow],
    ) -> tuple[int, list[int]]:
        positive_count = sum(int(_row_value(row, "opportunity_label", 0) or 0) for row in train_rows)
        negative_count = max(0, len(train_rows) - positive_count)
        majority = 1 if positive_count > negative_count else 0
        return majority, [majority] * len(target_rows)

    @staticmethod
    def setup_rule_baseline(rows: list[DatasetRow]) -> list[int]:
        predictions: list[int] = []
        for row in rows:
            predictions.append(
                int(
                    str(_row_value(row, "setup_type", "no_setup")) != "no_setup"
                    and float(_row_value(row, "setup_quality_score", 0.0) or 0.0) >= 0.55
                    and float(_row_value(row, "label_ambiguity_score", 1.0) or 1.0) <= 0.45
                )
            )
        return predictions

    @staticmethod
    def first_touch_setup_baseline(rows: list[DatasetRow]) -> list[int]:
        predictions: list[int] = []
        for row in rows:
            direction_label = str(
                _row_value(
                    row,
                    "direction_label",
                    _row_value(row, "selected_direction_label", "FLAT"),
                )
            )
            tp_first = _row_value(row, "tp_before_sl", _row_value(row, "first_touch_tp_hit", False))
            predictions.append(
                int(
                    str(_row_value(row, "setup_type", "no_setup")) != "no_setup"
                    and direction_label in {"UP", "DOWN"}
                    and bool(tp_first)
                    and float(_row_value(row, "setup_expected_move_atr", 0.0) or 0.0) >= 0.45
                    and float(_row_value(row, "setup_invalidation_distance_atr", 0.0) or 0.0) <= 1.10
                )
            )
        return predictions
