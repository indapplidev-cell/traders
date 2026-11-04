"""Ragged-history freeze, conservative costs and end-to-end replay support.

The module is deliberately research-only.  PostgreSQL is opened through the
SELECT-only adapter and every generated artifact is written below a caller
supplied directory.  Production configuration and PAPER/LIVE state are never
mutated here.
"""

from __future__ import annotations

import json
import math
from bisect import bisect_right
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from typing import Any

from pydantic import Field, model_validator
from sqlalchemy import text

from app.engine_paper.scalping_shadow import ShadowCostInputs

from .engine import ReadOnlyResearchDatabase, resolve_database_binding
from .full_pipeline import (
    Contract,
    CoverageSegmentV2,
    FullPipelineCalibrationRequestV2,
    RaggedDatasetManifestV2,
    SymbolCoverageV2,
    default_registry,
    fingerprint,
)
from .historical_replay import _baseline_values, chronological_portfolio_replay

INTERVAL_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "1h": 3_600_000}
TIMEFRAMES = tuple(INTERVAL_MS)


def _json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _percentile(values: Sequence[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    position = (len(ordered) - 1) * quantile
    low, high = math.floor(position), math.ceil(position)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


class HistoricalCostBucketV1(Contract):
    key: str
    sample_size: int = Field(ge=0)
    entry_fee_bps: float = Field(ge=0)
    exit_fee_bps: float = Field(ge=0)
    spread_bps: float = Field(ge=0)
    entry_slippage_bps: float = Field(ge=0)
    exit_slippage_bps: float = Field(ge=0)
    reserve_bps: float = Field(ge=3)

    @property
    def round_trip_bps(self) -> float:
        return (
            self.entry_fee_bps + self.exit_fee_bps + self.spread_bps
            + self.entry_slippage_bps + self.exit_slippage_bps + self.reserve_bps
        )


class HistoricalCostModelV1(Contract):
    version: str = "historical-conservative-cost-model/1"
    quantile: float = Field(default=.90, ge=.90, le=1)
    configured_fee_floor_bps: float = Field(default=10.0, ge=0)
    reserve_floor_bps: float = Field(default=3.0, ge=3)
    observed_start_ms: int | None = None
    observed_end_ms: int | None = None
    observed_rows: int = Field(ge=0)
    buckets: dict[str, HistoricalCostBucketV1]
    source: str = "OBSERVED_OR_MODELLED_CONSERVATIVE"

    @model_validator(mode="after")
    def global_bucket_required(self) -> HistoricalCostModelV1:
        if "GLOBAL" not in self.buckets:
            raise ValueError("GLOBAL conservative cost bucket required")
        return self

    @property
    def identity(self) -> str:
        return fingerprint(self.model_dump(mode="json"))

    def resolve(self, symbol: str, regime: str | None = None) -> tuple[HistoricalCostBucketV1, str]:
        symbol = symbol.upper()
        candidates = []
        if regime:
            candidates.append(f"SYMBOL_REGIME:{symbol}:{regime.upper()}")
        candidates.extend((f"SYMBOL:{symbol}", "GLOBAL"))
        for key in candidates:
            if key in self.buckets:
                provenance = "OBSERVED" if key != "GLOBAL" and self.buckets[key].sample_size >= 20 else "MODELLED_CONSERVATIVE"
                return self.buckets[key], provenance
        raise AssertionError("GLOBAL bucket validation failed")


def _cost_bucket(key: str, rows: Sequence[Mapping[str, Any]], *, fee_floor: float, reserve_floor: float) -> HistoricalCostBucketV1:
    def values(name: str) -> list[float]:
        return [float(row[name]) for row in rows if row.get(name) is not None and float(row[name]) >= 0]

    return HistoricalCostBucketV1(
        key=key,
        sample_size=len(rows),
        entry_fee_bps=max(fee_floor, _percentile(values("entry_fee_bps"), .90)),
        exit_fee_bps=max(fee_floor, _percentile(values("exit_fee_bps"), .90)),
        spread_bps=_percentile(values("spread_bps"), .90),
        entry_slippage_bps=max(0.0, _percentile(values("entry_slippage_bps"), .90)),
        exit_slippage_bps=max(0.0, _percentile(values("exit_slippage_bps"), .90)),
        reserve_bps=max(reserve_floor, _percentile(values("reserve_bps"), .90)),
    )


def fit_cost_model(connection: Any, request: FullPipelineCalibrationRequestV2) -> HistoricalCostModelV1:
    result = connection.execute(text("""
        SELECT r.symbol, r.closed_until_ms,
               COALESCE(r.analysis_payload_json->>'regime',
                        r.analysis_payload_json#>>'{analysis_context,scalping,market_regime}') AS regime,
               NULLIF(r.paper_payload_json#>>'{paper_context,scalping_geometry_diagnostics,entry_fee_bps}','')::double precision AS entry_fee_bps,
               NULLIF(r.paper_payload_json#>>'{paper_context,scalping_geometry_diagnostics,exit_fee_bps}','')::double precision AS exit_fee_bps,
               NULLIF(r.paper_payload_json#>>'{paper_context,scalping_geometry_diagnostics,spread_bps}','')::double precision AS spread_bps,
               NULLIF(r.paper_payload_json#>>'{paper_context,scalping_geometry_diagnostics,entry_slippage_bps}','')::double precision AS entry_slippage_bps,
               NULLIF(r.paper_payload_json#>>'{paper_context,scalping_geometry_diagnostics,exit_slippage_bps}','')::double precision AS exit_slippage_bps,
               NULLIF(r.paper_payload_json#>>'{paper_context,scalping_geometry_diagnostics,adverse_fill_reserve_bps}','')::double precision AS reserve_bps
        FROM online_pipeline_results r
        JOIN online_pipeline_runs u ON u.run_id=r.run_id
        WHERE u.trade_profile_id='trade-5m-v2'
          AND u.paper_status='PAPER_PLAN_READY'
          AND r.closed_until_ms>=:start_ms AND r.closed_until_ms<:end_ms
          AND r.symbol=ANY(:symbols)
    """), {
        "start_ms": request.data_start_ms,
        "end_ms": request.data_end_ms,
        "symbols": list(request.symbols),
    }).mappings()
    rows = [dict(row) for row in result if row.get("entry_fee_bps") is not None]
    grouped: dict[str, list[dict[str, Any]]] = {"GLOBAL": rows}
    for row in rows:
        symbol = str(row["symbol"]).upper()
        grouped.setdefault(f"SYMBOL:{symbol}", []).append(row)
        if row.get("regime"):
            grouped.setdefault(f"SYMBOL_REGIME:{symbol}:{str(row['regime']).upper()}", []).append(row)
    buckets = {
        key: _cost_bucket(key, values, fee_floor=10.0, reserve_floor=3.0)
        for key, values in grouped.items() if key == "GLOBAL" or len(values) >= 5
    }
    if not rows:
        buckets["GLOBAL"] = HistoricalCostBucketV1(
            key="GLOBAL", sample_size=0, entry_fee_bps=10, exit_fee_bps=10,
            spread_bps=5, entry_slippage_bps=2, exit_slippage_bps=2, reserve_bps=3,
        )
    boundaries = [int(row["closed_until_ms"]) for row in rows]
    return HistoricalCostModelV1(
        observed_start_ms=min(boundaries) if boundaries else None,
        observed_end_ms=max(boundaries) if boundaries else None,
        observed_rows=len(rows), buckets=buckets,
    )


def _timeframe_segments(connection: Any, symbol: str, timeframe: str, start_ms: int, end_ms: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    interval = INTERVAL_MS[timeframe]
    table = f"candles_{timeframe}"
    summary = dict(connection.execute(text(f"""
        SELECT min(open_time_ms) AS start_ms,max(open_time_ms) AS maximum_open,
               max(close_time_ms) AS end_ms,count(*) AS rows,
               count(*) FILTER (WHERE NOT is_closed) AS open_rows,
               count(DISTINCT open_time_ms) AS distinct_rows,
               md5(concat(min(open_time_ms),':',max(open_time_ms),':',count(*),':',
                          min(data_checksum),':',max(data_checksum))) AS checksum
        FROM {table}
        WHERE symbol=:symbol AND open_time_ms>=:start_ms AND open_time_ms<:end_ms
    """), {"symbol": symbol, "start_ms": start_ms, "end_ms": end_ms}).mappings().one())
    segments: list[dict[str, Any]] = []
    if summary["start_ms"] is not None:
        expected = (int(summary["maximum_open"]) - int(summary["start_ms"])) // interval + 1
        if int(summary["rows"]) == expected and int(summary["rows"]) == int(summary["distinct_rows"]):
            segments = [summary]
        else:
            # Only anomalous symbol/timeframe pairs pay the cost of fetching
            # boundaries.  Normal contiguous histories stay on the aggregate
            # index path and do not exceed the read-only statement budget.
            boundaries = [tuple(row) for row in connection.execute(text(f"""
                SELECT open_time_ms,close_time_ms,is_closed,data_checksum
                FROM {table}
                WHERE symbol=:symbol AND open_time_ms>=:start_ms AND open_time_ms<:end_ms
                ORDER BY open_time_ms
            """), {"symbol": symbol, "start_ms": start_ms, "end_ms": end_ms})]
            current: list[tuple[Any, ...]] = []
            for row in boundaries:
                if current and int(row[0]) - int(current[-1][0]) != interval:
                    segments.append({
                        "start_ms": int(current[0][0]), "maximum_open": int(current[-1][0]),
                        "end_ms": int(current[-1][1]), "rows": len(current),
                        "open_rows": sum(not bool(item[2]) for item in current),
                        "distinct_rows": len({int(item[0]) for item in current}),
                        "checksum": fingerprint([current[0][3], current[-1][3], len(current)]),
                    })
                    current = []
                current.append(row)
            if current:
                segments.append({
                    "start_ms": int(current[0][0]), "maximum_open": int(current[-1][0]),
                    "end_ms": int(current[-1][1]), "rows": len(current),
                    "open_rows": sum(not bool(item[2]) for item in current),
                    "distinct_rows": len({int(item[0]) for item in current}),
                    "checksum": fingerprint([current[0][3], current[-1][3], len(current)]),
                })
    inventory = {
        "rows": sum(int(row["rows"]) for row in segments),
        "segments": len(segments),
        "gaps": max(0, len(segments) - 1),
        "open_rows": sum(int(row["open_rows"]) for row in segments),
        "duplicate_rows": sum(int(row["rows"]) - int(row["distinct_rows"]) for row in segments),
        "minimum": min((int(row["start_ms"]) for row in segments), default=None),
        "maximum": max((int(row["end_ms"]) for row in segments), default=None),
        "checksums": [str(row["checksum"]) for row in segments],
    }
    return segments, inventory


def _intersect(left: Sequence[tuple[int, int]], right: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    i = j = 0
    while i < len(left) and j < len(right):
        start, end = max(left[i][0], right[j][0]), min(left[i][1], right[j][1])
        if start < end:
            result.append((start, end))
        if left[i][1] <= right[j][1]:
            i += 1
        else:
            j += 1
    return result


def _symbol_coverage(connection: Any, request: FullPipelineCalibrationRequestV2, symbol: str) -> SymbolCoverageV2:
    all_segments: list[tuple[int, int]] | None = None
    inventory: dict[str, dict[str, Any]] = {}
    reasons: list[str] = []
    for timeframe in TIMEFRAMES:
        segments, info = _timeframe_segments(
            connection, symbol, timeframe, request.data_start_ms, request.data_end_ms,
        )
        inventory[timeframe] = info
        if info["open_rows"]:
            reasons.append(f"UNCLOSED_CANDLES:{timeframe}")
        if info["duplicate_rows"]:
            reasons.append(f"DUPLICATE_BOUNDARIES:{timeframe}")
        values = [(int(row["start_ms"]), int(row["end_ms"])) for row in segments if not int(row["open_rows"])]
        all_segments = values if all_segments is None else _intersect(all_segments, values)
    warmup_ms = max(INTERVAL_MS[name] * bars for name, bars in request.warmup_bars.items())
    minimum_ms = request.minimum_segment_bars_5m * INTERVAL_MS["5m"]
    usable = [(start + warmup_ms, end) for start, end in (all_segments or ()) if end - start - warmup_ms >= minimum_ms]
    coverage_segments = tuple(CoverageSegmentV2(
        start_ms=start, end_ms=end, rows_5m=max(0, (end - start) // INTERVAL_MS["5m"]),
    ) for start, end in usable)
    raw_starts = [info["minimum"] for info in inventory.values() if info["minimum"] is not None]
    raw_ends = [info["maximum"] for info in inventory.values() if info["maximum"] is not None]
    if not coverage_segments:
        status = "UNUSABLE"
        reasons.append("NO_COMMON_CAUSAL_SEGMENT_AFTER_WARMUP")
    else:
        partial = coverage_segments[0].start_ms > request.data_start_ms or any(info["gaps"] for info in inventory.values())
        status = "PARTIAL_COVERAGE" if partial else "USABLE"
        if coverage_segments[0].start_ms > request.data_start_ms:
            reasons.append("LATE_HISTORY_START_ACCEPTED")
        if any(info["gaps"] for info in inventory.values()):
            reasons.append("GAPS_SEGMENTED")
    participation = {
        window.name: any(segment.start_ms < window.end_ms and segment.end_ms > window.start_ms for segment in coverage_segments)
        for window in request.windows
    }
    return SymbolCoverageV2(
        symbol=symbol, status=status,
        available_start_ms=min(raw_starts) if raw_starts else None,
        available_end_ms=max(raw_ends) if raw_ends else None,
        usable_start_ms=coverage_segments[0].start_ms if coverage_segments else None,
        usable_end_ms=coverage_segments[-1].end_ms if coverage_segments else None,
        segments=coverage_segments, timeframe_inventory=inventory,
        fold_participation=participation, reasons=tuple(sorted(set(reasons))),
    )


def freeze_ragged_dataset(request_path: Path, output: Path, database_url: str | None = None) -> RaggedDatasetManifestV2:
    if output.exists():
        raise FileExistsError(output)
    request = FullPipelineCalibrationRequestV2.model_validate_json(request_path.read_text(encoding="utf-8"))
    database = ReadOnlyResearchDatabase(resolve_database_binding(explicit_url=database_url))
    try:
        coverage_values = []
        # Bound transaction lifetime per symbol.  Long 1m inventories must not
        # turn a healthy read-only database into one monolithic snapshot.
        for symbol in request.symbols:
            with database.connection() as connection:
                coverage_values.append(_symbol_coverage(connection, request, symbol))
        symbols = tuple(coverage_values)
        with database.connection() as connection:
            cost_model = fit_cost_model(connection, request)
    finally:
        database.dispose()
    usable = tuple(item for item in symbols if item.status != "UNUSABLE")
    blocked: list[str] = []
    if not usable:
        blocked.append("NO_USABLE_SYMBOL_HISTORY")
    internal = next(window for window in request.windows if window.role == "INTERNAL_HOLDOUT")
    if not any(item.fold_participation.get(internal.name, False) for item in usable):
        blocked.append("NO_INTERNAL_HOLDOUT_COVERAGE")
    body = {
        "version": "ragged-full-pipeline-dataset/2",
        "request_hash": request.identity,
        "registry_hash": default_registry().identity,
        "status": "BLOCKED_DATA" if blocked else "FROZEN",
        "symbols": [item.model_dump(mode="json") for item in symbols],
        "usable_symbol_count": len(usable),
        "partial_symbol_count": sum(item.status == "PARTIAL_COVERAGE" for item in symbols),
        "historical_cost_evidence": {
            "observed_rows": cost_model.observed_rows,
            "minimum_boundary_ms": cost_model.observed_start_ms,
            "maximum_boundary_ms": cost_model.observed_end_ms,
            "modelled_before_ms": cost_model.observed_start_ms,
        },
        "cost_model_hash": cost_model.identity,
        "blocked_reasons": blocked,
        "closed_only_required": True,
        "production_mutations": 0,
    }
    body["dataset_hash"] = fingerprint(body)
    manifest = RaggedDatasetManifestV2.model_validate(body)
    output.mkdir(parents=True)
    _json(output / "REQUEST.json", request.model_dump(mode="json"))
    _json(output / "PARAMETER_REGISTRY.json", default_registry().model_dump(mode="json"))
    _json(output / "HISTORICAL_COST_MODEL.json", cost_model.model_dump(mode="json"))
    _json(output / "DATASET_MANIFEST.json", manifest.model_dump(mode="json"))
    return manifest


class HistoricalConservativeCostSource:
    """PipelineRunner cost adapter; every value is causal or conservative."""

    def __init__(self, model: HistoricalCostModelV1) -> None:
        self.model = model
        self.boundary_ms = 0
        self.regime: str | None = None

    def load(self, symbol: str, entry: float, *, safety_margin_bps: float) -> ShadowCostInputs:
        bucket, provenance = self.model.resolve(symbol, self.regime)
        return ShadowCostInputs(
            entry_fee_bps=bucket.entry_fee_bps, exit_fee_bps=bucket.exit_fee_bps,
            entry_slippage_bps=bucket.entry_slippage_bps,
            exit_slippage_bps=bucket.exit_slippage_bps,
            safety_margin_bps=max(0.0, float(safety_margin_bps)),
            adverse_fill_reserve_bps=max(3.0, bucket.reserve_bps),
            fee_source=f"HISTORICAL_COST_MODEL:{provenance}",
            commission_authoritative=True,
            commission_symbol=symbol.upper(),
            commission_snapshot_id=f"research:{self.model.identity[:16]}:{symbol.upper()}",
            spread_bps=bucket.spread_bps,
            spread_source=f"HISTORICAL_COST_MODEL:{provenance}",
            spread_authoritative=True,
            depth_impact_bps=0.0,
            depth_impact_source=f"HISTORICAL_COST_MODEL:{provenance}",
            depth_authoritative=True,
            economic_input_timestamp_ms=self.boundary_ms,
            economic_capture_started_at_ms=self.boundary_ms,
            decision_cutoff_timestamp_ms=self.boundary_ms,
            economic_input_source=f"HISTORICAL_COST_MODEL:{provenance}",
            maximum_age_ms=1,
            require_causal_timestamp=True,
            market_source_status="READY",
            fee_source_status="READY",
            book_source_status="READY",
            cost_model_status="READY",
        )


@dataclass(slots=True)
class FullPipelineReplayEngineV1:
    """Deterministic portfolio evaluator over production-derived opportunities."""

    rows: list[dict[str, Any]]
    initial_equity: float = 1000.0

    def split(self, windows: Sequence[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        result: dict[str, list[dict[str, Any]]] = {str(window["name"]): [] for window in windows}
        for row in self.rows:
            boundary = int(row["boundary_ms"])
            matches = [window for window in windows if int(window["start_ms"]) <= boundary < int(window["end_ms"])]
            if len(matches) > 1:
                raise ValueError("OVERLAPPING_REPLAY_WINDOWS")
            if matches:
                result[str(matches[0]["name"])].append(row)
        return result

    def evaluate(self, parameters: Mapping[str, object], rows: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
        resolved = _baseline_values()
        resolved.update(parameters)
        return chronological_portfolio_replay(
            [dict(row) for row in (self.rows if rows is None else rows)],
            resolved, starting_balance=self.initial_equity,
        )

    def symbol_day_score(self, trades: Iterable[Mapping[str, Any]]) -> float:
        groups: dict[tuple[str, str], list[float]] = {}
        for trade in trades:
            day = datetime.fromtimestamp(int(trade["closed_at_ms"]) / 1000, UTC).date().isoformat()
            groups.setdefault((str(trade["symbol"]), day), []).append(float(trade["net_pnl"]))
        if not groups:
            return float("-inf")
        # Each symbol/day contributes once irrespective of candle-history depth.
        return median(sum(values) / len(values) for values in groups.values())


def attach_market_paths(rows: list[dict[str, Any]], candles: Mapping[str, Sequence[Mapping[str, Any]]], horizon_ms: int) -> None:
    """Attach post-boundary paths without exposing them to decision features."""

    by_symbol: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_symbol.setdefault(str(row["symbol"]), []).append(row)
    for symbol, opportunities in by_symbol.items():
        values = list(candles.get(symbol, ()))
        closes = [int(item["close_time_ms"]) for item in values]
        for row in opportunities:
            boundary = int(row["boundary_ms"])
            start = bisect_right(closes, boundary)
            end = bisect_right(closes, boundary + horizon_ms)
            row["market_path_1m"] = [dict(item) for item in values[start:end]]


def _candidate_from_observation(observation: Mapping[str, Any]) -> dict[str, Any] | None:
    def number(value: object, default: float | None = None) -> float | None:
        try:
            result = float(value)  # type: ignore[arg-type]
            return result if math.isfinite(result) else default
        except (TypeError, ValueError):
            return default

    entry = number(observation.get("entry_reference"))
    stop = number(observation.get("stop_reference"))
    target = number(observation.get("target_reference"))
    direction = str(observation.get("direction") or "")
    if direction not in {"LONG", "BULLISH"} or None in {entry, stop, target}:
        return None
    entry, stop, target = float(entry), float(stop), float(target)
    if min(entry, stop, target) <= 0 or stop >= entry or target <= entry:
        return None
    cost_parts = [
        float(number(observation.get(name), 0.0) or 0.0) for name in (
            "entry_fee_bps", "exit_fee_bps", "spread_bps",
            "entry_slippage_bps", "exit_slippage_bps", "depth_impact_bps",
        )
    ]
    boundary = int(observation["closed_until_ms"])
    symbol = str(observation["symbol"])
    identity = str(observation.get("observation_id") or f"{symbol}:{boundary}:LONG")
    probability = observation.get("probability_inputs") or {}
    ev = observation.get("ev_inputs") or {}
    return {
        "candidate_id": identity,
        "causal_opportunity": identity,
        "causal_identity": identity,
        "run_id": identity,
        "symbol": symbol,
        "boundary_ms": boundary,
        "opened_at_ms": boundary,
        "direction": "LONG",
        "setup_type": str(observation.get("setup_type") or "UNKNOWN"),
        "setup_status": str(observation.get("setup_status") or "UNKNOWN"),
        "structural_setup": True,
        "entry_price": entry,
        "stop_price": stop,
        "target_price": target,
        "stop_distance_bps": (entry - stop) / entry * 10_000,
        "target_distance_bps": (target - entry) / entry * 10_000,
        "gross_rr": number(observation.get("gross_rr")),
        "net_rr": number(observation.get("net_rr")),
        "effective_total_cost_bps": sum(cost_parts),
        "adverse_fill_reserve_bps": 3.0,
        "entry_slippage_bps": float(number(observation.get("entry_slippage_bps"), 0.0) or 0.0),
        "probability_sample_size": int(number(probability.get("sample_size"), 0.0) or 0),
        "p_win_raw": number(observation.get("p_win_raw")),
        "expected_ev_r": number(observation.get("expected_ev_r")),
        "ev_reserve": number(ev.get("reserve")),
        "net_edge_bps": max(0.0, (target - entry) / entry * 10_000 - sum(cost_parts)),
        "strategy_score": float(number(observation.get("strategy_score"), 0.0) or 0.0),
        "risk_score": float(number(observation.get("strategy_score"), 0.0) or 0.0),
        "causal_reset_conditions": 1,
        "one_min_confirmation_count": 1,
        "cost_provenance": str(observation.get("cost_provenance") or "HISTORICAL_COST_MODEL"),
        "regime": str(observation.get("regime") or "UNKNOWN"),
    }


def _trace_from_observation(observation: Mapping[str, Any], dataset_hash: str, configuration_hash: str) -> dict[str, Any]:
    setup_pass = str(observation.get("setup_status")) == "SETUP_CANDIDATE"
    strategy_pass = str(observation.get("strategy_status")) in {
        "ALLOW_RESEARCH_TRADE_PLAN", "APPROVED", "ADMITTED", "PASS",
    }
    risk_pass = str(observation.get("risk_status")) in {
        "RISK_APPROVED", "APPROVED", "PASS", "ALLOW_RESEARCH_TRADE_PLAN",
    }
    geometry_pass = bool(observation.get("entry_reference") and observation.get("stop_reference") and observation.get("target_reference"))
    decisions = [{"stage": "ANALYSIS", "passed": True, "reason": "PRODUCTION_ANALYSIS_COMPLETED"}]
    for stage, passed, reason in (
        ("STRUCTURAL_SETUP", setup_pass, str(observation.get("rejection_reason") or "SETUP_CANDIDATE")),
        ("STRATEGY_ADMISSION", strategy_pass, str(observation.get("rejection_reason") or "STRATEGY_ADMITTED")),
        ("RISK_COMPATIBILITY", risk_pass, str(observation.get("rejection_reason") or "RISK_COMPATIBLE")),
        ("GEOMETRY", geometry_pass, str(observation.get("rejection_reason") or "GEOMETRY_AVAILABLE")),
    ):
        decisions.append({"stage": stage, "passed": passed, "reason": reason})
        if not passed:
            break
    terminal = next((item["stage"] for item in decisions if not item["passed"]), decisions[-1]["stage"])
    return {
        "version": "full-pipeline-decision-trace/1",
        "trace_id": str(observation.get("observation_id")),
        "configuration_hash": configuration_hash,
        "dataset_hash": dataset_hash,
        "symbol": str(observation["symbol"]),
        "boundary_ms": int(observation["closed_until_ms"]),
        "direction": "LONG",
        "decisions": decisions,
        "terminal_stage": terminal,
        "future_bars_used": False,
    }


def reconstruct_baseline(
    request_path: Path, dataset: Path, output: Path, database_url: str | None = None,
) -> dict[str, Any]:
    """Run the native production analysis chain over every usable 5m boundary.

    Per-symbol artifacts and done markers make the operation safely resumable.
    Holdout rows are written to a separate locked file and are not evaluated.
    """

    from app.config.trade_parameters import load_trade_parameters
    from app.engine_orchestrator.orchestrator_config import OrchestratorConfig
    from app.engine_orchestrator.pipeline_result import json_safe
    from app.engine_orchestrator.pipeline_runner import PipelineRunner
    from app.engine_paper.scalping_paper_runner import ScalpingPaperRunner

    from .historical_reconstruction import (
        SOURCE_RECONSTRUCTED,
        CausalCandleRepository,
        _load_candles,
        canonical_observation,
    )

    request = FullPipelineCalibrationRequestV2.model_validate_json(request_path.read_text(encoding="utf-8"))
    manifest = RaggedDatasetManifestV2.model_validate_json((dataset / "DATASET_MANIFEST.json").read_text(encoding="utf-8"))
    if manifest.status != "FROZEN":
        raise ValueError("RAGGED_DATASET_NOT_FROZEN")
    cost_model = HistoricalCostModelV1.model_validate_json((dataset / "HISTORICAL_COST_MODEL.json").read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)
    configuration_hash = fingerprint(_baseline_values())
    resolved_parameters = load_trade_parameters().resolve_scalping_v2_parameter_set()
    internal = next(window for window in request.windows if window.role == "INTERNAL_HOLDOUT")
    database = ReadOnlyResearchDatabase(resolve_database_binding(explicit_url=database_url))
    totals = {"boundaries": 0, "opportunities": 0, "symbols": 0}
    try:
        for coverage in manifest.symbols:
            if coverage.status == "UNUSABLE":
                continue
            symbol_dir = output / "symbols" / coverage.symbol
            done = symbol_dir / "DONE.json"
            if done.exists():
                value = json.loads(done.read_text(encoding="utf-8"))
                for name in totals:
                    totals[name] += int(value.get(name, 0))
                continue
            symbol_dir.mkdir(parents=True, exist_ok=True)
            trace_path = symbol_dir / "DECISION_TRACES.jsonl"
            row_path = symbol_dir / "REPLAY_ROWS.jsonl"
            holdout_path = symbol_dir / "HOLDOUT_ROWS.locked.jsonl"
            checkpoint_path = symbol_dir / "CHECKPOINT.json"
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8")) if checkpoint_path.exists() else {}
            symbol_counts = {
                "boundaries": int(checkpoint.get("boundaries", 0)),
                "opportunities": int(checkpoint.get("opportunities", 0)),
                "symbols": 1,
            }
            last_boundary = int(checkpoint.get("last_boundary_ms", -1))
            file_mode = "a" if checkpoint else "w"
            if checkpoint:
                for partial in (trace_path, row_path, holdout_path):
                    _truncate_to_checkpoint(partial, last_boundary)
            with database.connection() as connection, trace_path.open(file_mode, encoding="utf-8") as traces, row_path.open(file_mode, encoding="utf-8") as replay_rows, holdout_path.open(file_mode, encoding="utf-8") as holdout_rows:
                connection.execute(text("SET LOCAL statement_timeout = '10min'"))
                for segment in coverage.segments:
                    warmup_start = max(request.data_start_ms, segment.start_ms - max(
                        INTERVAL_MS[name] * value for name, value in request.warmup_bars.items()
                    ))
                    tail_end = min(request.data_end_ms, segment.end_ms + 45 * 60_000)
                    candles = _load_candles(connection, coverage.symbol, warmup_start, tail_end)
                    repository = CausalCandleRepository(coverage.symbol, candles)
                    cost_source = HistoricalConservativeCostSource(cost_model)
                    config = OrchestratorConfig(symbols=(coverage.symbol,), trade_profile_id="trade-5m-v2", primary_timeframe="5m")
                    paper_runner = ScalpingPaperRunner(
                        runtime_parameters=config.runtime_parameters,
                        cost_source=cost_source,
                        clock_ms=lambda source=cost_source: source.boundary_ms,
                    )
                    runner = PipelineRunner(
                        config, repository, paper_runner=paper_runner,
                        resolved_parameter_set=resolved_parameters,
                    )
                    boundaries = [
                        int(item.close_time_ms) + 1 for item in candles["5m"]
                        if segment.start_ms <= int(item.close_time_ms) + 1 < segment.end_ms
                        and int(item.close_time_ms) + 1 > last_boundary
                    ]
                    query_params = {
                        "symbol": coverage.symbol,
                        "start_ms": segment.start_ms,
                        "end_ms": segment.end_ms,
                    }
                    persisted_status: dict[int, dict[str, Any]] = {}
                    persisted_candidates: dict[int, dict[str, Any]] = {}
                    chunk_start = segment.start_ms
                    while chunk_start < segment.end_ms:
                        chunk_end = min(segment.end_ms, chunk_start + 7 * 86_400_000)
                        chunk_params = {**query_params, "start_ms": chunk_start, "end_ms": chunk_end}
                        persisted_status.update({
                            int(row["closed_until_ms"]): dict(row)
                            for row in connection.execute(text("""
                            SELECT run_id,symbol,primary_timeframe,closed_until_ms,
                                   trade_profile_id,analysis_status,setup_status,
                                   strategy_status,risk_status,paper_status,
                                   final_reason,future_bars_used
                            FROM online_pipeline_runs
                            WHERE trade_profile_id='trade-5m-v2' AND symbol=:symbol
                              AND closed_until_ms>=:start_ms AND closed_until_ms<:end_ms
                            """), chunk_params).mappings()
                        })
                        persisted_candidates.update({
                            int(row["closed_until_ms"]): dict(row)
                            for row in connection.execute(text("""
                            SELECT res.run_id,res.symbol,res.closed_until_ms,
                                   concat('persisted:',res.symbol,':',res.closed_until_ms) AS observation_id,
                                   res.setup_payload_json->>'setup_type' AS setup_type,
                                   res.setup_payload_json->>'status' AS setup_status,
                                   COALESCE(res.setup_payload_json->>'direction_hint',
                                            res.strategy_payload_json->>'direction_hint') AS direction,
                                   res.strategy_payload_json->>'strategy_score' AS strategy_score,
                                   res.strategy_payload_json->>'decision_status' AS strategy_status,
                                   res.risk_payload_json->>'risk_status' AS risk_status,
                                   COALESCE(res.analysis_payload_json->>'regime',
                                            res.analysis_payload_json#>>'{analysis_context,scalping,market_regime}') AS regime,
                                   res.paper_payload_json->>'hypothetical_entry_reference' AS entry_reference,
                                   res.paper_payload_json->>'hypothetical_stop_level' AS stop_reference,
                                   res.paper_payload_json->>'hypothetical_target_level' AS target_reference,
                                   res.paper_payload_json#>>'{paper_context,scalping_geometry_diagnostics,gross_rr}' AS gross_rr,
                                   res.paper_payload_json#>>'{paper_context,scalping_geometry_diagnostics,net_rr}' AS net_rr,
                                   res.paper_payload_json#>>'{paper_context,scalping_geometry_diagnostics,entry_fee_bps}' AS entry_fee_bps,
                                   res.paper_payload_json#>>'{paper_context,scalping_geometry_diagnostics,exit_fee_bps}' AS exit_fee_bps,
                                   res.paper_payload_json#>>'{paper_context,scalping_geometry_diagnostics,spread_bps}' AS spread_bps,
                                   res.paper_payload_json#>>'{paper_context,scalping_geometry_diagnostics,entry_slippage_bps}' AS entry_slippage_bps,
                                   res.paper_payload_json#>>'{paper_context,scalping_geometry_diagnostics,exit_slippage_bps}' AS exit_slippage_bps,
                                   res.paper_payload_json#>>'{paper_context,scalping_geometry_diagnostics,depth_impact_bps}' AS depth_impact_bps,
                                   res.paper_payload_json#>>'{paper_context,scalping_geometry_diagnostics,fee_source}' AS cost_provenance,
                                   res.paper_payload_json#>>'{paper_context,scalping_geometry_diagnostics,p_win_raw}' AS p_win_raw,
                                   res.paper_payload_json#>>'{paper_context,scalping_geometry_diagnostics,expected_ev_r}' AS expected_ev_r,
                                   jsonb_build_object(
                                     'sample_size',res.paper_payload_json#>>'{paper_context,scalping_geometry_diagnostics,probability_sample_size}'
                                   ) AS probability_inputs,
                                   jsonb_build_object(
                                     'reserve',res.paper_payload_json#>>'{paper_context,scalping_geometry_diagnostics,ev_reserve}'
                                   ) AS ev_inputs,
                                   run.final_reason AS rejection_reason,
                                   run.future_bars_used
                            FROM online_pipeline_runs run
                            JOIN online_pipeline_results res ON res.run_id=run.run_id
                            WHERE run.trade_profile_id='trade-5m-v2' AND run.symbol=:symbol
                              AND run.setup_status='SETUP_CANDIDATE'
                              AND run.closed_until_ms>=:start_ms AND run.closed_until_ms<:end_ms
                            """), chunk_params).mappings()
                        })
                        chunk_start = chunk_end
                    one_minute = [
                        {
                            "open_time_ms": int(item.open_time_ms), "close_time_ms": int(item.close_time_ms),
                            "open": float(item.open), "high": float(item.high), "low": float(item.low),
                            "close": float(item.close),
                            "data_checksum": fingerprint(item.market_values()),
                        } for item in candles["1m"]
                    ]
                    closes = [int(item["close_time_ms"]) for item in one_minute]
                    for boundary in boundaries:
                        cost_source.boundary_ms = boundary
                        raw_result = persisted_status.get(boundary)
                        if raw_result is None:
                            result = runner.run(coverage.symbol, boundary)
                            observation = canonical_observation(result, source_type=SOURCE_RECONSTRUCTED)
                            result_hash = fingerprint(json_safe(result))
                        elif boundary in persisted_candidates:
                            detailed = persisted_candidates[boundary]
                            observation = detailed
                            result_hash = fingerprint(detailed)
                        else:
                            observation = {
                                "observation_id": f"persisted:{coverage.symbol}:{boundary}",
                                "symbol": coverage.symbol, "closed_until_ms": boundary,
                                "setup_status": raw_result.get("setup_status"),
                                "strategy_status": raw_result.get("strategy_status"),
                                "risk_status": raw_result.get("risk_status"),
                                "rejection_reason": raw_result.get("final_reason"),
                                "future_bars_used": bool(raw_result.get("future_bars_used")),
                            }
                            result_hash = fingerprint(raw_result)
                        if observation["future_bars_used"]:
                            raise ValueError("CAUSALITY_VIOLATION_IN_RECONSTRUCTION")
                        traces.write(json.dumps(_trace_from_observation(
                            observation, manifest.dataset_hash, configuration_hash,
                        ), sort_keys=True, default=str) + "\n")
                        symbol_counts["boundaries"] += 1
                        candidate = _candidate_from_observation(observation)
                        if candidate is not None:
                            start = bisect_right(closes, boundary)
                            end = bisect_right(closes, boundary + 45 * 60_000)
                            candidate["market_path_1m"] = one_minute[start:end]
                            candidate["runtime_result_hash"] = result_hash
                            destination = holdout_rows if internal.start_ms <= boundary < internal.end_ms else replay_rows
                            destination.write(json.dumps(candidate, sort_keys=True, default=str) + "\n")
                            symbol_counts["opportunities"] += 1
                        if symbol_counts["boundaries"] % 100 == 0:
                            traces.flush(); replay_rows.flush(); holdout_rows.flush()
                            _json(checkpoint_path, {
                                **symbol_counts, "last_boundary_ms": boundary,
                                "dataset_hash": manifest.dataset_hash,
                            })
                    if boundaries:
                        traces.flush(); replay_rows.flush(); holdout_rows.flush()
                        _json(checkpoint_path, {
                            **symbol_counts, "last_boundary_ms": boundaries[-1],
                            "dataset_hash": manifest.dataset_hash,
                        })
            _json(done, symbol_counts)
            for name in totals:
                totals[name] += symbol_counts[name]
    finally:
        database.dispose()

    trace_files = sorted((output / "symbols").glob("*/DECISION_TRACES.jsonl"))
    replay_files = sorted((output / "symbols").glob("*/REPLAY_ROWS.jsonl"))
    holdout_files = sorted((output / "symbols").glob("*/HOLDOUT_ROWS.locked.jsonl"))
    for target, sources in (
        (output / "DECISION_TRACES.jsonl", trace_files),
        (output / "REPLAY_ROWS.jsonl", replay_files),
        (output / "HOLDOUT_ROWS.locked.jsonl", holdout_files),
    ):
        with target.open("w", encoding="utf-8") as handle:
            for source in sources:
                handle.write(source.read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in (output / "REPLAY_ROWS.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    replay = FullPipelineReplayEngineV1(rows, request.initial_equity).evaluate({})
    status = {
        "version": "full-pipeline-baseline/2", "status": "COMPLETE",
        "dataset_hash": manifest.dataset_hash, "configuration_hash": configuration_hash,
        "totals": totals, "baseline": {key: value for key, value in replay.items() if key != "trades"},
        "holdout_evaluated": False, "production_mutations": 0,
    }
    _json(output / "BASELINE.json", status)
    _json(output / "BASELINE_FUNNEL.json", replay.get("funnel", {}))
    return status


SEARCH_DOMAINS: dict[str, tuple[object, ...]] = {
    "strategy_minimum_score": (40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90),
    "stop_max_bps": (18, 24, 30, 36, 45, 55, 65),
    "target_min_bps": (20, 30, 40, 50, 60, 80),
    "minimum_planned_rr": (.6, .8, 1.0, 1.2, 1.5),
    "min_net_edge_bps": (5, 8, 10, 12, 15, 20),
    "min_positive_ev_r": (0, .02, .05, .10),
    "bucket_min_sample": (20, 30, 50, 100),
    "risk_per_trade_bps": (2.5, 5, 7.5, 10),
    "max_open_positions": (1, 2),
    "max_new_commands_per_cycle": (1, 2),
    "total_open_risk_limit_bps": (25, 35, 50),
    "soft_timeout_seconds": (300, 600, 900, 1200, 1800, 2700),
    "hard_timeout_seconds": (300, 600, 900, 1200, 1800, 2700),
    "extension_seconds": (0, 300, 600),
    "max_extensions": (0, 1),
    "adverse_fill_reserve_bps": (3, 5, 8, 10, 12),
    "entry_slippage_bps": (2, 3, 5, 8),
}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _training_validation_rows(
    rows: Sequence[Mapping[str, Any]], windows: Sequence[Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Keep validation out of search and clip execution paths at role boundaries."""

    validations = sorted((window for window in windows if window.role == "VALIDATION"),
                         key=lambda window: window.start_ms)
    final = validations[-1]
    training: list[dict[str, Any]] = []
    validation: list[dict[str, Any]] = []
    for source in rows:
        boundary = int(source["boundary_ms"])
        if boundary >= final.end_ms:
            continue
        if final.start_ms <= boundary < final.end_ms:
            destination, cutoff = validation, final.end_ms
        else:
            if any(window.start_ms <= boundary < window.end_ms for window in validations):
                continue
            destination = training
            cutoff = min((window.start_ms for window in validations if window.start_ms > boundary),
                         default=final.start_ms)
        row = dict(source)
        row["market_path_1m"] = [candle for candle in source.get("market_path_1m", [])
                                  if int(candle["close_time_ms"]) < cutoff]
        destination.append(row)
    return training, validation


def _truncate_to_checkpoint(path: Path, boundary_ms: int) -> None:
    if not path.exists():
        return
    retained = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        boundary = int(value.get("boundary_ms", value.get("entry_boundary_ms", -1)))
        if boundary <= boundary_ms:
            retained.append(json.dumps(value, sort_keys=True, default=str))
    path.write_text(("\n".join(retained) + "\n") if retained else "", encoding="utf-8")


def _replay_metrics(result: Mapping[str, Any]) -> dict[str, float | int]:
    trades = list(result.get("trades") or [])
    bps = [
        float(trade.get("net_pnl") or 0) / max(float(trade.get("reserved") or 0), 1e-12) * 10_000
        for trade in trades
    ]
    return {
        "closed_trades": len(trades),
        "net_pnl": float(result.get("net_pnl") or 0),
        "expectancy_bps": sum(bps) / len(bps) if bps else 0.0,
        "profit_factor": float(result.get("profit_factor") or 0),
        "win_rate": float(result.get("win_rate") or 0),
        "max_drawdown": float(result.get("max_drawdown") or 0),
        "symbol_days_score": FullPipelineReplayEngineV1([]).symbol_day_score(trades),
    }


def _lexicographic(metrics: Mapping[str, float | int]) -> tuple[float, ...]:
    return (
        float(float(metrics["net_pnl"]) > 0),
        float(float(metrics["expectancy_bps"]) >= 8),
        float(float(metrics["profit_factor"]) >= 1.2),
        float(float(metrics["win_rate"]) > .5),
        float(metrics["symbol_days_score"]),
        float(metrics["net_pnl"]),
        float(metrics["expectancy_bps"]),
        float(metrics["profit_factor"]),
        -float(metrics["max_drawdown"]),
    )


def _trial_scalar(metrics: Mapping[str, float | int]) -> float:
    key = _lexicographic(metrics)
    # Gate dominance is encoded in large, non-compensating bands.  The stored
    # lexicographic tuple remains the authoritative rank.
    return sum(value * weight for value, weight in zip(key, (1e12, 1e10, 1e8, 1e6, 1e3, 1, .1, .01, .001)))


def _trade_evaluations(trades: Sequence[Mapping[str, Any]], configuration_hash: str) -> list[dict[str, Any]]:
    values = []
    for index, trade in enumerate(trades):
        reserved = float(trade.get("reserved") or 0)
        entry = float(trade.get("entry_price") or 0)
        exit_price = float(trade.get("exit_price") or 0)
        if reserved <= 0 or entry <= 0 or exit_price <= 0:
            continue
        gross = float(trade.get("gross_pnl") or 0)
        net = float(trade.get("net_pnl") or 0)
        total_cost = max(0.0, gross - net)
        values.append({
            "version": "full-pipeline-trade-evaluation/1",
            "trade_id": str(trade.get("position_id") or trade.get("candidate_id") or f"trade-{index}"),
            "configuration_hash": configuration_hash,
            "symbol": str(trade["symbol"]),
            "setup_family": str(trade.get("setup_type") or "UNKNOWN"),
            "regime": str(trade.get("regime") or "UNKNOWN"),
            "entry_boundary_ms": int(trade["boundary_ms"]),
            "exit_boundary_ms": int(trade["closed_at_ms"]),
            "entry_price": entry, "exit_price": exit_price,
            "quantity": reserved / entry,
            "gross_pnl": gross,
            "fees": total_cost,
            "spread_cost": 0.0, "slippage_cost": 0.0, "reserve_cost": 0.0,
            "net_pnl": net,
            "net_pnl_bps": net / reserved * 10_000,
            "risk_r": net / max(reserved * float(trade.get("risk_bps") or 1) / 10_000, 1e-12),
            "exit_reason": str(trade.get("exit_reason") or "UNKNOWN"),
            "future_bars_used": False,
        })
    return values


def train_ragged(
    request_path: Path, dataset: Path, baseline: Path, output: Path,
) -> dict[str, Any]:
    """Resume-safe deterministic TPE over cached production-derived evidence."""

    import optuna

    from .full_pipeline import (
        EndToEndTradeEvaluationV1,
        FullPipelineCandidateV1,
        evaluate_gates,
        metrics_from_trades,
    )

    request = FullPipelineCalibrationRequestV2.model_validate_json(request_path.read_text(encoding="utf-8"))
    manifest = RaggedDatasetManifestV2.model_validate_json((dataset / "DATASET_MANIFEST.json").read_text(encoding="utf-8"))
    baseline_status = json.loads((baseline / "BASELINE.json").read_text(encoding="utf-8"))
    if baseline_status.get("dataset_hash") != manifest.dataset_hash:
        raise ValueError("BASELINE_DATASET_HASH_MISMATCH")
    if baseline_status.get("version") != "full-pipeline-baseline/3":
        raise ValueError("FULL_PIPELINE_FEATURE_CACHE_REQUIRED")
    rows = _read_jsonl(baseline / "REPLAY_ROWS.jsonl")
    if not rows:
        raise ValueError("NO_REPLAYABLE_PRODUCTION_OPPORTUNITIES")
    output.mkdir(parents=True, exist_ok=True)
    validations = sorted((window for window in request.windows if window.role == "VALIDATION"), key=lambda item: item.start_ms)
    calibration_rows, validation_rows = _training_validation_rows(rows, request.windows)
    if not calibration_rows or not validation_rows:
        raise ValueError("TRAIN_VALIDATION_ROWS_REQUIRED")
    baseline_values = _baseline_values()
    baseline_validation = FullPipelineReplayEngineV1(validation_rows, request.initial_equity).evaluate({})

    sensitivity = []
    for name, domain in SEARCH_DOMAINS.items():
        for value in domain:
            if value == baseline_values.get(name):
                continue
            result = FullPipelineReplayEngineV1(calibration_rows, request.initial_equity).evaluate({name: value})
            sensitivity.append({"parameter": name, "value": value, "metrics": _replay_metrics(result)})
    _json(output / "SENSITIVITY.json", sensitivity)

    storage = "sqlite:///" + (output / "study.sqlite3").resolve().as_posix()
    study = optuna.create_study(
        storage=storage, study_name=fingerprint({"dataset": manifest.dataset_hash, "seed": request.seed}),
        load_if_exists=True, direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=request.seed, n_startup_trials=20),
    )
    ledger = output / "TRIALS.jsonl"

    def objective(trial: Any) -> float:
        proposal = {name: trial.suggest_categorical(name, list(values)) for name, values in SEARCH_DOMAINS.items()}
        if int(proposal["hard_timeout_seconds"]) < int(proposal["soft_timeout_seconds"]):
            raise optuna.TrialPruned("hard timeout precedes soft timeout")
        result = FullPipelineReplayEngineV1(calibration_rows, request.initial_equity).evaluate(proposal)
        metrics = _replay_metrics(result)
        trial.set_user_attr("configuration_hash", fingerprint(proposal))
        trial.set_user_attr("lexicographic", list(_lexicographic(metrics)))
        with ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "trial": trial.number, "parameters": proposal,
                "configuration_hash": fingerprint(proposal), "metrics": metrics,
                "lexicographic": _lexicographic(metrics),
            }, sort_keys=True) + "\n")
        return _trial_scalar(metrics)

    completed = len([trial for trial in study.trials if trial.state == optuna.trial.TrialState.COMPLETE])
    target = request.search.joint + request.search.local_refinement
    if completed < target:
        study.optimize(objective, n_trials=target - completed, n_jobs=1, gc_after_trial=True)
    records = _read_jsonl(ledger)
    unique = {record["configuration_hash"]: record for record in records}
    # Search ranks on training only. Validation selects from the frozen
    # training Pareto shortlist without feeding its outcome back into TPE.
    training_shortlist = sorted(unique.values(), key=lambda item: tuple(item["lexicographic"]), reverse=True)[:20]
    finalists = []
    for item in training_shortlist:
        validation = FullPipelineReplayEngineV1(validation_rows, request.initial_equity).evaluate(item["parameters"])
        finalists.append({**item, "validation_metrics": _replay_metrics(validation),
                          "validation_rank": _lexicographic(_replay_metrics(validation))})
    finalists.sort(key=lambda item: tuple(item["validation_rank"]), reverse=True)
    finalists = finalists[:3]
    freeze = {
        "version": "full-pipeline-finalist-freeze/2", "dataset_hash": manifest.dataset_hash,
        "seed": request.seed, "finalists": finalists,
        "freeze_hash": fingerprint(finalists), "holdout_opened": False,
    }
    _json(output / "FROZEN_FINALISTS.json", freeze)

    # The freeze is durable before the locked file is opened.  Holdout is read
    # once and may only reject, never retune, a finalist.
    holdout_rows = _read_jsonl(baseline / "HOLDOUT_ROWS.locked.jsonl")
    best = finalists[0]
    holdout = FullPipelineReplayEngineV1(holdout_rows, request.initial_equity).evaluate(best["parameters"])
    holdout_trades = _trade_evaluations(holdout.get("trades") or [], best["configuration_hash"])
    trades = [EndToEndTradeEvaluationV1.model_validate(item) for item in holdout_trades]
    fold_profit = 0
    fold_metrics = []
    for window in validations:
        fold_rows = [row for row in rows if window.start_ms <= int(row["boundary_ms"]) < window.end_ms]
        if not fold_rows:
            continue
        result = FullPipelineReplayEngineV1(fold_rows, request.initial_equity).evaluate(best["parameters"])
        metrics = _replay_metrics(result)
        fold_profit += int(float(metrics["net_pnl"]) > 0)
        fold_metrics.append({"window": window.name, "metrics": metrics})
    baseline_metrics = _replay_metrics(baseline_validation)
    baseline_drawdown_fraction = float(baseline_metrics["max_drawdown"]) / request.initial_equity
    neighbor_pass = True
    for name, domain in SEARCH_DOMAINS.items():
        current = best["parameters"][name]
        position = list(domain).index(current)
        for neighbor in {max(0, position - 1), min(len(domain) - 1, position + 1)}:
            proposal = dict(best["parameters"]); proposal[name] = domain[neighbor]
            result = FullPipelineReplayEngineV1(holdout_rows, request.initial_equity).evaluate(proposal)
            if float(result.get("net_pnl") or 0) <= 0:
                neighbor_pass = False
    metrics = metrics_from_trades(
        trades, initial_equity=request.initial_equity,
        baseline_max_drawdown_fraction=baseline_drawdown_fraction,
        profitable_walk_forward_folds=fold_profit,
        neighbor_stability_pass=neighbor_pass,
        stress_multiplier=request.gates.stress_cost_multiplier,
    )
    gates = evaluate_gates(metrics, request.gates)
    candidate = FullPipelineCandidateV1(
        candidate_id=f"ragged-universal-{best['configuration_hash'][:12]}",
        request_hash=request.identity, dataset_hash=manifest.dataset_hash,
        registry_hash=default_registry().identity,
        configuration_hash=best["configuration_hash"], seed=request.seed,
        parameters=best["parameters"], metrics=metrics, gate_results=gates,
        status="ELIGIBLE" if all(gates.values()) else "NO_ELIGIBLE_CANDIDATE",
    )
    _json(output / "CANDIDATE.json", candidate.model_dump(mode="json"))
    with (output / "HOLDOUT_TRADES.jsonl").open("w", encoding="utf-8") as handle:
        for trade in holdout_trades:
            handle.write(json.dumps(trade, sort_keys=True) + "\n")
    _json(output / "FOLD_METRICS.json", fold_metrics)
    _json(output / "GATE_ATTRIBUTION.json", {name: passed for name, passed in gates.items()})
    summary = {
        "version": "full-pipeline-training/2", "status": candidate.status,
        "dataset_hash": manifest.dataset_hash, "completed_trials": len(unique),
        "candidate_id": candidate.candidate_id, "metrics": metrics.model_dump(mode="json"),
        "gates": gates, "holdout_opened_once": True, "production_mutations": 0,
    }
    _json(output / "STATUS.json", summary)
    return summary
