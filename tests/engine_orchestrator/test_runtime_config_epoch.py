from app.config.trade_parameters import load_trade_parameters
from app.engine_orchestrator.pipeline_runner import PipelineRunner
from tests.engine_orchestrator.test_parallel_trade_profiles import five_minute_config
from tests.engine_orchestrator_01_helpers import CandleRepo
import pytest
from dataclasses import replace


def test_active_global_parameters_reach_real_consumers():
    resolved = load_trade_parameters().resolve_scalping_v2_parameter_set()
    runner = PipelineRunner(five_minute_config(), CandleRepo(), resolved_parameter_set=resolved)
    config = runner.paper_runner.geometry_config
    assert config.minimum_positive_edge_bps == 73.004386
    assert config.production_rr_floor == 1.953403
    assert config.stop_envelope_bps == 48.496589
    assert config.minimum_target_diagnostic_bps == 49.163216
    snapshot = runner._profiled_payload({})['frozen_parameter_snapshot']['parameters']
    assert snapshot['economics.min_net_edge_bps']['value'] == config.minimum_positive_edge_bps
    assert snapshot['geometry.minimum_planned_rr']['value'] == config.production_rr_floor
    assert snapshot['geometry.stop_max_bps']['value'] == config.stop_envelope_bps
    assert snapshot['geometry.target_min_bps']['value'] == config.minimum_target_diagnostic_bps


@pytest.mark.parametrize('field,value', [
    ('stop_envelope_bps', 0), ('stop_envelope_bps', float('inf')),
    ('minimum_target_diagnostic_bps', -1), ('minimum_target_diagnostic_bps', float('nan')),
    ('production_rr_floor', .19), ('production_rr_floor', float('inf')),
])
def test_active_geometry_keeps_invalid_values_fail_closed(field, value):
    resolved = load_trade_parameters().resolve_scalping_v2_parameter_set()
    runner = PipelineRunner(five_minute_config(), CandleRepo(), resolved_parameter_set=resolved)
    with pytest.raises(ValueError):
        replace(runner.paper_runner.geometry_config, **{field: value})
