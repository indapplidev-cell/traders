from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from app.config.yaml_authority import RESEARCH_PARAMETERS
from traders_ml.parameter_sweep.adaptive_refinement import (
    AdaptiveCampaignInputs,
    assert_resume_compatible,
    behavioral_novelty_counts,
    build_parameter_sensitivity,
    generate_candidates,
    positive_behavioral_counts,
    resolve_adaptive_budget,
    run_adaptive_refinement,
)
from traders_ml.parameter_sweep.data_driven_ranges import _schema_domain
from traders_ml.parameter_sweep.expanded_search import (
    DataDrivenRangeHandoff,
    _canonical_dataset_hash,
    _split_without_holdout,
    evaluate_config,
    run_expanded_search,
)
from traders_ml.parameter_sweep.historical_replay import build_parameter_registry
from traders_ml.parameter_sweep.symbol_authority_audit import build_symbol_runtime_authority_audit


def _dataset(*, symbol: str = "DOGEUSDT", flat: bool = False) -> list[dict[str, object]]:
    observations = [(30.0, -0.25), (40.0, 1.0), (50.0, -0.5), (10.0, -1.0), (20.0, 2.0)]
    if flat:
        observations = [(100.0, pnl) for _edge, pnl in observations]
    rows = []
    for index, (edge, pnl) in enumerate(observations):
        rows.append({
            "symbol": symbol, "profile_id": "trade-5m-v2",
            "source_type": "PERSISTED_CAUSAL_OBSERVATION", "trade_id": f"t{index}",
            "candidate_id": f"c{index}", "entry_boundary_ms": 1_700_000_000_000 + index * 86_400_000,
            "close_timestamp": f"2026-09-0{index + 1}T00:00:00+00:00",
            "net_paper_pnl": pnl, "label": "WIN" if pnl > 0 else "LOSS",
            "features": {
                "net_edge_bps": edge, "planned_rr": edge / 10,
                "stop_distance_bps": edge, "target_distance_bps": edge,
                "direction": "LONG", "setup_type": "TEST",
            },
        })
    return rows


def _handoff_payload(
    domains: dict[str, list[object]], *, symbol: str = "DOGEUSDT",
    pressure: dict[str, str] | None = None, schema_max: dict[str, float] | None = None,
) -> dict[str, object]:
    registry = {row["canonical_key"]: row for row in build_parameter_registry(RESEARCH_PARAMETERS.search_space)}
    parameters = []
    for name, values in domains.items():
        descriptor = registry[name]
        domain = _schema_domain(str(descriptor["RUNTIME_OWNER"]), descriptor["baseline"], list(descriptor["candidate_values"]))
        if schema_max and name in schema_max:
            domain["maximum"] = schema_max[name]
            domain["maximum_inclusive"] = True
        parameters.append({
            "parameter": name, "generated_values": values,
            "parameter_type": domain["type"], "schema_domain": domain,
            "range_status": "PROVISIONAL_LOW_SAMPLE", "eligible_for_search": True,
            "confidence": "DESCRIPTIVE_ONLY", "provisional": True,
            "sample_adequacy": "DESCRIPTIVE_ONLY", "promotion_eligible": False,
            "boundary_pressure": (pressure or {}).get(name, "NO_BOUNDARY_PRESSURE"),
            "provenance": {"fixture": True}, "joint_search_priority_annotations": [],
        })
    return {
        "artifact": "DATA_DRIVEN_RANGE_HANDOFF", "schema_version": 2,
        "symbol": symbol, "profile": "trade-5m-v2",
        "separability_status": "PASS_LIMITED_SAMPLE", "sample_adequacy": "DESCRIPTIVE_ONLY",
        "range_provenance": {"fixture": True}, "research_approved_only": True,
        "promotion_eligible": False, "search_executed": False,
        "adaptive_refinement_executed": False, "holdout_opened": False,
        "parameters": parameters,
    }


