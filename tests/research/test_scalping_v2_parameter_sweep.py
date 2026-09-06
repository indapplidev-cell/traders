import json
from pathlib import Path

import pytest
import yaml

from app.research.scalping_v2_parameter_sweep import _stale_policy, run


def _time_stop_space() -> dict[str, list[object]]:
    return {
        "soft_timeout_seconds": [600], "hard_timeout_seconds": [900],
        "min_target_progress_at_soft_timeout": [.2],
        "min_mfe_bps_at_soft_timeout": [None],
        "min_remaining_ev_r_at_soft_timeout": [0],
        "extension_seconds": [300], "max_extensions": [1],
        "break_even_activation_target_progress": [.5],
        "net_break_even_protection_enabled": [True],
    }


def _rows() -> list[dict[str, object]]:
    rows = []
    for index, split in enumerate((
        "CALIBRATION", "CALIBRATION", "VALIDATION", "VALIDATION",
        "HOLDOUT", "HOLDOUT",
    )):
        opened = index * 2_000_000
        rows.append({
            "position_id": f"p{index}", "split": split,
            "opened_at_ms": opened, "closed_at_ms": opened + 1_200_000,
            "expected_ev_r": .2, "ev_reserve": .3, "net_edge_bps": 20,
            "probability_sample_size": 50, "stop_distance_bps": 40,
            "target_distance_bps": 80, "causal_reset_conditions": 1,
            "one_min_confirmation_count": 1,
            "net_pnl": 1 if index % 2 == 0 else -.5, "gross_pnl": 1.2,
            "fees": .2, "exit_reason": "TARGET" if index % 2 == 0 else "STOP",
            "holding_time_ms": 1_200_000, "mae": 2, "mfe": 4,
            "symbol": "BTCUSDT", "direction": "LONG",
            "setup_type": "BREAKOUT", "session": "UTC",
            "entry_price": 100, "quantity": 1, "stop_price": 99,
            "target_price": 102, "entry_fee_incurred": .09,
            "time_stop_observations": [{
                "evaluation_time_ms": opened + 600_000,
                "evaluation_closed_until_ms": opened + 600_000,
                "current_price": 100.1, "highs": [100.2], "lows": [99.9],
                "exit_commission_bps": 9, "spread_bps": 2,
                "slippage_bps": 2, "adverse_exit_reserve_bps": 3,
                "setup_valid": False, "momentum_valid": False,
                "remaining_ev_r": 0, "historical_cost_evidence": True,
                "commission_source": "HISTORICAL_BINANCE_ACCOUNT_COMMISSION",
            }],
            "causal_later_candidates": [{
                "candidate_id": f"later-{index}",
                "candidate_time_ms": opened + 700_000,
            }],
        })
    return rows


def _search(tmp_path: Path, rows: list[dict[str, object]]) -> Path:
    dataset = tmp_path / "dataset.json"
    dataset.write_text(json.dumps(rows), encoding="utf-8")
    space = {
        "min_positive_ev_r": [0, .1], "min_ev_reserve_r": [0],
        "min_net_edge_bps": [1], "bucket_min_sample": [20],
        "probability_confidence_level": [.95], "prior_alpha": [1],
        "prior_beta": [1], "adverse_fill_reserve_bps": [3],
        "entry_slippage_bps": [2], "stop_max_bps": [50],
        "target_min_bps": [45], "causal_reset_min_conditions": [1],
        "entry_refinement_1m_confirmation_count": [1], **_time_stop_space(),
    }
    search = {
        "schema_version": 2, "seed": 1, "dataset": str(dataset),
        "output_root": str(tmp_path / "artifacts"),
        "minimum_samples": {"calibration": 2, "validation": 2, "holdout": 2},
        "search_space": space,
    }
    search_path = tmp_path / "search.yaml"
    search_path.write_text(yaml.safe_dump(search), encoding="utf-8")
    return search_path


