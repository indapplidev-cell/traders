"""Bounded, outcome-aware offline search for the Scalping profile.

The input is the append-only prospective collector.  The tool has no database,
exchange, command, or control dependency and never promotes parameters.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from itertools import product
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Mapping


PROFILE_ID = "trade-5m-v2"
FEE_BPS = 20.0
SLIPPAGE_BPS = 4.0
SAFETY_MARGIN_BPS = 3.0
RR_VALUES = (0.4, 0.6, 0.8, 1.0, 1.2, 1.5)
EDGE_VALUES = (1.0, 10.0, 15.0, 20.0)
SCORE_VALUES = (55.0, 60.0, 65.0)
ATR_VALUES = (0.25, 0.5, 0.75)
STOP_VALUES = (50.0, 65.0, 80.0)


def _number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _utc_day(boundary_ms: int) -> str:
    return datetime.fromtimestamp(boundary_ms / 1000, timezone.utc).date().isoformat()


@dataclass(frozen=True, slots=True)
class ReplayCandidate:
    observation_id: str
    segment_id: str
    parameter_set_id: str
    boundary_ms: int
    day: str
    symbol: str
    opportunity_id: str
    direction: str
    setup_type: str
    strategy_score: float
    entry: float
    causal_invalidation: float
    atr: float
    targets: tuple[float, ...]
    spread_bps: float
    depth_impact_bps: float
    path: tuple[tuple[int, float, float, float], ...]


@dataclass(frozen=True, slots=True)
class SearchConfig:
    minimum_net_rr: float
    minimum_net_edge_bps: float
    minimum_strategy_score: float
    atr_buffer_multiplier: float
    maximum_stop_bps: float

    @property
    def version(self) -> str:
        return (
            f"rr{self.minimum_net_rr:g}-edge{self.minimum_net_edge_bps:g}-"
            f"score{self.minimum_strategy_score:g}-atr{self.atr_buffer_multiplier:g}-"
            f"stop{self.maximum_stop_bps:g}"
        )


def _load_outcomes(root: Path, prefixes: tuple[str, ...]) -> dict[str, Mapping[str, Any]]:
    outcomes: dict[str, Mapping[str, Any]] = {}
    for prefix in prefixes:
        for path in sorted(root.glob(f"outcomes-{prefix}-*.jsonl")):
            with path.open(encoding="utf-8") as stream:
                for line in stream:
                    row = json.loads(line)
                    outcomes[str(row["observation_id"])] = row
    return outcomes


def _candidate(observation: Mapping[str, Any], outcome: Mapping[str, Any]) -> ReplayCandidate | None:
    identity = observation.get("identity") or {}
    geometry = observation.get("geometry_baseline_inputs") or {}
    strategy = observation.get("strategy") or {}
    costs = observation.get("cost_inputs") or {}
    frozen = outcome.get("frozen_opportunity") or {}
    direction = str(frozen.get("direction") or observation.get("setup", {}).get("direction"))
    entry = _number(geometry.get("entry_reference") or frozen.get("entry_reference"))
    invalidation = _number(geometry.get("causal_invalidation"))
    atr = _number(geometry.get("atr"))
    score = _number(strategy.get("final_score"))
    spread = _number(costs.get("spread_bps"))
    depth = _number(costs.get("depth_impact_bps"))
    if None in (entry, invalidation, atr, score, spread, depth):
        return None
    target_values: list[float] = []
    for target in geometry.get("target_hierarchy_candidates") or ():
        price = _number(target.get("price")) if isinstance(target, Mapping) else None
        if price is None or target.get("future_safe") is False or target.get("validated") is False:
            continue
        if target.get("still_relevant") is False:
            continue
        if direction == "BULLISH" and price <= entry:
            continue
        if direction == "BEARISH" and price >= entry:
            continue
        if price not in target_values:
            target_values.append(price)
    target_values.sort(key=lambda price: abs(price - float(entry)))
    path = tuple(
        (int(bar["open_time_ms"]), float(bar["high"]), float(bar["low"]), float(bar["close"]))
        for bar in outcome.get("closed_candle_path") or ()
    )
    if direction not in {"BULLISH", "BEARISH"} or not target_values or not path:
        return None
    boundary = int(identity.get("boundary_time_ms") or frozen["boundary_time_ms"])
    return ReplayCandidate(
        observation_id=str(observation["observation_id"]),
        segment_id=str(observation["observation_segment_id"]),
        parameter_set_id=str(identity["parameter_set_id"]),
        boundary_ms=boundary,
        day=_utc_day(boundary),
        symbol=str(identity["symbol"]),
        opportunity_id=str(frozen.get("opportunity_id") or identity.get("opportunity_id")),
        direction=direction,
        setup_type=str((observation.get("setup") or {}).get("type")),
        strategy_score=float(score), entry=float(entry), causal_invalidation=float(invalidation),
        atr=float(atr), targets=tuple(target_values), spread_bps=float(spread),
        depth_impact_bps=float(depth), path=path,
    )


def load_candidates(root: Path, prefixes: tuple[str, ...]) -> tuple[list[ReplayCandidate], dict[str, int]]:
    outcomes = _load_outcomes(root, prefixes)
    candidates: list[ReplayCandidate] = []
    seen: set[str] = set()
    observation_rows = 0
    for prefix in prefixes:
        for path in sorted(root.glob(f"observations-{prefix}-*.jsonl")):
            with path.open(encoding="utf-8") as stream:
                for line in stream:
                    observation_rows += 1
                    row = json.loads(line)
                    observation_id = str(row.get("observation_id"))
                    if observation_id in seen or observation_id not in outcomes:
                        continue
                    seen.add(observation_id)
                    item = _candidate(row, outcomes[observation_id])
                    if item is not None:
                        candidates.append(item)
    candidates.sort(key=lambda row: (row.boundary_ms, row.symbol, row.observation_id))
    return candidates, {
        "observation_rows_scanned": observation_rows,
        "outcome_rows": len(outcomes),
        "replayable_outcomes": len(candidates),
        "unreplayable_outcomes": len(outcomes) - len(candidates),
    }


def _economics(candidate: ReplayCandidate, config: SearchConfig) -> tuple[float, float, float, float] | None:
    stop = (
        candidate.causal_invalidation - candidate.atr * config.atr_buffer_multiplier
        if candidate.direction == "BULLISH"
        else candidate.causal_invalidation + candidate.atr * config.atr_buffer_multiplier
    )
    risk_bps = abs(stop - candidate.entry) / candidate.entry * 10_000
    if risk_bps <= 0 or risk_bps > config.maximum_stop_bps:
        return None
    total_cost = FEE_BPS + SLIPPAGE_BPS + SAFETY_MARGIN_BPS + candidate.spread_bps + candidate.depth_impact_bps
    for target in candidate.targets:
        reward_bps = abs(target - candidate.entry) / candidate.entry * 10_000
        net_edge = reward_bps - total_cost
        net_rr = net_edge / (risk_bps + total_cost) if net_edge > 0 else -1.0
        if net_edge >= config.minimum_net_edge_bps and net_rr >= config.minimum_net_rr:
            return stop, target, risk_bps, total_cost
    return None


def _outcome(candidate: ReplayCandidate, stop: float, target: float, total_cost: float) -> tuple[float, str]:
    last_close = candidate.entry
    cutoff = candidate.boundary_ms + 30 * 60_000
    for open_ms, high, low, close in candidate.path:
        if open_ms > cutoff:
            break
        last_close = close
        target_hit = high >= target if candidate.direction == "BULLISH" else low <= target
        stop_hit = low <= stop if candidate.direction == "BULLISH" else high >= stop
        if stop_hit:  # conservative ordering when both lie inside one candle
            loss = abs(stop - candidate.entry) / candidate.entry * 10_000
            return -(loss + total_cost), "STOP"
        if target_hit:
            win = abs(target - candidate.entry) / candidate.entry * 10_000
            return win - total_cost, "TARGET"
    raw = (
        (last_close - candidate.entry) / candidate.entry * 10_000
        if candidate.direction == "BULLISH"
        else (candidate.entry - last_close) / candidate.entry * 10_000
    )
    return raw - total_cost, "TIME"


def metrics(candidates: Iterable[ReplayCandidate], config: SearchConfig, *, hours: float) -> dict[str, Any]:
    selected: list[tuple[ReplayCandidate, float, str, float]] = []
    claimed: set[str] = set()
    for candidate in candidates:
        if candidate.strategy_score < config.minimum_strategy_score or candidate.opportunity_id in claimed:
            continue
        economics = _economics(candidate, config)
        if economics is None:
            continue
        stop, target, risk_bps, total_cost = economics
        pnl_bps, outcome = _outcome(candidate, stop, target, total_cost)
        claimed.add(candidate.opportunity_id)
        selected.append((candidate, pnl_bps, outcome, risk_bps + total_cost))
    pnls = [row[1] for row in selected]
    wins = [value for value in pnls if value > 0]
    losses = [-value for value in pnls if value < 0]
    equity = peak = drawdown = 0.0
    streak = max_streak = 0
    for value in pnls:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
        streak = streak + 1 if value < 0 else 0
        max_streak = max(max_streak, streak)
    per_day: dict[str, list[float]] = defaultdict(list)
    per_symbol: dict[str, list[float]] = defaultdict(list)
    for candidate, pnl, _, _ in selected:
        per_day[candidate.day].append(pnl)
        per_symbol[candidate.symbol].append(pnl)
    count = len(selected)
    expectancy = mean(pnls) if pnls else None
    return {
        "configuration": asdict(config), "profile_version": config.version,
        "opportunities": count, "opportunities_per_hour": count / hours if hours else None,
        "plan_paper_per_hour": count / hours if hours else None,
        "net_expectancy_per_trade_bps": expectancy,
        "net_expectancy_per_hour_bps": expectancy * count / hours if expectancy is not None and hours else None,
        "profit_factor": sum(wins) / sum(losses) if losses else None,
        "win_rate": len(wins) / count if count else None,
        "average_win_bps": mean(wins) if wins else None,
        "average_loss_bps": mean(losses) if losses else None,
        "max_drawdown_bps": drawdown if pnls else None,
        "max_loss_streak": max_streak if pnls else None,
        "risk_adjusted_return": sum(p / risk for (_, p, _, risk) in selected) if selected else None,
        "outcomes": dict(Counter(row[2] for row in selected)),
        "symbols": len(per_symbol),
        "positive_days": sum(mean(values) > 0 for values in per_day.values()),
        "days": len(per_day),
        "positive_symbols": sum(mean(values) > 0 for values in per_symbol.values()),
        "per_day": {key: {"count": len(values), "expectancy_bps": mean(values)} for key, values in sorted(per_day.items())},
    }


def _hours(rows: Iterable[ReplayCandidate]) -> float:
    values = [row.boundary_ms for row in rows]
    return (max(values) - min(values) + 300_000) / 3_600_000 if values else 0.0


def run(candidates: list[ReplayCandidate]) -> dict[str, Any]:
    calibration = [row for row in candidates if row.day in {"2026-08-27", "2026-08-28"}]
    validation = [row for row in candidates if row.day == "2026-08-29"]
    holdout = [row for row in candidates if row.day in {"2026-08-30", "2026-09-01", "2026-09-02"}]
    windows = {"calibration": calibration, "validation": validation, "holdout": holdout}
    baseline = SearchConfig(1.5, 1.0, 65.0, 0.25, 80.0)
    baseline_metrics = {name: metrics(rows, baseline, hours=_hours(rows)) for name, rows in windows.items()}
    configurations = [SearchConfig(*values) for values in product(RR_VALUES, EDGE_VALUES, SCORE_VALUES, ATR_VALUES, STOP_VALUES)]
    calibration_results = [metrics(calibration, config, hours=_hours(calibration)) for config in configurations]
    viable = [
        row for row in calibration_results
        if row["opportunities"] >= 20
        and (row["net_expectancy_per_trade_bps"] or -1) > 0
        and (row["profit_factor"] or 0) > 1
        and row["positive_days"] == row["days"]
        and row["symbols"] >= 2
    ]
    viable.sort(key=lambda row: (
        row["net_expectancy_per_trade_bps"], -row["max_drawdown_bps"],
        row["opportunities_per_hour"], row["risk_adjusted_return"],
    ), reverse=True)
    all_ranked = sorted(
        calibration_results,
        key=lambda row: (
            row["net_expectancy_per_trade_bps"] if row["net_expectancy_per_trade_bps"] is not None else float("-inf"),
            -(row["max_drawdown_bps"] or float("inf")),
            row["opportunities_per_hour"] or 0,
        ),
        reverse=True,
    )
    validation_ranked: list[dict[str, Any]] = []
    for calibration_row in viable[:50]:
        config = SearchConfig(**calibration_row["configuration"])
        validation_row = metrics(validation, config, hours=_hours(validation))
        validation_ranked.append({"calibration": calibration_row, "validation": validation_row, "config": config})
    validation_ranked = [
        row for row in validation_ranked
        if row["validation"]["opportunities"] >= 3
        and (row["validation"]["net_expectancy_per_trade_bps"] or -1) > 0
        and (row["validation"]["profit_factor"] or 0) > 1
    ]
    validation_ranked.sort(key=lambda row: (
        row["validation"]["net_expectancy_per_trade_bps"],
        -row["validation"]["max_drawdown_bps"],
        row["validation"]["opportunities_per_hour"],
    ), reverse=True)
    selected = validation_ranked[0] if validation_ranked else None
    selected_result = None
    if selected:
        config = selected["config"]
        selected_result = {
            "configuration": asdict(config),
            "calibration": selected["calibration"],
            "validation": selected["validation"],
            "holdout": metrics(holdout, config, hours=_hours(holdout)),
        }
    return {
        "schema_version": "scalping-opportunity-cadence-search-v1",
        "profile_id": PROFILE_ID,
        "cost_model": {"entry_exit_fee_bps": FEE_BPS, "entry_exit_slippage_bps": SLIPPAGE_BPS, "safety_margin_bps": SAFETY_MARGIN_BPS, "spread": "OBSERVED", "depth_impact": "OBSERVED"},
        "search_space": {"configurations": len(configurations), "minimum_net_rr": RR_VALUES, "minimum_net_edge_bps": EDGE_VALUES, "minimum_strategy_score": SCORE_VALUES, "atr_buffer_multiplier": ATR_VALUES, "maximum_stop_bps": STOP_VALUES},
        "windows": {name: {"rows": len(rows), "hours": _hours(rows), "days": sorted({row.day for row in rows}), "symbols": sorted({row.symbol for row in rows})} for name, rows in windows.items()},
        "baseline": baseline_metrics,
        "viable_calibration_configurations": len(viable),
        "top_calibration_configurations_including_rejected": all_ranked[:20],
        "validation_survivors": len(validation_ranked),
        "selected": selected_result,
        "holdout_was_used_for_selection": False,
        "safety": {"production_mutations": 0, "parameter_promotions": 0, "binance_order_api_calls": 0, "live_enabled": False},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--prefix", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    candidates, load_stats = load_candidates(args.input_dir, tuple(args.prefix))
    report = run(candidates)
    report["load"] = load_stats
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "load": load_stats, "selected": report["selected"]}, sort_keys=True))
    return 0 if report["selected"] is not None else 2


if __name__ == "__main__":
    raise SystemExit(main())
