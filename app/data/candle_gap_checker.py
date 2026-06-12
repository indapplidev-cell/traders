from datetime import datetime, timedelta, timezone
from typing import Any


class CandleGapChecker:
    def check(
        self,
        candles: list[Any],
        interval: str,
        start_at: datetime,
        end_at: datetime,
        symbol: str | None = None,
    ) -> dict[str, Any]:
        normalized_start = self._normalize_datetime(start_at)
        normalized_end = self._normalize_datetime(end_at)
        open_times = [self._normalize_datetime(self._extract_open_time(candle)) for candle in candles]
        unique_open_times = sorted(set(open_times))
        last_open_time = unique_open_times[-1] if unique_open_times else None

        duplicates = sorted({open_time for open_time in open_times if open_times.count(open_time) > 1})
        misaligned = sorted({open_time for open_time in unique_open_times if not self.is_open_time_aligned(open_time, interval)})
        missing = self._find_missing_open_times(unique_open_times, interval, normalized_start, normalized_end)
        trailing_missing = self._split_trailing_incomplete_missing(
            unique_open_times=unique_open_times,
            missing=missing,
            interval=interval,
            end_at=normalized_end,
        )
        trailing_missing_set = set(trailing_missing)
        real_missing = [open_time for open_time in missing if open_time not in trailing_missing_set]

        return {
            "symbol": symbol,
            "interval": interval,
            "start_at": normalized_start.isoformat(),
            "end_at": normalized_end.isoformat(),
            "checked": len(candles),
            "unique_open_times": len(unique_open_times),
            "last_open_time": None if last_open_time is None else last_open_time.isoformat(),
            "duplicate_count": len(duplicates),
            "duplicates": [value.isoformat() for value in duplicates],
            "gap_count": len(missing),
            "missing_open_times": [value.isoformat() for value in missing],
            "real_gap_count": len(real_missing),
            "real_missing_open_times": [value.isoformat() for value in real_missing],
            "trailing_incomplete_count": len(trailing_missing),
            "trailing_incomplete_open_times": [value.isoformat() for value in trailing_missing],
            "trailing_incomplete_range_detected": bool(trailing_missing),
            "misaligned_count": len(misaligned),
            "misaligned_open_times": [value.isoformat() for value in misaligned],
            "is_valid": len(duplicates) == 0 and len(missing) == 0 and len(misaligned) == 0,
        }

    def is_open_time_aligned(self, open_time: datetime, interval: str) -> bool:
        value, unit = self._parse_interval(interval)
        normalized = self._normalize_datetime(open_time)

        if unit == "M":
            months_from_origin = (normalized.year - 1970) * 12 + (normalized.month - 1)
            return (
                normalized.day == 1
                and normalized.hour == 0
                and normalized.minute == 0
                and normalized.second == 0
                and normalized.microsecond == 0
                and months_from_origin % value == 0
            )

        if unit == "w":
            base = datetime(1970, 1, 5, tzinfo=timezone.utc)
            delta = normalized - base
            return (
                normalized.hour == 0
                and normalized.minute == 0
                and normalized.second == 0
                and normalized.microsecond == 0
                and delta.total_seconds() >= 0
                and delta.total_seconds() % (value * 7 * 24 * 60 * 60) == 0
            )

        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        delta_seconds = int((normalized - epoch).total_seconds())
        step_seconds = int(self.interval_to_timedelta(interval).total_seconds())
        return (
            normalized.second == 0
            and normalized.microsecond == 0
            and delta_seconds % step_seconds == 0
        )

    def advance_open_time(self, open_time: datetime, interval: str) -> datetime:
        value, unit = self._parse_interval(interval)
        normalized = self._normalize_datetime(open_time)

        if unit == "m":
            return normalized + timedelta(minutes=value)
        if unit == "h":
            return normalized + timedelta(hours=value)
        if unit == "d":
            return normalized + timedelta(days=value)
        if unit == "w":
            return normalized + timedelta(weeks=value)
        if unit == "M":
            month_index = (normalized.year * 12 + (normalized.month - 1)) + value
            year = month_index // 12
            month = month_index % 12 + 1
            return normalized.replace(year=year, month=month, day=1)
        raise ValueError(f"Unsupported interval: {interval}")

    def interval_to_timedelta(self, interval: str) -> timedelta:
        value, unit = self._parse_interval(interval)
        if unit == "m":
            return timedelta(minutes=value)
        if unit == "h":
            return timedelta(hours=value)
        if unit == "d":
            return timedelta(days=value)
        if unit == "w":
            return timedelta(weeks=value)
        raise ValueError(f"Unsupported timedelta interval: {interval}")

    def _find_missing_open_times(
        self,
        open_times: list[datetime],
        interval: str,
        start_at: datetime,
        end_at: datetime,
    ) -> list[datetime]:
        actual_set = set(open_times)
        missing: list[datetime] = []
        cursor = self._normalize_datetime(start_at)
        limit = self._normalize_datetime(end_at)

        while cursor < limit:
            if cursor not in actual_set:
                missing.append(cursor)
            cursor = self.advance_open_time(cursor, interval)

        return missing

    def _split_trailing_incomplete_missing(
        self,
        *,
        unique_open_times: list[datetime],
        missing: list[datetime],
        interval: str,
        end_at: datetime,
    ) -> list[datetime]:
        if not unique_open_times or not missing:
            return []

        last_open_time = unique_open_times[-1]
        expected_last_open_time = end_at - self.interval_to_timedelta(interval)
        if last_open_time.date() != expected_last_open_time.date():
            return []
        cursor = self.advance_open_time(last_open_time, interval)
        trailing_candidate: list[datetime] = []
        while cursor < end_at:
            trailing_candidate.append(cursor)
            cursor = self.advance_open_time(cursor, interval)
        if not trailing_candidate:
            return []

        missing_set = set(missing)
        if all(open_time in missing_set for open_time in trailing_candidate):
            return trailing_candidate
        return []


    @staticmethod
    def _extract_open_time(candle: Any) -> datetime:
        if isinstance(candle, dict):
            return candle["open_time"]
        return candle.open_time

    @staticmethod
    def _normalize_datetime(value: datetime) -> datetime:
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)

    @staticmethod
    def _parse_interval(interval: str) -> tuple[int, str]:
        if len(interval) < 2:
            raise ValueError(f"Invalid interval: {interval}")

        value = int(interval[:-1])
        unit = interval[-1]
        if unit not in {"m", "h", "d", "w", "M"}:
            raise ValueError(f"Unsupported interval: {interval}")
        return value, unit
