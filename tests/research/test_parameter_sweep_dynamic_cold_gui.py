from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import pytest

from app.config.yaml_authority import RESEARCH_PARAMETERS
from traders_ml.parameter_sweep.cold_start import run_cold_start_range_generation
from traders_ml.parameter_sweep.controller import ParameterSweepController
from traders_ml.parameter_sweep.data_driven_ranges import _schema_domain
from traders_ml.parameter_sweep.expanded_search import (
    DataDrivenRangeHandoff, _canonical_dataset_hash, normalize_handoff_values,
    run_expanded_search, validate_handoff,
)
from traders_ml.parameter_sweep.historical_replay import build_parameter_registry


def _handoff(domains: dict[str, list[object]], *, symbol: str = "BNBUSDT") -> dict[str, object]:
    registry = {row["canonical_key"]: row for row in build_parameter_registry(RESEARCH_PARAMETERS.search_space)}
    parameters = []
    for name, values in domains.items():
        descriptor = registry[name]
        domain = _schema_domain(str(descriptor["RUNTIME_OWNER"]), descriptor["baseline"], list(descriptor["candidate_values"]))
        parameters.append({
            "parameter": name, "generated_values": values,
            "parameter_type": domain["type"], "schema_domain": domain,
            "range_status": "PROVISIONAL_LOW_SAMPLE", "eligible_for_search": True,
            "confidence": "DESCRIPTIVE_ONLY", "provisional": True,
            "sample_adequacy": "DESCRIPTIVE_ONLY", "promotion_eligible": False,
            "boundary_pressure": "NONE", "provenance": {"source": "TEST"},
            "joint_search_priority_annotations": [],
        })
    return {
        "artifact": "DATA_DRIVEN_RANGE_HANDOFF", "schema_version": 2,
        "symbol": symbol, "profile": "trade-5m-v2", "separability_status": "PASS_LIMITED_SAMPLE",
        "sample_adequacy": "DESCRIPTIVE_ONLY", "range_provenance": {"source": "TEST"},
        "research_approved_only": True, "promotion_eligible": False, "search_executed": False,
        "adaptive_refinement_executed": False, "holdout_opened": False, "parameters": parameters,
    }


def test_dynamic_dimension_order_and_five_dimension_strategy_score_are_canonical():
    domains = {
        "target_min_bps": [45.0, 55.0], "strategy_minimum_score": [55.0, 75.0],
        "minimum_planned_rr": [0.2, 0.4], "stop_max_bps": [50.0, 60.0],
        "min_net_edge_bps": [1.0, 5.0],
    }
    left = DataDrivenRangeHandoff.model_validate(_handoff(domains))
    right = DataDrivenRangeHandoff.model_validate(_handoff(dict(reversed(list(domains.items())))))
    left_space, left_meta = normalize_handoff_values(left)
    right_space, right_meta = normalize_handoff_values(right)
    assert list(left_space) == sorted(domains)
    assert left_space == right_space
    assert left_meta == right_meta
    assert len(left_space) == 5
    assert "strategy_minimum_score" in left_space


def test_one_dimension_is_generic_and_invalid_typed_value_fails_closed():
    one = DataDrivenRangeHandoff.model_validate(_handoff({"min_net_edge_bps": [1.0, 5.0]}))
    space, metadata = normalize_handoff_values(one)
    assert space == {"min_net_edge_bps": [1.0, 5.0]}
    assert len(metadata["parameters"]) == 1

    invalid = _handoff({"min_net_edge_bps": ["not-a-number"]})
    with pytest.raises((ValueError, TypeError), match="INVALID|valid|number"):
        normalize_handoff_values(DataDrivenRangeHandoff.model_validate(invalid))


