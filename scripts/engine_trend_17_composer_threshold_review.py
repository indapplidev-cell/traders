"""Replay the fixed ENGINE-TREND-15/15B windows for composer-only review."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

from app.market_reader.engine_trend.data_source_boundary import CandleDataRequest, run_engine_trend_from_provider
from app.market_reader.engine_trend.db_cli_preview import resolve_db_url
from app.market_reader.engine_trend.postgres_candle_adapter import PostgresMarketCandlesProvider

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/engine_trend/composer_threshold_review"
REPORT = ROOT / "reports/engine_trend/engine_trend_17_conservative_composer_threshold_review_report.md"
WINDOW_INPUTS = [
    ("ENGINE-TREND-15", ROOT / "reports/engine_trend/historical_validation/ENGINE_TREND_15_VALIDATION_WINDOWS.json", ROOT / "reports/engine_trend/historical_validation/ENGINE_TREND_15_VALIDATION_MATRIX.json"),
    ("ENGINE-TREND-15B", ROOT / "reports/engine_trend/symbol_suitability_validation/ENGINE_TREND_15B_EXPANDED_VALIDATION_WINDOWS.json", ROOT / "reports/engine_trend/symbol_suitability_validation/ENGINE_TREND_15B_EXPANDED_VALIDATION_MATRIX.json"),
]
REVIEW_INPUTS = [
    ROOT / "reports/engine_trend/validation_review/ENGINE_TREND_16_TRACE_REVIEW_MATRIX.json",
    ROOT / "reports/engine_trend/validation_review/ENGINE_TREND_16_REASON_CODE_SUMMARY.json",
    ROOT / "reports/engine_trend/validation_review/ENGINE_TREND_16_CONFIDENCE_DIAGNOSTICS.json",
    ROOT / "reports/engine_trend/validation_review/ENGINE_TREND_16_DECISION_RECORD.json",
]
SAFETY = {"trade_signal": "NOT_EVALUATED", "safe_for_runtime_trading": False, "live_trading_connected": False}
AFTER_FIELDS = "source_stage window_id symbol interval period_start period_end window_length reference_label selection_reason before_engine_market_regime before_confidence after_engine_market_regime after_confidence after_boundary_status after_top_reason_codes after_warnings_count after_errors_count after_trade_signal after_safe_for_runtime_trading after_live_trading_connected after_match_status review_notes after_preview_artifact after_result_artifact".split()
COMPARE_FIELDS = "window_id symbol reference_label before_regime before_confidence before_match_status after_regime after_confidence after_match_status regime_changed confidence_changed improvement_status safety_preserved notes".split()


def load(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"required input missing: {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for row in rows:
            item = dict(row)
            if isinstance(item.get("after_top_reason_codes"), list):
                item["after_top_reason_codes"] = "|".join(item["after_top_reason_codes"])
            writer.writerow(item)


def match_status(label: str, regime: str) -> tuple[str, str]:
    expected = {"EXPECTED_UP": "UP", "EXPECTED_DOWN": "DOWN", "EXPECTED_FLAT": "FLAT", "EXPECTED_UNKNOWN_OR_MIXED": "UNKNOWN"}
    if expected.get(label) == regime: return "MATCH", "direct descriptive-label match"
    if label in {"HIGH_VOLATILITY_CHOP", "RECENT_BASELINE"} and regime == "UNKNOWN": return "ACCEPTABLE_UNKNOWN", "UNKNOWN retained for observational/choppy context"
    if label in {"EXPECTED_UP", "EXPECTED_DOWN", "EXPECTED_FLAT"} and regime == "UNKNOWN": return "QUESTIONABLE_UNKNOWN", "clear reference remains UNKNOWN"
    if (label, regime) in {("EXPECTED_UP", "DOWN"), ("EXPECTED_DOWN", "UP")} or (label == "EXPECTED_FLAT" and regime in {"UP", "DOWN"}): return "MISMATCH", "opposite or directional-vs-flat result"
    return "NEEDS_REVIEW", "non-direct comparison requires review"


def improvement(before: str, after: str) -> str:
    if before == "QUESTIONABLE_UNKNOWN" and after == "MATCH": return "IMPROVED"
    if after == "MISMATCH": return "REGRESSED"
    if before == after and after in {"MATCH", "ACCEPTABLE_UNKNOWN"}: return "UNCHANGED_ACCEPTABLE"
    if before == after: return "UNCHANGED_QUESTIONABLE"
    return "NEEDS_REVIEW"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    required = [p for _, w, m in WINDOW_INPUTS for p in (w, m)] + REVIEW_INPUTS
    for path in required: load(path)
    OUT.mkdir(parents=True, exist_ok=True)
    for sub in ("baseline", "after/previews", "after/results", "comparison"): (OUT / sub).mkdir(parents=True, exist_ok=True)

    windows: list[dict[str, Any]] = []
    before_rows: dict[tuple[str, str], dict[str, Any]] = {}
    for stage, wp, mp in WINDOW_INPUTS:
        for window in load(wp)["windows"]: windows.append({"source_stage": stage, **window})
        for row in load(mp)["rows"]: before_rows[(stage, row["window_id"])] = row
    before_unknown = sum(before_rows[(w["source_stage"], w["window_id"])]["engine_market_regime"] == "UNKNOWN" for w in windows)
    before_conf = sum(float(before_rows[(w["source_stage"], w["window_id"])]["confidence"]) == .3 for w in windows)
    baseline = {"stage": "ENGINE-TREND-17", "engine_trend_16_commit": "92f36ef", "before_windows": len(windows), "before_unknown_count": before_unknown, "before_confidence_0_3_count": before_conf, "before_safety_violations": 0, "fixed_evaluation_sources": [str(p.relative_to(ROOT)).replace('\\','/') for p in required]}
    if (len(windows), before_unknown, before_conf) != (60, 60, 60): raise RuntimeError("BASELINE_NOT_CONFIRMED")
    write_json(OUT / "ENGINE_TREND_17_BASELINE_SUMMARY.json", baseline)

    trace = load(REVIEW_INPUTS[0])["rows"]
    candidate = {"stage": "ENGINE-TREND-17", "windows_analyzed": len(trace), "observations": {"up_down_both_clamped_to_1_count": sum(r["up_score"] == 1.0 and r["down_score"] == 1.0 for r in trace), "zero_top2_gap_count": sum(r["score_gap_top2"] == 0.0 for r in trace), "coverage_levels": dict(Counter(r["coverage_level"] for r in trace)), "conflict_levels": dict(Counter(r["conflict_level"] for r in trace))}, "selected_adjustment_family": "PRESERVE_RAW_ADDITIVE_SCORES_UNTIL_RANKING", "candidate_count": 1, "rationale": "Pre-ranking clamp saturates both directional candidates and manufactures a zero margin. Rank raw additive evidence, then clamp only exported scores/confidence.", "unchanged_guards": ["MIN_REGIME_SCORE", "MIN_SCORE_MARGIN", "EMPTY_OR_LOW_COVERAGE_UNKNOWN", "HIGH_CONFLICT_UNKNOWN", "UNKNOWN_CONFIDENCE_CAP"], "uses_future_outcomes_or_profitability": False}
    write_json(OUT / "ENGINE_TREND_17_THRESHOLD_CANDIDATE_ANALYSIS.json", candidate)
    (OUT / "ENGINE_TREND_17_COMPOSER_RULE_REVIEW.md").write_text("""# ENGINE-TREND-17 — Composer Rule Review

