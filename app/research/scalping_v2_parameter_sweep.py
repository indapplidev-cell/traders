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
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.config.trade_parameters import CONFIG_PATH, TRADE_PARAMETERS
from app.config.settings import get_settings
from app.db.paper_models import (
    PaperExecutionCommandRecord, PaperOrderRecord, PaperPositionRecord,
    ScalpingOutcomeDiagnosticRecord,
)
from app.engine_orchestrator.orchestrator_models import OnlinePipelineResultRow, OnlinePipelineRun
from app.engine_paper.scalping_policy_v2 import EmpiricalSetupBucket, evaluate_expectancy

SCHEMA_VERSION = "SCALPING_V2_PARAMETER_SWEEP/1"


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _nested(value: object, *path: str) -> object | None:
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _production_rows(maximum_rows: int = 5_000) -> list[dict[str, Any]]:
    """Load bounded, closed PAPER truth using SELECT statements only."""
    database_url = get_settings().database_url
    if not database_url:
        raise RuntimeError("DATABASE_URL is required for the production read-only dataset")
    engine = create_engine(database_url, hide_parameters=True)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    statement = (
        select(PaperPositionRecord, OnlinePipelineResultRow, ScalpingOutcomeDiagnosticRecord)
        .join(PaperOrderRecord, PaperOrderRecord.order_id == PaperPositionRecord.entry_order_id)
        .join(PaperExecutionCommandRecord, PaperExecutionCommandRecord.command_id == PaperOrderRecord.command_id)
        .join(OnlinePipelineRun, OnlinePipelineRun.run_id == PaperExecutionCommandRecord.pipeline_run_id)
        .join(OnlinePipelineResultRow, OnlinePipelineResultRow.run_id == OnlinePipelineRun.run_id)
        .outerjoin(ScalpingOutcomeDiagnosticRecord,
                   ScalpingOutcomeDiagnosticRecord.position_id == PaperPositionRecord.position_id)
        .where(PaperPositionRecord.state == "CLOSED",
               OnlinePipelineRun.trade_profile_id == "trade-5m-v2")
        .order_by(PaperPositionRecord.closed_at.asc())
        .limit(maximum_rows)
    )
    try:
        with factory() as session:
            records = tuple(session.execute(statement))
    finally:
        engine.dispose()
    rows: list[dict[str, Any]] = []
    for position, result, outcome in records:
        diagnostic = _nested(
            result.paper_payload_json, "paper_context", "scalping_geometry_diagnostics"
        ) or {}
        fees = float(position.entry_fees + position.exit_fees)
        net_pnl = float(position.realized_pnl or 0)
        rows.append({
            "position_id": position.position_id,
            "opened_at_ms": int(position.opened_at.timestamp() * 1000),
            "closed_at_ms": int(position.closed_at.timestamp() * 1000),
            "net_pnl": net_pnl, "gross_pnl": net_pnl + fees, "fees": fees,
            "exit_reason": position.reason_code,
            "holding_time_ms": int((position.closed_at - position.opened_at).total_seconds() * 1000),
            "mae": None if outcome is None else float(outcome.mae),
            "mfe": None if outcome is None else float(outcome.mfe),
            "symbol": position.symbol, "direction": position.side,
            "setup_type": _nested(result.setup_payload_json, "setup_type") or "UNKNOWN",
            "session": "UTC", "rejection_reason": diagnostic.get("rejection_reason"),
            "p_win_raw": diagnostic.get("p_win_raw", diagnostic.get("estimated_p_win")),
            "probability_sample_size": diagnostic.get("probability_sample_size", 0),
            "stop_distance_bps": diagnostic.get("stop_distance_bps"),
            "target_distance_bps": diagnostic.get("target_distance_bps"),
            "effective_total_cost_bps": diagnostic.get("effective_total_cost_bps"),
            "adverse_fill_reserve_bps": diagnostic.get("adverse_fill_reserve_bps", 0),
            "entry_slippage_bps": diagnostic.get("entry_slippage_bps", 0),
            "causal_reset_conditions": 1,
            "one_min_confirmation_count": 1,
        })
    return rows


