from __future__ import annotations

from collections import Counter

from app.dataset.dataset_models import DatasetRow


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
