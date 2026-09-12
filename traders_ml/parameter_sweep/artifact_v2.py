"""Compact, reproducible Parameter Sweep artifact schema v2.

The module is intentionally independent from the evaluator.  It converts legacy
or current in-memory evaluation payloads into one compact row per configuration,
keeps detailed trades only for finalists, and resolves market paths from the
immutable dataset snapshot.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import statistics
import csv
import io
import uuid
from typing import Any, Iterable, Mapping

from app.config.yaml_authority import (
    RESEARCH_PARAMETERS, VALIDATION_SAMPLE_POLICY, ValidationSamplePolicy,
)
from .artifact_writer import ArtifactWriter, DEFAULT_ARTIFACT_WRITER


ARTIFACT_SCHEMA_VERSION = 2
RESULT_ARTIFACT = "RESULTS.jsonl"
FORBIDDEN_INLINE_FIELDS = frozenset({
    "market_path_1m", "candles", "snapshots", "full_trade_path",
    "opportunities", "trades",
})


class ArtifactSizeBudgetExceeded(RuntimeError):
    pass


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(payload.encode("utf-8")).hexdigest()


def _median(rows: Iterable[Mapping[str, Any]], *names: str) -> float | None:
    values = [float(row[name]) for row in rows for name in names if row.get(name) is not None]
    return statistics.median(values) if values else None


def _mean(rows: Iterable[Mapping[str, Any]], *names: str) -> float | None:
    values = [float(row[name]) for row in rows for name in names if row.get(name) is not None]
    return statistics.fmean(values) if values else None


def performance_class(
    metrics: Mapping[str, Any], *, stability: float | None = None,
    validation_policy: ValidationSamplePolicy = VALIDATION_SAMPLE_POLICY,
) -> str:
    policy = RESEARCH_PARAMETERS.ranking
    trades = int(metrics.get("trade_count") or 0)
    expectancy = metrics.get("expectancy_R", metrics.get("net_expectancy_per_trade"))
    profit_factor = metrics.get("profit_factor")
    symbols = metrics.get("symbol_coverage")
    independent_periods = metrics.get("independent_period_count")
    if metrics.get("invalid_reason"):
        return "INVALID"
    if (
        trades < validation_policy.minimum_validation_trades
        or int(symbols or 0) < 1
        or independent_periods is None
        or int(independent_periods) < validation_policy.minimum_independent_periods
    ):
        return "INSUFFICIENT_SAMPLE"
    if expectancy is None or float(expectancy) < 0:
        return "NEGATIVE_EXPECTANCY"
    if float(expectancy) < policy.promising_min_expectancy_r or float(profit_factor or 0) < policy.promising_min_profit_factor:
        return "WEAK"
    if stability is not None and stability >= policy.validation_candidate_min_stability:
        return "VALIDATION_CANDIDATE"
    return "PROMISING_RESEARCH"


def compact_result(
    item: Mapping[str, Any], *, dataset_manifest_ref: str = "DATASET_MANIFEST.json",
    baseline_set_id: str | None = None, baseline_config_hash: str | None = None,
    research_config_hash: str | None = None,
    validation_policy: ValidationSamplePolicy = VALIDATION_SAMPLE_POLICY,
) -> dict[str, Any]:
    """Return a v2 row with no market data or detailed trade payloads."""
    validation = dict(item.get("validation") or {})
    trade_records_present = isinstance(validation.get("trades"), list)
    trades = list(validation.get("trades") or [])
    wins = sum(float(t.get("net_pnl", 0)) > 0 for t in trades) if trade_records_present else int(validation.get("wins") or 0)
    losses = sum(float(t.get("net_pnl", 0)) < 0 for t in trades) if trade_records_present else int(validation.get("losses") or 0)
    trade_count = len(trades) if trade_records_present else int(validation.get("trade_count") or 0)
    funnel = dict(validation.get("funnel") or {})
    candidate_count = int(item.get("INPUT_ROWS") or sum(funnel.values()) or 0)
    rr_pass = int(funnel.get("PASSED_ROWS") or trade_count)
    symbols = {
        str(trade["symbol"]) for trade in trades
        if trade.get("symbol") not in (None, "")
    } if trade_records_present else set(validation.get("symbol_distribution") or ())
    setups = {
        str(trade.get("setup_type") or "UNKNOWN") for trade in trades
    } if trade_records_present else set(validation.get("setup_distribution") or ())
    regimes = {
        str(trade.get("regime") or "UNKNOWN") for trade in trades
    } if trade_records_present else set(validation.get("regime_distribution") or ())
    period_buckets: list[str] = []
    period_status = "COMPLETE"
    if trade_records_present:
        for trade in trades:
            timestamp = trade.get("opened_at_ms", trade.get("boundary_ms"))
            if timestamp is None:
                period_status = "DATA_INCOMPLETE"
                period_buckets = []
                break
            period_buckets.append(
                datetime.fromtimestamp(int(timestamp) / 1000, timezone.utc).date().isoformat()
            )
        independent_periods: int | None = (
            len(set(period_buckets)) if period_status == "COMPLETE" else None
        )
    else:
        raw_periods = validation.get("independent_period_count")
        independent_periods = None if raw_periods is None else int(raw_periods)
        period_status = str(validation.get("independent_period_status") or (
            "COMPLETE" if raw_periods is not None else "DATA_INCOMPLETE"
        ))
    overrides = dict(item.get("overrides") or item.get("parameters") or {})
    candidate_parameters = dict(item.get("candidate_parameters") or overrides)
    behavioral_signature = canonical_hash([
        {
            "trade_identity": trade.get("causal_opportunity") or trade.get("candidate_id") or trade.get("position_id"),
            "entry_timestamp": trade.get("opened_at_ms", trade.get("boundary_ms")),
            "exit_timestamp": trade.get("closed_at_ms", trade.get("exit_time_ms")),
            "side": trade.get("side", trade.get("direction")),
            "entry_outcome": trade.get("entry_status", "TRADE"),
            "exit_outcome": trade.get("exit_status", trade.get("exit_reason")),
            "net_pnl": trade.get("net_pnl"),
            "r_outcome": trade.get("realized_r", trade.get("net_rr")),
            "terminal_reason": trade.get("exit_reason", trade.get("reason")),
        }
        for trade in sorted(
            trades,
            key=lambda value: (
                int(value.get("opened_at_ms", value.get("boundary_ms", 0)) or 0),
                str(value.get("causal_opportunity") or value.get("candidate_id") or value.get("position_id") or ""),
            ),
        )
    ])
    metrics = {
        "trade_count": trade_count,
        "win_count": wins,
        "loss_count": losses,
        "win_rate": validation.get("win_rate"),
        "gross_pnl": validation.get("gross_pnl"),
        "net_pnl": validation.get("net_pnl"),
        "expectancy_R": validation.get("expectancy_R", validation.get("net_expectancy_per_trade")),
        "profit_factor": validation.get("profit_factor"),
        "max_drawdown": validation.get("max_drawdown"),
        "mean_net_rr": validation.get("mean_net_rr", _mean(trades, "net_rr")),
        "median_net_rr": validation.get("median_net_rr", _median(trades, "net_rr")),
        "mean_required_rr": validation.get("mean_required_rr", _mean(trades, "required_rr")),
        "median_required_rr": validation.get("median_required_rr", _median(trades, "required_rr")),
        "rr_pass_rate": validation.get("rr_pass_rate", rr_pass / candidate_count if candidate_count else None),
        "candidate_count": candidate_count,
        "opportunity_count": int(item.get("INPUT_ROWS") or candidate_count),
        "candidate_frequency": validation.get("candidate_frequency"),
        "trade_frequency": validation.get("trades_per_hour", validation.get("trade_frequency")),
        "cost_burden": validation.get("fee_to_gross_edge_ratio", validation.get("average_cost_per_trade")),
        "symbol_coverage": len(symbols) if trade_records_present else int(validation.get("symbol_coverage") or len(symbols)),
        "setup_coverage": len(setups) if trade_records_present else int(validation.get("setup_coverage") or len(setups)),
        "regime_coverage": len(regimes) if trade_records_present else int(validation.get("regime_coverage") or len(regimes)),
        "independent_period_count": independent_periods,
    }
    evaluation_status = {
        "ACCEPTED": "ACCEPTED", "REJECTED": "REJECTED",
        "EARLY_REJECTED": "REJECTED", "PRUNED_INVALID": "ERROR",
    }.get(str(item.get("result_status")), str(item.get("evaluation_status") or "ERROR"))
    metrics["invalid_reason"] = item.get("invalid_reason")
    slice_count = sum(
        int((item.get(name) or {}).get("trade_count") or 0) > 0
        for name in ("calibration", "validation")
    )
    gates = [
        ("validation_trade_count", trade_count, validation_policy.minimum_validation_trades),
        ("symbol_coverage", metrics["symbol_coverage"], 1),
        ("independent_period_count", independent_periods, validation_policy.minimum_independent_periods),
        ("minimum_slice_count", slice_count, 2),
    ]
    failed_gates = [
        {
            "gate": gate, "current": current, "required": required,
            "deficit": None if current is None else max(0, required - current),
            "status": "DATA_INCOMPLETE" if current is None else "BELOW_MINIMUM",
        }
        for gate, current, required in gates if current is None or current < required
    ]
    return {
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        "config_index": int(item.get("config_index", item.get("result_index", 0))),
        "config_id": str(item.get("config_id", item.get("config_hash") or canonical_hash(overrides))),
        "baseline_set_id": baseline_set_id or RESEARCH_PARAMETERS.calibration.baseline_set_id,
        "baseline_config_hash": baseline_config_hash,
        "research_config_hash": research_config_hash,
        "resolved_seed": item.get("resolved_seed"),
        "symbol": item.get("symbol"),
        "SYMBOL": item.get("symbol"),
        "evaluated_symbol_count": item.get("evaluated_symbol_count", 1),
        "symbol_coverage_expected": 1,
        "symbol_coverage_pass": int(metrics["symbol_coverage"] or 0) == 1,
        "validation_behavioral_signature": behavioral_signature,
        "minimum_slice_count": slice_count,
        "overrides": overrides,
        "candidate_parameters": candidate_parameters,
        "stage": item.get("stage"),
        "evaluation_status": evaluation_status,
        "performance_class": performance_class(metrics, validation_policy=validation_policy),
        "independent_period_status": period_status,
        "independent_period_unit": validation_policy.independent_period_unit,
        "independent_period_buckets": sorted(set(period_buckets)),
        "insufficient_sample_gates": failed_gates,
        **{key: value for key, value in metrics.items() if key != "invalid_reason"},
        "key_rejection_distribution": dict(sorted(funnel.items())),
        "replay_status": dict(sorted((validation.get("replay_status") or {}).items())),
        "cost_source_class": validation.get("cost_source_class", item.get("cost_source_class", "FROZEN_DATASET_POLICY")),
        "dataset_manifest_ref": dataset_manifest_ref,
        "trade_summary_ref": "FINALIST_TRADES.jsonl",
    }


def canonical_validation_projection(row: Mapping[str, Any]) -> dict[str, Any]:
    """Project readiness from one canonical compact validation result."""
    symbol_coverage = int(row.get("symbol_coverage") or 0)
    return {
        "config_id": row.get("config_id"),
        "validation_trade_count": int(row.get("trade_count") or 0),
        "symbol_coverage": symbol_coverage,
        "symbol_coverage_expected": 1,
        "symbol_coverage_pass": symbol_coverage == 1,
        "independent_period_count": row.get("independent_period_count"),
        "setup_coverage": int(row.get("setup_coverage") or 0),
        "regime_coverage": int(row.get("regime_coverage") or 0),
        "performance_class": row.get("performance_class"),
        "evaluation_status": row.get("evaluation_status"),
        "validation_readiness_pass": not bool(row.get("insufficient_sample_gates")),
        "minimum_slice_count": int(row.get("minimum_slice_count") or 0),
    }


def _readiness_from_projection(
    projection: Mapping[str, Any],
    validation_policy: ValidationSamplePolicy = VALIDATION_SAMPLE_POLICY,
) -> dict[str, dict[str, Any]]:
    requirements = {
        "validation_trade_count": validation_policy.minimum_validation_trades,
        "symbol_coverage": 1,
        "independent_period_count": validation_policy.minimum_independent_periods,
        "setup_coverage": 1,
        "minimum_slice_count": 2,
    }
    return {
        name: {
            "current": projection.get(name), "required": required,
            "pass": projection.get(name) is not None and projection.get(name) >= required,
        }
        for name, required in requirements.items()
    }


def aggregate_result_semantics(
    rows: Iterable[Mapping[str, Any]], *, error_count: int = 0,
    validation_policy: ValidationSamplePolicy = VALIDATION_SAMPLE_POLICY,
) -> dict[str, Any]:
    """Canonical counters shared by status, reports, CLI and GUI events."""
    values = list(rows)
    evaluation_counts: dict[str, int] = {"ACCEPTED": 0, "REJECTED": 0, "ERROR": int(error_count)}
    performance_counts: dict[str, int] = {}
    for row in values:
        evaluation = str(row.get("evaluation_status") or "ERROR")
        evaluation_counts[evaluation] = evaluation_counts.get(evaluation, 0) + 1
        classification = str(row.get("performance_class") or "INVALID")
        performance_counts[classification] = performance_counts.get(classification, 0) + 1
    canonical_row = max(
        values, key=lambda row: (int(row.get("config_index") or 0), str(row.get("config_id") or "")),
        default={},
    )
    projection = canonical_validation_projection(canonical_row)
    readiness = _readiness_from_projection(projection, validation_policy)
    promotable = performance_counts.get("VALIDATION_CANDIDATE", 0)
    return {
        "evaluated_configs": len(values),
        "evaluation_status_counts": dict(sorted(evaluation_counts.items())),
        "performance_class_counts": dict(sorted(performance_counts.items())),
        "classification_counts": dict(sorted(performance_counts.items())),
        "accepted_configs": evaluation_counts.get("ACCEPTED", 0),
        "rejected_configs": evaluation_counts.get("REJECTED", 0),
        "error_configs": evaluation_counts.get("ERROR", 0),
        "insufficient_configs": performance_counts.get("INSUFFICIENT_SAMPLE", 0),
        "candidate_promotion_eligible": promotable > 0,
        "promotable_candidate_count": promotable,
        "validation_readiness": dict(sorted(readiness.items())),
        "canonical_validation": projection,
    }


def build_opportunity_funnel(
    results: Iterable[Mapping[str, Any]], *, counterfactual_count: int,
    counterfactual_examples: Iterable[Mapping[str, Any]], error_count: int = 0,
    validation_policy: ValidationSamplePolicy = VALIDATION_SAMPLE_POLICY,
) -> dict[str, Any]:
    """Build the funnel exclusively from canonical compact result rows."""
    rows = list(results)
    resolved_seeds = {row.get("resolved_seed") for row in rows}
    configs = []
    aggregate: dict[str, int] = {}
    for row in rows:
        rejection = dict(row.get("key_rejection_distribution") or {})
        for key, value in rejection.items():
            aggregate[key] = aggregate.get(key, 0) + int(value)
        configs.append({
            "config_index": row.get("config_index"),
            "config_id": row.get("config_id"),
            "parameters": dict(row.get("overrides") or {}),
            "status": row.get("evaluation_status"),
            "performance_class": row.get("performance_class"),
            "validation_funnel": rejection,
            "validation_trade_count": int(row.get("trade_count") or 0),
            "rejection_distribution": rejection,
        })
    required = (
        "config_index", "config_id", "parameters", "status", "performance_class",
        "validation_funnel", "validation_trade_count", "rejection_distribution",
    )
    if any(any(item.get(key) is None for key in required) for item in configs):
        raise ValueError("FUNNEL_ARTIFACT_INCOMPLETE")
    return {
        "RUN_AGGREGATION": aggregate_result_semantics(
            rows, error_count=error_count, validation_policy=validation_policy,
        ),
        "RESOLVED_SEED": next(iter(resolved_seeds)) if len(resolved_seeds) == 1 else None,
        "AGGREGATE_FUNNEL": dict(sorted(aggregate.items())),
        "AGGREGATE_FUNNEL_SEMANTICS": "SUM_OF_PER_CONFIG_VALIDATION_FUNNELS",
        "CONFIG_RESULTS": configs,
        "COUNTERFACTUAL_REJECTED_OPPORTUNITIES_SIMULATED": int(counterfactual_count),
        "COUNTERFACTUAL_EXAMPLES": list(counterfactual_examples),
    }


def make_market_path_ref(
    dataset_manifest_hash: str, trade: Mapping[str, Any], path: list[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "dataset_manifest_hash": dataset_manifest_hash,
        "symbol": trade.get("symbol"),
        "start_boundary": min((int(row.get("close_time_ms", row.get("boundary_ms", 0))) for row in path), default=trade.get("opened_at_ms")),
        "end_boundary": max((int(row.get("close_time_ms", row.get("boundary_ms", 0))) for row in path), default=trade.get("closed_at_ms")),
        "resolution": "1m",
        "path_slice_identity": canonical_hash(path),
    }


def resolve_market_path(reference: Mapping[str, Any], dataset_rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    symbol = reference.get("symbol")
    start, end = int(reference["start_boundary"]), int(reference["end_boundary"])
    candidates: list[Mapping[str, Any]] = []
    for row in dataset_rows:
        nested = row.get("market_path_1m")
        if isinstance(nested, list) and row.get("symbol") == symbol:
            candidates.extend(item for item in nested if isinstance(item, dict))
        elif row.get("symbol") == symbol:
            candidates.append(row)
    result = [dict(row) for row in candidates if start <= int(row.get("close_time_ms", row.get("boundary_ms", -1))) <= end]
    if canonical_hash(result) != reference.get("path_slice_identity"):
        raise ValueError("MARKET_PATH_REF_MISMATCH")
    return result


def compact_trade(trade: Mapping[str, Any], dataset_manifest_hash: str) -> dict[str, Any]:
    result = {key: value for key, value in trade.items() if key not in FORBIDDEN_INLINE_FIELDS}
    result["setup_type"] = str(trade.get("setup_type") or "UNKNOWN")
    path = list(trade.get("market_path_1m") or [])
    if path:
        result["market_path_ref"] = make_market_path_ref(dataset_manifest_hash, trade, path)
    return result


def recursive_inline_market_path_count(value: object) -> int:
    if isinstance(value, dict):
        return int("market_path_1m" in value) + sum(recursive_inline_market_path_count(v) for v in value.values())
    if isinstance(value, list):
        return sum(recursive_inline_market_path_count(v) for v in value)
    return 0


def artifact_sizes(directory: Path) -> dict[str, int]:
    files = [path for path in directory.rglob("*") if path.is_file() and not path.name.startswith(".")]
    return {
        "TOTAL_ARTIFACT_BYTES": sum(path.stat().st_size for path in files),
        "RESULTS_BYTES": (directory / RESULT_ARTIFACT).stat().st_size if (directory / RESULT_ARTIFACT).exists() else 0,
        "FINALIST_BYTES": (directory / "FINALIST_TRADES.jsonl").stat().st_size if (directory / "FINALIST_TRADES.jsonl").exists() else 0,
        "DATASET_BYTES": (directory / "DATASET_SNAPSHOT.json").stat().st_size if (directory / "DATASET_SNAPSHOT.json").exists() else 0,
    }


def enforce_size_budget(directory: Path) -> dict[str, int | bool]:
    sizes = artifact_sizes(directory)
    policy = RESEARCH_PARAMETERS.artifact
    status = {
        **sizes,
        "SOFT_BUDGET_PASS": sizes["TOTAL_ARTIFACT_BYTES"] <= policy.soft_total_bytes and sizes["RESULTS_BYTES"] <= policy.soft_results_bytes,
        "HARD_BUDGET_PASS": sizes["TOTAL_ARTIFACT_BYTES"] <= policy.hard_total_bytes and sizes["RESULTS_BYTES"] <= policy.hard_results_bytes,
    }
    if not status["HARD_BUDGET_PASS"]:
        raise ArtifactSizeBudgetExceeded("ARTIFACT_SIZE_BUDGET_EXCEEDED")
    return status


def iter_results(path: Path) -> Iterable[dict[str, Any]]:
    """Read v1 or v2 JSONL transparently."""
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            yield item if item.get("artifact_schema_version") == 2 else compact_result(item)


@dataclass(frozen=True, slots=True)
class MigrationReport:
    source_rows: int
    target_rows: int
    source_bytes: int
    target_bytes: int
    inline_market_path_count: int
    dry_run: bool


def migrate_v1_run(source: Path, target: Path, *, dry_run: bool = False, writer: ArtifactWriter | None = None) -> MigrationReport:
    """Create a new v2 directory atomically; the v1 source is never modified."""
    rows = []
    source_results = source / RESULT_ARTIFACT
    with source_results.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(compact_result(json.loads(line)))
    rendered = "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows)
    report = MigrationReport(len(rows), len(rows), source_results.stat().st_size, len(rendered.encode()), sum(recursive_inline_market_path_count(row) for row in rows), dry_run)
    if dry_run:
        return report
    if target.exists():
        raise FileExistsError(target)
    temporary = target.parent / f".{target.name}.{uuid.uuid4().hex}.migrating"
    temporary.mkdir(parents=True)
    artifact_writer = writer or DEFAULT_ARTIFACT_WRITER
    try:
        artifact_writer.atomic_text(temporary / RESULT_ARTIFACT, rendered, operation="v1_v2_results")
        for name in ("DATASET_MANIFEST.json", "DATASET_SNAPSHOT.json"):
            if (source / name).is_file():
                shutil.copy2(source / name, temporary / name)
        artifact_writer.atomic_json(temporary / "RUN_MANIFEST.json", {
            "artifact_schema_version": 2,
            "migration_source": str(source),
            "source_results_sha256": sha256(source_results.read_bytes()).hexdigest(),
            "row_count": len(rows),
        }, operation="v1_v2_manifest")
        artifact_writer.atomic_text(temporary / "ACCEPTED_CONFIGS.jsonl", "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows if r["evaluation_status"] == "ACCEPTED"), operation="v1_v2_accepted")
        artifact_writer.atomic_text(temporary / "REJECTED_CONFIGS.jsonl", "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows if r["evaluation_status"] != "ACCEPTED"), operation="v1_v2_rejected")
        artifact_writer.atomic_text(temporary / "FINALIST_TRADES.jsonl", "", operation="v1_v2_finalists")
        buffer = io.StringIO(newline="")
        csv_writer = csv.DictWriter(buffer, fieldnames=("config_index", "config_id", "stage", "evaluation_status", "performance_class", "trade_count", "expectancy_R", "profit_factor", "max_drawdown", "overrides_json"))
        csv_writer.writeheader()
        for row in rows:
            csv_writer.writerow({**{key: row.get(key) for key in csv_writer.fieldnames if key != "overrides_json"}, "overrides_json": json.dumps(row["overrides"], sort_keys=True)})
        artifact_writer.atomic_text(temporary / "RESULTS.csv", buffer.getvalue(), operation="v1_v2_csv")
        from .ranking import pareto_frontier, rank_results
        ranked = rank_results(rows)[: RESEARCH_PARAMETERS.artifact.top_config_count]
        artifact_writer.atomic_json(temporary / "TOP_CONFIGS.json", {"artifact_schema_version": 2, "ranked_without_holdout": ranked, "pareto_frontier": pareto_frontier(ranked)}, operation="v1_v2_top")
        artifact_writer.atomic_json(temporary / "CHECKPOINT.json", {"artifact_schema_version": 2, "STATUS": "COMPLETED", "evaluated_count": len(rows), "durable_result_count": len(rows)}, operation="v1_v2_checkpoint")
        artifact_writer.atomic_text(temporary / "ERRORS.jsonl", "\n", operation="v1_v2_errors")
        artifact_writer.atomic_text(temporary / "REPORT.md", f"# Parameter Sweep v2 migration\n\n- Source: `{source}`\n- Rows: {len(rows)}\n- Original remains untouched: `YES`\n", operation="v1_v2_report")
        os.replace(temporary, target)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return report
