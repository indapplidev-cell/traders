"""Read-only candle reconstruction and overlap parity certification.

This module deliberately reuses the authoritative pipeline components.  It
never writes reconstructed observations to PostgreSQL and it refuses to build
a hybrid dataset unless the overlap comparison is certified.
"""

from __future__ import annotations

import argparse
from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from sqlalchemy import text

from app.config.trade_parameters import SCALPING_V2, TRADE_PARAMETERS
from app.engine_market_data.candle import Candle
from app.engine_orchestrator.orchestrator_config import OrchestratorConfig
from app.engine_orchestrator.pipeline_result import PipelineResult, json_safe
from app.engine_orchestrator.pipeline_runner import PipelineRunner
from app.engine_paper.scalping_paper_runner import ScalpingPaperRunner
from app.engine_paper.scalping_shadow import ShadowCostInputs
from .artifact_writer import DEFAULT_ARTIFACT_WRITER
from .engine import ReadOnlyResearchDatabase, resolve_database_binding
from .historical_replay import HISTORY_TARGET_DAYS, HISTORY_TARGET_MS, PROFILE
from .universe import validate_parameter_sweep_symbol


RECONSTRUCTION_VERSION = "historical-causal-observation:v1"
SCHEMA_VERSION = "PARAMETER_SWEEP_RECONSTRUCTION_SCHEMA/1"
SOURCE_PERSISTED = "PERSISTED_OBSERVATION"
SOURCE_RECONSTRUCTED = "RECONSTRUCTED_OBSERVATION"
TIMEFRAMES = ("1m", "5m", "15m", "1h")
TABLES = {value: f"candles_{value}" for value in TIMEFRAMES}
NUMERIC_TOLERANCE = 1e-8

CRITICAL_FIELDS = (
    "symbol", "profile", "timeframe", "setup_type", "setup_status", "direction", "strategy_status",
    "eligibility_status", "terminal_stage", "rejection_reason",
)
NUMERIC_FIELDS = (
    "strategy_score", "entry_reference", "stop_reference", "target_reference",
    "gross_rr", "net_rr", "dynamic_required_rr", "entry_fee_bps",
    "exit_fee_bps", "spread_bps", "entry_slippage_bps",
    "exit_slippage_bps", "depth_impact_bps", "p_win_raw",
    "p_win_conservative", "expected_ev_r",
)


def _nested(value: object, *path: str) -> Any:
    current = value
    for part in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(part)
    return current


def _first(*values: object) -> Any:
    return next((value for value in values if value not in (None, "", [])), None)


def _utc(milliseconds: int | None) -> str | None:
    if milliseconds is None:
        return None
    return datetime.fromtimestamp(milliseconds / 1000, timezone.utc).isoformat()


def _hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(encoded.encode("utf-8")).hexdigest()


