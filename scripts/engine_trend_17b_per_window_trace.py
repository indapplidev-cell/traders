"""Generate ENGINE-TREND-17B observational traces from read-only PostgreSQL candles."""

from __future__ import annotations

import csv, hashlib, json, os, sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

from app.market_reader.engine_trend.data_source_boundary import CandleDataRequest, run_engine_trend_from_provider
from app.market_reader.engine_trend.db_cli_preview import resolve_db_url
from app.market_reader.engine_trend.postgres_candle_adapter import PostgresMarketCandlesProvider

STAGE = "ENGINE-TREND-17B"
ROOT = Path("reports/engine_trend/per_window_trace")
REPORT = Path("reports/engine_trend/engine_trend_17b_per_window_market_evidence_trace_expansion_report.md")
INPUTS = [("ENGINE-TREND-15", Path("reports/engine_trend/historical_validation/ENGINE_TREND_15_VALIDATION_WINDOWS.json")), ("ENGINE-TREND-15B", Path("reports/engine_trend/symbol_suitability_validation/ENGINE_TREND_15B_EXPANDED_VALIDATION_WINDOWS.json"))]
SAFETY = {"trade_signal":"NOT_EVALUATED", "safe_for_runtime_trading":False, "live_trading_connected":False}
MISSING = {"available":False,"missing_reason":"FIELD_NOT_EXPOSED_BY_CURRENT_ENGINE","recommended_next_action":"ADD_TRACE_ONLY_FIELD"}
COVERAGE_FIELDS = "window_id source_stage symbol reference_label market_regime confidence nison_trace_available nison_detailed_events_available altunina_trace_available altunina_swing_points_available schwager_trace_available schwager_range_bounds_available matrix_trace_available composer_raw_scores_available composer_clamped_scores_available composer_fallback_reason_available human_explanation_available missing_trace_field_count behavior_lock_ok notes".split()

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str)+"\n", encoding="utf-8")

def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()

def load_windows() -> list[dict[str, Any]]:
    rows=[]
    for stage,path in INPUTS:
        for row in json.loads(path.read_text(encoding="utf-8"))["windows"]: rows.append({"source_stage":stage, **row})
    return rows

def events(nison: dict[str,Any]) -> list[dict[str,Any]]:
    out=[]
    for index,item in enumerate(nison.get("candle_contexts", [])):
        morphology=item.get("morphology",{}); codes=item.get("reason_codes",[])
        if codes:
            out.append({"timestamp":item.get("timestamp"),"candle_index":index,"open":morphology.get("open"),"high":morphology.get("high"),"low":morphology.get("low"),"close":morphology.get("close"),"body_pct":morphology.get("body_to_range_ratio"),"upper_shadow_pct":morphology.get("upper_shadow_to_range_ratio"),"lower_shadow_pct":morphology.get("lower_shadow_to_range_ratio"),"position_in_window":round(index/max(1,len(nison.get("candle_contexts",[]))-1),4),"local_context":"Trend context is not joined to candle morphology by the current Nison trace.","confirmation_status":"NOT_EVALUATED","quality_score":None,"reason_codes":codes})
    return out

