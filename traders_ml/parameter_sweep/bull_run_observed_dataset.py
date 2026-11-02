"""Freeze cost-authoritative persisted LONG observations for weight research.

This source is intentionally narrower than the full causal-history builder.  It
selects only boundaries at which the production database persisted an
authoritative Binance account commission snapshot and contemporaneous public
book/depth evidence.  Missing boundaries are never backfilled.  The resulting
manifest therefore says ``HISTORICAL_OBSERVED_SUBSET`` and cannot be confused
with full-market historical verification.
"""

from __future__ import annotations

import argparse
from bisect import bisect_left
from collections import defaultdict
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from sqlalchemy import text

from app.engine_paper import analytical_exit as analytical_exit_module

from .artifact_writer import DEFAULT_ARTIFACT_WRITER
from .bull_run_dataset import _atr14, _entry_components, _exit_path, _mapping, historical_costs
from .bull_run_weights import (
    CalibrationRequest, Candle5m, CausalObservation, DATASET_SCHEMA, ExitPathPoint,
)
from .engine import ReadOnlyResearchDatabase, resolve_database_binding
from .result_search import fingerprint


EVIDENCE_MODE = "HISTORICAL_OBSERVED_SUBSET"
CONSERVATIVE_MODE = "HISTORICAL_CONSERVATIVE_POLICY"
_ORIGINAL_RUN_ENGINE_ANALYSIS = analytical_exit_module.run_engine_analysis


@lru_cache(maxsize=128)
def _cached_engine_analysis(symbol: str, timeframe: str, candles: tuple[Any, ...]) -> Any:
    """Worker-local cache; keys are immutable causal candle windows."""
    return _ORIGINAL_RUN_ENGINE_ANALYSIS(symbol, timeframe, candles)


def _jsonl_bytes(rows: Iterable[Mapping[str, Any]]) -> bytes:
    return b"".join(
        json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False,
                   default=str).encode("utf-8") + b"\n"
        for row in rows
    )


def _historical_costs(paper: Mapping[str, Any], evidence_mode: str) -> dict[str, float] | None:
    geometry = _mapping(_mapping(paper.get("paper_context")).get("scalping_geometry_diagnostics"))
    market_ready = (
        geometry.get("spread_source") == "BINANCE_PUBLIC_BOOK_TICKER"
        and geometry.get("depth_impact_source") == "BINANCE_PUBLIC_MARKET_DATA_DEPTH"
        and geometry.get("economic_input_timestamp_ms") is not None
        and geometry.get("market_source_status") == "READY"
        and geometry.get("book_source_status") == "READY"
    )
    authoritative = (
        geometry.get("commission_authoritative") is True
        and geometry.get("fee_source") == "BINANCE_ACCOUNT_COMMISSION_SNAPSHOT"
        and geometry.get("fee_source_status") == "READY"
        and geometry.get("cost_model_status") == "READY"
    )
    if not market_ready or (evidence_mode == EVIDENCE_MODE and not authoritative):
        return None
    costs = historical_costs({"geometry": geometry})
    if costs is None:
        return None
    if evidence_mode == CONSERVATIVE_MODE:
        # A stale account snapshot is not called authoritative.  The persisted
        # taker cap is admitted only when it is at least the configured 10 bps
        # per side; discounts are deliberately ignored.
        costs["entry_fee_bps"] = max(10.0, costs["entry_fee_bps"])
        costs["exit_fee_bps"] = max(10.0, costs["exit_fee_bps"])
        costs["round_trip_cost_bps"] = sum(
            costs[name] for name in (
                "entry_fee_bps", "exit_fee_bps", "entry_slippage_bps",
                "exit_slippage_bps", "spread_bps", "adverse_fill_reserve_bps",
            )
        )
    return costs


def _geometry_plan(paper: Mapping[str, Any]) -> tuple[float, float, float] | None:
    geometry = _mapping(_mapping(paper.get("paper_context")).get("scalping_geometry_diagnostics"))
    values = (
        geometry.get("normalized_entry", geometry.get("entry")),
        geometry.get("normalized_stop", geometry.get("final_stop")),
        geometry.get("normalized_target", paper.get("hypothetical_target_level")),
    )
    try:
        entry, stop, target = (float(value) for value in values)
    except (TypeError, ValueError):
        return None
    return (entry, stop, target) if stop < entry < target else None