def test_unauthorized_and_missing_consumer_fail_closed(tmp_path: Path):
    unknown = _handoff({"min_net_edge_bps": [1.0]})
    unknown["parameters"][0]["parameter"] = "unknown_parameter"
    path = tmp_path / "unknown.json"
    path.write_text(json.dumps(unknown), encoding="utf-8")
    with pytest.raises(ValueError, match="UNAUTHORIZED_SEARCH_PARAMETER"):
        validate_handoff(path, symbol="BNBUSDT", profile="trade-5m-v2")

    missing = _handoff({"risk_per_trade_bps": [5.0, 10.0]})
    path.write_text(json.dumps(missing), encoding="utf-8")
    with pytest.raises(ValueError, match="MISSING_SEARCH_CONSUMER"):
        validate_handoff(path, symbol="BNBUSDT", profile="trade-5m-v2")


def _opportunity(index: int, *, symbol: str = "BTCUSDT") -> dict[str, object]:
    entry = 100.0
    return {
        "candidate_id": f"c{index}", "causal_identity": f"{symbol}:{index}:LONG", "run_id": f"r{index}",
        "symbol": symbol, "profile_id": "trade-5m-v2", "boundary_ms": 1_700_000_000_000 + index * 86_400_000,
        "direction": "LONG", "setup_type": "TEST", "setup_status": "SETUP_CANDIDATE",
        "historical_rejection_reason": "REJECT_TEST", "entry_price": entry, "stop_price": 99.5,
        "target_price": 101.0, "stop_distance_bps": 40.0 + index,
        "target_distance_bps": 70.0 + index, "net_rr": 0.2 + index * 0.03,
        "net_edge_bps": 1.0 + index, "strategy_score": 50.0 + index * 4,
        "effective_total_cost_bps": 5.0, "adverse_fill_reserve_bps": 1.0,
        "entry_slippage_bps": 1.0, "probability_sample_size": 30, "p_win_raw": 0.55,
        "expected_ev_r": 0.05, "ev_reserve": 0.05, "risk_score": 1.0,
        "causal_reset_conditions": 1, "one_min_confirmation_count": 1,
        "cost_provenance": "TEST", "market_path_1m": [{
            "open_time_ms": 1_700_000_000_000 + index * 86_400_000,
            "close_time_ms": 1_700_000_060_000 + index * 86_400_000,
            "open": entry, "high": 101.2, "low": 99.8, "close": 101.0,
        }],
    }


@dataclass
class _Dataset:
    rows: list[dict[str, object]]
    summary: dict[str, object]
    capabilities: dict[str, object]
    baseline_positions: list[dict[str, object]]
    inventory: list[dict[str, object]]
    fingerprint: str


class _Repository:
    rows: list[dict[str, object]] = []
    def __init__(self, _database): pass
    def load(self, **_kwargs):
        return _Dataset(list(self.rows), {}, {}, [], [], "f" * 64)
    def load_paths(self, rows, **_kwargs): return None


def test_zero_trade_cold_start_builds_five_dimensions_and_counterfactual_search(monkeypatch, tmp_path: Path):
    import traders_ml.parameter_sweep.cold_start as module
    _Repository.rows = [_opportunity(index) for index in range(10)]
    monkeypatch.setattr(module, "HistoricalReplayRepository", _Repository)
    result = run_cold_start_range_generation(
        database=object(), symbol="BTCUSDT", output=tmp_path / "ranges", production_closed_trades=0,
    )
    assert result["status"] == "COLD_START_OPPORTUNITY"
    assert result["opportunity_rows"] == 10
    assert result["generated_dimensions"] == 5
    assert {row["parameter"] for row in result["handoff"]["parameters"]} == {
        "strategy_minimum_score", "min_net_edge_bps", "minimum_planned_rr", "stop_max_bps", "target_min_bps",
    }
    assert all(row["provenance"]["value_provenance"] for row in result["handoff"]["parameters"])
    expanded = run_expanded_search(
        handoff_path=tmp_path / "ranges" / "DATA_DRIVEN_RANGE_HANDOFF.json",
        dataset_path=result["dataset_path"], dataset_manifest_path=result["dataset_manifest_path"],
        output=tmp_path / "expanded", symbol="BTCUSDT",
    )
    assert expanded["status"]["SEARCH_SOURCE"] == "COLD_START_OPPORTUNITY_RANGE_HANDOFF"
    assert expanded["status"]["EVALUATED_CONFIGS"] > 0
    manifest = json.loads((tmp_path / "expanded" / "COUNTERFACTUAL_BOOTSTRAP_MANIFEST.json").read_text())
    assert manifest["production_accounting_mutations"] == 0
    assert manifest["trade_count_primary_objective"] is False


