from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ConfidenceProfitabilityDiagnosticsResult:
    diagnostic_name: str
    diagnostic_version: str
    symbol: str | None
    config_id: str | None
    margin_q50: float | None
    margin_q90: float | None
    max_prob_q90: float | None
    rows_above_045: int | None
    walk_forward_profit_factor: float | None
    walk_forward_total_r: float | None
    profit_aware_profit_factor: float | None
    profit_aware_total_r: float | None
    anti_collapse_score: float | None
    anti_collapse_status: str | None
    collapse_detected: bool
    collapse_type: str | None
    confidence_profitability_score: float
    confidence_profitability_status: str
    recommendations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "diagnostic_name": self.diagnostic_name,
            "diagnostic_version": self.diagnostic_version,
            "symbol": self.symbol,
            "config_id": self.config_id,
            "margin_q50": self.margin_q50,
            "margin_q90": self.margin_q90,
            "max_prob_q90": self.max_prob_q90,
            "rows_above_045": self.rows_above_045,
            "walk_forward_profit_factor": self.walk_forward_profit_factor,
            "walk_forward_total_r": self.walk_forward_total_r,
            "profit_aware_profit_factor": self.profit_aware_profit_factor,
            "profit_aware_total_r": self.profit_aware_total_r,
            "anti_collapse_score": self.anti_collapse_score,
            "anti_collapse_status": self.anti_collapse_status,
            "collapse_detected": self.collapse_detected,
            "collapse_type": self.collapse_type,
            "confidence_profitability_score": self.confidence_profitability_score,
            "confidence_profitability_status": self.confidence_profitability_status,
            "recommendations": list(self.recommendations),
            "safety": {
                "accepts_candidate": False,
                "softens_gates": False,
                "auto_activation": False,
                "live_trading": False,
            },
        }