def _load_rows(dataset: str) -> list[dict[str, Any]]:
    if dataset == "postgres-paper-outcomes-readonly":
        return _production_rows()
    value = _json(Path(dataset))
    if not isinstance(value, list):
        raise ValueError("dataset must be a JSON list")
    return value


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
    samples = int(row.get("probability_sample_size", 0))
    raw = row.get("p_win_raw")
    if raw is None:
        # Backward-compatible offline fixtures may carry already-computed EV.
        return (
            float(row.get("expected_ev_r", -1e9)) >= float(config["min_positive_ev_r"])
            and float(row.get("ev_reserve", -1e9)) >= float(config["min_ev_reserve_r"])
            and float(row.get("net_edge_bps", -1e9)) >= float(config["min_net_edge_bps"])
            and samples >= int(config["bucket_min_sample"])
            and float(row.get("stop_distance_bps", 1e9)) <= float(config["stop_max_bps"])
            and float(row.get("target_distance_bps", -1e9)) >= float(config["target_min_bps"])
            and int(row.get("causal_reset_conditions", 0)) >= int(config["causal_reset_min_conditions"])
            and int(row.get("one_min_confirmation_count", 0)) >= int(config["entry_refinement_1m_confirmation_count"])
        )
    target = float(row.get("target_distance_bps") or 0)
    stop = float(row.get("stop_distance_bps") or 0)
    base_cost = float(row.get("effective_total_cost_bps") or 0)
    adjusted_cost = max(0.0, base_cost
        - float(row.get("adverse_fill_reserve_bps") or 0)
        - 2 * float(row.get("entry_slippage_bps") or 0)
        + float(config["adverse_fill_reserve_bps"])
        + 2 * float(config["entry_slippage_bps"]))
    if min(target - adjusted_cost, stop + adjusted_cost) <= 0:
        return False
    bucket = EmpiricalSetupBucket(
        setup_type=str(row.get("setup_type", "UNKNOWN")),
        direction=str(row.get("direction", "UNKNOWN")),
        samples=samples, wins=max(0, min(samples, round(float(raw) * samples))),
        level="historical_authority", bucket_key="historical_authority",
    )
    decision = evaluate_expectancy(
        net_win_bps=target - adjusted_cost, net_loss_bps=stop + adjusted_cost,
        bucket=bucket, minimum_samples=int(config["bucket_min_sample"]),
        minimum_positive_ev_r=float(config["min_positive_ev_r"]),
        minimum_ev_reserve_r=float(config["min_ev_reserve_r"]),
        probability_confidence_level=float(config["probability_confidence_level"]),
        prior_alpha=float(config["prior_alpha"]), prior_beta=float(config["prior_beta"]),
    )
    return (
        decision.admitted
        and target - adjusted_cost >= float(config["min_net_edge_bps"])
        and stop <= float(config["stop_max_bps"])
        and target >= float(config["target_min_bps"])
        and int(row.get("causal_reset_conditions", 0)) >= int(config["causal_reset_min_conditions"])
        and int(row.get("one_min_confirmation_count", 0)) >= int(config["entry_refinement_1m_confirmation_count"])
    )


def _distribution(rows: list[dict[str, Any]], name: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for row in rows:
        key = str(row.get(name, "UNKNOWN"))
        result[key] = result.get(key, 0) + 1
    return dict(sorted(result.items()))


def _optional_mean(rows: list[dict[str, Any]], field: str) -> float | None:
    values = [float(row[field]) for row in rows if row.get(field) is not None]
    return sum(values) / len(values) if values else None


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
        "mae_stats": {"mean": _optional_mean(rows, "mae")},
        "mfe_stats": {"mean": _optional_mean(rows, "mfe")},
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


def run(
    search_path: Path, *, run_id: str | None = None, max_configs: int | None = None,
) -> Path:
    search = yaml.safe_load(search_path.read_text(encoding="utf-8"))
    if search.get("schema_version") != 1 or "risk_per_trade" in search["search_space"]:
        raise ValueError("invalid research search space")
    dataset_source = str(search["dataset"])
    rows = _load_rows(dataset_source)
    splits = _split(rows, int(search["seed"]))
    minimums = search["minimum_samples"]
    results, rejected = [], []
    combinations = _combinations(search["search_space"])
    if max_configs is not None:
        if max_configs <= 0:
            raise ValueError("max_configs must be positive")
        combinations = itertools.islice(combinations, max_configs)
    for params in combinations:
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
        "dataset": dataset_source, "dataset_period": {
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
    parser.add_argument("--max-configs", type=int)
    args = parser.parse_args()
    print(run(args.config, run_id=args.run_id, max_configs=args.max_configs) / "REPORT.md")


if __name__ == "__main__":
    main()
