import json
from pathlib import Path
from dataclasses import asdict

import pytest

from traders_ml.parameter_sweep.frozen_funnel import resolve_frozen_configuration, _FrozenOrchestratorConfig
from app.engine_orchestrator.runtime_parameters import _runtime_parameters


@pytest.fixture
def frozen():
    values = json.loads(Path("tests/research/fixtures/result_search_applicability.json").read_text())
    return values["cost"]["frozen"]


def test_trial_configuration_is_isolated_from_frozen_source(frozen):
    before = json.dumps(frozen, sort_keys=True)
    baseline = resolve_frozen_configuration(frozen, {})
    changed = resolve_frozen_configuration(frozen, {"geometry.atr_multiplier": 0.5})
    assert baseline.resolved_config_hash != changed.resolved_config_hash
    assert baseline.parameters.geometry.atr_multiplier != changed.parameters.geometry.atr_multiplier
    assert json.dumps(frozen, sort_keys=True) == before
    assert resolve_frozen_configuration(frozen, {}) == baseline


@pytest.mark.parametrize("key,value,consumer", [
    ("signal.strategy_minimum_score", 20, "risk_minimum_strategy_score"),
    ("signal.impulse_atr_multiplier", 0.5, "impulse_atr_multiplier"),
    ("signal.regime_lookback_candles", 30, "regime_lookback_candles"),
    ("signal.confirmation_window_candles", 3, "confirmation_window_candles"),
    ("geometry.atr_multiplier", 0.5, "geometry_atr_buffer_multiplier"),
    ("geometry.stop_max_bps", 60, "geometry_stop_envelope_bps"),
    ("geometry.minimum_planned_rr", 1.2, "minimum_planned_rr"),
    ("economics.min_net_edge_bps", 2, "economics_minimum_net_edge_bps"),
])
def test_explicit_parameters_reach_shared_runtime(frozen, key, value, consumer):
    resolved = resolve_frozen_configuration(frozen, {key: value})
    config = _FrozenOrchestratorConfig(resolved.parameters, symbols=("BTCUSDT",), trade_profile_id="trade-5m-v2")
    assert getattr(_runtime_parameters(config.trade_profile, resolved), consumer) == value


def test_reject_unknown_and_invalid_configuration(frozen):
    with pytest.raises(ValueError, match="UNKNOWN_PARAMETER"):
        resolve_frozen_configuration(frozen, {"invented": 1})
    with pytest.raises(ValueError):
        resolve_frozen_configuration(frozen, {"geometry.stop_max_bps": 0})
