from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace

from app.config.trade_parameters import parameter_snapshot
from app.engine_orchestrator.pipeline_runner import PipelineRunner
from app.engine_paper.scalping_shadow import evaluate_scalping_shadow, CausalTarget
from app.engine_paper.trading_criteria import build_trading_criteria_snapshot
from app.server_api.schemas.paper import TradingCriteriaSnapshot
from tests.engine_orchestrator.test_parameter_set_cycle_binding import configuration
from tests.engine_orchestrator.test_parallel_trade_profiles import five_minute_config
from tests.engine_orchestrator_01_helpers import BOUNDARY, CandleRepo
from tests.test_5m_scalping_geometry_quota_cost_remediation import candidate, costs


def test_frozen_snapshot_matches_actual_geometry_ev_inputs(monkeypatch):
    current = configuration("scalping-v2-set-2")
    pipeline = PipelineRunner(five_minute_config(), CandleRepo(), parameter_loader=lambda: current)
    cycle = pipeline.for_cycle(BOUNDARY)
    frozen = cycle._profiled_payload({})["frozen_parameter_snapshot"]
    expected = {"geometry.minimum_planned_rr": .6, "geometry.target_min_bps": 60,
                "risk.risk_per_trade_bps": 5, "economics.min_ev_reserve_r": .05}
    for path, value in expected.items():
        assert frozen["parameters"][path]["value"] == value
        assert frozen["parameters"][path]["source"] == "SET_2_OVERRIDE"
    assert frozen["parameters"]["risk.max_open_positions"]["source"] == "SET_1_INHERITED"
    assert frozen["parameters"]["signal.impulse_absolute_threshold_pct"] == {
        "value": 3.0, "source": "SET_1_INHERITED", "owner_set_id": "scalping-v2-set-1",
        "source_component": "config/trading/trade_parameters.yaml::signal.impulse_absolute_threshold_pct",
    }
    assert cycle.risk_runner.policy.runtime_parameters.risk_per_trade_bps == 5
    captured = []
    import app.engine_paper.scalping_shadow as module
    actual = module.evaluate_expectancy
    def spy(**kwargs):
        captured.append(kwargs)
        return actual(**kwargs)
    monkeypatch.setattr(module, "evaluate_expectancy", spy)
    row = evaluate_scalping_shadow(candidate(trade_profile_id="trade-5m-v2", boundary_ms=BOUNDARY,
        targets=(CausalTarget(102, "LOCAL_5M", BOUNDARY),)),
        costs(commission_authoritative=True, fee_source="BINANCE_ACCOUNT_COMMISSION_SNAPSHOT"),
        cycle.paper_runner.geometry_config)
    assert row.evaluator_inputs["minimum_planned_rr"] == .6
    assert row.evaluator_inputs["target_min_bps"] == 60
    assert row.evaluator_inputs["min_ev_reserve_r"] == .05
    assert captured and captured[0]["minimum_ev_reserve_r"] == .05
    assert captured[0]["static_minimum_net_rr"] == .6
    current = configuration()
    assert pipeline.for_cycle(BOUNDARY)._profiled_payload({})["frozen_parameter_snapshot"] == frozen
    assert pipeline.for_cycle(BOUNDARY + 300000).runtime_parameters.minimum_planned_rr == .4
    snapshot = TradingCriteriaSnapshot.model_validate(build_trading_criteria_snapshot(None, frozen))
    assert snapshot.provenance.frozen_parameter_snapshot == frozen
    assert snapshot.groups["legacy_risk_reward_policy"][0].value == 1.5
    assert snapshot.groups["active_scalping_parameters"][0].parameter_source == "SET_2_OVERRIDE"


def test_missing_snapshot_does_not_fabricate_current_set():
    result = build_trading_criteria_snapshot()
    assert result["provenance"]["frozen_parameter_snapshot"] is None
    assert result["provenance"]["snapshot_availability"] == "LEGACY_UNAVAILABLE"
    assert result["groups"]["active_scalping_parameters"] == []


def test_quantity_sizing_uses_five_bps_not_legacy_one_percent():
    from app.engine_paper.controlled_quantity_validity import calculate_quantity_sizing
    common = dict(symbol="BTCUSDT", equity=Decimal("10000"),
                  entry=Decimal("100000"), stop=Decimal("99000"))
    sized = calculate_quantity_sizing(**common, risk_per_trade_bps=Decimal("5"))
    legacy = calculate_quantity_sizing(**common)
    assert sized.risk_budget == Decimal("5")
    assert sized.normalized_quantity * sized.risk_per_unit <= Decimal("5")
    assert sized.risk_parameter_source == "SCALPING_V2_RUNTIME_PARAMETERS/risk_per_trade_bps"
    assert legacy.risk_budget == Decimal("100")


def test_actual_materializer_passes_frozen_risk_to_quantity_authority(monkeypatch):
    import tests.final_approval_generation_integration.test_natural_materialization as fixture
    from app.engine_orchestrator.pipeline_result import PipelineResult
    from app.engine_orchestrator.runtime_parameters import resolve_runtime_parameters
    import app.engine_paper.final_approval_materializer as module
    # Adapt the old 15m fixture's implicit default to its explicit domain.
    monkeypatch.setattr(fixture, "PipelineResult", lambda **kw: PipelineResult(trade_profile_id="trade-15m-v1", **kw))
    monkeypatch.setattr(fixture, "resolve_runtime_parameters", lambda _profile: resolve_runtime_parameters("trade-5m-v2"))
    value = fixture.five_minute_natural_result()
    value.trade_profile_id = "trade-5m-v2"
    value.trigger_timeframe = "5m"
    value.runtime_parameters_snapshot = resolve_runtime_parameters("trade-5m-v2")
    value.runtime_parameter_set_id = value.runtime_parameters_snapshot.parameter_set_id
    calls = []
    original = module.issue_controlled_paper_quantity_approval
    def spy(*args, **kwargs):
        calls.append(kwargs["risk_per_trade_bps"])
        return original(*args, **kwargs)
    monkeypatch.setattr(module, "issue_controlled_paper_quantity_approval", spy)
    fixture.materialize(value, equity=Decimal("10000"))
    assert calls == [Decimal("5")]
