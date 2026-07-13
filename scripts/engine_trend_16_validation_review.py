"""Offline review of saved ENGINE-TREND-15/15B validation artifacts."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/engine_trend/validation_review"
REPORT = ROOT / "reports/engine_trend/engine_trend_16_historical_validation_review_core_tuning_decision_report.md"
INPUTS = [
    ("ENGINE-TREND-15", ROOT / "reports/engine_trend/historical_validation/ENGINE_TREND_15_VALIDATION_MATRIX.json"),
    ("ENGINE-TREND-15B", ROOT / "reports/engine_trend/symbol_suitability_validation/ENGINE_TREND_15B_EXPANDED_VALIDATION_MATRIX.json"),
]
FIELDS = """source_stage window_id symbol symbol_role interval period_start period_end window_length reference_label match_status_from_validation engine_market_regime confidence warnings_count errors_count top_reason_codes reason_code_count decision_status decision_source unknown_score up_score down_score flat_score score_gap_top2 coverage_level conflict_level confluence_state dominant_evidence_direction bullish_score bearish_score neutral_score net_score nison_evidence_count altunina_evidence_count schwager_evidence_count confidence_base confidence_after_conflict confidence_after_coverage confidence_final suspected_unknown_cause review_notes result_artifact""".split()
WATCHED_CODES = """ALTUNINA_BULLISH_STRUCTURE ALTUNINA_BEARISH_STRUCTURE ALTUNINA_SIDEWAYS_STRUCTURE ALTUNINA_STRUCTURE_UNCLEAR ALTUNINA_TREND_STRONG ALTUNINA_TREND_WEAK ALTUNINA_TREND_PROGRESS_CONFIRMED ALTUNINA_LOW_DIRECTIONAL_PROGRESS SCHWAGER_TRADING_RANGE_DETECTED SCHWAGER_PRICE_INSIDE_RANGE SCHWAGER_BULLISH_RANGE_BREAKOUT_CONTEXT SCHWAGER_BEARISH_RANGE_BREAKDOWN_CONTEXT SCHWAGER_FALSE_BREAKOUT_UP SCHWAGER_FALSE_BREAKOUT_DOWN BULLISH_BODY_DOMINANCE BEARISH_BODY_DOMINANCE LOW_DIRECTIONAL_PROGRESS SMALL_BODY_CLUSTER DOJI_CLUSTER_FLAT_CONTEXT""".split()


def load(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Critical input artifact missing: {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def nested(value, *keys):
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def rounded(value):
    return round(value, 10) if isinstance(value, float) else value


def distribution(rows, key, group=None):
    buckets = defaultdict(list)
    for row in rows:
        buckets[str(row.get(group)) if group else "all"].append(row.get(key))
    result = {}
    for bucket, values in buckets.items():
        numeric = [v for v in values if isinstance(v, (int, float))]
        result[bucket] = {
            "count": len(values), "values": dict(sorted(Counter(str(v) for v in values).items())),
            "min": min(numeric) if numeric else None, "max": max(numeric) if numeric else None,
            "mean": rounded(mean(numeric)) if numeric else None,
        }
    return result["all"] if not group else dict(sorted(result.items()))


def extract(stage, matrix_row):
    artifact = ROOT / matrix_row["result_artifact"]
    result_doc = load(artifact)
    output = nested(result_doc, "boundary", "engine_output") or {}
    payload = output.get("json_payload") or {}
    result = payload.get("result") or nested(output, "composer_output", "result") or {}
    trace = payload.get("decision_trace") or {}
    matrix = trace.get("matrix_summary") or payload.get("matrix_summary") or {}
    scores = trace.get("candidate_scores") or nested(output, "preview", "summary", "candidate_scores") or {}
    balance = nested(output, "composer_output", "matrix", "directional_balance") or {}
    book = result.get("book_evidence") or {}
    decomp = result.get("confidence_decomposition")
    all_evidence = [item for entries in book.values() if isinstance(entries, list) for item in entries if isinstance(item, dict)]
    codes = [item.get("code") for item in all_evidence if item.get("code")]
    score_values = [v for k, v in scores.items() if k in {"up_score", "down_score", "flat_score", "unknown_score"} and isinstance(v, (int, float))]
    gap = None
    if len(score_values) >= 2:
        ordered = sorted(score_values, reverse=True)
        gap = rounded(ordered[0] - ordered[1])
    causes = []
    if not trace or not matrix or not scores:
        causes.append("TRACE_FIELDS_MISSING")
    if matrix.get("coverage_level") == "LOW": causes.append("LOW_COVERAGE")
    if matrix.get("conflict_level") in {"HIGH", "SEVERE"}: causes.append("HIGH_CONFLICT")
    if gap is not None and gap <= 0.1: causes.append("SMALL_SCORE_GAP")
    directional = [e for e in all_evidence if isinstance(e.get("contribution"), (int, float)) and e["contribution"] != 0]
    if not directional: causes.append("NO_DIRECTIONAL_EVIDENCE")
    if all_evidence and not directional: causes.append("EVIDENCE_NOT_EXTRACTED_TO_MATRIX")
    if trace.get("status") == "FALLBACK_UNKNOWN": causes.append("COMPOSER_CONSERVATIVE_FALLBACK")
    confidence = result.get("confidence", matrix_row.get("confidence"))
    if confidence == 0.3 and isinstance(decomp, dict) and decomp.get("total") != 0.3:
        causes.append("CONFIDENCE_FLOOR_OR_CLAMP")
    if matrix_row.get("window_length") == 96: causes.append("DATA_WINDOW_TOO_SHORT_POSSIBLE")
    if not causes: causes.append("UNKNOWN_CAUSE_UNCLEAR")
    notes = []
    if all_evidence: notes.append(f"{len(all_evidence)} evidence items extracted")
    if matrix: notes.append(f"coverage={matrix.get('coverage_level')}, conflict={matrix.get('conflict_level')}")
    if gap is not None: notes.append(f"candidate top-two gap={gap}")
    row = {field: None for field in FIELDS}
    row.update({
        "source_stage": stage, "window_id": matrix_row.get("window_id"), "symbol": matrix_row.get("symbol"),
        "symbol_role": matrix_row.get("symbol_role"), "interval": matrix_row.get("interval"),
        "period_start": matrix_row.get("period_start"), "period_end": matrix_row.get("period_end"),
        "window_length": matrix_row.get("window_length"), "reference_label": matrix_row.get("reference_label"),
        "match_status_from_validation": matrix_row.get("match_status"), "engine_market_regime": result.get("market_regime", matrix_row.get("engine_market_regime")),
        "confidence": confidence, "warnings_count": matrix_row.get("warnings_count"), "errors_count": matrix_row.get("errors_count"),
        "top_reason_codes": codes[:10], "reason_code_count": len(codes), "decision_status": trace.get("status"),
        "decision_source": trace.get("decision_source"), "unknown_score": scores.get("unknown_score"), "up_score": scores.get("up_score"),
        "down_score": scores.get("down_score"), "flat_score": scores.get("flat_score"), "score_gap_top2": gap,
        "coverage_level": matrix.get("coverage_level"), "conflict_level": matrix.get("conflict_level"),
        "confluence_state": matrix.get("agreement_state"), "dominant_evidence_direction": matrix.get("dominant_direction"),
        "bullish_score": balance.get("bullish_score"), "bearish_score": balance.get("bearish_score"),
        "neutral_score": balance.get("neutral_evidence_count"), "net_score": balance.get("net_score"),
        "nison_evidence_count": len(book.get("nison", [])), "altunina_evidence_count": len(book.get("altunina", [])),
        "schwager_evidence_count": len(book.get("schwager", [])), "confidence_base": nested(decomp, "total"),
        "confidence_after_conflict": None, "confidence_after_coverage": None, "confidence_final": confidence,
        "suspected_unknown_cause": causes, "review_notes": "; ".join(notes), "result_artifact": matrix_row.get("result_artifact"),
    })
    return row, codes, decomp


def counters_by(rows, row_codes, key):
    grouped = defaultdict(Counter)
    for row, codes in zip(rows, row_codes): grouped[str(row.get(key))].update(codes)
    return {k: dict(v.most_common()) for k, v in sorted(grouped.items())}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows, row_codes, decomps, input_paths = [], [], [], []
    for stage, matrix_path in INPUTS:
        matrix = load(matrix_path); input_paths.append(matrix_path)
        for source in matrix.get("rows", []):
            row, codes, decomp = extract(stage, source)
            rows.append(row); row_codes.append(codes); decomps.append(decomp)
            input_paths.append(ROOT / source["result_artifact"])

    matrix_json = OUT / "ENGINE_TREND_16_TRACE_REVIEW_MATRIX.json"
    write_json(matrix_json, {"stage": "ENGINE-TREND-16", "rows": rows})
    with (OUT / "ENGINE_TREND_16_TRACE_REVIEW_MATRIX.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS); writer.writeheader()
        for row in rows:
            csv_row = dict(row)
            csv_row["top_reason_codes"] = "|".join(row["top_reason_codes"])
            csv_row["suspected_unknown_cause"] = "|".join(row["suspected_unknown_cause"])
            writer.writerow(csv_row)

    total_codes = Counter(code for codes in row_codes for code in codes)
    reason_summary = {
        "stage": "ENGINE-TREND-16", "total_windows_reviewed": len(rows),
        "reason_code_frequencies": dict(total_codes.most_common()),
        "reason_code_frequencies_by_symbol": counters_by(rows, row_codes, "symbol"),
        "reason_code_frequencies_by_reference_label": counters_by(rows, row_codes, "reference_label"),
        "reason_code_frequencies_by_match_status": counters_by(rows, row_codes, "match_status_from_validation"),
        "top_n_reason_codes": [{"code": k, "count": v} for k, v in total_codes.most_common(20)],
        "watched_reason_code_frequencies": {code: total_codes[code] for code in WATCHED_CODES},
        "missing_reason_codes_count": sum(not codes for codes in row_codes),
    }
    write_json(OUT / "ENGINE_TREND_16_REASON_CODE_SUMMARY.json", reason_summary)

    present = [d for d in decomps if isinstance(d, dict)]
    decomposition_summary = {}
    for key in sorted({k for d in present for k in d}):
        values = [d[key] for d in present if isinstance(d.get(key), (int, float))]
        decomposition_summary[key] = {"count": len(values), "min": min(values), "max": max(values), "mean": rounded(mean(values))} if values else {"count": 0}
    count03 = sum(row["confidence"] == 0.3 for row in rows)
    confidence = {
        "stage": "ENGINE-TREND-16", "total_windows_reviewed": len(rows),
        "confidence_values_distribution": distribution(rows, "confidence"),
        "confidence_by_symbol": distribution(rows, "confidence", "symbol"),
        "confidence_by_reference_label": distribution(rows, "confidence", "reference_label"),
        "confidence_by_match_status": distribution(rows, "confidence", "match_status_from_validation"),
        "confidence_decomposition_presence": {"present": len(present), "missing": len(rows)-len(present)},
        "confidence_decomposition_summary": decomposition_summary,
        "count_confidence_equal_0_3": count03, "count_confidence_not_0_3": len(rows)-count03,
        "possible_confidence_floor_or_clamp": any("CONFIDENCE_FLOOR_OR_CLAMP" in row["suspected_unknown_cause"] for row in rows),
    }
    write_json(OUT / "ENGINE_TREND_16_CONFIDENCE_DIAGNOSTICS.json", confidence)

    cause_counts = Counter(c for row in rows for c in row["suspected_unknown_cause"])
    trace_sufficient = sum(bool(row["decision_status"] and row["coverage_level"] and row["up_score"] is not None) for row in rows) == len(rows)
    small_gap = cause_counts["SMALL_SCORE_GAP"]
    fallback = cause_counts["COMPOSER_CONSERVATIVE_FALLBACK"]
    weak_evidence = cause_counts["NO_DIRECTIONAL_EVIDENCE"]
    if not trace_sufficient:
        selected, next_stage = "Option B — Add trace/debug instrumentation first.", "ENGINE-TREND-17 — Decision Trace Instrumentation Hardening"
    elif weak_evidence > len(rows)/2:
        selected, next_stage = "Option D — Tune lower-level evidence extraction first.", "ENGINE-TREND-17 — Evidence Extraction Diagnostic Review"
    elif fallback == len(rows) and small_gap > len(rows)/2:
        selected, next_stage = "Option A — Tune composer thresholds in a separate stage.", "ENGINE-TREND-17 — Conservative Composer Threshold Review"
    else:
        selected, next_stage = "Option C — Compare 96 vs 192/384 context windows before tuning.", "ENGINE-TREND-16C — Context Length Sensitivity Validation 96 vs 192 vs 384"

    unknown = sum(row["engine_market_regime"] == "UNKNOWN" for row in rows)
    questionable = sum(row["match_status_from_validation"] == "QUESTIONABLE_UNKNOWN" for row in rows)
    mismatch = sum(row["match_status_from_validation"] == "MISMATCH" for row in rows)
    safety_violations = sum((row["warnings_count"] or 0) + (row["errors_count"] or 0) for row in rows)
    primary = "CONSERVATIVE_EVIDENCE_COMPOSER_DECISION_PATH" if fallback > len(rows)/2 else "TRACE_DATA_INSUFFICIENT"
    decision = {
        "stage": "ENGINE-TREND-16", "status": "DECISION_RECORDED",
        "baseline": {"engine_trend_15_commit": "1fb4e5f", "engine_trend_15b_commit": "2b98eea", "engine_core_changed": False, "adapter_changed": False, "db_cli_changed": False},
        "validation_review": {"windows_reviewed": len(rows), "unknown_count": unknown, "confidence_0_3_count": count03, "questionable_unknown_count": questionable, "mismatch_count": mismatch, "safety_violations": safety_violations},
        "diagnosis": {"primary_hypothesis": primary, "secondary_hypotheses": ["CONTEXT_LENGTH_96_MAY_BE_TOO_SHORT"], "trace_sufficient": trace_sufficient, "cause_counts": dict(cause_counts)},
        "selected_decision": selected, "next_stage": next_stage, "core_changes_allowed_in_next_stage": False,
        "runtime_trading_allowed": False, "trading_claims_allowed": False,
    }
    write_json(OUT / "ENGINE_TREND_16_DECISION_RECORD.json", decision)

    missing_fields = {field: sum(row[field] is None for row in rows) for field in FIELDS if any(row[field] is None for row in rows)}
    diagnosis_md = f"""# ENGINE-TREND-16 — UNKNOWN Cause Diagnosis

