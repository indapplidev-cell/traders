"""Mapping plan между runtime prediction payload и GatePolicyInput.

Модуль описывает правила будущего преобразования prediction output
в GatePolicy input. Он не импортирует prediction_service, predictor,
БД и traders-core.
"""

from __future__ import annotations

from dataclasses import dataclass


PLAN_NAME = "gate_policy_prediction_payload_mapping"
PLAN_VERSION = "ml19.1"


@dataclass(frozen=True)
class PredictionMappingRule:
    """Одно правило mapping из prediction payload в GatePolicy field."""

    target_field: str
    source_fields: tuple[str, ...]
    mapping_type: str
    required: bool
    description: str
    fallback: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Преобразовать mapping rule в JSON-safe словарь."""

        return {
            "target_field": self.target_field,
            "source_fields": list(self.source_fields),
            "mapping_type": self.mapping_type,
            "required": self.required,
            "description": self.description,
            "fallback": self.fallback,
        }


@dataclass(frozen=True)
class DirectionMappingRule:
    """Правило выбора будущего GatePolicy direction."""

    output_direction: str
    condition: str
    source_fields: tuple[str, ...]
    description: str

    def to_dict(self) -> dict[str, object]:
        """Преобразовать direction rule в JSON-safe словарь."""

        return {
            "output_direction": self.output_direction,
            "condition": self.condition,
            "source_fields": list(self.source_fields),
            "description": self.description,
        }


DEFAULT_MAPPING_RULES: tuple[PredictionMappingRule, ...] = (
    PredictionMappingRule(
        target_field="direction",
        source_fields=("prob_up", "prob_down", "prob_flat"),
        mapping_type="probability_argmax",
        required=True,
        description=(
            "Future adapter should select direction from the highest probability. "
            "prob_up maps to LONG, prob_down maps to SHORT, prob_flat maps to FLAT/NONE."
        ),
        fallback="NONE when probabilities are missing, invalid or tied without confidence.",
    ),
    PredictionMappingRule(
        target_field="confidence",
        source_fields=("confidence",),
        mapping_type="direct_float",
        required=True,
        description="Runtime prediction confidence maps directly to GatePolicy confidence.",
        fallback="0.0 when confidence is missing or invalid.",
    ),
    PredictionMappingRule(
        target_field="tp_before_sl_probability",
        source_fields=("tp_before_sl_probability",),
        mapping_type="direct_float",
        required=True,
        description=(
            "Runtime probability of take-profit before stop-loss maps directly "
            "to GatePolicy tp_before_sl_probability."
        ),
        fallback="0.0 when tp_before_sl_probability is missing or invalid.",
    ),
    PredictionMappingRule(
        target_field="risk_score",
        source_fields=("risk_score",),
        mapping_type="direct_float",
        required=False,
        description="Runtime risk_score maps directly to GatePolicy risk_score.",
        fallback="None when risk_score is missing.",
    ),
    PredictionMappingRule(
        target_field="expected_move_atr",
        source_fields=("expected_move_atr",),
        mapping_type="direct_float",
        required=False,
        description=(
            "Runtime expected_move_atr maps directly to GatePolicy expected_move_atr."
        ),
        fallback="None when expected_move_atr is missing.",
    ),
    PredictionMappingRule(
        target_field="regime",
        source_fields=("regime", "market_regime", "detected_regime"),
        mapping_type="alias_first_present",
        required=True,
        description=(
            "Market regime should be read from regime first, then market_regime, "
            "then detected_regime."
        ),
        fallback="unknown when regime is missing.",
    ),
    PredictionMappingRule(
        target_field="model_version",
        source_fields=("model_version",),
        mapping_type="metadata_traceability",
        required=False,
        description=(
            "model_version is not required by GatePolicyInput but must be preserved "
            "as traceability metadata for diagnostics and reports."
        ),
        fallback="None when model_version is missing.",
    ),
    PredictionMappingRule(
        target_field="symbol",
        source_fields=("symbol",),
        mapping_type="metadata_traceability",
        required=False,
        description=(
            "symbol is not part of GatePolicy decision logic yet, but should be "
            "preserved as traceability metadata."
        ),
        fallback="None when symbol is missing.",
    ),
    PredictionMappingRule(
        target_field="interval",
        source_fields=("interval",),
        mapping_type="metadata_traceability",
        required=False,
        description=(
            "interval is not part of GatePolicy decision logic yet, but should be "
            "preserved as traceability metadata."
        ),
        fallback="None when interval is missing.",
    ),
)


DEFAULT_DIRECTION_RULES: tuple[DirectionMappingRule, ...] = (
    DirectionMappingRule(
        output_direction="LONG",
        condition="prob_up is strictly greater than prob_down and prob_flat",
        source_fields=("prob_up", "prob_down", "prob_flat"),
        description="Bullish probability dominance maps to LONG.",
    ),
    DirectionMappingRule(
        output_direction="SHORT",
        condition="prob_down is strictly greater than prob_up and prob_flat",
        source_fields=("prob_up", "prob_down", "prob_flat"),
        description="Bearish probability dominance maps to SHORT.",
    ),
    DirectionMappingRule(
        output_direction="FLAT",
        condition="prob_flat is strictly greater than prob_up and prob_down",
        source_fields=("prob_up", "prob_down", "prob_flat"),
        description="Flat probability dominance maps to FLAT.",
    ),
    DirectionMappingRule(
        output_direction="NONE",
        condition="probabilities are missing, invalid, negative, not numeric or tied",
        source_fields=("prob_up", "prob_down", "prob_flat"),
        description="Unsafe or ambiguous probabilities map to NONE.",
    ),
)


@dataclass(frozen=True)
class PredictionPayloadMappingPlan:
    """План будущего mapping prediction payload в GatePolicyInput."""

    name: str = PLAN_NAME
    version: str = PLAN_VERSION
    mapping_rules: tuple[PredictionMappingRule, ...] = DEFAULT_MAPPING_RULES
    direction_rules: tuple[DirectionMappingRule, ...] = DEFAULT_DIRECTION_RULES

    @property
    def required_target_fields(self) -> tuple[str, ...]:
        """Target fields, обязательные для будущего GatePolicy mapping."""

        return tuple(rule.target_field for rule in self.mapping_rules if rule.required)

    @property
    def optional_target_fields(self) -> tuple[str, ...]:
        """Target fields, опциональные для будущего GatePolicy mapping."""

        return tuple(
            rule.target_field
            for rule in self.mapping_rules
            if not rule.required
        )

    @property
    def all_target_fields(self) -> tuple[str, ...]:
        """Все target fields mapping plan."""

        return tuple(rule.target_field for rule in self.mapping_rules)

    @property
    def all_source_fields(self) -> tuple[str, ...]:
        """Все source fields mapping plan без дублей."""

        fields: set[str] = set()

        for rule in self.mapping_rules:
            fields.update(rule.source_fields)

        return tuple(sorted(fields))

    def rule_for_target(self, target_field: str) -> PredictionMappingRule | None:
        """Найти mapping rule по target field."""

        for rule in self.mapping_rules:
            if rule.target_field == target_field:
                return rule

        return None

    def to_dict(self) -> dict[str, object]:
        """Преобразовать mapping plan в JSON-safe словарь."""

        return {
            "name": self.name,
            "version": self.version,
            "required_target_fields": list(self.required_target_fields),
            "optional_target_fields": list(self.optional_target_fields),
            "all_target_fields": list(self.all_target_fields),
            "all_source_fields": list(self.all_source_fields),
            "mapping_rules": [
                rule.to_dict()
                for rule in self.mapping_rules
            ],
            "direction_rules": [
                rule.to_dict()
                for rule in self.direction_rules
            ],
            "integration_status": {
                "prediction_service_imported": False,
                "predictor_imported": False,
                "database_connected": False,
                "model_inference_connected": False,
                "traders_core_connected": False,
                "live_trading_connected": False,
                "runtime_adapter_implemented": False,
            },
        }
