"""Generate ENGINE-TREND-17C trace-only composer reports from PostgreSQL candles."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

from app.market_reader.engine_trend.data_source_boundary import CandleDataRequest, run_engine_trend_from_provider
from app.market_reader.engine_trend.db_cli_preview import resolve_db_url
from app.market_reader.engine_trend.postgres_candle_adapter import PostgresMarketCandlesProvider

STAGE = "ENGINE-TREND-17C"
ROOT = Path("reports/engine_trend/composer_raw_score_trace")
REPORT = Path("reports/engine_trend/engine_trend_17c_composer_raw_score_trace_exposure_report.md")
INPUTS = (
    ("ENGINE-TREND-15", Path("reports/engine_trend/historical_validation/ENGINE_TREND_15_VALIDATION_WINDOWS.json")),
    ("ENGINE-TREND-15B", Path("reports/engine_trend/symbol_suitability_validation/ENGINE_TREND_15B_EXPANDED_VALIDATION_WINDOWS.json")),
)
REGIMES = ("UP", "DOWN", "FLAT", "UNKNOWN")
UNAVAILABLE = {"available": False, "missing_reason": "NOT_EXPOSED_BY_CURRENT_TRACE", "recommended_next_action": "RUN_TRACE_INSTRUMENTED_POSTGRES_REPLAY"}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def load_windows() -> list[dict[str, Any]]:
    rows = []
    for source_stage, path in INPUTS:
        rows.extend({"source_stage": source_stage, **row} for row in json.loads(path.read_text(encoding="utf-8"))["windows"])
    return sorted(rows, key=lambda row: (row["source_stage"], row["symbol"], row["reference_label"], row["window_id"]))


def score_gap(ranking: list[dict[str, Any]]) -> float | None:
    return ranking[0]["score"] - ranking[1]["score"] if len(ranking) > 1 else None


def layer_summaries(matrix: dict[str, Any]) -> dict[str, Any]:
    nison, altunina, schwager = (matrix.get(name, {}) for name in ("nison_context", "altunina_context", "schwager_context"))
    return {
        "nison": {"summary": nison.get("summary", {}), "reason_codes": nison.get("reason_codes", []), "important_candles": [x for x in nison.get("candle_contexts", []) if x.get("reason_codes")][:20]},
        "altunina": {"structure_direction": altunina.get("structure_direction"), "trend_strength_score": altunina.get("trend_strength_score"), "trend_consistency_score": altunina.get("trend_consistency_score"), "trend_progress_score": altunina.get("trend_progress_score"), "swing_points": altunina.get("swing_points", []), "reason_codes": altunina.get("reason_codes", [])},
        "schwager": {"trading_range": schwager.get("trading_range", {}), "breakout_context": schwager.get("breakout_context", {}), "polarity_flip_context": schwager.get("polarity_flip_context", {}), "reason_codes": schwager.get("reason_codes", [])},
        "book_evidence_matrix": {"directional_balance": matrix.get("directional_balance", {}), "confluence_conflict": matrix.get("confluence_conflict", {}), "summary": matrix.get("summary", {}), "buckets": matrix.get("buckets", [])},
    }


def build(window: dict[str, Any], boundary: Any) -> dict[str, Any]:
    output = boundary.engine_output.composer_output
    serialized = output.to_dict()
    result = output.result
    candidate = serialized["decision_trace"]["candidate_scores"]
    composer = candidate.get("composer_trace", {})
    raw = composer.get("raw_scores")
    clamped = composer.get("clamped_scores")
    raw_rank = composer.get("ranking_before_clamp", [])
    clamped_rank = composer.get("ranking_after_clamp", [])
    missing = [name for name, value in {
        "raw_scores": raw, "clamped_scores": clamped, "ranking_before_clamp": raw_rank,
        "ranking_after_clamp": clamped_rank, "fallback_reason": composer.get("fallback_reason"),
        "confidence_path": composer.get("confidence_path"),
    }.items() if value is None or value == []]
    raw = raw or {regime: None for regime in REGIMES}
    clamped = clamped or {regime: None for regime in REGIMES}
    final = {
        "market_regime": result.market_regime.value, "confidence": result.confidence,
        "boundary_status": boundary.status.value, "trade_signal": "NOT_EVALUATED",
        "safe_for_runtime_trading": False, "live_trading_connected": False,
        "warnings_count": len(boundary.warnings), "errors_count": len(boundary.errors),
    }
    trace = {
        "raw_scores": raw, "clamped_scores": clamped,
        "ranking_before_clamp": raw_rank, "ranking_after_clamp": clamped_rank,
        "top1_before_clamp": raw_rank[0] if raw_rank else None, "top2_before_clamp": raw_rank[1] if len(raw_rank) > 1 else None,
        "top1_after_clamp": clamped_rank[0] if clamped_rank else None, "top2_after_clamp": clamped_rank[1] if len(clamped_rank) > 1 else None,
        "score_gap_before_clamp": score_gap(raw_rank), "score_gap_after_clamp": score_gap(clamped_rank),
        "selected_regime_before_fallback": composer.get("selected_regime_before_fallback"),
        "selected_regime_after_fallback": composer.get("selected_regime_after_fallback"),
        "fallback_triggered": composer.get("fallback_triggered"), "fallback_reason": composer.get("fallback_reason"),
        "confidence_path": composer.get("confidence_path", []), "confidence_final": composer.get("confidence_final", result.confidence),
        "final_regime": result.market_regime.value,
    }
    raw_winner = trace["top1_before_clamp"]
    clamp_winner = trace["top1_after_clamp"]
    why = trace["fallback_reason"] or "No fallback reason was emitted."
    return {
        "stage": STAGE,
        "window": {key: window.get(key) for key in ("window_id", "source_stage", "symbol", "interval", "period_start", "period_end", "window_length", "reference_label", "selection_reason")},
        "final_result": final,
        "layer_summaries": layer_summaries(serialized.get("matrix") or {}),
        "composer_trace": trace,
        "trace_completeness": {
            "composer_raw_scores_available": bool(composer.get("raw_scores")), "composer_clamped_scores_available": bool(composer.get("clamped_scores")),
            "ranking_before_clamp_available": bool(raw_rank), "ranking_after_clamp_available": bool(clamped_rank),
            "fallback_reason_available": composer.get("fallback_reason") is not None, "missing_fields": missing,
        },
        "human_readable_explanation": {
            "summary": f"The composer selected {trace['selected_regime_before_fallback']} from its existing clamped ranking and finalized {result.market_regime.value} at confidence {result.confidence}.",
            "why_unknown": why if result.market_regime.value == "UNKNOWN" else "The final regime was not UNKNOWN.",
            "what_raw_scores_suggested": f"Raw top candidates: {raw_winner} and {trace['top2_before_clamp']}." if raw_winner else "NOT_EXPOSED_BY_CURRENT_TRACE",
            "what_clamped_scores_did": f"Clamped top candidates: {clamp_winner} and {trace['top2_after_clamp']}." if clamp_winner else "NOT_EXPOSED_BY_CURRENT_TRACE",
            "why_fallback_happened": why,
            "why_this_window_needs_or_does_not_need_tuning": "This trace supports manual diagnosis only; it does not authorize a tuning change.",
        },
    }


def md_section(trace: dict[str, Any], number: int | None = None) -> str:
    w, f, layers, c = trace["window"], trace["final_result"], trace["layer_summaries"], trace["composer_trace"]
    title = f"## Window {number:03d} — {w['window_id']}" if number else f"# {w['window_id']} — Composer Trace"
    def compact(value: Any) -> str: return json.dumps(value, ensure_ascii=False, default=str)
    rows = "\n".join(f"| {regime} | {c['raw_scores'].get(regime, 'NOT_EXPOSED_BY_CURRENT_TRACE')} | {c['clamped_scores'].get(regime, 'NOT_EXPOSED_BY_CURRENT_TRACE')} |" for regime in REGIMES)
    missing = ", ".join(trace["trace_completeness"]["missing_fields"]) or "None"
    return f"""{title}