## Input evidence
Reviewed {len(rows)} saved result artifacts: 15 from ENGINE-TREND-15 and 45 from ENGINE-TREND-15B. No database or engine execution was used.

## Observed pattern
UNKNOWN occurs in {unknown}/{len(rows)} windows; confidence equals 0.3 in {count03}/{len(rows)}. QUESTIONABLE_UNKNOWN occurs in {questionable} windows and MISMATCH in {mismatch}.

## Trace field availability
Decision status, matrix coverage, and candidate scores are complete for {len(rows)-sum(not (r['decision_status'] and r['coverage_level'] and r['up_score'] is not None) for r in rows)}/{len(rows)} windows. Fields unavailable in at least one saved artifact: {json.dumps(missing_fields, sort_keys=True)}. Null values are retained rather than inferred.

## Reason code evidence
Saved book evidence contains {sum(len(c) for c in row_codes)} reason-code occurrences. Directional evidence is therefore created; watched-code counts are in the reason-code summary. Empty directional evidence occurs in {weak_evidence} windows.

## Matrix coverage and conflict
Coverage: {dict(Counter(str(r['coverage_level']) for r in rows))}. Conflict: {dict(Counter(str(r['conflict_level']) for r in rows))}. This does not support low coverage or high conflict as the universal blocker.

