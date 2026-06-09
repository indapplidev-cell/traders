"""Диагностика результатов GatePolicy.

Модуль агрегирует решения политики допуска по набору ML-сигналов.
Он не торгует, не запускает модель и не подключается к traders-core.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping, Sequence

from app.gates.gate_policy_models import GatePolicyInput, GatePolicyResult
from app.gates.gate_policy_service import GatePolicyService


@dataclass(frozen=True)
class GatePolicyDiagnosticsReport:
    """Сводка по результатам политики допуска."""

    total: int
    allowed_total: int
    blocked_total: int
    decision_counts: Mapping[str, int] = field(default_factory=dict)
    regime_counts: Mapping[str, int] = field(default_factory=dict)
    direction_counts: Mapping[str, int] = field(default_factory=dict)
    reason_counts: Mapping[str, int] = field(default_factory=dict)

    @staticmethod
    def build(
        *,
        total: int,
        allowed_total: int,
        blocked_total: int,
        decision_counts: Mapping[str, int],
        regime_counts: Mapping[str, int],
        direction_counts: Mapping[str, int],
        reason_counts: Mapping[str, int],
    ) -> "GatePolicyDiagnosticsReport":
        """Создать неизменяемый диагностический отчёт."""

        return GatePolicyDiagnosticsReport(
            total=total,
            allowed_total=allowed_total,
            blocked_total=blocked_total,
            decision_counts=MappingProxyType(dict(decision_counts)),
            regime_counts=MappingProxyType(dict(regime_counts)),
            direction_counts=MappingProxyType(dict(direction_counts)),
            reason_counts=MappingProxyType(dict(reason_counts)),
        )


class GatePolicyDiagnosticsService:
    """Сервис пакетной диагностики GatePolicy."""

    def __init__(self, policy_service: GatePolicyService | None = None) -> None:
        self.policy_service = policy_service or GatePolicyService()

    def evaluate_many(
        self,
        signals: Sequence[GatePolicyInput],
    ) -> tuple[GatePolicyResult, ...]:
        """Оценить набор ML-сигналов и сохранить порядок результатов."""

        return tuple(self.policy_service.evaluate(signal) for signal in signals)

    def build_report(
        self,
        signals: Sequence[GatePolicyInput],
    ) -> GatePolicyDiagnosticsReport:
        """Построить агрегированную диагностику по набору ML-сигналов."""

        results = self.evaluate_many(signals)

        total = len(results)
        allowed_total = sum(1 for result in results if result.allowed)
        blocked_total = total - allowed_total

        decision_counts: Counter[str] = Counter()
        regime_counts: Counter[str] = Counter()
        direction_counts: Counter[str] = Counter()
        reason_counts: Counter[str] = Counter()

        for result in results:
            decision_counts[result.decision.value] += 1
            regime_counts[result.regime] += 1
            direction_counts[result.direction.value] += 1

            for reason in result.reasons:
                reason_counts[reason] += 1

        return GatePolicyDiagnosticsReport.build(
            total=total,
            allowed_total=allowed_total,
            blocked_total=blocked_total,
            decision_counts=dict(decision_counts),
            regime_counts=dict(regime_counts),
            direction_counts=dict(direction_counts),
            reason_counts=dict(reason_counts),
        )