def test_two_variant_smoke_reuses_time_stop_evaluator_and_has_zero_mutation(tmp_path):
    output = run(_search(tmp_path, _rows()), run_id="smoke")
    expected = {
        "RUN_CONFIG.yaml", "RESULTS.csv", "RESULTS.json", "TOP_CONFIGS.json",
        "REJECTED_CONFIGS.json", "REPORT.md",
    }
    assert {path.name for path in output.iterdir()} == expected
    results = json.loads((output / "RESULTS.json").read_text())
    assert len(results) == 2
    validation = results[0]["validation"]
    assert validation["soft_timeout_count"] == 2
    assert validation["time_stop_exit_count"] == 2
    assert validation["stale_position_seconds_saved"] == 1200
    assert validation["candidates_blocked_while_position_open"] == 2
    assert validation["hypothetical_candidates_unblocked_after_stale_exit"] == 2
    assert validation["replay_status"] == {"REPLAYED": 2}
    report = (output / "REPORT.md").read_text(encoding="utf-8")
    assert "TIME-STOP / STALE-POSITION ANALYSIS" in report
    assert "Holdout is not ranked" in report
    run_config = yaml.safe_load((output / "RUN_CONFIG.yaml").read_text())
    assert run_config["time_stop_policy_schema"] == "StalePositionPolicyParameters"
    assert run_config["production_mutations"] == 0
    assert run_config["production_config_writes"] == 0
    assert run_config["approvals_created"] == 0
    assert run_config["commands_created"] == 0
    assert run_config["positions_created"] == 0
    assert run_config["binance_order_api_calls"] == 0


def test_invalid_timeout_relationship_is_rejected_not_executed(tmp_path):
    search_path = _search(tmp_path, _rows())
    search = yaml.safe_load(search_path.read_text())
    search["search_space"]["hard_timeout_seconds"] = [600]
    search_path.write_text(yaml.safe_dump(search), encoding="utf-8")
    output = run(search_path, run_id="invalid", max_configs=1)
    result = json.loads((output / "RESULTS.json").read_text())[0]
    assert result["split_status"]["validation"] == "INVALID_CONFIG"
    assert "soft timeout must be below hard timeout" in result["invalid_reason"]


def test_missing_historical_cost_evidence_is_unreplayable_without_invention(tmp_path):
    rows = _rows()
    rows[2]["time_stop_observations"][0]["historical_cost_evidence"] = False
    rows[3]["time_stop_observations"] = []
    output = run(_search(tmp_path, rows), run_id="missing", max_configs=1)
    result = json.loads((output / "RESULTS.json").read_text())[0]
    assert result["validation"]["replay_status"] == {
        "UNREPLAYABLE": 1, "INSUFFICIENT_DATA": 1,
    }
    assert result["validation"]["time_stop_exit_count"] == 0


def test_search_schema_requires_every_runtime_time_stop_dimension(tmp_path):
    search_path = _search(tmp_path, _rows())
    search = yaml.safe_load(search_path.read_text())
    del search["search_space"]["min_mfe_bps_at_soft_timeout"]
    search_path.write_text(yaml.safe_dump(search), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid research search space"):
        run(search_path, run_id="missing-dimension")


@pytest.mark.parametrize("overrides", (
    {"hard_timeout_seconds": 600},
    {"extension_seconds": 0, "max_extensions": 1},
    {"max_extensions": -1},
    {"min_target_progress_at_soft_timeout": 1.1},
    {"break_even_activation_target_progress": -0.1},
    {"min_mfe_bps_at_soft_timeout": -1},
    {"min_remaining_ev_r_at_soft_timeout": -0.1},
))
def test_runtime_schema_rejects_invalid_or_contradictory_time_stop_configs(overrides):
    config = {name: values[0] for name, values in _time_stop_space().items()}
    config.update(overrides)
    with pytest.raises(ValueError):
        _stale_policy(config)
