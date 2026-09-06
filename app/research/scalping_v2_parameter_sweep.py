"""Manual deterministic offline parameter sweep for Scalping v2."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import itertools
import json
from pathlib import Path
import random
import subprocess
from typing import Any, Iterable

import yaml

from app.config.trade_parameters import CONFIG_PATH, TRADE_PARAMETERS

SCHEMA_VERSION = "SCALPING_V2_PARAMETER_SWEEP/1"


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _config_hash(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, text=True,
        capture_output=True,
    ).stdout.strip()


def _combinations(space: dict[str, list[object]]) -> Iterable[dict[str, object]]:
    names = tuple(sorted(space))
    for values in itertools.product(*(space[name] for name in names)):
        yield dict(zip(names, values, strict=True))


def _split(rows: list[dict[str, Any]], seed: int) -> dict[str, list[dict[str, Any]]]:
    if rows and all(row.get("split") in {"CALIBRATION", "VALIDATION", "HOLDOUT"} for row in rows):
        return {name: [row for row in rows if row["split"] == name] for name in (
            "CALIBRATION", "VALIDATION", "HOLDOUT"
        )}
    ordered = sorted(rows, key=lambda row: (row.get("closed_at_ms", 0), row.get("position_id", "")))
    random.Random(seed).shuffle(ordered)
    a, b = int(len(ordered) * .6), int(len(ordered) * .8)
    return {"CALIBRATION": ordered[:a], "VALIDATION": ordered[a:b], "HOLDOUT": ordered[b:]}


def _admitted(row: dict[str, Any], config: dict[str, object]) -> bool:
    return (
        float(row.get("expected_ev_r", -1e9)) >= float(config["min_positive_ev_r"])
        and float(row.get("ev_reserve", -1e9)) >= float(config["min_ev_reserve_r"])
        and float(row.get("net_edge_bps", -1e9)) >= float(config["min_net_edge_bps"])
        and int(row.get("probability_sample_size", 0)) >= int(config["bucket_min_sample"])
        and float(row.get("stop_distance_bps", 1e9)) <= float(config["stop_max_bps"])
        and float(row.get("target_distance_bps", -1e9)) >= float(config["target_min_bps"])
        and int(row.get("causal_reset_conditions", 0)) >= int(config["causal_reset_min_conditions"])
        and int(row.get("one_min_confirmation_count", 0)) >= int(config["entry_refinement_1m_confirmation_count"])
    )


def _distribution(rows: list[dict[str, Any]], name: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for row in rows:
        key = str(row.get(name, "UNKNOWN"))
        result[key] = result.get(key, 0) + 1
    return dict(sorted(result.items()))


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(rows)
    pnl = [float(row.get("net_pnl", 0)) for row in rows]
    gross = [float(row.get("gross_pnl", value + float(row.get("fees", 0)))) for row, value in zip(rows, pnl)]
    fees = [float(row.get("fees", 0)) for row in rows]
    wins = [value for value in pnl if value > 0]
    losses = [-value for value in pnl if value < 0]
    curve = peak = drawdown = 0.0
    for value in pnl:
        curve += value
        peak = max(peak, curve)
        drawdown = max(drawdown, peak - curve)
    hours = 0.0 if not rows else max(0.0, (
        max(float(row.get("closed_at_ms", 0)) for row in rows)
        - min(float(row.get("opened_at_ms", row.get("closed_at_ms", 0))) for row in rows)
    ) / 3_600_000)
    avg_win = sum(wins) / len(wins) if wins else None
    avg_loss = sum(losses) / len(losses) if losses else None
    gross_profit, gross_loss = sum(wins), sum(losses)
    return {
        "trade_count": count, "trades_per_hour": count / hours if hours else None,
        "trades_per_day": count / hours * 24 if hours else None,
        "win_rate": len(wins) / count if count else None,
        "average_win": avg_win, "average_loss": avg_loss,
        "payoff_ratio": avg_win / avg_loss if avg_win is not None and avg_loss else None,
        "gross_pnl": sum(gross), "fees": sum(fees), "net_pnl": sum(pnl),
        "net_expectancy_per_trade": sum(pnl) / count if count else None,
        "net_expectancy_per_hour": sum(pnl) / hours if hours else None,
        "profit_factor": gross_profit / gross_loss if gross_loss else None,
        "max_drawdown": drawdown,
        "fee_to_gross_edge_ratio": sum(fees) / abs(sum(gross)) if sum(gross) else None,
        "stop_hit_rate": sum(row.get("exit_reason") == "STOP" for row in rows) / count if count else None,
        "target_hit_rate": sum(row.get("exit_reason") == "TARGET" for row in rows) / count if count else None,
        "average_holding_time": sum(float(row.get("holding_time_ms", 0)) for row in rows) / count if count else None,
        "mae_stats": {"mean": sum(float(row.get("mae", 0)) for row in rows) / count if count else None},
        "mfe_stats": {"mean": sum(float(row.get("mfe", 0)) for row in rows) / count if count else None},
        "symbol_distribution": _distribution(rows, "symbol"),
        "direction_distribution": _distribution(rows, "direction"),
        "setup_distribution": _distribution(rows, "setup_type"),
        "session_distribution": _distribution(rows, "session"),
        "rejection_reasons": _distribution(rows, "rejection_reason"),
    }


def _pareto(results: list[dict[str, Any]]) -> list[str]:
    frontier = []
    for row in results:
        m = row["validation"]
        dominated = any(
            other is not row
            and (other["validation"]["net_expectancy_per_trade"] or -1e99) >= (m["net_expectancy_per_trade"] or -1e99)
            and (other["validation"]["max_drawdown"] or 1e99) <= (m["max_drawdown"] or 1e99)
            and (other["validation"]["trade_count"] or 0) >= (m["trade_count"] or 0)
            for other in results
        )
        if not dominated:
            frontier.append(row["config_hash"])
    return frontier


def run(search_path: Path, *, run_id: str | None = None) -> Path:
    search = yaml.safe_load(search_path.read_text(encoding="utf-8"))
    if search.get("schema_version") != 1 or "risk_per_trade" in search["search_space"]:
        raise ValueError("invalid research search space")
    dataset_path = Path(search["dataset"])
    rows = _json(dataset_path)
    if not isinstance(rows, list):
        raise ValueError("dataset must be a JSON list")
    splits = _split(rows, int(search["seed"]))
    minimums = search["minimum_samples"]
    results, rejected = [], []
    for params in _combinations(search["search_space"]):
        item = {"parameters": params, "config_hash": _config_hash(params)}
        statuses = {}
        for name in ("CALIBRATION", "VALIDATION", "HOLDOUT"):
            admitted = [row for row in splits[name] if _admitted(row, params)]
            key = name.lower()
            item[key] = _metrics(admitted)
            statuses[key] = "PASS" if len(admitted) >= int(minimums[key]) else "INSUFFICIENT_SAMPLE"
        item["split_status"] = statuses
        (results if statuses["calibration"] == statuses["validation"] == "PASS" else rejected).append(item)
    # Holdout is reported but intentionally absent from ranking keys.
    ranked = sorted(results, key=lambda row: (
        row["validation"]["net_expectancy_per_trade"] or -1e99,
        row["validation"]["profit_factor"] or -1e99,
        -(row["validation"]["max_drawdown"] or 1e99),
    ), reverse=True)
    identifier = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = Path(search["output_root"]) / identifier
    output.mkdir(parents=True, exist_ok=False)
    run_config = {
        "schema_version": SCHEMA_VERSION, "seed": search["seed"],
        "dataset": str(dataset_path), "dataset_period": {
            "from_ms": min((row.get("opened_at_ms") for row in rows), default=None),
            "to_ms": max((row.get("closed_at_ms") for row in rows), default=None),
        }, "sample_sizes": {key: len(value) for key, value in splits.items()},
        "source_data_provenance": _config_hash(rows),
        "authoritative_trade_parameters": str(CONFIG_PATH),
        "baseline_config_hash": TRADE_PARAMETERS.config_hash,
        "search_space_config": str(search_path), "git_commit": _git_commit(),
        "production_mutations": 0, "binance_order_api_calls": 0,
    }
    (output / "RUN_CONFIG.yaml").write_text(yaml.safe_dump(run_config, sort_keys=False), encoding="utf-8")
    all_results = results + rejected
    (output / "RESULTS.json").write_text(json.dumps(all_results, indent=2, sort_keys=True), encoding="utf-8")
    flat = [{"config_hash": row["config_hash"], **row["parameters"],
             **{f"validation_{k}": v for k, v in row["validation"].items() if not isinstance(v, dict)}} for row in all_results]
    with (output / "RESULTS.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=sorted({key for row in flat for key in row}))
        writer.writeheader(); writer.writerows(flat)
    top = {"ranked_without_holdout": ranked[:10], "pareto_frontier": _pareto(results)}
    (output / "TOP_CONFIGS.json").write_text(json.dumps(top, indent=2, sort_keys=True), encoding="utf-8")
    (output / "REJECTED_CONFIGS.json").write_text(json.dumps(rejected, indent=2, sort_keys=True), encoding="utf-8")
    report = (
        "# Scalping v2 parameter sweep\n\n"
        f"- Schema: `{SCHEMA_VERSION}`\n- Git: `{run_config['git_commit']}`\n"
        f"- Baseline config hash: `{TRADE_PARAMETERS.config_hash}`\n"
        f"- Dataset rows: {len(rows)}; tested configurations: {len(all_results)}\n"
        f"- Calibration/validation accepted: {len(results)}; rejected or insufficient: {len(rejected)}\n"
        "- Holdout was reported and was not used for ranking.\n"
        "- Small samples are marked `INSUFFICIENT_SAMPLE`; no result is invented.\n"
        "- Full metrics and every configuration are in RESULTS.json/RESULTS.csv.\n"
    )
    (output / "REPORT.md").write_text(report, encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    print(run(args.config, run_id=args.run_id) / "REPORT.md")


if __name__ == "__main__":
    main()