def _prepare_campaign(
    root: Path, *, symbol: str = "DOGEUSDT", flat: bool = False,
    pressure: dict[str, str] | None = None,
) -> dict[str, Path]:
    root.mkdir(parents=True, exist_ok=True)
    domains = {"min_net_edge_bps": [5.0, 15.0, 35.0]}
    handoff_path = root / "DATA_DRIVEN_RANGE_HANDOFF.json"
    handoff_path.write_text(json.dumps(_handoff_payload(domains, symbol=symbol, pressure=pressure), sort_keys=True), encoding="utf-8")
    rows = _dataset(symbol=symbol, flat=flat)
    dataset_path = root / "SEPARABILITY_DATASET.jsonl"
    dataset_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    manifest_path = root / "SEPARABILITY_DATASET_MANIFEST.json"
    manifest_path.write_text(json.dumps({
        "symbol": symbol, "profile": "trade-5m-v2",
        "dataset_sha256": _canonical_dataset_hash(rows),
        "source_history_start": "2026-09-01T00:00:00+00:00",
        "source_history_end": "2026-09-05T00:00:00+00:00",
        "source_history_actual_days": 4.0,
    }, sort_keys=True), encoding="utf-8")
    expanded = root / "expanded"
    run_expanded_search(
        handoff_path=handoff_path, dataset_path=dataset_path,
        dataset_manifest_path=manifest_path, output=expanded, symbol=symbol,
    )
    return {"range": handoff_path, "dataset": dataset_path, "manifest": manifest_path, "expanded": expanded}


def _run(paths: dict[str, Path], output: Path, *, symbol: str = "DOGEUSDT", resume: bool = False):
    expanded = paths["expanded"]
    return run_adaptive_refinement(
        range_handoff_path=paths["range"],
        expanded_config_path=expanded / "EXPANDED_SEARCH_CONFIG.json",
        expanded_handoff_path=expanded / "EXPANDED_SEARCH_HANDOFF.json",
        behavioral_clusters_path=expanded / "BEHAVIORAL_CLUSTERS.json",
        expanded_results_path=expanded / "EXPANDED_SEARCH_RESULTS.jsonl",
        normalization_path=expanded / "SEARCH_VALUE_NORMALIZATION.json",
        dataset_path=paths["dataset"], dataset_manifest_path=paths["manifest"],
        output=output, symbol=symbol, resume=resume,
    )


@pytest.mark.parametrize("symbol", ["DOGEUSDT", "LINKUSDT"])
def test_universal_symbol_engine_uses_same_adaptive_path(tmp_path: Path, symbol: str):
    paths = _prepare_campaign(tmp_path / symbol, symbol=symbol)
    result = _run(paths, tmp_path / f"adaptive-{symbol}", symbol=symbol)
    assert result["status"]["SYMBOL"] == symbol
    assert result["status"]["FINAL_STATUS"] == "PASS"


def test_symbol_mismatch_fails_closed(tmp_path: Path):
    paths = _prepare_campaign(tmp_path / "campaign")
    with pytest.raises(ValueError, match="SYMBOL_MISMATCH"):
        _run(paths, tmp_path / "adaptive", symbol="LINKUSDT")


def test_dataset_fingerprint_mismatch_fails_closed(tmp_path: Path):
    paths = _prepare_campaign(tmp_path / "campaign")
    with paths["dataset"].open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(_dataset()[0]) + "\n")
    with pytest.raises(ValueError, match="DATASET_FINGERPRINT_MISMATCH"):
        _run(paths, tmp_path / "adaptive")


def test_holdout_artifact_is_never_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    paths = _prepare_campaign(tmp_path / "campaign")
    holdout = paths["expanded"] / "HOLDOUT_RESULTS.jsonl"
    holdout.write_text("THIS_MUST_NOT_BE_READ", encoding="utf-8")
    reads: list[str] = []
    original_bytes, original_text = Path.read_bytes, Path.read_text

    def watched_bytes(path: Path):
        if "HOLDOUT" in path.name: reads.append(str(path))
        return original_bytes(path)

    def watched_text(path: Path, *args, **kwargs):
        if "HOLDOUT" in path.name: reads.append(str(path))
        return original_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", watched_bytes)
    monkeypatch.setattr(Path, "read_text", watched_text)
    result = _run(paths, tmp_path / "adaptive")
    assert reads == []
    assert result["status"]["HOLDOUT_READS"] == 0


def _evaluated(domains: dict[str, list[object]], *, flat: bool = False):
    handoff = DataDrivenRangeHandoff.model_validate(_handoff_payload(domains))
    splits = _split_without_holdout(_dataset(flat=flat))
    results = [evaluate_config({name: values[index] for name, values in domains.items()}, splits, index=index) for index in range(min(len(v) for v in domains.values()))]
    return handoff, results