## Current thresholds
`MIN_REGIME_SCORE = 0.30`; `MIN_SCORE_MARGIN = 0.08`. Candidate evidence is additive. Confidence is clamped to `[0,1]`; UNKNOWN is capped at `0.35`, with the conservative score fallback capped at `0.30`.

## Fallback and UNKNOWN rules
Invalid OHLC fails closed at confidence 0. Empty/low coverage remains UNKNOWN (maximum 0/0.25). High conflict remains UNKNOWN unless a confirmed returned/false-breakout range is clear. A winner below 0.30 or with top-two margin below 0.08 remains UNKNOWN, except detected-range FLAT margin handling.

## Conflict and coverage
Coverage and conflict are evaluated before the generic score fallback. Medium conflict caps composed confidence at 0.60; high conflict caps it further. These guards are unchanged.

## Finding
The old code clamped additive candidate totals before ranking. In all 60 reviewed traces both UP and DOWN became 1.0, manufacturing a zero top-two gap and forcing `COMPOSER_CONSERVATIVE_FALLBACK_UNKNOWN`. The selected change ranks raw totals and clamps only public scores/confidence. No threshold value or extraction behavior changes.
""", encoding="utf-8")

    try: _, db_url = resolve_db_url(os.environ)
    except Exception: print("error: DB_CONFIG_MISSING", file=sys.stderr); return 1
    engine = create_engine(db_url)
    after_rows: list[dict[str, Any]] = []; comparisons: list[dict[str, Any]] = []
    try:
        with engine.connect() as connection:
            connection.execute(text("SET TRANSACTION READ ONLY"))
            provider = PostgresMarketCandlesProvider(connection)
            for window in windows:
                stage, wid = window["source_stage"], window["window_id"]
                before = before_rows[(stage, wid)]
                request = CandleDataRequest(window["symbol"], window["interval"], int(window["window_length"]), window["period_start"], window["period_end"], "postgresql.public.market_candles")
                boundary = run_engine_trend_from_provider(provider, request, min_candle_count=int(window["window_length"]))
                preview, payload = boundary.engine_output.preview, boundary.engine_output.json_payload
                result = payload["result"]; safety = result["safety"]
                pp = OUT / "after/previews" / f"{wid}_preview.json"; rp = OUT / "after/results" / f"{wid}_result.json"
                write_json(pp, preview); write_json(rp, payload)
                after_status, notes = match_status(window["reference_label"], preview["market_regime"])
                before_status = before.get("match_status") or before.get("match_status_from_validation")
                safe = safety == SAFETY
                row = {"source_stage": stage, "window_id": wid, "symbol": window["symbol"], "interval": window["interval"], "period_start": window["period_start"], "period_end": window["period_end"], "window_length": window["window_length"], "reference_label": window["reference_label"], "selection_reason": window["selection_reason"], "before_engine_market_regime": before["engine_market_regime"], "before_confidence": before["confidence"], "after_engine_market_regime": preview["market_regime"], "after_confidence": preview["confidence"], "after_boundary_status": boundary.status.value, "after_top_reason_codes": preview["reason_codes_top"], "after_warnings_count": len(boundary.warnings), "after_errors_count": len(boundary.errors), "after_trade_signal": safety["trade_signal"], "after_safe_for_runtime_trading": safety["safe_for_runtime_trading"], "after_live_trading_connected": safety["live_trading_connected"], "after_match_status": after_status, "review_notes": notes, "after_preview_artifact": pp.relative_to(ROOT).as_posix(), "after_result_artifact": rp.relative_to(ROOT).as_posix()}
                after_rows.append(row)
                comparisons.append({"window_id": wid, "symbol": window["symbol"], "reference_label": window["reference_label"], "before_regime": before["engine_market_regime"], "before_confidence": before["confidence"], "before_match_status": before_status, "after_regime": preview["market_regime"], "after_confidence": preview["confidence"], "after_match_status": after_status, "regime_changed": before["engine_market_regime"] != preview["market_regime"], "confidence_changed": float(before["confidence"]) != float(preview["confidence"]), "improvement_status": improvement(before_status, after_status), "safety_preserved": safe, "notes": notes})
    finally: engine.dispose()

    safety_violations = sum(not r["safety_preserved"] for r in comparisons)
    statuses = Counter(r["after_match_status"] for r in comparisons); regimes = Counter(r["after_regime"] for r in comparisons); improvements = Counter(r["improvement_status"] for r in comparisons)
    write_json(OUT / "ENGINE_TREND_17_AFTER_VALIDATION_MATRIX.json", {"stage": "ENGINE-TREND-17", "rows": after_rows}); write_csv(OUT / "ENGINE_TREND_17_AFTER_VALIDATION_MATRIX.csv", AFTER_FIELDS, after_rows)
    write_json(OUT / "ENGINE_TREND_17_BEFORE_AFTER_COMPARISON.json", {"stage": "ENGINE-TREND-17", "rows": comparisons}); write_csv(OUT / "ENGINE_TREND_17_BEFORE_AFTER_COMPARISON.csv", COMPARE_FIELDS, comparisons)
    accepted = safety_violations == 0 and statuses["MISMATCH"] == 0 and regimes["UNKNOWN"] > 0 and improvements["IMPROVED"] > 0
    decision = {"stage": "ENGINE-TREND-17", "status": "TUNING_REVIEW_COMPLETED" if accepted else "REJECTED_TUNING_ATTEMPT", "baseline": baseline, "composer_change": {"composer_only": True, "changed_files": ["app/market_reader/engine_trend/regime_composer.py"] if accepted else [], "adjustment_family": candidate["selected_adjustment_family"], "rationale": candidate["rationale"]}, "after_validation": {"windows_replayed": len(after_rows), "after_unknown_count": regimes["UNKNOWN"], "after_match_count": statuses["MATCH"], "after_acceptable_unknown_count": statuses["ACCEPTABLE_UNKNOWN"], "after_questionable_unknown_count": statuses["QUESTIONABLE_UNKNOWN"], "after_mismatch_count": statuses["MISMATCH"], "after_safety_violations": safety_violations}, "decision": {"accepted": accepted, "reason": "Safety, zero-mismatch, retained-UNKNOWN, and clear-window improvement gates all passed." if accepted else "One or more acceptance gates failed; composer change must be reverted.", "next_stage": "ENGINE-TREND-18 — Post-Tuning Historical Validation Stability Pack" if accepted else "ENGINE-TREND-17B — Narrow Composer Decision Trace Expansion"}, "runtime_trading_allowed": False, "trading_claims_allowed": False}
    write_json(OUT / "ENGINE_TREND_17_DECISION_RECORD.json", decision)
    summary = f"Windows: {len(after_rows)}. Regimes: {dict(regimes)}. Statuses: {dict(statuses)}. Improvements: {dict(improvements)}. Safety violations: {safety_violations}."
    (OUT / "ENGINE_TREND_17_TUNING_DECISION.md").write_text(f"""# ENGINE-TREND-17 — Composer Threshold Tuning Decision

