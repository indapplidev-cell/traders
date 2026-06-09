"""Сервис оценки политики допуска ML-сигналов."""

from __future__ import annotations

from app.gates.gate_policy_models import (
    GateDirection,
    GatePolicyConfig,
    GatePolicyDecision,
    GatePolicyInput,
    GatePolicyResult,
)


class GatePolicyService:
    """Risk-first сервис допуска ML-сигналов.

    Сервис не открывает сделки, не выбирает размер позиции,
    не активирует модель и не подключается к traders-core.
    """

    def __init__(self, config: GatePolicyConfig | None = None) -> None:
        self.config = config or GatePolicyConfig()

    def evaluate(self, signal: GatePolicyInput) -> GatePolicyResult:
        """Оценить ML-сигнал по консервативным правилам."""

        direction = self._normalize_direction(signal.direction)
        thresholds = self._build_thresholds()

        if direction in {GateDirection.FLAT, GateDirection.NONE}:
            return self._result(
                decision=GatePolicyDecision.BLOCK,
                allowed=False,
                signal=signal,
                direction=direction,
                reasons=("direction_is_not_tradeable",),
                thresholds=thresholds,
            )

        if self._is_bad_regime(signal.regime):
            return self._result(
                decision=GatePolicyDecision.BAD_REGIME,
                allowed=False,
                signal=signal,
                direction=direction,
                reasons=("regime_is_not_trusted",),
                thresholds=thresholds,
            )

        if signal.confidence < self.config.min_confidence:
            return self._result(
                decision=GatePolicyDecision.LOW_CONFIDENCE,
                allowed=False,
                signal=signal,
                direction=direction,
                reasons=("confidence_below_threshold",),
                thresholds=thresholds,
            )

        if signal.tp_before_sl_probability < self.config.min_tp_before_sl_probability:
            return self._result(
                decision=GatePolicyDecision.LOW_CONFIDENCE,
                allowed=False,
                signal=signal,
                direction=direction,
                reasons=("tp_before_sl_probability_below_threshold",),
                thresholds=thresholds,
            )

        if signal.risk_score is not None and signal.risk_score > self.config.max_risk_score:
            return self._result(
                decision=GatePolicyDecision.MODEL_UNTRUSTED,
                allowed=False,
                signal=signal,
                direction=direction,
                reasons=("risk_score_above_threshold",),
                thresholds=thresholds,
            )

        if signal.sample_count is not None and signal.sample_count < self.config.min_sample_count:
            return self._result(
                decision=GatePolicyDecision.MODEL_UNTRUSTED,
                allowed=False,
                signal=signal,
                direction=direction,
                reasons=("sample_count_below_threshold",),
                thresholds=thresholds,
            )

        if self._baseline_is_better_by_total_r(signal):
            return self._result(
                decision=GatePolicyDecision.BASELINE_BETTER,
                allowed=False,
                signal=signal,
                direction=direction,
                reasons=("baseline_total_r_better_than_model",),
                thresholds=thresholds,
            )

        if self._baseline_is_better_by_profit_factor(signal):
            return self._result(
                decision=GatePolicyDecision.BASELINE_BETTER,
                allowed=False,
                signal=signal,
                direction=direction,
                reasons=("baseline_profit_factor_better_than_model",),
                thresholds=thresholds,
            )

        decision = (
            GatePolicyDecision.ALLOW_LONG
            if direction == GateDirection.LONG
            else GatePolicyDecision.ALLOW_SHORT
        )

        return self._result(
            decision=decision,
            allowed=True,
            signal=signal,
            direction=direction,
            reasons=("signal_passed_gate_policy",),
            thresholds=thresholds,
        )

    def _normalize_direction(self, direction: GateDirection | str) -> GateDirection:
        """Привести направление к внутреннему enum."""

        if isinstance(direction, GateDirection):
            return direction

        normalized = str(direction).strip().upper()

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

    def _is_bad_regime(self, regime: str) -> bool:
        """Проверить, считается ли режим рынка недопустимым."""

        normalized = regime.strip().lower()

        if normalized in self.config.blocked_regimes:
            return True

        return normalized not in self.config.trusted_regimes

    def _baseline_is_better_by_total_r(self, signal: GatePolicyInput) -> bool:
        """Проверить, лучше ли baseline по total R."""

        if signal.model_total_r is None or signal.baseline_total_r is None:
            return False

        required_edge = signal.model_total_r + self.config.baseline_total_r_margin
        return signal.baseline_total_r > required_edge

    def _baseline_is_better_by_profit_factor(self, signal: GatePolicyInput) -> bool:
        """Проверить, лучше ли baseline по profit factor."""

        if signal.model_profit_factor is None or signal.baseline_profit_factor is None:
            return False

        required_edge = signal.model_profit_factor + self.config.baseline_profit_factor_margin
        return signal.baseline_profit_factor > required_edge

    def _build_thresholds(self) -> dict[str, object]:
        """Собрать применённые пороги для диагностики."""

        return {
            "trusted_regimes": self.config.trusted_regimes,
            "blocked_regimes": self.config.blocked_regimes,
            "min_confidence": self.config.min_confidence,
            "min_tp_before_sl_probability": self.config.min_tp_before_sl_probability,
            "max_risk_score": self.config.max_risk_score,
            "min_sample_count": self.config.min_sample_count,
            "baseline_total_r_margin": self.config.baseline_total_r_margin,
            "baseline_profit_factor_margin": self.config.baseline_profit_factor_margin,
        }

    def _result(
        self,
        *,
        decision: GatePolicyDecision,
        allowed: bool,
        signal: GatePolicyInput,
        direction: GateDirection,
        reasons: tuple[str, ...],
        thresholds: dict[str, object],
    ) -> GatePolicyResult:
        """Собрать результат оценки."""

        return GatePolicyResult.build(
            decision=decision,
            allowed=allowed,
            regime=signal.regime,
            direction=direction,
            reasons=reasons,
            thresholds=thresholds,
        )