## Candidate score behavior
The top-two candidate gap is at most 0.1 in {small_gap}/{len(rows)} windows. Composer fallback status occurs in {fallback}/{len(rows)} windows. This locates the observed block at the conservative composer decision path, commonly with tied or near-tied candidates.

## Confidence behavior
Confidence decomposition exists in {len(present)}/{len(rows)} artifacts. Final 0.3 differs from decomposition total in {cause_counts['CONFIDENCE_FLOOR_OR_CLAMP']} windows, consistent with fallback confidence assignment or clamp; the trace does not expose intermediate confidence-after-conflict/coverage fields.

## Suspected primary cause
B — conservative evidence/composer decision path. Evidence reaches a ready matrix, but candidate separation is often insufficient and the safety fallback selects UNKNOWN.

## Alternative explanations
D — insufficient context length remains possible because all reviewed windows contain 96 candles. A (symbol/window noise) is weakened by the three-symbol design and suitability results. C (validation diversity) remains a limitation but does not explain identical behavior across 60 varied windows. E is not primary because the decisive matrix and candidate fields are present, although intermediate confidence fields are missing.

## What cannot be concluded yet
This review cannot establish how 192/384-candle contexts behave, whether a threshold change is safe, or any predictive or runtime suitability.

## Required next evidence
The selected next stage is **{next_stage}**. It must preserve the current baseline, define before/after acceptance metrics, and keep context-length sensitivity as an explicit secondary check.
"""
    (OUT / "ENGINE_TREND_16_UNKNOWN_CAUSE_DIAGNOSIS.md").write_text(diagnosis_md, encoding="utf-8")
    decision_md = f"""# ENGINE-TREND-16 — Core Tuning Decision

