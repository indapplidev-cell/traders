from __future__ import annotations

from datetime import datetime
from typing import Any


class GapQualityDiagnostics:
    DIAGNOSTIC_NAME = "gap_quality_diagnostics"
    DIAGNOSTIC_VERSION = "ml27"

    def analyze(
        self,
        *,
        symbol: str,
        interval: str,
        start_date: str,
        end_date: str,
        gap_count: int,
        missing_open_times: list[str] | None = None,
    ) -> dict[str, Any]:
        interval_minutes = self._interval_to_minutes(interval)
        missing_open_times = missing_open_times or []
        parsed_missing = sorted(
            datetime.fromisoformat(value)
            for value in missing_open_times
        )
        total_missing_candles_estimate = len(parsed_missing) if parsed_missing else int(gap_count)
        largest_gap_candles = self._largest_contiguous_gap(parsed_missing, interval_minutes)
        if largest_gap_candles == 0 and total_missing_candles_estimate > 0:
            largest_gap_candles = 1
        largest_gap_minutes = largest_gap_candles * interval_minutes
        gap_severity = self._gap_severity(
            total_missing_candles_estimate=total_missing_candles_estimate,
            largest_gap_minutes=largest_gap_minutes,
        )
        dataset_safe_for_training = gap_severity in {"OK", "MINOR"}
        warnings = self._warnings(
            gap_severity=gap_severity,
            total_missing_candles_estimate=total_missing_candles_estimate,
            largest_gap_minutes=largest_gap_minutes,
            parsed_missing=parsed_missing,
            interval_minutes=interval_minutes,
        )
        return {
            "diagnostic_name": self.DIAGNOSTIC_NAME,
            "diagnostic_version": self.DIAGNOSTIC_VERSION,
            "symbol": symbol,
            "interval": interval,
            "start_date": start_date,
            "end_date": end_date,
            "expected_interval_minutes": interval_minutes,
            "gap_count": int(gap_count),
            "largest_gap_minutes": largest_gap_minutes,
            "total_missing_candles_estimate": total_missing_candles_estimate,
            "gap_severity": gap_severity,
            "dataset_safe_for_training": dataset_safe_for_training,
            "warnings": warnings,
            "recommendations": self._recommendations(
                gap_severity=gap_severity,
                warnings=warnings,
            ),
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
        gap_severity: str,
        total_missing_candles_estimate: int,
        largest_gap_minutes: int,
        parsed_missing: list[datetime],
        interval_minutes: int,
    ) -> list[str]:
        warnings: list[str] = []
        if gap_severity in {"HIGH", "CRITICAL"}:
            warnings.append("gap_quality_not_clean")
        if total_missing_candles_estimate > 0:
            warnings.append("missing_candles_detected")
        if largest_gap_minutes >= interval_minutes * 8:
            warnings.append("large_contiguous_gap_detected")
        if GapQualityDiagnostics._is_trailing_gap(parsed_missing, interval_minutes):
            warnings.append("trailing_incomplete_range_detected")
        return warnings

    @staticmethod
    def _recommendations(*, gap_severity: str, warnings: list[str]) -> list[str]:
        if gap_severity == "OK":
            return ["Gap check is clean enough for training."]
        recommendations = [
            "Review gap timestamps before accepting a training candidate.",
            "Re-run candle loading over the affected period to reduce missing candles.",
        ]
        if "trailing_incomplete_range_detected" in warnings:
            recommendations.append("Prefer running the pipeline after the current trading day is complete.")
        if gap_severity in {"HIGH", "CRITICAL"}:
            recommendations.append("Treat current dataset quality as insufficient for a reliable research candidate.")
        return recommendations

    @staticmethod
    def _is_trailing_gap(parsed_missing: list[datetime], interval_minutes: int) -> bool:
        if len(parsed_missing) < 2:
            return False
        step_seconds = interval_minutes * 60
        for previous, current in zip(parsed_missing, parsed_missing[1:]):
            if int((current - previous).total_seconds()) != step_seconds:
                return False
        return True