def test_flat_interval_has_no_refinement_candidate():
    domains = {"min_net_edge_bps": [5.0, 15.0]}
    handoff, results = _evaluated(domains, flat=True)
    sensitivity = build_parameter_sensitivity(results, domains, handoff)
    candidates, _trace, _counts = generate_candidates(results=results, domains=domains, handoff=handoff, round_id=1)
    assert sensitivity["parameters"][0]["active_status"] == "BEHAVIORALLY_FLAT"
    assert candidates == []


def test_behavior_transition_generates_deterministic_interior_candidate():
    domains = {"min_net_edge_bps": [5.0, 15.0]}
    handoff, results = _evaluated(domains)
    first, _trace, _counts = generate_candidates(results=results, domains=domains, handoff=handoff, round_id=1)
    second, _trace, _counts = generate_candidates(results=results, domains=domains, handoff=handoff, round_id=1)
    assert first == second
    assert first[0]["generated_value"] == 10.0
    assert first[0]["generation_reason"] == "INTERIOR_BEHAVIORAL_TRANSITION"


def test_duplicate_consumed_candidate_is_rejected_before_evaluation(monkeypatch: pytest.MonkeyPatch):
    domains = {"min_net_edge_bps": [5.0, 10.0, 15.0]}
    handoff, results = _evaluated(domains)
    candidates, trace, counts = generate_candidates(results=results, domains=domains, handoff=handoff, round_id=1)
    assert all(row["generated_value"] != 10.0 for row in candidates)
    assert counts["duplicates"] >= 0
    assert all(row["decision"] != "EVALUATED" for row in trace)


def test_boundary_expansion_requires_pressure_positive_active_and_schema():
    domains = {"min_net_edge_bps": [5.0, 15.0]}
    payload = _handoff_payload(domains, pressure={"min_net_edge_bps": "BOUNDARY_PRESSURE_HIGH"})
    handoff = DataDrivenRangeHandoff.model_validate(payload)
    splits = _split_without_holdout(_dataset())
    results = [evaluate_config({"min_net_edge_bps": value}, splits, index=index) for index, value in enumerate(domains["min_net_edge_bps"])]
    candidates, _trace, counts = generate_candidates(results=results, domains=domains, handoff=handoff, round_id=1)
    boundary = [row for row in candidates if "BOUNDARY" in row["generation_reason"]]
    assert len(boundary) == 1
    assert boundary[0]["generated_value"] == 25.0
    assert counts["boundary_generated"] == 1


def test_boundary_expansion_blocked_by_schema():
    domains = {"min_net_edge_bps": [5.0, 15.0]}
    payload = _handoff_payload(domains, pressure={"min_net_edge_bps": "BOUNDARY_PRESSURE_HIGH"}, schema_max={"min_net_edge_bps": 15.0})
    handoff = DataDrivenRangeHandoff.model_validate(payload)
    splits = _split_without_holdout(_dataset())
    results = [evaluate_config({"min_net_edge_bps": value}, splits, index=index) for index, value in enumerate(domains["min_net_edge_bps"])]
    candidates, trace, counts = generate_candidates(results=results, domains=domains, handoff=handoff, round_id=1)
    assert not [row for row in candidates if "BOUNDARY" in row["generation_reason"]]
    assert any(row["decision"] == "BOUNDARY_BLOCKED_BY_SCHEMA" for row in trace)
    assert counts["schema_blocked"] == 1


def test_no_boundary_pressure_means_no_expansion():
    domains = {"min_net_edge_bps": [5.0, 15.0]}
    handoff, results = _evaluated(domains)
    candidates, _trace, counts = generate_candidates(results=results, domains=domains, handoff=handoff, round_id=1)
    assert not [row for row in candidates if "BOUNDARY" in row["generation_reason"]]
    assert counts["boundary_generated"] == 0


def test_adaptive_budget_is_resolved_from_canonical_policy():
    budget, authority = resolve_adaptive_budget(10)
    assert budget <= RESEARCH_PARAMETERS.search.max_evaluated_configs
    assert budget <= RESEARCH_PARAMETERS.search.max_total_configs
    assert authority and all("research_parameters.yaml" in item for item in authority)


