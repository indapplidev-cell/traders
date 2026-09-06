import json
from pathlib import Path

import yaml

from app.research.scalping_v2_parameter_sweep import run


def test_two_variant_smoke_generates_complete_report_without_production_mutation(tmp_path):
    rows = []
    for index, split in enumerate(("CALIBRATION", "CALIBRATION", "VALIDATION", "VALIDATION", "HOLDOUT", "HOLDOUT")):
        rows.append({
            "position_id": f"p{index}", "split": split, "opened_at_ms": index * 1000,
            "closed_at_ms": index * 1000 + 500, "expected_ev_r": .2,
            "ev_reserve": .3, "net_edge_bps": 20, "probability_sample_size": 50,
            "stop_distance_bps": 40, "target_distance_bps": 80,
            "causal_reset_conditions": 1, "one_min_confirmation_count": 1,
            "net_pnl": 1 if index % 2 == 0 else -.5, "gross_pnl": 1.2,
            "fees": .2, "exit_reason": "TARGET" if index % 2 == 0 else "STOP",
            "holding_time_ms": 500, "mae": 2, "mfe": 4, "symbol": "BTCUSDT",
            "direction": "LONG", "setup_type": "BREAKOUT", "session": "UTC",
        })
    dataset = tmp_path / "dataset.json"
    dataset.write_text(json.dumps(rows), encoding="utf-8")
    search = {
        "schema_version": 1, "seed": 1, "dataset": str(dataset), "output_root": str(tmp_path / "artifacts"),
        "minimum_samples": {"calibration": 2, "validation": 2, "holdout": 2},
        "search_space": {
            "min_positive_ev_r": [0, .1], "min_ev_reserve_r": [0], "min_net_edge_bps": [1],
            "bucket_min_sample": [20], "probability_confidence_level": [.95],
            "prior_alpha": [1], "prior_beta": [1], "adverse_fill_reserve_bps": [3],
            "entry_slippage_bps": [2], "stop_max_bps": [50], "target_min_bps": [45],
            "causal_reset_min_conditions": [1], "entry_refinement_1m_confirmation_count": [1],
        },
    }
    search_path = tmp_path / "search.yaml"
    search_path.write_text(yaml.safe_dump(search), encoding="utf-8")
    output = run(search_path, run_id="smoke")
    expected = {"RUN_CONFIG.yaml", "RESULTS.csv", "RESULTS.json", "TOP_CONFIGS.json", "REJECTED_CONFIGS.json", "REPORT.md"}
    assert {path.name for path in output.iterdir()} == expected
    assert len(json.loads((output / "RESULTS.json").read_text())) == 2
    run_config = yaml.safe_load((output / "RUN_CONFIG.yaml").read_text())
    assert run_config["production_mutations"] == 0
    assert run_config["binance_order_api_calls"] == 0
