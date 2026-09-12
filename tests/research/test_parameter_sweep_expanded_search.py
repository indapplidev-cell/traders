from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from app.config.yaml_authority import RESEARCH_PARAMETERS
from traders_ml.parameter_sweep.data_driven_ranges import _schema_domain
from traders_ml.parameter_sweep.expanded_search import (
    DataDrivenRangeHandoff, assert_resume_compatible, build_plan,
    build_reporting_reconciliation,
    cluster_results, iter_planned_configs, normalize_handoff_values,
    run_expanded_search, validate_dataset, validate_handoff,
)
from traders_ml.parameter_sweep.historical_replay import build_parameter_registry
from traders_ml.parameter_sweep.symbol_authority_audit import build_symbol_runtime_authority_audit


def _handoff_payload(domains: dict[str, list[object]], *, symbol: str = "DOGEUSDT") -> dict[str, object]:
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
            "boundary_pressure": "NO_BOUNDARY_PRESSURE", "provenance": {"test": True},
            "joint_search_priority_annotations": [],
        })
    return {
        "artifact": "DATA_DRIVEN_RANGE_HANDOFF", "schema_version": 2,
        "symbol": symbol, "profile": "trade-5m-v2",
        "separability_status": "PASS_LIMITED_SAMPLE", "sample_adequacy": "DESCRIPTIVE_ONLY",
        "range_provenance": {"test": True}, "research_approved_only": True,
        "promotion_eligible": False, "search_executed": False,
        "adaptive_refinement_executed": False, "holdout_opened": False,
        "parameters": parameters,
    }


def _dataset(*, symbol: str = "DOGEUSDT") -> list[dict[str, object]]:
    rows = []
    for index, pnl in enumerate((-1.0, 2.0, -0.5, 1.0, -0.25)):
        rows.append({
            "symbol": symbol, "profile_id": "trade-5m-v2",
            "source_type": "PERSISTED_CAUSAL_OBSERVATION", "trade_id": f"t{index}",
            "candidate_id": f"c{index}", "entry_boundary_ms": 1_700_000_000_000 + index * 86_400_000,
            "close_timestamp": "2026-09-05T00:00:00+00:00", "net_paper_pnl": pnl,
            "label": "WIN" if pnl > 0 else "LOSS",
            "features": {"net_edge_bps": 50.0, "planned_rr": 2.0, "stop_distance_bps": 30.0, "target_distance_bps": 80.0, "direction": "LONG", "setup_type": "TEST"},
        })
    return rows


def test_handoff_only_authority_ignores_legacy_arrays():
    handoff = DataDrivenRangeHandoff.model_validate(_handoff_payload({"min_net_edge_bps": [11.0, 22.0]}))
    space, _ = normalize_handoff_values(handoff)
    assert space == {"min_net_edge_bps": [11.0, 22.0]}
    assert space["min_net_edge_bps"] != RESEARCH_PARAMETERS.search_space["min_net_edge_bps"]


def test_missing_handoff_parameter_is_excluded_without_legacy_fallback():
    handoff = DataDrivenRangeHandoff.model_validate(_handoff_payload({"target_min_bps": [50.0, 60.0]}))
    space, _ = normalize_handoff_values(handoff)
    assert set(space) == {"target_min_bps"}


def test_raw_cartesian_count_2_by_3_by_4_is_24():
    plan = build_plan({"a": [1, 2], "b": [1, 2, 3], "c": [1, 2, 3, 4]}, dataset_rows=100)
    assert plan.raw_search_space_size == 24
    assert plan.evaluation_budget == 24


def test_bounded_sampling_is_deterministic_and_frozen():
    space = {"a": list(range(30)), "b": list(range(30))}
    plan1 = build_plan(space, dataset_rows=10)
    before = list(iter_planned_configs(space, plan1))
    plan2 = build_plan(space, dataset_rows=10)
    assert before == list(iter_planned_configs(space, plan2))
    assert len(before) == plan1.evaluation_budget < 900


def test_precision_deduplicates_same_consumed_float_but_preserves_distinction():
    handoff = DataDrivenRangeHandoff.model_validate(_handoff_payload({"min_net_edge_bps": [1, 1.0, 1.0000001]}))
    space, evidence = normalize_handoff_values(handoff)
    assert space["min_net_edge_bps"] == [1.0, 1.0000001]
    assert evidence["parameters"][0]["duplicates_removed"] == 1


