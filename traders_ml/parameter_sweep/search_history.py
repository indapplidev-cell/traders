"""Bounded, SELECT-only history acquisition for result search.

Candles are independent of old PAPER positions and setup admission. Persisted
geometry is retained as evidence, never silently used as a universal historical
order book. Cost availability is inventory, not an unconditional dataset gate.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from sqlalchemy import text

from .engine import ReadOnlyResearchDatabase, resolve_database_binding
from .result_search import SearchRequest, fingerprint, ResultSearchService

SCHEMA = "result-search-history/3"
TIMEFRAMES = {"1m": 60000, "5m": 300000, "15m": 900000, "1h": 3600000}


def validate_candles(rows: list[dict[str, Any]], step: int, start: int, end: int) -> dict[str, Any]:
    opens = [int(r["open_time_ms"]) for r in rows]
    closes = [int(r["close_time_ms"]) for r in rows]
    gaps = sum(max(0, (b - a) // step - 1) for a, b in zip(opens, opens[1:]))
    invalid = sum(1 for r in rows if not (
        int(r["close_time_ms"]) == int(r["open_time_ms"]) + step - 1
        and float(r["low"]) <= min(float(r["open"]), float(r["close"]))
        and float(r["high"]) >= max(float(r["open"]), float(r["close"]))
        and float(r["low"]) > 0 and float(r["volume"]) >= 0))
    return {"count": len(rows), "first_open": min(opens) if opens else None,
            "last_close": max(closes) if closes else None,
            "duplicates": len(opens) - len(set(opens)), "gaps": gaps,
            "invalid_candles": invalid,
            "start_missing": not opens or min(opens) > start + step - 1,
            "tail_missing": not closes or max(closes) < end - step,
            "future_rows": sum(t >= end for t in closes)}


class HistoryProvider:
    def __init__(self, database: ReadOnlyResearchDatabase | None = None):
        self.database = database

    @staticmethod
    def load(directory: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        manifest = json.loads((directory / "DATASET_MANIFEST.json").read_text())
        data = (directory / "HISTORY.jsonl").read_bytes()
        if sha256(data).hexdigest() != manifest["content_sha256"]:
            raise ValueError("DATASET_CHECKSUM_MISMATCH")
        identity = dict(manifest)
        claimed = identity.pop("fingerprint")
        if fingerprint(identity) != claimed:
            raise ValueError("MANIFEST_FINGERPRINT_MISMATCH")
        if manifest.get("statistics"):
            stats = manifest["statistics"]
            content = (directory / "STATISTICS.json").read_bytes()
            if sha256(content).hexdigest() != stats["content_sha256"]:
                raise ValueError("STATISTICS_CHECKSUM_MISMATCH")
            from .historical_statistics import HistoricalStatistics
            if HistoricalStatistics(json.loads(content), 0).fingerprint != stats["fingerprint"]:
                raise ValueError("STATISTICS_IDENTITY_MISMATCH")
        return manifest, [json.loads(line) for line in data.splitlines()]

    @staticmethod
    def causal_window(rows: list[dict[str, Any]], symbol: str, timeframe: str,
                      cutoff_ms: int) -> list[dict[str, Any]]:
        return [r for r in rows if r["kind"] == "CANDLE" and r["symbol"] == symbol
                and r["timeframe"] == timeframe and int(r["close_time_ms"]) < cutoff_ms]

    def freeze(self, request: SearchRequest, directory: Path, *, warmup_bars: int = 200,
               exit_tail_ms: int = 3600000, max_rows: int = 100000,
               independent_interval: tuple[int, int] | None = None,
               statistics_source: Path | None = None, parameter_set_id: str | None = None) -> dict[str, Any]:
        if warmup_bars < 1 or exit_tail_ms < 1 or max_rows < 1:
            raise ValueError("POSITIVE_HISTORY_BOUNDS_REQUIRED")
        from app.engine_orchestrator.orchestrator_config import DEFAULT_MINIMUM_WINDOWS
        required_windows = dict(DEFAULT_MINIMUM_WINDOWS)
        if warmup_bars < max(required_windows.values()):
            raise ValueError("WARMUP_BELOW_AUTHORITATIVE_MINIMUM_WINDOWS")
        start = int(request.start.timestamp() * 1000)
        end = int(request.end.timestamp() * 1000)
        cutoff = int(request.data_cutoff.timestamp() * 1000)
        tail_end = min(end + exit_tail_ms, cutoff)
        acquisition_end = tail_end
        if independent_interval is not None:
            eval_start, eval_end = independent_interval
            if not end + exit_tail_ms <= eval_start < eval_end or eval_end + exit_tail_ms > cutoff:
                raise ValueError("INDEPENDENT_INTERVAL_OVERLAPS_SEARCH_TAIL_OR_EXCEEDS_CUTOFF")
            acquisition_end = eval_end + exit_tail_ms
        if (statistics_source is None) != (parameter_set_id is None):
            raise ValueError("STATISTICS_SOURCE_AND_SET_REQUIRED_TOGETHER")
        if directory.exists():
            raise ValueError("DATASET_DIRECTORY_ALREADY_EXISTS")
        database = self.database or ReadOnlyResearchDatabase(resolve_database_binding())
        coverage: dict[str, Any] = {}
        missing: list[str] = []
        conditional: list[str] = []
        epochs: set[str] = set()
        # Serialize incrementally in memory under both row and byte ceilings.
        # At most the configured budget is retained; no unbounded fetchall.
        lines: list[bytes] = []
        used = 0
        def append(row: dict[str, Any]) -> None:
            nonlocal used
            encoded = json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"
            used += len(encoded)
            if len(lines) >= max_rows or used > min(request.artifact_budget_bytes, request.storage_budget_bytes) - 16384:
                raise ValueError("HISTORY_STORAGE_OR_ROW_BUDGET_EXCEEDED")
            lines.append(encoded)
        try:
            with database.connection() as connection:
                connection.exec_driver_sql("SET LOCAL statement_timeout='20000ms'")
                readonly = connection.execute(text("SELECT current_setting('transaction_read_only')")).scalar_one()
                if readonly != "on":
                    raise ValueError("READONLY_SESSION_REQUIRED")
                tables = [r[0] for r in connection.execute(text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name"))]
                schema = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                for symbol in request.symbols:
                    for timeframe, step in TIMEFRAMES.items():
                        lower = start - warmup_bars * step
                        query = text(f"SELECT symbol,open_time_ms,close_time_ms,open,high,low,close,volume,data_checksum "
                                     f"FROM candles_{timeframe} WHERE symbol=:symbol AND is_closed=true "
                                     "AND open_time_ms>=:start AND close_time_ms<:end ORDER BY open_time_ms LIMIT :limit")
                        group = []
                        for raw in connection.execute(query, dict(symbol=symbol, start=lower,
                                                                  end=acquisition_end, limit=max_rows + 1)).mappings():
                            row = dict(raw)
                            for key in ("open", "high", "low", "close", "volume"):
                                row[key] = str(row[key])
                            row.update(kind="CANDLE", timeframe=timeframe)
                            append(row)
                            group.append(row)
                        coverage[symbol + ":" + timeframe] = validate_candles(group, step, lower, acquisition_end)
                    # No setup/PAPER-status filter: collect evidence across all causal boundaries.
                    query = text("SELECT symbol,closed_until_ms,run_id,"
                                 "paper_payload_json->'paper_context'->'scalping_geometry_diagnostics' AS geometry,"
                                 "risk_payload_json AS risk,"
                                 "paper_payload_json->>'paper_status' AS paper_status,"
                                 "paper_payload_json->'frozen_parameter_snapshot' AS frozen,"
                                 "paper_payload_json->'effective_configuration' AS epoch "
                                 "FROM online_pipeline_results WHERE trade_profile_id=:profile AND symbol=:symbol "
                                 "AND closed_until_ms>=:start AND closed_until_ms<:end "
                                 "ORDER BY closed_until_ms,run_id LIMIT :limit")
                    total = cost_ready = raw_book = 0
                    for raw in connection.execute(query, dict(profile=request.profile, symbol=symbol,
                                                              start=start, end=(independent_interval[1] if independent_interval else end), limit=max_rows + 1)).mappings():
                        row = dict(raw)
                        # Retain immutable values, not repeated UI provenance labels.
                        frozen = row.get("frozen") or {}
                        row["frozen"] = {
                            "resolved_config_hash": frozen.get("resolved_config_hash"),
                            "parameters": {k: v["value"] for k, v in frozen.get("parameters", {}).items()},
                            "runtime_parameters": {k: v["value"] for k, v in frozen.get("runtime_parameters", {}).items()},
                        }
                        g = row.get("geometry") or {}
                        total += 1
                        cost_ready += int(g.get("commission_authoritative") is True
                                          and g.get("economic_input_timestamp_ms") is not None
                                          and g.get("spread_bps") is not None
                                          and g.get("depth_impact_bps") is not None)
                        raw_book += int(bool(g.get("bids")) and bool(g.get("asks")))
                        if row.get("epoch"):
                            epochs.add(fingerprint(row["epoch"]))
                        if row["frozen"].get("resolved_config_hash"):
                            epochs.add(row["frozen"]["resolved_config_hash"])
                        row.update(kind="PERSISTED_BOUNDARY")
                        append(row)
                    coverage[symbol + ":cost_evidence"] = {"boundaries": total,
                        "derived_cost_snapshots": cost_ready, "raw_depth_snapshots": raw_book}
                    if raw_book < (end - start) // TIMEFRAMES["5m"]:
                        conditional.append(symbol + ":DEPTH_RECOMPUTATION_REQUIRES_COMPATIBLE_INPUTS")
                    if cost_ready < (end - start) // TIMEFRAMES["5m"]:
                        conditional.append(symbol + ":COST_SNAPSHOT_REQUIRED_ONLY_IF_STAGE_REACHED")
        finally:
            if self.database is None:
                database.dispose()
        for key, value in coverage.items():
            if "duplicates" in value and any(value[name] for name in
                    ("duplicates", "gaps", "invalid_candles", "start_missing", "tail_missing", "future_rows")):
                missing.append(key + ":CANDLE_COVERAGE_INCOMPLETE")
        if tail_end < end + exit_tail_ms:
            missing.append("EXIT_TAIL_TRUNCATED_BY_DATA_CUTOFF")
        content = b"".join(lines)
        manifest = {"schema": SCHEMA, "symbols": request.symbols, "request_hash": request.identity,
                    "source": "PROJECT_PROTECTED_READONLY_DATABASE", "alembic": schema,
                    "source_tables": tables, "coverage": coverage, "config_epochs": sorted(epochs),
                    "required_warmup_windows": required_windows,
                    "intervals": {"search_start_ms": start, "search_end_ms": end,
                                  "warmup_bars_per_timeframe": warmup_bars, "exit_tail_end_ms": tail_end,
                                  "data_cutoff_ms": cutoff, "independent_evaluation": independent_interval,
                                  "acquisition_end_ms": acquisition_end},
                    "content_sha256": sha256(content).hexdigest(), "bytes": len(content),
                    "rows": len(lines), "missing_inputs": missing,
                    "conditional_input_requirements": conditional,
                    "requested_data_mode": request.data_mode,
                    "evidence_quality": "INCOMPLETE" if missing else request.data_mode,
                    "quality_scope": "CLOSED_MARKET_HISTORY_AND_RECORDED_SNAPSHOTS; REQUIRED_INPUTS_CHECKED_PER_COMBINATION",
                    "outcome": "BLOCKED_DATA" if missing else "READY_FOR_COMBINATION_ASSESSMENT"}
        manifest["fingerprint"] = fingerprint(manifest)
        directory.mkdir(parents=True, exist_ok=False)
        from .artifact_writer import DEFAULT_ARTIFACT_WRITER
        DEFAULT_ARTIFACT_WRITER.atomic_bytes(directory / "HISTORY.jsonl", content)
        if statistics_source is not None:
            from .historical_statistics import freeze_statistics
            stats = freeze_statistics(statistics_source, directory / "STATISTICS.json", parameter_set_id)
            data = (directory / "STATISTICS.json").read_bytes()
            if len(content) + len(data) + 16384 > min(request.storage_budget_bytes, request.artifact_budget_bytes):
                raise ValueError("DATASET_BUNDLE_STORAGE_BUDGET_EXCEEDED")
            manifest["statistics"] = {"fingerprint": stats["fingerprint"],
                                      "content_sha256": sha256(data).hexdigest(), "bytes": len(data),
                                      "evidence_quality": stats["evidence_quality"]}
        manifest.pop("fingerprint", None)
        manifest["fingerprint"] = fingerprint(manifest)
        ResultSearchService._write(directory / "DATASET_MANIFEST.json", manifest)
        self.load(directory)
        return manifest

    @staticmethod
    def search_view(directory: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Range generation cannot see the independent interval or exit outcomes."""
        manifest, rows = HistoryProvider.load(directory)
        end = manifest["intervals"]["search_end_ms"]
        return manifest, [r for r in rows if (
            r["kind"] == "CANDLE" and r["close_time_ms"] < end
            or r["kind"] == "PERSISTED_BOUNDARY" and r["closed_until_ms"] < end)]

    @staticmethod
    def partition(directory: Path, name: str) -> list[dict[str, Any]]:
        """Explicit non-overlapping event intervals; warmup is never a trial."""
        manifest, rows = HistoryProvider.load(directory)
        intervals = manifest["intervals"]
        start, end = intervals["search_start_ms"], intervals["search_end_ms"]
        evaluation = intervals.get("independent_evaluation")
        bounds = {"warmup": (float("-inf"), start), "search": (start, end),
                  "exit_tail": (end, intervals["exit_tail_end_ms"])}
        if evaluation:
            bounds["independent_evaluation"] = tuple(evaluation)
            bounds["independent_exit_tail"] = (evaluation[1], intervals["acquisition_end_ms"])
        if name not in bounds:
            raise ValueError("HISTORY_PARTITION_UNAVAILABLE:" + name)
        lower, upper = bounds[name]
        return [r for r in rows if lower <= (r["close_time_ms"] if r["kind"] == "CANDLE"
                                             else r["closed_until_ms"]) < upper]
