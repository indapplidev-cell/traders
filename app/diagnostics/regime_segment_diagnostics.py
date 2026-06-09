from __future__ import annotations

from typing import Any, Callable


class RegimeSegmentDiagnostics:
    SEGMENT_KEYS = [
        "regime_trend_up",
        "regime_trend_down",
        "regime_range",
        "regime_high_volatility",
        "regime_low_volatility",
        "regime_volatility_expanding",
        "regime_volatility_contracting",
        "ema_stack_bullish",
        "ema_stack_bearish",
        "close_above_ema_200",
        "close_below_ema_200",
    ]

    def build_report(
        self,
        dataset_rows: list[Any],
        long_evaluator: Callable[[list[Any]], dict[str, Any]],
        short_evaluator: Callable[[list[Any]], dict[str, Any]],
        ema_baseline_evaluator: Callable[[list[Any]], dict[str, Any]],
    ) -> dict[str, Any]:
        segments = {
            segment_key: self._segment_report(
                segment_key=segment_key,
                dataset_rows=dataset_rows,
                long_evaluator=long_evaluator,
                short_evaluator=short_evaluator,
                ema_baseline_evaluator=ema_baseline_evaluator,
            )
            for segment_key in self.SEGMENT_KEYS
        }
        return {"segments": segments}

    def _segment_report(
        self,
        segment_key: str,
        dataset_rows: list[Any],
        long_evaluator: Callable[[list[Any]], dict[str, Any]],
        short_evaluator: Callable[[list[Any]], dict[str, Any]],
        ema_baseline_evaluator: Callable[[list[Any]], dict[str, Any]],
    ) -> dict[str, Any]:
        rows = [row for row in dataset_rows if self._match_segment(row, segment_key)]
        total_rows = len(dataset_rows)
        actual_counts = {
            "UP": sum(int(row.direction_label == "UP") for row in rows),
            "DOWN": sum(int(row.direction_label == "DOWN") for row in rows),
            "FLAT": sum(int(row.direction_label == "FLAT") for row in rows),
        }
        long_report = long_evaluator(rows)
        short_report = short_evaluator(rows)
        ema_report = ema_baseline_evaluator(rows)
        ema_profit_factor = ema_report.get("global_profit_factor")
        if ema_profit_factor is None:
            ema_profit_factor = ema_report.get("profit_factor")
        better_side = "FLAT"
        if float(long_report.get("total_r", 0.0)) > float(short_report.get("total_r", 0.0)):
            better_side = "LONG"
        elif float(short_report.get("total_r", 0.0)) > float(long_report.get("total_r", 0.0)):
            better_side = "SHORT"
        warnings: list[str] = []
        if len(rows) < 50:
            warnings.append("too_few_rows")
        if float(short_report.get("total_r", 0.0)) <= 0.0:
            warnings.append("no_short_opportunity")
        if float(long_report.get("total_r", 0.0)) <= 0.0:
            warnings.append("no_long_opportunity")
        if float(ema_report.get("total_r", 0.0)) <= 0.0 or float(ema_profit_factor or 0.0) <= 1.0:
            warnings.append("ema_baseline_unprofitable")
        if rows and abs((actual_counts["UP"] / len(rows)) - (actual_counts["DOWN"] / len(rows))) >= 0.25:
            warnings.append("side_bias_detected")
        return {
            "row_count": len(rows),
            "row_ratio": (len(rows) / total_rows) if total_rows else 0.0,
            "actual_counts": actual_counts,
            "actual_ratios": {
                key: (value / len(rows)) if rows else 0.0
                for key, value in actual_counts.items()
            },
            "long_opportunity_total_r": long_report.get("total_r"),
            "short_opportunity_total_r": short_report.get("total_r"),
            "better_side": better_side,
            "ema_9_21_baseline_total_r": ema_report.get("total_r"),
            "ema_9_21_baseline_profit_factor": ema_profit_factor,
            "ema_9_21_signal_count": ema_report.get("signal_count"),
            "warnings": warnings,
        }

    @staticmethod
    def _match_segment(row: Any, segment_key: str) -> bool:
        if segment_key == "close_below_ema_200":
            value = row.features_json.get("close_above_ema_200")
            return value is not None and float(value) == 0.0
        value = row.features_json.get(segment_key)
        return value is not None and float(value) == 1.0