def _percentile(values: Sequence[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


@dataclass(frozen=True, slots=True)
class ReconstructionResult:
    output: Path
    parity: dict[str, Any]
    hybrid_manifest: dict[str, Any]


class HistoricalUnavailableCostSource:
    """Fail-closed replacement for unavailable historical order-book inputs.

    Fees/slippage come from the same resolved runtime parameters, while spread,
    depth and account-commission authority remain explicitly unavailable.  No
    current network observation is allowed to masquerade as historical input.
    """

    def __init__(self, runtime_parameters: object) -> None:
        self.runtime_parameters = runtime_parameters
        self.boundary_ms = 0

    def load(self, symbol: str, entry: float, *, safety_margin_bps: float) -> ShadowCostInputs:
        return ShadowCostInputs(
            entry_fee_bps=float(self.runtime_parameters.economics_entry_fee_bps),
            exit_fee_bps=float(self.runtime_parameters.economics_exit_fee_bps),
            entry_slippage_bps=float(self.runtime_parameters.economics_entry_slippage_bps),
            exit_slippage_bps=float(self.runtime_parameters.economics_exit_slippage_bps),
            safety_margin_bps=float(safety_margin_bps),
            adverse_fill_reserve_bps=float(SCALPING_V2.costs.adverse_fill_reserve_bps),
            fee_source="HISTORICAL_ACCOUNT_COMMISSION_UNAVAILABLE",
            spread_source="HISTORICAL_BOOK_TICKER_UNAVAILABLE",
            depth_impact_source="HISTORICAL_BOOK_DEPTH_UNAVAILABLE",
            economic_input_timestamp_ms=self.boundary_ms,
            economic_capture_started_at_ms=self.boundary_ms,
            decision_cutoff_timestamp_ms=self.boundary_ms,
            economic_input_source="EXPLICITLY_UNAVAILABLE_NO_GUESS",
            maximum_age_ms=int(self.runtime_parameters.microstructure_max_age_ms),
            require_causal_timestamp=True,
            market_source_status="NOT_AVAILABLE_HISTORICALLY",
            fee_source_status="NOT_AVAILABLE_HISTORICALLY",
            book_source_status="NOT_AVAILABLE_HISTORICALLY",
            cost_model_status="NOT_READY",
        )


class CausalCandleRepository:
    """In-memory selected-symbol candle windows with a future-data audit."""

    def __init__(self, symbol: str, rows: Mapping[str, Sequence[Candle]]) -> None:
        self.symbol = symbol.upper()
        self.rows = {key: tuple(sorted(value, key=lambda row: row.open_time_ms)) for key, value in rows.items()}
        self.opens = {key: tuple(row.open_time_ms for row in value) for key, value in self.rows.items()}
        self.maximum_close_read_ms: int | None = None
        self.causality_violations: list[dict[str, Any]] = []

    def get_candles(
        self, symbol: str, timeframe: str, start_time_ms: int | None = None,
        end_time_ms: int | None = None, limit: int | None = None,
    ) -> list[Candle]:
        normalized = symbol.upper()
        if normalized != self.symbol:
            self.causality_violations.append({
                "type": "CROSS_SYMBOL_READ", "requested": normalized,
                "selected": self.symbol, "timeframe": timeframe,
            })
            return []
        values = self.rows.get(timeframe, ())
        opens = self.opens.get(timeframe, ())
        stop = len(values) if end_time_ms is None else bisect_right(opens, int(end_time_ms))
        selected = list(values[:stop])
        if start_time_ms is not None:
            selected = [row for row in selected if row.open_time_ms >= int(start_time_ms)]
        if limit is not None:
            selected = selected[-int(limit):]
        if end_time_ms is not None:
            invalid = [row for row in selected if row.open_time_ms > int(end_time_ms)]
            if invalid:
                self.causality_violations.append({
                    "type": "FUTURE_CANDLE_READ", "timeframe": timeframe,
                    "end_time_ms": int(end_time_ms),
                    "maximum_open_time_ms": max(row.open_time_ms for row in invalid),
                })
        if selected:
            maximum = max(row.close_time_ms for row in selected)
            self.maximum_close_read_ms = max(self.maximum_close_read_ms or maximum, maximum)
        return selected


def canonical_observation(
    value: Mapping[str, Any] | PipelineResult, *, source_type: str,
) -> dict[str, Any]:
    raw = json_safe(value)
    if not isinstance(raw, Mapping):
        raise TypeError("observation must be a mapping or PipelineResult")
    suffix = "_payload_json" if "setup_payload_json" in raw else "_payload"
    analysis = dict(raw.get(f"analysis{suffix}") or {})
    setup = dict(raw.get(f"setup{suffix}") or {})
    strategy = dict(raw.get(f"strategy{suffix}") or {})
    risk = dict(raw.get(f"risk{suffix}") or {})
    paper = dict(raw.get(f"paper{suffix}") or {})
    geometry = dict(_nested(paper, "paper_context", "scalping_geometry_diagnostics") or {})
    boundary = int(_first(raw.get("closed_until_ms"), setup.get("closed_until_ms")) or 0)
    symbol = str(_first(raw.get("symbol"), setup.get("symbol")) or "").upper()
    rejection = _first(
        geometry.get("rejection_reason"),
        (paper.get("rejection_reasons") or [None])[0],
        (risk.get("rejection_reasons") or [None])[0],
        (strategy.get("rejection_reasons") or [None])[0],
        (setup.get("invalidation_reasons") or [None])[0],
        raw.get("final_reason"),
    )
    terminal = _first(
        geometry.get("rejection_stage"), paper.get("paper_status"),
        risk.get("risk_status"), strategy.get("decision_status"), setup.get("status"),
    )
    eligibility = bool(
        geometry.get("execution_eligible")
        or paper.get("paper_status") == "PAPER_PLAN_READY"
    )
    causal_reasons: dict[str, str] = {}
    for name, source in {
        "spread_bps": geometry.get("spread_bps"),
        "depth_impact_bps": geometry.get("depth_impact_bps"),
        "commission": geometry.get("commission_snapshot_id"),
        "probability": geometry.get("probability_estimator_version"),
        "expected_ev_r": geometry.get("expected_ev_r"),
    }.items():
        if source is None:
            causal_reasons[name] = "CAUSAL_INPUT_UNAVAILABLE"
    result = {
        "schema": RECONSTRUCTION_VERSION,
        "observation_id": f"{RECONSTRUCTION_VERSION}:{_hash([symbol, PROFILE, boundary, source_type])}",
        "source_type": source_type,
        "source_priority": 0 if source_type == SOURCE_PERSISTED else 1,
        "symbol": symbol, "profile": str(_first(raw.get("trade_profile_id"), PROFILE)),
        "timeframe": str(_first(raw.get("primary_timeframe"), raw.get("timeframe"), "5m")),
        "closed_until_ms": boundary,
        "setup_type": setup.get("setup_type"), "setup_status": setup.get("status"),
        "direction": _first(setup.get("direction_hint"), strategy.get("direction_hint"), risk.get("direction_hint")),
        "strategy_score": strategy.get("strategy_score"),
        "strategy_status": strategy.get("decision_status"),
        "regime": _first(setup.get("regime"), _nested(analysis, "analysis_context", "scalping", "market_regime"), analysis.get("regime")),
        "entry_reference": _first(paper.get("hypothetical_entry_reference"), geometry.get("entry"), _nested(strategy, "context", "reference_close")),
        "stop_reference": _first(paper.get("hypothetical_stop_level"), geometry.get("final_stop")),
        "target_reference": _first(paper.get("hypothetical_target_level"), geometry.get("causal_target")),
        "gross_rr": geometry.get("gross_rr"), "net_rr": geometry.get("net_rr"),
        "dynamic_required_rr": _first(geometry.get("dynamic_required_net_rr"), geometry.get("required_rr")),
        "entry_fee_bps": geometry.get("entry_fee_bps"), "exit_fee_bps": geometry.get("exit_fee_bps"),
        "spread_bps": geometry.get("spread_bps"), "entry_slippage_bps": geometry.get("entry_slippage_bps"),
        "exit_slippage_bps": geometry.get("exit_slippage_bps"), "depth_impact_bps": geometry.get("depth_impact_bps"),
        "cost_provenance": geometry.get("fee_source"),
        "p_win_raw": geometry.get("p_win_raw"), "p_win_conservative": geometry.get("p_win_conservative"),
        "probability_inputs": {
            "bucket": geometry.get("probability_bucket"),
            "sample_size": geometry.get("probability_sample_size"),
            "estimator": geometry.get("probability_estimator_version"),
        },
        "expected_ev_r": geometry.get("expected_ev_r"),
        "ev_inputs": {"reserve": geometry.get("ev_reserve"), "minimum": geometry.get("min_required_ev")},
        "risk_status": risk.get("risk_status"), "eligibility_status": eligibility,
        "rejection_reason": rejection, "terminal_stage": terminal,
        "component_versions": {
            "trade_parameters": TRADE_PARAMETERS.config_version,
            "setup": _first(setup.get("setup_policy_id"), _nested(setup, "context", "setup_policy_id")),
            "strategy": _first(_nested(strategy, "context", "strategy_policy_id"), strategy.get("strategy_type")),
            "risk": risk.get("risk_policy_version"),
            "geometry": geometry.get("geometry_calculation_version"),
        },
        "parameter_provenance": _first(raw.get("runtime_parameter_set_id"), setup.get("runtime_parameter_set_id")),
        "market_data_fingerprint": _hash(raw.get("market_data_payload") or raw.get("market_data_payload_json") or {}),
        "causal_input_fingerprint": _hash({"analysis": analysis, "setup": setup, "strategy": strategy}),
        "reconstruction_version": RECONSTRUCTION_VERSION if source_type == SOURCE_RECONSTRUCTED else None,
        "causally_unavailable": causal_reasons,
        "future_bars_used": bool(
            raw.get("safety_counters", {}).get("future_bars_used_count", 0)
            if isinstance(raw.get("safety_counters"), Mapping)
            else False
        ) or any(bool(part.get("future_bars_used")) for part in (analysis, setup, strategy, risk, paper)),
    }
    return result


def compare_observations(
    persisted: Sequence[Mapping[str, Any]], reconstructed: Sequence[Mapping[str, Any]],
    *, total_overlap_boundaries: int | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    left = {int(row["closed_until_ms"]): row for row in persisted}
    right = {int(row["closed_until_ms"]): row for row in reconstructed}
    matched = sorted(left.keys() & right.keys())
    mismatches: list[dict[str, Any]] = []
    field_counts: dict[str, dict[str, int]] = {}
    errors: dict[str, list[float]] = {name: [] for name in NUMERIC_FIELDS}
    relative_errors: dict[str, list[float]] = {name: [] for name in NUMERIC_FIELDS}
    for boundary in sorted(left.keys() | right.keys()):
        if boundary not in left or boundary not in right:
            mismatches.append({
                "closed_until_ms": boundary, "field": "boundary",
                "classification": "MISSING_RECONSTRUCTED" if boundary not in right else "MISSING_PERSISTED",
            })
            continue
        for field in CRITICAL_FIELDS:
            a, b = left[boundary].get(field), right[boundary].get(field)
            classification = "EXACT_MATCH" if a == b else (
                "MISSING_RECONSTRUCTED" if b is None else
                "MISSING_PERSISTED" if a is None else "SEMANTIC_MISMATCH"
            )
            field_counts.setdefault(field, {})[classification] = field_counts.setdefault(field, {}).get(classification, 0) + 1
            if classification != "EXACT_MATCH":
                mismatches.append({"closed_until_ms": boundary, "field": field, "persisted": a, "reconstructed": b, "classification": classification})
        for field in NUMERIC_FIELDS:
            a, b = left[boundary].get(field), right[boundary].get(field)
            if a is None and b is None:
                classification = "EXACT_MATCH"
            elif b is None:
                classification = "MISSING_RECONSTRUCTED"
            elif a is None:
                classification = "MISSING_PERSISTED"
            else:
                absolute = abs(float(a) - float(b))
                relative = absolute / max(abs(float(a)), NUMERIC_TOLERANCE)
                errors[field].append(absolute)
                relative_errors[field].append(relative)
                classification = "NUMERIC_MATCH_WITHIN_TOLERANCE" if absolute <= NUMERIC_TOLERANCE else "SEMANTIC_MISMATCH"
            field_counts.setdefault(field, {})[classification] = field_counts.setdefault(field, {}).get(classification, 0) + 1
            if classification not in {"EXACT_MATCH", "NUMERIC_MATCH_WITHIN_TOLERANCE"}:
                mismatches.append({"closed_until_ms": boundary, "field": field, "persisted": a, "reconstructed": b, "classification": classification})
    critical_mismatches = sum(
        sum(count for status, count in field_counts.get(field, {}).items() if status != "EXACT_MATCH")
        for field in CRITICAL_FIELDS
    )
    numeric_mismatches = sum(
        sum(count for status, count in field_counts.get(field, {}).items() if status not in {"EXACT_MATCH", "NUMERIC_MATCH_WITHIN_TOLERANCE"})
        for field in NUMERIC_FIELDS
    )
    complete = total_overlap_boundaries is None or len(matched) == int(total_overlap_boundaries)
    summary = {
        "schema": "PARAMETER_SWEEP_PARITY_SUMMARY/1",
        "persisted_overlap_rows": len(persisted), "reconstructed_overlap_rows": len(reconstructed),
        "matched_boundaries": len(matched), "total_overlap_boundaries": total_overlap_boundaries or len(matched),
        "complete_overlap_compared": complete,
        "field_classifications": field_counts,
        "critical_field_mismatches": critical_mismatches,
        "numeric_mismatch_count": numeric_mismatches,
        "numeric_errors": {
            field: {
                "absolute_error_p50": _percentile(values, .5),
                "absolute_error_p95": _percentile(values, .95),
                "absolute_error_max": max(values) if values else None,
                "relative_error_p50": _percentile(relative_errors[field], .5),
                "relative_error_p95": _percentile(relative_errors[field], .95),
                "relative_error_max": max(relative_errors[field]) if relative_errors[field] else None,
            } for field, values in errors.items()
        },
    }
    return summary, mismatches


def merge_hybrid_observations(
    persisted: Sequence[Mapping[str, Any]], reconstructed: Sequence[Mapping[str, Any]],
    *, certified: bool, symbol: str,
) -> tuple[list[dict[str, Any]], int]:
    if not certified:
        return [], 0
    selected = symbol.upper()
    if any(str(row.get("symbol", "")).upper() != selected for row in (*persisted, *reconstructed)):
        raise ValueError("CROSS_SYMBOL_CONTAMINATION")
    by_boundary = {int(row["closed_until_ms"]): dict(row) for row in reconstructed}
    duplicates = 0
    for row in persisted:
        boundary = int(row["closed_until_ms"])
        duplicates += int(boundary in by_boundary)
        by_boundary[boundary] = dict(row)
    return [by_boundary[key] for key in sorted(by_boundary)], duplicates


def _load_candles(connection: Any, symbol: str, start: int, end: int) -> dict[str, list[Candle]]:
    result: dict[str, list[Candle]] = {}
    for timeframe, table in TABLES.items():
        rows = connection.execute(text(f"""
            SELECT symbol,open_time_ms,close_time_ms,open,high,low,close,volume,
                   quote_volume,trades_count,source,is_closed
            FROM {table}
            WHERE symbol=:symbol AND is_closed=true
              AND close_time_ms BETWEEN :start AND :end
            ORDER BY open_time_ms
        """), {"symbol": symbol, "start": start, "end": end}).mappings()
        result[timeframe] = [Candle(
            symbol=row["symbol"], timeframe=timeframe,
            open_time_ms=int(row["open_time_ms"]), close_time_ms=int(row["close_time_ms"]),
            open=row["open"], high=row["high"], low=row["low"], close=row["close"],
            volume=row["volume"], quote_volume=row["quote_volume"],
            trades_count=row["trades_count"], source=row["source"], is_closed=bool(row["is_closed"]),
        ) for row in rows]
    return result


def _source_inventory(connection: Any, symbol: str) -> dict[str, Any]:
    candles: dict[str, tuple[int | None, int | None, int]] = {}
    for timeframe in ("1m", "5m"):
        table = TABLES[timeframe]
        row = connection.execute(text(f"SELECT min(close_time_ms),max(close_time_ms),count(*) FROM {table} WHERE symbol=:symbol AND is_closed=true"), {"symbol": symbol}).one()
        candles[timeframe] = (int(row[0]) if row[0] is not None else None, int(row[1]) if row[1] is not None else None, int(row[2]))
    persisted = connection.execute(text("""
        SELECT min(r.closed_until_ms),max(r.closed_until_ms),count(*)
        FROM online_pipeline_results r JOIN online_pipeline_runs u ON u.run_id=r.run_id
        WHERE u.trade_profile_id=:profile AND r.symbol=:symbol
    """), {"profile": PROFILE, "symbol": symbol}).one()
    persisted_start = int(persisted[0]) if persisted[0] is not None else None
    persisted_end = int(persisted[1]) if persisted[1] is not None else None
    candle_end = min(value[1] for value in candles.values() if value[1] is not None) + 1
    target_start = candle_end - HISTORY_TARGET_MS
    overlap_start = max(target_start, persisted_start) if persisted_start is not None else None
    overlap_end = min(candle_end, persisted_end) if persisted_end is not None else None
    overlap_count = 0
    if overlap_start is not None and overlap_end is not None:
        overlap_count = int(connection.execute(text("""
            SELECT count(*) FROM online_pipeline_results r
            JOIN online_pipeline_runs u ON u.run_id=r.run_id
            WHERE u.trade_profile_id=:profile AND r.symbol=:symbol
              AND r.closed_until_ms BETWEEN :start AND :end
        """), {"profile": PROFILE, "symbol": symbol, "start": overlap_start, "end": overlap_end}).scalar_one())
    return {
        "symbol": symbol, "target_history_days": HISTORY_TARGET_DAYS,
        "candle_1m_start": _utc(candles["1m"][0]), "candle_1m_end": _utc(candles["1m"][1]), "candle_1m_rows": candles["1m"][2],
        "candle_5m_start": _utc(candles["5m"][0]), "candle_5m_end": _utc(candles["5m"][1]), "candle_5m_rows": candles["5m"][2],
        "persisted_observation_start": _utc(persisted_start), "persisted_observation_end": _utc(persisted_end), "persisted_observation_rows": int(persisted[2]),
        "target_start": _utc(target_start), "target_end": _utc(candle_end),
        "target_start_ms": target_start, "target_end_ms": candle_end,
        "overlap_start": _utc(overlap_start), "overlap_end": _utc(overlap_end),
        "overlap_start_ms": overlap_start, "overlap_end_ms": overlap_end,
        "overlap_boundary_count": overlap_count,
        "required_pipeline_components": ["analysis", "setup", "strategy", "risk", "geometry", "net_cost", "probability", "EV"],
        "reusable_read_only_components": [
            "PipelineRunner", "run_engine_analysis", "SetupDetector/SetupRunner",
            "StrategyFilter/StrategyRunner", "RiskPolicy/RiskRunner", "evaluate_scalping_shadow",
        ],
        "components_missing_for_reconstruction": [
            "historical_account_commission_snapshot", "historical_book_ticker",
            "historical_order_book_depth", "historical_as_of_probability_statistics",
        ],
    }


def _persisted_rows(connection: Any, symbol: str, start: int, end: int) -> list[dict[str, Any]]:
    return [dict(row) for row in connection.execute(text("""
        SELECT r.run_id,r.symbol,r.primary_timeframe,r.closed_until_ms,r.trade_profile_id,
               r.market_data_payload_json,r.analysis_payload_json,r.setup_payload_json,
               r.strategy_payload_json,r.risk_payload_json,r.paper_payload_json,
               r.module_reasons_json,r.safety_counters_json
        FROM online_pipeline_results r JOIN online_pipeline_runs u ON u.run_id=r.run_id
        WHERE u.trade_profile_id=:profile AND r.symbol=:symbol
          AND r.closed_until_ms BETWEEN :start AND :end
        ORDER BY r.closed_until_ms,r.run_id
    """), {"profile": PROFILE, "symbol": symbol, "start": start, "end": end}).mappings()]


def _schema_artifact() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION, "observation_schema": RECONSTRUCTION_VERSION,
        "source_types": [SOURCE_PERSISTED, SOURCE_RECONSTRUCTED],
        "source_policy": "PERSISTED_PREFERRED_ELSE_CERTIFIED_RECONSTRUCTED_ELSE_UNAVAILABLE",
        "critical_fields": list(CRITICAL_FIELDS), "numeric_fields": list(NUMERIC_FIELDS),
        "numeric_absolute_tolerance": NUMERIC_TOLERANCE,
        "causal_contract": [
            "max_1m_close_lt_boundary", "max_5m_close_lt_boundary",
            "higher_timeframe_close_lt_boundary", "no_future_market_observation",
            "no_future_outcome", "no_future_label",
        ],
    }


def run_reconstruction_audit(
    *, symbol: str, output: Path, max_overlap_boundaries: int | None = None,
    database_url: str | None = None,
) -> ReconstructionResult:
    selected = validate_parameter_sweep_symbol(symbol)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    database = ReadOnlyResearchDatabase(resolve_database_binding(explicit_url=database_url))
    try:
        with database.connection() as connection:
            inventory = _source_inventory(connection, selected)
            overlap_start = inventory["overlap_start_ms"]
            overlap_end = inventory["overlap_end_ms"]
            persisted_raw = _persisted_rows(connection, selected, overlap_start, overlap_end)
            if max_overlap_boundaries is not None:
                persisted_raw = persisted_raw[-max(1, int(max_overlap_boundaries)):]
            boundaries = [int(row["closed_until_ms"]) for row in persisted_raw]
            if not boundaries:
                raise ValueError("NO_PERSISTED_OVERLAP")
            lookback_start = min(boundaries) - 52 * 60 * 60 * 1000
            candles = _load_candles(connection, selected, lookback_start, max(boundaries))
        repository = CausalCandleRepository(selected, candles)
        config = OrchestratorConfig(symbols=(selected,), trade_profile_id=PROFILE, primary_timeframe="5m")
        cost_source = HistoricalUnavailableCostSource(config.runtime_parameters)
        paper_runner = ScalpingPaperRunner(
            runtime_parameters=config.runtime_parameters, cost_source=cost_source,
            clock_ms=lambda: cost_source.boundary_ms,
        )
        runner = PipelineRunner(config, repository, paper_runner=paper_runner)
        reconstructed: list[dict[str, Any]] = []
        for boundary in boundaries:
            cost_source.boundary_ms = boundary
            reconstructed.append(canonical_observation(runner.run(selected, boundary), source_type=SOURCE_RECONSTRUCTED))
        persisted = [canonical_observation(row, source_type=SOURCE_PERSISTED) for row in persisted_raw]
        parity, mismatches = compare_observations(
            persisted, reconstructed,
            total_overlap_boundaries=int(inventory["overlap_boundary_count"]),
        )
        cross_symbol = sum(row.get("symbol") != selected for row in (*persisted, *reconstructed))
        causality = {
            "schema": "PARAMETER_SWEEP_RECONSTRUCTION_CAUSALITY/1",
            "symbol": selected,
            "maximum_candle_close_read_ms": repository.maximum_close_read_ms,
            "maximum_reconstructed_boundary_ms": max(boundaries),
            "future_bars_reported": sum(bool(row.get("future_bars_used")) for row in reconstructed),
            "violations": repository.causality_violations,
            "violation_count": len(repository.causality_violations) + sum(bool(row.get("future_bars_used")) for row in reconstructed),
            "cross_symbol_contamination": cross_symbol,
        }
        parity["symbol"] = selected
        parity["profile"] = PROFILE
        parity["timeframe"] = "5m"
        parity["overlap_start"] = _utc(min(boundaries))
        parity["overlap_end"] = _utc(max(boundaries))
        parity["causality_violations"] = causality["violation_count"]
        parity["cross_symbol_contamination"] = cross_symbol
        classifications = parity["field_classifications"]

        def field_parity(*names: str) -> str:
            return "PASS" if all(
                sum(count for status, count in classifications.get(name, {}).items() if status != "EXACT_MATCH") == 0
                for name in names
            ) else "FAIL"

        parity.update({
            "setup_parity": field_parity("setup_type", "setup_status"),
            "direction_parity": field_parity("direction"),
            "strategy_status_parity": field_parity("strategy_status"),
            "eligibility_parity": field_parity("eligibility_status"),
            "terminal_stage_parity": field_parity("terminal_stage"),
            "rejection_reason_parity": field_parity("rejection_reason"),
            "cost_input_parity": field_parity(
                "entry_fee_bps", "exit_fee_bps", "spread_bps",
                "entry_slippage_bps", "exit_slippage_bps", "depth_impact_bps",
            ),
            "probability_input_parity": field_parity("p_win_raw", "p_win_conservative"),
            "ev_input_parity": field_parity("expected_ev_r"),
        })
        if all(row.get("p_win_raw") is None and row.get("p_win_conservative") is None for row in reconstructed):
            parity["probability_input_parity"] = "NOT_PROVEN_CAUSAL_INPUT_UNAVAILABLE"
        if all(row.get("expected_ev_r") is None for row in reconstructed):
            parity["ev_input_parity"] = "NOT_PROVEN_CAUSAL_INPUT_UNAVAILABLE"
        parity["required_causal_components_available"] = not bool(
            inventory["components_missing_for_reconstruction"]
        )
        certified = bool(
            parity["complete_overlap_compared"]
            and parity["critical_field_mismatches"] == 0
            and parity["numeric_mismatch_count"] == 0
            and parity["required_causal_components_available"]
            and parity["cost_input_parity"] == "PASS"
            and parity["probability_input_parity"] == "PASS"
            and parity["ev_input_parity"] == "PASS"
            and causality["violation_count"] == 0
            and cross_symbol == 0
        )
        parity["reconstruction_parity"] = "PASS_CERTIFIED" if certified else "FAIL_NOT_CERTIFIED"
        hybrid_rows, duplicates = merge_hybrid_observations(persisted, reconstructed, certified=certified, symbol=selected)
        hybrid_manifest = {
            "schema": "PARAMETER_SWEEP_HYBRID_30D_DATASET_MANIFEST/1",
            "symbol": selected, "profile": PROFILE, "timeframe": "5m",
            "history_target_days": HISTORY_TARGET_DAYS,
            "dataset_created": certified,
            "status": "PASS_30D_RECONSTRUCTED_PLUS_PERSISTED" if certified else "NOT_CREATED_PARITY_NOT_CERTIFIED",
            "history_start": _utc(min((row["closed_until_ms"] for row in hybrid_rows), default=None)),
            "history_end": _utc(max((row["closed_until_ms"] for row in hybrid_rows), default=None)),
            "history_actual_days": (
                (max(row["closed_until_ms"] for row in hybrid_rows) - min(row["closed_until_ms"] for row in hybrid_rows)) / 86_400_000
                if hybrid_rows else 0.0
            ),
            "persisted_observation_count": sum(row.get("source_type") == SOURCE_PERSISTED for row in hybrid_rows),
            "reconstructed_observation_count": sum(row.get("source_type") == SOURCE_RECONSTRUCTED for row in hybrid_rows),
            "overlap_persisted_used": sum(row.get("source_type") == SOURCE_PERSISTED for row in hybrid_rows),
            "overlap_reconstructed_compared": len(reconstructed),
            "duplicate_boundaries_removed": duplicates,
            "dataset_symbol_count": len({row.get("symbol") for row in hybrid_rows}),
            "dataset_distinct_symbols": sorted({row.get("symbol") for row in hybrid_rows}),
            "opportunities": len(hybrid_rows),
            "reason": None if certified else "RECONSTRUCTION_PARITY_REQUIRED_BEFORE_OLDER_HISTORY",
        }
        DEFAULT_ARTIFACT_WRITER.atomic_json(output / "HISTORICAL_RECONSTRUCTION_SOURCE_INVENTORY.json", inventory, operation="reconstruction_inventory")
        DEFAULT_ARTIFACT_WRITER.atomic_json(output / "RECONSTRUCTION_SCHEMA.json", _schema_artifact(), operation="reconstruction_schema")
        DEFAULT_ARTIFACT_WRITER.atomic_json(output / "PARITY_SUMMARY.json", parity, operation="reconstruction_parity")
        DEFAULT_ARTIFACT_WRITER.atomic_text(output / "PARITY_MISMATCHES.jsonl", "".join(json.dumps(row, sort_keys=True, default=str) + "\n" for row in mismatches), operation="reconstruction_mismatches")
        DEFAULT_ARTIFACT_WRITER.atomic_json(output / "RECONSTRUCTION_CAUSALITY.json", causality, operation="reconstruction_causality")
        DEFAULT_ARTIFACT_WRITER.atomic_json(output / "HYBRID_30D_DATASET_MANIFEST.json", hybrid_manifest, operation="hybrid_manifest")
        report = f"""# Historical causal reconstruction parity

SYMBOL = {selected}
PROFILE = {PROFILE}
TIMEFRAME = 5m
CANDLE_HISTORY_START = {inventory['candle_5m_start']}
CANDLE_HISTORY_END = {inventory['candle_5m_end']}
PERSISTED_START = {inventory['persisted_observation_start']}
PERSISTED_END = {inventory['persisted_observation_end']}
OVERLAP_START = {parity['overlap_start']}
OVERLAP_END = {parity['overlap_end']}
OVERLAP_BOUNDARIES = {inventory['overlap_boundary_count']}
RECONSTRUCTED_OVERLAP_ROWS = {len(reconstructed)}
PERSISTED_OVERLAP_ROWS = {len(persisted)}
MATCHED_BOUNDARIES = {parity['matched_boundaries']}
SETUP_PARITY = {parity['setup_parity']}
DIRECTION_PARITY = {parity['direction_parity']}
STRATEGY_STATUS_PARITY = {parity['strategy_status_parity']}
ELIGIBILITY_PARITY = {parity['eligibility_parity']}
TERMINAL_STAGE_PARITY = {parity['terminal_stage_parity']}
REJECTION_REASON_PARITY = {parity['rejection_reason_parity']}
STRATEGY_SCORE_ERROR_P50 = {parity['numeric_errors']['strategy_score']['absolute_error_p50']}
STRATEGY_SCORE_ERROR_P95 = {parity['numeric_errors']['strategy_score']['absolute_error_p95']}
STRATEGY_SCORE_ERROR_MAX = {parity['numeric_errors']['strategy_score']['absolute_error_max']}
NET_RR_ERROR_P50 = {parity['numeric_errors']['net_rr']['absolute_error_p50']}
NET_RR_ERROR_P95 = {parity['numeric_errors']['net_rr']['absolute_error_p95']}
NET_RR_ERROR_MAX = {parity['numeric_errors']['net_rr']['absolute_error_max']}
COST_INPUT_PARITY = {parity['cost_input_parity']}
PROBABILITY_INPUT_PARITY = {parity['probability_input_parity']}
EV_INPUT_PARITY = {parity['ev_input_parity']}
CRITICAL_FIELD_MISMATCHES = {parity['critical_field_mismatches']}
NUMERIC_MISMATCHES = {parity['numeric_mismatch_count']}
CAUSALITY_VIOLATIONS = {causality['violation_count']}
CROSS_SYMBOL_CONTAMINATION = {cross_symbol}
RECONSTRUCTION_PARITY = {parity['reconstruction_parity']}
HISTORY_TARGET_DAYS = {HISTORY_TARGET_DAYS}
HISTORY_ACTUAL_DAYS = {hybrid_manifest['history_actual_days']}
HISTORY_DEPTH_STATUS = {hybrid_manifest['status']}
"""
        DEFAULT_ARTIFACT_WRITER.atomic_text(output / "REPORT.md", report, operation="reconstruction_report")
        return ReconstructionResult(output, parity, hybrid_manifest)
    finally:
        database.dispose()


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Read-only historical reconstruction parity audit")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-overlap-boundaries", type=int)
    parser.add_argument("--database-url")
    args = parser.parse_args(argv)
    result = run_reconstruction_audit(
        symbol=args.symbol, output=args.output,
        max_overlap_boundaries=args.max_overlap_boundaries,
        database_url=args.database_url,
    )
    print(result.output / "REPORT.md")
    print(f"RECONSTRUCTION_PARITY = {result.parity['reconstruction_parity']}")


if __name__ == "__main__":
    main()