class ConfidenceProfitabilityDiagnostics:
    """ML38.6 диагностика confidence collapse + profitability.

    Не принимает модель сама.
    Не смягчает gates.
    Используется только для ranking/reporting и выбора следующего эксперимента.
    """

    DIAGNOSTIC_NAME = "confidence_profitability_diagnostics"
    DIAGNOSTIC_VERSION = "ml38_6"

    def build(
        self,
        *,
        symbol: str | None,
        config_id: str | None,
        probability_diagnostics: dict[str, Any] | None,
        collapse_diagnostics_v2: dict[str, Any] | None,
        profit_aware_diagnostics: dict[str, Any] | None,
        walk_forward_profit_diagnostics: dict[str, Any] | None,
        anti_collapse_diagnostics: dict[str, Any] | None,
    ) -> ConfidenceProfitabilityDiagnosticsResult:
        probability_diagnostics = probability_diagnostics or {}
        collapse_diagnostics_v2 = collapse_diagnostics_v2 or {}
        profit_aware_diagnostics = profit_aware_diagnostics or {}
        walk_forward_profit_diagnostics = walk_forward_profit_diagnostics or {}
        anti_collapse_diagnostics = anti_collapse_diagnostics or {}

        probability_margin_distribution = dict(
            collapse_diagnostics_v2.get("probability_margin_distribution") or {}
        )
        confidence_distribution = dict(
            collapse_diagnostics_v2.get("confidence_distribution") or {}
        )
        rows_above_thresholds = dict(
            confidence_distribution.get("rows_above_thresholds")
            or probability_diagnostics.get("rows_above_thresholds")
            or {}
        )

        margin_q50 = self._first_float(
            probability_margin_distribution.get("margin_q50"),
            probability_diagnostics.get("margin_q50"),
        )
        margin_q90 = self._first_float(
            probability_margin_distribution.get("margin_q90"),
            probability_diagnostics.get("margin_q90"),
        )
        max_prob_q90 = self._first_float(
            confidence_distribution.get("max_prob_q90"),
            probability_diagnostics.get("max_prob_q90"),
        )
        rows_above_045 = self._optional_int(
            rows_above_thresholds.get("0.45")
            if "0.45" in rows_above_thresholds
            else rows_above_thresholds.get("0.45".rstrip("0"))
        )

        walk_forward_profit_factor = self._first_float(
            walk_forward_profit_diagnostics.get("walk_forward_profit_factor"),
            walk_forward_profit_diagnostics.get("global_profit_factor"),
        )
        walk_forward_total_r = self._first_float(
            walk_forward_profit_diagnostics.get("walk_forward_total_r"),
            walk_forward_profit_diagnostics.get("global_total_r"),
        )
        profit_aware_profit_factor = self._first_float(
            profit_aware_diagnostics.get("profit_aware_profit_factor"),
            profit_aware_diagnostics.get("profit_factor"),
        )
        profit_aware_total_r = self._first_float(
            profit_aware_diagnostics.get("profit_aware_total_r"),
            profit_aware_diagnostics.get("total_r"),
        )
        anti_collapse_score = self._optional_float(
            anti_collapse_diagnostics.get("anti_collapse_score")
        )
        anti_collapse_status = (
            str(anti_collapse_diagnostics.get("anti_collapse_status") or "UNKNOWN").upper()
            if anti_collapse_diagnostics
            else None
        )
        collapse_detected = bool(collapse_diagnostics_v2.get("collapse_detected", False))
        collapse_type = collapse_diagnostics_v2.get("collapse_type")

        score = 0.0
        recommendations: list[str] = []

        if margin_q50 is not None:
            if margin_q50 >= 0.035:
                score += 2.0
            elif margin_q50 >= 0.025:
                score += 1.0
            else:
                score -= 2.0
                recommendations.append("Increase probability separation: margin_q50 is too low.")

        if margin_q90 is not None:
            if margin_q90 >= 0.075:
                score += 2.0
            elif margin_q90 >= 0.055:
                score += 1.0
            else:
                score -= 1.0
                recommendations.append("Increase high-confidence tail: margin_q90 is weak.")

        if max_prob_q90 is not None:
            if max_prob_q90 >= 0.45:
                score += 1.0
            elif max_prob_q90 < 0.40:
                score -= 1.0
                recommendations.append("Model remains too uniform: max_prob_q90 is below 0.40.")

        if rows_above_045 is not None:
            if rows_above_045 >= 50:
                score += 1.0
            elif rows_above_045 <= 0:
                score -= 1.5
                recommendations.append("No usable confidence-filtered rows above 0.45.")

        if walk_forward_profit_factor is not None and walk_forward_total_r is not None:
            if walk_forward_profit_factor > 1.0 and walk_forward_total_r > 0.0:
                score += 2.5
            else:
                score -= 2.0
                recommendations.append("Walk-forward profitability is not stable enough.")

        if profit_aware_profit_factor is not None and profit_aware_total_r is not None:
            if profit_aware_profit_factor > 1.0 and profit_aware_total_r > 0.0:
                score += 1.5
            else:
                score -= 1.0
                recommendations.append("Profit-aware filter does not produce positive R and PF.")

        if anti_collapse_score is not None:
            if anti_collapse_score >= 4.0:
                score += 1.0
            elif anti_collapse_score >= 1.0:
                score += 0.5
            else:
                score -= 0.5

        if anti_collapse_status == "GOOD":
            score += 0.5
        elif anti_collapse_status == "WEAK":
            score -= 0.5

        if collapse_detected:
            score -= 3.0
            recommendations.append(f"Collapse still detected: {collapse_type or 'unknown'}.")

        if score >= 5.0:
            status = "GOOD"
        elif score >= 1.5:
            status = "WATCH"
        else:
            status = "WEAK"

        if not recommendations:
            recommendations.append("Confidence/profitability diagnostics look promising for research review.")

        return ConfidenceProfitabilityDiagnosticsResult(
            diagnostic_name=self.DIAGNOSTIC_NAME,
            diagnostic_version=self.DIAGNOSTIC_VERSION,
            symbol=symbol,
            config_id=config_id,
            margin_q50=margin_q50,
            margin_q90=margin_q90,
            max_prob_q90=max_prob_q90,
            rows_above_045=rows_above_045,
            walk_forward_profit_factor=walk_forward_profit_factor,
            walk_forward_total_r=walk_forward_total_r,
            profit_aware_profit_factor=profit_aware_profit_factor,
            profit_aware_total_r=profit_aware_total_r,
            anti_collapse_score=anti_collapse_score,
            anti_collapse_status=anti_collapse_status,
            collapse_detected=collapse_detected,
            collapse_type=None if collapse_type is None else str(collapse_type),
            confidence_profitability_score=round(score, 6),
            confidence_profitability_status=status,
            recommendations=list(dict.fromkeys(recommendations)),
        )

    @classmethod
    def _first_float(cls, *values: Any) -> float | None:
        for value in values:
            parsed = cls._optional_float(value)
            if parsed is not None:
                return parsed
        return None

    @staticmethod
    def _optional_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None
        if parsed in {float("inf"), float("-inf")}:
            return None
        return parsed

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