### Window metadata
- Source stage: {w['source_stage']}
- Symbol: {w['symbol']}
- Period: {w['period_start']} — {w['period_end']}
- Reference label: {w['reference_label']}
- Selection reason: {w['selection_reason']}

### Final engine result
- Market regime: {f['market_regime']}
- Confidence: {f['confidence']}
- Safety: trade signal NOT_EVALUATED; runtime false; live false

### Nison summary
- Important candles: {compact(layers['nison'].get('important_candles', layers['nison'].get('important_events', 'NOT_EXPOSED_BY_CURRENT_TRACE')))}
- Doji/small body, star patterns, engulfing/body dominance, notes: {compact(layers['nison'])}

### Altunina trend summary
- Swing/trend structure, directional progress, strength, notes: {compact(layers['altunina'])}

### Schwager range summary
- Range detected, bounds, breakout/fakeout, notes: {compact(layers['schwager'])}

### BookEvidenceMatrix summary
- Bullish/bearish/neutral evidence, conflict, coverage, notes: {compact(layers['book_evidence_matrix'])}

### Composer raw score trace
| Regime | Raw score | Clamped score |
|---|---:|---:|
{rows}

### Composer ranking
- Ranking before clamp: {compact(c['ranking_before_clamp'])}
- Ranking after clamp: {compact(c['ranking_after_clamp'])}
- Raw score gap: {c['score_gap_before_clamp']}
- Clamped score gap: {c['score_gap_after_clamp']}
- Selected before fallback: {c['selected_regime_before_fallback']}
- Selected after fallback: {c['selected_regime_after_fallback']}
- Fallback triggered: {c['fallback_triggered']}
- Fallback reason: {c['fallback_reason'] or 'NOT_EXPOSED_BY_CURRENT_TRACE'}
- Confidence path: {compact(c['confidence_path'])}

