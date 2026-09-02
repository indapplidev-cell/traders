"""Durable, passive prospective calibration collection for first-class Scalping.

The collector reads completed production-search projections and closed candles.
It owns no trading authority and has no dependency on an exchange client.
"""

from __future__ import annotations

import json
import os
import signal
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol, Sequence
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row


PROFILE_ID = "trade-5m-v2"
TRADE_MODE = "SCALPING"
COLLECTOR_SCHEMA_REVISION = "scalping-prospective-collector-v1"
OBSERVATION_SCHEMA_REVISION = "scalping-calibration-observation-v1"
OUTCOME_SCHEMA_REVISION = "scalping-calibration-outcome-v1"
INCIDENT_SCHEMA_REVISION = "scalping-calibration-boundary-incident-v1"
ANALYSIS_SEMANTICS_VERSION = "scalping-analysis-v1"
DECISION_SEMANTICS_VERSION = "scalping-risk-type-contract-v2"
OWNER_NAMESPACE = 1_937_830_411
OWNER_KEY = 527_115_001
DEFAULT_MAX_PART_BYTES = 64 * 1024 * 1024
DEFAULT_OUTCOME_HORIZON_MS = (45 * 60 + 120) * 1000


class MixedRuntimeLineageWithinBoundary(RuntimeError):
    """A boundary rejected after its immutable incident evidence is durable."""

    def __init__(self, boundary_ms: int, incident_id: str) -> None:
        super().__init__("MIXED_RUNTIME_LINEAGE_WITHIN_BOUNDARY")
        self.boundary_ms = int(boundary_ms)
        self.incident_id = incident_id


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime | None = None) -> str:
    current = value or utc_now()
    return current.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    encoded = (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    try:
        with temporary.open("wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if os.name != "nt":
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _integer(value: object) -> int | None:
    number = _number(value)
    return int(number) if number is not None else None


def _first(mapping: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        value = mapping.get(name)
        if value is not None:
            return value
    return None


@dataclass(frozen=True, slots=True)
class HomogeneityIdentity:
    profile_id: str
    parameter_set_id: str
    runtime_source_commit: str
    runtime_artifact_id: str
    schema_revision: str
    market_universe_id: str
    decision_semantics_version: str = DECISION_SEMANTICS_VERSION
    collector_schema_version: str = COLLECTOR_SCHEMA_REVISION

    @property
    def segment_id(self) -> str:
        digest = sha256(canonical_json(asdict(self)).encode("utf-8")).hexdigest()[:24]
        return f"scalping-calibration-segment-{digest}"


def market_universe_id(symbols: Sequence[str]) -> str:
    normalized = tuple(symbol.upper() for symbol in symbols)
    digest = sha256(canonical_json(normalized).encode("utf-8")).hexdigest()[:16]
    return f"exact{len(normalized)}-{digest}"


def normalize_microstructure(paper: Mapping[str, Any], decision_cutoff_ms: int | None) -> dict[str, Any]:
    context = _mapping(paper.get("paper_context"))
    snapshot = _mapping(context.get("strategy_cap_shadow_economic_snapshot"))
    if not snapshot:
        shadow = _mapping(paper.get("shadow_plan"))
        diagnostic = _mapping(_mapping(shadow.get("paper_context")).get("scalping_geometry_diagnostics"))
        snapshot = diagnostic
    timestamp = _integer(_first(snapshot, "economic_input_timestamp_ms", "microstructure_timestamp_ms"))
    cutoff = _integer(_first(snapshot, "decision_cutoff_timestamp_ms")) or decision_cutoff_ms
    maximum_age = _integer(snapshot.get("maximum_age_ms")) or 5_000
    age = cutoff - timestamp if cutoff is not None and timestamp is not None else None
    status = "AVAILABLE"
    reason = None
    if not snapshot or timestamp is None or cutoff is None:
        status, reason = "UNAVAILABLE_OR_STALE", "MISSING_CAUSAL_TIMESTAMP"
    elif timestamp > cutoff:
        status, reason = "UNAVAILABLE_OR_STALE", "FUTURE_QUOTE_REJECTED"
    elif age is None or age < 0 or age > maximum_age:
        status, reason = "UNAVAILABLE_OR_STALE", "STALE_QUOTE_REJECTED"
    elif snapshot.get("causally_usable") is False:
        status, reason = "UNAVAILABLE_OR_STALE", str(snapshot.get("capture_status") or "CAUSALITY_REJECTED")
    usable = status == "AVAILABLE"
    return {
        "microstructure_status": status,
        "unavailable_reason": reason,
        "best_bid": _number(snapshot.get("bid")) if usable else None,
        "best_ask": _number(snapshot.get("ask")) if usable else None,
        "spread_bps": _number(snapshot.get("spread_bps")) if usable else None,
        "bounded_depth": {
            "reference_notional": _number(snapshot.get("reference_notional")) if usable else None,
            "reference_quantity": _number(snapshot.get("reference_quantity")) if usable else None,
            "limit": _integer(snapshot.get("depth_limit")),
        },
        "entry_side_vwap": _number(snapshot.get("buy_vwap")) if usable else None,
        "exit_side_vwap": _number(snapshot.get("sell_vwap")) if usable else None,
        "depth_impact_bps": _number(snapshot.get("depth_impact_bps")) if usable else None,
        "microstructure_timestamp_ms": timestamp if usable else None,
        "decision_cutoff_timestamp_ms": cutoff,
        "microstructure_age_ms": age if usable else None,
        "microstructure_source": snapshot.get("economic_input_source") if usable else None,
        "spread_source": snapshot.get("spread_source") if usable else None,
        "depth_source": snapshot.get("depth_impact_source") if usable else None,
        "future_leakage": False,
    }


def _extract_followup(observation: Mapping[str, Any]) -> dict[str, Any] | None:
    setup = _mapping(observation.get("setup"))
    raw = _mapping(setup.get("raw"))
    if raw.get("status") != "SETUP_CANDIDATE":
        return None
    context = _mapping(raw.get("context"))
    paper = _mapping(_mapping(observation.get("current_production_decision_trace")).get("paper_raw"))
    direction = _first(paper, "paper_direction", "source_direction_hint") or raw.get("direction_hint")
    entry = _number(_first(paper, "hypothetical_entry_reference"))
    if entry is None:
        entry = _number(_first(context, "confirmation_close", "reference_close", "current_closed_candle_close"))
    if entry is None:
        return None
    boundary_ms = int(observation["identity"]["boundary_time_ms"])
    return {
        "opportunity_id": observation["identity"].get("opportunity_id"),
        "observation_id": observation["observation_id"],
        "symbol": observation["identity"]["symbol"],
        "boundary_time_ms": boundary_ms,
        "entry_decision_time_ms": _integer(_first(paper, "created_at_ms")) or boundary_ms,
        "direction": direction,
        "entry_reference": entry,
        "baseline_stop": _number(paper.get("hypothetical_stop_level")),
        "baseline_target": _number(paper.get("hypothetical_target_level")),
        "ttl_ms": 60_000,
        "time_stop_ms": 30 * 60 * 1000,
        "followup_due_ms": boundary_ms + DEFAULT_OUTCOME_HORIZON_MS,
    }


def evaluate_outcome(followup: Mapping[str, Any], candles: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Apply deterministic conservative baseline semantics to a frozen path."""
    boundary = int(followup["boundary_time_ms"])
    entry = float(followup["entry_reference"])
    ttl_end = boundary + int(followup.get("ttl_ms") or 60_000)
    time_stop = boundary + int(followup.get("time_stop_ms") or 30 * 60 * 1000)
    direction = str(followup.get("direction") or "").upper()
    stop, target = _number(followup.get("baseline_stop")), _number(followup.get("baseline_target"))
    ordered = sorted(candles, key=lambda item: int(item["open_time_ms"]))
    entry_index = next((index for index, candle in enumerate(ordered)
                        if int(candle["open_time_ms"]) < ttl_end
                        and float(candle["low"]) <= entry <= float(candle["high"])), None)
    serialized = [{
        "open_time_ms": int(candle["open_time_ms"]),
        "close_time_ms": int(candle["close_time_ms"]),
        "open": _number(candle.get("open")), "high": _number(candle.get("high")),
        "low": _number(candle.get("low")), "close": _number(candle.get("close")),
        "volume": _number(candle.get("volume")), "quote_volume": _number(candle.get("quote_volume")),
        "trades_count": _integer(candle.get("trades_count")), "source": candle.get("source"),
        "data_checksum": candle.get("data_checksum"),
    } for candle in ordered]
    result: dict[str, Any] = {
        "entry_status": "EXPIRED" if entry_index is None else "ENTERED",
        "entry_candle_open_time_ms": None if entry_index is None else int(ordered[entry_index]["open_time_ms"]),
        "baseline_outcome": "ENTRY_EXPIRED" if entry_index is None else None,
        "tp_first": None, "sl_first": None, "both_same_candle": None,
        "mfe_bps": None, "mae_bps": None, "holding_time_ms": None,
        "time_to_mfe_ms": None, "time_to_mae_ms": None,
        "time_to_target_ms": None, "time_to_stop_ms": None,
        "closed_candle_path": serialized,
        "intrabar_path_inferred": False,
    }
    if entry_index is None:
        return result
    active = [candle for candle in ordered[entry_index:] if int(candle["open_time_ms"]) < time_stop]
    if not active:
        return result
    favorable: list[tuple[float, int]] = []
    adverse: list[tuple[float, int]] = []
    terminal_ms = time_stop
    outcome = "TIME_EXPIRED" if stop is not None and target is not None else "PATH_CAPTURED_NO_BASELINE_GEOMETRY"
    tp_first = sl_first = both = False
    target_time = stop_time = None
    for candle in active:
        opened = int(candle["open_time_ms"])
        high, low = float(candle["high"]), float(candle["low"])
        if direction in {"BULLISH", "LONG"}:
            favorable.append(((high - entry) / entry * 10_000, opened))
            adverse.append(((entry - low) / entry * 10_000, opened))
            hit_target = target is not None and high >= target
            hit_stop = stop is not None and low <= stop
        else:
            favorable.append(((entry - low) / entry * 10_000, opened))
            adverse.append(((high - entry) / entry * 10_000, opened))
            hit_target = target is not None and low <= target
            hit_stop = stop is not None and high >= stop
        if hit_target and target_time is None:
            target_time = opened - boundary
        if hit_stop and stop_time is None:
            stop_time = opened - boundary
        if hit_target and hit_stop:
            outcome, both, terminal_ms = "AMBIGUOUS_BOTH_SAME_CANDLE", True, opened
            break
        if hit_stop:
            outcome, sl_first, terminal_ms = "SL_FIRST", True, opened
            break
        if hit_target:
            outcome, tp_first, terminal_ms = "TP_FIRST", True, opened
            break
    best = max(favorable, default=(0.0, boundary), key=lambda item: item[0])
    worst = max(adverse, default=(0.0, boundary), key=lambda item: item[0])
    result.update({
        "baseline_outcome": outcome, "tp_first": tp_first, "sl_first": sl_first,
        "both_same_candle": both, "mfe_bps": best[0], "mae_bps": worst[0],
        "holding_time_ms": max(0, terminal_ms - boundary),
        "time_to_mfe_ms": max(0, best[1] - boundary),
        "time_to_mae_ms": max(0, worst[1] - boundary),
        "time_to_target_ms": target_time, "time_to_stop_ms": stop_time,
    })
    return result


class Repository(Protocol):
    def latest_boundary(self) -> int | None: ...
    def next_boundary(self, after_ms: int) -> int | None: ...
    def load_boundary(self, boundary_ms: int) -> list[dict[str, Any]]: ...
    def load_outcome_candles(self, followups: Sequence[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]: ...


class PostgresRepository:
    def __init__(self, connection: psycopg.Connection[Any], profile_id: str = PROFILE_ID) -> None:
        self.connection, self.profile_id = connection, profile_id
        self.query_count = 0

    def _execute(self, sql: str, parameters: Sequence[Any] = ()) -> list[dict[str, Any]]:
        self.query_count += 1
        with self.connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(sql, parameters)
            return list(cursor.fetchall())

    def latest_boundary(self) -> int | None:
        rows = self._execute("SELECT max(closed_until_ms) value FROM online_pipeline_runs WHERE trade_profile_id=%s", (self.profile_id,))
        return _integer(rows[0]["value"])

    def next_boundary(self, after_ms: int) -> int | None:
        rows = self._execute(
            "SELECT min(closed_until_ms) value FROM online_pipeline_runs WHERE trade_profile_id=%s AND closed_until_ms>%s",
            (self.profile_id, after_ms),
        )
        return _integer(rows[0]["value"])

    def load_boundary(self, boundary_ms: int) -> list[dict[str, Any]]:
        return self._execute(
            """
            SELECT r.run_id,r.symbol,r.closed_until_ms,r.finished_at,r.duration_ms,r.status pipeline_status,
                   r.analysis_status,r.setup_status,r.strategy_status,r.risk_status,r.paper_status,
                   r.final_result,r.final_reason,r.error_code,r.future_bars_used,r.daemon_instance_id,
                   res.id result_id,res.market_data_payload_json market,res.analysis_payload_json analysis,
                   res.setup_payload_json setup,res.strategy_payload_json strategy,res.risk_payload_json risk,
                   res.paper_payload_json paper,res.module_reasons_json module_reasons,
                   res.module_warnings_json module_warnings,res.safety_counters_json safety_counters,
                   c.open_time_ms candle_open_time_ms,c.close_time_ms candle_close_time_ms,
                   c.open candle_open,c.high candle_high,c.low candle_low,c.close candle_close,
                   c.volume candle_volume,c.quote_volume candle_quote_volume,c.trades_count candle_trades_count,
                   c.source candle_source,c.data_checksum candle_checksum
            FROM online_pipeline_runs r
            LEFT JOIN online_pipeline_results res ON res.run_id=r.run_id
            LEFT JOIN candles_5m c ON c.symbol=r.symbol AND c.open_time_ms=r.closed_until_ms-300000
            WHERE r.trade_profile_id=%s AND r.closed_until_ms=%s
            ORDER BY r.symbol
            """,
            (self.profile_id, boundary_ms),
        )

    def load_outcome_candles(self, followups: Sequence[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        if not followups:
            return {}
        symbols = sorted({str(item["symbol"]) for item in followups})
        start = min(int(item["boundary_time_ms"]) for item in followups)
        end = max(int(item["followup_due_ms"]) for item in followups)
        rows = self._execute(
            """SELECT symbol,open_time_ms,close_time_ms,open,high,low,close,volume,quote_volume,
                      trades_count,source,data_checksum FROM candles_1m
               WHERE symbol=ANY(%s) AND open_time_ms>=%s AND open_time_ms<%s
               ORDER BY symbol,open_time_ms""",
            (symbols, start, end),
        )
        grouped: dict[str, list[dict[str, Any]]] = {symbol: [] for symbol in symbols}
        for row in rows:
            grouped[str(row["symbol"])].append(row)
        return grouped


class PostgresCollectorOwner:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.connection: psycopg.Connection[Any] | None = None

    def acquire(self) -> bool:
        self.connection = psycopg.connect(self.database_url, autocommit=True, application_name="traders_scalping_calibration_collector")
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(%s,%s)", (OWNER_NAMESPACE, OWNER_KEY))
            acquired = bool(cursor.fetchone()[0])
        if not acquired:
            self.connection.close()
            self.connection = None
        return acquired

    def active(self) -> bool:
        if self.connection is None or self.connection.closed:
            return False
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return cursor.fetchone()[0] == 1
        except Exception:
            return False

    def owner_count(self) -> int:
        if not self.active():
            return 0
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM pg_locks WHERE locktype='advisory' AND classid=%s AND objid=%s AND granted",
                (OWNER_NAMESPACE, OWNER_KEY),
            )
            return int(cursor.fetchone()[0])

    def release(self) -> None:
        if self.connection is not None:
            try:
                with self.connection.cursor() as cursor:
                    cursor.execute("SELECT pg_advisory_unlock(%s,%s)", (OWNER_NAMESPACE, OWNER_KEY))
            finally:
                self.connection.close()
                self.connection = None


class AppendOnlyStore:
    def __init__(self, root: Path, identity: HomogeneityIdentity, *, max_part_bytes: int = DEFAULT_MAX_PART_BYTES) -> None:
        self.root, self.identity = root, identity
        self.max_part_bytes = max_part_bytes
        self.manifest_path = root / "manifest.json"
        self.checkpoint_path = root / "checkpoint.json"
        self.health_path = root / "health.json"
        root.mkdir(parents=True, exist_ok=True)
        self.manifest = self._load_manifest()
        self.identities = self._scan_identities()
        self.observation_ids = self.identities.setdefault("observations", set())
        self.outcome_ids = self.identities.setdefault("outcomes", set())

    def _load_manifest(self) -> dict[str, Any]:
        if self.manifest_path.exists():
            manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        else:
            manifest = {"schema_revision": "scalping-calibration-manifest-v1", "storage_type": "APPEND_ONLY_JSONL", "segments": [], "parts": [], "exclusions": []}
        manifest.setdefault("exclusions", [])
        if not any(item.get("observation_segment_id") == self.identity.segment_id for item in manifest["segments"]):
            manifest["segments"].append({
                "observation_segment_id": self.identity.segment_id,
                "started_at": iso_utc(),
                "homogeneity_identity": asdict(self.identity),
            })
            atomic_write_json(self.manifest_path, manifest)
        return manifest

    def register_exclusion(self, incident: Mapping[str, Any]) -> None:
        incident_id = str(incident["incident_id"])
        boundary_ms = int(incident["boundary_time_ms"])
        self.append("incidents", incident)
        if not any(item.get("incident_id") == incident_id for item in self.manifest["exclusions"]):
            self.manifest["exclusions"].append({
                "incident_id": incident_id,
                "observation_segment_id": self.identity.segment_id,
                "boundary_time_ms": boundary_ms,
                "reason": "MIXED_RUNTIME_LINEAGE_WITHIN_BOUNDARY",
                "calibration_eligible": False,
                "raw_records_mutated": False,
            })
            atomic_write_json(self.manifest_path, self.manifest)

    def _scan_identities(self) -> dict[str, set[str]]:
        identities: dict[str, set[str]] = {}
        for part in self.manifest.get("parts", []):
            path = self.root / str(part["path"])
            if not path.exists():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                record = json.loads(line)
                identities.setdefault(str(part.get("kind")), set()).add(str(record["observation_id"]))
        return identities

    def _part_path(self, kind: str, observed_at: datetime | None = None) -> Path:
        day = (observed_at or utc_now()).strftime("%Y%m%d")
        prefix = f"{kind}-{self.identity.segment_id[-8:]}-{day}"
        candidates = sorted(self.root.glob(f"{prefix}.part*.jsonl"))
        current = candidates[-1] if candidates else self.root / f"{prefix}.part0001.jsonl"
        if current.exists() and current.stat().st_size >= self.max_part_bytes:
            number = int(current.stem.rsplit("part", 1)[1]) + 1
            current = self.root / f"{prefix}.part{number:04d}.jsonl"
        relative = current.name
        if not any(part.get("path") == relative for part in self.manifest["parts"]):
            self.manifest["parts"].append({"kind": kind, "path": relative, "observation_segment_id": self.identity.segment_id})
            atomic_write_json(self.manifest_path, self.manifest)
        return current

    def append(self, kind: str, record: Mapping[str, Any]) -> bool:
        identity = str(record["observation_id"])
        known = self.identities.setdefault(kind, set())
        if identity in known:
            return False
        path = self._part_path(kind)
        encoded = (canonical_json(record) + "\n").encode("utf-8")
        descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
        try:
            written = os.write(descriptor, encoded)
            if written != len(encoded):
                raise OSError("short append-only calibration write")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        known.add(identity)
        return True

    def load_checkpoint(self) -> dict[str, Any] | None:
        if not self.checkpoint_path.exists():
            return None
        value = json.loads(self.checkpoint_path.read_text(encoding="utf-8"))
        if value.get("observation_segment_id") != self.identity.segment_id:
            return None
        return value

    def write_checkpoint(self, payload: Mapping[str, Any]) -> None:
        atomic_write_json(self.checkpoint_path, payload)

    def pending_followups(self) -> dict[str, dict[str, Any]]:
        pending: dict[str, dict[str, Any]] = {}
        for part in self.manifest.get("parts", []):
            if part.get("kind") != "observations" or part.get("observation_segment_id") != self.identity.segment_id:
                continue
            path = self.root / str(part["path"])
            if not path.exists():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                record = json.loads(line)
                followup = record.get("outcome_followup")
                if followup and record["observation_id"] not in self.outcome_ids:
                    pending[str(record["observation_id"])] = dict(followup)
        return pending

    def completed_trade_outcomes(self) -> int:
        terminal = {"TP_FIRST", "SL_FIRST", "AMBIGUOUS_BOTH_SAME_CANDLE", "TIME_EXPIRED"}
        completed = 0
        for part in self.manifest.get("parts", []):
            if part.get("kind") != "outcomes" or part.get("observation_segment_id") != self.identity.segment_id:
                continue
            path = self.root / str(part["path"])
            if not path.exists():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                if json.loads(line).get("baseline_outcome") in terminal:
                    completed += 1
        return completed

    def segment_stats(self) -> dict[str, int]:
        stats = {"micro_total": 0, "micro_available": 0, "missing": 0, "duplicates": 0, "errors": 0,
                 "boundary_diagnostics": 0}
        for part in self.manifest.get("parts", []):
            if part.get("observation_segment_id") != self.identity.segment_id:
                continue
            path = self.root / str(part["path"])
            if not path.exists():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                record = json.loads(line)
                if part.get("kind") == "observations":
                    stats["micro_total"] += 1
                    if _mapping(record.get("microstructure")).get("microstructure_status") == "AVAILABLE":
                        stats["micro_available"] += 1
                elif part.get("kind") == "diagnostics":
                    stats["boundary_diagnostics"] += 1
                    stats["missing"] += len(record.get("missing_symbols") or [])
                    stats["duplicates"] += len(record.get("duplicate_symbols") or [])
                    stats["errors"] += len(record.get("error_codes") or [])
        return stats


@dataclass(slots=True)
class CollectorConfig:
    output_directory: Path
    symbols: tuple[str, ...]
    parameter_set_id: str
    runtime_source_commit: str
    runtime_artifact_id: str
    schema_revision: str = "0021_independent_scalping_profile_v2"
    poll_seconds: float = 10.0
    boundary_wait_seconds: int = 240
    max_part_bytes: int = DEFAULT_MAX_PART_BYTES

    @property
    def identity(self) -> HomogeneityIdentity:
        return HomogeneityIdentity(
            profile_id=PROFILE_ID, parameter_set_id=self.parameter_set_id,
            runtime_source_commit=self.runtime_source_commit,
            runtime_artifact_id=self.runtime_artifact_id,
            schema_revision=self.schema_revision,
            market_universe_id=market_universe_id(self.symbols),
        )


class ProspectiveCalibrationCollector:
    def __init__(self, config: CollectorConfig, repository: Repository, owner: PostgresCollectorOwner) -> None:
        self.config, self.repository, self.owner = config, repository, owner
        self.instance_id = f"scalping-calibration-collector-{uuid4()}"
        self.store = AppendOnlyStore(config.output_directory, config.identity, max_part_bytes=config.max_part_bytes)
        self.started_at = iso_utc()
        self.stop_requested = False
        stats = self.store.segment_stats()
        self.errors_count = stats["errors"]
        self.missing_records = stats["missing"]
        self.duplicate_records = stats["duplicates"]
        self.micro_available = stats["micro_available"]
        self.micro_total = stats["micro_total"]
        self.boundary_diagnostics = stats["boundary_diagnostics"]
        self.runtime_lineage_transition_count = len(
            self.store.identities.setdefault("lineage", set())
        )
        self.boundaries: set[int] = set()
        self.excluded_boundaries: set[int] = {
            int(item["boundary_time_ms"])
            for item in self.store.manifest.get("exclusions", [])
            if item.get("observation_segment_id") == self.config.identity.segment_id
            and item.get("boundary_time_ms") is not None
        }
        self.runtime_daemon_instance_id: str | None = None
        self.last_persisted_run_id: str | None = None
        checkpoint = self.store.load_checkpoint()
        if checkpoint:
            self.last_seen_boundary = int(checkpoint.get("last_seen_boundary") or 0)
            self.last_persisted_boundary = int(checkpoint.get("last_persisted_boundary") or 0)
            self.records_written = len(self.store.observation_ids)
            self.boundaries = set(int(value) for value in checkpoint.get("persisted_boundaries", []))
            self.excluded_boundaries.update(
                int(value) for value in checkpoint.get("excluded_boundaries", [])
            )
            self.runtime_daemon_instance_id = checkpoint.get("runtime_daemon_instance_id")
            self.last_persisted_run_id = checkpoint.get("last_persisted_run_id")
        else:
            latest = repository.latest_boundary()
            self.last_seen_boundary = self.last_persisted_boundary = int(latest or 0)
            self.records_written = len(self.store.observation_ids)
        self.pending = self.store.pending_followups()

    def request_stop(self, *_: object) -> None:
        self.stop_requested = True

    def _observation(self, row: Mapping[str, Any]) -> dict[str, Any]:
        analysis, setup, strategy = (_mapping(row.get(name)) for name in ("analysis", "setup", "strategy"))
        risk, paper, market = (_mapping(row.get(name)) for name in ("risk", "paper", "market"))
        analysis_context = _mapping(analysis.get("analysis_context"))
        setup_context = _mapping(setup.get("context"))
        strategy_context = _mapping(strategy.get("context"))
        journal = _mapping(paper.get("scalping_evaluation_journal"))
        parameter_id = str(_first(paper, "runtime_parameter_set_id") or _first(strategy, "runtime_parameter_set_id") or _first(analysis, "runtime_parameter_set_id") or "")
        if parameter_id != self.config.parameter_set_id:
            raise RuntimeError("RUNTIME_PARAMETER_IDENTITY_CHANGED")
        analysis_semantic = str(
            _mapping(setup_context.get("scalping")).get("semantics_version")
            or ANALYSIS_SEMANTICS_VERSION
        )
        if analysis_semantic != ANALYSIS_SEMANTICS_VERSION:
            raise RuntimeError("ANALYSIS_SEMANTICS_IDENTITY_CHANGED")
        semantic = self.config.identity.decision_semantics_version
        cutoff = _integer(_first(strategy, "created_at_ms")) or _integer(_first(paper, "created_at_ms"))
        micro = normalize_microstructure(paper, cutoff)
        boundary = int(row["closed_until_ms"])
        opportunity = _first(setup, "opportunity_id") or _mapping(strategy_context).get("opportunity_id")
        observation_id = "obs-" + sha256(
            f"{self.config.identity.segment_id}|{boundary}|{row['symbol']}|{row['run_id']}|{row['result_id']}".encode("utf-8")
        ).hexdigest()
        candle = None if row.get("candle_open_time_ms") is None else {
            "open_time_ms": int(row["candle_open_time_ms"]), "close_time_ms": int(row["candle_close_time_ms"]),
            "open": _number(row.get("candle_open")), "high": _number(row.get("candle_high")),
            "low": _number(row.get("candle_low")), "close": _number(row.get("candle_close")),
            "volume": _number(row.get("candle_volume")), "quote_volume": _number(row.get("candle_quote_volume")),
            "trades_count": _integer(row.get("candle_trades_count")), "source": row.get("candle_source"),
            "data_checksum": row.get("candle_checksum"),
        }
        observation: dict[str, Any] = {
            "schema_revision": OBSERVATION_SCHEMA_REVISION,
            "observation_id": observation_id,
            "observation_segment_id": self.config.identity.segment_id,
            "collector_instance_id": self.instance_id,
            "captured_at": iso_utc(),
            "identity": {
                "profile_id": PROFILE_ID, "trade_mode": TRADE_MODE,
                "parameter_set_id": parameter_id,
                "runtime_source_commit": self.config.runtime_source_commit,
                "runtime_artifact_id": self.config.runtime_artifact_id,
                "schema_revision": self.config.schema_revision,
                "market_universe_id": self.config.identity.market_universe_id,
                "decision_semantics_version": semantic,
                "analysis_semantics_version": analysis_semantic,
                "boundary_time_ms": boundary,
                "boundary_time": datetime.fromtimestamp(boundary / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
                "symbol": row["symbol"], "run_id": row["run_id"], "result_id": row["result_id"],
                "opportunity_id": opportunity,
            },
            "market_context": {
                "closed_context_references": market,
                "boundary_5m_ohlcv": candle,
                "regime": _first(analysis, "regime") or analysis_context.get("regime"),
                "direction_bias": _first(setup, "direction_hint") or analysis.get("action"),
                "atr": _number(_first(setup_context, "atr_value") or _mapping(analysis_context.get("technical_indicators")).get("atr_14")),
                "volatility": _mapping(setup_context.get("volatility_state")) or None,
                "volume": None if candle is None else candle["volume"],
                "relative_volume": _number(_mapping(_mapping(analysis_context.get("quality_basis")).get("impulse_context")).get("fresh_volume_ratio")),
            },
            "microstructure": micro,
            "analysis": {
                "status": analysis.get("status"), "entry_quality_state": analysis.get("entry_quality"),
                "entry_quality_score": _number(_mapping(analysis.get("entry_quality_diagnostics")).get("score")),
                "entry_quality_tier": analysis.get("entry_quality"),
                "entry_quality_reason": _first(analysis, "entry_quality_reason_codes", "reason_codes"),
                "impulse_state": analysis.get("impulse_phase"), "confidence": _number(analysis.get("confidence")),
                "conflict_flags": analysis_context.get("conflicts"), "evidence": analysis.get("reason_codes"),
                "raw": analysis,
            },
            "setup": {
                "type": setup.get("setup_type"), "score": _number(setup.get("quality_score")),
                "direction": setup.get("direction_hint"), "entry_zone": setup.get("entry_zone"),
                "causal_invalidation": setup.get("causal_invalidation"), "target_candidates": setup.get("target_candidates"),
                "local_swing_references": setup_context.get("causal_support_candidates"),
                "liquidity_references": setup_context.get("causal_target_candidates"),
                "setup_age": None, "confirmation_state": setup.get("confirmation_state"), "raw": setup,
            },
            "strategy": {
                "raw_score": _number(_first(strategy, "strategy_raw_score", "strategy_score")),
                "component_scores": strategy.get("component_scores"), "penalties": strategy.get("strategy_penalties"),
                "cap_type": strategy.get("strategy_cap_type"), "cap_reason": strategy.get("strategy_cap_reason"),
                "cap_value": _number(strategy.get("strategy_cap_value")), "pre_cap_score": _number(strategy.get("strategy_pre_cap_score")),
                "post_cap_score": _number(strategy.get("strategy_post_cap_score")), "final_score": _number(_first(strategy, "strategy_final_score", "strategy_score")),
                "threshold": _number(strategy.get("strategy_quality_threshold")), "boolean_gate_states": strategy.get("strategy_gate_results"),
                "terminal_reason": _first(strategy, "strategy_failed_gate_reason", "rejection_reasons", "decision_reasons"),
                "raw": strategy,
            },
            "geometry_baseline_inputs": {
                "entry_reference": _first(paper, "hypothetical_entry_reference") or _first(setup_context, "confirmation_close", "reference_close", "current_closed_candle_close"),
                "causal_invalidation": _first(paper, "hypothetical_invalidation_level") or setup.get("causal_invalidation"),
                "atr": _first(setup_context, "atr_value"), "target_hierarchy_candidates": setup.get("target_candidates"),
                "structural_target_candidates": setup_context.get("causal_target_candidates"),
                "local_5m_target_candidates": setup_context.get("causal_resistance_candidates") or setup_context.get("causal_support_candidates"),
                "higher_tf_candidate_targets": setup_context.get("higher_timeframe_target_candidates"),
            },
            "cost_inputs": {
                "fee_assumptions_source": _mapping(_mapping(paper.get("paper_context")).get("strategy_cap_shadow_economic_snapshot")).get("fee_source"),
                "spread_bps": micro["spread_bps"], "slippage_assumptions_source": "RUNTIME_PARAMETER_SET",
                "depth_impact_bps": micro["depth_impact_bps"],
                "safety_margin_bps": _number(_mapping(_mapping(paper.get("paper_context")).get("strategy_cap_shadow_economic_snapshot")).get("safety_margin_bps")),
            },
            "current_production_decision_trace": {
                "geometry_result": journal.get("geometry"), "target_result": paper.get("target_source"),
                "cost_result": journal.get("economics"), "rr_result": paper.get("planned_rr"),
                "risk_result": risk, "portfolio_result": _mapping(risk.get("context")).get("cross_profile_arbiter"),
                "final_approval": paper.get("shadow_final_approval_candidate") or paper.get("persisted_final_approvals"),
                "paper_eligibility": paper.get("paper_status"), "terminal_stage": row.get("final_result"),
                "terminal_reason": row.get("final_reason"), "paper_raw": paper,
            },
            "diagnostics": {
                "pipeline_status": row.get("pipeline_status"), "error_code": row.get("error_code"),
                "future_bars_used": bool(row.get("future_bars_used")), "module_reasons": row.get("module_reasons"),
                "module_warnings": row.get("module_warnings"), "safety_counters": row.get("safety_counters"),
            },
            "outcome_followup": None,
        }
        observation["outcome_followup"] = _extract_followup(observation)
        return observation

    def _checkpoint(self, last_run_id: str | None) -> None:
        if last_run_id is not None:
            self.last_persisted_run_id = last_run_id
        self.store.write_checkpoint({
            "schema_revision": "scalping-calibration-checkpoint-v1",
            "collector_instance_id": self.instance_id,
            "observation_segment_id": self.config.identity.segment_id,
            "started_at": self.started_at,
            "last_seen_boundary": self.last_seen_boundary,
            "last_persisted_boundary": self.last_persisted_boundary,
            "last_persisted_run_id": self.last_persisted_run_id,
            "records_written": self.records_written,
            "persisted_boundaries": sorted(self.boundaries),
            "excluded_boundaries": sorted(self.excluded_boundaries),
            "homogeneity_identity": asdict(self.config.identity),
            "runtime_source_identity": self.config.runtime_source_commit,
            "runtime_artifact_identity": self.config.runtime_artifact_id,
            "parameter_set_id": self.config.parameter_set_id,
            "market_universe_id": self.config.identity.market_universe_id,
            "runtime_daemon_instance_id": self.runtime_daemon_instance_id,
            "runtime_lineage_transition_count": self.runtime_lineage_transition_count,
        })

    def _record_runtime_lineage_transition(
        self, boundary_ms: int, previous_daemon_id: str, daemon_id: str,
    ) -> None:
        transition_id = "runtime-lineage-" + sha256(
            f"{self.config.identity.segment_id}|{boundary_ms}|{previous_daemon_id}|{daemon_id}".encode("utf-8")
        ).hexdigest()[:24]
        if self.store.append("lineage", {
            "schema_revision": "scalping-runtime-lineage-transition-v1",
            "observation_id": transition_id,
            "observation_segment_id": self.config.identity.segment_id,
            "captured_at": iso_utc(),
            "boundary_time_ms": boundary_ms,
            "previous_runtime_daemon_instance_id": previous_daemon_id,
            "runtime_daemon_instance_id": daemon_id,
            "reason": "CLEAN_BOUNDARY_RUNTIME_OWNER_CHANGED",
            "mixed_lineage_within_boundary": False,
            "calibration_eligible": True,
        }):
            self.runtime_lineage_transition_count += 1

    def _preserve_mixed_lineage_incident(
        self, boundary_ms: int, rows: Sequence[Mapping[str, Any]], daemon_ids: set[str]
    ) -> str:
        members: list[dict[str, Any]] = []
        distribution: dict[str, int] = {}
        result_offsets: list[int] = []
        for row in rows:
            daemon_id = str(row.get("daemon_instance_id") or "UNKNOWN")
            distribution[daemon_id] = distribution.get(daemon_id, 0) + 1
            result_id = _integer(row.get("result_id"))
            if result_id is not None:
                result_offsets.append(result_id)
            member = {
                "symbol": str(row.get("symbol") or ""),
                "run_id": str(row.get("run_id") or ""),
                "result_id": result_id,
                "daemon_instance_id": daemon_id,
                "pipeline_status": row.get("pipeline_status"),
                "final_result": row.get("final_result"),
                "final_reason": row.get("final_reason"),
                "error_code": row.get("error_code"),
                "future_bars_used": bool(row.get("future_bars_used")),
            }
            member["record_reference_sha256"] = sha256(
                canonical_json(member).encode("utf-8")
            ).hexdigest()
            members.append(member)
        members.sort(key=lambda item: (item["symbol"], item["run_id"]))
        lineage_membership = {
            daemon_id: sorted(
                item["symbol"] for item in members
                if item["daemon_instance_id"] == daemon_id
            )
            for daemon_id in sorted(daemon_ids)
        }
        incident_id = "mixed-lineage-" + sha256(
            f"{self.config.identity.segment_id}|{boundary_ms}|{canonical_json(lineage_membership)}".encode("utf-8")
        ).hexdigest()[:24]
        incident = {
            "schema_revision": INCIDENT_SCHEMA_REVISION,
            "observation_id": incident_id,
            "incident_id": incident_id,
            "observation_segment_id": self.config.identity.segment_id,
            "collector_instance_id": self.instance_id,
            "captured_at": iso_utc(),
            "boundary_time_ms": int(boundary_ms),
            "boundary_start_ms": int(boundary_ms) - 300_000,
            "boundary_end_ms": int(boundary_ms),
            "closed_until_ms": int(boundary_ms),
            "profile_id": PROFILE_ID,
            "parameter_set_id": self.config.parameter_set_id,
            "expected_runtime_lineage": {
                "runtime_daemon_instance_id": self.runtime_daemon_instance_id,
                "runtime_source_commit": self.config.runtime_source_commit,
                "runtime_artifact_id": self.config.runtime_artifact_id,
                "schema_revision": self.config.schema_revision,
                "decision_semantics_version": self.config.identity.decision_semantics_version,
            },
            "distinct_runtime_lineage_count": len(daemon_ids),
            "runtime_lineage_distribution": distribution,
            "runtime_lineage_membership": lineage_membership,
            "record_count": len(members),
            "record_references": members,
            "source": {
                "type": "PRODUCTION_DATABASE_APPEND_ONLY_RUN_ROWS",
                "relation": "online_pipeline_runs+online_pipeline_results",
                "first_result_id_offset": min(result_offsets) if result_offsets else None,
                "last_result_id_offset": max(result_offsets) if result_offsets else None,
            },
            "exclusion": {
                "reason": "MIXED_RUNTIME_LINEAGE_WITHIN_BOUNDARY",
                "calibration_eligible": False,
                "outcome_followup_eligible": False,
                "raw_records_mutated": False,
            },
        }
        incident["record_set_sha256"] = sha256(
            canonical_json(members).encode("utf-8")
        ).hexdigest()
        self.store.register_exclusion(incident)
        self.excluded_boundaries.add(int(boundary_ms))
        self.last_seen_boundary = int(boundary_ms)
        self._checkpoint(None)
        return incident_id

    def process_boundary(self, boundary_ms: int) -> bool:
        rows = self.repository.load_boundary(boundary_ms)
        expected = set(self.config.symbols)
        present = {str(row["symbol"]) for row in rows if row.get("result_id") is not None}
        age_seconds = max(0, int(time.time() - boundary_ms / 1000))
        if present != expected and age_seconds < self.config.boundary_wait_seconds:
            return False
        daemon_ids = {str(row["daemon_instance_id"]) for row in rows if row.get("daemon_instance_id")}
        if len(daemon_ids) > 1:
            incident_id = self._preserve_mixed_lineage_incident(
                boundary_ms, rows, daemon_ids
            )
            raise MixedRuntimeLineageWithinBoundary(boundary_ms, incident_id)
        daemon_id = next(iter(daemon_ids), None)
        if self.runtime_daemon_instance_id is None:
            self.runtime_daemon_instance_id = daemon_id
        elif daemon_id and daemon_id != self.runtime_daemon_instance_id:
            self._record_runtime_lineage_transition(
                boundary_ms, self.runtime_daemon_instance_id, daemon_id,
            )
            self.runtime_daemon_instance_id = daemon_id
        last_run_id = None
        for row in rows:
            if row.get("result_id") is None:
                continue
            observation = self._observation(row)
            if self.store.append("observations", observation):
                self.records_written += 1
                followup = observation.get("outcome_followup")
                if followup:
                    self.pending[observation["observation_id"]] = dict(followup)
            self.micro_total += 1
            if observation["microstructure"]["microstructure_status"] == "AVAILABLE":
                self.micro_available += 1
            last_run_id = str(row["run_id"])
        missing = sorted(expected - present)
        row_symbols = [str(row["symbol"]) for row in rows if row.get("result_id") is not None]
        duplicates = sorted({symbol for symbol in row_symbols if row_symbols.count(symbol) > 1})
        errors = sorted({str(row["error_code"]) for row in rows if row.get("error_code")})
        diagnostic_id = "boundary-" + sha256(
            f"{self.config.identity.segment_id}|{boundary_ms}".encode("utf-8")
        ).hexdigest()
        if self.store.append("diagnostics", {
            "schema_revision": "scalping-calibration-boundary-diagnostic-v1",
            "observation_id": diagnostic_id,
            "observation_segment_id": self.config.identity.segment_id,
            "collector_instance_id": self.instance_id,
            "captured_at": iso_utc(), "boundary_time_ms": boundary_ms,
            "expected_symbols": list(self.config.symbols), "available_symbols": sorted(present),
            "expected_evaluations": len(expected), "actual_evaluations": len(row_symbols),
            "missing_symbols": missing, "duplicate_symbols": duplicates, "error_codes": errors,
            "bounded_wait_expired": bool(missing),
        }):
            self.boundary_diagnostics += 1
        self.missing_records += len(missing)
        self.duplicate_records += len(duplicates)
        self.errors_count += len(errors)
        self.last_seen_boundary = self.last_persisted_boundary = boundary_ms
        self.boundaries.add(boundary_ms)
        self._checkpoint(last_run_id)
        return True

    def process_outcomes(self, now_ms: int | None = None) -> int:
        current = now_ms if now_ms is not None else time.time_ns() // 1_000_000
        due = [item for item in self.pending.values()
               if int(item["followup_due_ms"]) + self.config.boundary_wait_seconds * 1000 <= current]
        if not due:
            return 0
        candles = self.repository.load_outcome_candles(due)
        written = 0
        for followup in due:
            symbol_rows = [row for row in candles.get(str(followup["symbol"]), [])
                           if int(followup["boundary_time_ms"]) <= int(row["open_time_ms"]) < int(followup["followup_due_ms"])]
            outcome = {
                "schema_revision": OUTCOME_SCHEMA_REVISION,
                "observation_id": followup["observation_id"],
                "observation_segment_id": self.config.identity.segment_id,
                "collector_instance_id": self.instance_id,
                "completed_at": iso_utc(),
                "frozen_opportunity": followup,
                **evaluate_outcome(followup, symbol_rows),
            }
            expected_opens = set(range(
                int(followup["boundary_time_ms"]), int(followup["followup_due_ms"]), 60_000
            ))
            actual_opens = {int(item["open_time_ms"]) for item in symbol_rows}
            outcome["path_diagnostics"] = {
                "expected_closed_candles": len(expected_opens),
                "actual_closed_candles": len(actual_opens),
                "missing_open_time_ms": sorted(expected_opens - actual_opens),
                "duplicate_open_time_ms": [],
            }
            if self.store.append("outcomes", outcome):
                written += 1
            self.pending.pop(str(followup["observation_id"]), None)
        return written

    def health(self, status: str = "RUNNING", last_error: str | None = None) -> dict[str, Any]:
        coverage = 100.0 * self.micro_available / self.micro_total if self.micro_total else 0.0
        completed_outcomes = self.store.completed_trade_outcomes()
        checkpoint_age = None
        if self.store.checkpoint_path.exists():
            checkpoint_age = max(0.0, time.time() - self.store.checkpoint_path.stat().st_mtime)
        value = {
            "schema_revision": "scalping-calibration-health-v1", "status": status,
            "collector_instance_id": self.instance_id,
            "observation_segment_id": self.config.identity.segment_id,
            "started_at": self.started_at, "generated_at": iso_utc(),
            "last_boundary": self.last_persisted_boundary, "records_written": self.records_written,
            "checkpoint_age_seconds": checkpoint_age, "owner_active": self.owner.active(),
            "collector_singleton_owner_count": self.owner.owner_count(),
            "parameter_set_id": self.config.parameter_set_id,
            "runtime_source_commit": self.config.runtime_source_commit,
            "runtime_artifact_id": self.config.runtime_artifact_id,
            "microstructure_coverage_percent": round(coverage, 6),
            "microstructure_future_leakage_count": 0,
            "pending_outcome_followups": len(self.pending), "completed_outcomes": completed_outcomes,
            "errors_count": self.errors_count, "missing_records": self.missing_records,
            "duplicate_records": self.duplicate_records, "db_query_count": getattr(self.repository, "query_count", None),
            "boundary_diagnostics_written": self.boundary_diagnostics,
            "runtime_lineage_transition_count": self.runtime_lineage_transition_count,
            "excluded_boundary_count": len(self.excluded_boundaries),
            "excluded_boundaries": sorted(self.excluded_boundaries),
            "gates": {
                "gate_24h": {"required_boundaries": 288, "observed_boundaries": len(self.boundaries), "reached": len(self.boundaries) >= 288},
                "gate_72h": {"required_boundaries": 864, "observed_boundaries": len(self.boundaries), "reached": len(self.boundaries) >= 864},
                "gate_min_trades": {"required_outcomes": 30, "completed_outcomes": completed_outcomes, "reached": completed_outcomes >= 30},
                "gate_strong_trades": {"required_outcomes": 100, "completed_outcomes": completed_outcomes, "reached": completed_outcomes >= 100},
            },
            "last_error": last_error,
            "safety": {"production_trading_mutations": 0, "binance_order_api_calls": 0, "parameter_promotions": 0},
        }
        atomic_write_json(self.store.health_path, value)
        return value

    def run(self, *, once: bool = False) -> int:
        if not self.owner.acquire():
            raise RuntimeError("CALIBRATION_COLLECTOR_ALREADY_RUNNING")
        signal.signal(signal.SIGTERM, self.request_stop)
        signal.signal(signal.SIGINT, self.request_stop)
        try:
            self.health()
            while not self.stop_requested:
                boundary = self.repository.next_boundary(self.last_seen_boundary)
                if boundary is not None:
                    self.last_seen_boundary = boundary
                    try:
                        self.process_boundary(boundary)
                    except MixedRuntimeLineageWithinBoundary:
                        self.health("RUNNING", "MIXED_RUNTIME_LINEAGE_WITHIN_BOUNDARY_EXCLUDED")
                        if once:
                            return 0
                        continue
                self.process_outcomes()
                self.health()
                if once:
                    return 0
                time.sleep(self.config.poll_seconds)
            self.health("STOPPING")
            return 0
        except Exception as exc:
            self.errors_count += 1
            self.health("FAILED", type(exc).__name__)
            raise
        finally:
            self.owner.release()
            self.health("STOPPED" if self.errors_count == 0 else "FAILED")


__all__ = [
    "AppendOnlyStore", "CollectorConfig", "HomogeneityIdentity", "PostgresCollectorOwner",
    "PostgresRepository", "ProspectiveCalibrationCollector", "MixedRuntimeLineageWithinBoundary", "evaluate_outcome",
    "market_universe_id", "normalize_microstructure",
]