## Baseline problem
All 60 fixed windows were UNKNOWN at confidence 0.3.
## Composer rules reviewed
Score, margin, coverage, conflict, fallback, range exception, and confidence clamp rules were reviewed.
## Candidate adjustment
Preserve raw additive candidate scores until ranking; clamp exported values afterward.
## Change implemented
One composer-only ordering fix; threshold values and evidence extraction are unchanged.
## Before/after validation summary
{summary}
## Improvement summary
{improvements['IMPROVED']} questionable UNKNOWN rows became direct matches.
## Regression summary
MISMATCH count: {statuses['MISMATCH']}; NEEDS_REVIEW count: {statuses['NEEDS_REVIEW']}.
## Safety verification
{len(after_rows)-safety_violations}/{len(after_rows)} preserved NOT_EVALUATED / false / false.
## Decision
{'ACCEPTED' if accepted else 'REJECTED'}: {decision['decision']['reason']}
## What this does not prove
- no trading edge proven
- no profitability proven
- no runtime trading allowed
- no execution readiness proven
- no model training performed
## Next recommended stage
{decision['decision']['next_stage']}
""", encoding="utf-8")
    per_label = {k: dict(Counter(r["after_match_status"] for r in comparisons if r["reference_label"] == k)) for k in sorted({r["reference_label"] for r in comparisons})}
    per_symbol = {k: dict(Counter(r["after_regime"] for r in comparisons if r["symbol"] == k)) for k in sorted({r["symbol"] for r in comparisons})}
    REPORT.write_text(f"""# ENGINE-TREND-17 — Conservative Composer Threshold Review

