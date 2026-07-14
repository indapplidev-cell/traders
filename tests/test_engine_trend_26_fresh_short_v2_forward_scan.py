from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/engine_trend_26_fresh_short_v2_forward_scan.py"
SPEC = importlib.util.spec_from_file_location("engine_trend_26", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    output = tmp_path_factory.mktemp("engine_trend_26")
    result = audit.run(output)
    return output, result


def test_locked_window_is_common_and_reserves_full_outcome_horizon():
    contract = audit.locked_contract()
    assert contract["universe"].startswith("all 15m decision points")
    assert contract["forward_window"]["start"] == "2025-12-18T00:00:00Z"
    assert audit.SCAN_END + audit.HORIZON * audit.STEP == audit.COMMON_LAST_CANDLE
    assert contract["paper_enabled"] is False


def test_fresh_scanner_does_not_load_v1_candidate_artifacts():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "HISTORICAL_ENTRY_DISCOVERY_RESULTS.json" not in source
    assert "ENGINE_TREND_25_CANDIDATE_REPLAY" not in source
    assert "449-candidate artifact is not loaded" in source


def test_all_symbols_pass_exact_data_quality_gate(generated):
    _, result = generated
    assert {row["symbol"] for row in result["coverage"]} == set(audit.SYMBOLS)
    assert all(row["status"] == "PASS" for row in result["coverage"])
    assert all(row["actual"] == row["expected"] == 17505 for row in result["coverage"])


def test_pre_entry_freeze_precedes_and_excludes_outcomes(generated):
    output, result = generated
    payload = (output / "ENGINE_TREND_26_PRE_ENTRY_PLANS.json").read_bytes()
    assert hashlib.sha256(payload).hexdigest() == result["decision"]["pre_entry_freeze_sha256"]
    frozen = json.loads(payload)["plans"]
    assert frozen
    assert all("label" not in plan and "net_return_pct" not in plan for plan in frozen)
    run_source = inspect.getsource(audit.run)
    assert run_source.index("freeze_plans(plans)") < run_source.index("label_plan(plan")


def test_generation_functions_do_not_access_outcome_fields():
    source = "\n".join(inspect.getsource(function) for function in (
        audit.engine_hypothesis, audit.nearest_target, audit.find_break_entry, audit.scan_symbol,
    ))
    for forbidden in ("label_plan", "net_return_pct", "TP_BEFORE_SL", "SL_BEFORE_TP", "mfe", "mae"):
        assert forbidden not in source


def test_every_frozen_trade_satisfies_locked_geometry(generated):
    _, result = generated
    assert result["plans"]
    for plan in result["plans"]:
        assert plan["stage_trace"] == ["SETUP_READY", "ENTRY_ARMED", "TRADE_CANDIDATE"]
        assert plan["stop_distance_atr"] >= 0.75
        assert plan["target_distance_atr"] <= 4.0
        assert plan["planned_rr"] >= 1.5
        assert plan["engine_hypothesis"]["market_regime"] == "DOWN"
        assert plan["engine_hypothesis"]["selected_hypothesis"] == "DOWN_CONTINUATION"
        assert plan["engine_hypothesis"]["selected_hypothesis_status"] == "CONFIRMED"


def test_forward_scan_result_and_empty_partitions_are_explicit(generated):
    _, result = generated
    assert result["funnel"]["DECISION_POINTS"] == 51507
    assert result["funnel"]["SETUP_READY_CONFIRMED"] == 214
    assert result["funnel"]["TRADE_CANDIDATE"] == 1
    metrics = result["metrics"]
    assert metrics["full_forward"]["clean_trades"] == 1
    assert metrics["full_forward"]["losses"] == 1
    assert set(metrics["by_symbol"]) == set(audit.SYMBOLS)
    assert set(metrics["by_month"]) == {"2025-12", "2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"}


def test_gate_fails_and_runtime_remains_unchanged(generated):
    output, result = generated
    decision = json.loads((output / "ENGINE_TREND_26_DECISION_RECORD.json").read_text(encoding="utf-8"))
    assert decision == result["decision"]
    assert decision["final_status"] == "ENGINE_TREND_26_FORWARD_GATE_FAIL_NOT_READY_FOR_PAPER"
    assert decision["acceptance_gate"]["paper_evidence_gate_pass"] is False
    assert decision["paper_enabled"] is False
    assert decision["runtime_changed"] is False
    assert decision["v1_candidates_loaded"] is False


def test_manifest_lists_every_artifact(generated):
    output, _ = generated
    manifest = json.loads((output / "ENGINE_TREND_26_ARTIFACT_MANIFEST.json").read_text(encoding="utf-8"))
    assert set(manifest["created_files"]) == set(audit.OUTPUT_FILES)
    assert all((output / name).is_file() for name in audit.OUTPUT_FILES)
