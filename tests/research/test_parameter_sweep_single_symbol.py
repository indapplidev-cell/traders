import json
from pathlib import Path

import pytest
import yaml

from app.config.yaml_authority import RESEARCH_PARAMETERS
from traders_ml.parameter_sweep.artifact_v2 import canonical_validation_projection, compact_result
from traders_ml.parameter_sweep.cli import build_parser
from traders_ml.parameter_sweep.controller import ParameterSweepController
from traders_ml.parameter_sweep.engine import SweepExpectedError, _evaluate_config, run
from traders_ml.parameter_sweep.universe import (
    resolve_parameter_sweep_universe,
    validate_parameter_sweep_symbol,
)
from traders_ml.parameter_sweep.research_protocol import (
    HoldoutAccessPolicy, ResearchPhase, ResearchProtocolError,
    create_finalist_freeze, deduplicate_validation_behavior,
    eligible_validation_finalists,
)


def _rows(symbols=("LINKUSDT", "BTCUSDT")):
    rows = []
    for symbol in symbols:
        for index, split in enumerate((
            "CALIBRATION", "CALIBRATION", "VALIDATION", "VALIDATION",
            "HOLDOUT", "HOLDOUT",
        )):
            opened = index * 86_400_000
            rows.append({
                "position_id": f"{symbol}-p{index}", "command_id": f"{symbol}-c{index}",
                "profile_id": "trade-5m-v2", "primary_timeframe": "5m",
                "split": split, "opened_at_ms": opened,
                "closed_at_ms": opened + 1_200_000, "expected_ev_r": .2,
                "ev_reserve": .3, "net_edge_bps": 20,
                "probability_sample_size": 50, "stop_distance_bps": 40,
                "target_distance_bps": 80, "causal_reset_conditions": 1,
                "one_min_confirmation_count": 1,
                "net_pnl": 1 if index % 2 == 0 else -.5, "gross_pnl": 1.2,
                "fees": .2, "exit_reason": "TARGET" if index % 2 == 0 else "STOP",
                "holding_time_ms": 1_200_000, "mae": 2, "mfe": 4,
                "symbol": symbol, "direction": "LONG", "setup_type": "BREAKOUT",
                "session": "UTC", "entry_price": 100, "quantity": 1,
                "stop_price": 99, "exit_price": 101, "target_price": 102,
                "entry_fee_incurred": .09, "exit_fee_incurred": .11,
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
            })
    return rows


def _search(tmp_path: Path) -> Path:
    dataset = tmp_path / "mixed.json"
    dataset.write_text(json.dumps(_rows()), encoding="utf-8")
    value = RESEARCH_PARAMETERS.model_dump(mode="python")
    value["dataset"] = {
        "source": str(dataset), "profile": "trade-5m-v2",
        "primary_timeframe": "5m", "closed_only": False,
        "selection_mode": "ALL_UNTIL_CUTOFF", "max_rows": None,
    }
    value["output_root"] = str(tmp_path / "artifacts")
    value["minimum_samples"] = {"calibration": 2, "validation": 2, "holdout": 2}
    value["search"]["strategy"] = "bounded"
    value["search"]["max_evaluated_configs"] = 1
    value["search"]["batch_size"] = 1
    value["search_space"] = {
        "min_positive_ev_r": [0, .1], "min_ev_reserve_r": [0], "min_net_edge_bps": [1],
        "bucket_min_sample": [20], "probability_confidence_level": [.95],
        "prior_alpha": [1], "prior_beta": [1], "adverse_fill_reserve_bps": [3],
        "entry_slippage_bps": [2], "stop_max_bps": [50], "target_min_bps": [45],
        "causal_reset_min_conditions": [1],
        "entry_refinement_1m_confirmation_count": [1], "soft_timeout_seconds": [600],
        "hard_timeout_seconds": [900], "min_target_progress_at_soft_timeout": [.2],
        "min_mfe_bps_at_soft_timeout": [None], "min_remaining_ev_r_at_soft_timeout": [0],
        "extension_seconds": [300], "max_extensions": [1],
        "break_even_activation_target_progress": [.5],
        "net_break_even_protection_enabled": [True],
    }
    path = tmp_path / "search.yaml"
    path.write_text(yaml.safe_dump(value), encoding="utf-8")
    return path


