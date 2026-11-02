from app.engine_strategy.strategy_filter import StrategyFilter


def test_expert_long_score_cannot_promote_bearish_setup(candidate_factory):
    candidate = candidate_factory(
        direction_hint="BEARISH", setup_quality="ACCEPTABLE", quality_score=70.0,
        context={"independent_expert": {
            "eligible": True, "calibration_id": "bull-run-expert-october-2026-v1",
            "entry_components": {name: 100.0 for name in (
                "structure", "context", "momentum", "volume", "entry_quality",
                "liquidity", "confirmation",
            )},
        }},
    )
    runtime = type("Runtime", (), {
        "profile_id": "trade-5m-v2", "entry_score_weights": (
            ("structure", 8.0), ("context", 22.0), ("momentum", 14.0),
            ("volume", 2.0), ("entry_quality", 22.0), ("liquidity", 22.0),
            ("confirmation", 10.0),
        ), "expert_calibration_enabled": True, "risk_minimum_strategy_score": 50.0,
        "strategy_not_evaluated_handling": "LEGACY_WEAK_CAP",
        "strategy_shadow_thresholds": (), "parameter_set_id": "set-2",
        "strategy_policy_id": "expert-long-only",
    })()
    decision = StrategyFilter(runtime_parameters=runtime).evaluate(candidate)
    assert decision.direction_hint == "BEARISH"
    assert decision.strategy_score == 49.999
