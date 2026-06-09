"""Адаптер данных для GatePolicy.

Модуль преобразует внешние словари prediction/evaluation данных
в GatePolicyInput. Он не запускает модель, не читает БД и не подключается
к traders-core.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from app.gates.gate_policy_models import GateDirection, GatePolicyInput


@dataclass(frozen=True)
class GatePolicyAdapterConfig:
    """Настройки адаптера GatePolicy."""

    default_regime: str = "unknown"
    default_direction: GateDirection = GateDirection.NONE
    default_confidence: float = 0.0
    default_tp_before_sl_probability: float = 0.0


class GatePolicyEvaluationAdapter:
    """Преобразует prediction/evaluation payload в GatePolicyInput."""

    def __init__(self, config: GatePolicyAdapterConfig | None = None) -> None:
        self.config = config or GatePolicyAdapterConfig()

    def from_mapping(self, payload: Mapping[str, Any]) -> GatePolicyInput:
        """Собрать GatePolicyInput из произвольного словаря.

        Поддерживаются несколько вариантов ключей, потому что разные части
        ML-сервиса могут отдавать direction/confidence/regime под разными именами.
        """

        regime = self._get_str(
            payload,
            keys=("regime", "market_regime", "detected_regime"),
            default=self.config.default_regime,
        )

        direction = self._normalize_direction(
            self._get_raw(
                payload,
                keys=("direction", "predicted_direction", "signal_direction", "side"),
                default=self.config.default_direction,
            )
        )

        confidence = self._get_float(
            payload,
            keys=("confidence", "model_confidence", "signal_confidence"),
            default=self.config.default_confidence,
        )

        tp_before_sl_probability = self._get_float(
            payload,
            keys=(
                "tp_before_sl_probability",
                "tp_before_sl_prob",
                "take_profit_before_stop_loss_probability",
            ),
            default=self.config.default_tp_before_sl_probability,
        )

        risk_score = self._get_optional_float(
            payload,
            keys=("risk_score", "model_risk_score"),
        )

        expected_move_atr = self._get_optional_float(
            payload,
            keys=("expected_move_atr", "expected_atr_move"),
        )

        model_total_r = self._get_optional_float(
            payload,
            keys=("model_total_r", "ml_total_r", "total_r"),
        )

        baseline_total_r = self._get_optional_float(
            payload,
            keys=("baseline_total_r", "baseline_r"),
        )

        model_profit_factor = self._get_optional_float(
            payload,
            keys=("model_profit_factor", "ml_profit_factor", "profit_factor"),
        )

        baseline_profit_factor = self._get_optional_float(
            payload,
            keys=("baseline_profit_factor",),
        )

        sample_count = self._get_optional_int(
            payload,
            keys=("sample_count", "samples", "n"),
        )

        return GatePolicyInput(
            regime=regime,
            direction=direction,
            confidence=confidence,
            tp_before_sl_probability=tp_before_sl_probability,
            risk_score=risk_score,
            expected_move_atr=expected_move_atr,
            model_total_r=model_total_r,
            baseline_total_r=baseline_total_r,
            model_profit_factor=model_profit_factor,
            baseline_profit_factor=baseline_profit_factor,
            sample_count=sample_count,
            metadata=dict(payload),
        )

    def from_mappings(
        self,
        payloads: Sequence[Mapping[str, Any]],
    ) -> tuple[GatePolicyInput, ...]:
        """Собрать несколько GatePolicyInput из набора словарей."""

        return tuple(self.from_mapping(payload) for payload in payloads)

    def _get_raw(
        self,
        payload: Mapping[str, Any],
        *,
        keys: tuple[str, ...],
        default: Any,
    ) -> Any:
        """Получить первое найденное значение по списку ключей."""

        for key in keys:
            value = payload.get(key)
            if value is not None:
                return value

        return default

    def _get_str(
        self,
        payload: Mapping[str, Any],
        *,
        keys: tuple[str, ...],
        default: str,
    ) -> str:
        """Получить строковое значение по списку ключей."""

        value = self._get_raw(payload, keys=keys, default=default)
        return str(value).strip() or default

    def _get_float(
        self,
        payload: Mapping[str, Any],
        *,
        keys: tuple[str, ...],
        default: float,
    ) -> float:
        """Получить float-значение по списку ключей."""

        value = self._get_raw(payload, keys=keys, default=default)

        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _get_optional_float(
        self,
        payload: Mapping[str, Any],
        *,
        keys: tuple[str, ...],
    ) -> float | None:
        """Получить optional float-значение по списку ключей."""

        value = self._get_raw(payload, keys=keys, default=None)

        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _get_optional_int(
        self,
        payload: Mapping[str, Any],
        *,
        keys: tuple[str, ...],
    ) -> int | None:
        """Получить optional int-значение по списку ключей."""

        value = self._get_raw(payload, keys=keys, default=None)

        if value is None:
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _normalize_direction(self, value: Any) -> GateDirection:
        """Нормализовать направление для GatePolicyInput."""

        if isinstance(value, GateDirection):
            return value

        normalized = str(value).strip().upper()

        aliases = {
            "UP": GateDirection.LONG,
            "BUY": GateDirection.LONG,
            "LONG": GateDirection.LONG,
            "DOWN": GateDirection.SHORT,
            "SELL": GateDirection.SHORT,
            "SHORT": GateDirection.SHORT,
            "FLAT": GateDirection.FLAT,
            "SIDEWAYS": GateDirection.FLAT,
            "NONE": GateDirection.NONE,
            "NO_TRADE": GateDirection.NONE,
        }

        return aliases.get(normalized, GateDirection.NONE)
