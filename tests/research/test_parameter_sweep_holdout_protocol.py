from __future__ import annotations

import json

import pytest

from traders_ml.parameter_sweep.checkpoint import compatible
from traders_ml.parameter_sweep.ranking import rank_results
from traders_ml.parameter_sweep.research_protocol import (
    HoldoutAccessPolicy, ResearchPhase, ResearchProtocolError,
    build_data_driven_ranges, build_winner_loser_dataset, canonical_hash,
    create_finalist_freeze, orchestrate_research_blocks, write_immutable_freeze,
    load_run_local_search_ranges,
)


def _ranked(params=None):
    values = params or {"threshold": 1}
    identity = canonical_hash(values)
    return [{
        "config_id": identity, "overrides": values,
        "evaluation_status": "ACCEPTED", "performance_class": "NEGATIVE_EXPECTANCY",
        "trade_count": 24, "expectancy_R": -.1, "profit_factor": .8,
        "max_drawdown": 2, "symbol_coverage": 5, "independent_period_count": 2,
    }]


def _freeze(params=None):
    rows = _ranked(params)
    return create_finalist_freeze(
        campaign_id="campaign", dataset_fingerprint="dataset",
        split_fingerprint="split", baseline_id="set2", search_space_hash="space",
        selection_rule={"validation_only": True}, ranked_rows=rows,
        finalist_count=1, freeze_timestamp="2026-09-11T00:00:00+00:00",
    )


@pytest.mark.parametrize("phase", [
    ResearchPhase.CALIBRATION_SEARCH,
    ResearchPhase.SEPARABILITY_ANALYSIS,
    ResearchPhase.DATA_DRIVEN_RANGE_GENERATION,
])
def test_holdout_read_before_freeze_fails_closed(phase):
    policy = HoldoutAccessPolicy(phase=phase)
    with pytest.raises(ResearchProtocolError, match="HOLDOUT_ACCESS_BEFORE_FINALIST_FREEZE"):
        policy.holdout_rows([], finalist_id="x", config_hash="x")


def test_ranking_rejects_holdout_metrics():
    row = _ranked()[0] | {"holdout_expectancy": 999}
    with pytest.raises(ResearchProtocolError, match="HOLDOUT_METRIC_IN_VALIDATION_RANKING"):
        rank_results([row])


def test_holdout_requires_freeze_and_rejects_non_finalist_and_is_one_shot():
    policy = HoldoutAccessPolicy()
    with pytest.raises(ResearchProtocolError, match="HOLDOUT_ACCESS_BEFORE_FINALIST_FREEZE"):
        policy.transition(ResearchPhase.HOLDOUT_EVALUATION)
    frozen = _freeze()
    policy.install_freeze(frozen)
    policy.transition(ResearchPhase.HOLDOUT_EVALUATION)
    finalist = frozen["finalists"][0]
    with pytest.raises(ResearchProtocolError, match="HOLDOUT_CONFIG_NOT_IN_FINALIST_FREEZE"):
        policy.holdout_rows([], finalist_id="other", config_hash="other")
    policy.holdout_rows([], finalist_id=finalist["finalist_id"], config_hash=finalist["config_hash"])
    with pytest.raises(ResearchProtocolError, match="HOLDOUT_ONE_SHOT_ALREADY_EVALUATED"):
        policy.holdout_rows([], finalist_id=finalist["finalist_id"], config_hash=finalist["config_hash"])
    with pytest.raises(ResearchProtocolError, match="POST_HOLDOUT_RETUNING_FORBIDDEN"):
        policy.transition(ResearchPhase.VALIDATION_RANKING)


def test_freeze_is_immutable_and_parameter_mutation_is_rejected(tmp_path):
    path = tmp_path / "FINALIST_FREEZE.json"
    original = _freeze()
    write_immutable_freeze(path, original)
    changed = _freeze({"threshold": 2})
    with pytest.raises(ResearchProtocolError, match="FINALIST_FREEZE_IMMUTABLE"):
        write_immutable_freeze(path, changed)
    policy = HoldoutAccessPolicy()
    policy.install_freeze(original)
    policy.transition(ResearchPhase.HOLDOUT_EVALUATION)
    finalist = original["finalists"][0]
    with pytest.raises(ResearchProtocolError, match="FINALIST_CONFIG_HASH_MISMATCH"):
        policy.holdout_rows([], finalist_id=finalist["finalist_id"], config_hash="mutated")


def test_resume_freeze_and_holdout_hashes_are_immutable():
    base = {
        "run_id": "r", "git_commit": "g", "config_hash": "c",
        "search_space_hash": "s", "dataset_fingerprint": "d", "strategy": "x",
        "seed": 1, "resolved_seed": 1, "freeze_hash": "f",
        "finalists_frozen": True, "holdout_opened": True,
        "holdout_result_hash": "h",
    }
    assert compatible(base, dict(base))
    assert not compatible(base, base | {"freeze_hash": "changed"})
    assert not compatible(base, base | {"holdout_result_hash": "changed"})


def test_zero_positive_block1_runs_blocks_2_and_3_and_reaches_4():
    calls = []
    status = orchestrate_research_blocks(
        "NO_POSITIVE_CONFIG_IN_CURRENT_SPACE",
        run_block2=lambda: calls.append("BLOCK2") or "STARTED",
        run_block3=lambda: calls.append("BLOCK3") or "STARTED",
    )
    assert calls == ["BLOCK2", "BLOCK3"]
    assert status["BLOCK4_REACHABLE"] is True


def test_winner_loser_dataset_excludes_holdout_and_proves_pre_entry_causality():
    calibration = [{
        "split": "CALIBRATION", "net_pnl": 1, "symbol": "BTCUSDT",
        "opened_at_ms": 100, "market_data_watermark_ms": 99, "strategy_score": 80,
    }]
    validation = [{
        "split": "VALIDATION", "net_pnl": -1, "symbol": "ETHUSDT",
        "opened_at_ms": 200, "market_data_watermark_ms": 200, "strategy_score": 70,
    }, {
        "split": "VALIDATION", "net_pnl": 1, "symbol": "LEAK",
        "opened_at_ms": 200, "market_data_watermark_ms": 201,
    }]
    rows = build_winner_loser_dataset(calibration, validation)
    assert [row["label"] for row in rows] == ["WIN", "LOSS"]
    assert {row["split"] for row in rows} == {"CALIBRATION", "VALIDATION"}
    assert all(row["feature_timestamp"] <= row["entry_decision_timestamp"] for row in rows)


def test_data_driven_range_artifact_is_run_local_and_does_not_mutate_yaml(tmp_path):
    yaml_path = tmp_path / "research.yaml"
    yaml_path.write_text("range: [1, 2]\n", encoding="utf-8")
    before = yaml_path.read_bytes()
    artifact = build_data_driven_ranges(
        search_space={"threshold": [1, 2]}, baseline={"threshold": 1},
        winner_loser_rows=[], proposals={"threshold": [1, 2]},
    )
    (tmp_path / "DATA_DRIVEN_SEARCH_RANGES.json").write_text(json.dumps(artifact), encoding="utf-8")
    assert artifact["mutates_yaml"] is False
    assert artifact["global_authority"] is False
    assert yaml_path.read_bytes() == before
    loaded = load_run_local_search_ranges(
        tmp_path / "DATA_DRIVEN_SEARCH_RANGES.json", {"threshold": [0]},
    )
    assert loaded == {"threshold": [1, 2]}
