"""Read-only, causal replay of persisted 5m geometry against closed level maps.

The script uses only fixed local PostgreSQL container access, never inspects a
container environment, and never calls an exchange, Control, or an order API.
Future candles are loaded only after the decision has been fixed and solely for
offline outcome diagnostics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from app.engine_analysis.analysis_contract import AnalysisWindowConfig
from app.engine_analysis.engine import run_engine_analysis
from app.engine_analysis.schemas import EngineAnalysisCandle
from app.engine_observation.scalping_calibration import distribution
from app.engine_orchestrator.runtime_parameters import resolve_runtime_parameters
from app.engine_paper.scalping_shadow import (
    CausalTarget,
    ShadowCostInputs,
    ShadowGeometryCandidate,
    ShadowGeometryConfig,
    evaluate_scalping_shadow,
)

CONTAINER = "traders-ml-postgres-1"
PROFILE = "trade-5m-v1"
TABLE = {"5m": "candles_5m", "15m": "candles_15m", "1h": "candles_1h"}


def _psql(sql: str) -> list[dict[str, Any]]:
    result = subprocess.run(
        ["docker", "exec", "--user", "postgres", CONTAINER, "psql", "-U",
         "traders_ml", "-d", "traders_ml", "-AtX", "-c", sql],
        check=True, capture_output=True, text=True, encoding="utf-8",
    )
    return [json.loads(line) for line in result.stdout.splitlines() if line.strip()]


def load_candidates(start_ms: int, end_ms: int, parameter_set_id: str) -> list[dict[str, Any]]:
    return _psql(f"""
SELECT jsonb_build_object(
 'run_id',r.run_id,'boundary',r.closed_until_ms,'symbol',r.symbol,
 'parameter_set_id',coalesce(res.paper_payload_json::jsonb->>'runtime_parameter_set_id',
                             res.analysis_payload_json::jsonb->>'runtime_parameter_set_id'),
 'direction',res.risk_payload_json::jsonb->>'direction_hint',
 'setup_type',res.setup_payload_json::jsonb->>'setup_type',
 'diagnostic',res.paper_payload_json::jsonb#>'{{paper_context,scalping_geometry_diagnostics}}'
)::text
FROM online_pipeline_runs r JOIN online_pipeline_results res USING(run_id)
WHERE r.trade_profile_id='{PROFILE}'
  AND r.closed_until_ms BETWEEN {int(start_ms)} AND {int(end_ms)}
  AND coalesce(res.paper_payload_json::jsonb->>'runtime_parameter_set_id',
               res.analysis_payload_json::jsonb->>'runtime_parameter_set_id')='{parameter_set_id}'
  AND res.paper_payload_json::jsonb#>>'{{paper_context,scalping_geometry_diagnostics,entry}}' IS NOT NULL
ORDER BY r.closed_until_ms,r.symbol
""")


def load_candles(symbol: str, timeframe: str, boundary_ms: int, *, limit: int = 96) -> list[EngineAnalysisCandle]:
    rows = _psql(f"""
SELECT jsonb_build_object(
 'timestamp',open_time_utc,'open',open,'high',high,'low',low,'close',close,'volume',volume
)::text FROM (
 SELECT open_time_utc,open,high,low,close,volume,open_time_ms
 FROM {TABLE[timeframe]}
 WHERE symbol='{symbol}' AND is_closed=true AND close_time_ms < {int(boundary_ms)}
 ORDER BY open_time_ms DESC LIMIT {int(limit)}
) q ORDER BY open_time_ms
""")
    return [EngineAnalysisCandle(
        timestamp=str(row["timestamp"]), open=float(row["open"]), high=float(row["high"]),
        low=float(row["low"]), close=float(row["close"]), volume=float(row["volume"]),
    ) for row in rows]


def load_future_candles(symbol: str, boundary_ms: int, horizon_minutes: int = 60) -> list[dict[str, Any]]:
    return _psql(f"""
