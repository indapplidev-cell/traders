"""Preview and JSON serialization helpers for engine_analysis results."""

from __future__ import annotations

import json
from pathlib import Path

from app.engine_analysis.analysis_quality_basis import build_analysis_quality_basis
from app.engine_analysis.causal_planning_context import build_causal_planning_context
from app.engine_analysis.regime_composer import RegimeComposerOutput


def build_engine_analysis_preview(output: RegimeComposerOutput) -> dict[str, object]:
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
            "selected_hypothesis": output.decision_trace.selected_hypothesis,
        },
    }


def build_engine_analysis_json_payload(
    output: RegimeComposerOutput,
) -> dict[str, object]:
    """Build the standalone preview JSON contract."""
    quality_basis = build_analysis_quality_basis(output)
    payload: dict[str, object] = {
        "service": "ENGINE_ANALYSIS",
        "contract_version": "engine_analysis_preview_v2",
        "result": output.result.to_dict(),
        "decision_trace": output.decision_trace.to_dict(),
        "ohlc_integrity": output.ohlc_integrity.to_dict(),
        "matrix_summary": dict(output.matrix.summary) if output.matrix else {},
        "analysis_context": (
            {
                "analysis_window": output.matrix.unified_context.analysis_window.to_dict(),
                "technical_indicators": output.matrix.unified_context.indicator_context.to_dict(),
                "hypotheses": output.matrix.hypothesis_result.to_dict(),
                "selected_hypothesis": output.decision_trace.selected_hypothesis,
            }
            if output.matrix
            else {}
        ),
        "safety": output.result.safety.to_dict(),
        "warnings": list(output.result.warnings),
        "errors": list(output.result.errors),
    }
    if quality_basis is not None:
        payload.update({
            "impulse_phase": quality_basis["impulse_phase"],
            "entry_quality": quality_basis["entry_quality"],
            "entry_quality_reason_codes": quality_basis["entry_quality_reason_codes"],
            "human_readable_explanation": quality_basis["human_explanation"],
        })
        payload["analysis_context"]["quality_basis"] = quality_basis
    if output.matrix:
        payload["analysis_context"].update(build_causal_planning_context(
            output.matrix.unified_context, output.matrix.hypothesis_result,
        ))
    return payload


def save_engine_analysis_json(
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