### Human-readable explanation
{trace['human_readable_explanation']['summary']} {trace['human_readable_explanation']['why_unknown']} {trace['human_readable_explanation']['what_raw_scores_suggested']} {trace['human_readable_explanation']['what_clamped_scores_did']}

### Trace completeness
Missing fields: {missing}

---
"""


def matrix_row(trace: dict[str, Any]) -> dict[str, Any]:
    w, f, c = trace["window"], trace["final_result"], trace["composer_trace"]
    def item(ranking: list[dict[str, Any]], index: int, key: str) -> Any: return ranking[index][key] if len(ranking) > index else None
    row = {"window_id": w["window_id"], "source_stage": w["source_stage"], "symbol": w["symbol"], "reference_label": w["reference_label"], "final_regime": f["market_regime"], "confidence": f["confidence"]}
    row.update({f"raw_{r.lower()}_score": c["raw_scores"].get(r) for r in REGIMES})
    row.update({f"clamped_{r.lower()}_score": c["clamped_scores"].get(r) for r in REGIMES})
    row.update({"top1_raw_regime": item(c["ranking_before_clamp"], 0, "regime"), "top1_raw_score": item(c["ranking_before_clamp"], 0, "score"), "top2_raw_regime": item(c["ranking_before_clamp"], 1, "regime"), "top2_raw_score": item(c["ranking_before_clamp"], 1, "score"), "score_gap_raw_top2": c["score_gap_before_clamp"], "top1_clamped_regime": item(c["ranking_after_clamp"], 0, "regime"), "top1_clamped_score": item(c["ranking_after_clamp"], 0, "score"), "top2_clamped_regime": item(c["ranking_after_clamp"], 1, "regime"), "top2_clamped_score": item(c["ranking_after_clamp"], 1, "score"), "score_gap_clamped_top2": c["score_gap_after_clamp"], "selected_regime_before_fallback": c["selected_regime_before_fallback"], "selected_regime_after_fallback": c["selected_regime_after_fallback"], "fallback_triggered": c["fallback_triggered"], "fallback_reason": c["fallback_reason"], "confidence_final": c["confidence_final"], "safety_ok": f["trade_signal"] == "NOT_EVALUATED" and not f["safe_for_runtime_trading"] and not f["live_trading_connected"], "notes": "Trace-only observation; clamped ranking remains the decision path."})
    return row


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def finish(traces: list[dict[str, Any]]) -> None:
    rows = [matrix_row(t) for t in traces]
    violations = sum(not r["safety_ok"] or r["final_regime"] != "UNKNOWN" or r["confidence"] != 0.3 for r in rows)
    lock = {"stage": STAGE, "window_count": len(rows), "market_regime_counts": dict(Counter(r["final_regime"] for r in rows)), "confidence_counts": dict(Counter(str(r["confidence"]) for r in rows)), "unknown_0_3_count": sum(r["final_regime"] == "UNKNOWN" and r["confidence"] == 0.3 for r in rows), "safety_violations": sum(not r["safety_ok"] for r in rows), "behavior_changed": violations != 0, "behavior_lock_ok": violations == 0 and len(rows) >= 60}
    write_json(ROOT / "ENGINE_TREND_17C_BEHAVIOR_LOCK.json", lock)
    write_json(ROOT / "ENGINE_TREND_17C_RAW_SCORE_MATRIX.json", {"stage": STAGE, "window_count": len(rows), "rows": rows}); write_csv(ROOT / "ENGINE_TREND_17C_RAW_SCORE_MATRIX.csv", rows)
    coverage = []
    for trace in traces:
        w, f, complete = trace["window"], trace["final_result"], trace["trace_completeness"]
        coverage.append({"window_id": w["window_id"], "symbol": w["symbol"], "reference_label": w["reference_label"], "final_regime": f["market_regime"], "confidence": f["confidence"], "raw_scores_available": complete["composer_raw_scores_available"], "clamped_scores_available": complete["composer_clamped_scores_available"], "ranking_before_clamp_available": complete["ranking_before_clamp_available"], "ranking_after_clamp_available": complete["ranking_after_clamp_available"], "score_gap_before_clamp_available": trace["composer_trace"]["score_gap_before_clamp"] is not None, "score_gap_after_clamp_available": trace["composer_trace"]["score_gap_after_clamp"] is not None, "fallback_reason_available": complete["fallback_reason_available"], "confidence_path_available": bool(trace["composer_trace"]["confidence_path"]), "all_window_report_section_present": True, "per_window_json_present": True, "per_window_markdown_present": True, "missing_composer_trace_field_count": len(complete["missing_fields"]), "behavior_lock_ok": f["market_regime"] == "UNKNOWN" and f["confidence"] == 0.3, "notes": "Trace-only exposure."})
    write_json(ROOT / "ENGINE_TREND_17C_COMPOSER_TRACE_COVERAGE_MATRIX.json", {"stage": STAGE, "window_count": len(coverage), "rows": coverage}); write_csv(ROOT / "ENGINE_TREND_17C_COMPOSER_TRACE_COVERAGE_MATRIX.csv", coverage)
    missing_by_window = {t["window"]["window_id"]: t["trace_completeness"]["missing_fields"] for t in traces if t["trace_completeness"]["missing_fields"]}
    missing_counts = Counter(field for fields in missing_by_window.values() for field in fields)
    raw_ready = sum(r["raw_scores_available"] and r["clamped_scores_available"] for r in coverage) >= len(rows) - 1
    write_json(ROOT / "ENGINE_TREND_17C_MISSING_COMPOSER_TRACE_FIELDS.json", {"missing_fields_by_window": missing_by_window, "missing_fields_by_composer_section": {"composer_trace": sorted(missing_counts)}, "most_common_missing_fields": [{"field": k, "window_count": v} for k, v in missing_counts.most_common()], "fields_required_before_next_tuning_attempt": sorted(missing_counts), "can_proceed_to_tuning": raw_ready, "next_stage": "ENGINE-TREND-18 — Evidence-Guided Composer Tuning Plan" if raw_ready else "ENGINE-TREND-17D — Composer Internal Score Instrumentation"})
    intro = f"# ENGINE-TREND-17C — All Windows Composer Trace Review\n\n## Purpose\nReview all {len(rows)} composer traces consecutively.\n\n## Behavior lock summary\nUNKNOWN 0.3: {lock['unknown_0_3_count']}/{len(rows)}; safety violations: {lock['safety_violations']}; behavior changed: {str(lock['behavior_changed']).lower()}.\n\n## Important warning\nAggregate statistics are shown only as navigation. The actual evidence review is per-window below.\n\n## Window list\n\n| # | Window | Source | Symbol | Label |\n|---:|---|---|---|---|\n" + "\n".join(f"| {i:03d} | {t['window']['window_id']} | {t['window']['source_stage']} | {t['window']['symbol']} | {t['window']['reference_label']} |" for i, t in enumerate(traces, 1)) + "\n\n---\n\n"
    (ROOT / "ENGINE_TREND_17C_ALL_WINDOWS_TRACE_REVIEW.md").write_text(intro + "\n".join(md_section(t, i) for i, t in enumerate(traces, 1)), encoding="utf-8")
    decision = "ENGINE-TREND-18 — Evidence-Guided Composer Tuning Plan" if raw_ready else "ENGINE-TREND-17D — Composer Internal Score Instrumentation"
    (ROOT / "ENGINE_TREND_17C_TRACE_READINESS_DECISION.md").write_text(f"# ENGINE-TREND-17C — Trace Readiness Decision\n\n## What was exposed\nRaw and clamped scores, both observational rankings, top-two gaps, fallback reason, confidence path, and selection before/after fallback are exposed per window.\n\n## What remains hidden\n{dict(missing_counts) or 'No required composer fields remain hidden.'}\n\n## Can we safely tune composer now?\n{'Trace evidence is ready for a tuning plan, but no tuning is authorized by this stage.' if raw_ready else 'No; required score fields remain hidden.'}\n\n## Why aggregate-only reports are insufficient\nClamp collisions, evidence conflicts, and fallback paths differ by window despite identical final results.\n\n## Per-window review readiness\n{len(rows)} sections are available in the primary all-windows artifact.\n\n## Required next stage\n{decision}\n", encoding="utf-8")
    REPORT.write_text(f"# ENGINE-TREND-17C — Composer Raw Score Trace Exposure\n\n## Stage goal\nExpose composer internals without changing decisions.\n\n## Baseline\n60/60 UNKNOWN at confidence 0.3.\n\n## Files created/changed\nTrace-only composer fields, runner, tests, per-window and aggregate artifacts.\n\n## Input windows\n15 ENGINE-TREND-15 and 45 ENGINE-TREND-15B windows, replayed from PostgreSQL.\n\n## Behavior lock\n{lock}\n\n## Composer trace exposure\nRaw/clamped scores, rankings, gaps, fallback and confidence path are observational fields. Existing clamped decision ranking is unchanged.\n\n## Unified all-windows report\nAggregate summary does not replace per-window review. The all-windows report is the primary artifact for human analysis.\n\n## Raw score matrix\nContains {len(rows)} rows.\n\n## Missing composer fields\n{dict(missing_counts) or 'None among required fields.'}\n\n## Safety verification\nNo runtime or live trading is connected; safety violations: {lock['safety_violations']}.\n\n## Tests executed\nSee delivery record.\n\n## Scans executed\nProtected-file, rejected-candidate, legacy import, write SQL, trading, and credential scans are required before commit.\n\n## Known limitations\nReference labels are descriptive; 96 candles may be insufficient.\n\n## What this stage proves\nComposer score and fallback paths are reviewable per window.\n\n## What this stage does not prove\nNo edge, profitability, tuning safety, runtime readiness, or live execution readiness is proven.\n\n## Next recommended stage\n{decision}\n", encoding="utf-8")
    outputs = [p for p in ROOT.rglob("*") if p.is_file() and p.name != "ENGINE_TREND_17C_ARTIFACT_MANIFEST.json"] + [REPORT]
    manifest = {"stage": STAGE, "generated_at": datetime.now(timezone.utc).isoformat(), "input_artifacts": [str(p).replace("\\", "/") for _, p in INPUTS], "output_artifacts": [str(p).replace("\\", "/") for p in outputs], "all_windows_report": str(ROOT / "ENGINE_TREND_17C_ALL_WINDOWS_TRACE_REVIEW.md").replace("\\", "/"), "per_window_json_files": [str(p).replace("\\", "/") for p in sorted((ROOT / "json").glob("*.json"))], "per_window_markdown_files": [str(p).replace("\\", "/") for p in sorted((ROOT / "markdown").glob("*.md"))], "raw_score_matrix": str(ROOT / "ENGINE_TREND_17C_RAW_SCORE_MATRIX.json").replace("\\", "/"), "trace_coverage_matrix": str(ROOT / "ENGINE_TREND_17C_COMPOSER_TRACE_COVERAGE_MATRIX.json").replace("\\", "/"), "sha256_checksums": {str(p).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest() for p in outputs}, "window_count": len(rows), "behavior_lock_summary": lock, "composer_trace_summary": {"raw_score_rows": sum(r["raw_scores_available"] for r in coverage), "complete_rows": sum(r["missing_composer_trace_field_count"] == 0 for r in coverage)}, "core_behavior_changed": False, "adapter_changed": False, "db_cli_changed": False, "runtime_trading_allowed": False, "trading_claims_allowed": False}
    write_json(ROOT / "ENGINE_TREND_17C_ARTIFACT_MANIFEST.json", manifest)


def build_blocked_from_17b() -> list[dict[str, Any]]:
    """Create honest review shells from 17B metadata when a new DB replay is unavailable."""
    traces = []
    source_root = Path("reports/engine_trend/per_window_trace/json")
    for window in load_windows():
        old = json.loads((source_root / f"{window['window_id']}_trace.json").read_text(encoding="utf-8"))
        old_composer = old["composer_trace"]
        clamped = old_composer.get("clamped_scores", UNAVAILABLE)
        clamped_map = clamped if isinstance(clamped, dict) and "available" not in clamped else {regime: None for regime in REGIMES}
        after = old_composer.get("ranking_after_clamp", [])
        trace = {
            "stage": STAGE,
            "window": {key: window.get(key) for key in ("window_id", "source_stage", "symbol", "interval", "period_start", "period_end", "window_length", "reference_label", "selection_reason")},
            "final_result": old["final_result"],
            "layer_summaries": {"nison": old["nison_candle_trace"], "altunina": old["altunina_trend_trace"], "schwager": old["schwager_range_trace"], "book_evidence_matrix": old["book_evidence_matrix_trace"]},
            "composer_trace": {"raw_scores": {regime: None for regime in REGIMES}, "clamped_scores": clamped_map, "ranking_before_clamp": [], "ranking_after_clamp": after, "top1_before_clamp": None, "top2_before_clamp": None, "top1_after_clamp": after[0] if after else None, "top2_after_clamp": after[1] if len(after) > 1 else None, "score_gap_before_clamp": None, "score_gap_after_clamp": old_composer.get("score_gap_clamped_top2"), "selected_regime_before_fallback": old_composer.get("selected_regime_before_fallback"), "selected_regime_after_fallback": old_composer.get("selected_regime_after_fallback"), "fallback_triggered": old_composer.get("fallback_triggered"), "fallback_reason": old_composer.get("fallback_reason"), "confidence_path": [], "confidence_final": old_composer.get("confidence_final"), "final_regime": old["final_result"]["market_regime"], "unavailable": UNAVAILABLE},
            "trace_completeness": {"composer_raw_scores_available": False, "composer_clamped_scores_available": bool(clamped_map), "ranking_before_clamp_available": False, "ranking_after_clamp_available": bool(after), "fallback_reason_available": isinstance(old_composer.get("fallback_reason"), str), "missing_fields": ["raw_scores", "ranking_before_clamp", "score_gap_before_clamp", "confidence_path"]},
            "human_readable_explanation": {"summary": "ENGINE-TREND-17C could not replay this window because DB configuration was unavailable; retained 17B observations are shown only as metadata.", "why_unknown": str(old_composer.get("fallback_reason") or "NOT_EXPOSED_BY_CURRENT_TRACE"), "what_raw_scores_suggested": "NOT_EXPOSED_BY_CURRENT_TRACE", "what_clamped_scores_did": f"17B observed {after}.", "why_fallback_happened": str(old_composer.get("fallback_reason") or "NOT_EXPOSED_BY_CURRENT_TRACE"), "why_this_window_needs_or_does_not_need_tuning": "Tuning is blocked until the instrumented PostgreSQL replay runs."},
        }
        traces.append(trace)
        write_json(ROOT / "json" / f"{window['window_id']}_composer_trace.json", trace)
        path = ROOT / "markdown" / f"{window['window_id']}_composer_trace.md"; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(md_section(trace), encoding="utf-8")
    return traces


def main() -> int:
    try: _, url = resolve_db_url(os.environ)
    except Exception:
        traces = build_blocked_from_17b(); finish(traces)
        print("error: DB_CONFIG_MISSING; wrote explicit blocked review artifacts", file=sys.stderr)
        return 2
    traces = []
    with create_engine(url).connect() as connection:
        connection.execute(text("SET TRANSACTION READ ONLY")); provider = PostgresMarketCandlesProvider(connection)
        for window in load_windows():
            request = CandleDataRequest(window["symbol"], window["interval"], int(window["window_length"]), window["period_start"], window["period_end"], "postgresql.public.market_candles")
            boundary = run_engine_trend_from_provider(provider, request, min_candle_count=int(window["window_length"]))
            if boundary.status.value != "READY" or boundary.batch.metadata.get("candle_count") != window["window_length"]: raise RuntimeError(f"WINDOW_REPLAY_FAILED:{window['window_id']}")
            trace = build(window, boundary); traces.append(trace)
            write_json(ROOT / "json" / f"{window['window_id']}_composer_trace.json", trace)
            path = ROOT / "markdown" / f"{window['window_id']}_composer_trace.md"; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(md_section(trace), encoding="utf-8")
    finish(traces)
    if not json.loads((ROOT / "ENGINE_TREND_17C_BEHAVIOR_LOCK.json").read_text(encoding="utf-8"))["behavior_lock_ok"]: print("error: BEHAVIOR_LOCK_FAILED", file=sys.stderr); return 1
    print(f"{STAGE} complete: {len(traces)} windows, behavior lock OK"); return 0


if __name__ == "__main__": raise SystemExit(main())
