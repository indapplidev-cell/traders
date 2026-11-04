"""Research-only causal feature cache and explicit execution cost accounting.

The cache is deliberately independent of the v2 opportunity list. Every usable
closed 5m boundary is evaluated with the native pipeline, including boundaries
that the active configuration rejects before setup or geometry.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from bisect import bisect_left
from dataclasses import replace
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator
from sqlalchemy import text

from app.config.trade_parameters import (
    ResolvedParameterSet,
    ScalpingV2Parameters,
    frozen_parameter_hash,
    load_trade_parameters,
)
from app.engine_orchestrator.orchestrator_config import OrchestratorConfig
from app.engine_orchestrator.pipeline_result import json_safe
from app.engine_orchestrator.pipeline_runner import PipelineRunner
from app.engine_paper.scalping_paper_runner import ScalpingPaperRunner

from .engine import ReadOnlyResearchDatabase, resolve_database_binding
from .full_pipeline import (
    Contract,
    FullPipelineCalibrationRequestV2,
    RaggedDatasetManifestV2,
    fingerprint,
)
from .full_pipeline_ragged import (
    INTERVAL_MS,
    HistoricalConservativeCostSource,
    HistoricalCostModelV1,
)
from .historical_reconstruction import CausalCandleRepository, _load_candles


class CausalBoundaryFeaturesV3(Contract):
    version: Literal["causal-boundary-features/3"] = "causal-boundary-features/3"
    symbol: str
    segment_start_ms: int
    boundary_ms: int
    dataset_hash: str
    analysis_parameter_hash: str
    candle_refs: dict[str, dict[str, Any]]
    market_data: dict[str, Any]
    analysis: dict[str, Any]
    setup: dict[str, Any]
    strategy: dict[str, Any]
    risk: dict[str, Any]
    paper: dict[str, Any]
    statuses: dict[str, Any]
    first_rejection: str | None = None
    feature_completeness: dict[str, bool]
    decision_hash: str

    @model_validator(mode="after")
    def closed_inputs(self) -> CausalBoundaryFeaturesV3:
        if any(int(ref["close_time_ms"]) >= self.boundary_ms for ref in self.candle_refs.values()):
            raise ValueError("FUTURE_CANDLE_IN_FEATURE_CACHE")
        return self


class FeatureCacheManifestV3(Contract):
    version: Literal["feature-cache-manifest/3"] = "feature-cache-manifest/3"
    dataset_hash: str
    request_hash: str
    code_hash: str
    configuration_hash: str
    status: Literal["IN_PROGRESS", "COMPLETE"]
    completed_boundaries: int = Field(ge=0)
    expected_boundaries: int = Field(ge=0)
    partitions: list[dict[str, Any]]
    holdout_evaluated: Literal[False] = False


class HistoricalCostLedgerV3(Contract):
    version: Literal["historical-cost-ledger/3"] = "historical-cost-ledger/3"
    boundary_ms: int = Field(ge=0)
    provenance: Literal["OBSERVED", "MODELLED_CONSERVATIVE"]
    evidence_ms: int | None = None
    notional: float = Field(gt=0)
    gross_pnl: float
    entry_fee: float = Field(ge=0)
    exit_fee: float = Field(ge=0)
    spread: float = Field(ge=0)
    entry_slippage: float = Field(ge=0)
    exit_slippage: float = Field(ge=0)
    depth_impact: float = Field(ge=0)
    reserve: float = Field(ge=0)
    net_pnl: float

    @model_validator(mode="after")
    def reconcile(self) -> HistoricalCostLedgerV3:
        if self.evidence_ms is not None and self.evidence_ms > self.boundary_ms:
            raise ValueError("FUTURE_COST_EVIDENCE")
        if abs(self.gross_pnl - sum((self.entry_fee, self.exit_fee, self.spread,
                self.entry_slippage, self.exit_slippage, self.depth_impact,
                self.reserve)) - self.net_pnl) > 1e-8:
            raise ValueError("COST_LEDGER_DOES_NOT_RECONCILE")
        return self

    @classmethod
    def from_bps(cls, *, boundary_ms: int, provenance: str, evidence_ms: int | None,
                 notional: float, gross_pnl: float, entry_fee_bps: float,
                 exit_fee_bps: float, spread_bps: float, entry_slippage_bps: float,
                 exit_slippage_bps: float, depth_impact_bps: float,
                 reserve_bps: float) -> HistoricalCostLedgerV3:
        components = {
            "entry_fee": notional * entry_fee_bps / 10_000,
            "exit_fee": notional * exit_fee_bps / 10_000,
            "spread": notional * spread_bps / 10_000,
            "entry_slippage": notional * entry_slippage_bps / 10_000,
            "exit_slippage": notional * exit_slippage_bps / 10_000,
            "depth_impact": notional * depth_impact_bps / 10_000,
            "reserve": notional * reserve_bps / 10_000,
        }
        return cls(boundary_ms=boundary_ms, provenance=provenance,
                   evidence_ms=evidence_ms, notional=notional, gross_pnl=gross_pnl,
                   net_pnl=gross_pnl-sum(components.values()), **components)


# Only paths consumed by native pipeline components belong here. Execution
# costs are intentionally absent: they are observed/modelled data, not knobs.
NATIVE_PARAMETER_PATHS_V3: dict[str, str] = {
    "strategy_minimum_score": "signal.strategy_minimum_score",
    "atr_multiplier": "geometry.atr_multiplier",
    "stop_max_bps": "geometry.stop_max_bps",
    "target_min_bps": "geometry.target_min_bps",
    "minimum_planned_rr": "geometry.minimum_planned_rr",
    "min_net_edge_bps": "economics.min_net_edge_bps",
    "min_positive_ev_r": "economics.min_positive_ev_r",
    "min_ev_reserve_r": "economics.min_ev_reserve_r",
    "bucket_min_sample": "economics.bucket_min_sample",
    "risk_per_trade_bps": "risk.risk_per_trade_bps",
    "max_open_positions": "risk.max_open_positions",
    "total_open_risk_limit_bps": "risk.total_open_risk_limit_bps",
    "max_new_commands_per_cycle": "risk.max_new_commands_per_cycle",
    "regime_lookback_candles": "signal.regime_lookback_candles",
    "entry_refinement_1m_confirmation_count": "signal.confirmation_window_candles",
    "soft_timeout_seconds": "exit_policy.stale_position.soft_timeout_seconds",
    "hard_timeout_seconds": "exit_policy.stale_position.hard_timeout_seconds",
    "extension_seconds": "exit_policy.stale_position.extension_seconds",
    "max_extensions": "exit_policy.stale_position.max_extensions",
}


def resolve_research_parameter_set_v3(
    baseline: ResolvedParameterSet, changes: dict[str, Any],
) -> ResolvedParameterSet:
    """Build an isolated, validated native parameter snapshot for one trial."""
    unknown = set(changes) - set(NATIVE_PARAMETER_PATHS_V3)
    if unknown:
        raise ValueError(f"UNSUPPORTED_NATIVE_PARAMETER: {sorted(unknown)}")
    values = baseline.parameters.model_dump(mode="python")
    for name, value in changes.items():
        path = NATIVE_PARAMETER_PATHS_V3[name].split(".")
        target = values
        for part in path[:-1]:
            target = target[part]
        target[path[-1]] = value
    parameters = ScalpingV2Parameters.model_validate(values)
    if (parameters.costs != baseline.parameters.costs or
            parameters.risk.risk_per_trade_bps > baseline.parameters.risk.risk_per_trade_bps or
            parameters.risk.max_open_positions > baseline.parameters.risk.max_open_positions):
        raise ValueError("RESEARCH_SAFETY_OR_COST_CAP_VIOLATION")
    identity = frozen_parameter_hash(parameters, baseline.resolved_config_hash)
    return replace(baseline, id=f"research-v3-{identity[:12]}",
                   label="Research-only v3 candidate", version="research-v3",
                   parameters=parameters, resolved_config_hash=identity,
                   provenance={**baseline.provenance,
                               **{NATIVE_PARAMETER_PATHS_V3[name]: "RESEARCH_ONLY"
                                  for name in changes}})


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, sort_keys=True, indent=2, default=str) + "\n", encoding="utf-8")
    temporary.replace(path)


def _truncate_after_checkpoint(path: Path, boundary_ms: int) -> None:
    if not path.exists():
        raise ValueError("FEATURE_CACHE_CHECKPOINT_WITHOUT_PARTITION")
    retained = []
    with path.open(encoding="utf-8") as source:
        for line in source:
            if not line.endswith("\n"):
                break
            row = json.loads(line)
            if int(row["boundary_ms"]) <= boundary_ms:
                retained.append(line)
    with path.open("w", encoding="utf-8") as destination:
        destination.writelines(retained)


def _first_rejection(payload: dict[str, Any]) -> str | None:
    for stage in ("analysis", "setup", "strategy", "risk", "paper"):
        data = payload.get(stage) or {}
        for name in ("invalidation_reasons", "rejection_reasons"):
            reasons = data.get(name) or []
            if reasons:
                return str(reasons[0])
    return payload.get("final_reason")


def _write_candles_once(path: Path, candles: dict[str, list[Any]], *,
                        dataset_hash: str, allowed_end: int) -> str:
    """Materialize the actual pre-holdout inputs independently of decisions."""
    receipt = path.with_name("CANDLES.json")
    if receipt.exists():
        saved = json.loads(receipt.read_text(encoding="utf-8"))
        if saved["dataset_hash"] != dataset_hash or saved["allowed_end_ms"] != allowed_end:
            raise ValueError("FROZEN_CANDLE_PARTITION_IDENTITY_CHANGED")
        if saved["sha256"] != _sha256(path):
            raise ValueError("FROZEN_CANDLE_PARTITION_CORRUPT")
        return saved["sha256"]
    if path.exists():
        raise ValueError("UNVERIFIED_FROZEN_CANDLE_PARTITION")
    with path.open("w", encoding="utf-8") as handle:
        for timeframe, values in candles.items():
            for candle in values:
                if candle.close_time_ms >= allowed_end:
                    raise ValueError("HOLDOUT_CANDLE_IN_PREHOLDOUT_PARTITION")
                handle.write(json.dumps({
                    "timeframe": timeframe, "open_time_ms": candle.open_time_ms,
                    "close_time_ms": candle.close_time_ms,
                    "open": str(candle.open), "high": str(candle.high),
                    "low": str(candle.low), "close": str(candle.close),
                    "volume": str(candle.volume), "quote_volume": str(candle.quote_volume),
                    "trades_count": candle.trades_count,
                    "checksum": fingerprint(candle.market_values()),
                }, sort_keys=True) + "\n")
    digest = _sha256(path)
    _write_json(receipt, {"dataset_hash": dataset_hash,
                          "allowed_end_ms": allowed_end, "sha256": digest,
                          "rows": {key: len(value) for key, value in candles.items()}})
    return digest


def build_feature_cache_v3(request_path: Path, dataset: Path, output: Path,
                           database_url: str | None = None,
                           *, max_boundaries: int | None = None) -> FeatureCacheManifestV3:
    """Build a resumable native-pipeline cache; limit is for smoke tests only."""
    request = FullPipelineCalibrationRequestV2.model_validate_json(request_path.read_text(encoding="utf-8"))
    manifest = RaggedDatasetManifestV2.model_validate_json((dataset / "DATASET_MANIFEST.json").read_text(encoding="utf-8"))
    if manifest.status != "FROZEN" or manifest.request_hash != request.identity:
        raise ValueError("FEATURE_CACHE_FROZEN_REQUEST_MISMATCH")
    if shutil.disk_usage(output.parent).free < 5 * (1 << 30):
        raise ValueError("FEATURE_CACHE_DISK_RESERVE_BELOW_5GB")
    cost_model = HistoricalCostModelV1.model_validate_json((dataset / "HISTORICAL_COST_MODEL.json").read_text(encoding="utf-8"))
    holdout = next(window for window in request.windows if window.role == "INTERNAL_HOLDOUT")
    resolved = load_trade_parameters().resolve_scalping_v2_parameter_set()
    config_hash = resolved.resolved_config_hash
    code_hash = fingerprint({"module": _sha256(Path(__file__)),
                             "runner": _sha256(Path(PipelineRunner.__module__.replace(".", "/") + ".py"))
                             if Path(PipelineRunner.__module__.replace(".", "/") + ".py").exists() else "unknown"})
    output.mkdir(parents=True, exist_ok=True)
    db = ReadOnlyResearchDatabase(resolve_database_binding(explicit_url=database_url))
    partitions: list[dict[str, Any]] = []
    processed = 0
    try:
        for coverage in manifest.symbols:
            if coverage.status == "UNUSABLE":
                continue
            for segment in coverage.segments:
                root = output / "symbols" / coverage.symbol / str(segment.start_ms)
                data_file = root / "FEATURES.jsonl"
                checkpoint_file = root / "CHECKPOINT.json"
                done_file = root / "DONE.json"
                if done_file.exists():
                    done = json.loads(done_file.read_text(encoding="utf-8"))
                    if done["dataset_hash"] != manifest.dataset_hash or done["configuration_hash"] != config_hash:
                        raise ValueError("FEATURE_CACHE_IDENTITY_CHANGED")
                    if done["sha256"] != _sha256(data_file):
                        raise ValueError("FEATURE_CACHE_PARTITION_CORRUPT")
                    partitions.append(done)
                    processed += int(done["boundaries"])
                    continue
                root.mkdir(parents=True, exist_ok=True)
                checkpoint = json.loads(checkpoint_file.read_text(encoding="utf-8")) if checkpoint_file.exists() else None
                if checkpoint:
                    if checkpoint["dataset_hash"] != manifest.dataset_hash or checkpoint["configuration_hash"] != config_hash:
                        raise ValueError("FEATURE_CACHE_CHECKPOINT_IDENTITY_CHANGED")
                    _truncate_after_checkpoint(data_file, int(checkpoint["last_boundary_ms"]))
                last = int(checkpoint["last_boundary_ms"]) if checkpoint else -1
                count = int(checkpoint["boundaries"]) if checkpoint else 0
                warmup = max(INTERVAL_MS[key] * value for key, value in request.warmup_bars.items())
                allowed_end = min(segment.end_ms, holdout.start_ms)
                if segment.start_ms >= allowed_end:
                    continue
                with db.connection() as connection:
                    connection.execute(text("SET LOCAL statement_timeout = '10min'"))
                    candles = _load_candles(connection, coverage.symbol,
                                            max(request.data_start_ms, segment.start_ms-warmup),
                                            allowed_end - 1)
                candle_hash = _write_candles_once(root / "CANDLES.jsonl", candles,
                                                  dataset_hash=manifest.dataset_hash,
                                                  allowed_end=allowed_end)
                repo = CausalCandleRepository(coverage.symbol, candles)
                cost_source = HistoricalConservativeCostSource(cost_model)
                config = OrchestratorConfig(symbols=(coverage.symbol,), trade_profile_id="trade-5m-v2",
                                            primary_timeframe="5m")
                paper = ScalpingPaperRunner(runtime_parameters=config.runtime_parameters,
                                            cost_source=cost_source,
                                            clock_ms=lambda source=cost_source: source.boundary_ms)
                runner = PipelineRunner(config, repo, paper_runner=paper, resolved_parameter_set=resolved)
                opens = {tf: [item.close_time_ms for item in values] for tf, values in candles.items()}
                expected = [item.close_time_ms + 1 for item in candles["5m"]
                            if segment.start_ms <= item.close_time_ms+1 < allowed_end]
                with data_file.open("a" if checkpoint else "w", encoding="utf-8") as destination:
                    for boundary in expected:
                        if boundary <= last:
                            continue
                        cost_source.boundary_ms = boundary
                        result = json_safe(runner.run(coverage.symbol, boundary))
                        if result.get("safety_counters", {}).get("future_bars_used_count", 0):
                            raise ValueError("FEATURE_CACHE_FUTURE_BAR_READ")
                        if repo.maximum_close_read_ms is not None and repo.maximum_close_read_ms >= boundary:
                            raise ValueError("FEATURE_CACHE_FUTURE_CANDLE_READ")
                        refs = {}
                        for tf, values in candles.items():
                            index = bisect_left(opens[tf], boundary)-1
                            if index >= 0:
                                candle = values[index]
                                refs[tf] = {"open_time_ms": candle.open_time_ms,
                                            "close_time_ms": candle.close_time_ms,
                                            "checksum": fingerprint(candle.market_values())}
                        payload = {stage: dict(result.get(stage + "_payload") or {})
                                   for stage in ("market_data", "analysis", "setup", "strategy", "risk", "paper")}
                        payload["final_reason"] = result.get("final_reason")
                        statuses = {name: result.get(name) for name in
                                    ("analysis_status", "setup_status", "strategy_status", "risk_status", "paper_status")}
                        completeness = {stage: bool(payload[stage]) for stage in
                                        ("market_data", "analysis", "setup", "strategy", "risk", "paper")}
                        row = CausalBoundaryFeaturesV3(
                            symbol=coverage.symbol, segment_start_ms=segment.start_ms,
                            boundary_ms=boundary, dataset_hash=manifest.dataset_hash,
                            analysis_parameter_hash=config_hash, candle_refs=refs,
                            statuses=statuses, first_rejection=_first_rejection(payload),
                            feature_completeness=completeness,
                            decision_hash=fingerprint({"payload": payload, "statuses": statuses}), **{
                                name: payload[name] for name in
                                ("market_data", "analysis", "setup", "strategy", "risk", "paper")
                            })
                        destination.write(row.model_dump_json() + "\n")
                        count += 1
                        if count % 100 == 0:
                            destination.flush()
                            _write_json(checkpoint_file, {"last_boundary_ms": boundary,
                                "boundaries": count, "dataset_hash": manifest.dataset_hash,
                                "configuration_hash": config_hash})
                        if max_boundaries is not None and processed + count >= max_boundaries:
                            destination.flush()
                            _write_json(checkpoint_file, {"last_boundary_ms": boundary,
                                "boundaries": count, "dataset_hash": manifest.dataset_hash,
                                "configuration_hash": config_hash})
                            return FeatureCacheManifestV3(dataset_hash=manifest.dataset_hash,
                                request_hash=request.identity, code_hash=code_hash,
                                configuration_hash=config_hash, status="IN_PROGRESS",
                                completed_boundaries=processed+count,
                                expected_boundaries=sum(s.rows_5m for c in manifest.symbols for s in c.segments),
                                partitions=partitions)
                if count != len(expected):
                    raise ValueError("FEATURE_CACHE_BOUNDARY_COUNT_MISMATCH")
                done = {"symbol": coverage.symbol, "segment_start_ms": segment.start_ms,
                        "boundaries": count, "dataset_hash": manifest.dataset_hash,
                        "configuration_hash": config_hash, "sha256": _sha256(data_file),
                        "candle_sha256": candle_hash}
                _write_json(done_file, done)
                partitions.append(done)
                processed += count
                _write_json(output / "FEATURE_CACHE_MANIFEST.json", FeatureCacheManifestV3(
                    dataset_hash=manifest.dataset_hash, request_hash=request.identity,
                    code_hash=code_hash, configuration_hash=config_hash,
                    status="IN_PROGRESS", completed_boundaries=processed,
                    expected_boundaries=sum(s.rows_5m for c in manifest.symbols for s in c.segments),
                    partitions=partitions).model_dump(mode="json"))
    finally:
        db.dispose()
    result = FeatureCacheManifestV3(dataset_hash=manifest.dataset_hash,
        request_hash=request.identity, code_hash=code_hash, configuration_hash=config_hash,
        status="IN_PROGRESS", completed_boundaries=processed,
        expected_boundaries=sum(s.rows_5m for c in manifest.symbols for s in c.segments),
        partitions=partitions)
    # Holdout is deliberately absent until finalists are frozen. The cache is
    # therefore never marked complete merely because all pre-holdout rows ran.
    _write_json(output / "FEATURE_CACHE_MANIFEST.json", result.model_dump(mode="json"))
    return result
