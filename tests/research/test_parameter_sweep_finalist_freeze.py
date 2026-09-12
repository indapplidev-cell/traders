from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
import yaml

from app.config.yaml_authority import RESEARCH_PARAMETERS
from traders_ml.parameter_sweep.finalist_freeze import (
    CANONICAL_SERIALIZATION_VERSION, FinalistFreezeError,
    run_finalist_freeze, validation_ranking_handoff_fingerprint, verify_freeze,
)


IDENTITY = {
    "symbol": "DOGEUSDT", "profile": "trade-5m-v2",
    "dataset_fingerprint": "dataset", "calibration_split_fingerprint": "calibration",
    "validation_split_fingerprint": "validation",
    "validation_policy_fingerprint": "validation-policy",
    "ranking_policy_fingerprint": "ranking-policy",
    "parameter_registry_fingerprint": "registry",
}


def _candidate(config_id: str, signature: str, rank: int, *, eligible: bool = True, members=None):
    return {
        "validation_eligible": eligible, "behavioral_signature": signature,
        "representative_config_id": config_id,
        "member_config_ids": members or [config_id],
        "canonical_validation_rank": rank,
        "canonical_gate_results": {"minimum_trades_20": True, "independent_periods_3": True},
        "parameters": {"min_net_edge_bps": rank},
        "validation_trade_count": 20 + rank, "wins": 12, "losses": 8,
        "neutrals": 0, "net_pnl": 1.5, "expectancy_r": .1,
        "stored_profit_factor": 1.2, "profit_factor_available": True,
        "profit_factor_ranking_value": 1.2, "max_drawdown": .5,
        "independent_periods": 3,
        "robustness_diagnostics": {"rank_stability": .9},
    }


def _handoff(eligible=None, descriptive=None):
    value = {
        "artifact": "VALIDATION_RANKING_HANDOFF", "schema_version": 1,
        **IDENTITY,
        "eligible_behavioral_representatives": eligible or [],
        "descriptive_non_eligible_ranking": descriptive or [],
    }
    value["validation_ranking_handoff_fingerprint"] = validation_ranking_handoff_fingerprint(value)
    return value


def _policy(tmp_path: Path, count: int) -> Path:
    value = RESEARCH_PARAMETERS.model_dump(mode="python")
    value["artifact"]["finalist_config_count"] = count
    path = tmp_path / f"research-{count}.yaml"
    path.write_text(yaml.safe_dump(value), encoding="utf-8")
    return path


def _run(tmp_path: Path, handoff, *, symbol="DOGEUSDT", count=5, output_name="out"):
    path = tmp_path / f"handoff-{output_name}.json"
    path.write_text(json.dumps(handoff), encoding="utf-8")
    identity = dict(IDENTITY)
    identity["symbol"] = symbol
    return run_finalist_freeze(
        handoff_path=path, output=tmp_path / output_name,
        research_parameters_path=_policy(tmp_path, count), **identity,
    )


def test_eligible_only_and_exact_handoff_order_with_behavioral_members(tmp_path):
    first = _candidate("a", "sig-a", 1, members=["a", "a-alias"])
    second = _candidate("c", "sig-c", 3)
    descriptive = _candidate("b", "sig-b", 2, eligible=False)
    result = _run(tmp_path, _handoff([first, second], [descriptive]))
    freeze = result["freeze"]
    assert [row["representative_config_id"] for row in freeze["finalists"]] == ["a", "c"]
    assert freeze["selected_finalist_count"] == 2
    assert result["status"]["ELIGIBLE_NUMERIC_CONFIGS"] == 3
    assert result["status"]["DESCRIPTIVE_BEHAVIORAL_CANDIDATES_EXCLUDED"] == 1
    assert result["handoff"]["holdout_reads"] == 0
    assert result["handoff"]["holdout_opened"] is False


def test_duplicate_eligible_behavioral_representatives_fail_closed(tmp_path):
    rows = [_candidate("a", "same", 1), _candidate("b", "same", 2)]
    with pytest.raises(FinalistFreezeError, match="FAIL_CLOSED_DUPLICATE_BEHAVIORAL_REPRESENTATIVE"):
        _run(tmp_path, _handoff(rows), output_name="duplicate")


def test_zero_eligible_creates_immutable_empty_freeze(tmp_path):
    result = _run(tmp_path, _handoff([], [_candidate("b", "b", 1, eligible=False)]))
    assert result["freeze"]["finalists"] == []
    assert result["freeze"]["selection_reason"] == "ZERO_ELIGIBLE_VALIDATION_FINALISTS"
    assert result["handoff"]["promotion_eligible"] is False
    verify_freeze(result["freeze"])


