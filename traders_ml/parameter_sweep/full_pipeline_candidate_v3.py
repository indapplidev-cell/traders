"""Recompute native stage decisions for a frozen v3 cache partition.

This produces candidate-specific causal decisions. Portfolio execution and
economic acceptance remain separate gates; this module cannot declare a
candidate eligible or read the locked holdout.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from app.config.trade_parameters import load_trade_parameters
from app.engine_market_data.candle import Candle
from app.engine_orchestrator.orchestrator_config import OrchestratorConfig
from app.engine_orchestrator.pipeline_result import json_safe
from app.engine_orchestrator.pipeline_runner import PipelineRunner
from app.engine_paper.scalping_paper_runner import ScalpingPaperRunner

from .full_pipeline import (
    FullPipelineCalibrationRequestV2,
    RaggedDatasetManifestV2,
    fingerprint,
)
from .full_pipeline_ragged import (
    HistoricalConservativeCostSource,
    HistoricalCostModelV1,
    _closed_boundary_count,
)
from .full_pipeline_v3 import (
    CausalBoundaryFeaturesV3,
    _compact_stage_payloads,
    _first_rejection,
    _sha256,
    _write_json,
    resolve_research_parameter_set_v3,
)
from .historical_reconstruction import CausalCandleRepository


def _frozen_candles(partition: Path, dataset_hash: str) -> dict[str, list[Candle]]:
    source = partition / "CANDLES.jsonl"
    receipt = json.loads((partition / "CANDLES.json").read_text(encoding="utf-8"))
    if receipt["dataset_hash"] != dataset_hash or _sha256(source) != receipt["sha256"]:
        raise ValueError("CANDIDATE_FROZEN_CANDLES_CORRUPT")
    values: dict[str, list[Candle]] = {tf: [] for tf in ("1m", "5m", "15m", "1h")}
    symbol = partition.parent.name
    with source.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            timeframe = row["timeframe"]
            if timeframe not in values or int(row["close_time_ms"]) >= int(receipt["allowed_end_ms"]):
                raise ValueError("CANDIDATE_FROZEN_CANDLE_OUTSIDE_ROLE")
            candle = Candle(symbol=symbol, timeframe=timeframe,
                            open_time_ms=int(row["open_time_ms"]),
                            close_time_ms=int(row["close_time_ms"]),
                            open=row["open"], high=row["high"], low=row["low"],
                            close=row["close"], volume=row["volume"],
                            quote_volume=row["quote_volume"],
                            trades_count=row["trades_count"], is_closed=True,
                            source="v3-frozen-research")
            if fingerprint(candle.market_values()) != row["checksum"]:
                raise ValueError("CANDIDATE_CANDLE_CHECKSUM_MISMATCH")
            values[timeframe].append(candle)
    return values


def native_candidate_decisions_v3(
    request_path: Path, dataset: Path, cache: Path, partition: Path,
    changes: dict[str, Any], *, maximum: int | None = None,
) -> Iterator[CausalBoundaryFeaturesV3]:
    """Yield a fresh native decision for each certified pre-holdout boundary."""
    request = FullPipelineCalibrationRequestV2.model_validate_json(request_path.read_text(encoding="utf-8"))
    manifest = RaggedDatasetManifestV2.model_validate_json((dataset / "DATASET_MANIFEST.json").read_text(encoding="utf-8"))
    if manifest.status != "FROZEN" or manifest.request_hash != request.identity:
        raise ValueError("CANDIDATE_REQUEST_DATASET_MISMATCH")
    root = cache / "symbols" / partition.parent.name / partition.name
    if root.resolve() != partition.resolve():
        raise ValueError("CANDIDATE_PARTITION_OUTSIDE_CACHE")
    done_path = partition / "DONE.json"
    if not done_path.exists():
        raise ValueError("CANDIDATE_REQUIRES_COMPLETE_PARTITION")
    done = json.loads(done_path.read_text(encoding="utf-8"))
    feature_path = partition / "FEATURES.jsonl"
    if done["dataset_hash"] != manifest.dataset_hash or _sha256(feature_path) != done["sha256"]:
        raise ValueError("CANDIDATE_FEATURE_PARTITION_CORRUPT")
    baseline = load_trade_parameters().resolve_scalping_v2_parameter_set()
    if done["configuration_hash"] != baseline.resolved_config_hash:
        raise ValueError("CANDIDATE_BASELINE_CONFIGURATION_CHANGED")
    candles = _frozen_candles(partition, manifest.dataset_hash)
    repository = CausalCandleRepository(partition.parent.name, candles)
    resolved = resolve_research_parameter_set_v3(baseline, changes)
    cost_path = cache / "PREVALIDATION_COST_MODEL.json"
    cost_receipt = cost_path.with_suffix(".receipt.json")
    if not cost_path.exists() or not cost_receipt.exists():
        raise ValueError("CANDIDATE_PREVALIDATION_COST_MODEL_REQUIRED")
    receipt = json.loads(cost_receipt.read_text(encoding="utf-8"))
    final_validation = max(window.start_ms for window in request.windows
                           if window.role == "VALIDATION")
    if (receipt.get("dataset_hash") != manifest.dataset_hash
            or receipt.get("request_hash") != request.identity
            or receipt.get("cutoff_ms") != final_validation
            or receipt.get("sha256") != _sha256(cost_path)):
        raise ValueError("CANDIDATE_PREVALIDATION_COST_MODEL_INVALID")
    cost_model = HistoricalCostModelV1.model_validate_json(
        cost_path.read_text(encoding="utf-8"))
    cost_source = HistoricalConservativeCostSource(cost_model)
    config = OrchestratorConfig(symbols=(partition.parent.name,),
                                trade_profile_id="trade-5m-v2", primary_timeframe="5m")
    paper = ScalpingPaperRunner(runtime_parameters=config.runtime_parameters,
                                 cost_source=cost_source,
                                 clock_ms=lambda source=cost_source: source.boundary_ms)
    runner = PipelineRunner(config, repository, paper_runner=paper,
                            resolved_parameter_set=resolved)
    holdout = next(window for window in request.windows if window.role == "INTERNAL_HOLDOUT")
    with feature_path.open(encoding="utf-8") as handle:
        for count, line in enumerate(handle):
            original = CausalBoundaryFeaturesV3.model_validate_json(line)
            if original.boundary_ms >= holdout.start_ms:
                raise ValueError("CANDIDATE_HOLDOUT_READ")
            cost_source.boundary_ms = original.boundary_ms
            result = json_safe(runner.run(original.symbol, original.boundary_ms))
            if result.get("safety_counters", {}).get("future_bars_used_count", 0):
                raise ValueError("CANDIDATE_FUTURE_BAR_READ")
            if (repository.maximum_close_read_ms is not None and
                    repository.maximum_close_read_ms >= original.boundary_ms):
                raise ValueError("CANDIDATE_FUTURE_CANDLE_READ")
            payload = _compact_stage_payloads({
                stage: dict(result.get(stage + "_payload") or {})
                for stage in ("market_data", "analysis", "setup", "strategy", "risk", "paper")
            })
            payload["final_reason"] = result.get("final_reason")
            statuses = {name: result.get(name) for name in
                        ("analysis_status", "setup_status", "strategy_status", "risk_status", "paper_status")}
            yield CausalBoundaryFeaturesV3(
                symbol=original.symbol, segment_start_ms=original.segment_start_ms,
                boundary_ms=original.boundary_ms, dataset_hash=manifest.dataset_hash,
                analysis_parameter_hash=resolved.resolved_config_hash,
                candle_refs=original.candle_refs, statuses=statuses,
                first_rejection=_first_rejection(payload),
                feature_completeness={stage: bool(payload[stage]) for stage in
                                      ("market_data", "analysis", "setup", "strategy", "risk", "paper")},
                decision_hash=fingerprint({"payload": payload, "statuses": statuses}),
                **{stage: payload[stage] for stage in
                   ("market_data", "analysis", "setup", "strategy", "risk", "paper")},
            )
            if maximum is not None and count + 1 >= maximum:
                break


def write_native_candidate_partition_v3(
    request_path: Path, dataset: Path, cache: Path, partition: Path,
    changes: dict[str, Any], output: Path,
) -> dict[str, Any]:
    """Materialize and hash one candidate partition without reading holdout."""
    if output.exists():
        raise ValueError("CANDIDATE_OUTPUT_ALREADY_EXISTS")
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    configuration_hash = None
    with output.open("w", encoding="utf-8") as handle:
        for decision in native_candidate_decisions_v3(
                request_path, dataset, cache, partition, changes):
            handle.write(decision.model_dump_json() + "\n")
            configuration_hash = decision.analysis_parameter_hash
            count += 1
    done = json.loads((partition / "DONE.json").read_text(encoding="utf-8"))
    if count != int(done["boundaries"]):
        raise ValueError("CANDIDATE_BOUNDARY_COUNT_MISMATCH")
    receipt = {"version": "candidate-native-stage-partition/3",
               "dataset_hash": done["dataset_hash"],
               "configuration_hash": configuration_hash,
               "boundaries": count, "sha256": _sha256(output),
               "holdout_evaluated": False}
    _write_json(output.with_suffix(".json"), receipt)
    return receipt


def write_native_candidate_signals_v3(
    request_path: Path, dataset: Path, cache: Path, partition: Path,
    changes: dict[str, Any], output: Path,
) -> dict[str, Any]:
    """Checkpoint a compact native stage trace for one candidate and symbol.

    Only a ready plan's execution inputs are copied; every boundary retains its
    stage statuses, first rejection and native decision hash. The full frozen
    cache remains the source of raw stage evidence for independent verification.
    """
    manifest = RaggedDatasetManifestV2.model_validate_json(
        (dataset / "DATASET_MANIFEST.json").read_text(encoding="utf-8"))
    baseline = load_trade_parameters().resolve_scalping_v2_parameter_set()
    candidate = resolve_research_parameter_set_v3(baseline, changes)
    identity = {"version": "candidate-native-signals/3",
                "dataset_hash": manifest.dataset_hash,
                "request_hash": manifest.request_hash,
                "configuration_hash": candidate.resolved_config_hash,
                "symbol": partition.parent.name,
                "segment_start_ms": int(partition.name),
                "source_sha256": json.loads((partition / "DONE.json").read_text(encoding="utf-8"))["sha256"]}
    receipt_path = output.with_suffix(".json")
    if output.exists() or receipt_path.exists():
        if output.exists() and not receipt_path.exists():
            # A crash between the atomic rename and receipt write is safe to
            # finish after checking every compact record against the source count.
            source_done = json.loads((partition / "DONE.json").read_text(encoding="utf-8"))
            with output.open(encoding="utf-8") as handle:
                rows = [json.loads(line) for line in handle if line.endswith("\n")]
            if len(rows) != int(source_done["boundaries"]) or any(
                row["symbol"] != partition.parent.name
                or row["analysis_parameter_hash"] != candidate.resolved_config_hash
                for row in rows
            ):
                raise ValueError("CANDIDATE_SIGNAL_INCOMPLETE_FINAL_OUTPUT")
            recovered = {**identity, "boundaries": len(rows),
                         "sha256": _sha256(output), "holdout_evaluated": False}
            _write_json(receipt_path, recovered)
            output.with_suffix(".checkpoint.json").unlink(missing_ok=True)
        if not output.exists() or not receipt_path.exists():
            raise ValueError("CANDIDATE_SIGNAL_INCOMPLETE_FINAL_OUTPUT")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if any(receipt.get(key) != value for key, value in identity.items()) or receipt.get("sha256") != _sha256(output):
            raise ValueError("CANDIDATE_SIGNAL_RESUME_IDENTITY_MISMATCH")
        return receipt
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_suffix(".partial")
    checkpoint_path = output.with_suffix(".checkpoint.json")
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8")) if checkpoint_path.exists() else None
    if partial.exists() and not checkpoint and partial.stat().st_size == 0:
        checkpoint = {**identity, "boundaries": 0, "last_boundary_ms": -1}
        _write_json(checkpoint_path, checkpoint)
    if checkpoint and any(checkpoint.get(key) != value for key, value in identity.items()):
        raise ValueError("CANDIDATE_SIGNAL_CHECKPOINT_IDENTITY_MISMATCH")
    if partial.exists() != bool(checkpoint):
        raise ValueError("CANDIDATE_SIGNAL_PARTIAL_WITHOUT_CHECKPOINT")
    count = int(checkpoint["boundaries"]) if checkpoint else 0
    if checkpoint:
        from .full_pipeline_v3 import _truncate_after_checkpoint
        _truncate_after_checkpoint(partial, int(checkpoint["last_boundary_ms"]))
    if checkpoint is None:
        partial.touch()
        checkpoint = {**identity, "boundaries": 0, "last_boundary_ms": -1}
        _write_json(checkpoint_path, checkpoint)
    with partial.open("a", encoding="utf-8") as handle:
        for index, decision in enumerate(native_candidate_decisions_v3(
                request_path, dataset, cache, partition, changes)):
            if index < count:
                continue
            paper = decision.paper
            signal = {"symbol": decision.symbol, "boundary_ms": decision.boundary_ms,
                      "statuses": decision.statuses,
                      "first_rejection": decision.first_rejection,
                      "decision_hash": decision.decision_hash,
                      "analysis_parameter_hash": decision.analysis_parameter_hash,
                      "paper": {}}
            if decision.statuses.get("paper_status") == "PAPER_PLAN_READY":
                context = paper.get("paper_context") or {}
                diagnostic = context.get("scalping_geometry_diagnostics") or {}
                signal["paper"] = {
                    key: paper.get(key) for key in (
                        "source_setup_id", "source_risk_score",
                        "hypothetical_entry_reference", "hypothetical_stop_level",
                        "hypothetical_target_level")
                }
                signal["paper"]["paper_context"] = {
                    "empirical_regime_normalized": context.get("empirical_regime_normalized"),
                    "scalping_geometry_diagnostics": {
                        "opportunity_id": diagnostic.get("opportunity_id")}}
            handle.write(json.dumps(signal, sort_keys=True, separators=(",", ":")) + "\n")
            count = index + 1
            if count % 100 == 0:
                handle.flush()
                _write_json(checkpoint_path, {**identity, "boundaries": count,
                                              "last_boundary_ms": decision.boundary_ms})
        handle.flush()
    done = json.loads((partition / "DONE.json").read_text(encoding="utf-8"))
    if count != int(done["boundaries"]):
        raise ValueError("CANDIDATE_SIGNAL_BOUNDARY_COUNT_MISMATCH")
    partial.replace(output)
    receipt = {**identity, "boundaries": count, "sha256": _sha256(output),
               "holdout_evaluated": False}
    _write_json(receipt_path, receipt)
    checkpoint_path.unlink(missing_ok=True)
    return receipt


def build_native_candidate_signal_cache_v3(
    request_path: Path, dataset: Path, cache: Path, output: Path,
    changes: dict[str, Any],
) -> dict[str, Any]:
    """Run one candidate sequentially over every certified pre-holdout partition."""
    request = FullPipelineCalibrationRequestV2.model_validate_json(
        request_path.read_text(encoding="utf-8"))
    dataset_manifest = RaggedDatasetManifestV2.model_validate_json(
        (dataset / "DATASET_MANIFEST.json").read_text(encoding="utf-8"))
    cache_manifest = json.loads((cache / "FEATURE_CACHE_MANIFEST.json").read_text(encoding="utf-8"))
    holdout_start = next(window.start_ms for window in request.windows
                         if window.role == "INTERNAL_HOLDOUT")
    expected = sum(_closed_boundary_count(segment.start_ms,
                   min(segment.end_ms, holdout_start), 300_000)
                   for symbol in dataset_manifest.symbols if symbol.status != "UNUSABLE"
                   for segment in symbol.segments if segment.start_ms < holdout_start)
    partitions = cache_manifest["partitions"]
    if (dataset_manifest.status != "FROZEN"
            or dataset_manifest.request_hash != request.identity
            or cache_manifest.get("dataset_hash") != dataset_manifest.dataset_hash
            or cache_manifest.get("request_hash") != request.identity
            or cache_manifest.get("holdout_evaluated") is not False
            or cache_manifest.get("completed_boundaries") != expected
            or sum(int(item["boundaries"]) for item in partitions) != expected):
        raise ValueError("CANDIDATE_PREHOLDOUT_CACHE_INCOMPLETE")
    if shutil.disk_usage(output.parent).free < 5 * (1 << 30):
        raise ValueError("CANDIDATE_SIGNAL_DISK_RESERVE_BELOW_5GB")
    baseline = load_trade_parameters().resolve_scalping_v2_parameter_set()
    candidate = resolve_research_parameter_set_v3(baseline, changes)
    identity = {"version": "candidate-native-signal-cache/3",
                "dataset_hash": dataset_manifest.dataset_hash,
                "request_hash": request.identity,
                "source_cache_hash": fingerprint(cache_manifest),
                "configuration_hash": candidate.resolved_config_hash,
                "expected_boundaries": expected, "holdout_evaluated": False}
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "CANDIDATE_SIGNAL_MANIFEST.json"
    if manifest_path.exists():
        saved = json.loads(manifest_path.read_text(encoding="utf-8"))
        if any(saved.get(key) != value for key, value in identity.items()):
            raise ValueError("CANDIDATE_SIGNAL_CACHE_IDENTITY_CHANGED")
    receipts: list[dict[str, Any]] = []
    for part in partitions:
        symbol = part["symbol"]
        partition = cache / "symbols" / symbol / str(part["segment_start_ms"])
        destination = output / "symbols" / symbol / str(part["segment_start_ms"]) / "SIGNALS.jsonl"
        print(f"CANDIDATE_V3_SYMBOL_START {symbol} {part['segment_start_ms']}", flush=True)
        receipt = write_native_candidate_signals_v3(
            request_path, dataset, cache, partition, changes, destination)
        receipts.append(receipt)
        progress = {**identity, "status": "IN_PROGRESS",
                    "completed_boundaries": sum(item["boundaries"] for item in receipts),
                    "partitions": receipts}
        _write_json(manifest_path, progress)
        print(f"CANDIDATE_V3_SYMBOL_DONE {symbol} {receipt['boundaries']}", flush=True)
    result = {**identity, "status": "COMPLETE_PREHOLDOUT",
              "completed_boundaries": sum(item["boundaries"] for item in receipts),
              "partitions": receipts}
    _write_json(manifest_path, result)
    return result
