"""Print a compact out-of-sample threshold probe for a frozen bull-run dataset."""

from __future__ import annotations

import argparse
from pathlib import Path

from traders_ml.parameter_sweep.bull_run_weights import (
    BullRunEvent,
    CalibrationRequest,
    ScoreThresholds,
    WeightConfiguration,
    _split_rows,
    load_dataset,
    replay_configuration,
    trade_metrics,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    args = parser.parse_args()
    request = CalibrationRequest.model_validate_json(args.request.read_text(encoding="utf-8"))
    _, _, observations = load_dataset(args.dataset)
    events = [BullRunEvent.model_validate_json(line) for line in args.events.read_bytes().splitlines()]
    for entry_threshold in (90, 92, 94, 96, 98, 99):
        for exit_threshold in (55, 65, 75, 85):
            config = WeightConfiguration(thresholds=ScoreThresholds(
                entry=entry_threshold, at_risk=50, exit=exit_threshold,
                strong_reversal=max(exit_threshold, 85),
            ))
            values = []
            for split in ("SEARCH", "VALIDATION", "HOLDOUT"):
                rows, labels = _split_rows(request, observations, events, split)
                trades, _ = replay_configuration(
                    rows, labels, config,
                    confirmation_boundaries=request.confirmation_boundaries,
                    maximum_holding_minutes=request.maximum_holding_minutes,
                    initial_capital=request.initial_capital,
                    risk_per_trade_bps=request.risk_per_trade_bps,
                    maximum_open_positions=request.maximum_open_positions,
                )
                metrics = trade_metrics(trades)
                values.append({
                    "trades": metrics["closed_trades"],
                    "net": round(metrics["net_pnl"], 6),
                    "pf": round(metrics["profit_factor"], 4),
                    "wr": round(metrics["win_rate"], 4),
                    "days": metrics["independent_days"],
                })
            print(entry_threshold, exit_threshold, values, flush=True)


if __name__ == "__main__":
    main()
