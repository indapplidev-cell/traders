"""Preview and JSON serialization helpers for engine_trend results."""

from __future__ import annotations

import json
from pathlib import Path

from app.market_reader.engine_trend.regime_composer import RegimeComposerOutput


def build_engine_trend_preview(output: RegimeComposerOutput) -> dict[str, object]:
    """Build a compact, human-readable view of a composer result."""
    result = output.result
    scores = output.decision_trace.candidate_scores
    return {
        "symbol": result.symbol,
        "interval": result.interval,
        "period_start": result.period_start,
        "period_end": result.period_end,
        "candle_count": result.candle_count,
        "market_regime": result.market_regime.value,
        "confidence": result.confidence,
        "confidence_level": scores.confidence_level.value,
        "status": output.decision_trace.status.value,
        "reason_codes_top": list(result.reason_codes[:10]),
        "safety": result.safety.to_dict(),
        "summary": {
            "matrix_summary": dict(output.matrix.summary) if output.matrix else {},
            "candidate_scores": scores.to_dict(),
        },
    }


def build_engine_trend_json_payload(
    output: RegimeComposerOutput,
) -> dict[str, object]:
    """Build the standalone preview JSON contract."""
    return {
        "service": "ENGINE_TREND",
        "contract_version": "engine_trend_preview_v1",
        "result": output.result.to_dict(),
        "decision_trace": output.decision_trace.to_dict(),
        "ohlc_integrity": output.ohlc_integrity.to_dict(),
        "matrix_summary": dict(output.matrix.summary) if output.matrix else {},
        "safety": output.result.safety.to_dict(),
        "warnings": list(output.result.warnings),
        "errors": list(output.result.errors),
    }


def save_engine_trend_json(
    payload: dict[str, object], output_path: str | Path
) -> Path:
    """Write a JSON-compatible payload and return its path."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path
