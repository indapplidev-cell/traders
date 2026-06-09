from __future__ import annotations

from typing import Any


class DirectionalOpportunityDiagnostics:
    def build_report(
        self,
        symbol: str,
        interval: str,
        feature_version: str,
        label_version: str,
        folds: list[dict[str, Any]],
    ) -> dict[str, Any]:
        warnings = sorted({warning for fold in folds for warning in fold["warnings"]})
        summary = self._build_summary(folds)
        return {
            "symbol": symbol,
            "interval": interval,
            "feature_version": feature_version,
            "label_version": label_version,
            "fold_count": len(folds),
            "folds": folds,
            "summary": summary,
            "warnings": warnings,
        }

    def _build_summary(self, folds: list[dict[str, Any]]) -> dict[str, Any]:
        test_long_total_r = sum(float(fold["test"]["long"]["total_r"]) for fold in folds)
        test_short_total_r = sum(float(fold["test"]["short"]["total_r"]) for fold in folds)
        short_opportunities_exist = any(self._is_profitable(fold["test"]["short"]) for fold in folds)
        long_opportunities_exist = any(self._is_profitable(fold["test"]["long"]) for fold in folds)
        better_side = "LONG" if test_long_total_r >= test_short_total_r else "SHORT"
        return {
            "short_opportunities_exist": short_opportunities_exist,
            "long_opportunities_exist": long_opportunities_exist,
            "test_long_total_r": test_long_total_r,
            "test_short_total_r": test_short_total_r,
            "better_side": better_side,
        }

    @staticmethod
    def _is_profitable(summary: dict[str, Any]) -> bool:
        profit_factor = summary.get("profit_factor")
        return (
            int(summary.get("signal_count", 0)) > 0
            and profit_factor is not None
            and float(profit_factor) > 1.0
            and float(summary.get("total_r", 0.0)) > 0.0
        )

    def build_fold_report(
        self,
        fold: dict[str, Any],
        validation_long: dict[str, Any],
        validation_short: dict[str, Any],
        test_long: dict[str, Any],
        test_short: dict[str, Any],
    ) -> dict[str, Any]:
        warnings: list[str] = []
        if int(test_short.get("signal_count", 0)) == 0:
            warnings.append("no_short_opportunity")
        if int(test_long.get("signal_count", 0)) == 0:
            warnings.append("no_long_opportunity")
        if self._is_profitable(test_long) and not self._is_profitable(test_short):
            warnings.append("long_only_market_segment")
        if self._is_profitable(test_short) and not self._is_profitable(test_long):
            warnings.append("short_only_market_segment")
        if not self._is_profitable(test_long) and not self._is_profitable(test_short):
            warnings.append("both_sides_unprofitable")

        return {
            "fold_index": fold["fold_index"],
            "train_start": fold["train_start"],
            "train_end": fold["train_end"],
            "validation_start": fold["validation_start"],
            "validation_end": fold["validation_end"],
            "test_start": fold["test_start"],
            "test_end": fold["test_end"],
            "validation": {
                "long": self._shape_side_summary(validation_long),
                "short": self._shape_side_summary(validation_short),
                "better_side": self._better_side(validation_long, validation_short),
            },
            "test": {
                "long": self._shape_side_summary(test_long),
                "short": self._shape_side_summary(test_short),
                "better_side": self._better_side(test_long, test_short),
            },
            "warnings": sorted(set(warnings)),
        }

    @staticmethod
    def _better_side(long_summary: dict[str, Any], short_summary: dict[str, Any]) -> str:
        long_total_r = float(long_summary.get("total_r", 0.0))
        short_total_r = float(short_summary.get("total_r", 0.0))
        return "LONG" if long_total_r >= short_total_r else "SHORT"

    @staticmethod
    def _shape_side_summary(summary: dict[str, Any]) -> dict[str, Any]:
        return {
            "signal_count": int(summary.get("signal_count", 0)),
            "long_tp_first_count": int(summary.get("win_count", 0)),
            "long_stop_first_count": int(summary.get("loss_count", 0)),
            "long_neither_count": int(summary.get("neither_count", 0)),
            "short_tp_first_count": int(summary.get("win_count", 0)),
            "short_stop_first_count": int(summary.get("loss_count", 0)),
            "short_neither_count": int(summary.get("neither_count", 0)),
            "gross_profit_r": float(summary.get("gross_profit_r", 0.0)),
            "gross_loss_r": float(summary.get("gross_loss_r", 0.0)),
            "profit_factor": summary.get("profit_factor"),
            "total_r": float(summary.get("total_r", 0.0)),
            "expectancy_r": summary.get("expectancy_r"),
            "win_rate": summary.get("win_rate"),
        }