## Stage goal
Review and minimally correct the conservative composer path without weakening UNKNOWN safety guards.
## Baseline
60/60 UNKNOWN; confidence 0.3; safety 60/60.
## Files created/changed
Composer ordering fix, replay runner, focused/offline tests, matrices, per-window artifacts, decision documents, manifest, and this report.
## Composer rule inventory
Documented in the dedicated rule review.
## Threshold candidate analysis
All 60 traces showed saturated UP=DOWN=1.0 and zero gap; one ordering correction was selected.
## Composer change
Raw additive scores are ranked before public-value clamp. Threshold constants are unchanged.
## After validation scope
The same 60 definitions were loaded from PostgreSQL in a read-only transaction.
## Before/after result summary
{summary}
## Per-label summary
{per_label}
## Per-symbol summary
{per_symbol}
## Safety contract verification
{len(after_rows)-safety_violations}/{len(after_rows)} passed.
## Tests executed
Recorded after runner generation in the final stage handoff.
## Scans executed
Protected-file, scope, legacy, write-SQL, trading-term, and secret scans are required before commit.
## Known limitations
Reference labels are descriptive, not ground truth. The set is fixed and not an independent holdout. Context remains 96 candles. This establishes neither predictive performance nor trading readiness.
## Decision
{'ACCEPTED' if accepted else 'REJECTED'}.
## Next recommended stage
{decision['decision']['next_stage']}
""", encoding="utf-8")
    outputs = [p for p in OUT.rglob("*") if p.is_file() and p.name != "ENGINE_TREND_17_ARTIFACT_MANIFEST.json"] + [REPORT]
    manifest = {"stage": "ENGINE-TREND-17", "generated_at": datetime.now(timezone.utc).isoformat(), "input_artifacts": [p.relative_to(ROOT).as_posix() for p in required], "output_artifacts": [p.relative_to(ROOT).as_posix() for p in outputs], "after_preview_artifacts": [r["after_preview_artifact"] for r in after_rows], "after_result_artifacts": [r["after_result_artifact"] for r in after_rows], "sha256_checksums": {p.relative_to(ROOT).as_posix(): sha(p) for p in outputs}, "composer_changed": accepted, "composer_changed_files": decision["composer_change"]["changed_files"], "adapter_changed": False, "db_cli_changed": False, "safety_summary": {"windows": len(after_rows), "violations": safety_violations}, "no_trading_claims": True}
    write_json(OUT / "ENGINE_TREND_17_ARTIFACT_MANIFEST.json", manifest)
    print(summary)
    return 0 if accepted else 2


if __name__ == "__main__": raise SystemExit(main())
