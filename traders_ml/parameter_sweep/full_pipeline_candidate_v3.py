"""Recompute native stage decisions for a frozen v3 cache partition.

This produces candidate-specific causal decisions. Portfolio execution and
economic acceptance remain separate gates; this module cannot declare a
candidate eligible or read the locked holdout.
"""

from __future__ import annotations

import json
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
    cost_model = HistoricalCostModelV1.model_validate_json(
        (dataset / "HISTORICAL_COST_MODEL.json").read_text(encoding="utf-8")
    )
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
