from __future__ import annotations

import copy

import pytest

from app.config.yaml_authority import RESEARCH_PARAMETERS
from traders_ml.parameter_sweep.targeted import (
    active_search_space, deduplicate_behavioral_configs, research_config_hash,
    sensitivity_preflight, staged_candidates, TargetedCandidate,
    validate_targeted_space,
)


def _config():
    return RESEARCH_PARAMETERS.model_dump(mode="python")


def test_targeted_space_contains_only_yaml_owned_active_families():
    config = _config()
    validate_targeted_space(config)
    active = active_search_space(config)
    allowed = {name for family in config["calibration"]["targeted_families"] for name in config["calibration"]["parameter_families"][family]}
    frozen = {name for family in config["calibration"]["frozen_families"] for name in config["calibration"]["parameter_families"][family]}
    assert set(active) <= allowed
    assert not set(active) & frozen
    assert "minimum_planned_rr" not in active
    assert "probability_confidence_level" not in active
    assert "risk_per_trade_bps" not in active


def test_staged_candidates_are_deterministic_bounded_and_baseline_first():
    config = _config()
    baseline = {name: values[0] for name, values in config["search_space"].items()}
    left = list(staged_candidates(config, baseline))
    right = list(staged_candidates(copy.deepcopy(config), baseline))
    assert left == right
    assert left[0].stage == "SET2_BASELINE" and left[0].overrides == {}
    assert len(left) <= config["search"]["max_total_configs"]
    assert len({tuple(sorted(item.overrides.items())) for item in left}) == len(left)
    assert {item.stage for item in left} == {
        "SET2_BASELINE", "ONE_FACTOR_SENSITIVITY", "SMALL_FAMILY_SEARCH",
        "TOP_REGION_REFINEMENT", "LOCAL_FINALIST_VALIDATION",
    }


def test_frozen_family_cannot_be_declared_targeted():
    config = _config()
    config["calibration"]["targeted_families"] = (*config["calibration"]["targeted_families"], "COSTS")
    with pytest.raises(ValueError, match="PARAMETER_FAMILY_PARTITION_INVALID"):
        validate_targeted_space(config)


def test_research_hash_changes_with_yaml_search_value():
    config = _config()
    before = research_config_hash(config)
    config["search_space"]["stop_max_bps"][0] += 1
    assert research_config_hash(config) != before


def test_sensitivity_detects_no_op_and_preserves_each_declared_family():
    config = _config()
    config["search_space"] = {
        "strategy_minimum_score": [45.0, 55.0],
        "regime_lookback_candles": [12, 24],
        "entry_refinement_1m_confirmation_count": [1, 2],
        "stop_max_bps": [50.0, 60.0],
        "target_min_bps": [45.0, 55.0],
        "causal_reset_min_conditions": [1, 2],
    }
    baseline = {name: values[0] for name, values in config["search_space"].items()}
    def signature(resolved):
        return {key: value for key, value in resolved.items() if key != "causal_reset_min_conditions"}
    result = sensitivity_preflight(config, baseline, signature)
    assert set(result["active_families"]) == {"SIGNAL", "REGIME", "ENTRY", "GEOMETRY"}
    assert set(result["no_op_dimensions"]) == {"causal_reset_min_conditions"}
    assert result["raw_config_count"] == 64
    assert result["unique_effective_config_count"] == 32
    assert result["planning_snapshots"]["declared_targeted_families"] == [
        "SIGNAL", "REGIME", "ENTRY", "GEOMETRY",
    ]
    assert result["dimension_trace"]["causal_reset_min_conditions"] == {
        "canonical_key": "causal_reset_min_conditions",
        "family": "ENTRY",
        "baseline_value": 1,
        "candidate_values": [1, 2],
        "source_yaml": "config/research/research_parameters.yaml#search_space",
        "activation_state": "BEHAVIORAL_NO_OP",
        "removal_stage": "NO_OP_DETECTION",
        "removal_reason": "BEHAVIORAL_NO_OP",
    }


def test_behavioral_dedup_records_aliases():
    configs = [TargetedCandidate("X", {"value": value}) for value in (1, 2, 3)]
    representatives, aliases = deduplicate_behavioral_configs(configs, lambda item: item["value"] % 2)
    assert len(representatives) == 2
    assert sum(map(len, aliases.values())) == 1
