"""Read-only candle replay for the independent Scalping v2 setup family."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from itertools import product
from pathlib import Path
from statistics import mean, median, pstdev

from app.engine_market_data.db.candle_repository import CandleRepository
from app.engine_market_data.db.session import create_market_data_session_factory
from app.trading_universe.domain import PREPARED_NEXT_TRADING_UNIVERSE


PROFILE = "trade-5m-v2"
BASE_COST_BPS = 27.0


@dataclass(frozen=True, slots=True)
class Opportunity:
    symbol: str
    boundary_ms: int
    day: str
    setup_type: str
    direction: str
    entry: float
    atr_bps: float
    spread_depth_bps: float
    path: tuple[tuple[int, float, float, float], ...]


@dataclass(frozen=True, slots=True)
class Config:
    setup_set: str
    breakout_lookback: int
    volume_ratio: float
    momentum_bps: float
    extreme_z: float
    stop_atr: float
    maximum_stop_bps: float
    target_atr: float
    minimum_net_rr: float
    minimum_net_edge_bps: float
    holding_minutes: int
    ev_gate: bool


def _day(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).date().isoformat()


def _atr(candles: list[object], periods: int = 12) -> float:
    rows = candles[-periods:]
    return mean(float(row.high) - float(row.low) for row in rows)


def _detect(history: list[object], config: Config) -> tuple[str, str] | None:
    current = history[-1]
    prior = history[-config.breakout_lookback - 1:-1]
    volumes = [float(row.volume) for row in history[-13:-1]]
    volume_ratio = float(current.volume) / mean(volumes) if volumes and mean(volumes) else 0.0
    close = float(current.close)
    open_price = float(current.open)
    breakout = None
    if volume_ratio >= config.volume_ratio:
        if close > max(float(row.high) for row in prior):
            breakout = ("MICRO_BREAKOUT", "BULLISH")
        elif close < min(float(row.low) for row in prior):
            breakout = ("MICRO_BREAKOUT", "BEARISH")
    momentum = None
    move_bps = (close - float(history[-4].close)) / float(history[-4].close) * 10_000
    if volume_ratio >= config.volume_ratio and abs(move_bps) >= config.momentum_bps:
        momentum = ("MOMENTUM_CONTINUATION", "BULLISH" if move_bps > 0 else "BEARISH")
    closes = [float(row.close) for row in history[-13:-1]]
    sigma = pstdev(closes)
    z = (close - mean(closes)) / sigma if sigma else 0.0
    lower_wick = min(open_price, close) - float(current.low)
    upper_wick = float(current.high) - max(open_price, close)
    extreme = None
    if z <= -config.extreme_z and close >= open_price and lower_wick > upper_wick:
        extreme = ("LOCAL_EXTREME_REVERSION", "BULLISH")
    elif z >= config.extreme_z and close <= open_price and upper_wick > lower_wick:
        extreme = ("LOCAL_EXTREME_REVERSION", "BEARISH")
    allowed = {
        "BREAKOUT": (breakout,),
        "MOMENTUM": (momentum,),
        "REVERSION": (extreme,),
        "ALL": (extreme, breakout, momentum),
    }[config.setup_set]
    return next((item for item in allowed if item is not None), None)


def _costs_from_collector(root: Path) -> dict[str, float]:
    values: dict[str, list[float]] = defaultdict(list)
    for path in sorted(root.glob("observations-*.jsonl")):
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                cost = row.get("cost_inputs") or {}
                spread = cost.get("spread_bps")
                depth = cost.get("depth_impact_bps")
                symbol = (row.get("identity") or {}).get("symbol")
                if symbol and spread is not None and depth is not None and float(spread) >= 0 and float(depth) >= 0:
                    values[str(symbol)].append(float(spread) + float(depth))
    return {symbol: median(rows) for symbol, rows in values.items()}


def _load(repository: CandleRepository, costs: dict[str, float]) -> dict[str, tuple[list[object], list[object]]]:
    start = int(datetime(2026, 8, 26, tzinfo=timezone.utc).timestamp() * 1000)
    end = int(datetime(2026, 9, 3, tzinfo=timezone.utc).timestamp() * 1000)
    return {
        symbol: (
            repository.get_candles(symbol, "5m", start_time_ms=start - 12 * 3_600_000, end_time_ms=end),
            repository.get_candles(symbol, "1m", start_time_ms=start, end_time_ms=end + 30 * 60_000),
        )
        for symbol in PREPARED_NEXT_TRADING_UNIVERSE.symbols
    }


def _opportunities(data: dict[str, tuple[list[object], list[object]]], costs: dict[str, float], config: Config) -> list[Opportunity]:
    output: list[Opportunity] = []
    for symbol, (five, one) in data.items():
        one_by_open = {int(row.open_time_ms): index for index, row in enumerate(one)}
        for index in range(24, len(five)):
            boundary = int(five[index].close_time_ms) + 1
            day = _day(boundary)
            if day not in {"2026-08-27", "2026-08-28", "2026-08-29", "2026-08-30", "2026-09-01", "2026-09-02"}:
                continue
            causal_history = five[index - 24:index + 1]
            setup = _detect(causal_history, config)
            next_minute = one_by_open.get(boundary)
            if setup is None or next_minute is None or next_minute + 2 >= len(one):
                continue
            # One complete 1m confirmation candle, then executable entry and
            # later-only outcome path.
            entry = float(one[next_minute].close)
            path = tuple((int(row.open_time_ms), float(row.high), float(row.low), float(row.close)) for row in one[next_minute + 1:next_minute + 31])
            atr_bps = _atr(causal_history) / entry * 10_000
            output.append(Opportunity(symbol, boundary, day, setup[0], setup[1], entry, atr_bps, costs.get(symbol, 5.0), path))
    return output


def _outcome(row: Opportunity, config: Config) -> tuple[float, str, float, float] | None:
    stop_bps = max(15.0, row.atr_bps * config.stop_atr)
    if stop_bps > config.maximum_stop_bps:
        return None
    total_cost = BASE_COST_BPS + row.spread_depth_bps
    target_bps = max(row.atr_bps * config.target_atr, total_cost + config.minimum_net_edge_bps,
                     total_cost + config.minimum_net_rr * (stop_bps + total_cost))
    net_win, net_loss = target_bps - total_cost, stop_bps + total_cost
    sign = 1 if row.direction == "BULLISH" else -1
    stop = row.entry * (1 - sign * stop_bps / 10_000)
    target = row.entry * (1 + sign * target_bps / 10_000)
    last = row.entry
    cutoff = row.boundary_ms + (config.holding_minutes + 1) * 60_000
    for open_ms, high, low, close in row.path:
        if open_ms > cutoff:
            break
        last = close
        stop_hit = low <= stop if row.direction == "BULLISH" else high >= stop
        target_hit = high >= target if row.direction == "BULLISH" else low <= target
        if stop_hit:
            return -net_loss, "STOP", net_win, net_loss
        if target_hit:
            return net_win, "TARGET", net_win, net_loss
    raw = ((last - row.entry) if row.direction == "BULLISH" else (row.entry - last)) / row.entry * 10_000
    return raw - total_cost, "TIME", net_win, net_loss


def _rates(rows: list[tuple[Opportunity, tuple[float, str, float, float]]]) -> dict[tuple[str, str], tuple[int, float]]:
    grouped: dict[tuple[str, str], list[bool]] = defaultdict(list)
    for row, outcome in rows:
        grouped[(row.setup_type, row.direction)].append(outcome[0] > 0)
    return {key: (len(values), (sum(values) + 1) / (len(values) + 2)) for key, values in grouped.items()}


def _selected(opportunities: list[Opportunity], config: Config, rates: dict[tuple[str, str], tuple[int, float]] | None) -> list[tuple[Opportunity, tuple[float, str, float, float]]]:
    output = []
    for row in opportunities:
        outcome = _outcome(row, config)
        if outcome is None:
            continue
        if config.ev_gate:
            count, p_win = (rates or {}).get((row.setup_type, row.direction), (0, 0.0))
            if count < 20 or p_win * outcome[2] - (1 - p_win) * outcome[3] <= 0:
                continue
        output.append((row, outcome))
    return output


def _metrics(rows: list[tuple[Opportunity, tuple[float, str, float, float]]], hours: float) -> dict[str, object]:
    pnls = [outcome[0] for _, outcome in rows]
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
    expectancy = mean(pnls) if pnls else None
    return {"opportunities": len(rows), "opportunities_per_hour": len(rows) / hours,
            "plan_paper_per_hour": len(rows) / hours,
            "net_expectancy_per_trade_bps": expectancy,
            "net_expectancy_per_hour_bps": expectancy * len(rows) / hours if expectancy is not None else None,
            "profit_factor": sum(wins) / sum(losses) if losses else None,
            "win_rate": len(wins) / len(rows) if rows else None,
            "max_drawdown_bps": drawdown if rows else None, "max_loss_streak": max_streak,
            "symbols": len({row.symbol for row, _ in rows}),
            "outcomes": dict(Counter(outcome[1] for _, outcome in rows))}


def _configs() -> list[Config]:
    return [Config(*values) for values in product(
        ("BREAKOUT", "MOMENTUM", "REVERSION", "ALL"), (3,), (0.8,),
        (10.0,), (1.5,), (0.25, 0.5),
        (40.0, 60.0), (0.5, 1.0, 2.0), (0.2, 0.4), (1.0,),
        (5, 10, 15), (False, True),
    )]


def run(data: dict[str, tuple[list[object], list[object]]], costs: dict[str, float]) -> dict[str, object]:
    cache: dict[tuple[object, ...], list[Opportunity]] = {}
    ranked = []
    all_results = []
    for config in _configs():
        setup_key = (config.setup_set, config.breakout_lookback, config.volume_ratio, config.momentum_bps, config.extreme_z)
        if setup_key not in cache:
            cache[setup_key] = _opportunities(data, costs, config)
        opportunities = cache[setup_key]
        fit = [row for row in opportunities if row.day == "2026-08-27"]
        calibration = [row for row in opportunities if row.day == "2026-08-28"]
        fit_outcomes = _selected(fit, config, None)
        rates = _rates(fit_outcomes)
        selected = _selected(calibration, config, rates)
        metrics = _metrics(selected, 24.0)
        all_results.append((config, metrics))
        if metrics["opportunities"] >= 10 and (metrics["net_expectancy_per_trade_bps"] or -1) > 0 and (metrics["profit_factor"] or 0) > 1 and metrics["opportunities_per_hour"] > 0.25:
            ranked.append((config, metrics, rates, opportunities))
    ranked.sort(key=lambda item: (item[1]["net_expectancy_per_hour_bps"], -item[1]["max_drawdown_bps"]), reverse=True)
    all_results.sort(key=lambda item: (
        item[1]["net_expectancy_per_trade_bps"] if item[1]["net_expectancy_per_trade_bps"] is not None else float("-inf"),
        item[1]["opportunities_per_hour"],
    ), reverse=True)
    survivors = []
    for config, calibration, rates, opportunities in ranked[:100]:
        validation = _metrics(_selected([row for row in opportunities if row.day == "2026-08-29"], config, rates), 24.0)
        if validation["opportunities"] >= 5 and (validation["net_expectancy_per_trade_bps"] or -1) > 0 and (validation["profit_factor"] or 0) > 1 and validation["opportunities_per_hour"] > 0.25:
            survivors.append((config, calibration, validation, rates, opportunities))
    survivors.sort(key=lambda item: (item[2]["net_expectancy_per_hour_bps"], item[1]["net_expectancy_per_hour_bps"]), reverse=True)
    selected = None
    if survivors:
        config, calibration, validation, rates, opportunities = survivors[0]
        holdout_rows = [row for row in opportunities if row.day in {"2026-08-30", "2026-09-01", "2026-09-02"}]
        selected = {"configuration": asdict(config), "calibration": calibration, "validation": validation,
                    "holdout": _metrics(_selected(holdout_rows, config, rates), 72.0),
                    "empirical_buckets": {"|".join(key): {"samples": value[0], "p_win_laplace": value[1]} for key, value in rates.items()}}
    best_rejected = None
    if all_results:
        rejected_config, _ = all_results[0]
        setup_key = (
            rejected_config.setup_set, rejected_config.breakout_lookback,
            rejected_config.volume_ratio, rejected_config.momentum_bps,
            rejected_config.extreme_z,
        )
        rejected_opportunities = cache[setup_key]
        rejected_fit = _selected(
            [row for row in rejected_opportunities if row.day == "2026-08-27"],
            rejected_config,
            None,
        )
        rejected_rates = _rates(rejected_fit)
        best_rejected = {
            "selection_role": "DIAGNOSTIC_ONLY_NOT_PROMOTABLE",
            "configuration": asdict(rejected_config),
            "calibration": _metrics(_selected(
                [row for row in rejected_opportunities if row.day == "2026-08-28"],
                rejected_config, rejected_rates,
            ), 24.0),
            "validation": _metrics(_selected(
                [row for row in rejected_opportunities if row.day == "2026-08-29"],
                rejected_config, rejected_rates,
            ), 24.0),
            "holdout": _metrics(_selected([
                row for row in rejected_opportunities
                if row.day in {"2026-08-30", "2026-09-01", "2026-09-02"}
            ], rejected_config, rejected_rates), 72.0),
            "empirical_buckets": {
                "|".join(key): {"samples": value[0], "p_win_laplace": value[1]}
                for key, value in rejected_rates.items()
            },
        }
    return {"schema_version": "scalping-v2-candle-replay-v1", "profile_id": PROFILE,
            "configurations": len(_configs()), "calibration_survivors": len(ranked),
            "top_calibration_including_rejected": [
                {"configuration": asdict(config), "metrics": metrics}
                for config, metrics in all_results[:20]
            ],
            "validation_survivors": len(survivors), "selected": selected,
            "best_rejected_diagnostic": best_rejected,
            "costs": {"fixed_fee_slippage_margin_bps": BASE_COST_BPS,
                      "observed_spread_depth_median_by_symbol": costs},
            "holdout_was_used_for_selection": False,
            "safety": {"database_writes": 0, "binance_order_api_calls": 0, "live_enabled": False}}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--collector-dir", type=Path, default=Path("reports/calibration/scalping-prospective"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    costs = _costs_from_collector(args.collector_dir)
    result = run(_load(CandleRepository(create_market_data_session_factory()), costs), costs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"selected": result["selected"], "survivors": result["validation_survivors"]}, sort_keys=True))
    return 0 if result["selected"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
