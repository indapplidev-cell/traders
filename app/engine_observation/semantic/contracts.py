from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any


PRIMARY_STEP_MS = 900_000
SUPPORTED_TIMEFRAMES = ("1m", "5m", "15m", "1h", "4h", "1d")


class WindowState(StrEnum):
    NOT_DUE = "NOT_DUE"
    DUE_WAITING_FOR_RUN = "DUE_WAITING_FOR_RUN"
    RUN_WAITING_RETRYABLE = "RUN_WAITING_RETRYABLE"
    RUN_COMPLETED = "RUN_COMPLETED"
    RUN_SKIPPED = "RUN_SKIPPED"
    RUN_FAILED = "RUN_FAILED"
    RUN_STUCK = "RUN_STUCK"
    RUN_DUPLICATE = "RUN_DUPLICATE"
    RUN_RESULT_CARDINALITY_ERROR = "RUN_RESULT_CARDINALITY_ERROR"


class IncidentState(StrEnum):
    OPEN = "OPEN"
    UPDATED = "UPDATED"
    RESOLVED = "RESOLVED"


class Severity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AcceptanceImpact(StrEnum):
    NONE = "NONE"
    REVIEW = "REVIEW"
    BLOCKING = "BLOCKING"


@dataclass(frozen=True, slots=True)
class SemanticContract:
    soak_id: str
    soak_directory: Path
    symbols: tuple[str, ...]
    primary_timeframe: str
    anchor_closed_until_ms: int
    anchor_excluded: bool
    first_measured_boundary_ms: int
    last_measured_boundary_ms: int
    settlement_end_ms: int
    expected_boundaries_per_symbol: int
    expected_total_windows: int
    freshness_deadline_policy: str
    missing_run_grace_seconds: int
    required_timeframes: tuple[str, ...]
    strict_freshness_mode: bool
    higher_timeframe_policy: str
    sample_interval_seconds: float
    semantic_lookback_windows: int
    runtime_freshness_grace_seconds: int

    def __post_init__(self) -> None:
        if not self.soak_id or not self.symbols:
            raise ValueError("soak_id and symbols are required")
        if self.primary_timeframe != "15m":
            raise ValueError("semantic observer currently requires primary_timeframe=15m")
        if not self.anchor_excluded:
            raise ValueError("anchor_excluded must be true")
        if self.first_measured_boundary_ms != self.anchor_closed_until_ms + PRIMARY_STEP_MS:
            raise ValueError("first measured boundary must be anchor + 15m")
        if self.last_measured_boundary_ms < self.first_measured_boundary_ms:
            raise ValueError("invalid measured interval")
        boundaries = ((self.last_measured_boundary_ms - self.anchor_closed_until_ms) // PRIMARY_STEP_MS)
        if boundaries != self.expected_boundaries_per_symbol:
            raise ValueError("expected boundaries do not match measured interval")
        if self.expected_total_windows != boundaries * len(self.symbols):
            raise ValueError("expected total windows does not match symbols x boundaries")
        if self.settlement_end_ms < self.last_measured_boundary_ms:
            raise ValueError("settlement must not end before measurement")
        if set(self.required_timeframes) - set(SUPPORTED_TIMEFRAMES):
            raise ValueError("unsupported required timeframe")
        if self.primary_timeframe not in self.required_timeframes:
            raise ValueError("primary timeframe must be required")
        if self.missing_run_grace_seconds < 0 or self.runtime_freshness_grace_seconds <= 0:
            raise ValueError("invalid grace")
        if self.sample_interval_seconds <= 0 or self.semantic_lookback_windows <= 0:
            raise ValueError("invalid sampling/lookback configuration")
        if self.freshness_deadline_policy != "PERSISTED_OR_RUNTIME_GRACE":
            raise ValueError("deadline policy must explicitly match deployed runtime")

    @property
    def contract_hash(self) -> str:
        value = asdict(self)
        value["soak_directory"] = str(self.soak_directory.resolve())
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


def _parse_bool(value: str) -> bool:
    normalized = value.strip().upper()
    if normalized in {"YES", "TRUE", "1", "ENABLED", "STRICT"}:
        return True
    if normalized in {"NO", "FALSE", "0", "DISABLED", "NON_STRICT"}:
        return False
    raise ValueError(f"invalid boolean: {value}")


def _utc_ms(value: str) -> int:
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("UTC timestamp must be timezone-aware")
    return int(parsed.astimezone(timezone.utc).timestamp() * 1000)


def _read_mapping(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".json":
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("semantic contract JSON must be an object")
        return {str(k).upper(): v for k, v in value.items()}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*([A-Z][A-Z0-9_]*)\s*=\s*(.*?)\s*$", raw)
        if match:
            values[match.group(1)] = match.group(2)
    return values


def load_semantic_contract(path: Path) -> SemanticContract:
    values = _read_mapping(path)
    required = {
        "SOAK_ID", "SOAK_DIRECTORY", "SYMBOLS", "PRIMARY_TIMEFRAME", "ANCHOR_CLOSED_UNTIL_MS",
        "ANCHOR_EXCLUDED", "FIRST_MEASURED_BOUNDARY_MS", "LAST_MEASURED_BOUNDARY_MS",
        "EXPECTED_BOUNDARIES_PER_SYMBOL", "EXPECTED_TOTAL_WINDOWS", "FRESHNESS_DEADLINE_POLICY",
        "MISSING_RUN_GRACE_SECONDS", "REQUIRED_TIMEFRAMES", "STRICT_FRESHNESS_MODE",
        "HIGHER_TIMEFRAME_POLICY", "SEMANTIC_LOOKBACK_WINDOWS", "FRESHNESS_GRACE_SECONDS",
    }
    missing = sorted(required - values.keys())
    if missing:
        raise ValueError(f"semantic contract missing fields: {', '.join(missing)}")
    settlement_ms = int(values.get("SETTLEMENT_END_MS") or _utc_ms(str(values["SETTLEMENT_END_UTC"])))
    symbols = tuple(dict.fromkeys(item.strip().upper() for item in str(values["SYMBOLS"]).split(",") if item.strip()))
    timeframes = tuple(dict.fromkeys(item.strip() for item in str(values["REQUIRED_TIMEFRAMES"]).split(",") if item.strip()))
    return SemanticContract(
        soak_id=str(values["SOAK_ID"]), soak_directory=Path(str(values["SOAK_DIRECTORY"])), symbols=symbols,
        primary_timeframe=str(values["PRIMARY_TIMEFRAME"]), anchor_closed_until_ms=int(values["ANCHOR_CLOSED_UNTIL_MS"]),
        anchor_excluded=_parse_bool(str(values["ANCHOR_EXCLUDED"])), first_measured_boundary_ms=int(values["FIRST_MEASURED_BOUNDARY_MS"]),
        last_measured_boundary_ms=int(values["LAST_MEASURED_BOUNDARY_MS"]), settlement_end_ms=settlement_ms,
        expected_boundaries_per_symbol=int(values["EXPECTED_BOUNDARIES_PER_SYMBOL"]), expected_total_windows=int(values["EXPECTED_TOTAL_WINDOWS"]),
        freshness_deadline_policy=str(values["FRESHNESS_DEADLINE_POLICY"]), missing_run_grace_seconds=int(values["MISSING_RUN_GRACE_SECONDS"]),
        required_timeframes=timeframes, strict_freshness_mode=_parse_bool(str(values["STRICT_FRESHNESS_MODE"])),
        higher_timeframe_policy=str(values["HIGHER_TIMEFRAME_POLICY"]),
        sample_interval_seconds=float(values.get("SEMANTIC_SAMPLE_INTERVAL_SECONDS", values.get("OBSERVER_SAMPLE_INTERVAL_SECONDS", 60))),
        semantic_lookback_windows=int(values["SEMANTIC_LOOKBACK_WINDOWS"]), runtime_freshness_grace_seconds=int(values["FRESHNESS_GRACE_SECONDS"]),
    )