def test_no_closed_and_no_opportunities_has_canonical_stop(monkeypatch, tmp_path: Path):
    import traders_ml.parameter_sweep.cold_start as module
    _Repository.rows = []
    monkeypatch.setattr(module, "HistoricalReplayRepository", _Repository)
    result = run_cold_start_range_generation(
        database=object(), symbol="XRPUSDT", output=tmp_path, production_closed_trades=0,
    )
    assert result == {
        "status": "NO_USABLE_EVIDENCE", "reason": "STOPPED_NO_USABLE_RESEARCH_EVIDENCE",
        "opportunity_rows": 0,
    }


def test_cold_start_future_leakage_and_cross_symbol_rows_fail_closed(monkeypatch, tmp_path: Path):
    import traders_ml.parameter_sweep.cold_start as module
    monkeypatch.setattr(module, "HistoricalReplayRepository", _Repository)
    leaked = _opportunity(1)
    leaked["future_fields_read_for_range_generation"] = 1
    _Repository.rows = [leaked, _opportunity(2), _opportunity(3)]
    with pytest.raises(ValueError, match="FUTURE_LEAKAGE"):
        run_cold_start_range_generation(
            database=object(), symbol="BTCUSDT", output=tmp_path / "leaked",
            production_closed_trades=0,
        )
    _Repository.rows = [_opportunity(index, symbol="ETHUSDT") for index in range(3)]
    with pytest.raises(ValueError, match="CROSS_SYMBOL"):
        run_cold_start_range_generation(
            database=object(), symbol="BTCUSDT", output=tmp_path / "cross",
            production_closed_trades=0,
        )


def test_progress_projection_is_sequenced_and_old_events_cannot_overwrite_terminal(tmp_path: Path):
    controller = ParameterSweepController(tmp_path / "config.yaml", tmp_path / "runs")
    controller._apply_pipeline_progress({
        "progress_sequence": 2, "phase": "EXPANDED_AUTOMATIC_SEARCH", "event_type": "CONFIG_STARTED",
        "config_index": 3, "planned_total": 10, "parameters": {"strategy_minimum_score": 75.0},
    })
    assert controller.state.current_index == 3
    controller._apply_pipeline_progress({
        "progress_sequence": 1, "phase": "EXPANDED_AUTOMATIC_SEARCH", "event_type": "CONFIG_STARTED",
        "config_index": 1, "planned_total": 10, "parameters": {"strategy_minimum_score": 55.0},
    })
    assert controller.state.current_index == 3