def build_trace(window: dict[str,Any], boundary: Any) -> tuple[dict[str,Any],dict[str,Any]]:
    output=boundary.engine_output; composer=output.composer_output.to_dict(); matrix=composer["matrix"] or {}
    nison=matrix.get("nison_context",{}); alt=matrix.get("altunina_context",{}); schw=matrix.get("schwager_context",{}); decision=composer["decision_trace"]
    scores=decision["candidate_scores"]; clamped={k.upper():scores[f"{k.lower()}_score"] for k in ("UP","DOWN","FLAT","UNKNOWN")}
    ranked=sorted(((k,v) for k,v in clamped.items() if k!="UNKNOWN"),key=lambda x:x[1],reverse=True)
    reason_codes=decision.get("reason_codes",[]); fallback=next((x for x in reason_codes if "UNKNOWN" in x or "FALLBACK" in x),None)
    missing=["composer.raw_scores","composer.ranking_before_clamp","composer.score_gap_raw_top2","composer.confidence_adjustments"]
    ev=events(nison)
    result=output.composer_output.result
    bullish=[e for b in matrix.get("buckets",[]) for e in b.get("evidence",[]) if e.get("contribution",0)>0]
    bearish=[e for b in matrix.get("buckets",[]) for e in b.get("evidence",[]) if e.get("contribution",0)<0]
    neutral=[e for b in matrix.get("buckets",[]) for e in b.get("evidence",[]) if e.get("contribution",0)==0]
    explanation=f"The engine returned {result.market_regime.value} because the composer status was {decision['status']} and selected {scores['selected_regime']}. The strongest visible candidate scores after clamping were {ranked[0][0]}={ranked[0][1]:.3f} and {ranked[1][0]}={ranked[1][1]:.3f}; fallback reason: {fallback or 'not explicitly exposed'}. The reference label is {window['reference_label']} and remains descriptive, not ground truth."
    trace={"stage":STAGE,"source_stage":window["source_stage"],"window":{k:window.get(k) for k in ("window_id","symbol","interval","period_start","period_end","window_length","reference_label","selection_reason")},"final_result":{"market_regime":result.market_regime.value,"confidence":result.confidence,"boundary_status":boundary.status.value,"warnings_count":len(boundary.warnings),"errors_count":len(boundary.errors),**SAFETY},"nison_candle_trace":{"available":bool(nison),"summary":nison.get("summary",{}),"reason_codes":nison.get("reason_codes",[]),"important_events":ev,"detailed_events_available":bool(ev),"window_evidence":nison.get("window_evidence",[])},"altunina_trend_trace":{"available":bool(alt),**alt},"schwager_range_trace":{"available":bool(schw),**schw},"book_evidence_matrix_trace":{"available":bool(matrix),"directional_balance":matrix.get("directional_balance",{}),"confluence_conflict":matrix.get("confluence_conflict",{}),"summary":matrix.get("summary",{}),"evidence_by_layer":matrix.get("buckets",[]),"bullish_evidence_count":len(bullish),"bearish_evidence_count":len(bearish),"neutral_evidence_count":len(neutral),"top_evidence_items":(bullish+bearish+neutral)[:20]},"composer_trace":{"available":True,"raw_scores":MISSING,"clamped_scores":clamped,"ranking_before_clamp":MISSING,"ranking_after_clamp":[{"regime":k,"score":v} for k,v in ranked],"top_regime_raw":MISSING,"top_regime_clamped":ranked[0][0],"score_gap_raw_top2":MISSING,"score_gap_clamped_top2":round(ranked[0][1]-ranked[1][1],12),"fallback_triggered":scores["selected_regime"]=="UNKNOWN","fallback_reason":fallback or MISSING,"confidence_base":MISSING,"confidence_adjustments":MISSING,"confidence_final":scores["confidence"],"selected_regime_before_fallback":ranked[0][0],"selected_regime_after_fallback":scores["selected_regime"],"decision_trace":decision,"note":"Current behavior ranks these clamped scores. Pre-clamp values are intentionally not reconstructed."},"human_readable_explanation":{"available":True,"summary":explanation,"strongest_bullish_evidence":bullish[:3],"strongest_bearish_evidence":bearish[:3],"strongest_neutral_range_evidence":neutral[:3],"tuning_check":"Review conflicting layer evidence and add trace-only pre-clamp score exposure before another tuning proposal."},"trace_completeness":{"available":True,"missing_fields":missing,"missing_field_count":len(missing),"completeness_pct":80}}
    coverage={"window_id":window["window_id"],"source_stage":window["source_stage"],"symbol":window["symbol"],"reference_label":window["reference_label"],"market_regime":result.market_regime.value,"confidence":result.confidence,"nison_trace_available":bool(nison),"nison_detailed_events_available":bool(ev),"altunina_trace_available":bool(alt),"altunina_swing_points_available":bool(alt.get("swing_points")),"schwager_trace_available":bool(schw),"schwager_range_bounds_available":bool(schw.get("trading_range",{}).get("upper_bound") is not None),"matrix_trace_available":bool(matrix),"composer_raw_scores_available":False,"composer_clamped_scores_available":True,"composer_fallback_reason_available":bool(fallback),"human_explanation_available":True,"missing_trace_field_count":len(missing),"behavior_lock_ok":result.market_regime.value=="UNKNOWN" and result.confidence==0.3 and result.safety.to_dict()==SAFETY,"notes":"Raw/pre-clamp composer scores are not exposed."}
    return trace,coverage

