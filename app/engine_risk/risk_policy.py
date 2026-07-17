"""Deterministic research pre-risk policy over StrategyDecision fields only."""

from __future__ import annotations

import time

from app.engine_risk.risk_config import RiskConfig
from app.engine_risk.risk_decision import RiskDecision, risk_decision_id
from app.engine_risk.risk_level import RiskLevel
from app.engine_risk.risk_limits import ResearchRiskLimits
from app.engine_risk.risk_reason_codes import RiskReasonCode as R
from app.engine_risk.risk_status import RiskStatus
from app.engine_strategy.strategy_decision import StrategyDecision


_CAUSAL_PRIMITIVES = frozenset({
    "reference_close", "confirmation_close", "current_closed_candle_close",
    "causal_support_level", "causal_resistance_level", "causal_invalidation_level",
    "causal_target_level", "nearest_opposite_level", "atr_value", "volatility_buffer",
    "setup_type", "strategy_type", "direction_hint",
})


def _with_causal_context(source: StrategyDecision, context: dict | None) -> dict:
    result = dict(context or {})
    source_context = source.context if isinstance(source.context, dict) else {}
    result.update({key: source_context[key] for key in _CAUSAL_PRIMITIVES
                   if source_context.get(key) is not None})
    result.setdefault("setup_type", source.setup_type)
    result.setdefault("strategy_type", source.strategy_type)
    result.setdefault("direction_hint", source.direction_hint)
    return result


