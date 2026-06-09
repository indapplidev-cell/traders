from __future__ import annotations

from collections import Counter
from typing import Any

from app.dataset.dataset_models import DatasetRow
from app.features.feature_models import FEATURE_NAMES


class DatasetDiagnostics:
    LABELS = ["UP", "DOWN", "FLAT"]

    def build_report(
        self,
        dataset_rows: list[DatasetRow],
        split_rows: dict[str, list[DatasetRow]],
        raw_feature_rows: list[Any],
    ) -> dict[str, Any]:
        return {
            "total_rows": len(dataset_rows),
            "train_rows": len(split_rows["train"]),
            "validation_rows": len(split_rows["validation"]),
            "test_rows": len(split_rows["test"]),
            "label_counts_total": self._label_counts(dataset_rows),
            "label_counts_train": self._label_counts(split_rows["train"]),
            "label_counts_validation": self._label_counts(split_rows["validation"]),
            "label_counts_test": self._label_counts(split_rows["test"]),
            "label_ratios_total": self._label_ratios(dataset_rows),
            "label_ratios_train": self._label_ratios(split_rows["train"]),
            "label_ratios_validation": self._label_ratios(split_rows["validation"]),
            "label_ratios_test": self._label_ratios(split_rows["test"]),
            "feature_null_counts": self._feature_null_counts(raw_feature_rows),
            "feature_min_max_mean": self._feature_min_max_mean(dataset_rows),
            "feature_extreme_values": self._feature_extreme_values(dataset_rows),
            "train_first_open_time": self._first_open_time(split_rows["train"]),
            "train_last_open_time": self._last_open_time(split_rows["train"]),
            "validation_first_open_time": self._first_open_time(split_rows["validation"]),
            "validation_last_open_time": self._last_open_time(split_rows["validation"]),
            "test_first_open_time": self._first_open_time(split_rows["test"]),
            "test_last_open_time": self._last_open_time(split_rows["test"]),
        }

    def _label_counts(self, rows: list[DatasetRow]) -> dict[str, int]:
        counts = Counter(row.direction_label for row in rows)
        return {label: counts.get(label, 0) for label in self.LABELS}

    def _label_ratios(self, rows: list[DatasetRow]) -> dict[str, float]:
        total = len(rows)
        counts = self._label_counts(rows)
        if total == 0:
            return {label: 0.0 for label in self.LABELS}
        return {label: counts[label] / total for label in self.LABELS}

    @staticmethod
    def _feature_null_counts(raw_feature_rows: list[Any]) -> dict[str, int]:
        counts = {name: 0 for name in FEATURE_NAMES}
        for row in raw_feature_rows:
            for name in FEATURE_NAMES:
                if row.features_json.get(name) is None:
                    counts[name] += 1
        return counts

    @staticmethod
    def _feature_min_max_mean(rows: list[DatasetRow]) -> dict[str, dict[str, float | None]]:
        report: dict[str, dict[str, float | None]] = {}
        for name in FEATURE_NAMES:
            values = [float(row.features_json[name]) for row in rows]
            if not values:
                report[name] = {"min": None, "max": None, "mean": None}
                continue
            report[name] = {
                "min": min(values),
                "max": max(values),
                "mean": sum(values) / len(values),
            }
        return report

    @staticmethod
    def _feature_extreme_values(rows: list[DatasetRow]) -> dict[str, dict[str, float | str | None]]:
        report: dict[str, dict[str, float | str | None]] = {}
        for name in FEATURE_NAMES:
            if not rows:
                report[name] = {
                    "min_value": None,
                    "min_open_time": None,
                    "max_value": None,
                    "max_open_time": None,
                }
                continue
            min_row = min(rows, key=lambda row: float(row.features_json[name]))
            max_row = max(rows, key=lambda row: float(row.features_json[name]))
            report[name] = {
                "min_value": float(min_row.features_json[name]),
                "min_open_time": min_row.candle_open_time.isoformat(),
                "max_value": float(max_row.features_json[name]),
                "max_open_time": max_row.candle_open_time.isoformat(),
            }
        return report

    @staticmethod
    def _first_open_time(rows: list[DatasetRow]) -> str | None:
        return rows[0].candle_open_time.isoformat() if rows else None

    @staticmethod
    def _last_open_time(rows: list[DatasetRow]) -> str | None:
        return rows[-1].candle_open_time.isoformat() if rows else None