SELECT jsonb_build_object(
 'open_time_ms',open_time_ms,'close_time_ms',close_time_ms,
 'high',high,'low',low,'close',close
)::text
FROM candles_5m
WHERE symbol='{symbol}' AND is_closed=true
  AND open_time_ms >= {int(boundary_ms)}
  AND open_time_ms < {int(boundary_ms + horizon_minutes * 60_000)}
ORDER BY open_time_ms
""")


def _offline_outcome(row: dict[str, Any], horizon_minutes: int = 60) -> dict[str, Any]:
    entry = float(row["entry"])
    stop = float(row["stop"])
    target = float(row["target"])
    bullish = row["direction"] == "BULLISH"
    mfe = mae = 0.0
    outcome = "NEITHER"
    exit_minutes = None
    for candle in load_future_candles(str(row["symbol"]), int(row["boundary"]), horizon_minutes):
        high, low = float(candle["high"]), float(candle["low"])
        favorable = high - entry if bullish else entry - low
        adverse = entry - low if bullish else high - entry
        mfe = max(mfe, favorable / entry * 10_000)
        mae = max(mae, adverse / entry * 10_000)
        target_hit = high >= target if bullish else low <= target
        stop_hit = low <= stop if bullish else high >= stop
        if target_hit or stop_hit:
            outcome = (
                "STOP_HIT_BEFORE_TARGET_CONSERVATIVE_AMBIGUOUS"
                if target_hit and stop_hit
                else "TARGET_HIT_BEFORE_STOP" if target_hit
                else "STOP_HIT_BEFORE_TARGET"
            )
            exit_minutes = (int(candle["close_time_ms"]) + 1 - int(row["boundary"])) / 60_000
            break
    gross = (
        float(row["target_distance_bps"])
        if outcome == "TARGET_HIT_BEFORE_STOP"
        else -float(row["stop_distance_bps"])
        if outcome.startswith("STOP_HIT") else 0.0
    )
    return {
        "opportunity_id": row["opportunity_id"],
        "symbol": row["symbol"], "boundary": row["boundary"],
        "horizon_minutes": horizon_minutes, "outcome": outcome,
        "time_to_exit_minutes": exit_minutes,
        "mfe_bps": round(mfe, 8), "mae_bps": round(mae, 8),
        "gross_outcome_bps": round(gross, 8),
        "estimated_net_outcome_bps": round(gross - float(row["total_cost_bps"]), 8),
    }


def _level_candidates(symbol: str, boundary_ms: int, entry: float) -> list[CausalTarget]:
    runtime = resolve_runtime_parameters(PROFILE)
    values: list[CausalTarget] = []
    for timeframe in ("5m", "15m", "1h"):
        candles = load_candles(symbol, timeframe, boundary_ms)
        if len(candles) < 64:
            continue
        output = run_engine_analysis(
            symbol, timeframe, candles,
            config=AnalysisWindowConfig(
                minimum_candles=64, context_candles=min(96, len(candles)),
                decision_candles=runtime.analysis_decision_candles,
                confirmation_candles=runtime.confirmation_window_candles,
                atr_lookback_candles=runtime.atr_lookback_candles,
                impulse_lookback_candles=runtime.impulse_lookback_candles,
                structure_lookback_candles=runtime.structure_lookback_candles,
                volume_baseline_candles=runtime.volume_baseline_candles,
                breakout_volume_baseline_candles=runtime.breakout_volume_baseline_candles,
            ),
        )
        context = output.json_payload.get("analysis_context", {})
        indicators = context.get("technical_indicators", {}) if isinstance(context, dict) else {}
        atr = indicators.get("atr_14") if isinstance(indicators, dict) else None
        for side in ("support", "resistance"):
            candidates = context.get(f"causal_{side}_candidates", []) if isinstance(context, dict) else []
            for raw in candidates if isinstance(candidates, list) else []:
                if not isinstance(raw, dict) or raw.get("price") is None:
                    continue
                price = float(raw["price"])
                achievable = True
                if timeframe == "1h":
                    achievable = bool(atr and float(atr) > 0 and abs(price - entry) <= float(atr))
                values.append(CausalTarget(
                    price=price, source_type=str(raw["source_type"]), known_at_ms=boundary_ms,
                    validated=bool(raw.get("validated")),
                    relevant=bool(raw.get("still_relevant", True)), achievable=achievable,
                    timeframe=timeframe, source_detail=str(raw.get("source_detail") or "UNKNOWN"),
                ))
    return values


def _number(value: object) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def replay(rows: list[dict[str, Any]]) -> dict[str, Any]:
    outputs = []
    for row in rows:
        diagnostic = row.get("diagnostic") or {}
        entry = _number(diagnostic.get("entry"))
        if entry is None or row.get("direction") not in {"BULLISH", "BEARISH"}:
            continue
        targets = _level_candidates(str(row["symbol"]), int(row["boundary"]), entry)
        costs = ShadowCostInputs(
            entry_fee_bps=_number(diagnostic.get("entry_fee_bps")) or 0,
            exit_fee_bps=_number(diagnostic.get("exit_fee_bps")) or 0,
            entry_slippage_bps=_number(diagnostic.get("entry_slippage_bps")) or 0,
            exit_slippage_bps=_number(diagnostic.get("exit_slippage_bps")) or 0,
            safety_margin_bps=_number(diagnostic.get("safety_margin_bps")) or 0,
            spread_bps=_number(diagnostic.get("spread_bps")),
            depth_impact_bps=_number(diagnostic.get("depth_impact_bps")),
            spread_source=str(diagnostic.get("spread_source") or "PERSISTED_DECISION_BOUNDARY"),
            depth_impact_source=str(diagnostic.get("depth_impact_source") or "PERSISTED_DECISION_BOUNDARY"),
            spread_authoritative=diagnostic.get("spread_bps") is not None,
            depth_authoritative=diagnostic.get("depth_impact_bps") is not None,
        )
        edge_cohorts = {}
        primary = None
        for minimum_edge in (0.0, 5.0, 10.0):
            value = evaluate_scalping_shadow(
                ShadowGeometryCandidate(
                    trade_profile_id=PROFILE, symbol=str(row["symbol"]),
                    boundary_ms=int(row["boundary"]), direction=str(row["direction"]),
                    entry=entry, causal_invalidation=_number(diagnostic.get("causal_invalidation")),
                    atr=_number(diagnostic.get("atr")), targets=tuple(targets),
                    setup_identity=str(row.get("setup_type") or "UNKNOWN"),
                ),
                costs,
                ShadowGeometryConfig(.25, 80.0, 45.0, minimum_positive_edge_bps=minimum_edge),
            )
            edge_cohorts[str(minimum_edge)] = {
                "actionable": value.economically_actionable_target_exists,
                "rr_1_0": value.rr_cohorts_net.get("1.00", False),
                "rr_1_2": value.rr_cohorts_net.get("1.20", False),
                "rr_1_5": value.rr_cohorts_net.get("1.50", False),
                "valid_plan": value.valid_plan,
            }
            if minimum_edge == 5.0:
                primary = value
        assert primary is not None
        outputs.append({
            "run_id": row["run_id"], "boundary": row["boundary"], "symbol": row["symbol"],
            "opportunity_id": primary.opportunity_id,
            "direction": row["direction"], "entry": primary.entry,
            "stop": primary.final_stop, "target": primary.causal_target,
            "target_trace": primary.target_considerations,
            "first_causal_target": primary.first_causal_target,
            "first_actionable_target": primary.first_actionable_target,
            "target_candidates_considered": primary.target_candidates_considered,
            "selected_target_source": primary.target_source_type,
            "stop_distance_bps": primary.stop_distance_bps,
            "target_distance_bps": primary.target_distance_bps,
            "total_cost_bps": primary.total_cost_bps,
            "expected_net_edge_bps": primary.expected_net_edge_bps,
            "gross_rr": primary.gross_rr, "net_rr": primary.net_rr,
            "break_even_win_rate": primary.break_even_win_rate,
            "rejection_stage": primary.rejection_stage,
            "rejection_reason": primary.rejection_reason,
            "edge_cohorts": edge_cohorts,
        })
    sources = Counter(
        trace["target_source"] for row in outputs for trace in row["target_trace"]
        if trace.get("causal_valid") and trace.get("direction_valid") and trace.get("still_relevant")
    )
    actionable_sources = Counter(
        row["first_actionable_target"]["target_source"]
        for row in outputs if row["first_actionable_target"] is not None
    )
    local_non_actionable = sum(
        trace.get("target_source") == "LOCAL_5M" and not trace.get("actionable")
        and trace.get("causal_valid") and trace.get("direction_valid")
        for row in outputs for trace in row["target_trace"]
    )
    unique_rows: dict[str, dict[str, Any]] = {}
    for row in sorted(outputs, key=lambda item: item["boundary"]):
        if row["first_actionable_target"] is not None:
            unique_rows.setdefault(str(row["opportunity_id"]), row)
    outcome_horizons = {
        str(minutes): [_offline_outcome(row, minutes) for row in unique_rows.values()]
        for minutes in (15, 30, 60)
    }
    outcomes = outcome_horizons["60"]
    wins = [row for row in outcomes if row["outcome"] == "TARGET_HIT_BEFORE_STOP"]
    losses = [row for row in outcomes if row["outcome"].startswith("STOP_HIT")]
    completed = [*wins, *losses]
    win_total = sum(max(0.0, row["estimated_net_outcome_bps"]) for row in wins)
    loss_total = abs(sum(min(0.0, row["estimated_net_outcome_bps"]) for row in losses))
    return {
        "schema": "traders-5m-causal-target-replay-v1",
        "execution_authority": "NONE",
        "future_data_used_in_decision": False,
        "candidate_rows": len(outputs),
        "unique_opportunities": len({row["opportunity_id"] for row in outputs}),
        "offline_completed_unique_opportunities": len(completed),
        "shadow_win_rate": len(wins) / len(completed) if completed else None,
        "shadow_profit_factor": win_total / loss_total if loss_total else None,
        "shadow_net_expectancy_bps": (
            sum(row["estimated_net_outcome_bps"] for row in completed) / len(completed)
            if completed else None
        ),
        "target_candidates_considered": sum(row["target_candidates_considered"] for row in outputs),
        "causal_target_source_histogram": dict(sources),
        "actionable_target_source_histogram": dict(actionable_sources),
        "local_target_non_actionable_count": local_non_actionable,
        "next_local_target_actionable_count": actionable_sources["LOCAL_5M"],
        "structural_target_actionable_count": actionable_sources["STRUCTURAL"],
        "15m_target_actionable_count": actionable_sources["15M"],
        "1h_target_actionable_count": actionable_sources["1H"],
        "no_actionable_causal_target_count": sum(
            row["first_actionable_target"] is None for row in outputs
        ),
        "actionable_targets_edge_5": sum(row["first_actionable_target"] is not None for row in outputs),
        "rr_1_0_net_pass": sum(row["edge_cohorts"]["5.0"]["rr_1_0"] for row in outputs),
        "rr_1_2_net_pass": sum(row["edge_cohorts"]["5.0"]["rr_1_2"] for row in outputs),
        "rr_1_5_net_pass": sum(row["edge_cohorts"]["5.0"]["rr_1_5"] for row in outputs),
        "stop_distance": distribution(row["stop_distance_bps"] for row in outputs),
        "target_distance": distribution(row["target_distance_bps"] for row in outputs),
        "total_cost_bps": distribution(row["total_cost_bps"] for row in outputs),
        "net_edge_bps": distribution(row["expected_net_edge_bps"] for row in outputs),
        "offline_outcomes": outcomes,
        "offline_outcome_horizons": outcome_horizons,
        "rows": outputs,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-ms", type=int, required=True)
    parser.add_argument("--to-ms", type=int, required=True)
    parser.add_argument("--parameter-set-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = replay(load_candidates(args.from_ms, args.to_ms, args.parameter_set_id))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(result, indent=2, sort_keys=True) + "\n"
    args.output.write_text(data, encoding="utf-8")
    digest = hashlib.sha256(data.encode()).hexdigest()
    print(json.dumps({"output": str(args.output), "sha256": digest,
                      "candidate_rows": result["candidate_rows"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
