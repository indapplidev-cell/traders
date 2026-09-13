from app.config.trade_parameters import load_trade_parameters
from app.engine_orchestrator.pipeline_runner import PipelineRunner
from tests.engine_orchestrator.test_parallel_trade_profiles import five_minute_config
from tests.engine_orchestrator_01_helpers import CandleRepo
import pytest
from dataclasses import replace
from app.config.trade_parameters import TradeParameters
from app.engine_orchestrator.config_epoch import ConfigurationEpoch
from app.server_api.effective_configuration import effective_configuration
from app.server_api.funnel_export import build_export_record
from tests.server_api.test_funnel_export import _pair


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


def test_hash_epoch_and_stale_process_snapshot(monkeypatch):
    monkeypatch.setenv('TRADERS_RUNTIME_SOURCE_IDENTITY', 'a' * 40)
    raw = load_trade_parameters().model_dump(mode='python', by_alias=True)
    raw['profiles']['trade-5m-v2']['economics']['min_net_edge_bps'] = 1.0
    old = TradeParameters.model_validate(raw).resolve_scalping_v2_parameter_set()
    new = load_trade_parameters().resolve_scalping_v2_parameter_set()
    a = ConfigurationEpoch.capture(old, loaded_at='2026-09-13T01:00:00+00:00')
    b = ConfigurationEpoch.capture(new, loaded_at='2026-09-13T02:00:00+00:00')
    c = ConfigurationEpoch.capture(new, loaded_at='2026-09-13T03:00:00+00:00')
    assert a.config_content_hash != b.config_content_hash
    assert b.config_content_hash == c.config_content_hash
    assert b.project()['config_epoch_id'] != c.project()['config_epoch_id']
    assert len(b.config_content_hash) == 64
    assert a.project()['parameters']['min_net_edge_bps'] == 1.0
    for resolved in (old, new):
        runner = PipelineRunner(five_minute_config(), CandleRepo(), resolved_parameter_set=resolved)
        projected = runner._profiled_payload({})['effective_configuration']
        assert projected['parameters']['min_net_edge_bps'] == runner.paper_runner.geometry_config.minimum_positive_edge_bps
        assert projected['source_commit'] == 'a' * 40


def test_early_rejection_export_uses_persisted_epoch_not_current_yaml():
    run, result = _pair(profile='trade-5m-v2')
    epoch = ConfigurationEpoch.capture(load_trade_parameters().resolve_scalping_v2_parameter_set()).project()
    result.analysis_payload_json['effective_configuration'] = epoch
    result.setup_payload_json = {'setup_status': 'NO_SETUP'}
    result.paper_payload_json = {'paper_status': 'NO_PLAN'}
    record = build_export_record(run, result, generated_at_ms=run.closed_until_ms,
                                 from_ms=run.closed_until_ms, to_ms=run.closed_until_ms)
    assert record['effective_configuration'] == epoch
    assert len(record['effective_configuration']['parameters']) == 4
    # Serialization must not alter the captured record or replace old values.
    epoch['parameters']['min_net_edge_bps'] = 1.0
    assert effective_configuration(result)['parameters']['min_net_edge_bps'] == 1.0
    result.analysis_payload_json = {}
    assert effective_configuration(result) is None


def test_v1_export_schema_accepts_additive_epoch_via_real_http():
    import json
    from tests.server_api.test_funnel_export import _get, _client, ExportRepo
    run, result = _pair(profile='trade-5m-v2')
    epoch = ConfigurationEpoch.capture(load_trade_parameters().resolve_scalping_v2_parameter_set()).project()
    result.analysis_payload_json['effective_configuration'] = epoch
    response = _get(_client(ExportRepo(((run, result),))), trade_profile_id='trade-5m-v2')
    assert response.status_code == 200
    row = json.loads(response.text)
    assert row['provenance']['export_schema_version'] == 'trading-funnel-export-v1'
    assert row['effective_configuration'] == epoch
