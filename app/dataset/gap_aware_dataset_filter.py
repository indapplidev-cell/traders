from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


GAP_AWARE_DATASET_FILTER_NAME = "gap_aware_dataset_filter"
GAP_AWARE_DATASET_FILTER_VERSION = "ml30"


class GapAwareDatasetFilter:
    """Exclude dataset rows around detailed candle gaps when timestamps are available."""

    def apply(
        self,
        *,
        rows: list[Any],
        symbol: str,
        interval: str,
        gap_count: int,
        missing_open_times: list[str] | None = None,
        lookback_bars: int = 3,
        lookahead_bars: int = 3,
    ) -> tuple[list[Any], dict[str, Any]]:
        missing_open_times = missing_open_times or []
        input_rows = len(rows)
        parsed_missing = [
            self._normalize_datetime(datetime.fromisoformat(value))
            for value in missing_open_times
        ]
        if gap_count <= 0 and not parsed_missing:
            return list(rows), {
                "filter_name": GAP_AWARE_DATASET_FILTER_NAME,
                "filter_version": GAP_AWARE_DATASET_FILTER_VERSION,
                "symbol": symbol,
                "interval": interval,
                "input_rows": input_rows,
                "excluded_rows": 0,
                "remaining_rows": input_rows,
                "gap_count": 0,
                "lookback_bars": int(lookback_bars),
                "lookahead_bars": int(lookahead_bars),
                "excluded_windows": 0,
                "dataset_safe_for_training": True,
                "detail_gap_data_available": False,
                "filter_applied": False,
                "warnings": [],
                "recommendations": ["No gaps detected; gap-aware filtering is not required."],
            }

        if not parsed_missing:
            return list(rows), {
                "filter_name": GAP_AWARE_DATASET_FILTER_NAME,
                "filter_version": GAP_AWARE_DATASET_FILTER_VERSION,
                "symbol": symbol,
                "interval": interval,
                "input_rows": input_rows,
                "excluded_rows": 0,
                "remaining_rows": input_rows,
                "gap_count": int(gap_count),
                "lookback_bars": int(lookback_bars),
                "lookahead_bars": int(lookahead_bars),
                "excluded_windows": 0,
                "dataset_safe_for_training": False,
                "detail_gap_data_available": False,
                "filter_applied": False,
                "warnings": ["detail_gap_data_unavailable"],
                "recommendations": [
                    "Collect detailed gap locations before strict filtering.",
                ],
            }

        excluded_indexes = self._excluded_indexes(
            rows=rows,
            parsed_missing=parsed_missing,
            lookback_bars=max(int(lookback_bars), 0),
            lookahead_bars=max(int(lookahead_bars), 0),
        )
        filtered_rows = [
            row for index, row in enumerate(rows) if index not in excluded_indexes
        ]
        return filtered_rows, {
            "filter_name": GAP_AWARE_DATASET_FILTER_NAME,
            "filter_version": GAP_AWARE_DATASET_FILTER_VERSION,
            "symbol": symbol,
            "interval": interval,
            "input_rows": input_rows,
            "excluded_rows": len(excluded_indexes),
            "remaining_rows": len(filtered_rows),
            "gap_count": int(gap_count),
            "lookback_bars": int(lookback_bars),
            "lookahead_bars": int(lookahead_bars),
            "excluded_windows": len(parsed_missing),
            "dataset_safe_for_training": len(filtered_rows) > 0,
            "detail_gap_data_available": True,
            "filter_applied": True,
            "warnings": (
                ["rows_excluded_around_gaps"] if excluded_indexes else []
            ),
            "recommendations": self._recommendations(
                excluded_rows=len(excluded_indexes),
                remaining_rows=len(filtered_rows),
            ),
        }

    def _excluded_indexes(
        self,
        *,
        rows: list[Any],
        parsed_missing: list[datetime],
        lookback_bars: int,
        lookahead_bars: int,
    ) -> set[int]:
        row_times = [
            self._normalize_datetime(self._extract_open_time(row)) for row in rows
        ]
        indexes_by_time = {open_time: index for index, open_time in enumerate(row_times)}
        excluded_indexes: set[int] = set()

        for missing_time in parsed_missing:
            if missing_time not in indexes_by_time:
                insertion_index = 0
                while insertion_index < len(row_times) and row_times[insertion_index] < missing_time:
                    insertion_index += 1
            else:
                insertion_index = indexes_by_time[missing_time]

            start_index = max(insertion_index - lookback_bars, 0)
            end_index = min(insertion_index + lookahead_bars, len(rows) - 1)
            for index in range(start_index, end_index + 1):
                excluded_indexes.add(index)
        return excluded_indexes

    @staticmethod
    def _extract_open_time(row: Any) -> datetime:
        if isinstance(row, dict):
            value = row["candle_open_time"]
        else:
            value = row.candle_open_time
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return value

    @staticmethod
    def _normalize_datetime(value: datetime) -> datetime:
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)

    @staticmethod
    def _recommendations(*, excluded_rows: int, remaining_rows: int) -> list[str]:
        recommendations = [
            "Use detailed gap timestamps to exclude dataset windows around missing candles.",
        ]
        if excluded_rows > 0:
            recommendations.append("Review the excluded windows before trusting affected training candidates.")
        if remaining_rows <= 0:
            recommendations.append("Dataset is empty after filtering; recollect candles before retraining.")
        return recommendations