class RiskPolicy:
    def __init__(self, config: RiskConfig | None = None,
                 limits: ResearchRiskLimits | None = None) -> None:
        self.config = config or RiskConfig()
        self.limits = limits or ResearchRiskLimits()

    def evaluate(self, source: StrategyDecision) -> RiskDecision:
        if not isinstance(source, StrategyDecision):
            raise TypeError("source must be a StrategyDecision")
        safety = self._safety_reasons(source)
        if safety:
            return self._decision(source, RiskStatus.REJECT, RiskLevel.BLOCKED,
                                  risk_reasons=safety + self._safety_confirmations(),
                                  rejection_reasons=safety)

        status = source.decision_status
        if status == "ERROR":
            return self._decision(source, RiskStatus.ERROR, RiskLevel.ERROR,
                                  risk_reasons=[R.RISK_REJECT_SOURCE_ERROR, *self._safety_confirmations()],
                                  rejection_reasons=[R.RISK_REJECT_SOURCE_ERROR])
        if status == "WAIT":
            return self._decision(source, RiskStatus.WAIT, RiskLevel.WAITING,
                                  risk_reasons=[R.RISK_WAIT_SOURCE_WAITING, *self._safety_confirmations()],
                                  wait_reasons=[R.RISK_WAIT_SOURCE_WAITING])
        if status == "NO_DECISION":
            return self._decision(source, RiskStatus.NO_DECISION, RiskLevel.UNKNOWN,
                                  risk_reasons=[R.RISK_NO_DECISION_SOURCE_NO_DECISION,
                                                *self._safety_confirmations()])
        if status == "REJECT":
            return self._decision(source, RiskStatus.REJECT, RiskLevel.BLOCKED,
                                  risk_reasons=[R.RISK_REJECT_SOURCE_REJECTED,
                                                R.RISK_BLOCKED_BY_POLICY,
                                                *self._safety_confirmations()],
                                  rejection_reasons=[R.RISK_REJECT_SOURCE_REJECTED])
        if status not in self.config.allow_only_strategy_status:
            return self._decision(source, RiskStatus.NO_DECISION, RiskLevel.UNKNOWN,
                                  risk_reasons=[R.RISK_NO_DECISION_SOURCE_NO_DECISION,
                                                *self._safety_confirmations()])

        if self.config.require_risk_review_flag and not source.requires_risk_review:
            return self._decision(
                source, RiskStatus.NO_DECISION, RiskLevel.UNKNOWN,
                risk_reasons=[R.RISK_NO_DECISION_NOT_MARKED_FOR_RISK_REVIEW,
                              *self._safety_confirmations()],
            )
        if not self.config.quality_meets_minimum(source.strategy_quality):
            return self._blocked(source, R.RISK_REJECT_LOW_STRATEGY_QUALITY)
        if source.strategy_score is None or (
            self.config.minimum_strategy_score is not None
            and source.strategy_score < self.config.minimum_strategy_score
        ):
            return self._blocked(source, R.RISK_REJECT_LOW_STRATEGY_SCORE,
                                 score=self._risk_score(source))
        if source.strategy_type not in self.config.allowed_strategy_types:
            return self._blocked(source, R.RISK_REJECT_UNSUPPORTED_STRATEGY_TYPE,
                                 score=self._risk_score(source))
        if source.direction_hint not in {"BULLISH", "BEARISH"}:
            return self._blocked(source, R.RISK_REJECT_NEUTRAL_DIRECTION,
                                 score=self._risk_score(source))

        score = self._risk_score(source)
        level = self._score_level(score)
        if level == RiskLevel.HIGH or (level == RiskLevel.MEDIUM and not self.config.allow_medium_risk):
            return self._decision(
                source, RiskStatus.REJECT, level, risk_score=score,
                risk_reasons=[self._level_reason(level), R.RISK_BLOCKED_BY_POLICY,
                              *self._safety_confirmations()],
                rejection_reasons=[R.RISK_BLOCKED_BY_POLICY],
            )

        identity = source.decision_id
        allowed, context = self.limits.check_and_reserve(
            identity=identity, symbol=source.symbol, direction=source.direction_hint,
            closed_until_ms=source.closed_until_ms, config=self.config,
        )
        if not allowed:
            return self._decision(
                source, RiskStatus.REJECT, RiskLevel.BLOCKED, risk_score=score,
                risk_reasons=[R.RISK_REJECT_RESEARCH_LIMIT_EXCEEDED, R.RISK_BLOCKED_BY_POLICY,
                              *self._safety_confirmations()],
                rejection_reasons=[R.RISK_REJECT_RESEARCH_LIMIT_EXCEEDED],
                context=context.to_dict(),
            )
        quality_reason = (R.RISK_PREAPPROVE_GOOD_STRATEGY if source.strategy_quality == "GOOD"
                          else R.RISK_PREAPPROVE_ACCEPTABLE_STRATEGY)
        return self._decision(
            source, RiskStatus.RISK_PRE_APPROVED_RESEARCH, level, risk_score=score,
            risk_reasons=[quality_reason, self._level_reason(level), *self._safety_confirmations()],
            context=context.to_dict(), risk_pre_approved=True, requires_execution_review=True,
        )

    def _safety_reasons(self, source: StrategyDecision) -> list[R]:
        reasons: list[R] = []
        if self.config.reject_if_future_bars_used and source.future_bars_used:
            reasons.append(R.RISK_REJECT_FUTURE_BARS)
            reasons.append(R.RISK_REJECT_UNSAFE_SOURCE_DECISION)
        if source.risk_approved or (
            self.config.reject_if_source_trade_signal and source.is_trade_signal
        ) or (self.config.reject_if_source_executable and source.is_executable):
            reasons.append(R.RISK_REJECT_UNSAFE_SOURCE_DECISION)
        return list(dict.fromkeys(reasons))

    @staticmethod
    def _safety_confirmations() -> list[R]:
        return [R.RISK_NO_FUTURE_BARS_USED, R.RISK_NOT_EXECUTABLE, R.RISK_NOT_ORDER_APPROVED]

    @staticmethod
    def _risk_score(source: StrategyDecision) -> float | None:
        if source.strategy_score is None:
            return None
        quality_bonus = 5.0 if source.strategy_quality == "GOOD" else 2.0
        warning_penalty = min(len(source.decision_warnings) * 2.0, 10.0)
        return round(max(0.0, min(100.0, float(source.strategy_score) + quality_bonus - warning_penalty)), 3)

    @staticmethod
    def _score_level(score: float | None) -> RiskLevel:
        if score is None:
            return RiskLevel.UNKNOWN
        if score >= 80:
            return RiskLevel.LOW
        if score >= 65:
            return RiskLevel.MEDIUM
        return RiskLevel.HIGH

    @staticmethod
    def _level_reason(level: RiskLevel) -> R:
        return {RiskLevel.LOW: R.RISK_POLICY_LOW_RISK,
                RiskLevel.MEDIUM: R.RISK_POLICY_MEDIUM_RISK,
                RiskLevel.HIGH: R.RISK_POLICY_HIGH_RISK}[level]

    def _blocked(self, source: StrategyDecision, reason: R, *, score: float | None = None) -> RiskDecision:
        return self._decision(
            source, RiskStatus.REJECT, RiskLevel.BLOCKED, risk_score=score,
            risk_reasons=[reason, R.RISK_BLOCKED_BY_POLICY, *self._safety_confirmations()],
            rejection_reasons=[reason],
        )

    def _decision(self, source: StrategyDecision, status: RiskStatus, level: RiskLevel, *,
                  risk_score: float | None = None, risk_reasons: list[R] | None = None,
                  risk_warnings: list[str] | None = None,
                  rejection_reasons: list[R] | None = None,
                  wait_reasons: list[R] | None = None, context: dict | None = None,
                  risk_pre_approved: bool = False,
                  requires_execution_review: bool = False) -> RiskDecision:
        return RiskDecision(
            risk_decision_id=risk_decision_id(source.symbol, source.timeframe,
                                              source.closed_until_ms, source.decision_id),
            created_at_ms=time.time_ns() // 1_000_000,
            source_strategy_decision_id=source.decision_id,
            source_setup_id=source.source_setup_id,
            source_analysis_snapshot_id=source.source_analysis_snapshot_id,
            symbol=source.symbol, timeframe=source.timeframe,
            closed_until_ms=source.closed_until_ms,
            risk_status=status.value, risk_level=level.value, risk_score=risk_score,
            risk_policy_version=self.config.policy_version,
            source_decision_status=source.decision_status,
            source_strategy_type=source.strategy_type,
            source_strategy_quality=source.strategy_quality,
            source_strategy_score=source.strategy_score,
            direction_hint=source.direction_hint,
            risk_reasons=[str(value) for value in (risk_reasons or [])],
            risk_warnings=list(risk_warnings or []),
            rejection_reasons=[str(value) for value in (rejection_reasons or [])],
            wait_reasons=[str(value) for value in (wait_reasons or [])],
            risk_context=_with_causal_context(source, context), risk_pre_approved=risk_pre_approved,
            requires_execution_review=requires_execution_review,
        )
