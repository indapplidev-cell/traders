from __future__ import annotations

import copy

import pytest

from app.config.yaml_authority import RESEARCH_PARAMETERS
from traders_ml.parameter_sweep.targeted import (
    active_search_space, research_config_hash, staged_candidates,
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
