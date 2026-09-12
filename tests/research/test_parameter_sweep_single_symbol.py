import json
from pathlib import Path

import pytest
import yaml

from app.config.yaml_authority import RESEARCH_PARAMETERS
from traders_ml.parameter_sweep.artifact_v2 import compact_result
from traders_ml.parameter_sweep.cli import build_parser
from traders_ml.parameter_sweep.controller import ParameterSweepController
from traders_ml.parameter_sweep.engine import SweepExpectedError, _evaluate_config, run
from traders_ml.parameter_sweep.universe import (
    resolve_parameter_sweep_universe,
    validate_parameter_sweep_symbol,
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