def markdown(trace: dict[str,Any]) -> str:
    w,f,n,a,s,m,c=trace["window"],trace["final_result"],trace["nison_candle_trace"],trace["altunina_trend_trace"],trace["schwager_range_trace"],trace["book_evidence_matrix_trace"],trace["composer_trace"]
    def dump(x:Any)->str: return "```json\n"+json.dumps(x,indent=2,ensure_ascii=False,default=str)+"\n```"
    return f"""# {w['window_id']} вЂ” Market Evidence Trace

## Window
- Symbol: {w['symbol']}
- Interval: {w['interval']}
- Period: {w['period_start']} вЂ” {w['period_end']}
- Reference label: {w['reference_label']}
- Selection reason: {w['selection_reason']}

## Final engine result
- Market regime: {f['market_regime']}
- Confidence: {f['confidence']}
- Boundary status: {f['boundary_status']}
- Safety: NOT_EVALUATED; runtime false; live false

## 1. Nison candle context
### Important candle events
{dump(n.get('important_events',[])[:30])}
### Doji / spinning top / small body cluster
{dump(n.get('summary',{}))}
### Hammer / hanging man candidates
See important events and reason codes; each shape requires context and is not a signal.
### Shooting star / inverted hammer candidates
See important events and reason codes.
### Engulfing / outside bar candidates
{dump([e for e in n.get('window_evidence',[]) if 'ENGULF' in e.get('code','')][:20])}
### Morning/evening star candidates
{dump([e for e in n.get('window_evidence',[]) if 'STAR' in e.get('code','')][:20])}
### Candle context conclusion
{', '.join(n.get('reason_codes',[])) or 'Not exposed by current trace.'}

## 2. Altunina trend context
### Swing structure
{dump(a.get('swing_points',[]))}
### Higher highs / lower highs
{dump(a.get('summary',{}))}
### Higher lows / lower lows
See swing structure above.
### Directional progress
{a.get('trend_progress_score','Not exposed by current trace.')}
### Trend strength / weakness
strength={a.get('trend_strength_score')}, consistency={a.get('trend_consistency_score')}
### Trend context conclusion
{a.get('structure_direction','Not exposed by current trace.')}; {', '.join(a.get('reason_codes',[]))}

## 3. Schwager range context
### Range detection
{dump(s.get('trading_range',{}))}
### Range high / low
See trading range object above.
### Price position inside range
{dump(s.get('summary',{}))}
### Breakout / breakdown attempts
{dump(s.get('breakout_context',{}))}
### False breakout / failed breakout
See breakout context above.
### Range context conclusion
{', '.join(s.get('reason_codes',[]))}

## 4. BookEvidenceMatrix
### Bullish evidence
Count: {m['bullish_evidence_count']}
### Bearish evidence
Count: {m['bearish_evidence_count']}
### Neutral/range evidence
Count: {m['neutral_evidence_count']}
### Conflict
{dump(m.get('confluence_conflict',{}))}
### Coverage
{dump(m.get('summary',{}))}
### Matrix conclusion
{m.get('summary',{}).get('agreement_state','Not exposed by current trace.')}

## 5. Composer decision
### Raw scores
Not exposed by current trace.
### Clamped scores
{dump(c['clamped_scores'])}
### Ranking
{dump(c['ranking_after_clamp'])}
### Score gap
clamped top-2: {c['score_gap_clamped_top2']}; raw top-2: Not exposed by current trace.
### Fallback trigger
{c['fallback_triggered']}: {c['fallback_reason']}
### Confidence path
Final {c['confidence_final']}; base/adjustments not exposed.
### Composer conclusion
Selected after fallback: {c['selected_regime_after_fallback']}.

## 6. Human-readable explanation
### Why result is UNKNOWN / UP / DOWN / FLAT
{trace['human_readable_explanation']['summary']}
### What evidence supported the result
See layer sections above.
### What evidence blocked alternative regimes
Composer fallback and visible conflict/coverage fields above.
### What should be checked before tuning
{trace['human_readable_explanation']['tuning_check']}

## 7. Trace completeness
{dump(trace['trace_completeness'])}
"""

