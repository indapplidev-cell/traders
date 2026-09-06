"""Manual deterministic offline parameter sweep for Scalping v2."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
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

from app.config.trade_parameters import (
    CONFIG_PATH, SCALPING_V2, TRADE_PARAMETERS, StalePositionPolicyParameters,
)
from app.config.settings import get_settings
from app.db.paper_models import (
    PaperExecutionCommandRecord, PaperOrderRecord, PaperPositionRecord,
    ScalpingOutcomeDiagnosticRecord,
)
from app.engine_orchestrator.orchestrator_models import OnlinePipelineResultRow, OnlinePipelineRun
from app.engine_paper.scalping_policy_v2 import EmpiricalSetupBucket, evaluate_expectancy
from app.engine_paper.stale_position_shadow import (
    StalePositionInputs, evaluate_stale_position_shadow,
)

SCHEMA_VERSION = "SCALPING_V2_PARAMETER_SWEEP/2"
TIME_STOP_SEARCH_FIELDS = frozenset({
    "soft_timeout_seconds", "hard_timeout_seconds",
    "min_target_progress_at_soft_timeout", "min_mfe_bps_at_soft_timeout",
    "min_remaining_ev_r_at_soft_timeout", "extension_seconds", "max_extensions",
    "break_even_activation_target_progress", "net_break_even_protection_enabled",
})


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
            "entry_price": float(position.average_entry_price),
            "quantity": float(position.entry_quantity),
            "stop_price": float(position.stop_price),
            "target_price": float(position.target_price),
            "entry_fee_incurred": float(position.entry_fees),
            # Historical closed rows without timestamped market/cost observations
            # remain explicitly unreplayable; current commission is never substituted.
            "time_stop_observations": [],
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


def _stale_policy(config: dict[str, object]) -> StalePositionPolicyParameters:
    payload = SCALPING_V2.exit_policy.stale_position.model_dump(mode="python")
    payload.update({name: config[name] for name in TIME_STOP_SEARCH_FIELDS})
    return StalePositionPolicyParameters.model_validate(payload)


def _utc_from_ms(value: object) -> datetime:
    return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)


def _historical_input(
    row: dict[str, Any], observation: dict[str, Any], *, extension_count: int,
) -> StalePositionInputs | None:
    required = (
        "evaluation_time_ms", "evaluation_closed_until_ms", "current_price",
        "highs", "lows", "exit_commission_bps", "spread_bps",
        "slippage_bps", "adverse_exit_reserve_bps", "commission_source",
    )
    if observation.get("historical_cost_evidence") is not True:
        return None
    if any(observation.get(name) is None for name in required):
        return None
    try:
        opened_ms = int(row["opened_at_ms"])
        evaluation_ms = int(observation["evaluation_time_ms"])
        closed_until_ms = int(observation["evaluation_closed_until_ms"])
        if not (opened_ms < closed_until_ms <= evaluation_ms <= int(row["closed_at_ms"])):
            return None
        highs = tuple(Decimal(str(value)) for value in observation["highs"])
        lows = tuple(Decimal(str(value)) for value in observation["lows"])
        if not highs or not lows:
            return None
        return StalePositionInputs(
            position_id=str(row["position_id"]), symbol=str(row["symbol"]),
            side=str(row["direction"]), opened_at=_utc_from_ms(opened_ms),
            evaluation_time=_utc_from_ms(evaluation_ms),
            evaluation_closed_until_ms=closed_until_ms,
            entry_price=Decimal(str(row["entry_price"])),
            current_price=Decimal(str(observation["current_price"])),
            quantity=Decimal(str(row["quantity"])),
            stop_price=Decimal(str(row["stop_price"])),
            target_price=Decimal(str(row["target_price"])),
            entry_fee_incurred=Decimal(str(row["entry_fee_incurred"])),
            exit_commission_bps=Decimal(str(observation["exit_commission_bps"])),
            spread_bps=Decimal(str(observation["spread_bps"])),
            slippage_bps=Decimal(str(observation["slippage_bps"])),
            adverse_exit_reserve_bps=Decimal(str(observation["adverse_exit_reserve_bps"])),
            highs=highs, lows=lows,
            setup_valid=observation.get("setup_valid"),
            momentum_valid=observation.get("momentum_valid"),
            remaining_ev_r=(
                None if observation.get("remaining_ev_r") is None
                else Decimal(str(observation["remaining_ev_r"]))
            ),
            extension_count=extension_count,
            commission_provenance={
                "source": str(observation["commission_source"]),
                "historical": True,
            },
        )
    except (KeyError, TypeError, ValueError, ArithmeticError):
        return None


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


def _percentile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = index - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _replay_time_stop(
    row: dict[str, Any], policy: StalePositionPolicyParameters,
    *, config_hash: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    observations = row.get("time_stop_observations")
    state = {
        "status": "UNREPLAYABLE", "soft": False, "hard": False,
        "exit": False, "break_even": False, "seconds_saved": 0.0,
        "blocked_candidates": None, "unblocked_candidates": None,
    }
    if not isinstance(observations, list) or not observations:
        return dict(row), state
    extension_count = 0
    decision = None
    try:
        opened_ms = int(row["opened_at_ms"])
        actual_close_ms = int(row["closed_at_ms"])
        ordered = sorted(
            (
                item for item in observations
                if isinstance(item, dict)
                and opened_ms < int(item.get("evaluation_closed_until_ms", -1))
                <= int(item.get("evaluation_time_ms", -1)) <= actual_close_ms
            ),
            key=lambda item: int(item["evaluation_closed_until_ms"]),
        )
    except (TypeError, ValueError):
        ordered = []
    if not ordered:
        state["status"] = "INSUFFICIENT_DATA"
        return dict(row), state
    for observation in ordered:
        inputs = _historical_input(row, observation, extension_count=extension_count)
        if inputs is None:
            state["status"] = "INSUFFICIENT_DATA"
            return dict(row), state
        decision = evaluate_stale_position_shadow(
            inputs, policy=policy, config_hash=config_hash,
        )
        extension_count = decision.extension_count
        state["soft"] = bool(state["soft"] or decision.soft_timeout_reached)
        state["hard"] = bool(state["hard"] or decision.hard_timeout_reached)
        if decision.shadow_decision == "HYPOTHETICAL_EXIT":
            break
    if decision is None:
        state["status"] = "INSUFFICIENT_DATA"
        return dict(row), state
    state["status"] = "REPLAYED"
    if decision.shadow_decision != "HYPOTHETICAL_EXIT":
        return dict(row), state
    replayed = dict(row)
    replayed.update({
        "closed_at_ms": int(decision.evaluated_at.timestamp() * 1000),
        "holding_time_ms": decision.holding_seconds * 1000,
        "net_pnl": float(decision.shadow_net_pnl),
        "gross_pnl": float(decision.shadow_gross_pnl),
        "fees": float(decision.shadow_fees),
        "exit_reason": decision.shadow_exit_reason,
    })
    state["exit"] = True
    state["break_even"] = decision.shadow_exit_reason == "TIME_STOP_SHADOW_BREAK_EVEN_PROTECT"
    state["seconds_saved"] = max(
        0.0, (float(row["closed_at_ms"]) - replayed["closed_at_ms"]) / 1000,
    )
    candidates = row.get("causal_later_candidates")
    if isinstance(candidates, list) and all(
        isinstance(item, dict) and item.get("candidate_time_ms") is not None
        for item in candidates
    ):
        baseline_close = int(row["closed_at_ms"])
        exit_ms = int(replayed["closed_at_ms"])
        blocked = [
            item for item in candidates
            if int(row["opened_at_ms"]) < int(item["candidate_time_ms"]) <= baseline_close
        ]
        state["blocked_candidates"] = len(blocked)
        state["unblocked_candidates"] = sum(
            exit_ms < int(item["candidate_time_ms"]) <= baseline_close
            for item in blocked
        )
    return replayed, state


def _time_stop_metrics(
    rows: list[dict[str, Any]], config: dict[str, object], *, config_hash: str,
) -> dict[str, Any]:
    policy = _stale_policy(config)
    outcomes = [
        _replay_time_stop(row, policy, config_hash=config_hash) for row in rows
    ]
    replayed = [row for row, _state in outcomes]
    states = [state for _row, state in outcomes]
    baseline = _metrics(rows)
    time_stop = _metrics(replayed)
    holding_seconds = [float(row.get("holding_time_ms", 0)) / 1000 for row in replayed]
    evidence_states = [
        state for state in states if state["blocked_candidates"] is not None
    ]
    result = {
        **time_stop,
        "baseline": baseline,
        "time_stop": time_stop,
        "time_stop_exit_count": sum(bool(state["exit"]) for state in states),
        "soft_timeout_count": sum(bool(state["soft"]) for state in states),
        "hard_timeout_count": sum(bool(state["hard"]) for state in states),
        "break_even_protection_count": sum(bool(state["break_even"]) for state in states),
        "average_holding_seconds": (
            sum(holding_seconds) / len(holding_seconds) if holding_seconds else None
        ),
        "baseline_average_holding_seconds": (
            None if baseline["average_holding_time"] is None
            else baseline["average_holding_time"] / 1000
        ),
        "holding_p50": _percentile(holding_seconds, .50),
        "holding_p90": _percentile(holding_seconds, .90),
        "baseline_net_pnl": baseline["net_pnl"],
        "time_stop_net_pnl": time_stop["net_pnl"],
        "net_pnl_delta": time_stop["net_pnl"] - baseline["net_pnl"],
        "baseline_net_expectancy": baseline["net_expectancy_per_trade"],
        "time_stop_net_expectancy": time_stop["net_expectancy_per_trade"],
        "expectancy_delta": (
            None if baseline["net_expectancy_per_trade"] is None
            or time_stop["net_expectancy_per_trade"] is None else
            time_stop["net_expectancy_per_trade"] - baseline["net_expectancy_per_trade"]
        ),
        "baseline_profit_factor": baseline["profit_factor"],
        "time_stop_profit_factor": time_stop["profit_factor"],
        "baseline_max_drawdown": baseline["max_drawdown"],
        "time_stop_max_drawdown": time_stop["max_drawdown"],
        "fees_total": time_stop["fees"],
        "baseline_fees_total": baseline["fees"],
        "fees_per_trade": time_stop["fees"] / len(replayed) if replayed else None,
        "fee_drag_delta": time_stop["fees"] - baseline["fees"],
        "stale_position_seconds_saved": sum(float(state["seconds_saved"]) for state in states),
        "capacity_seconds_saved": sum(float(state["seconds_saved"]) for state in states),
        "candidates_blocked_while_position_open": (
            sum(int(state["blocked_candidates"]) for state in evidence_states)
            if evidence_states else None
        ),
        "hypothetical_candidates_unblocked_after_stale_exit": (
            sum(int(state["unblocked_candidates"]) for state in evidence_states)
            if evidence_states else None
        ),
        "replay_status": _distribution(states, "status"),
    }
    return result


def _pareto(results: list[dict[str, Any]]) -> list[str]:
    frontier = []
    for row in results:
        m = row["validation"]
        dominated = any(
            other is not row
            and (other["validation"]["net_expectancy_per_trade"] or -1e99) >= (m["net_expectancy_per_trade"] or -1e99)
            and (other["validation"]["max_drawdown"] or 1e99) <= (m["max_drawdown"] or 1e99)
            and (other["validation"]["trade_count"] or 0) >= (m["trade_count"] or 0)
            and (
                (other["validation"]["net_expectancy_per_trade"] or -1e99) > (m["net_expectancy_per_trade"] or -1e99)
                or (other["validation"]["max_drawdown"] or 1e99) < (m["max_drawdown"] or 1e99)
                or (other["validation"]["trade_count"] or 0) > (m["trade_count"] or 0)
            )
            for other in results
        )
        if not dominated:
            frontier.append(row["config_hash"])
    return frontier


def run(
    search_path: Path, *, run_id: str | None = None, max_configs: int | None = None,
) -> Path:
    search = yaml.safe_load(search_path.read_text(encoding="utf-8"))
    space = search.get("search_space")
    if (
        search.get("schema_version") != 2
        or not isinstance(space, dict)
        or "risk_per_trade" in space
        or not TIME_STOP_SEARCH_FIELDS.issubset(space)
        or any(not isinstance(values, list) or not values for values in space.values())
    ):
        raise ValueError("invalid research search space")
    dataset_source = str(search["dataset"])
    rows = _load_rows(dataset_source)
    splits = _split(rows, int(search["seed"]))
    minimums = search["minimum_samples"]
    results, rejected = [], []
    combinations = _combinations(space)
    if max_configs is not None:
        if max_configs <= 0:
            raise ValueError("max_configs must be positive")
        combinations = itertools.islice(combinations, max_configs)
    for params in combinations:
        item = {"parameters": params, "config_hash": _config_hash(params)}
        try:
            _stale_policy(params)
        except (TypeError, ValueError) as error:
            item["invalid_reason"] = str(error)
            item["split_status"] = {
                name: "INVALID_CONFIG" for name in ("calibration", "validation", "holdout")
            }
            for name in ("calibration", "validation", "holdout"):
                item[name] = _metrics([])
            rejected.append(item)
            continue
        statuses = {}
        for name in ("CALIBRATION", "VALIDATION", "HOLDOUT"):
            admitted = [row for row in splits[name] if _admitted(row, params)]
            key = name.lower()
            item[key] = _time_stop_metrics(
                admitted, params, config_hash=item["config_hash"],
            )
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
        "time_stop_policy_schema": "StalePositionPolicyParameters",
        "time_stop_evaluator": "app.engine_paper.stale_position_shadow.evaluate_stale_position_shadow",
        "search_space_config": str(search_path), "git_commit": _git_commit(),
        "production_mutations": 0, "production_config_writes": 0,
        "approvals_created": 0, "commands_created": 0, "positions_created": 0,
        "binance_order_api_calls": 0,
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
    report_lines = [
        "# Scalping v2 parameter sweep\n\n"
        f"- Schema: `{SCHEMA_VERSION}`\n- Git: `{run_config['git_commit']}`\n"
        f"- Baseline config hash: `{TRADE_PARAMETERS.config_hash}`\n"
        f"- Dataset rows: {len(rows)}; tested configurations: {len(all_results)}\n"
        f"- Calibration/validation accepted: {len(results)}; rejected or insufficient: {len(rejected)}\n"
        "- Holdout was reported and was not used for ranking.\n"
        "- Small samples are marked `INSUFFICIENT_SAMPLE`; no result is invented.\n"
        "- Missing historical timestamped cost/market evidence is `UNREPLAYABLE` or `INSUFFICIENT_DATA`.\n"
        "- Full metrics and every configuration are in RESULTS.json/RESULTS.csv.\n\n"
        "## TIME-STOP / STALE-POSITION ANALYSIS\n\n"
        "Runtime and replay share `StalePositionPolicyParameters` and "
        "`evaluate_stale_position_shadow`; current commissions never replace historical evidence.\n\n"
    ]
    for item in all_results:
        report_lines.append(
            f"### `{item['config_hash']}`\n\n"
            f"- Parameters: `{json.dumps(item['parameters'], sort_keys=True)}`\n"
            f"- Sample sufficiency: `{json.dumps(item['split_status'], sort_keys=True)}`\n"
        )
        if item.get("invalid_reason"):
            report_lines.append(f"- Invalid configuration: `{item['invalid_reason']}`\n\n")
            continue
        for split_name in ("calibration", "validation", "holdout"):
            metrics = item[split_name]
            report_lines.append(
                f"- {split_name}: baseline PnL={metrics['baseline_net_pnl']}; "
                f"time-stop PnL={metrics['time_stop_net_pnl']}; "
                f"expectancy baseline/time-stop={metrics['baseline_net_expectancy']}/"
                f"{metrics['time_stop_net_expectancy']}; "
                f"PF baseline/time-stop={metrics['baseline_profit_factor']}/"
                f"{metrics['time_stop_profit_factor']}; "
                f"drawdown baseline/time-stop={metrics['baseline_max_drawdown']}/"
                f"{metrics['time_stop_max_drawdown']}; "
                f"holding baseline/avg/p50/p90={metrics['baseline_average_holding_seconds']}/"
                f"{metrics['average_holding_seconds']}/"
                f"{metrics['holding_p50']}/{metrics['holding_p90']}; "
                f"fees baseline/time-stop/delta={metrics['baseline_fees_total']}/"
                f"{metrics['fees_total']}/{metrics['fee_drag_delta']}; "
                f"stale/soft/hard/break-even counts={metrics['time_stop_exit_count']}/"
                f"{metrics['soft_timeout_count']}/{metrics['hard_timeout_count']}/"
                f"{metrics['break_even_protection_count']}; "
                f"capacity seconds saved={metrics['capacity_seconds_saved']}; "
                f"replay={json.dumps(metrics['replay_status'], sort_keys=True)}\n"
            )
        report_lines.append("\n")
    report_lines.append(
        "## Pareto frontier\n\n"
        f"Validation-only frontier: `{json.dumps(top['pareto_frontier'])}`. "
        "Holdout is not ranked.\n"
    )
    (output / "REPORT.md").write_text("".join(report_lines), encoding="utf-8")
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