def test_completed_terminal_hydration_reconciles_counts_artifacts_and_integrity(tmp_path: Path):
    root = tmp_path / "runs" / "complete"
    for folder in ("02_data_driven_ranges", "03_expanded_search", "04_adaptive_refinement", "05_validation_ranking", "06_finalist_freeze"):
        (root / folder).mkdir(parents=True)
    handoff = _handoff({"min_net_edge_bps": [1.0, 5.0]}, symbol="LINKUSDT")
    (root / "02_data_driven_ranges" / "DATA_DRIVEN_RANGE_HANDOFF.json").write_text(json.dumps(handoff))
    results = [
        {"config_index": index, "parameters": {"min_net_edge_bps": float(index)}, "evaluation_status": "ACCEPTED",
         "performance_class": "INSUFFICIENT_SAMPLE", "behavioral_signature": f"s{index}"}
        for index in range(10)
    ]
    (root / "03_expanded_search" / "EXPANDED_SEARCH_RESULTS.jsonl").write_text("".join(json.dumps(row)+"\n" for row in results))
    (root / "03_expanded_search" / "STATUS.json").write_text(json.dumps({"PLANNED_CONFIGS": 10, "EVALUATED_CONFIGS": 10, "BEHAVIORALLY_DISTINCT_CONFIGS": 10, "BEHAVIORAL_DUPLICATE_CONFIGS": 0}))
    (root / "04_adaptive_refinement" / "STATUS.json").write_text(json.dumps({"NEW_NUMERIC_CONFIGS_EVALUATED": 2, "ADAPTIVE_ROUNDS": 1, "NEW_BEHAVIORAL_CLUSTERS_DISCOVERED": 1}))
    (root / "05_validation_ranking" / "STATUS.json").write_text(json.dumps({"TOTAL_NUMERIC_CONFIGS": 12, "TOTAL_BEHAVIORAL_CLUSTERS": 11, "ELIGIBLE_NUMERIC_CONFIGS": 0, "ELIGIBLE_BEHAVIORAL_CLUSTERS": 0}))
    (root / "06_finalist_freeze" / "FINALIST_FREEZE.json").write_text(json.dumps({"requested_finalist_count": 5, "selected_finalist_count": 0, "selection_reason": "ZERO_ELIGIBLE"}))
    (root / "06_finalist_freeze" / "FINALIST_FREEZE_INTEGRITY.json").write_text(json.dumps({"integrity_status": "PASS"}))
    controller = ParameterSweepController(tmp_path / "config.yaml", tmp_path / "runs")
    controller._hydrate_pipeline_artifacts(root)
    assert (controller.state.planned, controller.state.completed) == (10, 10)
    assert controller.state.total_research_evaluated == 12
    assert controller.state.artifact_bytes > 0
    assert controller.state.integrity_status == "PASS"
    assert len(controller.state.search_dimensions) == 1


def test_expanded_stop_after_current_and_resume_preserve_progress(monkeypatch, tmp_path: Path):
    import traders_ml.parameter_sweep.cold_start as module
    _Repository.rows = [_opportunity(index) for index in range(10)]
    monkeypatch.setattr(module, "HistoricalReplayRepository", _Repository)
    cold = run_cold_start_range_generation(
        database=object(), symbol="BTCUSDT", output=tmp_path / "ranges",
        production_closed_trades=0,
    )
    completed = 0

    def progress(event):
        nonlocal completed
        if event.get("event_type") == "CONFIG_COMPLETED":
            completed += 1

    output = tmp_path / "expanded"
    stopped = run_expanded_search(
        handoff_path=tmp_path / "ranges" / "DATA_DRIVEN_RANGE_HANDOFF.json",
        dataset_path=cold["dataset_path"], dataset_manifest_path=cold["dataset_manifest_path"],
        output=output, symbol="BTCUSDT", progress=progress,
        should_stop=lambda: completed >= 3,
    )
    assert stopped["stopped"] is True
    assert stopped["status"]["EVALUATED_CONFIGS"] == 3
    checkpoint = json.loads((output / "CHECKPOINT.json").read_text())
    assert checkpoint["evaluated_configs"] == 3
    assert checkpoint["completed"] is False

    resumed = run_expanded_search(
        handoff_path=tmp_path / "ranges" / "DATA_DRIVEN_RANGE_HANDOFF.json",
        dataset_path=cold["dataset_path"], dataset_manifest_path=cold["dataset_manifest_path"],
        output=output, symbol="BTCUSDT", resume=True,
    )
    assert resumed["stopped"] is False
    assert resumed["status"]["EVALUATED_CONFIGS"] == resumed["status"]["PLANNED_CONFIGS"]
    rows = [json.loads(line) for line in (output / "EXPANDED_SEARCH_RESULTS.jsonl").read_text().splitlines()]
    assert len(rows) == len({row["config_id"] for row in rows})