def _load_candles(connection: Any, symbols: Sequence[str], timeframe: str,
                  start_ms: int, end_ms: int) -> dict[str, list[dict[str, Any]]]:
    table = {"1m": "candles_1m", "5m": "candles_5m"}[timeframe]
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    query = text(
        f"SELECT symbol,open_time_ms,close_time_ms,open,high,low,close,volume,data_checksum "
        f"FROM {table} WHERE symbol=:symbol AND is_closed=true "
        "AND open_time_ms>=:start AND open_time_ms<:end ORDER BY open_time_ms"
    )
    for symbol in symbols:
        for raw in connection.execute(query, {"symbol": symbol, "start": start_ms,
                                               "end": end_ms}).mappings():
            row = dict(raw)
            for key in ("open", "high", "low", "close", "volume"):
                row[key] = str(row[key])
            groups[symbol].append(row)
    return groups


def _load_persisted_rows(connection: Any, request: CalibrationRequest,
                         chunk_size: int = 1000) -> tuple[list[dict[str, Any]], dict[str, int]]:
    bounds = connection.execute(text(
        "SELECT min(id),max(id) FROM online_pipeline_results "
        "WHERE trade_profile_id='trade-5m-v2' AND closed_until_ms>=:start AND closed_until_ms<:end"
    ), {"start": request.period_start_ms, "end": request.period_end_ms}).one()
    if bounds[0] is None:
        return [], {"scanned_id_chunks": 0}
    cost_filter = (
        "AND paper_payload_json->'paper_context'->'scalping_geometry_diagnostics'->>"
        "'commission_authoritative'='true' " if request.evidence_mode == EVIDENCE_MODE else ""
    )
    query = text(
        "SELECT id,run_id,symbol,closed_until_ms,"
        "json_build_object("
        "'analysis_status',analysis_payload_json->'analysis_status',"
        "'direction',analysis_payload_json->'direction',"
        "'market_regime',analysis_payload_json->'market_regime',"
        "'confidence',analysis_payload_json->'confidence',"
        "'impulse_phase',analysis_payload_json->'impulse_phase',"
        "'trend',analysis_payload_json->'trend',"
        "'reasons',analysis_payload_json->'reasons',"
        "'warnings',analysis_payload_json->'warnings') AS analysis,"
        "json_build_object("
        "'setup_status',setup_payload_json->'setup_status',"
        "'setup_type',setup_payload_json->'setup_type',"
        "'direction_hint',setup_payload_json->'direction_hint',"
        "'setup_quality',setup_payload_json->'setup_quality',"
        "'setup_quality_score',setup_payload_json->'setup_quality_score',"
        "'confirmation',setup_payload_json->'confirmation',"
        "'rejection_reasons',setup_payload_json->'rejection_reasons',"
        "'decision_reasons',setup_payload_json->'decision_reasons') AS setup,"
        "json_build_object("
        "'direction_hint',strategy_payload_json->'direction_hint',"
        "'decision_status',strategy_payload_json->'decision_status',"
        "'strategy_type',strategy_payload_json->'strategy_type',"
        "'strategy_score',strategy_payload_json->'strategy_score',"
        "'strategy_quality',strategy_payload_json->'strategy_quality',"
        "'strategy_penalty_total',strategy_payload_json->'strategy_penalty_total',"
        "'strategy_cap_value',strategy_payload_json->'strategy_cap_value',"
        "'strategy_failed_gate',strategy_payload_json->'strategy_failed_gate',"
        "'strategy_failed_gate_reason',strategy_payload_json->'strategy_failed_gate_reason',"
        "'decision_reasons',strategy_payload_json->'decision_reasons',"
        "'rejection_reasons',strategy_payload_json->'rejection_reasons',"
        "'context',json_build_object('scalping_score_decomposition',"
        "strategy_payload_json->'context'->'scalping_score_decomposition')) AS strategy,"
        "json_build_object("
        "'decision_status',risk_payload_json->'decision_status',"
        "'reason_codes',risk_payload_json->'reason_codes',"
        "'rejection_reasons',risk_payload_json->'rejection_reasons') AS risk,"
        "json_build_object('paper_status',paper_payload_json->'paper_status',"
        "'hypothetical_entry_reference',paper_payload_json->'hypothetical_entry_reference',"
        "'hypothetical_stop_level',paper_payload_json->'hypothetical_stop_level',"
        "'hypothetical_target_level',paper_payload_json->'hypothetical_target_level',"
        "'paper_context',json_build_object('scalping_geometry_diagnostics',json_build_object("
        "'normalized_entry',paper_payload_json->'paper_context'->'scalping_geometry_diagnostics'->'normalized_entry',"
        "'entry',paper_payload_json->'paper_context'->'scalping_geometry_diagnostics'->'entry',"
        "'normalized_stop',paper_payload_json->'paper_context'->'scalping_geometry_diagnostics'->'normalized_stop',"
        "'final_stop',paper_payload_json->'paper_context'->'scalping_geometry_diagnostics'->'final_stop',"
        "'normalized_target',paper_payload_json->'paper_context'->'scalping_geometry_diagnostics'->'normalized_target',"
        "'entry_fee_bps',paper_payload_json->'paper_context'->'scalping_geometry_diagnostics'->'entry_fee_bps',"
        "'exit_fee_bps',paper_payload_json->'paper_context'->'scalping_geometry_diagnostics'->'exit_fee_bps',"
        "'entry_slippage_bps',paper_payload_json->'paper_context'->'scalping_geometry_diagnostics'->'entry_slippage_bps',"
        "'exit_slippage_bps',paper_payload_json->'paper_context'->'scalping_geometry_diagnostics'->'exit_slippage_bps',"
        "'spread_bps',paper_payload_json->'paper_context'->'scalping_geometry_diagnostics'->'spread_bps',"
        "'adverse_fill_reserve_bps',paper_payload_json->'paper_context'->'scalping_geometry_diagnostics'->'adverse_fill_reserve_bps',"
        "'effective_total_cost_bps',paper_payload_json->'paper_context'->'scalping_geometry_diagnostics'->'effective_total_cost_bps',"
        "'total_cost_bps',paper_payload_json->'paper_context'->'scalping_geometry_diagnostics'->'total_cost_bps',"
        "'commission_authoritative',paper_payload_json->'paper_context'->'scalping_geometry_diagnostics'->'commission_authoritative',"
        "'fee_source',paper_payload_json->'paper_context'->'scalping_geometry_diagnostics'->'fee_source',"
        "'spread_source',paper_payload_json->'paper_context'->'scalping_geometry_diagnostics'->'spread_source',"
        "'depth_impact_source',paper_payload_json->'paper_context'->'scalping_geometry_diagnostics'->'depth_impact_source',"
        "'economic_input_timestamp_ms',paper_payload_json->'paper_context'->'scalping_geometry_diagnostics'->'economic_input_timestamp_ms',"
        "'market_source_status',paper_payload_json->'paper_context'->'scalping_geometry_diagnostics'->'market_source_status',"
        "'book_source_status',paper_payload_json->'paper_context'->'scalping_geometry_diagnostics'->'book_source_status',"
        "'fee_source_status',paper_payload_json->'paper_context'->'scalping_geometry_diagnostics'->'fee_source_status',"
        "'cost_model_status',paper_payload_json->'paper_context'->'scalping_geometry_diagnostics'->'cost_model_status',"
        "'commission_snapshot_id',paper_payload_json->'paper_context'->'scalping_geometry_diagnostics'->'commission_snapshot_id',"
        "'bid',paper_payload_json->'paper_context'->'scalping_geometry_diagnostics'->'bid',"
        "'ask',paper_payload_json->'paper_context'->'scalping_geometry_diagnostics'->'ask'))) AS paper,"
        "module_reasons_json AS module_reasons,module_warnings_json AS module_warnings "
        "FROM online_pipeline_results WHERE id>=:lower AND id<:upper "
        "AND trade_profile_id='trade-5m-v2' AND closed_until_ms>=:start AND closed_until_ms<:end "
        "AND strategy_payload_json->>'direction_hint'='BULLISH' "
        "AND strategy_payload_json->'context'->'scalping_score_decomposition'->'components' IS NOT NULL "
        + cost_filter
    )
    rows: list[dict[str, Any]] = []
    chunks = 0
    for lower in range(int(bounds[0]), int(bounds[1]) + 1, chunk_size):
        chunks += 1
        for raw in connection.execute(query, {
            "lower": lower, "upper": lower + chunk_size,
            "start": request.period_start_ms, "end": request.period_end_ms,
        }).mappings():
            rows.append(dict(raw))
        if chunks % 10 == 0:
            print(f"OBSERVED_DATASET_SCAN chunks={chunks} selected={len(rows)}", flush=True)
    return rows, {"scanned_id_chunks": chunks, "selected_persisted_rows": len(rows)}


