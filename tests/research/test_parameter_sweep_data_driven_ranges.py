from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from app.config.yaml_authority import RESEARCH_PATH, load_data_driven_range_policy
from traders_ml.parameter_sweep.data_driven_ranges import (
    build_parameter_evidence_map,
    generate_range_artifacts,
)


def _policy():
    return load_data_driven_range_policy(RESEARCH_PATH)


def _mapping(
    *, name="threshold", parameter_type="NUMERIC", current=50.0,
    evidence_class="DIRECT_EVIDENCE", feature="signal", eligible=True,
    minimum=0.0, maximum=100.0, inclusive=True,
):
    return {
        "artifact": "PARAMETER_EVIDENCE_MAP",
        "parameters": [{
            "parameter": name, "parameter_type": parameter_type,
            "current_authoritative_value": current, "current_search_values": [20, 50, 80],
            "schema_domain": {"type": parameter_type, "minimum": minimum, "maximum": maximum, "minimum_inclusive": inclusive, "maximum_inclusive": inclusive, "values": None, "allows_null": False},
            "evidence_class": evidence_class, "evidence_features": [feature] if feature else [],
            "mapping_path": "threshold -> signal", "eligible_for_range_generation": eligible,
        }],
    }


def _feature(*, direction="WINNERS_HIGHER", usable=True, semantic_type="NUMERIC", coverage=1.0):
    return {
        "feature": "signal", "data_type": semantic_type, "semantic_type": semantic_type,
        "do_not_generate_linear_min_max_range": semantic_type == "CYCLIC",
        "period": 24 if semantic_type == "CYCLIC" else None,
        "direction": direction, "usable": usable, "coverage": coverage,
        "separation_score": 0.8, "stability_score": 0.9,
        "winner_distribution": {"p10": 68.0, "p25": 72.0, "p50": 80.0, "p75": 88.0, "p90": 92.0},
        "loser_distribution": {"p10": 8.0, "p25": 12.0, "p50": 20.0, "p75": 28.0, "p90": 32.0},
    }


def _generate(mapping=None, feature=None, *, adequacy="USABLE", activity="ACTIVE", policy=None):
    resolved, provenance = _policy()
    return generate_range_artifacts(
        parameter_map=mapping or _mapping(),
        handoff={"features": [feature or _feature()]},
        activity=[{"feature": "signal", "activity_status": activity}], interactions=[],
        manifest={"symbol": "TESTUSDT", "profile": "trade-5m-v2", "final_status": "PASS", "sample_adequacy": adequacy},
        policy=policy or resolved, policy_provenance=provenance,
    )


def test_clear_numeric_separation_moves_to_winner_dense_region():
    row = _generate()["ranges"]["parameters"][0]
    assert row["evidence_direction"] == "WINNERS_HIGHER"
    assert max(row["generated_values"]) >= 88
    assert row["range_status"] == "GENERATED"


def test_reverse_numeric_separation_is_preserved():
    feature = _feature(direction="WINNERS_LOWER")
    feature["winner_distribution"], feature["loser_distribution"] = feature["loser_distribution"], feature["winner_distribution"]
    row = _generate(feature=feature)["ranges"]["parameters"][0]
    assert row["evidence_direction"] == "WINNERS_LOWER"
    assert min(row["generated_values"]) <= 12


def test_low_sample_is_provisional_and_preserves_current_without_collapse():
    row = _generate(adequacy="DESCRIPTIVE_ONLY")["ranges"]["parameters"][0]
    assert row["range_status"] == "PROVISIONAL_LOW_SAMPLE"
    assert row["range_confidence"] == "DESCRIPTIVE_ONLY"
    assert row["promotion_eligible"] is False
    assert row["current_value_included"] is True
    assert len(row["generated_values"]) >= 3


@pytest.mark.parametrize("activity", ["ALL_MISSING", "CONSTANT", "NON_CAUSAL", "UNUSABLE"])
def test_unusable_evidence_has_no_legacy_fallback(activity):
    row = _generate(activity=activity)["ranges"]["parameters"][0]
    assert row["range_status"] == "NOT_GENERATED_UNUSABLE_EVIDENCE"
    assert row["generated_values"] == []


