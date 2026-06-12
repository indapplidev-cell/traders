from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any


class GapQualityDiagnostics:
    DIAGNOSTIC_NAME = "gap_quality_diagnostics"
    DIAGNOSTIC_VERSION = "ml34"

    def analyze(
        self,
        *,
        symbol: str,
        interval: str,
        start_date: str,
        end_date: str,
        gap_count: int,
        missing_open_times: list[str] | None = None,
        last_open_time: str | None = None,
        real_gap_count: int | None = None,
        real_missing_open_times: list[str] | None = None,
        trailing_incomplete_count: int | None = None,
        trailing_incomplete_open_times: list[str] | None = None,
        trailing_incomplete_range_detected: bool | None = None,
    ) -> dict[str, Any]:
        interval_minutes = self._interval_to_minutes(interval)
        parsed_missing = self._parse_datetimes(missing_open_times)
        parsed_real_missing = self._parse_datetimes(real_missing_open_times)
        parsed_trailing_missing = self._parse_datetimes(trailing_incomplete_open_times)
        parsed_last_open_time = (
            self._normalize_datetime(datetime.fromisoformat(last_open_time))
            if last_open_time
            else None
        )

        classification = self._classify_missing_ranges(
            end_date=end_date,
            interval=interval,
            gap_count=int(gap_count),
            parsed_missing=parsed_missing,
            parsed_last_open_time=parsed_last_open_time,
            explicit_real_gap_count=real_gap_count,
            explicit_real_missing=parsed_real_missing,
            explicit_trailing_gap_count=trailing_incomplete_count,
            explicit_trailing_missing=parsed_trailing_missing,
            explicit_trailing_detected=trailing_incomplete_range_detected,
        )

        raw_gap_count = int(gap_count)
        effective_gap_count_for_training = int(classification["real_gap_count"])
        largest_gap_candles = self._largest_contiguous_gap(classification["real_missing_open_times"], interval_minutes)
        if largest_gap_candles == 0 and effective_gap_count_for_training > 0:
            largest_gap_candles = 1
        largest_gap_minutes = largest_gap_candles * interval_minutes

        raw_gap_severity = self._gap_severity(
            total_missing_candles_estimate=max(raw_gap_count, len(parsed_missing)),
            largest_gap_minutes=self._largest_gap_minutes(parsed_missing, interval_minutes, raw_gap_count),
        )
        gap_severity_for_training = self._gap_severity(
            total_missing_candles_estimate=effective_gap_count_for_training,
            largest_gap_minutes=largest_gap_minutes,
        )
        dataset_safe_for_training = gap_severity_for_training in {"OK", "MINOR"}
        warnings = self._warnings(
            raw_gap_count=raw_gap_count,
            effective_gap_count_for_training=effective_gap_count_for_training,
            gap_severity_for_training=gap_severity_for_training,
            trailing_incomplete_range_detected=bool(classification["trailing_incomplete_range_detected"]),
            largest_gap_minutes=largest_gap_minutes,
            interval_minutes=interval_minutes,
            degraded_mode=bool(classification["degraded_mode"]),
            detail_gap_data_available=bool(classification["detail_gap_data_available"]),
        )

        return {
            "diagnostic_name": self.DIAGNOSTIC_NAME,
            "diagnostic_version": self.DIAGNOSTIC_VERSION,
            "symbol": symbol,
            "interval": interval,
            "start_date": start_date,
            "end_date": end_date,
            "expected_interval_minutes": interval_minutes,
            "gap_count": raw_gap_count,
            "real_gap_count": effective_gap_count_for_training,
            "trailing_incomplete_count": int(classification["trailing_incomplete_count"]),
            "trailing_incomplete_range_detected": bool(classification["trailing_incomplete_range_detected"]),
            "effective_gap_count_for_training": effective_gap_count_for_training,
            "largest_gap_minutes": largest_gap_minutes,
            "total_missing_candles_estimate": max(raw_gap_count, len(parsed_missing)),
            "gap_severity": raw_gap_severity,
            "gap_severity_for_training": gap_severity_for_training,
            "dataset_safe_for_training": dataset_safe_for_training,
            "detail_gap_data_available": bool(classification["detail_gap_data_available"]),
            "degraded_mode": bool(classification["degraded_mode"]),
            "last_open_time": None if parsed_last_open_time is None else parsed_last_open_time.isoformat(),
            "real_missing_open_times": [value.isoformat() for value in classification["real_missing_open_times"]],
            "trailing_incomplete_open_times": [value.isoformat() for value in classification["trailing_incomplete_open_times"]],
            "warnings": warnings,
            "recommendations": self._recommendations(
                gap_severity_for_training=gap_severity_for_training,
                warnings=warnings,
                trailing_only_gap=raw_gap_count > 0 and effective_gap_count_for_training == 0,
                degraded_mode=bool(classification["degraded_mode"]),
            ),
        }

    @staticmethod
    def _parse_datetimes(values: list[str] | None) -> list[datetime]:
        return sorted(
            GapQualityDiagnostics._normalize_datetime(datetime.fromisoformat(value))
            for value in (values or [])
        )

    @staticmethod
    def _normalize_datetime(value: datetime) -> datetime:
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)

    def _classify_missing_ranges(
        self,
        *,
        end_date: str,
        interval: str,
        gap_count: int,
        parsed_missing: list[datetime],
        parsed_last_open_time: datetime | None,
        explicit_real_gap_count: int | None,
        explicit_real_missing: list[datetime],
        explicit_trailing_gap_count: int | None,
        explicit_trailing_missing: list[datetime],
        explicit_trailing_detected: bool | None,
    ) -> dict[str, Any]:
        if explicit_real_gap_count is not None or explicit_trailing_gap_count is not None or explicit_trailing_detected is not None:
            resolved_real_missing = explicit_real_missing
            resolved_trailing_missing = explicit_trailing_missing
            real_gap_count = len(resolved_real_missing) if resolved_real_missing else int(explicit_real_gap_count or 0)
            trailing_gap_count = len(resolved_trailing_missing) if resolved_trailing_missing else int(explicit_trailing_gap_count or 0)
            trailing_detected = bool(explicit_trailing_detected if explicit_trailing_detected is not None else trailing_gap_count > 0)
            return {
                "real_gap_count": real_gap_count,
                "real_missing_open_times": resolved_real_missing,
                "trailing_incomplete_count": trailing_gap_count,
                "trailing_incomplete_open_times": resolved_trailing_missing,
                "trailing_incomplete_range_detected": trailing_detected,
                "detail_gap_data_available": bool(parsed_missing or resolved_real_missing or resolved_trailing_missing),
                "degraded_mode": gap_count > 0 and not (parsed_missing or resolved_real_missing or resolved_trailing_missing or parsed_last_open_time),
            }

        if gap_count <= 0:
            return {
                "real_gap_count": 0,
                "real_missing_open_times": [],
                "trailing_incomplete_count": 0,
                "trailing_incomplete_open_times": [],
                "trailing_incomplete_range_detected": False,
                "detail_gap_data_available": bool(parsed_missing),
                "degraded_mode": False,
            }

        if not parsed_missing or parsed_last_open_time is None:
            return {
                "real_gap_count": gap_count,
                "real_missing_open_times": list(parsed_missing),
                "trailing_incomplete_count": 0,
                "trailing_incomplete_open_times": [],
                "trailing_incomplete_range_detected": False,
                "detail_gap_data_available": bool(parsed_missing),
                "degraded_mode": True,
            }

        interval_delta = self._interval_to_timedelta(interval)
        requested_day = date.fromisoformat(end_date)
        end_at = datetime.combine(requested_day, time.min, tzinfo=timezone.utc) + timedelta(days=1)
        expected_last_open_time = end_at - interval_delta
        trailing_start = parsed_last_open_time + interval_delta
        trailing_candidate: list[datetime] = []
        cursor = trailing_start
        while cursor < end_at:
            trailing_candidate.append(cursor)
            cursor += interval_delta

        missing_set = set(parsed_missing)
        trailing_detected = (
            parsed_last_open_time.date() == expected_last_open_time.date()
            and bool(trailing_candidate)
            and all(open_time in missing_set for open_time in trailing_candidate)
        )
        resolved_trailing_missing = trailing_candidate if trailing_detected else []
        resolved_trailing_set = set(resolved_trailing_missing)
        resolved_real_missing = [open_time for open_time in parsed_missing if open_time not in resolved_trailing_set]
        return {
            "real_gap_count": len(resolved_real_missing),
            "real_missing_open_times": resolved_real_missing,
            "trailing_incomplete_count": len(resolved_trailing_missing),
            "trailing_incomplete_open_times": resolved_trailing_missing,
            "trailing_incomplete_range_detected": trailing_detected,
            "detail_gap_data_available": True,
            "degraded_mode": False,
        }

    @staticmethod
    def _interval_to_minutes(interval: str) -> int:
        value = int(interval[:-1])
        unit = interval[-1]
        if unit == "m":
            return value
        if unit == "h":
            return value * 60
        if unit == "d":
            return value * 60 * 24
        if unit == "w":
            return value * 60 * 24 * 7
        raise ValueError(f"Unsupported interval for gap diagnostics: {interval}")

    def _interval_to_timedelta(self, interval: str) -> timedelta:
        return timedelta(minutes=self._interval_to_minutes(interval))

    @staticmethod
    def _largest_contiguous_gap(parsed_missing: list[datetime], interval_minutes: int) -> int:
        if not parsed_missing:
            return 0
        step_seconds = interval_minutes * 60
        largest = 1
        current = 1
        for previous, current_item in zip(parsed_missing, parsed_missing[1:]):
            delta_seconds = int((current_item - previous).total_seconds())
            if delta_seconds == step_seconds:
                current += 1
                largest = max(largest, current)
            else:
                current = 1
        return largest

    def _largest_gap_minutes(
        self,
        parsed_missing: list[datetime],
        interval_minutes: int,
        gap_count: int,
    ) -> int:
        largest_gap_candles = self._largest_contiguous_gap(parsed_missing, interval_minutes)
        if largest_gap_candles == 0 and gap_count > 0:
            largest_gap_candles = 1
        return largest_gap_candles * interval_minutes

    @staticmethod
    def _gap_severity(
        *,
        total_missing_candles_estimate: int,
        largest_gap_minutes: int,
    ) -> str:
        if total_missing_candles_estimate == 0:
            return "OK"
        if total_missing_candles_estimate <= 4 and largest_gap_minutes <= 60:
            return "MINOR"
        if total_missing_candles_estimate <= 24 and largest_gap_minutes <= 240:
            return "MODERATE"
        if total_missing_candles_estimate <= 96 and largest_gap_minutes <= 1440:
            return "HIGH"
        return "CRITICAL"

    @staticmethod
    def _warnings(
        *,
        raw_gap_count: int,
        effective_gap_count_for_training: int,
        gap_severity_for_training: str,
        trailing_incomplete_range_detected: bool,
        largest_gap_minutes: int,
        interval_minutes: int,
        degraded_mode: bool,
        detail_gap_data_available: bool,
    ) -> list[str]:
        warnings: list[str] = []
        if raw_gap_count > 0:
            warnings.append("missing_candles_detected")
        if trailing_incomplete_range_detected:
            warnings.append("trailing_incomplete_range_detected")
        if degraded_mode:
            warnings.append("gap_classification_degraded")
        if raw_gap_count > 0 and not detail_gap_data_available:
            warnings.append("detail_gap_data_unavailable")
        if effective_gap_count_for_training > 0 and gap_severity_for_training in {"HIGH", "CRITICAL"}:
            warnings.append("gap_quality_not_clean")
        if largest_gap_minutes >= interval_minutes * 8 and effective_gap_count_for_training > 0:
            warnings.append("large_contiguous_gap_detected")
        return warnings

    @staticmethod
    def _recommendations(
        *,
        gap_severity_for_training: str,
        warnings: list[str],
        trailing_only_gap: bool,
        degraded_mode: bool,
    ) -> list[str]:
        if trailing_only_gap and not degraded_mode:
            return [
                "Trailing incomplete current-day range was excluded from training gap severity.",
                "Keep reviewing real historical gaps separately before trusting the dataset.",
            ]

        recommendations = []
        if degraded_mode:
            recommendations.append("Collect detailed gap timestamps or last_open_time to classify trailing incomplete ranges safely.")
        if gap_severity_for_training == "OK":
            recommendations.append("Gap check is clean enough for training.")
        else:
            recommendations.extend(
                [
                    "Review gap timestamps before accepting a training candidate.",
                    "Re-run candle loading over the affected period to reduce real historical gaps.",
                ]
            )
        if "trailing_incomplete_range_detected" in warnings and gap_severity_for_training != "OK":
            recommendations.append("Wait for the current trading day to complete before rechecking mixed gap periods.")
        if gap_severity_for_training in {"HIGH", "CRITICAL"}:
            recommendations.append("Treat current dataset quality as insufficient for a reliable research candidate.")
        return list(dict.fromkeys(recommendations))
