from types import SimpleNamespace
import pytest

from app.server_api.funnel_state import (
    STAGE_ALIASES, canonical_stages, compatibility_trace, lifecycle_stages,
)
from app.server_api.funnel_fields import market_fields, timeframe_states, detail_states
from app.server_api.funnel_export import build_export_record
from app.i18n.catalog import RU, EN
from tests.server_api.test_funnel_export import _pair


@pytest.mark.parametrize('rejection', [
    'STRUCTURAL_SETUP', 'GEOMETRY_VALID', 'TARGET_VALID', 'NET_COST_PASS', 'RR_PASS', None,
])
def test_canonical_stage_parity_and_no_pass_after_terminal(rejection):
    facts = dict.fromkeys(STAGE_ALIASES, 'PASS')
    if rejection:
        facts[rejection] = 'REJECTED'
    stages = canonical_stages(facts, {rejection: 'EXACT_CAUSAL_REASON'})
    compat = compatibility_trace(stages)
    terminated = False
    for stage in stages:
        assert compat[STAGE_ALIASES[stage.stage_id]]['canonical_status'] == stage.status
        assert compat[STAGE_ALIASES[stage.stage_id]]['reached'] == stage.reached
        if terminated:
            assert stage.status == 'NOT_REACHED' and not stage.reached
        if stage.terminal:
            assert stage.reason_code == 'EXACT_CAUSAL_REASON'
            terminated = True
        if stage.status in {'PASS', 'REJECTED'}:
            assert stage.reached


@pytest.mark.parametrize('outcome', [{}, {'command_id': 'cmd'}, {'command_id': 'cmd', 'position_id': 'pos'}])
def test_command_and_position_are_explicit_persisted_lifecycle_facts(outcome):
    stages = lifecycle_stages(outcome)
    compat = compatibility_trace(stages)
    assert compat['paper_command']['reached'] == bool(outcome.get('command_id'))
    assert compat['position']['reached'] == bool(outcome.get('position_id'))
    assert all(stage.phase == 'LIFECYCLE' for stage in stages)


@pytest.mark.parametrize('stage', ['STRUCTURAL_SETUP', 'GEOMETRY_VALID', 'TARGET_VALID', 'NET_COST_PASS', 'RR_PASS'])
def test_real_export_projects_same_rejection_for_both_traces(stage):
    run, result = _pair(profile='trade-5m-v2')
    diagnostic = result.paper_payload_json['paper_context']['scalping_geometry_diagnostics']
    if stage == 'STRUCTURAL_SETUP':
        run.setup_status = 'NO_SETUP'
        result.module_reasons_json = {'setup': ['NO_STRUCTURAL_SETUP']}
    else:
        key = {'GEOMETRY_VALID': 'stop_envelope_pass', 'TARGET_VALID': 'causal_target_exists',
               'NET_COST_PASS': 'economic_gate_pass', 'RR_PASS': 'valid_plan'}[stage]
        diagnostic[key] = False
        diagnostic['rejection_reason'] = 'EXACT_GATE_REASON'
    row = build_export_record(run, result, generated_at_ms=run.closed_until_ms,
                              from_ms=run.closed_until_ms, to_ms=run.closed_until_ms)
    assert row['first_rejection_stage'] == stage
    assert row['first_rejection_reason_code'] == row['terminal_reason']
    for canonical, alias in STAGE_ALIASES.items():
        assert row['downstream_stage_trace'][canonical] == row['funnel_trace'][alias]['canonical_status']
        assert row['canonical_stage_trace'][canonical]['reached'] == row['funnel_trace'][alias]['reached']


def test_real_sources_zero_values_and_distinct_absence_semantics():
    fields = market_fields({'analysis_context': {
        'quality_basis': {'impulse_context': {'atr_pct': 0.0}},
        'funnel_descriptive_sources': {'structure_state': 'SIDEWAYS_STRUCTURE', 'volume_context': {'available': True}},
    }})
    assert fields['atr_pct'] == 0.0 and fields['semantic_states']['atr_pct'] == 'AVAILABLE'
    assert fields['structure_state'] == 'SIDEWAYS_STRUCTURE'
    assert fields['semantic_states']['direction_confidence'] == 'NOT_EVALUATED'
    assert fields['semantic_states']['liquidity_state'] == 'NOT_EVALUATED'
    assert market_fields({})['semantic_states']['atr_pct'] == 'SOURCE_UNAVAILABLE'
    assert market_fields({}, analysis_reached=False)['semantic_states']['atr_pct'] == 'NOT_REACHED'
    for catalog in (RU, EN):
        labels = [catalog['funnel.status.' + state] for state in (
            'NOT_REACHED', 'NOT_EVALUATED', 'NOT_APPLICABLE', 'SOURCE_UNAVAILABLE')]
        assert len(set(labels)) == 4
        assert catalog['funnel.unavailable'] not in labels


def test_four_hours_is_not_in_v2_closed_candle_contract():
    states = timeframe_states({'1m': 100, '5m': 100, '15m': 100, '1h': 100, '4h': None}, ('1m', '5m', '15m', '1h'))
    assert states['4h'] == 'NOT_APPLICABLE'
    assert states['5m'] == 'AVAILABLE'


def test_downstream_null_does_not_conflate_unreached_with_unevaluated():
    assert detail_states({'stop_price': None}, {'GEOMETRY_VALID': 'NOT_REACHED'})['stop_price'] == 'NOT_REACHED'
    assert detail_states({'stop_price': None}, {'GEOMETRY_VALID': 'PASS'})['stop_price'] == 'NOT_EVALUATED'


def test_real_analysis_preserves_existing_structure_and_volume_sources():
    from app.engine_analysis.online_runner import OnlineAnalysisRunner
    from app.engine_analysis.online_config import OnlineAnalysisConfig
    from app.engine_analysis.market_data_adapter import MarketDataAdapter
    from app.engine_analysis.analysis_snapshot_store import AnalysisSnapshotStore
    from tests.engine_analysis.test_scalping_semantics import snapshot
    runner = OnlineAnalysisRunner(
        OnlineAnalysisConfig(required_history_candles=32, max_snapshot_age_ms=0),
        MarketDataAdapter(), AnalysisSnapshotStore(),
    )
    result = runner.analyze_market_data_snapshot(snapshot([2.0] * 32))
    assert result.status == 'ANALYZED'
    sources = result.analysis_context['funnel_descriptive_sources']
    assert sources['structure_state'] in {'BULLISH_STRUCTURE', 'BEARISH_STRUCTURE', 'SIDEWAYS_STRUCTURE', 'UNCLEAR_STRUCTURE'}
    assert sources['volume_context']['available'] is True