def test_no_authorized_mapping_generates_nothing():
    row = _generate(mapping=_mapping(evidence_class="NO_AUTHORIZED_EVIDENCE_MAPPING", feature=None, eligible=False))["ranges"]["parameters"][0]
    assert row["range_status"] == "NOT_GENERATED_NO_MAPPING"
    assert row["generated_values"] == []


def test_schema_bounds_clip_all_candidates():
    row = _generate(mapping=_mapping(minimum=30, maximum=75))["ranges"]["parameters"][0]
    assert all(30 <= value <= 75 for value in row["generated_values"])


def test_integer_parameter_never_generates_fractional_candidates():
    mapping = _mapping(parameter_type="INTEGER", current=5, minimum=1, maximum=100)
    row = _generate(mapping=mapping)["ranges"]["parameters"][0]
    assert all(isinstance(value, int) for value in row["generated_values"])


def test_authorized_cyclic_fixture_preserves_wraparound_without_linear_min_max():
    feature = _feature(semantic_type="CYCLIC")
    feature["categories"] = [{"category": value, "wins": 1, "losses": 0} for value in (23, 0, 1)]
    mapping = _mapping(parameter_type="CYCLIC", current=23, minimum=0, maximum=23)
    row = _generate(mapping=mapping, feature=feature, adequacy="DESCRIPTIVE_ONLY")["ranges"]["parameters"][0]
    assert row["range_status"] == "PROVISIONAL_LOW_SAMPLE"
    assert row["generated_values"] == [23, 0, 1]
    assert row["generated_min"] is None and row["generated_max"] is None


def test_utc_hour_is_evidence_only_when_not_tunable():
    registry = [{"feature_name": "utc_hour", "data_type": "CYCLIC", "do_not_generate_linear_min_max_range": True}]
    artifact = build_parameter_evidence_map(search_space={}, feature_registry=registry)
    assert artifact["evidence_only_not_tunable"] == [{"feature": "utc_hour", "status": "EVIDENCE_ONLY_NOT_TUNABLE", "reason": "NO_CURRENT_RESEARCH_TUNABLE_PARAMETER"}]


def test_schema_invalid_current_value_fails_instead_of_altering_it():
    row = _generate(mapping=_mapping(current=150, minimum=0, maximum=100), adequacy="DESCRIPTIVE_ONLY")["ranges"]["parameters"][0]
    assert row["range_status"] == "NOT_GENERATED_SCHEMA_CONFLICT"
    assert row["generated_values"] == []


def test_boundary_pressure_is_handoff_only_without_expansion_execution():
    row = _generate()["ranges"]["parameters"][0]
    handoff = _generate()["handoff"]
    assert row["boundary_pressure"] == "BOUNDARY_PRESSURE_HIGH"
    assert row["boundary_expansion_candidate"] is True
    assert handoff["adaptive_refinement_executed"] is False


def test_same_inputs_produce_identical_logical_artifacts():
    first = json.dumps(_generate(), sort_keys=True, separators=(",", ":"))
    second = json.dumps(_generate(), sort_keys=True, separators=(",", ":"))
    assert first == second


def test_policy_authority_mutation_changes_generator_without_code_change(tmp_path: Path):
    raw = yaml.safe_load(RESEARCH_PATH.read_text(encoding="utf-8"))
    raw["data_driven_range_generation"]["max_generated_points"] = 4
    changed = tmp_path / "research_parameters.yaml"
    changed.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    policy, _ = load_data_driven_range_policy(changed)
    assert policy.max_generated_points == 4
    row = _generate(policy=policy)["ranges"]["parameters"][0]
    assert len(row["generated_values"]) <= 4


def test_missing_required_policy_key_fails_closed(tmp_path: Path):
    raw = yaml.safe_load(RESEARCH_PATH.read_text(encoding="utf-8"))
    del raw["data_driven_range_generation"]["transition_weight"]
    changed = tmp_path / "research_parameters.yaml"
    changed.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    with pytest.raises(RuntimeError, match="invalid authoritative YAML"):
        load_data_driven_range_policy(changed)