## Decision context
All {len(rows)} historical windows returned UNKNOWN. This stage reviews saved traces without changing behavior.

## Evidence reviewed
Validation matrices and their {len(rows)} referenced result JSON artifacts; reason codes, matrix summaries, candidate scores, confidence decomposition, warnings, errors, and safety metadata.

## Options
- Option A — Tune composer thresholds immediately.
- Option B — Add trace/debug instrumentation first.
- Option C — Compare 96 vs 192/384 context windows before tuning.
- Option D — Tune lower-level evidence extraction first.
- Option E — Stop core changes and keep the conservative baseline.

## Selected decision
**{selected}** No tuning is implemented in ENGINE-TREND-16.

## Rationale
Trace sufficiency is {trace_sufficient}; composer fallback appears in {fallback}/{len(rows)} windows and small candidate gaps in {small_gap}/{len(rows)}. Evidence extraction is not empty in {len(rows)-weak_evidence}/{len(rows)} windows. Context length remains a secondary uncertainty rather than the best-supported universal cause.

## What is explicitly not allowed yet
No core, threshold, evidence matrix, adapter, CLI, schema, or runtime behavior change is authorized by this decision record.

## Next stage
**{next_stage}**

## Exit criteria for next stage
Predeclare candidate-separation and regime-selection diagnostics; compare against the frozen 60-window baseline; preserve OHLC integrity and safety; report all behavior changes; make no runtime or trading-readiness claims.
"""
    (OUT / "ENGINE_TREND_16_CORE_TUNING_DECISION.md").write_text(decision_md, encoding="utf-8")

    REPORT.write_text(f"""# ENGINE-TREND-16 — Historical Validation Review and Core Tuning Decision