def test_policy_fixture_changes_count_without_code_change(tmp_path):
    rows = [_candidate(str(index), f"sig-{index}", index) for index in range(1, 4)]
    handoff = _handoff(rows)
    one = _run(tmp_path, handoff, count=1, output_name="one")["freeze"]
    two = _run(tmp_path, handoff, count=2, output_name="two")["freeze"]
    assert one["selected_finalist_count"] == 1
    assert two["selected_finalist_count"] == 2


def test_same_inputs_are_byte_deterministic_and_resume_safe(tmp_path):
    handoff = _handoff([_candidate("a", "sig-a", 1)])
    first = _run(tmp_path, handoff, output_name="same")
    before = (tmp_path / "same" / "FINALIST_FREEZE.json").read_bytes()
    second = _run(tmp_path, handoff, output_name="same")
    assert first["freeze"] == second["freeze"]
    assert before == (tmp_path / "same" / "FINALIST_FREEZE.json").read_bytes()
    assert first["freeze"]["canonical_serialization_version"] == CANONICAL_SERIALIZATION_VERSION


def test_mutated_frozen_parameter_fails_closed(tmp_path):
    result = _run(tmp_path, _handoff([_candidate("a", "sig-a", 1)]), output_name="mutated")
    path = tmp_path / "mutated" / "FINALIST_FREEZE.json"
    changed = deepcopy(result["freeze"])
    changed["finalists"][0]["parameters"]["min_net_edge_bps"] = 999
    path.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(FinalistFreezeError, match="FAIL_CLOSED_FINALIST_FREEZE_MUTATED"):
        _run(tmp_path, _handoff([_candidate("a", "sig-a", 1)]), output_name="mutated")


@pytest.mark.parametrize("field", [
    "dataset_fingerprint", "validation_split_fingerprint",
    "ranking_policy_fingerprint", "validation_policy_fingerprint",
])
def test_campaign_mismatches_fail_closed(tmp_path, field):
    handoff = _handoff([_candidate("a", "sig-a", 1)])
    handoff[field] = "wrong"
    handoff["validation_ranking_handoff_fingerprint"] = validation_ranking_handoff_fingerprint(handoff)
    with pytest.raises(FinalistFreezeError, match="FAIL_CLOSED_CAMPAIGN_MISMATCH"):
        _run(tmp_path, handoff, output_name=field)


def test_holdout_shaped_neighbor_is_never_read(tmp_path):
    handoff = _handoff([_candidate("a", "sig-a", 1)])
    path = tmp_path / "input" / "VALIDATION_RANKING_HANDOFF.json"
    path.parent.mkdir()
    path.write_text(json.dumps(handoff), encoding="utf-8")
    (path.parent / "HOLDOUT_RESULTS.json").write_text("not-json-and-must-not-be-read", encoding="utf-8")
    result = run_finalist_freeze(
        handoff_path=path, output=tmp_path / "holdout-blind",
        research_parameters_path=_policy(tmp_path, 5), **IDENTITY,
    )
    assert result["status"]["HOLDOUT_READS"] == 0


def test_embedded_holdout_data_fails_closed(tmp_path):
    handoff = _handoff([_candidate("a", "sig-a", 1)])
    handoff["holdout_ranking"] = [{"net_pnl": 999}]
    handoff["validation_ranking_handoff_fingerprint"] = validation_ranking_handoff_fingerprint(handoff)
    with pytest.raises(FinalistFreezeError, match="FAIL_CLOSED_HOLDOUT_DATA_IN_VALIDATION_RANKING_HANDOFF"):
        _run(tmp_path, handoff, output_name="embedded-holdout")


@pytest.mark.parametrize("symbol", ["DOGEUSDT", "LINKUSDT"])
def test_same_path_for_two_symbols(tmp_path, symbol):
    identity = dict(IDENTITY, symbol=symbol)
    handoff = _handoff([_candidate("a", "sig-a", 1)]) | {"symbol": symbol}
    handoff["validation_ranking_handoff_fingerprint"] = validation_ranking_handoff_fingerprint(handoff)
    path = tmp_path / f"{symbol}.json"
    path.write_text(json.dumps(handoff), encoding="utf-8")
    result = run_finalist_freeze(
        handoff_path=path, output=tmp_path / f"out-{symbol}",
        research_parameters_path=_policy(tmp_path, 5), **identity,
    )
    assert result["freeze"]["symbol"] == symbol


def test_missing_handoff_fails_closed_without_reconstruction(tmp_path):
    with pytest.raises(FinalistFreezeError, match="FAIL_CLOSED_MISSING_VALIDATION_RANKING_HANDOFF"):
        run_finalist_freeze(
            handoff_path=tmp_path / "missing.json", output=tmp_path / "out",
            research_parameters_path=_policy(tmp_path, 5), **IDENTITY,
        )
    assert not (tmp_path / "out").exists()
