"""Build immutable causal observations for bullish-run weight calibration.

The source is a result-search history bundle created from a PostgreSQL read-only
session.  This adapter replays the authoritative pipeline, stores complete module
payloads, and precomputes unweighted analytical-exit factors.  It never connects
to an order adapter and never writes to PostgreSQL.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from app.engine_paper.analytical_exit import ClosedAnalysisCandle, analyze_position_exit

from .artifact_writer import DEFAULT_ARTIFACT_WRITER
from .bull_run_weights import (
    BASELINE_ENTRY_WEIGHTS,
    BASELINE_EXIT_WEIGHTS,
    CalibrationRequest,
    Candle5m,
    CausalObservation,
    DATASET_SCHEMA,
    ENTRY_COMPONENTS,
    ExitPathPoint,
)
from .frozen_funnel import FrozenFunnel
from .result_search import fingerprint
from .search_history import HistoryProvider


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _number(source: Mapping[str, Any], *names: str) -> float | None:
    for name in names:
        value = source.get(name)
        if value is None:
            continue
        try:
            result = float(value)
        except (TypeError, ValueError):
            continue
        if result >= 0:
            return result
    return None


def historical_costs(row: Mapping[str, Any]) -> dict[str, float] | None:
    geometry = _mapping(row.get("geometry"))
    required = {
        "entry_fee_bps": _number(geometry, "entry_fee_bps", "effective_entry_fee_bps"),
        "exit_fee_bps": _number(geometry, "exit_fee_bps", "effective_exit_fee_bps"),
        "entry_slippage_bps": _number(geometry, "entry_slippage_bps"),
        "exit_slippage_bps": _number(geometry, "exit_slippage_bps"),
        "spread_bps": _number(geometry, "spread_bps"),
        "adverse_fill_reserve_bps": _number(geometry, "adverse_fill_reserve_bps"),
    }
    if any(value is None for value in required.values()):
        return None
    result = {name: float(value) for name, value in required.items() if value is not None}
    result["round_trip_cost_bps"] = _number(geometry, "effective_total_cost_bps", "total_cost_bps") or sum(
        result.values()
    )
    return result


def _atr14(rows: Sequence[dict[str, Any]]) -> dict[int, float]:
    values: dict[int, float] = {}
    ranges: list[float] = []
    previous_close: float | None = None
    for row in rows:
        high, low, close = float(row["high"]), float(row["low"]), float(row["close"])
        true_range = max(high - low, abs(high - previous_close), abs(low - previous_close)) \
            if previous_close is not None else high - low
        ranges.append(true_range)
        values[int(row["open_time_ms"])] = sum(ranges[-14:]) / min(14, len(ranges))
        previous_close = close
    return values


def _entry_components(strategy: Mapping[str, Any]) -> dict[str, float] | None:
    context = _mapping(strategy.get("context"))
    decomposition = _mapping(context.get("scalping_score_decomposition"))
    contributions = _mapping(decomposition.get("components"))
    if set(contributions) != set(ENTRY_COMPONENTS):
        return None
    normalized = {}
    for name in ENTRY_COMPONENTS:
        baseline_weight = BASELINE_ENTRY_WEIGHTS[name]
        normalized[name] = max(0.0, min(100.0, float(contributions[name]) / baseline_weight * 100.0))
    return normalized


def _opposed(value: Any) -> bool:
    token = str(value or "").upper()
    return "BEAR" in token or token in {"DOWN", "TREND_DOWN"}


def _strong_reversal(evidence: Any) -> bool:
    graphical = _mapping(evidence.graphical_1m)
    altunina = _mapping(graphical.get("altunina"))
    return _opposed(altunina.get("structure_direction")) and _opposed(graphical.get("regime"))


def _closed(row: Mapping[str, Any], timeframe: str) -> ClosedAnalysisCandle:
    step = 60_000 if timeframe == "1m" else 300_000
    return ClosedAnalysisCandle(
        symbol=str(row["symbol"]), timeframe=timeframe,
        open_time_ms=int(row["open_time_ms"]),
        close_boundary_ms=int(row["close_time_ms"]) + 1,
        open_price=Decimal(str(row["open"])), high_price=Decimal(str(row["high"])),
        low_price=Decimal(str(row["low"])), close_price=Decimal(str(row["close"])),
        volume=Decimal(str(row["volume"])), quote_volume=None, trades_count=None,
        source="FROZEN_HISTORY", is_closed=True,
    )


def _exit_path(
    *, symbol: str, boundary: int, entry: float, stop: float, target: float,
    costs: Mapping[str, float], rows_1m: Sequence[dict[str, Any]], rows_5m: Sequence[dict[str, Any]],
    maximum_holding_minutes: int,
) -> tuple[ExitPathPoint, ...]:
    tail = boundary + maximum_holding_minutes * 60_000
    one_source = [row for row in rows_1m if boundary - 120 * 60_000 <=
                  int(row["open_time_ms"]) < tail]
    five_source = [row for row in rows_5m if boundary - 120 * 300_000 <=
                   int(row["open_time_ms"]) < tail]
    one = tuple(_closed(row, "1m") for row in one_source)
    five = tuple(_closed(row, "5m") for row in five_source)
    future = [row for row in rows_1m if boundary <= int(row["open_time_ms"]) <
              tail]
    points: list[ExitPathPoint] = []
    for row in future:
        causal_boundary = int(row["close_time_ms"]) + 1
        gross_bps = (float(row["close"]) / entry - 1.0) * 10_000.0
        net = Decimal(str(gross_bps - costs["round_trip_cost_bps"]))
        evidence = analyze_position_exit(
            position_id=f"research:{symbol}:{boundary}", symbol=symbol, side="LONG",
            entry_price=Decimal(str(entry)), stop_price=Decimal(str(stop)),
            target_price=Decimal(str(target)), opened_at_ms=boundary,
            candles_1m=one, candles_5m=five, boundary_ms=causal_boundary,
            gross_pnl=Decimal(str(gross_bps)), net_pnl=net,
        )
        if evidence.future_bars_used or evidence.decision.value in {"DATA_UNAVAILABLE", "ERROR"}:
            continue
        factors = {
            name: max(0.0, min(1.0, float(evidence.component_scores[name]) /
                              BASELINE_EXIT_WEIGHTS[name]))
            for name in ("graphical_structure", "technical_indicators", "momentum_volume")
        }
        points.append(ExitPathPoint(
            open_time_ms=int(row["open_time_ms"]), close_time_ms=int(row["close_time_ms"]),
            open=float(row["open"]), high=float(row["high"]), low=float(row["low"]),
            close=float(row["close"]), strong_reversal=_strong_reversal(evidence),
            module_verdicts={
                "technical_1m": evidence.technical_1m, "technical_5m": evidence.technical_5m,
                "graphical_1m": evidence.graphical_1m, "graphical_5m": evidence.graphical_5m,
                "volume_1m": evidence.volume_1m, "baseline_decision": evidence.decision.value,
                "baseline_exit_score": evidence.exit_score,
            }, **factors,
        ))
    return tuple(points)


def _plan_values(result: Any) -> tuple[float, float, float] | None:
    paper = _mapping(result.paper_payload)
    entry = paper.get("hypothetical_entry_reference")
    stop = paper.get("hypothetical_stop_level")
    target = paper.get("hypothetical_target_level")
    try:
        values = float(entry), float(stop), float(target)
    except (TypeError, ValueError):
        return None
    return values if values[1] < values[0] < values[2] else None


def _jsonl_bytes(rows: Iterable[Mapping[str, Any]]) -> bytes:
    return b"".join(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False,
                               default=str).encode("utf-8") + b"\n" for row in rows)


def build_dataset(request: CalibrationRequest, source: Path, output: Path) -> dict[str, Any]:
    if output.exists():
        raise ValueError("OUTPUT_DIRECTORY_ALREADY_EXISTS")
    source_manifest, rows = HistoryProvider.load(source)
    if tuple(sorted(source_manifest["symbols"])) != request.symbols:
        raise ValueError("REQUEST_SOURCE_SYMBOL_MISMATCH")
    interval = source_manifest["intervals"]
    if interval["search_start_ms"] > request.period_start_ms or interval["search_end_ms"] < request.period_end_ms:
        raise ValueError("SOURCE_HISTORY_DOES_NOT_COVER_REQUEST_PERIOD")
    candles_by_symbol_tf: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    boundaries: dict[tuple[str, int], dict[str, Any]] = {}
    for row in rows:
        if row["kind"] == "CANDLE":
            candles_by_symbol_tf[(row["symbol"], row["timeframe"])].append(row)
        else:
            boundaries[(row["symbol"], int(row["closed_until_ms"]))] = row
    candle_models: list[Candle5m] = []
    missing_candle_costs = 0
    for symbol in request.symbols:
        values = sorted(candles_by_symbol_tf[(symbol, "5m")], key=lambda item: int(item["open_time_ms"]))
        atr = _atr14(values)
        for row in values:
            open_ms = int(row["open_time_ms"])
            if not request.period_start_ms <= open_ms < request.period_end_ms:
                continue
            boundary = int(row["close_time_ms"]) + 1
            costs = historical_costs(boundaries.get((symbol, boundary), {}))
            missing_candle_costs += int(costs is None)
            candle_models.append(Candle5m(
                symbol=symbol, open_time_ms=open_ms, close_time_ms=int(row["close_time_ms"]),
                open=float(row["open"]), high=float(row["high"]), low=float(row["low"]),
                close=float(row["close"]), atr=atr[open_ms],
                round_trip_cost_bps=None if costs is None else costs["round_trip_cost_bps"],
                checksum=row.get("data_checksum") or fingerprint(row),
            ))
    funnel = FrozenFunnel(source, {"signal.strategy_minimum_score": 0.0})
    observations: list[CausalObservation] = []
    skipped = defaultdict(int)
    for candle in sorted(candle_models, key=lambda item: (item.open_time_ms, item.symbol)):
        boundary = candle.close_time_ms + 1
        try:
            result, cost_blocker, statistics_missing = funnel.run(candle.symbol, boundary)
        except ValueError as error:
            skipped[f"PIPELINE_{error}"] += 1
            continue
        if result.safety_counters.has_violation:
            raise ValueError("CAUSAL_PIPELINE_SAFETY_VIOLATION")
        components = _entry_components(_mapping(result.strategy_payload))
        plan = _plan_values(result)
        costs = historical_costs(boundaries.get((candle.symbol, boundary), {}))
        if components is None:
            skipped["ENTRY_COMPONENTS_UNAVAILABLE"] += 1
            continue
        if plan is None:
            skipped["DOWNSTREAM_PLAN_UNAVAILABLE"] += 1
            continue
        if costs is None or cost_blocker or statistics_missing:
            skipped["HISTORICAL_COST_OR_STATISTICS_UNAVAILABLE"] += 1
            continue
        entry, stop, target = plan
        path = _exit_path(
            symbol=candle.symbol, boundary=boundary, entry=entry, stop=stop, target=target,
            costs=costs, rows_1m=candles_by_symbol_tf[(candle.symbol, "1m")],
            rows_5m=candles_by_symbol_tf[(candle.symbol, "5m")],
            maximum_holding_minutes=request.maximum_holding_minutes,
        )
        if not path:
            skipped["CAUSAL_EXIT_PATH_UNAVAILABLE"] += 1
            continue
        strategy = _mapping(result.strategy_payload)
        cap = strategy.get("strategy_cap_value")
        observations.append(CausalObservation(
            observation_id=fingerprint({"symbol": candle.symbol, "boundary": boundary,
                                        "source": source_manifest["fingerprint"]}),
            symbol=candle.symbol, boundary_ms=boundary,
            direction=str(strategy.get("direction_hint") or _mapping(strategy.get("context")).get(
                "direction_hint") or "NONE"), future_bars_used=False,
            hard_invalid=bool(strategy.get("strategy_failed_gate") in {
                "HARD_INVALIDATION_GATE", "SOURCE_SETUP_STATUS",
            }), entry_components=components,
            entry_penalty=float(strategy.get("strategy_penalty_total") or 0.0),
            entry_cap=float(cap) if cap is not None else 100.0,
            entry_price=entry, stop_price=stop, target_price=target,
            entry_fee_bps=costs["entry_fee_bps"], exit_fee_bps=costs["exit_fee_bps"],
            entry_slippage_bps=costs["entry_slippage_bps"],
            exit_slippage_bps=costs["exit_slippage_bps"], spread_bps=costs["spread_bps"],
            adverse_fill_reserve_bps=costs["adverse_fill_reserve_bps"], exit_path=path,
            module_snapshot={
                "analysis": result.analysis_payload, "setup": result.setup_payload,
                "strategy": result.strategy_payload, "risk": result.risk_payload,
                "paper": result.paper_payload, "module_reasons": result.module_reasons,
                "module_warnings": result.module_warnings,
            },
        ))
    candle_bytes = _jsonl_bytes(item.model_dump(mode="json") for item in candle_models)
    observation_bytes = _jsonl_bytes(item.model_dump(mode="json") for item in observations)
    evidence_quality = "HISTORICAL_VERIFIED" if (
        not source_manifest.get("missing_inputs") and missing_candle_costs == 0
        and observations and not skipped.get("HISTORICAL_COST_OR_STATISTICS_UNAVAILABLE")
    ) else "INCOMPLETE"
    manifest: dict[str, Any] = {
        "schema": DATASET_SCHEMA, "source_schema": source_manifest["schema"],
        "source_fingerprint": source_manifest["fingerprint"], "request_hash": request.identity,
        "symbols": list(request.symbols), "period_start_ms": request.period_start_ms,
        "period_end_ms": request.period_end_ms, "candles_5m": len(candle_models),
        "causal_observations": len(observations), "missing_candle_costs": missing_candle_costs,
        "skipped": dict(sorted(skipped.items())), "evidence_quality": evidence_quality,
        "candles_sha256": sha256(candle_bytes).hexdigest(),
        "observations_sha256": sha256(observation_bytes).hexdigest(),
        "production_mutations": 0, "live_enabled": False,
    }
    manifest["fingerprint"] = fingerprint(manifest)
    output.mkdir(parents=True, exist_ok=False)
    DEFAULT_ARTIFACT_WRITER.atomic_bytes(output / "CANDLES_5M.jsonl", candle_bytes)
    DEFAULT_ARTIFACT_WRITER.atomic_bytes(output / "CAUSAL_OBSERVATIONS.jsonl", observation_bytes)
    DEFAULT_ARTIFACT_WRITER.atomic_bytes(output / "DATASET_MANIFEST.json", json.dumps(
        manifest, sort_keys=True, indent=2, allow_nan=False,
    ).encode("utf-8"))
    return manifest


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--source-history", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    request = CalibrationRequest.model_validate_json(args.request.read_text(encoding="utf-8"))
    try:
        manifest = build_dataset(request, args.source_history, args.output)
    except (OSError, ValueError) as error:
        print("BULL_RUN_DATASET = FAILED")
        print(f"REASON = {error}")
        raise SystemExit(2) from None
    print(json.dumps({key: manifest[key] for key in (
        "evidence_quality", "candles_5m", "causal_observations", "missing_candle_costs",
    )}, sort_keys=True))
    if manifest["evidence_quality"] != "HISTORICAL_VERIFIED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