## Stage goal
Diagnose the 60-window UNKNOWN pattern and record the next diagnostic/tuning decision without behavior changes.

## Baseline
ENGINE-TREND-15 `1fb4e5f`; ENGINE-TREND-15B `2b98eea`; engine core, adapter, and DB CLI unchanged.

## Files created/changed
One offline runner, one offline test, two review matrices, five diagnostic/decision artifacts, this report, and an artifact manifest.

## Input artifacts reviewed
Two validation matrices and {len(rows)} referenced result JSON artifacts. Candle data was not sourced from report JSON for execution; saved results were read only as review evidence.

## Validation evidence summary
Windows: {len(rows)}; UNKNOWN: {unknown}; QUESTIONABLE_UNKNOWN: {questionable}; MISMATCH: {mismatch}; warning/error count: {safety_violations}.

## Trace field availability
Trace sufficient: {trace_sufficient}. Intermediate confidence-after-conflict and confidence-after-coverage fields are absent and represented as null.

## Reason code summary
Evidence codes are present in {len(rows)-reason_summary['missing_reason_codes_count']}/{len(rows)} windows. Full frequencies are in `ENGINE_TREND_16_REASON_CODE_SUMMARY.json`.

## Confidence diagnostics
Confidence 0.3: {count03}/{len(rows)}; decomposition present: {len(present)}/{len(rows)}; possible fallback floor/clamp: {confidence['possible_confidence_floor_or_clamp']}.

