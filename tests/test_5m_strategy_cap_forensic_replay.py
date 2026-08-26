from __future__ import annotations

import pytest

from app.engine_observation.strategy_forensic import replay_strategy_rejects
from app.engine_risk.risk_config import RiskConfig
from app.engine_risk.risk_limits import ResearchRiskLimits
from app.engine_risk.risk_policy import RiskPolicy
from app.engine_setup.setup_diagnostics import SetupDiagnostics
from app.engine_setup.setup_candidate import SetupCandidate
from app.engine_setup.setup_quality_diagnostics import diagnose_setup_quality
from app.engine_strategy.strategy_filter import StrategyFilter
from app.engine_strategy.strategy_rules import strategy_shadow_variants
from app.engine_strategy.strategy_context import StrategyContext


@pytest.fixture
def candidate_factory():
    def build(**changes):
        values = {
            "setup_id": "setup:forensic:1", "symbol": "BTCUSDT", "timeframe": "15m",
            "closed_until_ms": 1_700_000_000_000, "created_at_ms": 1_700_000_000_001,
            "source_analysis_snapshot_id": "analysis:forensic:1", "source_regime": "UP",
            "source_confidence": .8, "source_action": "NO_ACTION",
            "source_entry_quality": "ACCEPTABLE", "status": "SETUP_CANDIDATE",
            "setup_type": "BREAKOUT_CONTINUATION", "direction_hint": "BULLISH",
            "confirmation_state": "CONFIRMED_BY_ANALYSIS", "setup_quality": "ACCEPTABLE",
            "quality_score": 72.0, "diagnostics": SetupDiagnostics(
                has_structural_trigger=True, has_directional_context=True,
                is_actionable_setup_candidate=True, semantic_bucket="CANDIDATE_STRUCTURE",
            ),
        }
        values.update(changes)
        return SetupCandidate(**values)
    return build


def _raw95_candidate(candidate_factory):
    quality = diagnose_setup_quality(
        status="SETUP_CANDIDATE", setup_type="BREAKOUT_CONTINUATION",
        direction_hint="BULLISH", confirmation_state="CONFIRMED_BY_ANALYSIS",
        diagnostics=SetupDiagnostics(
            has_structural_trigger=True, has_directional_context=True,
            has_level_context=False, is_actionable_setup_candidate=True,
            semantic_bucket="CANDIDATE_STRUCTURE",
        ),
        source_analysis_entry_quality="NOT_EVALUATED", source_confidence=1.0,
        source_regime="UP", source_impulse_phase="IMPULSE_EXTENSION",
    )
    return candidate_factory(
        timeframe="5m", source_confidence=1.0,
        source_entry_quality="NOT_EVALUATED", quality_diagnostics=quality,
    )


def test_raw95_to_64_999_has_two_caps_and_boolean_terminal_gate(candidate_factory):
    candidate = _raw95_candidate(candidate_factory)
    decision = StrategyFilter().evaluate(candidate)
    assert decision.strategy_raw_score == 95.0
    assert decision.strategy_penalty_total == 0.0
    assert decision.strategy_pre_cap_score == 66.999
    assert decision.strategy_final_score == 64.999
    assert [item["cap_type"] for item in decision.strategy_caps] == [
        "ANALYSIS_ENTRY_QUALITY_TIER_CAP", "SETUP_QUALITY_TIER_CLAMP",
    ]
    assert decision.strategy_failed_gate == "WEAK_QUALITY_GATE"
    assert decision.strategy_failed_gate_reason == "STRATEGY_REJECT_WEAK_QUALITY"


def test_shadow_no_cap_is_one_factor_and_production_decision_is_unchanged(candidate_factory):
    candidate = _raw95_candidate(candidate_factory)
    context = StrategyContext.from_setup_candidate(candidate)
    production_before = StrategyFilter().evaluate(candidate)
    variants = strategy_shadow_variants(context, StrategyFilter().config)
    production_after = StrategyFilter().evaluate(candidate)
    assert (
        production_before.decision_status, production_before.strategy_score,
        production_before.rejection_reasons,
    ) == (
        production_after.decision_status, production_after.strategy_score,
        production_after.rejection_reasons,
    )
    assert variants["SHADOW_BASELINE"].status == "REJECT"
    assert variants["SHADOW_NO_CAP"].status == "ALLOW_RESEARCH_TRADE_PLAN"
    assert variants["SHADOW_NO_SPECIFIC_GATE"].status == "REJECT"
    assert variants["SHADOW_RAW_SCORE_ONLY_DIAGNOSTIC"]["diagnostic_only"] is True


def test_shadow_risk_does_not_reserve_quota(candidate_factory):
    decision = StrategyFilter().evaluate(candidate_factory())
    limits = ResearchRiskLimits()
    policy = RiskPolicy(config=RiskConfig(allow_medium_risk=True), limits=limits)
    assert limits.profile_attempts("trade-15m-v1", decision.closed_until_ms) == 0
    assert policy.evaluate_shadow(decision).risk_status == "RISK_PRE_APPROVED_RESEARCH"
    assert policy.evaluate_shadow(decision).risk_status == "RISK_PRE_APPROVED_RESEARCH"
    assert limits.profile_attempts("trade-15m-v1", decision.closed_until_ms) == 0


def test_persisted_replay_uses_causal_geometry_and_missing_costs_fail_closed():
    row = {
        "run_id": "run:1", "boundary": 1_800_000_000_000, "symbol": "BTCUSDT",
        "parameter_set_id": "trade-5m-v1-runtime-v1-test",
        "setup": {
            "setup_status": "SETUP_CANDIDATE", "setup_type": "BREAKOUT_CONTINUATION",
            "setup_quality": "WEAK", "quality_score": 64.999,
            "source_entry_quality": "NOT_EVALUATED",
            "quality_diagnostics": {
                "capped_by_analysis_entry_quality": True,
                "source_analysis_entry_quality": "NOT_EVALUATED",
                "quality_reasons": ["QUALITY_CAPPED_BY_ANALYSIS_ENTRY_QUALITY"],
            },
        },
        "strategy": {
            "decision_status": "REJECT", "strategy_score": 64.999,
            "strategy_raw_score": 95.0, "strategy_penalty_total": 0.0,
            "component_scores": {
                "structure": 30.0, "candle_confirmation": 30.0,
                "context_alignment": 35.0,
            },
            "rejection_reasons": ["STRATEGY_REJECT_WEAK_QUALITY"],
            "context": {
                "analysis_confidence": 1.0, "direction_hint": "BULLISH",
                "confirmation_close": 100.0, "causal_invalidation_level": 99.5,
                "atr_value": 0.5, "causal_target_level": 101.0,
                "setup_type": "BREAKOUT_CONTINUATION",
            },
        },
    }
    result = replay_strategy_rejects([row])
    summary = result["summary"]
    record = result["records"][0]
    assert summary["cap_bound_reject_count"] == 1
    assert summary["shadow_no_cap_strategy_pass"] == 1
    assert summary["shadow_no_cap_geometry_valid"] == 1
    assert summary["shadow_no_cap_target_valid"] == 1
    assert summary["shadow_no_cap_cost_pass"] == 0
    assert record["shadow_geometry"]["rejection_stage"] == "NET_COST_GATE"
    assert record["future_leakage"] is False
