"""Calibrate the independent ``trade-5m-v2`` Scalping policy family.

This is an offline, causal replay.  It consumes the v1 prospective snapshots
only as immutable market observations; policy identity and outcome semantics
are v2.  Candidate selection never reads validation or holdout outcomes.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from itertools import product
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.calibrate_scalping_opportunity_cadence import (
    ReplayCandidate,
    _hours,
    load_candidates,
)


PROFILE_ID = "trade-5m-v2"
POLICY_VERSIONS = {
    "setup": "scalping-micro-setup-v2",
    "entry": "scalping-next-closed-1m-entry-v2",
    "stop": "scalping-causal-volatility-stop-v2",
    "target": "scalping-nearest-viable-target-v3",
    "rr_ev": "scalping-empirical-ev-v1",
    "cost": "scalping-round-trip-net-pnl-v2",
    "ttl_holding": "scalping-short-lifecycle-v2",
    "risk": "scalping-risk-capped-v2",
}
BASE_COST_BPS = 27.0  # 20 fees + 4 slippage + unchanged 3 bps safety margin


@dataclass(frozen=True, slots=True)
class PolicyConfig:
    admission_policy: str
    entry_policy: str
    direction_policy: str
    stop_policy: str
    stop_atr: float
    minimum_stop_bps: float
    maximum_stop_bps: float
    target_policy: str
    target_atr: float
    minimum_net_edge_bps: float
    minimum_net_rr: float
    holding_minutes: int
    minimum_bucket_samples: int
    minimum_expected_value_bps: float

    @property
    def version(self) -> str:
        return "-".join(str(value).replace(".", "p") for value in asdict(self).values())


@dataclass(frozen=True, slots=True)
class Trade:
    candidate: ReplayCandidate
    direction: str
    stop: float
    target: float
    total_cost_bps: float
    net_win_bps: float
    net_loss_bps: float
    net_rr: float
    pnl_bps: float
    outcome: str


def _direction(candidate: ReplayCandidate, policy: str) -> str:
    if policy == "CONTINUATION":
        return candidate.direction
    if policy == "LOCAL_EXTREME_REVERSION":
        return "BEARISH" if candidate.direction == "BULLISH" else "BULLISH"
    raise ValueError(policy)


def _price(entry: float, direction: str, bps: float, favorable: bool) -> float:
    sign = 1 if direction == "BULLISH" else -1
    if not favorable:
        sign *= -1
    return entry * (1 + sign * bps / 10_000)


def _trade(candidate: ReplayCandidate, config: PolicyConfig) -> Trade | None:
    direction = _direction(candidate, config.direction_policy)
    if config.entry_policy != "NEXT_CLOSED_1M":
        raise ValueError(config.entry_policy)
    if len(candidate.path) < 2:
        return None
    # The stored analysis close is not assumed executable.  Confirm on the
    # first complete post-decision minute and replay only later bars.
    entry = candidate.path[0][3]
    outcome_path = candidate.path[1:]
    atr_bps = candidate.atr / entry * 10_000
    if config.stop_policy == "CAUSAL":
        if (candidate.causal_invalidation < entry) != (direction == "BULLISH"):
            return None
        causal_bps = abs(candidate.causal_invalidation - entry) / entry * 10_000
        # A causal invalidation from the opposite thesis is not reused by the
        # mean-reversion family; its local-extreme stop is volatility-derived.
        if direction != candidate.direction:
            return None
        stop_bps = causal_bps + atr_bps * config.stop_atr
    else:
        stop_bps = max(config.minimum_stop_bps, atr_bps * config.stop_atr)
    if stop_bps <= 0 or stop_bps > config.maximum_stop_bps:
        return None
    total_cost = BASE_COST_BPS + candidate.spread_bps + candidate.depth_impact_bps
    structural = [
        abs(value - entry) / entry * 10_000
        for value in candidate.targets
        if (value > entry) == (direction == "BULLISH")
    ]
    minimum_reward = total_cost + config.minimum_net_edge_bps
    rr_reward = total_cost + config.minimum_net_rr * (stop_bps + total_cost)
    floor = max(minimum_reward, rr_reward)
    atr_reward = max(floor, atr_bps * config.target_atr)
    if config.target_policy == "NEAREST_STRUCTURAL_OR_ATR":
        target_bps = next((value for value in sorted(structural) if value >= floor), atr_reward)
    elif config.target_policy == "COST_AWARE_ATR":
        target_bps = atr_reward
    else:
        raise ValueError(config.target_policy)
    net_win = target_bps - total_cost
    net_loss = stop_bps + total_cost
    net_rr = net_win / net_loss
    stop = _price(entry, direction, stop_bps, False)
    target = _price(entry, direction, target_bps, True)
    cutoff = candidate.boundary_ms + config.holding_minutes * 60_000
    last = entry
    outcome = "TIME"
    pnl = -total_cost
    for open_ms, high, low, close in outcome_path:
        if open_ms > cutoff:
            break
        last = close
        hit_stop = low <= stop if direction == "BULLISH" else high >= stop
        hit_target = high >= target if direction == "BULLISH" else low <= target
        if hit_stop:
            outcome, pnl = "STOP", -net_loss
            break
        if hit_target:
            outcome, pnl = "TARGET", net_win
            break
    else:
        open_ms = cutoff + 1
    if outcome == "TIME":
        raw = ((last - entry) if direction == "BULLISH" else (entry - last)) / entry * 10_000
        pnl = raw - total_cost
    return Trade(candidate, direction, stop, target, total_cost, net_win, net_loss, net_rr, pnl, outcome)


def _bucket(trade: Trade) -> tuple[str, str]:
    # Setup/direction is the prespecified empirical cohort.  Symbol-specific
    # estimates are too sparse and would silently turn the EV gate into a
    # symbol whitelist learned from one day.
    return (trade.candidate.setup_type, trade.direction)


def _rates(trades: Iterable[Trade]) -> dict[tuple[str, str], tuple[int, float]]:
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for trade in trades:
        grouped[_bucket(trade)].append(trade.pnl_bps)
    return {key: (len(values), (sum(value > 0 for value in values) + 1) / (len(values) + 2)) for key, values in grouped.items()}


def _admit(trade: Trade, rates: dict[tuple[str, str], tuple[int, float]], config: PolicyConfig) -> bool:
    if config.admission_policy == "DYNAMIC_RR_STATIC_FALLBACK":
        return True
    count, probability = rates.get(_bucket(trade), (0, 0.0))
    if count < config.minimum_bucket_samples:
        # Explicit stricter static fallback: no empirical evidence means no
        # trade, never a borrowed 15m RR rule or invented probability.
        return False
    expected_value = probability * trade.net_win_bps - (1 - probability) * trade.net_loss_bps
    return expected_value >= config.minimum_expected_value_bps


def _metrics(trades: list[Trade], *, hours: float) -> dict[str, Any]:
    pnls = [trade.pnl_bps for trade in trades]
    wins = [value for value in pnls if value > 0]
    losses = [-value for value in pnls if value < 0]
    equity = peak = drawdown = 0.0
    streak = maximum_streak = 0
    days: dict[str, list[float]] = defaultdict(list)
    for trade in trades:
        equity += trade.pnl_bps
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
        streak = streak + 1 if trade.pnl_bps < 0 else 0
        maximum_streak = max(maximum_streak, streak)
        days[trade.candidate.day].append(trade.pnl_bps)
    expectancy = mean(pnls) if pnls else None
    return {
        "opportunities": len(trades),
        "opportunities_per_hour": len(trades) / hours if hours else None,
        "plan_paper_per_hour": len(trades) / hours if hours else None,
        "net_expectancy_per_trade_bps": expectancy,
        "net_expectancy_per_hour_bps": expectancy * len(trades) / hours if expectancy is not None and hours else None,
        "profit_factor": sum(wins) / sum(losses) if losses else None,
        "win_rate": len(wins) / len(trades) if trades else None,
        "max_drawdown_bps": drawdown if trades else None,
        "max_loss_streak": maximum_streak if trades else None,
        "positive_days": sum(mean(values) > 0 for values in days.values()),
        "days": len(days),
        "outcomes": dict(Counter(trade.outcome for trade in trades)),
        "symbols": len({trade.candidate.symbol for trade in trades}),
    }


def _configs() -> list[PolicyConfig]:
    return [PolicyConfig(*values) for values in product(
        ("EMPIRICAL_EV", "DYNAMIC_RR_STATIC_FALLBACK"),
        ("NEXT_CLOSED_1M",),
        ("CONTINUATION", "LOCAL_EXTREME_REVERSION"),
        ("CAUSAL", "ATR_LOCAL_EXTREME"),
        (0.25, 0.5, 0.75),
        (20.0,), (50.0, 80.0),
        ("NEAREST_STRUCTURAL_OR_ATR", "COST_AWARE_ATR"),
        (0.5, 1.0),
        (1.0, 5.0),
        (0.2, 0.4, 0.6),
        (5, 10, 15),
        (3,),
        (0.0,),
    )]


def run(candidates: list[ReplayCandidate]) -> dict[str, Any]:
    fit = [row for row in candidates if row.day == "2026-08-27"]
    calibration = [row for row in candidates if row.day == "2026-08-28"]
    validation = [row for row in candidates if row.day == "2026-08-29"]
    holdout = [row for row in candidates if row.day in {"2026-08-30", "2026-09-01", "2026-09-02"}]
    ranked: list[tuple[PolicyConfig, dict[str, Any], dict[tuple[str, str], tuple[int, float]]]] = []
    all_results: list[tuple[PolicyConfig, dict[str, Any]]] = []
    for config in _configs():
        fit_trades = [trade for row in fit if (trade := _trade(row, config)) is not None]
        rates = _rates(fit_trades)
        selected = [trade for row in calibration if (trade := _trade(row, config)) is not None and _admit(trade, rates, config)]
        result = _metrics(selected, hours=_hours(calibration))
        all_results.append((config, result))
        if (result["opportunities"] >= 5 and (result["net_expectancy_per_trade_bps"] or -1) > 0
                and (result["profit_factor"] or 0) > 1 and result["symbols"] >= 2):
            ranked.append((config, result, rates))
    ranked.sort(key=lambda item: (item[1]["net_expectancy_per_hour_bps"], -item[1]["max_drawdown_bps"]), reverse=True)
    all_results.sort(key=lambda item: (
        item[1]["net_expectancy_per_trade_bps"] if item[1]["net_expectancy_per_trade_bps"] is not None else float("-inf"),
        item[1]["opportunities_per_hour"] or 0,
    ), reverse=True)
    survivors: list[tuple[PolicyConfig, dict[str, Any], dict[str, Any], dict[tuple[str, str], tuple[int, float]]]] = []
    for config, calibration_result, rates in ranked[:100]:
        selected = [trade for row in validation if (trade := _trade(row, config)) is not None and _admit(trade, rates, config)]
        result = _metrics(selected, hours=_hours(validation))
        if (result["opportunities"] >= 3 and (result["net_expectancy_per_trade_bps"] or -1) > 0 and (result["profit_factor"] or 0) > 1):
            survivors.append((config, calibration_result, result, rates))
    survivors.sort(key=lambda item: (item[2]["net_expectancy_per_hour_bps"], item[1]["net_expectancy_per_hour_bps"]), reverse=True)
    selected = None
    if survivors:
        config, calibration_result, validation_result, rates = survivors[0]
        trades = [trade for row in holdout if (trade := _trade(row, config)) is not None and _admit(trade, rates, config)]
        selected = {
            "configuration": asdict(config), "profile_version": config.version,
            "empirical_buckets": {"|".join(key): {"samples": value[0], "p_win_laplace": value[1]} for key, value in sorted(rates.items())},
            "calibration": calibration_result, "validation": validation_result,
            "holdout": _metrics(trades, hours=_hours(holdout)),
        }
    return {
        "schema_version": "scalping-independent-profile-replay-v1",
        "profile_id": PROFILE_ID, "policy_versions": POLICY_VERSIONS,
        "cost_model": "UNCHANGED_FULL_ROUND_TRIP_PLUS_OBSERVED_SPREAD_DEPTH",
        "split": {"fit": ["2026-08-27"], "calibration": ["2026-08-28"], "validation": ["2026-08-29"], "holdout": ["2026-08-30", "2026-09-01", "2026-09-02"]},
        "configurations": len(_configs()), "calibration_survivors": len(ranked),
        "top_calibration_including_rejected": [
            {"configuration": asdict(config), "metrics": metrics}
            for config, metrics in all_results[:20]
        ],
        "validation_survivors": len(survivors), "selected": selected,
        "holdout_was_used_for_selection": False,
        "safety": {"production_mutations": 0, "binance_order_api_calls": 0, "live_enabled": False},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--prefix", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    candidates, load = load_candidates(args.input_dir, tuple(args.prefix))
    result = run(candidates)
    result["load"] = load
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"load": load, "selected": result["selected"], "survivors": result["validation_survivors"]}, sort_keys=True))
    return 0 if result["selected"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