def test_byte_determinism_resume_and_required_artifacts(tmp_path: Path):
    paths = _prepare_campaign(tmp_path / "campaign")
    out_a, out_b = tmp_path / "a", tmp_path / "b"
    first = _run(paths, out_a)
    second = _run(paths, out_b)
    required = {
        "ADAPTIVE_REFINEMENT_CONFIG.json", "BEHAVIORAL_TRANSITION_GRAPH.json",
        "ADAPTIVE_PARAMETER_SENSITIVITY.json", "ADAPTIVE_CANDIDATE_TRACE.jsonl",
        "ADAPTIVE_ROUNDS.jsonl", "ADAPTIVE_RESULTS.jsonl",
        "ADAPTIVE_BEHAVIORAL_CLUSTERS.json", "ADAPTIVE_REFINEMENT_HANDOFF.json",
        "STATUS.json", "REPORT.md",
    }
    assert required <= {path.name for path in out_a.iterdir()}
    assert {name: (out_a / name).read_bytes() for name in required} == {name: (out_b / name).read_bytes() for name in required}
    before = {path.name: path.read_bytes() for path in out_a.iterdir()}
    resumed = _run(paths, out_a, resume=True)
    assert before == {path.name: path.read_bytes() for path in out_a.iterdir()}
    assert first["status"] == second["status"] == resumed["status"]


def test_resume_guard_mismatch_fails_closed():
    base = {
        "symbol": "DOGEUSDT", "profile": "trade-5m-v2",
        "dataset_fingerprint": "a" * 64, "calibration_split_fingerprint": "b" * 64,
        "validation_split_fingerprint": "c" * 64, "parameter_registry_version": "d" * 64,
        "range_handoff_fingerprint": "e" * 64, "expanded_search_fingerprint": "f" * 64,
        "adaptive_policy_fingerprint": "1" * 64, "seed": 1,
    }
    expected = AdaptiveCampaignInputs.model_validate(base)
    changed = deepcopy(base); changed["dataset_fingerprint"] = "9" * 64
    checkpoint = {
        "artifact": "ADAPTIVE_REFINEMENT_CHECKPOINT", "schema_version": 1,
        "inputs": changed, "evaluated_candidate_keys": [], "completed_rounds": 0,
        "cumulative_evaluations": 0, "completed": False, "stop_reason": None,
        "holdout_opened": False,
    }
    with pytest.raises(ValueError, match="RESUME_DATASET_FINGERPRINT_MISMATCH"):
        assert_resume_compatible(checkpoint, expected)


def test_behavioral_and_positive_duplicates_are_counted_by_signature():
    initial = [{"behavioral_signature": "A", "net_pnl": -1.0}]
    new = [
        {"behavioral_signature": "B", "net_pnl": 1.0},
        {"behavioral_signature": "B", "net_pnl": 2.0},
    ]
    assert behavioral_novelty_counts(initial, new) == {
        "NEW_NUMERIC_CONFIGS": 2, "NEW_BEHAVIORAL_CLUSTERS": 1,
        "BEHAVIORAL_DUPLICATES": 1,
    }
    assert positive_behavioral_counts(new) == {
        "POSITIVE_NUMERIC_CONFIGS": 2, "POSITIVE_BEHAVIORAL_CLUSTERS": 1,
        "POSITIVE_BEHAVIORAL_DUPLICATES": 1,
    }


def test_no_holdout_finalist_promotion_or_production_mutation(tmp_path: Path):
    paths = _prepare_campaign(tmp_path / "campaign")
    output = tmp_path / "adaptive"
    status = _run(paths, output)["status"]
    assert status["HOLDOUT_OPENED"] is False
    assert status["FINALIST_FREEZE_EXECUTED"] is False
    assert status["PROMOTION_ELIGIBLE"] is False
    assert status["ADAPTIVE_RESULT_CERTIFIED"] is False
    assert status["LIVE_STATE"] is False
    assert status["BINANCE_ORDER_CALLS"] == status["PRODUCTION_MUTATIONS"] == 0
    assert not list(output.glob("*HOLDOUT*"))
    assert not list(output.glob("*FINALIST*"))


def test_runtime_symbol_literal_forensic_remains_zero():
    audit = build_symbol_runtime_authority_audit()
    assert audit["RUNTIME_SYMBOL_HARDCODES"] == 0
    assert audit["RUNTIME_SYMBOL_DEFAULTS"] == 0
    assert audit["RUNTIME_SYMBOL_BRANCHES"] == 0