def _slice(rows: Sequence[dict[str, Any]], opens: Sequence[int], start: int,
           end: int) -> Sequence[dict[str, Any]]:
    return rows[bisect_left(opens, start):bisect_left(opens, end)]


def _exit_task(payload: tuple[Any, ...]) -> tuple[Any, ...]:
    # ``analyze_position_exit`` resolves this module global at call time.  The
    # replacement exists only inside spawned research workers and avoids
    # recalculating identical overlapping 1m/5m analysis windows.
    analytical_exit_module.run_engine_analysis = _cached_engine_analysis
    symbol, boundary, entry, stop, target, costs, one_rows, five_rows, holding = payload
    return _exit_path(
        symbol=symbol, boundary=boundary, entry=entry, stop=stop, target=target,
        costs=costs, rows_1m=one_rows, rows_5m=five_rows,
        maximum_holding_minutes=holding,
    )


def build_observed_dataset(request: CalibrationRequest, output: Path) -> dict[str, Any]:
    if request.evidence_mode not in {EVIDENCE_MODE, CONSERVATIVE_MODE}:
        raise ValueError("REQUEST_MUST_EXPLICITLY_SELECT_AN_OBSERVED_EVIDENCE_MODE")
    if output.exists():
        raise ValueError("OUTPUT_DIRECTORY_ALREADY_EXISTS")
    database = ReadOnlyResearchDatabase(resolve_database_binding())
    try:
        with database.connection() as connection:
            connection.exec_driver_sql("SET LOCAL statement_timeout='300000ms'")
            if connection.execute(text("SELECT current_setting('transaction_read_only')")).scalar_one() != "on":
                raise ValueError("READONLY_SESSION_REQUIRED")
            persisted, scan = _load_persisted_rows(connection, request)
            warmup_start = request.period_start_ms - 10 * 60 * 60_000
            tail_end = request.period_end_ms + request.maximum_holding_minutes * 60_000
            one = _load_candles(connection, request.symbols, "1m", warmup_start, tail_end)
            five = _load_candles(connection, request.symbols, "5m", warmup_start, tail_end)
            alembic = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    finally:
        database.dispose()

    costs_by_boundary: dict[tuple[str, int], dict[str, float]] = {}
    accepted_rows: list[tuple[dict[str, Any], dict[str, float], tuple[float, float, float]]] = []
    rejected: dict[str, int] = defaultdict(int)
    for row in persisted:
        costs = _historical_costs(_mapping(row.get("paper")), request.evidence_mode)
        plan = _geometry_plan(_mapping(row.get("paper")))
        components = _entry_components(_mapping(row.get("strategy")))
        if costs is None:
            rejected["COST_PROVENANCE_INVALID"] += 1
        elif plan is None:
            rejected["LONG_GEOMETRY_UNAVAILABLE"] += 1
        elif components is None:
            rejected["ENTRY_COMPONENTS_UNAVAILABLE"] += 1
        else:
            accepted_rows.append((row, costs, plan))
            costs_by_boundary[(str(row["symbol"]), int(row["closed_until_ms"]))] = costs

    candle_models: list[Candle5m] = []
    for symbol in request.symbols:
        values = five[symbol]
        atr = _atr14(values)
        for row in values:
            open_ms = int(row["open_time_ms"])
            if not request.period_start_ms <= open_ms < request.period_end_ms:
                continue
            boundary = int(row["close_time_ms"]) + 1
            costs = costs_by_boundary.get((symbol, boundary))
            candle_models.append(Candle5m(
                symbol=symbol, open_time_ms=open_ms, close_time_ms=int(row["close_time_ms"]),
                open=float(row["open"]), high=float(row["high"]), low=float(row["low"]),
                close=float(row["close"]), atr=atr[open_ms],
                round_trip_cost_bps=None if costs is None else costs["round_trip_cost_bps"],
                checksum=row.get("data_checksum") or fingerprint(row),
            ))

    opens_1m = {symbol: [int(row["open_time_ms"]) for row in rows] for symbol, rows in one.items()}
    opens_5m = {symbol: [int(row["open_time_ms"]) for row in rows] for symbol, rows in five.items()}
    ordered_rows = sorted(
        accepted_rows, key=lambda item: (int(item[0]["closed_until_ms"]), str(item[0]["symbol"]))
    )

    def task(item: tuple[dict[str, Any], dict[str, float], tuple[float, float, float]]) -> tuple[Any, ...]:
        row, costs, plan = item
        symbol = str(row["symbol"])
        boundary = int(row["closed_until_ms"])
        entry, stop, target = plan
        one_rows = _slice(one[symbol], opens_1m[symbol], boundary - 121 * 60_000,
                          boundary + request.maximum_holding_minutes * 60_000)
        five_rows = _slice(five[symbol], opens_5m[symbol], boundary - 121 * 300_000,
                           boundary + request.maximum_holding_minutes * 60_000)
        return (
            symbol, boundary, entry, stop, target, costs, tuple(one_rows), tuple(five_rows),
            request.maximum_holding_minutes,
        )

    checkpoint = output.with_name(output.name + ".exit_paths.checkpoint.jsonl")
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    paths: list[tuple[Any, ...] | None] = [None] * len(ordered_rows)
    if checkpoint.exists():
        for line in checkpoint.read_bytes().splitlines():
            saved = json.loads(line)
            saved_index = int(saved["index"])
            if 0 <= saved_index < len(paths):
                paths[saved_index] = tuple(
                    ExitPathPoint.model_validate(value) for value in saved["path"]
                )
        print(f"OBSERVED_DATASET_EXIT_CHECKPOINT restored={sum(value is not None for value in paths)}",
              flush=True)
    maximum_workers = 4
    with ProcessPoolExecutor(max_workers=maximum_workers) as executor:
        pending: dict[Any, int] = {}
        next_index = 0
        while next_index < len(ordered_rows) or pending:
            while next_index < len(ordered_rows) and len(pending) < maximum_workers * 2:
                if paths[next_index] is None:
                    pending[executor.submit(_exit_task, task(ordered_rows[next_index]))] = next_index
                next_index += 1
            if not pending:
                continue
            completed, _ = wait(tuple(pending), return_when=FIRST_COMPLETED)
            for future in completed:
                index = pending.pop(future)
                paths[index] = future.result()
                with checkpoint.open("ab") as handle:
                    handle.write(json.dumps({
                        "index": index,
                        "path": [value.model_dump(mode="json") for value in paths[index] or ()],
                    }, sort_keys=True, separators=(",", ":"), allow_nan=False,
                       default=str).encode("utf-8") + b"\n")
                processed = sum(value is not None for value in paths)
                if processed % 100 == 0:
                    ready = sum(bool(value) for value in paths if value is not None)
                    print(f"OBSERVED_DATASET_EXIT_REPLAY processed={processed} ready={ready}", flush=True)

    observations: list[CausalObservation] = []
    for index, ((row, costs, plan), path) in enumerate(zip(ordered_rows, paths), 1):
        symbol = str(row["symbol"])
        boundary = int(row["closed_until_ms"])
        entry, stop, target = plan
        path = path or ()
        if not path:
            rejected["CAUSAL_EXIT_PATH_UNAVAILABLE"] += 1
            continue
        strategy = _mapping(row.get("strategy"))
        components = _entry_components(strategy)
        if components is None:
            rejected["ENTRY_COMPONENTS_UNAVAILABLE"] += 1
            continue
        cap = strategy.get("strategy_cap_value")
        observations.append(CausalObservation(
            observation_id=fingerprint({"run_id": row["run_id"], "boundary": boundary}),
            symbol=symbol, boundary_ms=boundary, direction="BULLISH", future_bars_used=False,
            hard_invalid=bool(strategy.get("strategy_failed_gate") in {
                "HARD_INVALIDATION_GATE", "SOURCE_SETUP_STATUS",
            }),
            entry_components=components,
            entry_penalty=float(strategy.get("strategy_penalty_total") or 0.0),
            entry_cap=float(cap) if cap is not None else 100.0,
            entry_price=entry, stop_price=stop, target_price=target,
            entry_fee_bps=costs["entry_fee_bps"], exit_fee_bps=costs["exit_fee_bps"],
            entry_slippage_bps=costs["entry_slippage_bps"],
            exit_slippage_bps=costs["exit_slippage_bps"], spread_bps=costs["spread_bps"],
            adverse_fill_reserve_bps=costs["adverse_fill_reserve_bps"], exit_path=path,
            module_snapshot={
                "source": "PERSISTED_COST_AUTHORITATIVE_BOUNDARY",
                "run_id": row["run_id"], "analysis": row.get("analysis"),
                "setup": row.get("setup"), "strategy": strategy, "risk": row.get("risk"),
                "paper": row.get("paper"), "module_reasons": row.get("module_reasons"),
                "module_warnings": row.get("module_warnings"),
            },
        ))

    candle_bytes = _jsonl_bytes(item.model_dump(mode="json") for item in candle_models)
    observation_bytes = _jsonl_bytes(item.model_dump(mode="json") for item in observations)
    symbol_counts: dict[str, int] = defaultdict(int)
    for item in observations:
        symbol_counts[item.symbol] += 1
    manifest: dict[str, Any] = {
        "schema": DATASET_SCHEMA, "request_hash": request.identity,
        "symbols": list(request.symbols), "period_start_ms": request.period_start_ms,
        "period_end_ms": request.period_end_ms, "candles_5m": len(candle_models),
        "causal_observations": len(observations), "evidence_quality": request.evidence_mode,
        "selection_scope": (
            "ONLY_PERSISTED_BULLISH_BOUNDARIES_WITH_AUTHORITATIVE_HISTORICAL_COSTS"
            if request.evidence_mode == EVIDENCE_MODE else
            "PERSISTED_BULLISH_BOUNDARIES_WITH_CAUSAL_BOOK_AND_CONSERVATIVE_TAKER_FEE_CAP"
        ),
        "selection_bias_warning": "NOT_FULL_MARKET_COVERAGE; NO_MISSING_BOUNDARY_BACKFILL",
        "cost_provenance": (
            "BINANCE_ACCOUNT_COMMISSION_PLUS_CAUSAL_PUBLIC_BOOK_AND_DEPTH"
            if request.evidence_mode == EVIDENCE_MODE else
            "PERSISTED_10_BPS_PER_SIDE_TAKER_CAP_PLUS_CAUSAL_PUBLIC_BOOK_AND_DEPTH"
        ),
        "observation_counts_by_symbol": dict(sorted(symbol_counts.items())),
        "rejected": dict(sorted(rejected.items())), "scan": scan, "alembic": alembic,
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
    checkpoint.unlink(missing_ok=True)
    return manifest


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    request = CalibrationRequest.model_validate_json(args.request.read_text(encoding="utf-8"))
    try:
        manifest = build_observed_dataset(request, args.output)
    except (OSError, ValueError) as error:
        print("BULL_RUN_OBSERVED_DATASET = FAILED")
        print(f"REASON = {error}")
        raise SystemExit(2) from None
    print(json.dumps({key: manifest[key] for key in (
        "evidence_quality", "candles_5m", "causal_observations", "observation_counts_by_symbol"
    )}, sort_keys=True))


if __name__ == "__main__":
    main()
