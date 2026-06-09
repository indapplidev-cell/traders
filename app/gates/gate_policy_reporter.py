"""JSON-репортёр для GatePolicy.

Модуль отвечает только за форматирование результатов политики допуска.
Он не принимает торговых решений, не запускает модель и не подключается к traders-core.
"""

from __future__ import annotations

import json
from typing import Any

from app.gates.gate_policy_diagnostics import GatePolicyDiagnosticsReport
from app.gates.gate_policy_models import GatePolicyResult


class GatePolicyReporter:
    """Сериализация результатов GatePolicy в dict/JSON."""

    def result_to_dict(self, result: GatePolicyResult) -> dict[str, Any]:
        """Преобразовать одиночный результат GatePolicy в словарь."""

        return {
            "decision": result.decision.value,
            "allowed": result.allowed,
            "regime": result.regime,
            "direction": result.direction.value,
            "reasons": list(result.reasons),
            "thresholds": dict(result.thresholds),
        }

    def report_to_dict(
        self,
        report: GatePolicyDiagnosticsReport,
    ) -> dict[str, Any]:
        """Преобразовать агрегированный диагностический отчёт в словарь."""

        return {
            "total": report.total,
            "allowed_total": report.allowed_total,
            "blocked_total": report.blocked_total,
            "decision_counts": dict(report.decision_counts),
            "regime_counts": dict(report.regime_counts),
            "direction_counts": dict(report.direction_counts),
            "reason_counts": dict(report.reason_counts),
        }

    def report_to_json(
        self,
        report: GatePolicyDiagnosticsReport,
        *,
        indent: int | None = 2,
    ) -> str:
        """Преобразовать диагностический отчёт в стабильную JSON-строку."""

        return json.dumps(
            self.report_to_dict(report),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )
