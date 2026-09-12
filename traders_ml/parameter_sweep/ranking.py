"""Deterministic multi-metric ranking and overfitting controls."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from app.config.yaml_authority import RESEARCH_PARAMETERS
from .research_protocol import assert_validation_only_rows


PERFORMANCE_CLASSES = (
    "INVALID", "INSUFFICIENT_SAMPLE", "NEGATIVE_EXPECTANCY", "WEAK",
    "PROMISING_RESEARCH", "VALIDATION_CANDIDATE",
)


def rank_score(row: Mapping[str, Any]) -> tuple[float, ...]:
    trades = int(row.get("trade_count") or 0)
    expectancy = float(row.get("expectancy_R") or -1e12)
    pf = float(row.get("profit_factor") or 0)
    drawdown = float(row.get("max_drawdown") or 0)
    stability = float(row.get("rank_stability") or 0)
    symbols = int(row.get("symbol_coverage") or 0)
    return (expectancy, pf, -drawdown, min(trades, RESEARCH_PARAMETERS.ranking.minimum_trades), symbols, stability)


def rank_results(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    values = list(rows)
    assert_validation_only_rows(values)
    eligible = [row for row in values if row.get("evaluation_status") == "ACCEPTED"]
    return sorted(eligible, key=lambda row: (rank_score(row), str(row.get("config_id"))), reverse=True)


def selection_bias_guard(*, hypothesis_count: int, independent_observations: int) -> str:
    threshold = RESEARCH_PARAMETERS.ranking.selection_bias_hypotheses_per_observation
    if independent_observations <= 0 or hypothesis_count / independent_observations > threshold:
        return "PROMOTION_FORBIDDEN_SELECTION_BIAS_RISK"
    return "PASS"


def rank_stability(period_expectancies: Iterable[float]) -> float:
    values = [float(value) for value in period_expectancies]
    if not values:
        return 0.0
    positive_share = sum(value > 0 for value in values) / len(values)
    if len(values) == 1:
        return positive_share
    spread = max(values) - min(values)
    scale = max(abs(value) for value in values) or 1.0
    smoothness = max(0.0, 1.0 - spread / (2 * scale))
    return round(positive_share * smoothness, 12)


def pareto_frontier(rows: Iterable[dict[str, Any]]) -> list[str]:
    values = list(rows)
    result = []
    for point in values:
        dominated = any(
            other is not point
            and float(other.get("expectancy_R") or -1e12) >= float(point.get("expectancy_R") or -1e12)
            and float(other.get("max_drawdown") or 1e12) <= float(point.get("max_drawdown") or 1e12)
            and int(other.get("trade_count") or 0) >= int(point.get("trade_count") or 0)
            and (
                float(other.get("expectancy_R") or -1e12) > float(point.get("expectancy_R") or -1e12)
                or float(other.get("max_drawdown") or 1e12) < float(point.get("max_drawdown") or 1e12)
                or int(other.get("trade_count") or 0) > int(point.get("trade_count") or 0)
            )
            for other in values
        )
        if not dominated:
            result.append(str(point.get("config_id")))
    return sorted(result)
