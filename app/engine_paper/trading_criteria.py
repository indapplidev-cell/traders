"""Read-only projection of the effective production PAPER trading policy."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

from app.engine_analysis.regime_composer import MIN_REGIME_SCORE, MIN_SCORE_MARGIN
from app.engine_market_data.continuous_sync_config import FRESHNESS_ALLOWANCE_MS
from app.engine_orchestrator.orchestrator_config import OrchestratorConfig
from app.engine_paper.paper_config import PaperConfig
from app.engine_paper.production_approval import (
    PRIMARY_TIMEFRAME, SYMBOL_ALLOWLIST, _RISK_APPROVED, _SETUP_ELIGIBLE,
    _STRATEGY_ALLOWED,
)
from app.engine_paper.production_market_data import (
    SYMBOL_ALLOWLIST as MARKET_DATA_SYMBOL_ALLOWLIST,
    TIMEFRAME_ALLOWLIST,
)
from app.engine_risk.risk_config import RiskConfig
from app.engine_strategy.strategy_config import StrategyConfig


class CriterionClassification(StrEnum):
    FIXED_THRESHOLD = "FIXED_THRESHOLD"
    DYNAMIC_RULE = "DYNAMIC_RULE"
    DERIVED_VALUE = "DERIVED_VALUE"
    BOOLEAN_GATE = "BOOLEAN_GATE"
    ENUM_ALLOWLIST = "ENUM_ALLOWLIST"
    NOT_CONFIGURED_AS_FIXED_THRESHOLD = "NOT_CONFIGURED_AS_FIXED_THRESHOLD"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True, slots=True)
class TradingCriterion:
    key: str
    category: str
    classification: CriterionClassification
    value: Any
    unit: str | None
    source_component: str


def _criterion(key: str, category: str, classification: CriterionClassification,
               value: Any, source: str, unit: str | None = None) -> TradingCriterion:
    return TradingCriterion(key, category, classification, value, unit, source)


def build_trading_criteria_snapshot() -> dict[str, object]:
    """Build a bounded snapshot directly from active policy/config objects."""

    orchestrator, strategy, risk, paper = (
        OrchestratorConfig(), StrategyConfig(), RiskConfig(), PaperConfig()
    )
    # This is the exact factory used by ProductionPaperFirstCanaryExecutor.
    from app.operator_control.production_executor import _foundation_policy
    from app.operator_control.config import PaperOperatorControlConfig
    from app.operator_control.schemas import PaperOperatorCanaryStatus
    fill = _foundation_policy()
    control = PaperOperatorControlConfig.production_paper()
    canary_fields = PaperOperatorCanaryStatus.model_fields
    symbols = [s for s in orchestrator.symbols
               if s in SYMBOL_ALLOWLIST and s in MARKET_DATA_SYMBOL_ALLOWLIST]
    C = CriterionClassification
    groups = {
        "environment": (
            _criterion("environment", "environment", C.ENUM_ALLOWLIST, [control.environment],
                       "app.operator_control.config.PaperOperatorControlConfig.environment"),
            _criterion("mode", "environment", C.ENUM_ALLOWLIST, [control.mode],
                       "app.operator_control.config.PaperOperatorControlConfig.mode"),
            _criterion("live_allowed", "environment", C.BOOLEAN_GATE, control.live_allowed,
                       "app.operator_control.config.PaperOperatorControlConfig.live_allowed"),
        ),
        "symbols": (_criterion("allowed_symbols", "symbols", C.ENUM_ALLOWLIST, symbols,
                    "app.engine_orchestrator.orchestrator_config.OrchestratorConfig.symbols"),),
        "timeframes": (
            _criterion("primary_timeframe", "timeframes", C.ENUM_ALLOWLIST, [PRIMARY_TIMEFRAME],
                       "app.engine_paper.production_approval.PRIMARY_TIMEFRAME"),
            _criterion("required_timeframes", "timeframes", C.ENUM_ALLOWLIST,
                       list(orchestrator.required_timeframes),
                       "app.engine_orchestrator.orchestrator_config.OrchestratorConfig.required_timeframes"),
            _criterion("market_data_timeframes", "timeframes", C.ENUM_ALLOWLIST,
                       list(TIMEFRAME_ALLOWLIST),
                       "app.engine_paper.production_market_data.TIMEFRAME_ALLOWLIST"),
        ),
        "market_data_requirements": (
            _criterion("closed_candles_only", "market_data_requirements", C.BOOLEAN_GATE, True,
                       "app.engine_analysis.online_config.OnlineAnalysisConfig.run_on_closed_candle_only"),
            _criterion("require_all_timeframes_ok", "market_data_requirements", C.BOOLEAN_GATE,
                       orchestrator.require_all_timeframes_ok,
                       "app.engine_orchestrator.orchestrator_config.OrchestratorConfig.require_all_timeframes_ok"),
            _criterion("allow_stale_higher_timeframes", "market_data_requirements", C.BOOLEAN_GATE,
                       orchestrator.allow_stale_higher_timeframes,
                       "app.engine_orchestrator.orchestrator_config.OrchestratorConfig.allow_stale_higher_timeframes"),
            _criterion("minimum_closed_candles", "market_data_requirements", C.FIXED_THRESHOLD,
                       dict(orchestrator.minimum_windows),
                       "app.engine_orchestrator.orchestrator_config.OrchestratorConfig.minimum_windows", "candles"),
            _criterion("freshness_allowance", "market_data_requirements", C.FIXED_THRESHOLD,
                       dict(FRESHNESS_ALLOWANCE_MS),
                       "app.engine_market_data.continuous_sync_config.FRESHNESS_ALLOWANCE_MS", "ms"),
        ),
        "analysis_requirements": (
            _criterion("market_regime", "analysis_requirements", C.DYNAMIC_RULE,
                       "HYPOTHESIS_EVIDENCE_COMPOSER",
                       "app.engine_analysis.regime_composer.score_regime_candidates"),
            _criterion("minimum_regime_score", "analysis_requirements", C.FIXED_THRESHOLD,
                       MIN_REGIME_SCORE, "app.engine_analysis.regime_composer.MIN_REGIME_SCORE", "score"),
            _criterion("minimum_regime_margin", "analysis_requirements", C.FIXED_THRESHOLD,
                       MIN_SCORE_MARGIN, "app.engine_analysis.regime_composer.MIN_SCORE_MARGIN", "score"),
            _criterion("impulse_phase", "analysis_requirements", C.DYNAMIC_RULE,
                       "CLOSED_CANDLE_MORPHOLOGY_AND_CONFLICT_RESOLUTION",
                       "app.engine_analysis.impulse_phase_conflict_resolver.resolve_impulse_phase_conflicts"),
            _criterion("entry_quality", "analysis_requirements", C.DERIVED_VALUE,
                       "IMPULSE_PHASE_DIAGNOSTICS", "app.engine_analysis.impulse_phase_diagnostics"),
        ),
        "setup_requirements": (
            _criterion("setup_eligibility", "setup_requirements", C.ENUM_ALLOWLIST,
                       sorted(_SETUP_ELIGIBLE), "app.engine_paper.production_approval._SETUP_ELIGIBLE"),
            _criterion("setup_rule", "setup_requirements", C.DYNAMIC_RULE,
                       "STRUCTURE_DIRECTION_LEVEL_CONFIRMATION_INVALIDATION",
                       "app.engine_setup.setup_rules.evaluate_setup_rules"),
            _criterion("setup_quality", "setup_requirements", C.DERIVED_VALUE,
                       "ANALYSIS_ENTRY_QUALITY_WITH_WAIT_DOWNGRADE", "app.engine_setup.setup_rules._quality"),
        ),
        "strategy_requirements": (
            _criterion("allowed_setup_types", "strategy_requirements", C.ENUM_ALLOWLIST,
                       sorted(strategy.allowed_setup_types),
                       "app.engine_strategy.strategy_config.StrategyConfig.allowed_setup_types"),
            _criterion("minimum_setup_quality", "strategy_requirements", C.ENUM_ALLOWLIST,
                       [strategy.minimum_allowed_quality],
                       "app.engine_strategy.strategy_config.StrategyConfig.minimum_allowed_quality"),
            _criterion("require_analysis_confirmation", "strategy_requirements", C.BOOLEAN_GATE,
                       strategy.require_confirmed_by_analysis,
                       "app.engine_strategy.strategy_config.StrategyConfig.require_confirmed_by_analysis"),
            _criterion("strategy_approval_status", "strategy_requirements", C.ENUM_ALLOWLIST,
                       sorted(_STRATEGY_ALLOWED), "app.engine_paper.production_approval._STRATEGY_ALLOWED"),
        ),
        "risk_requirements": (
            _criterion("minimum_strategy_quality", "risk_requirements", C.ENUM_ALLOWLIST,
                       [risk.minimum_strategy_quality],
                       "app.engine_risk.risk_config.RiskConfig.minimum_strategy_quality"),
            _criterion("minimum_strategy_score", "risk_requirements", C.FIXED_THRESHOLD,
                       risk.minimum_strategy_score,
                       "app.engine_risk.risk_config.RiskConfig.minimum_strategy_score", "score"),
            _criterion("allowed_strategy_types", "risk_requirements", C.ENUM_ALLOWLIST,
                       sorted(risk.allowed_strategy_types),
                       "app.engine_risk.risk_config.RiskConfig.allowed_strategy_types"),
            _criterion("allow_medium_risk", "risk_requirements", C.BOOLEAN_GATE,
                       risk.allow_medium_risk, "app.engine_risk.risk_config.RiskConfig.allow_medium_risk"),
            _criterion("final_risk_status", "risk_requirements", C.ENUM_ALLOWLIST,
                       sorted(_RISK_APPROVED),
                       "app.engine_paper.production_approval._RISK_APPROVED"),
            _criterion("risk_per_trade", "risk_requirements", C.NOT_CONFIGURED_AS_FIXED_THRESHOLD,
                       None, "app.engine_paper.paper_approvals.PaperQuantityApproval"),
        ),
        "entry_policy": (
            _criterion("entry_reference", "entry_policy", C.DYNAMIC_RULE,
                       ["confirmation_close", "reference_close", "current_closed_candle_close"],
                       "app.engine_paper.paper_level_builder.PaperLevelBuilder.build"),
            _criterion("final_approvals_required", "entry_policy", C.BOOLEAN_GATE, True,
                       "app.engine_paper.production_approval.PaperProductionApprovalSourceAdapter"),
        ),
        "stop_policy": (
            _criterion("stop_loss", "stop_policy", C.DYNAMIC_RULE,
                       "CAUSAL_INVALIDATION_PLUS_VOLATILITY_BUFFER",
                       "app.engine_paper.paper_level_builder.PaperLevelBuilder.build"),
            _criterion("fallback_stop_allowed", "stop_policy", C.BOOLEAN_GATE,
                       paper.allow_fallback_stop,
                       "app.engine_paper.paper_config.PaperConfig.allow_fallback_stop"),
            _criterion("maximum_stop_distance", "stop_policy", C.NOT_CONFIGURED_AS_FIXED_THRESHOLD,
                       paper.maximum_stop_distance_pct,
                       "app.engine_paper.paper_config.PaperConfig.maximum_stop_distance_pct", "percent"),
        ),
        "target_policy": (
            _criterion("take_profit", "target_policy", C.DYNAMIC_RULE,
                       ["causal_target_level", "nearest_opposite_level"],
                       "app.engine_paper.paper_level_builder.PaperLevelBuilder.build"),
            _criterion("fallback_target_allowed", "target_policy", C.BOOLEAN_GATE,
                       paper.allow_fallback_target,
                       "app.engine_paper.paper_config.PaperConfig.allow_fallback_target"),
            _criterion("minimum_target_return", "target_policy", C.NOT_CONFIGURED_AS_FIXED_THRESHOLD,
                       None, "app.engine_paper.paper_config.PaperConfig.maximum_target_distance_pct", "percent"),
        ),
        "risk_reward_policy": (
            _criterion("minimum_planned_risk_reward", "risk_reward_policy", C.FIXED_THRESHOLD,
                       paper.minimum_planned_rr,
                       "app.engine_paper.paper_config.PaperConfig.minimum_planned_rr", "ratio"),
            _criterion("planned_risk_reward", "risk_reward_policy", C.DERIVED_VALUE,
                       "REWARD_DISTANCE_DIVIDED_BY_RISK_DISTANCE",
                       "app.engine_paper.paper_level_builder.PaperLevelBuilder.build", "ratio"),
        ),
        "position_sizing_policy": (
            _criterion("position_sizing", "position_sizing_policy", C.DYNAMIC_RULE,
                       "PERSISTED_CONTROLLED_QUANTITY_APPROVAL",
                       "app.engine_paper.paper_approvals.PaperQuantityApproval.approved_quantity"),
            _criterion("fixed_position_size", "position_sizing_policy",
                       C.NOT_CONFIGURED_AS_FIXED_THRESHOLD, None,
                       "app.engine_paper.paper_approvals.PaperQuantityApproval"),
        ),
        "fees_policy": (_criterion("fee_per_side", "fees_policy", C.FIXED_THRESHOLD,
                        str(fill.fee_bps), "app.operator_control.production_executor._foundation_policy", "bps"),),
        "slippage_policy": (
            _criterion("adverse_slippage_per_fill", "slippage_policy", C.FIXED_THRESHOLD,
                       str(fill.slippage_bps), "app.operator_control.production_executor._foundation_policy", "bps"),
            _criterion("fill_latency", "slippage_policy", C.FIXED_THRESHOLD,
                       fill.latency_candles, "app.operator_control.production_executor._foundation_policy",
                       "closed_1m_candles"),
        ),
        "approval_policy": (
            _criterion("approval_validity", "approval_policy", C.DYNAMIC_RULE,
                       "EARLIEST_PERSISTED_VALID_UNTIL_MS",
                       "app.engine_paper.production_approval.PaperProductionApprovalSourceAdapter"),
            _criterion("fixed_approval_ttl", "approval_policy", C.NOT_CONFIGURED_AS_FIXED_THRESHOLD,
                       None, "app.engine_paper.paper_approvals"),
        ),
        "first_canary_bounds": (
            _criterion("max_new_commands", "first_canary_bounds", C.FIXED_THRESHOLD,
                       canary_fields["max_new_commands"].default,
                       "app.operator_control.service.PaperOperatorControlService.arm_first_canary", "commands"),
            _criterion("max_open_positions", "first_canary_bounds", C.FIXED_THRESHOLD,
                       canary_fields["max_open_positions"].default,
                       "app.operator_control.service.PaperOperatorControlService.arm_first_canary", "positions"),
        ),
    }
    return {
        "title_key": "current_server_trading_criteria",
        "environment": control.environment, "mode": control.mode,
        "versioned_trading_policy_present": True,
        "canary_bound_policy_snapshot_available": False,
        "groups": {name: [asdict(item) for item in items] for name, items in groups.items()},
        "provenance": {
            "projection": "EFFECTIVE_CURRENT_SERVER_POLICY",
            "policy_versions": {"strategy": "StrategyConfig", "risk": risk.policy_version,
                                "paper_plan": paper.plan_policy_version, "fill": fill.contract_version},
        },
    }


__all__ = ("CriterionClassification", "TradingCriterion", "build_trading_criteria_snapshot")