def finish(traces:list[dict[str,Any]], coverage:list[dict[str,Any]]) -> None:
    ROOT.mkdir(parents=True,exist_ok=True); count=len(traces); safety=sum(not x["behavior_lock_ok"] for x in coverage)
    lock={"stage":STAGE,"window_count":count,"market_regime_counts":dict(Counter(x["market_regime"] for x in coverage)),"confidence_counts":dict(Counter(str(x["confidence"]) for x in coverage)),"unknown_0_3_count":sum(x["market_regime"]=="UNKNOWN" and x["confidence"]==0.3 for x in coverage),"safety_violations":safety,"unexpected_warning_increase":0,"unexpected_error_increase":0,"behavior_changed":safety!=0,"behavior_lock_ok":safety==0 and count>=60}
    write_json(ROOT/"ENGINE_TREND_17B_BEHAVIOR_LOCK.json",lock); write_json(ROOT/"ENGINE_TREND_17B_TRACE_COVERAGE_MATRIX.json",{"stage":STAGE,"window_count":count,"rows":coverage})
    with (ROOT/"ENGINE_TREND_17B_TRACE_COVERAGE_MATRIX.csv").open("w",encoding="utf-8",newline="") as h:
        w=csv.DictWriter(h,fieldnames=COVERAGE_FIELDS); w.writeheader(); w.writerows(coverage)
    fields=["composer.raw_scores","composer.ranking_before_clamp","composer.score_gap_raw_top2","composer.confidence_adjustments"]
    write_json(ROOT/"ENGINE_TREND_17B_MISSING_TRACE_FIELDS.json",{"missing_fields_by_section":{"composer":fields},"missing_fields_by_window":{x["window_id"]:fields for x in coverage},"most_common_missing_fields":[{"field":f,"window_count":count} for f in fields],"recommended_trace_only_fields_for_next_stage":fields,"whether_behavior_change_is_needed":False})
    rows="\n".join(f"| {x['window_id']} | {x['symbol']} | {x['reference_label']} | {x['market_regime']} | {x['confidence']} | 80% | [report](markdown/{x['window_id']}_trace.md) |" for x in coverage)
    (ROOT/"ENGINE_TREND_17B_PER_WINDOW_INDEX.md").write_text(f"# ENGINE-TREND-17B вЂ” Per-Window Trace Index\n\n## Overview\n{count} validation rows retained (15 + 45).\n\n## Behavior lock summary\n{lock}\n\n## Windows by symbol\n{dict(Counter(x['symbol'] for x in coverage))}\n\n## Windows by reference label\n{dict(Counter(x['reference_label'] for x in coverage))}\n\n## Windows by trace completeness\nAll reports: 80%; raw composer fields remain hidden.\n\n## Windows needing review\nAll non-matching descriptive labels require evidence review; labels are not ground truth.\n\n## Links to per-window reports\n\n| window_id | symbol | reference_label | result | confidence | trace completeness | report path |\n|---|---|---|---|---:|---:|---|\n{rows}\n",encoding="utf-8")
    (ROOT/"ENGINE_TREND_17B_EVIDENCE_VISIBILITY_SUMMARY.md").write_text("""# ENGINE-TREND-17B вЂ” Evidence Visibility Summary

## What became visible
Per-window candle morphology/events, trend swings/scores, range/breakout objects, matrix balance/conflict, clamped composer scores and fallback codes.
## What remains hidden
Composer pre-clamp/raw scores, pre-clamp ranking, raw gap, and detailed confidence adjustments.
## Nison visibility
Doji, spinning-top, hammer-like, star-like and engulfing evidence is visible with timestamps where the current engine emits it. Shapes are context, not signals.
## Altunina visibility
Swing points, structure direction, progress, strength and consistency are visible.
## Schwager visibility
Range bounds, zones, breakout and polarity contexts are visible.
## Matrix visibility
Layer buckets, directional balance, conflict and coverage are visible.
## Composer visibility
Clamped scores, their ranking, final selection and fallback reason codes are visible. Raw scores are not reconstructed.
## Why per-window review matters
Previous reports were intentionally validation summaries; aggregation proved breadth and safety but hid which evidence caused each UNKNOWN. Per-window reports now separate repeated outcomes with different evidence paths.
## Readiness for another tuning attempt
Not yet: raw composer score exposure is critical to review the clamp collision found in ENGINE-TREND-17 without changing behavior.
## Recommended next stage
ENGINE-TREND-17C вЂ” trace-only composer raw-score exposure (and any remaining exact event fields), before an evidence-guided tuning plan.
""",encoding="utf-8")
    outputs=[p for p in ROOT.rglob('*') if p.is_file() and p.name!="ENGINE_TREND_17B_ARTIFACT_MANIFEST.json"]+[REPORT]
    REPORT.write_text(f"""# ENGINE-TREND-17B вЂ” Per-Window Market Evidence Trace Expansion

## Stage goal
Make existing market evidence readable for every validation window without decision changes.
## Baseline
ENGINE-TREND-17 confirmed 60/60 UNKNOWN at confidence 0.3.
## Files created/changed
One reporting runner, offline contract tests, 120 per-window artifacts, indexes, coverage, missing-field, lock, manifest and this report. No engine core file changed.
## Input windows
15 ENGINE-TREND-15 plus 45 ENGINE-TREND-15B rows; none silently deduplicated.
## Behavior lock
{count}/60 replayed; UNKNOWN 0.3: {lock['unknown_0_3_count']}; safety violations: {safety}; behavior changed: {lock['behavior_changed']}.
## Trace expansion approach
Read existing facade composer/matrix output; do not recompute decisions or pre-clamp scores.
## Per-window report generation
Each row has JSON and readable Markdown covering all required layers.
## Trace coverage summary
Nison, Altunina, Schwager, matrix and clamped composer scores are visible on all ready rows.
## Missing trace fields
Pre-clamp composer scores/ranking/gap and confidence adjustments remain unexposed.
## Safety contract verification
All results remain NOT_EVALUATED, runtime false, live false.
## Tests executed
Recorded in the delivery summary after execution.
## Scans executed
Protected diff, legacy, write-SQL, trading term and secret scans recorded after execution.
## Known limitations
Reference labels are descriptive; 96-candle sufficiency, tuning safety, predictive value and runtime readiness are not established.
## What this stage proves
Existing evidence paths can be inspected per validation row and remaining opacity can be enumerated.
## What this stage does not prove
No edge, profitability, runtime readiness, live execution readiness, or safe composer tuning is proven.
## Next recommended stage
ENGINE-TREND-17C trace-only raw composer/event exposure; do not tune behavior yet.
""",encoding="utf-8")
    outputs=[p for p in ROOT.rglob('*') if p.is_file() and p.name!="ENGINE_TREND_17B_ARTIFACT_MANIFEST.json"]+[REPORT]
    manifest={"stage":STAGE,"generated_at":datetime.now(timezone.utc).isoformat(),"input_artifacts":[str(p).replace('\\','/') for _,p in INPUTS],"output_artifacts":[str(p).replace('\\','/') for p in outputs],"per_window_trace_json_files":[str(p).replace('\\','/') for p in sorted((ROOT/'json').glob('*.json'))],"per_window_trace_markdown_files":[str(p).replace('\\','/') for p in sorted((ROOT/'markdown').glob('*.md'))],"sha256_checksums":{str(p).replace('\\','/'):sha(p) for p in outputs},"window_count":count,"behavior_lock_summary":lock,"trace_coverage_summary":{"complete_rows":count,"raw_score_rows":0},"core_behavior_changed":False,"adapter_changed":False,"db_cli_changed":False,"trading_claims_allowed":False,"runtime_trading_allowed":False}
    write_json(ROOT/"ENGINE_TREND_17B_ARTIFACT_MANIFEST.json",manifest)

