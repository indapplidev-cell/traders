"""Anti-collapse diagnostics for ML38.5.

Диагностика не принимает модель сама.
Она только считает, насколько candidate уменьшает:
- FLAT bias;
- DOWN blindness;
- слабое разделение вероятностей.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AntiCollapseDiagnosticsResult:
    diagnostic_name: str
    diagnostic_version: str
    symbol: str | None
    config_id: str | None
    flat_overprediction_ratio: float | None
    down_prediction_coverage_ratio: float | None
    up_prediction_coverage_ratio: float | None
    margin_q50: float | None
    margin_q90: float | None
    anti_collapse_score: float
    anti_collapse_status: str
    recommendations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "diagnostic_name": self.diagnostic_name,
            "diagnostic_version": self.diagnostic_version,
            "symbol": self.symbol,
            "config_id": self.config_id,
            "flat_overprediction_ratio": self.flat_overprediction_ratio,
            "down_prediction_coverage_ratio": self.down_prediction_coverage_ratio,
            "up_prediction_coverage_ratio": self.up_prediction_coverage_ratio,
            "margin_q50": self.margin_q50,
            "margin_q90": self.margin_q90,
            "anti_collapse_score": self.anti_collapse_score,
            "anti_collapse_status": self.anti_collapse_status,
            "recommendations": list(self.recommendations),
        }


class AntiCollapseDiagnostics:
    """Считает anti-collapse score по уже существующим diagnostics.

    Важно: этот score используется только для анализа и ranking.
    Он не смягчает gates и не принимает модель автоматически.
    """

    diagnostic_name = "anti_collapse_diagnostics"
    diagnostic_version = "ml38_5"

    def build(
        self,
        *,
        symbol: str | None,
        config_id: str | None,
        flat_bias_diagnostics: dict[str, Any] | None,
        collapse_diagnostics_v2: dict[str, Any] | None,
    ) -> AntiCollapseDiagnosticsResult:
        flat_bias_diagnostics = flat_bias_diagnostics or {}
        collapse_diagnostics_v2 = collapse_diagnostics_v2 or {}

        flat_overprediction_ratio = self._optional_float(
            flat_bias_diagnostics.get("flat_overprediction_ratio")
        )
        down_prediction_coverage_ratio = self._optional_float(
            flat_bias_diagnostics.get("down_underprediction_ratio")
        )
        up_prediction_coverage_ratio = self._optional_float(
            flat_bias_diagnostics.get("up_bias_ratio")
        )

        probability_margin_distribution = dict(
            collapse_diagnostics_v2.get("probability_margin_distribution") or {}
        )
        margin_q50 = self._optional_float(probability_margin_distribution.get("margin_q50"))
        margin_q90 = self._optional_float(probability_margin_distribution.get("margin_q90"))

        score = 0.0
        recommendations: list[str] = []

        if flat_overprediction_ratio is not None:
            if flat_overprediction_ratio <= 1.20:
                score += 2.0
            elif flat_overprediction_ratio <= 1.50:
                score += 0.75
            else:
                score -= 2.0
                recommendations.append("Снизить FLAT-перекос: модель слишком часто выбирает FLAT.")

        if down_prediction_coverage_ratio is not None:
            if 0.75 <= down_prediction_coverage_ratio <= 1.35:
                score += 2.0
            elif 0.50 <= down_prediction_coverage_ratio <= 1.60:
                score += 0.5
            else:
                score -= 2.0
                recommendations.append("Снизить down blindness: DOWN класс предсказывается слишком редко или слишком часто.")

        if up_prediction_coverage_ratio is not None:
            if 0.75 <= up_prediction_coverage_ratio <= 1.35:
                score += 1.0
            elif up_prediction_coverage_ratio < 0.50 or up_prediction_coverage_ratio > 1.75:
                score -= 1.0
                recommendations.append("Проверить UP coverage: UP класс распределён неадекватно относительно actual.")

        if margin_q50 is not None:
            if margin_q50 >= 0.03:
                score += 1.0
            elif margin_q50 < 0.015:
                score -= 1.0
                recommendations.append("Усилить разделение вероятностей: margin_q50 слишком низкий.")

        if margin_q90 is not None:
            if margin_q90 >= 0.06:
                score += 1.0
            elif margin_q90 < 0.04:
                score -= 0.5

        if score >= 4.0:
            status = "GOOD"
        elif score >= 1.0:
            status = "WATCH"
        else:
            status = "WEAK"

        return AntiCollapseDiagnosticsResult(
            diagnostic_name=self.diagnostic_name,
            diagnostic_version=self.diagnostic_version,
            symbol=symbol,
            config_id=config_id,
            flat_overprediction_ratio=flat_overprediction_ratio,
            down_prediction_coverage_ratio=down_prediction_coverage_ratio,
            up_prediction_coverage_ratio=up_prediction_coverage_ratio,
            margin_q50=margin_q50,
            margin_q90=margin_q90,
            anti_collapse_score=round(score, 6),
            anti_collapse_status=status,
            recommendations=recommendations,
        )

    @staticmethod
    def _optional_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        if numeric in {float("inf"), float("-inf")}:
            return None
        return numeric