def test_single_symbol_and_reconstructed_sources_fail_closed():
    rows = _dataset()
    assert validate_dataset(rows, symbol="DOGEUSDT", profile="trade-5m-v2") == {"cross_symbol_rows": 0, "reconstructed_rows_used": 0}
    contaminated = deepcopy(rows); contaminated[0]["symbol"] = "BTCUSDT"
    with pytest.raises(ValueError, match="CROSS_SYMBOL"):
        validate_dataset(contaminated, symbol="DOGEUSDT", profile="trade-5m-v2")
    reconstructed = deepcopy(rows); reconstructed[0]["source_type"] = "RECONSTRUCTED"
    with pytest.raises(ValueError, match="RECONSTRUCTED"):
        validate_dataset(reconstructed, symbol="DOGEUSDT", profile="trade-5m-v2")


def test_behavioral_duplicate_configs_cluster_without_losing_raw_rows():
    domains = {"min_net_edge_bps": [1.0, 2.0]}
    handoff = DataDrivenRangeHandoff.model_validate(_handoff_payload(domains))
    space, _ = normalize_handoff_values(handoff)
    from traders_ml.parameter_sweep.expanded_search import _run_rows
    _plan, raw, representatives, clusters = _run_rows(space, _dataset())
    assert len(raw) == 2
    assert len(representatives) == 1
    assert clusters[0]["equivalence_count"] == 2


@pytest.mark.parametrize("field", ["symbol", "dataset_fingerprint", "range_handoff_fingerprint"])
def test_resume_mismatch_fails_closed(field):
    expected = {key: "same" for key in ("symbol", "profile", "dataset_fingerprint", "range_handoff_fingerprint", "search_space_fingerprint", "seed")}
    checkpoint = dict(expected); checkpoint[field] = "different"
    with pytest.raises(ValueError, match="RESUME_"):
        assert_resume_compatible(checkpoint, expected)


def test_end_to_end_creates_only_frozen_existing_values_and_never_holdout(tmp_path: Path):
    payload = _handoff_payload({"min_net_edge_bps": [1.0, 60.0], "target_min_bps": [50.0, 100.0]})
    handoff_path = tmp_path / "DATA_DRIVEN_RANGE_HANDOFF.json"
    handoff_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    rows = _dataset()
    dataset_path = tmp_path / "SEPARABILITY_DATASET.jsonl"
    dataset_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    from traders_ml.parameter_sweep.expanded_search import _canonical_dataset_hash
    manifest = {
        "symbol": "DOGEUSDT", "profile": "trade-5m-v2",
        "dataset_sha256": _canonical_dataset_hash(rows),
        "source_history_start": "2026-09-01T00:00:00+00:00",
        "source_history_end": "2026-09-05T00:00:00+00:00", "source_history_actual_days": 4.0,
    }
    manifest_path = tmp_path / "SEPARABILITY_DATASET_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    output = tmp_path / "out"
    result = run_expanded_search(
        handoff_path=handoff_path, dataset_path=dataset_path,
        dataset_manifest_path=manifest_path, output=output,
        symbol="DOGEUSDT",
    )
    assert result["status"]["HOLDOUT_OPENED"] is False
    assert result["status"]["ADAPTIVE_REFINEMENT_EXECUTED"] is False
    assert result["status"]["HANDOFF_FALLBACKS_TO_LEGACY"] == 0
    allowed = {name: set(values) for name, values in {"min_net_edge_bps": [1.0, 60.0], "target_min_bps": [50.0, 100.0]}.items()}
    for line in (output / "EXPANDED_SEARCH_RESULTS.jsonl").read_text(encoding="utf-8").splitlines():
        for name, value in json.loads(line)["parameters"].items():
            assert value in allowed[name]
    assert not (output / "HOLDOUT_RESULTS.jsonl").exists()
    assert (output / "EXPANDED_SEARCH_HANDOFF.json").is_file()
    first = {path.name: path.read_bytes() for path in output.iterdir() if path.is_file()}
    run_expanded_search(
        handoff_path=handoff_path, dataset_path=dataset_path,
        dataset_manifest_path=manifest_path, output=output,
        symbol="DOGEUSDT", resume=True,
    )
    assert first == {path.name: path.read_bytes() for path in output.iterdir() if path.is_file()}
    assert result["status"]["BINANCE_ORDER_CALLS"] == 0
    assert result["status"]["PRODUCTION_MUTATIONS"] == 0


def test_handoff_provenance_and_schema_mismatch_fail_closed(tmp_path: Path):
    payload = _handoff_payload({"min_net_edge_bps": [1.0]})
    path = tmp_path / "handoff.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    validate_handoff(path, symbol="DOGEUSDT", profile="trade-5m-v2")
    with pytest.raises(ValueError, match="SYMBOL"):
        validate_handoff(path, symbol="BTCUSDT", profile="trade-5m-v2")
    payload["parameters"][0]["schema_domain"]["minimum"] = 999
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="SCHEMA"):
        validate_handoff(path, symbol="DOGEUSDT", profile="trade-5m-v2")


