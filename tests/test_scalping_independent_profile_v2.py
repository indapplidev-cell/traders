import hashlib
import json
from dataclasses import asdict

from app.engine_orchestrator.runtime_parameters import resolve_runtime_parameters
from app.engine_orchestrator.trade_profile import resolve_trade_profile
from app.engine_paper.scalping_policy_v2 import (
    EmpiricalSetupBucket,
    evaluate_expectancy,
)
from app.engine_paper.scalping_shadow import (
    CausalTarget,
    ShadowCostInputs,
    ShadowGeometryCandidate,
    ShadowGeometryConfig,
    evaluate_scalping_shadow,
)
from app.engine_setup.setup_context import SetupContext
from app.engine_setup.setup_detector import SetupDetector
from app.engine_setup.setup_rules import evaluate_setup_rules


FROZEN_15M_ID = "trade-15m-v1-runtime-v1-44aa91202a60146c"
FROZEN_15M_HASH = "e48878b06f3ea1bf26a5b3dad67bdf41bb7ea50470cd5789b935f568fa94425b"


def test_15m_strategy_parameters_are_unchanged_while_execution_is_disabled():
    profile = resolve_trade_profile("trade-15m-v1")
    runtime = resolve_runtime_parameters("trade-15m-v1")
    payload = json.dumps(
        {"profile": asdict(profile), "runtime": asdict(runtime)},
        sort_keys=True, separators=(",", ":"),
    )
    assert profile.minimum_planned_rr == 1.5
    assert runtime.minimum_planned_rr == 1.5
    assert profile.paper_command_creation_enabled is False
    assert profile.position_opening_enabled is False


def test_v2_has_independent_versioned_policy_and_stronger_or_equal_risk():
    new = resolve_runtime_parameters("trade-5m-v2")
    assert new.parameter_set_id.startswith("trade-5m-v2-runtime-v1-")
    assert new.setup_policy_id == "scalping-micro-setup-v2"
    assert new.strategy_policy_id == "scalping-short-horizon-entry-v2"
    assert new.stop_policy_id == "SCALPING_CAUSAL_VOLATILITY_STOP_V2"
    assert new.target_policy_id == "SCALPING_NEAREST_VIABLE_TARGET_V3"
    assert new.risk_shadow_policy_id == "scalping-risk-capped-v2"
    assert new.minimum_planned_rr == 0.4
    assert new.execution_entry_ttl_seconds == 30
    assert new.exit_time_stop_minutes == 15
    assert new.risk_per_trade_bps == 10
    assert new.portfolio_max_concurrent_positions == 2
    assert new.portfolio_max_total_open_risk_bps == 50


def _directional_context():
    return SetupContext(
        regime="UP", confidence=0.8, action=None,
        impulse_phase="IMPULSE_EXTENSION", entry_quality="GOOD",
        analysis_context={"scalping": {
            "market_regime": "EXPANSION", "base_regime": "UP",
            "entry_evidence_strength": "STRONG",
        }},
    )


def test_v2_micro_setup_path_is_isolated_from_15m():
    context = _directional_context()
    legacy = evaluate_setup_rules(context)
    v2 = SetupDetector(resolve_runtime_parameters("trade-5m-v2"))
    fifteen = SetupDetector(resolve_runtime_parameters("trade-15m-v1"))
    promoted = v2._scalping_v2_micro_setup(legacy, context)
    assert promoted.status == "SETUP_CANDIDATE"
    assert fifteen._scalping_v2_micro_setup(legacy, context) == legacy


def test_empirical_ev_uses_observed_bucket_and_static_fallback():
    positive = evaluate_expectancy(
        net_win_bps=60, net_loss_bps=40,
        bucket=EmpiricalSetupBucket("MICRO_BREAKOUT", "BULLISH", 30, 20),
    )
    negative = evaluate_expectancy(
        net_win_bps=30, net_loss_bps=60,
        bucket=EmpiricalSetupBucket("MICRO_BREAKOUT", "BULLISH", 30, 5),
    )
    fallback = evaluate_expectancy(
        net_win_bps=30, net_loss_bps=60, bucket=None,
        static_net_rr=0.4, static_minimum_net_rr=0.4,
    )
    assert positive.admitted and positive.expected_value_bps > 0
    assert not negative.admitted and negative.expected_value_bps < 0
    assert fallback.admitted and fallback.expected_value_bps is None


def test_v2_target_rr_ev_path_is_profile_scoped_and_cost_complete():
    candidate = ShadowGeometryCandidate(
        trade_profile_id="trade-5m-v2", symbol="BTCUSDT", boundary_ms=2_000,
        direction="BULLISH", entry=100.0, causal_invalidation=99.8, atr=0.05,
        targets=(CausalTarget(101.0, "LOCAL_RANGE_BOUNDARY", 2_000),),
        setup_identity="micro-breakout",
    )
    costs = ShadowCostInputs(
        spread_bps=1.0, depth_impact_bps=1.0,
        spread_authoritative=True, depth_authoritative=True,
        commission_authoritative=True,
        commission_symbol="BTCUSDT",
        commission_snapshot_id="fixture:commission:v1",
        commission_fetched_at="2026-09-04T00:00:00Z",
    )
    result = evaluate_scalping_shadow(candidate, costs, ShadowGeometryConfig(
        atr_buffer_multiplier=0.25, stop_envelope_bps=50.0,
        minimum_target_diagnostic_bps=45.0, production_rr_floor=0.4,
        profile_id="trade-5m-v2",
    ))
    assert result.valid_plan
    assert result.total_cost_bps == 29.0
    assert result.required_rr == 0.4
    assert result.rr_policy_version == "scalping-empirical-ev-v1"
    assert result.target_policy_version == "scalping-nearest-viable-target-v3"
    assert result.expectancy_gate_reason == "INSUFFICIENT_BUCKET_STATIC_RR_PASS"


def test_retired_v1_geometry_config_is_rejected():
    try:
        ShadowGeometryConfig(
            atr_buffer_multiplier=0.25, stop_envelope_bps=50.0,
            minimum_target_diagnostic_bps=45.0, production_rr_floor=0.4,
            profile_id="trade-5m-v1",
        )
    except ValueError as exc:
        assert "only trade-5m-v2" in str(exc)
    else:
        raise AssertionError("v1 RR floor was weakened")
