from __future__ import annotations

import csv
import importlib.util
import inspect
import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/engine_trend_25_short_v2_contract_audit.py"
SPEC = importlib.util.spec_from_file_location("engine_trend_25", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


@pytest.fixture(scope="module")
def candidates():
    return audit.load_candidates()


@pytest.fixture(scope="module")
def candles(candidates):
    return audit.load_candles(candidates)


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    output = tmp_path_factory.mktemp("engine_trend_25")
    result = audit.run(output_dir=output)
    return output, result


def test_contract_is_audit_only_and_blocks_non_short_contracts():
    contract = audit.default_contract()
    assert contract["audit_only"] is True
    assert contract["paper_enabled"] is False
    assert contract["stages"] == ["SETUP_READY", "ENTRY_ARMED", "TRADE_CANDIDATE"]
    assert contract["contract_dispositions"][audit.SHORT_V1] == "ALLOW_FOR_REDESIGN_NOT_PAPER"
    assert contract["contract_dispositions"]["LONG_UP_CONTINUATION_RETEST"] == "BLOCK_FROM_PAPER"
    assert contract["contract_dispositions"]["RANGE_MEAN_REVERSION_CANDIDATE"] == "BLOCK_FROM_PAPER"


def test_replay_covers_449_candidates_and_all_36_variants(generated):
    _, result = generated
    assert result["processed"] == 449
    assert result["rows"] == 449 * 3 * 3 * 4 == 16164
    assert len(result["default_rows"]) == 449


def test_only_old_short_contract_can_reach_trade_candidate(generated):
    _, result = generated
    assert all(
        row["setup_type"] == audit.SHORT_V1
        for row in result["default_rows"]
        if row["stage"] == "TRADE_CANDIDATE"
    )
    blocked = [row for row in result["default_rows"] if row["setup_type"] != audit.SHORT_V1]
    assert blocked and all(row["stage"] == "BLOCKED_CONTRACT" for row in blocked)


def test_legacy_short_hypothesis_is_normalized_only_when_replay_is_absent(candidates, candles):
    candidate = next(c for c in candidates if c["setup_type"] == audit.SHORT_V1 and not c.get("current_engine_trend_replay"))
    context = audit.candidate_context(candidate, candles[candidate["symbol"]])
    _, failures, _ = audit.base_stage(candidate, context)
    assert "DOWN_CONTINUATION_NOT_CONFIRMED" not in failures
    conflicted = deepcopy(candidate)
    conflicted["current_engine_trend_replay"] = {
        "market_regime": "FLAT", "selected_hypothesis": "CONFIRMED_RANGE",
        "selected_hypothesis_status": "CONFIRMED", "conflict_level": "HIGH",
    }
    context["replay"] = conflicted["current_engine_trend_replay"]
    _, failures, _ = audit.base_stage(conflicted, context)
    assert "DOWN_CONTINUATION_NOT_CONFIRMED" in failures
    assert "DOWN_REGIME_NOT_CONFIRMED" in failures


def test_volume_below_point_seven_is_hard_fail(candidates, candles):
    candidate = next(
        c for c in candidates
        if c["setup_type"] == audit.SHORT_V1
        and c["technical_confirmation"]["values"]["volume_ratio_20"] < 0.7
        and not c.get("current_engine_trend_replay")
    )
    context = audit.candidate_context(candidate, candles[candidate["symbol"]])
    _, failures, _ = audit.base_stage(candidate, context)
    assert "VOLUME_BELOW_0_7" in failures


def test_stop_target_and_room_hard_fails_are_structural():
    context = {"atr": 100.0, "nearest_support": 800.0, "strong_support": None}
    failures, _, geometry = audit.trade_geometry(1000.0, 1050.0, 900.0, context, "previous_low")
    assert geometry["stop_atr"] == 0.5
    assert "STOP_DISTANCE_ATR_BELOW_0_75" in failures
    failures, _, _ = audit.trade_geometry(1000.0, 1100.0, 550.0, context, "previous_low")
    assert "TARGET_DISTANCE_ATR_ABOVE_4_0" in failures
    failures, _, _ = audit.trade_geometry(1000.0, 1100.0, 900.0, context, "previous_low")
    assert "NO_ROOM_TO_TARGET_RR_BELOW_1_5" in failures


def test_pre_entry_decision_functions_do_not_read_outcomes():
    source = "\n".join(inspect.getsource(fn) for fn in (
        audit.base_stage, audit.find_entry, audit.trade_geometry, audit.evaluate_variant,
    ))
    for forbidden in ("outcome", "mfe", "mae", "net_return_pct"):
        assert f'candidate["{forbidden}"]' not in source


def test_validation_is_separate_and_old_engine_24_pocket_is_reproduced(generated):
    _, result = generated
    pocket = result["comparison"]["validation"]["old_engine_24_pass_short"]
    assert pocket["clean_trades"] == 12
    assert pocket["profit_factor"] == pytest.approx(1.2705817501245233)
    assert pocket["expectancy_pct"] == pytest.approx(0.12841809453176514)
    assert {row["split"] for row in result["default_rows"]} == {"TRAIN_DESIGN", "OUT_OF_TIME_VALIDATION"}


def test_artifacts_and_controlled_mode_comparisons_are_written(generated):
    output, _ = generated
    assert all((output / name).is_file() for name in audit.OUTPUT_FILES)
    comparison = json.loads((output / "ENGINE_TREND_25_VALIDATION_COMPARISON.json").read_text(encoding="utf-8"))
    assert set(comparison["mode_comparison"]) == {
        "entry_modes_at_atr_0_15_previous_low",
        "target_modes_at_break_atr_0_15",
        "stop_modes_at_break_previous_low",
    }
    with (output / "ENGINE_TREND_25_CANDIDATE_REPLAY.csv").open(encoding="utf-8", newline="") as handle:
        assert len(list(csv.DictReader(handle))) == 449


def test_no_runtime_or_paper_code_is_claimed_changed(generated):
    output, result = generated
    decision = json.loads((output / "ENGINE_TREND_25_DECISION_RECORD.json").read_text(encoding="utf-8"))
    assert decision == result["decision"]
    assert decision["paper_enabled"] is False
    assert decision["runtime_changed"] is False
    assert decision["trading_runtime_changed"] is False
    assert decision["profitable_system_validated"] is False
