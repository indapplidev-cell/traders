from __future__ import annotations

from datetime import date, datetime, timezone

from app.dataset.dataset_models import DatasetRow


class DatasetSplitter:
    DEFAULT_TRAIN_END = datetime(2025, 11, 1, tzinfo=timezone.utc)
    DEFAULT_VALIDATION_END = datetime(2026, 3, 1, tzinfo=timezone.utc)

    def __init__(self, train_end: date | datetime | None = None, validation_end: date | datetime | None = None) -> None:
        self._train_end = self._normalize_boundary(train_end) if train_end is not None else self.DEFAULT_TRAIN_END
        self._validation_end = (
            self._normalize_boundary(validation_end) if validation_end is not None else self.DEFAULT_VALIDATION_END
        )

    def split(self, rows: list[DatasetRow]) -> dict[str, list[DatasetRow]]:
        ordered_rows = sorted(rows, key=lambda item: item.candle_open_time)
        train: list[DatasetRow] = []
        validation: list[DatasetRow] = []
        test: list[DatasetRow] = []

        for row in ordered_rows:
            open_time = self._normalize_datetime(row.candle_open_time)
            if open_time < self._train_end:
                train.append(row)
            elif open_time < self._validation_end:
                validation.append(row)
            else:
                test.append(row)

        if self._should_use_fallback_split(ordered_rows, train, validation, test):
            return self._fallback_split(ordered_rows)

        return {
            "train": train,
            "validation": validation,
            "test": test,
        }

    def _should_use_fallback_split(
        self,
        ordered_rows: list[DatasetRow],
        train: list[DatasetRow],
        validation: list[DatasetRow],
        test: list[DatasetRow],
    ) -> bool:
        return (
            len(ordered_rows) >= 3
            and self._train_end == self.DEFAULT_TRAIN_END
            and self._validation_end == self.DEFAULT_VALIDATION_END
            and (len(validation) == 0 or len(test) == 0)
        )

    @staticmethod
    def _fallback_split(rows: list[DatasetRow]) -> dict[str, list[DatasetRow]]:
        total = len(rows)
        train_end_index = max(1, int(total * 0.70))
        validation_end_index = max(train_end_index + 1, int(total * 0.85))
        validation_end_index = min(validation_end_index, total - 1)

        train = rows[:train_end_index]
        validation = rows[train_end_index:validation_end_index]
        test = rows[validation_end_index:]

        if not validation and len(test) > 1:
            validation = test[:1]
            test = test[1:]
        if not test and len(validation) > 1:
            test = validation[-1:]
            validation = validation[:-1]

        return {
            "train": train,
            "validation": validation,
            "test": test,
        }

    @staticmethod
    def _normalize_datetime(value: datetime) -> datetime:
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)

    @staticmethod
    def _normalize_boundary(value: date | datetime) -> datetime:
        if isinstance(value, datetime):
            return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
