"""Bounded, SELECT-only history acquisition for result search.

Candles are independent of old PAPER positions and setup admission. Persisted
geometry is retained as evidence, never silently used as a universal historical
order book. Missing inputs keep the dataset BLOCKED_DATA.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from sqlalchemy import text

from .engine import ReadOnlyResearchDatabase, resolve_database_binding
from .result_search import SearchRequest, fingerprint, ResultSearchService

SCHEMA = "result-search-history/1"
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
        return manifest, [json.loads(line) for line in data.splitlines()]

    @staticmethod
    def causal_window(rows: list[dict[str, Any]], symbol: str, timeframe: str,
                      cutoff_ms: int) -> list[dict[str, Any]]:
        return [r for r in rows if r["kind"] == "CANDLE" and r["symbol"] == symbol
                and r["timeframe"] == timeframe and int(r["close_time_ms"]) < cutoff_ms]

    def freeze(self, request: SearchRequest, directory: Path, *, warmup_bars: int = 200,
               exit_tail_ms: int = 3600000, max_rows: int = 100000) -> dict[str, Any]:
        if warmup_bars < 1 or exit_tail_ms < 1 or max_rows < 1:
            raise ValueError("POSITIVE_HISTORY_BOUNDS_REQUIRED")
        start = int(request.start.timestamp() * 1000)
        end = int(request.end.timestamp() * 1000)
        cutoff = int(request.data_cutoff.timestamp() * 1000)
        tail_end = min(end + exit_tail_ms, cutoff)
        if directory.exists():
            raise ValueError("DATASET_DIRECTORY_ALREADY_EXISTS")
        database = self.database or ReadOnlyResearchDatabase(resolve_database_binding())
        coverage: dict[str, Any] = {}
        missing: list[str] = []
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
                                                                  end=tail_end, limit=max_rows + 1)).mappings():
                            row = dict(raw)
                            for key in ("open", "high", "low", "close", "volume"):
                                row[key] = str(row[key])
                            row.update(kind="CANDLE", timeframe=timeframe)
                            append(row)
                            group.append(row)
                        coverage[symbol + ":" + timeframe] = validate_candles(group, step, lower, tail_end)
                    # No setup/PAPER-status filter: collect evidence across all causal boundaries.
                    query = text("SELECT symbol,closed_until_ms,run_id,"
                                 "paper_payload_json->'paper_context'->'scalping_geometry_diagnostics' AS geometry,"
                                 "paper_payload_json->'effective_configuration' AS epoch "
                                 "FROM online_pipeline_results WHERE trade_profile_id=:profile AND symbol=:symbol "
                                 "AND closed_until_ms>=:start AND closed_until_ms<:end "
                                 "ORDER BY closed_until_ms,run_id LIMIT :limit")
                    total = cost_ready = raw_book = 0
                    for raw in connection.execute(query, dict(profile=request.profile, symbol=symbol,
                                                              start=start, end=end, limit=max_rows + 1)).mappings():
                        row = dict(raw)
                        g = row.get("geometry") or {}
                        total += 1
                        cost_ready += int(g.get("commission_authoritative") is True
                                          and g.get("economic_input_timestamp_ms") is not None
                                          and g.get("spread_bps") is not None
                                          and g.get("depth_impact_bps") is not None)
                        raw_book += int(bool(g.get("bids")) and bool(g.get("asks")))
                        if row.get("epoch"):
                            epochs.add(fingerprint(row["epoch"]))
                        row.update(kind="PERSISTED_BOUNDARY")
                        append(row)
                    coverage[symbol + ":cost_evidence"] = {"boundaries": total,
                        "derived_cost_snapshots": cost_ready, "raw_depth_snapshots": raw_book}
                    if raw_book < (end - start) // TIMEFRAMES["5m"]:
                        missing.append(symbol + ":HISTORICAL_DEPTH_LADDER_UNAVAILABLE_FOR_NEW_ENTRY_QUANTITY")
                    if cost_ready < (end - start) // TIMEFRAMES["5m"]:
                        missing.append(symbol + ":HISTORICAL_CAUSAL_COST_COVERAGE_INCOMPLETE")
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
                    "intervals": {"search_start_ms": start, "search_end_ms": end,
                                  "warmup_bars_per_timeframe": warmup_bars, "exit_tail_end_ms": tail_end,
                                  "data_cutoff_ms": cutoff, "independent_evaluation": None},
                    "content_sha256": sha256(content).hexdigest(), "bytes": len(content),
                    "rows": len(lines), "missing_inputs": missing,
                    "requested_data_mode": request.data_mode,
                    "evidence_quality": "INCOMPLETE" if missing else "UNVERIFIED",
                    "outcome": "BLOCKED_DATA" if missing else "REQUIRES_ENGINE_INPUT_CERTIFICATION"}
        manifest["fingerprint"] = fingerprint(manifest)
        directory.mkdir(parents=True, exist_ok=False)
        from .artifact_writer import DEFAULT_ARTIFACT_WRITER
        DEFAULT_ARTIFACT_WRITER.atomic_bytes(directory / "HISTORY.jsonl", content)
        ResultSearchService._write(directory / "DATASET_MANIFEST.json", manifest)
        self.load(directory)
        return manifest
