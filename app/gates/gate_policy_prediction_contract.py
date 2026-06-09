"""Контракт prediction/evaluation payload для GatePolicy.

Модуль фиксирует, какие поля будущий ML prediction/evaluation слой должен
передавать в GatePolicy adapter. Он не запускает модель, не читает БД
и не подключается к traders-core.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping


REQUIRED_GATE_POLICY_FIELDS: tuple[str, ...] = (
    "regime",
    "direction",
    "confidence",
    "tp_before_sl_probability",
)

OPTIONAL_GATE_POLICY_FIELDS: tuple[str, ...] = (
    "risk_score",
    "expected_move_atr",
    "model_total_r",
    "baseline_total_r",
    "model_profit_factor",
    "baseline_profit_factor",
    "sample_count",
)

FIELD_ALIASES: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "regime": (
            "regime",
            "market_regime",
            "detected_regime",
        ),
        "direction": (
            "direction",
            "predicted_direction",
            "signal_direction",
            "side",
        ),
        "confidence": (
            "confidence",
            "model_confidence",
            "signal_confidence",
        ),
        "tp_before_sl_probability": (
            "tp_before_sl_probability",
            "tp_before_sl_prob",
            "take_profit_before_stop_loss_probability",
        ),
        "risk_score": (
            "risk_score",
            "model_risk_score",
        ),
        "expected_move_atr": (
            "expected_move_atr",
            "expected_atr_move",
        ),
        "model_total_r": (
            "model_total_r",
            "ml_total_r",
            "total_r",
        ),
        "baseline_total_r": (
            "baseline_total_r",
            "baseline_r",
        ),
        "model_profit_factor": (
            "model_profit_factor",
            "ml_profit_factor",
            "profit_factor",
        ),
        "baseline_profit_factor": (
            "baseline_profit_factor",
        ),
        "sample_count": (
            "sample_count",
            "samples",
            "n",
        ),
    }
)

DIRECTION_ALIASES: Mapping[str, str] = MappingProxyType(
    {
        "UP": "LONG",
        "BUY": "LONG",
        "LONG": "LONG",
        "DOWN": "SHORT",
        "SELL": "SHORT",
        "SHORT": "SHORT",
        "FLAT": "FLAT",
        "SIDEWAYS": "FLAT",
        "NONE": "NONE",
        "NO_TRADE": "NONE",
    }
)

KNOWN_REGIME_VALUES: tuple[str, ...] = (
    "trend_up",
    "trend_down",
    "breakout_setup",
    "range",
    "high_volatility",
    "low_volatility",
    "low_liquidity",
    "unknown",
)


@dataclass(frozen=True)
class GatePolicyPredictionPayloadContract:
    """Описание payload-контракта для будущей GatePolicy integration."""

    required_fields: tuple[str, ...] = REQUIRED_GATE_POLICY_FIELDS
    optional_fields: tuple[str, ...] = OPTIONAL_GATE_POLICY_FIELDS
    field_aliases: Mapping[str, tuple[str, ...]] = field(
        default_factory=lambda: FIELD_ALIASES
    )
    direction_aliases: Mapping[str, str] = field(
        default_factory=lambda: DIRECTION_ALIASES
    )
    known_regime_values: tuple[str, ...] = KNOWN_REGIME_VALUES

    @property
    def all_fields(self) -> tuple[str, ...]:
        """Вернуть все canonical поля контракта."""

        return self.required_fields + self.optional_fields

    def aliases_for(self, canonical_field: str) -> tuple[str, ...]:
        """Вернуть alias-имена для canonical поля."""

        return self.field_aliases.get(canonical_field, ())

    def canonical_field_for_alias(self, alias: str) -> str | None:
        """Найти canonical field по alias-имени."""

        normalized = alias.strip()

        for canonical_field, aliases in self.field_aliases.items():
            if normalized in aliases:
                return canonical_field

        return None

    def is_required_field(self, field_name: str) -> bool:
        """Проверить, является ли поле обязательным."""

        return field_name in self.required_fields

    def is_optional_field(self, field_name: str) -> bool:
        """Проверить, является ли поле опциональным."""

        return field_name in self.optional_fields

    def is_known_field(self, field_name: str) -> bool:
        """Проверить, известно ли поле контракту."""

        return field_name in self.all_fields

    def normalize_direction_alias(self, value: str) -> str:
        """Нормализовать direction alias в LONG/SHORT/FLAT/NONE."""

        normalized = value.strip().upper()
        return self.direction_aliases.get(normalized, "NONE")

    def to_dict(self) -> dict[str, object]:
        """Вернуть JSON-safe представление контракта."""

        return {
            "required_fields": list(self.required_fields),
            "optional_fields": list(self.optional_fields),
            "field_aliases": {
                key: list(value)
                for key, value in self.field_aliases.items()
            },
            "direction_aliases": dict(self.direction_aliases),
            "known_regime_values": list(self.known_regime_values),
        }
