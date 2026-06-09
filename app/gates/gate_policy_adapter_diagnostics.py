"""End-to-end диагностика GatePolicy adapter.

Модуль принимает raw payload-словари, преобразует их в GatePolicyInput,
прогоняет через GatePolicyDiagnosticsService и возвращает полный результат.
Он не запускает модель, не читает БД и не подключается к traders-core.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from app.gates.gate_policy_adapter import GatePolicyEvaluationAdapter
from app.gates.gate_policy_diagnostics import (
    GatePolicyDiagnosticsReport,
    GatePolicyDiagnosticsService,
)
from app.gates.gate_policy_models import GatePolicyInput, GatePolicyResult


@dataclass(frozen=True)
class GatePolicyAdapterDiagnosticsResult:
    """Полный результат диагностики raw payload-набора."""

    inputs: tuple[GatePolicyInput, ...]
    results: tuple[GatePolicyResult, ...]
    report: GatePolicyDiagnosticsReport


class GatePolicyAdapterDiagnosticsService:
    """End-to-end сервис диагностики raw GatePolicy payload."""

    def __init__(
        self,
        *,
        adapter: GatePolicyEvaluationAdapter | None = None,
        diagnostics: GatePolicyDiagnosticsService | None = None,
    ) -> None:
        self.adapter = adapter or GatePolicyEvaluationAdapter()
        self.diagnostics = diagnostics or GatePolicyDiagnosticsService()

    def evaluate_payloads(
        self,
        payloads: Sequence[Mapping[str, Any]],
    ) -> GatePolicyAdapterDiagnosticsResult:
        """Преобразовать raw payloads и построить GatePolicy диагностику."""

        inputs = self.adapter.from_mappings(payloads)
        results = self.diagnostics.evaluate_many(inputs)
        report = self.diagnostics.build_report(inputs)

        return GatePolicyAdapterDiagnosticsResult(
            inputs=inputs,
            results=results,
            report=report,
        )