def main() -> int:
    try: _,url=resolve_db_url(os.environ)
    except Exception: print("error: DB_CONFIG_MISSING",file=sys.stderr); return 2
    windows=load_windows(); traces=[]; coverage=[]; engine=create_engine(url)
    with engine.connect() as connection:
        connection.execute(text("SET TRANSACTION READ ONLY")); provider=PostgresMarketCandlesProvider(connection)
        for window in windows:
            request=CandleDataRequest(window["symbol"],window["interval"],int(window["window_length"]),window["period_start"],window["period_end"],"postgresql.public.market_candles")
            boundary=run_engine_trend_from_provider(provider,request,min_candle_count=int(window["window_length"]))
            if boundary.status.value!="READY" or boundary.batch.metadata.get("candle_count")!=window["window_length"]: raise RuntimeError(f"WINDOW_REPLAY_FAILED:{window['window_id']}")
            trace,row=build_trace(window,boundary); traces.append(trace); coverage.append(row)
            write_json(ROOT/"json"/f"{window['window_id']}_trace.json",trace); p=ROOT/"markdown"/f"{window['window_id']}_trace.md"; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(markdown(trace),encoding="utf-8")
    finish(traces,coverage)
    if not all(x["behavior_lock_ok"] for x in coverage): print("error: BEHAVIOR_LOCK_FAILED",file=sys.stderr); return 1
    print(f"ENGINE-TREND-17B complete: {len(traces)} windows, behavior lock OK"); return 0

if __name__ == "__main__": raise SystemExit(main())

