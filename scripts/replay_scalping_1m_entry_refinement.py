"""Compare persisted 5m-only selections with a causal 1m refinement replay.

The script never generates candidates.  It begins with persisted selector
winners and reads only candles/cost snapshots which were already stored.
Because a historical book snapshot is not available at every later 1m close,
the report explicitly blocks authoritative promotion when that limitation is
present.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
import json
import os
from pathlib import Path
from statistics import mean

from sqlalchemy import create_engine, text

from app.engine_paper.scalping_shadow import compute_net_economics


def _number(value):
    if value is None:
        return None
    return float(value)


def _metrics(rows, *, selected_count, hours):
    positions = [row for row in rows if row.get("position_id")]
    closed = [row for row in positions if row.get("position_state") == "CLOSED"]
    pnl = [_number(row.get("realized_pnl")) or 0.0 for row in closed]
    wins = [value for value in pnl if value > 0]
    losses = [-value for value in pnl if value < 0]
    slippage = [
        abs(_number(row["actual_entry"]) - row["planned_entry"]) / row["planned_entry"] * 10_000
        for row in positions if row.get("actual_entry") is not None and row.get("planned_entry")
    ]
    holding = [
        (row["closed_at"] - row["opened_at"]).total_seconds()
        for row in closed if row.get("closed_at") and row.get("opened_at")
    ]
    return {
        "selected_count": selected_count,
        "trade_count": len(positions),
        "entry_fill_rate": (len(positions) / selected_count if selected_count else None),
        "missed_entry_rate": ((selected_count - len(positions)) / selected_count if selected_count else None),
        "entry_slippage_bps_mean": mean(slippage) if slippage else None,
        "stop_loss_rate": (
            sum(row.get("exit_cause") == "STOP_LOSS" for row in closed) / len(closed)
            if closed else None
        ),
        "take_profit_rate": (
            sum(row.get("exit_cause") == "TAKE_PROFIT" for row in closed) / len(closed)
            if closed else None
        ),
        "holding_time_seconds_mean": mean(holding) if holding else None,
        "net_expectancy_per_trade_usdt": mean(pnl) if pnl else None,
        "net_expectancy_per_hour_usdt": (sum(pnl) / hours if hours > 0 else None),
        "profit_factor": (sum(wins) / sum(losses) if losses else None),
        "win_rate": (len(wins) / len(closed) if closed else None),
        "max_drawdown_usdt": _max_drawdown(pnl),
        "fees_per_trade_usdt": (
            mean((_number(row.get("entry_fees")) or 0) + (_number(row.get("exit_fees")) or 0) for row in closed)
            if closed else None
        ),
        "trades_per_hour": len(positions) / hours if hours > 0 else None,
        "trades_per_day": len(positions) / hours * 24 if hours > 0 else None,
    }


def _max_drawdown(pnl):
    equity = peak = drawdown = 0.0
    for value in pnl:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return drawdown if pnl else None


def _decision(row, candles):
    payload = row["paper_payload"] or {}
    diagnostic = ((payload.get("paper_context") or {}).get("scalping_geometry_diagnostics") or {})
    planned = _number(payload.get("hypothetical_entry_reference") or diagnostic.get("entry"))
    stop = _number(payload.get("hypothetical_stop_level") or diagnostic.get("final_stop"))
    target = _number(payload.get("hypothetical_target_level") or diagnostic.get("causal_target"))
    side = str(payload.get("paper_direction") or "")
    row["planned_entry"] = planned
    row["stop"] = stop
    row["target"] = target
    required = _number(diagnostic.get("required_rr"))
    costs = tuple(_number(diagnostic.get(key)) for key in (
        "entry_fee_bps", "exit_fee_bps", "entry_slippage_bps",
        "exit_slippage_bps", "spread_bps", "depth_impact_bps", "safety_margin_bps",
    ))
    authoritative_costs = bool(
        diagnostic.get("commission_authoritative")
        and diagnostic.get("spread_source") and diagnostic.get("depth_impact_source")
        and all(value is not None for value in costs)
    )
    if not all(value is not None for value in (planned, stop, target, required)):
        return "FAILED", "MISSING_5M_PLAN_FIELDS", None
    started_ms = int(row["selected_at"].timestamp() * 1000)
    valid_until = min(row["approval_valid_until_ms"], row["boundary_closed_at_ms"] + 300_000)
    eligible = [
        value for value in candles
        if value["close_ms"] >= started_ms and value["close_ms"] <= valid_until
        and value["open_ms"] >= row["boundary_closed_at_ms"]
    ]
    if not eligible:
        return "EXPIRED_1M", "ENTRY_REFINEMENT_WINDOW_EXPIRED", None
    expected_up = side == "LONG"
    for candle in eligible:
        bullish = candle["close"] >= candle["open"]
        if bullish != expected_up and candle["close"] != candle["open"]:
            continue
        reference = candle["close"]
        drift = abs(reference - planned) / planned * 10_000
        if drift > 10.0:
            return "REJECTED_1M", "ENTRY_REFINEMENT_PRICE_DRIFT_TOO_LARGE", candle
        if not authoritative_costs:
            return "FAILED", "HISTORICAL_REFINEMENT_COST_SNAPSHOT_UNAVAILABLE", candle
        risk = ((reference - stop) if expected_up else (stop - reference)) / reference * 10_000
        reward = ((target - reference) if expected_up else (reference - target)) / reference * 10_000
        try:
            edge, _effective, net_rr = compute_net_economics(
                gross_reward_bps=reward, gross_risk_bps=risk,
                total_cost_bps=sum(costs),
            )
        except ValueError:
            return "REJECTED_1M", "ENTRY_REFINEMENT_ECONOMICS_INVALIDATED", candle
        if net_rr is None or net_rr < required or edge < 1.0:
            return "REJECTED_1M", "ENTRY_REFINEMENT_ECONOMICS_INVALIDATED", candle
        candle["executed_net_rr"] = net_rr
        candle["executed_net_edge_bps"] = edge
        return "READY_TO_ENTER", "ENTRY_REFINEMENT_CONFIRMED", candle
    return "EXPIRED_1M", "ENTRY_REFINEMENT_WINDOW_EXPIRED", eligible[-1]


def replay(database_url: str) -> dict[str, object]:
    engine = create_engine(database_url, hide_parameters=True, pool_pre_ping=True)
    with engine.connect() as connection:
        raw = connection.execute(text("""
            SELECT o.pipeline_run_id, o.candidate_id, o.symbol,
                   o.boundary_closed_at_ms, o.approval_valid_until_ms,
                   o.first_observed_at AS selected_at, o.lifecycle_state,
                   o.terminal_reason, r.paper_payload_json AS paper_payload,
                   c.command_id, p.position_id, p.state AS position_state,
                   p.average_entry_price AS actual_entry, p.realized_pnl,
                   p.entry_fees, p.exit_fees, p.opened_at, p.closed_at,
                   p.reason_code AS position_reason,
                   x.cause AS exit_cause, x.reason_code AS exit_reason
            FROM paper_plan_execution_outcomes o
            JOIN online_pipeline_results r ON r.run_id = o.pipeline_run_id
            LEFT JOIN paper_execution_commands c ON c.pipeline_run_id = o.pipeline_run_id
            LEFT JOIN paper_orders e ON e.command_id = c.command_id AND e.order_role = 'ENTRY'
            LEFT JOIN paper_positions p ON p.entry_order_id = e.order_id
            LEFT JOIN LATERAL (
                SELECT d.cause, d.reason_code
                FROM paper_exit_decisions d
                WHERE d.position_id = p.position_id
                ORDER BY d.decided_at DESC
                LIMIT 1
            ) x ON TRUE
            WHERE o.trade_profile_id = 'trade-5m-v2' AND o.selected_winner = TRUE
            ORDER BY o.boundary_closed_at_ms, o.pipeline_run_id
        """)).mappings().all()
        rows = [dict(value) for value in raw]
        if not rows:
            return {"verdict": "INCONCLUSIVE", "reason": "NO_PERSISTED_5M_SELECTOR_WINNERS"}
        minimum = min(row["boundary_closed_at_ms"] for row in rows)
        maximum = max(row["approval_valid_until_ms"] for row in rows)
        symbols = tuple(sorted({row["symbol"] for row in rows}))
        candle_rows = connection.execute(text("""
            SELECT symbol, open_time_ms, close_time_ms + 1 AS close_ms,
                   open, high, low, close
            FROM candles_1m
            WHERE symbol = ANY(:symbols) AND open_time_ms >= :minimum - 60000
              AND open_time_ms <= :maximum
            ORDER BY symbol, open_time_ms
        """), {"symbols": list(symbols), "minimum": minimum, "maximum": maximum}).mappings()
        grouped = defaultdict(list)
        for value in candle_rows:
            grouped[value["symbol"]].append({
                "open_ms": value["open_time_ms"], "close_ms": value["close_ms"],
                "open": float(value["open"]), "high": float(value["high"]),
                "low": float(value["low"]), "close": float(value["close"]),
            })
    for row in rows:
        state, reason, candle_value = _decision(row, grouped[row["symbol"]])
        row["refinement_state"] = state
        row["refinement_reason"] = reason
        row["refinement_candle"] = candle_value
    hours = max((maximum - minimum) / 3_600_000, 1 / 60)
    ready = [row for row in rows if row["refinement_state"] == "READY_TO_ENTER"]
    matched_ready = [row for row in ready if row.get("position_id")]
    counts = {state: sum(row["refinement_state"] == state for row in rows) for state in (
        "READY_TO_ENTER", "REJECTED_1M", "EXPIRED_1M", "FAILED"
    )}
    limitation = any(row["refinement_reason"] == "HISTORICAL_REFINEMENT_COST_SNAPSHOT_UNAVAILABLE" for row in rows)
    return {
        "schema": "TRADERS_SCALPING_V2_1M_ENTRY_REFINEMENT_REPLAY/1",
        "source": "PERSISTED_5M_SELECTOR_WINNERS_ONLY",
        "candidate_generation": "FORBIDDEN_AND_NOT_PERFORMED",
        "candidate_count": len(rows), "selected_count": len(rows),
        "same_candidate_identity_comparison": True,
        "period_hours": hours,
        "baseline_5m_only": _metrics(rows, selected_count=len(rows), hours=hours),
        "five_min_plus_one_min_refinement": {
            **_metrics(matched_ready, selected_count=len(rows), hours=hours),
            "refinement_decision_count": len(ready),
            "outcome_metrics_population": "READY_WITH_OBSERVED_BASELINE_POSITION_ONLY",
        },
        "refinement_counts": counts,
        "refinement_reject_rate": counts["REJECTED_1M"] / len(rows),
        "refinement_expire_rate": counts["EXPIRED_1M"] / len(rows),
        "historical_dynamic_cost_coverage_complete": not limitation,
        "counterfactual_fill_model_complete": False,
        "promotion_decision": "SHADOW",
        "verdict": "INCONCLUSIVE",
        "reason": "COUNTERFACTUAL_FILLS_AND_EXACT_REFINEMENT_TIME_BOOK_SNAPSHOTS_ARE_NOT_COMPLETE",
        "records": [
            {
                "pipeline_run_id": row["pipeline_run_id"],
                "candidate_id": row["candidate_id"], "symbol": row["symbol"],
                "boundary_closed_at_ms": row["boundary_closed_at_ms"],
                "refinement_state": row["refinement_state"],
                "refinement_reason": row["refinement_reason"],
            }
            for row in rows
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    report = replay(database_url)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps({key: report.get(key) for key in (
        "verdict", "promotion_decision", "candidate_count", "refinement_counts"
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