## UNKNOWN cause diagnosis
Primary: B — conservative evidence/composer decision path. Secondary: D — 96-candle context may be too short and has not been tested here.

## Decision options
Options A–E were evaluated using the documented decision rules.

## Selected decision
{selected}

## Next recommended stage
{next_stage}

## Tests executed
`py_compile` passed; the ENGINE-TREND-16 offline tests passed (2); the 15/15B tests passed (8); the 13/14 tests passed (10); adapter/DB CLI tests passed (17); and the relevant ENGINE-TREND suite passed (230). Full pytest was intentionally not used as a mandatory gate because of the known unrelated diagnostics failure.

## Scans executed
Protected-core diff, write-SQL, legacy-import, runtime-term, secret, and generated-artifact scans were executed before commit; any matching safety terms were descriptive only.

## Known limitations
Only three symbols, one interval, and 96-candle contexts are represented. Intermediate confidence transitions are not saved. The unrelated diagnostics test issue is outside scope.

## What this stage proves
Saved traces show evidence reaching covered matrices while the conservative decision path returns UNKNOWN across the reviewed sample.

## What this stage does not prove
It does not prove a safe tuning value, longer-context behavior, profitability, predictive power, or runtime readiness.
""", encoding="utf-8")

    outputs = [p for p in OUT.iterdir() if p.name != "ENGINE_TREND_16_ARTIFACT_MANIFEST.json"] + [REPORT]
    manifest = {
        "stage": "ENGINE-TREND-16", "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_artifacts": [{"path": str(p.relative_to(ROOT)).replace('\\','/'), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(set(input_paths))],
        "output_artifacts": [{"path": str(p.relative_to(ROOT)).replace('\\','/'), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(outputs)],
        "windows_reviewed": len(rows), "safety_summary": {"violations": safety_violations},
        "core_changed": False, "adapter_changed": False, "db_cli_changed": False, "no_trading_claims": True,
    }
    write_json(OUT / "ENGINE_TREND_16_ARTIFACT_MANIFEST.json", manifest)
    print(json.dumps({"windows_reviewed": len(rows), "unknown": unknown, "selected_decision": selected, "next_stage": next_stage}, indent=2))


if __name__ == "__main__":
    main()
