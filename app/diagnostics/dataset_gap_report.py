from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from app.data.candle_gap_checker import CandleGapChecker
from app.diagnostics.gap_quality_diagnostics import GapQualityDiagnostics


class DatasetGapReportBuilder:
    """Build a detailed candle dataset gap report.

    This diagnostic is intentionally more verbose than CandleGapChecker:
    it separates requested-range missing candles into leading, internal,
    trailing incomplete, and after-last non-trailing buckets.
    """

    DIAGNOSTIC_NAME = "dataset_gap_report"
    DIAGNOSTIC_VERSION = "ml38_3"

    def build(
        self,
        *,
        candles: list[Any],
        symbol: str,
        interval: str,
        start_at: datetime,
        end_at: datetime,
        start_date: str,
        end_date: str,
        limit_gaps: int = 50,
    ) -> dict[str, Any]:
        checker = CandleGapChecker()
        normalized_start = self._normalize_datetime(start_at)
        normalized_end = self._normalize_datetime(end_at)
        step = checker.interval_to_timedelta(interval)
        step_minutes = int(step.total_seconds() // 60)

        raw_open_times = [self._normalize_datetime(self._extract_open_time(candle)) for candle in candles]
        unique_open_times = sorted(set(raw_open_times))
        duplicate_values = sorted([value for value, count in Counter(raw_open_times).items() if count > 1])
        out_of_order_count = sum(
            1
            for previous, current in zip(raw_open_times, raw_open_times[1:])
            if current < previous
        )
        misaligned = sorted(
            {open_time for open_time in unique_open_times if not checker.is_open_time_aligned(open_time, interval)}
        )

        expected_open_times = self._expected_open_times(normalized_start, normalized_end, step)
        actual_set = set(unique_open_times)
        missing = [open_time for open_time in expected_open_times if open_time not in actual_set]

        first_open_time = unique_open_times[0] if unique_open_times else None
        last_open_time = unique_open_times[-1] if unique_open_times else None

        trailing_missing = self._split_trailing_missing(
            missing=missing,
            last_open_time=last_open_time,
            interval_step=step,
            end_at=normalized_end,
        )
        trailing_set = set(trailing_missing)

        leading_missing = [
            open_time for open_time in missing
            if first_open_time is not None and open_time < first_open_time
        ]
        internal_missing = [
            open_time for open_time in missing
            if first_open_time is not None
            and last_open_time is not None
            and first_open_time < open_time < last_open_time
        ]
        after_last_missing = [
            open_time for open_time in missing
            if last_open_time is not None and open_time > last_open_time
        ]
        after_last_non_trailing_missing = [
            open_time for open_time in after_last_missing
            if open_time not in trailing_set
        ]

        # This matches current training-safety behavior more closely than just internal gaps:
        # leading coverage gaps and after-last non-trailing gaps are unsafe for a requested full training range.
        real_training_missing = list(dict.fromkeys(
            [*leading_missing, *internal_missing, *after_last_non_trailing_missing]
        ))

        contiguous_ranges = self._build_gap_ranges(real_training_missing, step)
        largest_gap_slots = max((item["missing_slots"] for item in contiguous_ranges), default=0)
        largest_gap_minutes = largest_gap_slots * step_minutes

        gap_quality = GapQualityDiagnostics().analyze(
            symbol=symbol,
            interval=interval,
            start_date=start_date,
            end_date=end_date,
            gap_count=len(missing),
            missing_open_times=[value.isoformat() for value in missing],
            last_open_time=None if last_open_time is None else last_open_time.isoformat(),
            real_gap_count=len(real_training_missing),
            real_missing_open_times=[value.isoformat() for value in real_training_missing],
            trailing_incomplete_count=len(trailing_missing),
            trailing_incomplete_open_times=[value.isoformat() for value in trailing_missing],
            trailing_incomplete_range_detected=bool(trailing_missing),
        )

        return {
            "diagnostic_name": self.DIAGNOSTIC_NAME,
            "diagnostic_version": self.DIAGNOSTIC_VERSION,
            "symbol": symbol,
            "interval": interval,
            "start_at": normalized_start.isoformat(),
            "end_at": normalized_end.isoformat(),
            "start_date": start_date,
            "end_date": end_date,
            "expected_interval_minutes": step_minutes,
            "expected_candle_count": len(expected_open_times),
            "actual_candle_count": len(raw_open_times),
            "unique_candle_count": len(unique_open_times),
            "duplicate_candle_count": len(duplicate_values),
            "duplicates": [value.isoformat() for value in duplicate_values[:limit_gaps]],
            "out_of_order_count": out_of_order_count,
            "misaligned_count": len(misaligned),
            "misaligned_open_times": [value.isoformat() for value in misaligned[:limit_gaps]],
            "first_candle_timestamp": None if first_open_time is None else first_open_time.isoformat(),
            "last_candle_timestamp": None if last_open_time is None else last_open_time.isoformat(),
            "requested_missing_candle_count": len(missing),
            "leading_missing_candle_count": len(leading_missing),
            "internal_missing_candle_count": len(internal_missing),
            "after_last_missing_candle_count": len(after_last_missing),
            "after_last_non_trailing_missing_candle_count": len(after_last_non_trailing_missing),
            "trailing_incomplete_count": len(trailing_missing),
            "effective_gap_count_for_training": len(real_training_missing),
            "gap_count": len(contiguous_ranges),
            "largest_gap_minutes": largest_gap_minutes,
            "largest_gap_missing_slots": largest_gap_slots,
            "gap_severity": gap_quality.get("gap_severity"),
            "gap_severity_for_training": gap_quality.get("gap_severity_for_training"),
            "training_safe": bool(gap_quality.get("dataset_safe_for_training")),
            "dataset_safe_for_training": bool(gap_quality.get("dataset_safe_for_training")),
            "gap_quality": gap_quality,
            "gap_ranges": contiguous_ranges[:limit_gaps],
            "sample_missing_open_times": [value.isoformat() for value in real_training_missing[:limit_gaps]],
            "sample_trailing_incomplete_open_times": [value.isoformat() for value in trailing_missing[:limit_gaps]],
            "root_cause_hint": self._root_cause_hint(
                leading_missing=leading_missing,
                internal_missing=internal_missing,
                after_last_non_trailing_missing=after_last_non_trailing_missing,
                trailing_missing=trailing_missing,
                duplicate_values=duplicate_values,
                misaligned=misaligned,
            ),
        }

    @staticmethod
    def _extract_open_time(candle: Any) -> datetime:
        if isinstance(candle, dict):
            return candle["open_time"]
        return candle.open_time

    @staticmethod
    def _normalize_datetime(value: datetime) -> datetime:
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)

    @staticmethod
    def _expected_open_times(start_at: datetime, end_at: datetime, step: timedelta) -> list[datetime]:
        values: list[datetime] = []
        cursor = start_at
        while cursor < end_at:
            values.append(cursor)
            cursor += step
        return values

    @staticmethod
    def _split_trailing_missing(
        *,
        missing: list[datetime],
        last_open_time: datetime | None,
        interval_step: timedelta,
        end_at: datetime,
    ) -> list[datetime]:
        if last_open_time is None or not missing:
            return []
        expected_last_open_time = end_at - interval_step
        if last_open_time.date() != expected_last_open_time.date():
            return []

        cursor = last_open_time + interval_step
        trailing_candidate: list[datetime] = []
        while cursor < end_at:
            trailing_candidate.append(cursor)
            cursor += interval_step
        if not trailing_candidate:
            return []

        missing_set = set(missing)
        if all(open_time in missing_set for open_time in trailing_candidate):
            return trailing_candidate
        return []

    @staticmethod
    def _build_gap_ranges(missing: list[datetime], step: timedelta) -> list[dict[str, Any]]:
        if not missing:
            return []

        ranges: list[dict[str, Any]] = []
        sorted_missing = sorted(missing)
        start = sorted_missing[0]
        previous = sorted_missing[0]
        count = 1

        for current in sorted_missing[1:]:
            if current - previous == step:
                count += 1
                previous = current
                continue
            ranges.append(DatasetGapReportBuilder._range_payload(start, previous, count, step))
            start = current
            previous = current
            count = 1

        ranges.append(DatasetGapReportBuilder._range_payload(start, previous, count, step))
        return ranges

    @staticmethod
    def _range_payload(start: datetime, end: datetime, count: int, step: timedelta) -> dict[str, Any]:
        return {
            "gap_start": start.isoformat(),
            "gap_end": end.isoformat(),
            "missing_slots": count,
            "gap_minutes": int(count * step.total_seconds() // 60),
            "before_timestamp": (start - step).isoformat(),
            "after_timestamp": (end + step).isoformat(),
        }

    @staticmethod
    def _root_cause_hint(
        *,
        leading_missing: list[datetime],
        internal_missing: list[datetime],
        after_last_non_trailing_missing: list[datetime],
        trailing_missing: list[datetime],
        duplicate_values: list[datetime],
        misaligned: list[datetime],
    ) -> str:
        if internal_missing:
            return "internal_missing_candles"
        if leading_missing:
            return "requested_range_starts_before_available_history"
        if after_last_non_trailing_missing:
            return "requested_range_ends_after_available_history"
        if trailing_missing:
            return "trailing_incomplete_current_day_only"
        if duplicate_values:
            return "duplicate_open_times"
        if misaligned:
            return "misaligned_open_times"
        return "clean"