def test_authoritative_universe_and_strict_selection(tmp_path):
    universe_id, symbols = resolve_parameter_sweep_universe()
    assert universe_id == "trading-universe-v2"
    assert len(symbols) == 10
    assert validate_parameter_sweep_symbol("linkusdt") == "LINKUSDT"
    with pytest.raises(ValueError, match="SYMBOL_REQUIRED"):
        validate_parameter_sweep_symbol(None)
    with pytest.raises(ValueError, match="SYMBOL_NOT_IN_ACTIVE_UNIVERSE"):
        validate_parameter_sweep_symbol("NOTREAL")
    controller = ParameterSweepController(_search(tmp_path), tmp_path / "artifacts")
    assert controller.available_symbols == symbols
    with pytest.raises(ValueError, match="SYMBOL_REQUIRED"):
        controller.start_new_run(symbol=None)
    assert build_parser().parse_args(["--symbol", "LINKUSDT"]).symbol == "LINKUSDT"


@pytest.mark.parametrize("symbol", ("LINKUSDT", "BTCUSDT"))
def test_single_symbol_smoke_binds_every_artifact(tmp_path, symbol):
    output = run(_search(tmp_path), run_id=f"smoke-{symbol}", symbol=symbol, max_configs=1)
    manifest = json.loads((output / "DATASET_MANIFEST.json").read_text())
    checkpoint = json.loads((output / "CHECKPOINT.json").read_text())
    status = json.loads((output / "STATUS.json").read_text())
    run_manifest = json.loads((output / "RUN_MANIFEST.json").read_text())
    config = yaml.safe_load((output / "RUN_CONFIG.yaml").read_text())
    results = [json.loads(line) for line in (output / "RESULTS.jsonl").read_text().splitlines() if line]
    assert manifest["symbols"] == [symbol]
    assert manifest["dataset_symbol_count"] == 1
    assert {row["symbol"] for row in results} == {symbol}
    assert all(row["evaluated_symbol_count"] == 1 for row in results)
    assert checkpoint["symbol"] == status["symbol"] == run_manifest["symbol"] == symbol
    assert config["symbol"] == symbol
    assert json.loads((output / "FINALIST_FREEZE.json").read_text())["symbol"] == symbol
    report = (output / "REPORT.md").read_text()
    assert report.startswith(f"PROFILE = trade-5m-v2\nTIMEFRAME = 5m\nSYMBOL = {symbol}\n")


def test_resume_and_contamination_fail_closed(tmp_path):
    path = _search(tmp_path)
    run(path, run_id="resume-symbol", symbol="LINKUSDT", max_configs=1, preflight_only=True)
    run(path, run_id="resume-symbol", symbol="LINKUSDT", max_configs=1, resume=True)
    run(path, run_id="wrong-symbol", symbol="LINKUSDT", max_configs=1, preflight_only=True)
    with pytest.raises(SweepExpectedError, match="RESUME_SYMBOL_MISMATCH"):
        run(path, run_id="wrong-symbol", symbol="BTCUSDT", max_configs=1, resume=True)
    split = {"CALIBRATION": _rows(("LINKUSDT",))[:2], "VALIDATION": _rows(("BTCUSDT",))[2:4]}
    with pytest.raises(SweepExpectedError, match="CROSS_SYMBOL_CONTAMINATION"):
        _evaluate_config({}, split, {"calibration": 1, "validation": 1}, index=0, stage="TEST")


def test_single_symbol_coverage_expected_is_one():
    row = compact_result({
        "result_index": 0, "config_hash": "x", "symbol": "LINKUSDT",
        "evaluated_symbol_count": 1, "result_status": "ACCEPTED",
        "validation": {"trades": [{"symbol": "LINKUSDT", "setup_type": "BREAKOUT", "net_pnl": 1, "opened_at_ms": 0}]},
    })
    assert row["symbol_coverage"] == row["symbol_coverage_expected"] == 1
    assert row["symbol_coverage_pass"] is True
    assert not any(gate["gate"] == "symbol_coverage" for gate in row["insufficient_sample_gates"])


def test_canonical_result_status_report_projection_parity(tmp_path):
    output = run(_search(tmp_path), run_id="parity", symbol="LINKUSDT", max_configs=1)
    result = json.loads((output / "RESULTS.json").read_text())[0]
    expected = canonical_validation_projection(result)
    status = json.loads((output / "STATUS.json").read_text())
    checkpoint = json.loads((output / "CHECKPOINT.json").read_text())
    report = (output / "REPORT.md").read_text()
    assert status["canonical_validation"] == checkpoint["canonical_validation"] == expected
    for field in (
        "validation_trade_count", "symbol_coverage", "symbol_coverage_expected",
        "symbol_coverage_pass", "independent_period_count", "setup_coverage",
        "regime_coverage",
    ):
        assert status[field] == checkpoint[field] == expected[field]
    assert f"CANONICAL_VALIDATION: `{json.dumps(expected, sort_keys=True)}`" in report


def _eligible(config_id, signature):
    return {
        "config_id": config_id, "evaluation_status": "ACCEPTED",
        "performance_class": "VALIDATION_CANDIDATE",
        "symbol_coverage_pass": True, "insufficient_sample_gates": [],
        "validation_behavioral_signature": signature,
        "candidate_parameters": {"x": config_id}, "trade_count": 21,
    }


