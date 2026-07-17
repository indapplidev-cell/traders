"""Policy gates for turning a RiskDecision into a paper-only planning eligibility result."""

from __future__ import annotations

from dataclasses import dataclass

from app.engine_paper.paper_config import PaperConfig
from app.engine_paper.paper_reason_codes import PaperReasonCode as R
from app.engine_risk.risk_decision import RiskDecision


@dataclass(frozen=True, slots=True)
class PaperPolicyResult:
    proceed: bool
    status: str
    quality: str
    reason: str | None = None


class PaperPlanPolicy:
    def __init__(self, config: PaperConfig | None = None) -> None:
        self.config = config or PaperConfig()

    def evaluate(self, source: RiskDecision) -> PaperPolicyResult:
        if not isinstance(source, RiskDecision):
            raise TypeError("source must be a RiskDecision")
        if source.risk_status == "ERROR":
            return PaperPolicyResult(False, "ERROR", "ERROR", R.PAPER_REJECT_SOURCE_ERROR.value)
        if source.risk_status == "WAIT":
            return PaperPolicyResult(False, "WAIT", "WAITING", R.PAPER_WAIT_SOURCE_WAITING.value)
        if self._unsafe(source):
            return PaperPolicyResult(False, "REJECT", "REJECTED",
                                     R.PAPER_REJECT_UNSAFE_SOURCE_RISK_DECISION.value)
        if source.risk_status == "NO_DECISION":
            return PaperPolicyResult(False, "NO_PLAN", "UNKNOWN",
                                     R.PAPER_NO_PLAN_SOURCE_NO_DECISION.value)
        if source.risk_status == "REJECT":
            return PaperPolicyResult(False, "NO_PLAN", "REJECTED",
                                     R.PAPER_REJECT_SOURCE_REJECTED.value)
        if source.risk_status not in self.config.allow_only_risk_status:
            return PaperPolicyResult(False, "NO_PLAN", "UNKNOWN",
                                     R.PAPER_NO_PLAN_NOT_RISK_PREAPPROVED.value)
        if ((self.config.require_risk_pre_approved and not source.risk_pre_approved) or
                (self.config.require_execution_review_flag and not source.requires_execution_review)):
            return PaperPolicyResult(False, "NO_PLAN", "UNKNOWN",
                                     R.PAPER_NO_PLAN_NOT_RISK_PREAPPROVED.value)
        if source.risk_level not in self.config.allowed_risk_levels:
            return PaperPolicyResult(False, "REJECT", "REJECTED",
                                     R.PAPER_REJECT_UNSUPPORTED_RISK_LEVEL.value)
        if source.source_strategy_type not in self.config.allowed_strategy_types:
            return PaperPolicyResult(False, "REJECT", "REJECTED",
                                     R.PAPER_REJECT_UNSUPPORTED_STRATEGY_TYPE.value)
        if source.direction_hint not in {"BULLISH", "BEARISH"}:
            return PaperPolicyResult(False, "REJECT", "REJECTED",
                                     R.PAPER_REJECT_INVALID_DIRECTION.value)
        quality = self._quality(source)
        if quality not in {"GOOD", "ACCEPTABLE"}:
            return PaperPolicyResult(False, "REJECT", "REJECTED",
                                     R.PAPER_REJECT_UNSUPPORTED_RISK_LEVEL.value)
        return PaperPolicyResult(True, "PAPER_PLAN_READY", quality)

    def _unsafe(self, source: RiskDecision) -> bool:
        checks = (
            self.config.reject_if_source_trade_signal and source.is_trade_signal,
            self.config.reject_if_source_executable and source.is_executable,
            self.config.reject_if_source_order_approved and source.order_approved,
            self.config.reject_if_source_execution_approved and source.execution_approved,
            self.config.reject_if_position_size_approved and source.position_size_approved,
            self.config.reject_if_future_bars_used and source.future_bars_used,
        )
        return any(checks)

    @staticmethod
    def _quality(source: RiskDecision) -> str:
        if source.risk_level == "LOW":
            return source.source_strategy_quality if source.source_strategy_quality in {
                "GOOD", "ACCEPTABLE", "WEAK", "REJECTED", "WAITING", "UNKNOWN", "ERROR"} else "UNKNOWN"
        if source.risk_level == "MEDIUM":
            return "ACCEPTABLE" if source.source_strategy_quality in {"GOOD", "ACCEPTABLE"} else "WEAK"
        return {"WAITING": "WAITING", "UNKNOWN": "UNKNOWN", "ERROR": "ERROR"}.get(
            source.risk_level, "REJECTED")