def _compact_row(
    config_id: str, *, net_pnl: float, pf: float | None,
    signature: str, parameters: dict[str, object],
) -> dict[str, object]:
    return {
        "config_id": config_id, "parameters": parameters,
        "evaluation_status": "ACCEPTED", "performance_class": "INSUFFICIENT_SAMPLE",
        "expectancy_R": None, "profit_factor": pf, "max_drawdown": 0.0,
        "trade_count": 1, "symbol_coverage": 1, "rank_stability": 0.0,
        "net_pnl": net_pnl, "wins": int(net_pnl > 0), "losses": int(net_pnl < 0),
        "neutrals": 0, "independent_period_count": 1,
        "behavioral_signature": signature,
        "insufficient_sample_gates": [{"gate": "validation_trade_count"}],
    }


def test_canonical_best_and_metric_best_are_reported_separately():
    canonical = _compact_row("canonical", net_pnl=-0.1, pf=1.5, signature="negative", parameters={"x": 1})
    positive_a = _compact_row("positive-a", net_pnl=2.0, pf=None, signature="positive", parameters={"x": 2})
    positive_b = _compact_row("positive-b", net_pnl=2.0, pf=None, signature="positive", parameters={"x": 3})
    summary, artifact = build_reporting_reconciliation(
        [canonical, positive_a, positive_b], [canonical, positive_b],
    )
    assert summary["BEST_CANONICAL_RANKED_CONFIG"]["config_id"] == "canonical"
    assert summary["BEST_NET_PNL_CONFIG"]["config_id"] == "positive-b"
    assert summary["BEST_EXPECTANCY_CONFIG"] is None
    assert summary["BEST_PROFIT_FACTOR_CONFIG"]["config_id"] == "canonical"
    assert summary["POSITIVE_NUMERIC_CONFIGS"] == 2
    assert summary["POSITIVE_BEHAVIORAL_CLUSTERS"] == 1
    assert summary["POSITIVE_BEHAVIORAL_DUPLICATES"] == 1
    assert len(artifact["configs"]) == 2


@pytest.mark.parametrize("symbol", ["DOGEUSDT", "LINKUSDT"])
def test_same_expanded_engine_accepts_different_valid_symbol_fixtures(tmp_path: Path, symbol: str):
    handoff_path = tmp_path / f"{symbol}-handoff.json"
    handoff_path.write_text(json.dumps(_handoff_payload({"min_net_edge_bps": [1.0]}, symbol=symbol)), encoding="utf-8")
    dataset_path = tmp_path / f"{symbol}-dataset.jsonl"
    rows = _dataset(symbol=symbol)
    dataset_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    from traders_ml.parameter_sweep.expanded_search import _canonical_dataset_hash
    manifest_path = tmp_path / f"{symbol}-manifest.json"
    manifest_path.write_text(json.dumps({
        "symbol": symbol, "profile": "trade-5m-v2",
        "dataset_sha256": _canonical_dataset_hash(rows),
        "source_history_start": "2026-09-01T00:00:00+00:00",
        "source_history_end": "2026-09-05T00:00:00+00:00",
        "source_history_actual_days": 4.0,
    }), encoding="utf-8")
    result = run_expanded_search(
        handoff_path=handoff_path, dataset_path=dataset_path,
        dataset_manifest_path=manifest_path, output=tmp_path / f"out-{symbol}",
        symbol=symbol,
    )
    assert result["status"]["SYMBOL"] == symbol


def test_handoff_symbol_mismatch_and_missing_symbol_fail_closed(tmp_path: Path):
    path = tmp_path / "handoff.json"
    path.write_text(json.dumps(_handoff_payload({"min_net_edge_bps": [1.0]})), encoding="utf-8")
    with pytest.raises(ValueError, match="HANDOFF_SYMBOL_MISMATCH"):
        validate_handoff(path, symbol="LINKUSDT", profile="trade-5m-v2")
    for missing in (None, ""):
        with pytest.raises(ValueError, match="SYMBOL_REQUIRED"):
            validate_handoff(path, symbol=missing, profile="trade-5m-v2")


def test_runtime_symbol_literal_forensic_is_zero():
    audit = build_symbol_runtime_authority_audit()
    assert audit["RUNTIME_SYMBOL_HARDCODES"] == 0
    assert audit["RUNTIME_SYMBOL_DEFAULTS"] == 0
    assert audit["RUNTIME_SYMBOL_BRANCHES"] == 0
    assert audit["symbol_binding_status"] == "PASS"
