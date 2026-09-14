"""Historical fixtures are reduced to causal inputs; no database/network needed."""
import copy
import json
from dataclasses import fields
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from traders_ml.parameter_sweep.history_applicability import (
    HistoricalCostSource, assess_boundary, assess_dataset, baseline_parity,
)
from traders_ml.parameter_sweep.result_search import fingerprint

FIXTURES = Path(__file__).parent / "fixtures/result_search_applicability.json"


@pytest.fixture
def rows(monkeypatch):
    from app.engine_paper.scalping_paper_runner import BinancePublicScalpingCostSource
    def forbidden(*args, **kwargs):
        raise AssertionError("Live cost source must never be constructed")
    monkeypatch.setattr(BinancePublicScalpingCostSource, "__init__", forbidden)
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


def test_authoritative_baseline_parity_without_live_calls(rows):
    for row in rows.values():
        replay = assess_boundary(row, {})
        assert replay["state"] == "VERIFIED_REJECTION"
        assert baseline_parity(row, replay)


def test_no_setup_does_not_need_cost_and_upstream_change_is_not_silently_supported(rows):
    row = rows["early"]
    row["geometry"] = None
    assert assess_boundary(row, {})["cost_requirement"] == "NOT_REQUIRED"
    x = assess_boundary(row, {"signal.strategy_minimum_score": 50})
    assert x["state"] == "BLOCKED"
    assert x["reason"] == "UPSTREAM_OR_UNSUPPORTED_PARAMETER_REQUIRES_RECOMPUTATION"


def test_same_snapshot_without_raw_depth_is_reusable(rows):
    row = rows["cost"]
    assert "bids" not in row["geometry"]
    x = assess_boundary(row, {"economics.min_net_edge_bps": 80})
    assert x["state"] == "VERIFIED_REJECTION"
    assert x["cost_requirement"] == "VERIFIED_SAME_INPUT_SNAPSHOT"


def test_relaxing_stop_exposes_required_missing_cost(rows):
    row = rows["wide"]
    assert assess_boundary(row, {})["cost_requirement"] == "NOT_REQUIRED"
    x = assess_boundary(row, {"geometry.stop_max_bps": 10000})
    assert x["cost_requirement"] == "REQUIRED"
    assert x["state"] == "BLOCKED" and x["reason"] == "MISSING_REQUIRED_COST_SNAPSHOT"


@pytest.mark.parametrize("field,value,reason", [
    ("reference_quantity", 999999, "QUANTITY_CHANGED"),
    ("entry", 999999, "ENTRY_CHANGED"),
    ("symbol", "BTCUSDT", "SYMBOL_OR_BOUNDARY"),
    ("commission_authoritative", False, "UNVERIFIED_COST_PROVENANCE"),
    ("economic_input_timestamp_ms", 9999999999999, "STALE_OR_FUTURE"),
    ("decision_cutoff_timestamp_ms", 1, "STALE_OR_FUTURE"),
    ("depth_impact_bps", None, "INVALID_COST_EVIDENCE"),
    ("entry_slippage_bps", 0, "FROZEN_COST_POLICY_MISMATCH"),
    ("cost_model_version", "other", "ENGINE_VERSION"),
])
def test_incompatible_required_snapshot_is_blocked(rows, field, value, reason):
    row = rows["cost"]
    row["geometry"][field] = value
    x = assess_boundary(row, {})
    assert x["state"] == "BLOCKED"
    assert reason in x["reason"]


def test_missing_cost_does_not_block_tighter_geometry(rows):
    row = rows["cost"]
    row["geometry"]["economic_input_timestamp_ms"] = None
    x = assess_boundary(row, {"geometry.stop_max_bps": 5})
    assert x["state"] == "VERIFIED_REJECTION"
    assert x["cost_requirement"] == "NOT_REQUIRED"


def test_probability_is_not_rejected_using_empty_statistics(rows):
    row = rows["cost"]
    x = assess_boundary(row, {"economics.min_net_edge_bps": 0, "geometry.minimum_planned_rr": 0.2})
    assert x["state"] == "PREFIX_VERIFIED"
    assert x["reason"] == "HISTORICAL_PROBABILITY_HIERARCHY_REQUIRED"


def save_dataset(tmp_path, row, missing=None):
    content = (json.dumps(row) + "\n").encode()
    m = {"content_sha256": sha256(content).hexdigest(), "symbols": [row["symbol"]],
         "intervals": {"search_start_ms": row["closed_until_ms"],
                       "search_end_ms": row["closed_until_ms"]+300000}, "missing_inputs": missing or []}
    m["fingerprint"] = fingerprint(m)
    (tmp_path / "HISTORY.jsonl").write_bytes(content)
    (tmp_path / "DATASET_MANIFEST.json").write_text(json.dumps(m))


def test_dataset_boundary_and_hard_gaps_cannot_be_certified(rows, tmp_path):
    save_dataset(tmp_path, rows["early"], ["CANDLE_COVERAGE_INCOMPLETE"])
    x = assess_dataset(tmp_path, [{}])
    assert x["combinations"][0]["admission_prefix_complete"] is False
    assert x["full_trade_simulation_verified"] is False


def test_tighter_combination_survives_missing_later_baseline_input(rows, tmp_path):
    row = rows["cost"]
    row["geometry"]["economic_input_timestamp_ms"] = None
    save_dataset(tmp_path, row)
    x = assess_dataset(tmp_path, [{"geometry.stop_max_bps": 5}])
    assert x["combinations"][0]["admission_prefix_complete"] is True


def test_tampered_baseline_blocks_reuse_and_combinations_are_independent(rows, tmp_path):
    row = rows["cost"]
    before = copy.deepcopy(row)
    a = assess_boundary(row, {})
    assess_boundary(row, {"geometry.stop_max_bps": 5})
    assert assess_boundary(row, {}) == a and row == before
    row["geometry"]["final_stop"] *= 1.1
    save_dataset(tmp_path, row)
    x = assess_dataset(tmp_path, [{}])
    assert x["combinations"][0]["states"] == {"BLOCKED": 1}


@pytest.mark.parametrize("change", [{"geometry.minimum_planned_rr": 0},
    {"geometry.stop_max_bps": 0}, {"economics.min_net_edge_bps": float('nan')}])
def test_invalid_combinations_are_not_certified(rows, change):
    assert assess_boundary(rows["cost"], change)["state"] == "BLOCKED"
