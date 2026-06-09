from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any


@dataclass(slots=True)
class WalkForwardConfig:
    mode: str
    train_days: int
    validation_days: int
    test_days: int
    step_days: int
    min_train_rows: int


class WalkForwardSplitter:
    def build_plan(self, dataset_rows: list[Any], config: WalkForwardConfig) -> list[dict[str, Any]]:
        if not dataset_rows:
            return []
        ordered_rows = sorted(dataset_rows, key=lambda row: row.candle_open_time)
        overall_start = ordered_rows[0].candle_open_time
        overall_end = ordered_rows[-1].candle_open_time
        folds: list[dict[str, Any]] = []
        fold_index = 1
        anchor_start = overall_start

        while True:
            if config.mode == "expanding":
                train_start = overall_start
                train_end = anchor_start + timedelta(days=config.train_days)
            elif config.mode == "rolling":
                train_start = anchor_start
                train_end = train_start + timedelta(days=config.train_days)
            else:
                raise ValueError(f"Unsupported walk-forward mode: {config.mode}")

            validation_start = train_end
            validation_end = validation_start + timedelta(days=config.validation_days)
            test_start = validation_end
            test_end = test_start + timedelta(days=config.test_days)

            if test_start > overall_end:
                break

            train_rows = self._slice_rows(ordered_rows, train_start, train_end)
            validation_rows = self._slice_rows(ordered_rows, validation_start, validation_end)
            test_rows = self._slice_rows(ordered_rows, test_start, test_end)

            if len(train_rows) >= config.min_train_rows and validation_rows and test_rows:
                folds.append(
                    {
                        "fold_index": fold_index,
                        "train_start": train_start.isoformat(),
                        "train_end": train_end.isoformat(),
                        "validation_start": validation_start.isoformat(),
                        "validation_end": validation_end.isoformat(),
                        "test_start": test_start.isoformat(),
                        "test_end": test_end.isoformat(),
                        "train_rows": len(train_rows),
                        "validation_rows": len(validation_rows),
                        "test_rows": len(test_rows),
                    }
                )
                fold_index += 1

            anchor_start += timedelta(days=config.step_days)
            if anchor_start > overall_end:
                break

        return folds

    @staticmethod
    def apply_fold(dataset_rows: list[Any], fold: dict[str, Any]) -> dict[str, list[Any]]:
        ordered_rows = sorted(dataset_rows, key=lambda row: row.candle_open_time)
        return {
            "train": WalkForwardSplitter._slice_rows(
                ordered_rows,
                WalkForwardSplitter._parse_timestamp(fold["train_start"]),
                WalkForwardSplitter._parse_timestamp(fold["train_end"]),
            ),
            "validation": WalkForwardSplitter._slice_rows(
                ordered_rows,
                WalkForwardSplitter._parse_timestamp(fold["validation_start"]),
                WalkForwardSplitter._parse_timestamp(fold["validation_end"]),
            ),
            "test": WalkForwardSplitter._slice_rows(
                ordered_rows,
                WalkForwardSplitter._parse_timestamp(fold["test_start"]),
                WalkForwardSplitter._parse_timestamp(fold["test_end"]),
            ),
        }

    @staticmethod
    def _slice_rows(rows: list[Any], start_at, end_at) -> list[Any]:
        return [row for row in rows if start_at <= row.candle_open_time < end_at]

    @staticmethod
    def _parse_timestamp(value: str):
        from datetime import datetime

        return datetime.fromisoformat(value)
