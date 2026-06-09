"""JSON-репортёр для GatePolicy adapter diagnostics.

Модуль превращает GatePolicyAdapterDiagnosticsResult в JSON-safe dict/JSON.
Он не запускает модель, не читает БД и не подключается к traders-core.
"""

from __future__ import annotations

import json
from enum import Enum
from typing import Any

from app.gates.gate_policy_adapter_diagnostics import (
    GatePolicyAdapterDiagnosticsResult,
)
from app.gates.gate_policy_models import GatePolicyInput
from app.gates.gate_policy_reporter import GatePolicyReporter


class GatePolicyAdapterReporter:
    """Сериализация результата GatePolicy adapter diagnostics."""

    def __init__(self, policy_reporter: GatePolicyReporter | None = None) -> None:
        self.policy_reporter = policy_reporter or GatePolicyReporter()

    def input_to_dict(self, gate_input: GatePolicyInput) -> dict[str, Any]:
        """Преобразовать GatePolicyInput в JSON-safe словарь."""

        return {
            "regime": gate_input.regime,
            "direction": self._enum_or_string_value(gate_input.direction),
            "confidence": gate_input.confidence,
            "tp_before_sl_probability": gate_input.tp_before_sl_probability,
            "risk_score": gate_input.risk_score,
            "expected_move_atr": gate_input.expected_move_atr,
            "model_total_r": gate_input.model_total_r,
            "baseline_total_r": gate_input.baseline_total_r,
            "model_profit_factor": gate_input.model_profit_factor,
            "baseline_profit_factor": gate_input.baseline_profit_factor,
            "sample_count": gate_input.sample_count,
            "metadata": self._json_safe(dict(gate_input.metadata)),
        }

    def adapter_result_to_dict(
        self,
        result: GatePolicyAdapterDiagnosticsResult,
    ) -> dict[str, Any]:
        """Преобразовать полный adapter diagnostics результат в словарь."""

        inputs = [self.input_to_dict(item) for item in result.inputs]
        results = [self.policy_reporter.result_to_dict(item) for item in result.results]
        report = self.policy_reporter.report_to_dict(result.report)

        return {
            "input_count": len(result.inputs),
            "result_count": len(result.results),
            "report": report,
            "inputs": inputs,
            "results": results,
            "decision_sequence": [
                item["decision"]
                for item in results
            ],
            "allowed_sequence": [
                item["allowed"]
                for item in results
            ],
        }

    def adapter_result_to_json(
        self,
        result: GatePolicyAdapterDiagnosticsResult,
        *,
        indent: int | None = 2,
    ) -> str:
        """Преобразовать adapter diagnostics результат в JSON-строку."""

        return json.dumps(
            self.adapter_result_to_dict(result),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def _enum_or_string_value(self, value: Any) -> str:
        """Вернуть .value для enum или строковое значение для обычного объекта."""

        if isinstance(value, Enum):
            return str(value.value)

        return str(value)

    def _json_safe(self, value: Any) -> Any:
        """Сделать значение безопасным для json.dumps.

        Если встретится неизвестный объект, он будет превращён в строку.
        """

        if value is None or isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, Enum):
            return value.value

        if isinstance(value, dict):
            return {
                str(key): self._json_safe(item)
                for key, item in value.items()
            }

        if isinstance(value, (list, tuple)):
            return [
                self._json_safe(item)
                for item in value
            ]

        return str(value)
