from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

import pytest

from app.config.trade_parameters import TRADE_PARAMETERS, TradeParameters
from app.engine_orchestrator.pipeline_runner import PipelineRunner
from app.engine_orchestrator.runtime_parameters import resolve_runtime_parameters
from tests.engine_orchestrator.test_parallel_trade_profiles import five_minute_config
from tests.engine_orchestrator_01_helpers import BOUNDARY, CandleRepo, component, outputs


def configuration(active="scalping-v2-set-1", previous="scalping-v2-set-1", cutoff=BOUNDARY):
    raw = deepcopy(TRADE_PARAMETERS.model_dump(mode="python", by_alias=True))
    raw["scalping_v2"]["paper"].update(
        active_parameter_set=active, previous_parameter_set=previous,
        activation_cycle_boundary_ms=cutoff,
    )
    return TradeParameters.model_validate(raw)


def test_real_pipeline_cycle_uses_cutoff_and_keeps_snapshot_during_switch():
    current = configuration("scalping-v2-set-2", cutoff=BOUNDARY + 300000)
    analysis, setup, strategy, risk, paper = outputs()
    runner = PipelineRunner(
        five_minute_config(), CandleRepo(), parameter_loader=lambda: current,
        analysis_runner=component(analysis), setup_runner=component(setup),
        strategy_runner=component(strategy), risk_runner=component(risk),
        paper_runner=component(paper),
    )
    before = runner.run("BTCUSDT", BOUNDARY)
    assert before.runtime_parameter_set_id == "scalping-v2-set-1"
    frozen = runner.for_cycle(BOUNDARY)
    assert frozen.runtime_parameters.minimum_planned_rr == .4
    assert frozen.runtime_parameters.risk_per_trade_bps == 10
    # Selector changes while more symbols/retries for A can still arrive.
    current = configuration("scalping-v2-set-2", cutoff=BOUNDARY)
    assert runner.for_cycle(BOUNDARY) is frozen
    after = runner.run("BTCUSDT", BOUNDARY + 300000)
    assert after.runtime_parameter_set_id == "scalping-v2-set-2"
    assert before.runtime_parameters_snapshot.risk_per_trade_bps == 10
    assert after.runtime_parameters_snapshot.risk_per_trade_bps == 5
    assert runner.for_cycle(BOUNDARY + 300000).runtime_parameters.minimum_planned_rr == .6
    current = configuration("scalping-v2-set-1", "scalping-v2-set-2", BOUNDARY + 600000)
    rollback = runner.run("BTCUSDT", BOUNDARY + 600000)
    assert rollback.runtime_parameter_set_id == "scalping-v2-set-1"
    assert before.runtime_parameter_set_id == "scalping-v2-set-1"
    assert after.runtime_parameter_set_id == "scalping-v2-set-2"


def test_geometry_and_ev_consumers_receive_same_frozen_values_and_concurrent_read_is_atomic():
    current = configuration()
    reads = []
    def load():
        reads.append(1)
        return current
    runner = PipelineRunner(five_minute_config(), CandleRepo(), parameter_loader=load)
    with ThreadPoolExecutor(max_workers=8) as pool:
        cycles = list(pool.map(runner.for_cycle, [BOUNDARY] * 24))
    assert len(reads) == 1
    assert all(cycle is cycles[0] for cycle in cycles)
    first = cycles[0]
    current = configuration("scalping-v2-set-2")
    second = runner.for_cycle(BOUNDARY + 300000)
    assert first.paper_runner.geometry_config.production_rr_floor == .4
    assert first.paper_runner.geometry_config.minimum_ev_reserve_r == 0
    assert second.paper_runner.geometry_config.production_rr_floor == .6
    assert second.paper_runner.geometry_config.minimum_target_diagnostic_bps == 60
    assert second.paper_runner.geometry_config.minimum_ev_reserve_r == .05
    assert second.runtime_parameters.risk_per_trade_bps == 5
    assert first.paper_runner.geometry_config.minimum_ev_reserve_r == 0
    assert runner.for_cycle(BOUNDARY) is first


def test_invalid_next_cycle_never_runs_with_previous_or_mixed_config():
    runner = PipelineRunner(five_minute_config(), CandleRepo(),
                            parameter_loader=lambda: configuration("scalping-v2-set-999"))
    with pytest.raises(RuntimeError, match="UNKNOWN_PARAMETER_SET"):
        runner.run("BTCUSDT", BOUNDARY)
    assert not runner._cycle_runners


def test_15m_identity_remains_identical_to_pre_named_set_commit():
    assert resolve_runtime_parameters("trade-15m-v1").parameter_set_id == "trade-15m-v1-runtime-v1-9d094c9e2a6186bf"
