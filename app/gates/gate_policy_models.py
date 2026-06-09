"""Модели политики допуска ML-сигналов.

Модуль не торгует и не активирует модель автоматически.
Он только описывает вход, выход и настройки risk-first допуска ML-сигнала.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping


class GatePolicyDecision(str, Enum):
    """Итоговое решение политики допуска."""

    ALLOW_LONG = "ALLOW_LONG"
    ALLOW_SHORT = "ALLOW_SHORT"
    BLOCK = "BLOCK"
    MODEL_UNTRUSTED = "MODEL_UNTRUSTED"
    BASELINE_BETTER = "BASELINE_BETTER"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    BAD_REGIME = "BAD_REGIME"


class GateDirection(str, Enum):
    """Направление ML-сигнала."""

    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"
    NONE = "NONE"


@dataclass(frozen=True)
class GatePolicyConfig:
    """Консервативная конфигурация политики допуска."""

    trusted_regimes: tuple[str, ...] = (
        "trend_up",
        "trend_down",
        "breakout_setup",
    )

    blocked_regimes: tuple[str, ...] = (
        "range",
        "high_volatility",
        "low_volatility",
        "low_liquidity",
        "unknown",
    )

    min_confidence: float = 0.60
    min_tp_before_sl_probability: float = 0.55
    max_risk_score: float = 0.65
    min_sample_count: int = 30

    baseline_total_r_margin: float = 0.0
    baseline_profit_factor_margin: float = 0.05


@dataclass(frozen=True)
class GatePolicyInput:
    """Входные данные для оценки ML-сигнала."""

    regime: str
    direction: GateDirection | str
    confidence: float
    tp_before_sl_probability: float

    risk_score: float | None = None
    expected_move_atr: float | None = None

    model_total_r: float | None = None
    baseline_total_r: float | None = None

    model_profit_factor: float | None = None
    baseline_profit_factor: float | None = None

    sample_count: int | None = None

    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GatePolicyResult:
    """Результат оценки политики допуска."""

    decision: GatePolicyDecision
    allowed: bool
    regime: str
    direction: GateDirection
    reasons: tuple[str, ...]
    thresholds: Mapping[str, Any] = field(default_factory=dict)

    @staticmethod
    def build(
        *,
        decision: GatePolicyDecision,
        allowed: bool,
        regime: str,
        direction: GateDirection,
        reasons: tuple[str, ...],
        thresholds: Mapping[str, Any],
    ) -> "GatePolicyResult":
        """Создать результат с неизменяемыми thresholds."""

        return GatePolicyResult(
            decision=decision,
            allowed=allowed,
            regime=regime,
            direction=direction,
            reasons=reasons,
            thresholds=MappingProxyType(dict(thresholds)),
        )