def test_eligible_only_behavioral_finalist_dedup_is_deterministic():
    rows = [
        _eligible("representative", "same"), _eligible("equivalent", "same"),
        _eligible("different", "different"),
        {**_eligible("ineligible", "third"), "performance_class": "INSUFFICIENT_SAMPLE"},
    ]
    eligible = eligible_validation_finalists(rows)
    deduplicated = deduplicate_validation_behavior(eligible)
    assert [row["config_id"] for row in deduplicated] == ["representative", "different"]
    first = deduplicated[0]
    assert first["representative_config_id"] == "representative"
    assert first["equivalent_config_ids"] == ["equivalent", "representative"]
    assert first["equivalence_count"] == 2
    assert first["behavioral_signature"] == "same"
    freeze = create_finalist_freeze(
        campaign_id="dedup", symbol="LINKUSDT", dataset_fingerprint="dataset",
        split_fingerprint="split", baseline_id="set2", search_space_hash="space",
        selection_rule={"ranking": "unchanged"}, ranked_rows=deduplicated,
        finalist_count=2, freeze_timestamp="2026-09-12T00:00:00+00:00",
    )
    assert freeze["finalists"][0]["representative_config_id"] == "representative"
    assert freeze["finalists"][0]["equivalence_count"] == 2
    assert len(freeze["finalists"]) == 2


def test_empty_freeze_skips_holdout_and_policy_fails_closed(tmp_path):
    output = run(_search(tmp_path), run_id="zero-finalists", symbol="LINKUSDT", max_configs=1)
    freeze = json.loads((output / "FINALIST_FREEZE.json").read_text())
    checkpoint = json.loads((output / "CHECKPOINT.json").read_text())
    status = json.loads((output / "STATUS.json").read_text())
    assert freeze["finalists"] == []
    assert freeze["reason"] == "ZERO_ELIGIBLE_VALIDATION_FINALISTS"
    assert checkpoint["campaign_verdict"] == "HOLDOUT_SKIPPED_ZERO_FINALISTS"
    assert checkpoint["holdout_opened"] is checkpoint["holdout_evaluated"] is False
    assert checkpoint["holdout_evaluations"] == checkpoint["holdout_rows_read"] == 0
    assert status["holdout_opened"] is status["holdout_evaluated"] is False
    policy = HoldoutAccessPolicy()
    with pytest.raises(ResearchProtocolError, match="HOLDOUT_ACCESS_BEFORE_FINALIST_FREEZE"):
        policy.holdout_rows([], finalist_id="x", config_hash="x")
    policy.install_freeze(freeze)
    policy.transition(ResearchPhase.HOLDOUT_EVALUATION)
    with pytest.raises(ResearchProtocolError, match="HOLDOUT_SKIPPED_ZERO_FINALISTS"):
        policy.holdout_rows([], finalist_id="x", config_hash="x")


def test_fixed_30_day_window_has_no_future_or_cross_symbol_rows(tmp_path):
    path = _search(tmp_path)
    config = yaml.safe_load(path.read_text())
    rows = []
    seeds = _rows(("LINKUSDT", "BTCUSDT"))
    for symbol in ("LINKUSDT", "BTCUSDT"):
        seed = next(row for row in seeds if row["symbol"] == symbol)
        for day in range(41):
            row = json.loads(json.dumps(seed))
            row.pop("split", None)
            row["position_id"] = f"{symbol}-{day}"
            row["command_id"] = f"{symbol}-{day}"
            row["opened_at_ms"] = day * 86_400_000
            row["closed_at_ms"] = row["opened_at_ms"] + 1_200_000
            row["time_stop_observations"][0]["evaluation_time_ms"] = row["opened_at_ms"] + 600_000
            row["time_stop_observations"][0]["evaluation_closed_until_ms"] = row["opened_at_ms"] + 600_000
            rows.append(row)
    Path(config["dataset"]["source"]).write_text(json.dumps(rows), encoding="utf-8")
    output = run(path, run_id="history-30d", symbol="LINKUSDT", max_configs=1)
    snapshot = json.loads((output / "DATASET_SNAPSHOT.json").read_text())
    manifest = json.loads((output / "DATASET_MANIFEST.json").read_text())
    assert {row["symbol"] for row in snapshot} == {"LINKUSDT"}
    assert manifest["history_target_days"] == 30
    assert manifest["history_actual_days"] >= 30
    assert manifest["history_depth_status"] == "PASS"
    assert min(row["opened_at_ms"] for row in snapshot) >= 10 * 86_400_000
    assert max(row["opened_at_ms"] for row in snapshot) <= 40 * 86_400_000
