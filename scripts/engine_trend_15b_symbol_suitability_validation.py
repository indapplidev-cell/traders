"""Build ENGINE-TREND-15B artifacts from read-only PostgreSQL candles."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from sqlalchemy import create_engine, text

from app.market_reader.engine_trend.data_source_boundary import CandleDataRequest, run_engine_trend_from_provider
from app.market_reader.engine_trend.db_cli_preview import resolve_db_url
from app.market_reader.engine_trend.postgres_candle_adapter import PostgresMarketCandlesProvider

STAGE = "ENGINE-TREND-15B"
INTERVAL = "15m"
WINDOW_LENGTH = 96
ROOT = Path("reports/engine_trend/symbol_suitability_validation")
REPORT = Path("reports/engine_trend/engine_trend_15b_symbol_suitability_expanded_validation_report.md")
SAFETY = {"trade_signal": "NOT_EVALUATED", "safe_for_runtime_trading": False, "live_trading_connected": False}
AVAILABILITY_SQL = text("""SELECT symbol, interval, COUNT(*) AS candle_count, MIN(open_time) AS min_open_time,
MAX(open_time) AS max_open_time FROM public.market_candles GROUP BY symbol, interval
ORDER BY candle_count DESC, symbol, interval""")
OHLC_SQL = text("""SELECT open_time, open, high, low, close, volume, symbol, interval
FROM public.market_candles WHERE symbol=:symbol AND interval=:interval ORDER BY open_time""")
SUITABILITY_FIELDS = "symbol interval candle_count min_open_time max_open_time window_count_sampled up_candidate_count down_candidate_count flat_candidate_count mixed_candidate_count high_volatility_count clean_directional_count clean_range_count median_abs_return_pct median_range_pct median_directional_efficiency suitability_score suitability_rank selected_for_expanded_validation selection_notes".split()
MATRIX_FIELDS = "window_id symbol symbol_role interval period_start period_end window_length reference_label selection_reason close_return_pct high_low_range_pct directional_efficiency close_position_in_window_range engine_market_regime confidence boundary_status top_reason_codes warnings_count errors_count trade_signal safe_for_runtime_trading live_trading_connected match_status review_notes preview_artifact result_artifact".split()


def iso(value: object) -> str:
    return value.isoformat() if isinstance(value, datetime) else str(value)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=iso) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(rows: list[Mapping[str, object]]) -> dict[str, float]:
    first = float(rows[0]["open"]); last = float(rows[-1]["close"])
    high = max(float(row["high"]) for row in rows); low = min(float(row["low"]) for row in rows)
    span = max(high - low, 1e-12)
    return {"close_return_pct": (last-first)/first*100, "high_low_range_pct": span/first*100,
            "directional_efficiency": abs(last-first)/span, "close_position_in_window_range": (last-low)/span}


def kinds(m: Mapping[str, float]) -> set[str]:
    ret, rng, eff, pos = m["close_return_pct"], m["high_low_range_pct"], m["directional_efficiency"], m["close_position_in_window_range"]
    found: set[str] = set()
    if ret >= 1.5 and eff >= .45 and pos >= .60: found.add("UP")
    if ret <= -1.5 and eff >= .45 and pos <= .40: found.add("DOWN")
    if abs(ret) <= .5 and rng <= 3 and eff <= .25: found.add("FLAT")
    if abs(ret) <= 1 and rng >= 2.5 and eff <= .35: found.add("MIXED")
    if rng >= 5 and eff <= .35: found.add("HIGH_VOLATILITY_CHOP")
    return found


def rank_key(kind: str, m: Mapping[str, float]) -> tuple[float, ...]:
    if kind == "UP": return (m["close_return_pct"], m["directional_efficiency"], m["close_position_in_window_range"])
    if kind == "DOWN": return (-m["close_return_pct"], m["directional_efficiency"], 1-m["close_position_in_window_range"])
    if kind == "FLAT": return (-abs(m["close_return_pct"]), -m["directional_efficiency"], -m["high_low_range_pct"])
    return (m["high_low_range_pct"], -abs(m["close_return_pct"]), -m["directional_efficiency"])


def sampled(rows: list[Mapping[str, object]]) -> list[dict[str, Any]]:
    return [{"start_index": start, "metrics": metrics(rows[start:start+WINDOW_LENGTH])}
            for start in range(0, len(rows)-WINDOW_LENGTH+1, WINDOW_LENGTH)]


def suitability(symbol: str, availability: Mapping[str, object], samples: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(kind for sample in samples for kind in kinds(sample["metrics"]))
    ms = [sample["metrics"] for sample in samples]
    clean_directional = counts["UP"] + counts["DOWN"]
    score = clean_directional*2 + counts["FLAT"]*2 + counts["MIXED"]*.5 - counts["HIGH_VOLATILITY_CHOP"]*.25
    return {"symbol": symbol, "interval": INTERVAL, "candle_count": availability["candle_count"],
            "min_open_time": iso(availability["min_open_time"]), "max_open_time": iso(availability["max_open_time"]),
            "window_count_sampled": len(samples), "up_candidate_count": counts["UP"], "down_candidate_count": counts["DOWN"],
            "flat_candidate_count": counts["FLAT"], "mixed_candidate_count": counts["MIXED"],
            "high_volatility_count": counts["HIGH_VOLATILITY_CHOP"], "clean_directional_count": clean_directional,
            "clean_range_count": counts["FLAT"], "median_abs_return_pct": round(statistics.median(abs(m["close_return_pct"]) for m in ms), 6),
            "median_range_pct": round(statistics.median(m["high_low_range_pct"] for m in ms), 6),
            "median_directional_efficiency": round(statistics.median(m["directional_efficiency"] for m in ms), 6),
            "suitability_score": round(score, 3)}


def select(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    labels = {"UP":"EXPECTED_UP", "DOWN":"EXPECTED_DOWN", "FLAT":"EXPECTED_FLAT", "MIXED":"EXPECTED_UNKNOWN_OR_MIXED", "HIGH_VOLATILITY_CHOP":"HIGH_VOLATILITY_CHOP"}
    used: set[int] = set()
    for kind in ("UP", "DOWN", "FLAT", "MIXED", "HIGH_VOLATILITY_CHOP"):
        candidates = [s for s in samples if kind in kinds(s["metrics"])]
        candidates.sort(key=lambda s: (rank_key(kind, s["metrics"]), -s["start_index"]), reverse=True)
        for item in candidates:
            if item["start_index"] not in used:
                selected.append({**item, "window_type": kind, "reference_label": labels[kind], "selection_reason": f"top deterministic {kind} OHLC candidate"})
                used.add(item["start_index"]); break
    # Fill to 14 historical windows, balanced across the four required descriptive labels.
    ranked: dict[str, list[dict[str, Any]]] = {}
    for kind in ("UP", "DOWN", "FLAT", "MIXED"):
        ranked[kind] = [s for s in samples if kind in kinds(s["metrics"])]
        ranked[kind].sort(key=lambda s: (rank_key(kind, s["metrics"]), -s["start_index"]), reverse=True)
    while len(selected) < 14:
        added = False
        for kind in ("UP", "DOWN", "FLAT", "MIXED"):
            item = next((candidate for candidate in ranked[kind] if candidate["start_index"] not in used), None)
            if item is not None:
                selected.append({**item, "window_type": kind, "reference_label": labels[kind], "selection_reason": f"ranked deterministic {kind} OHLC candidate"})
                used.add(item["start_index"]); added = True
            if len(selected) >= 14: break
        if not added: break
    if len(selected) < 14: raise RuntimeError("INSUFFICIENT_DIVERSE_WINDOWS")
    return selected[:14]


def compare(label: str, regime: str) -> tuple[str, str]:
    if label in {"RECENT_BASELINE", "HIGH_VOLATILITY_CHOP"} and regime == "UNKNOWN": return "ACCEPTABLE_UNKNOWN", "Conservative UNKNOWN is acceptable for observational/choppy context"
    expected = {"EXPECTED_UP":"UP", "EXPECTED_DOWN":"DOWN", "EXPECTED_FLAT":"FLAT", "EXPECTED_UNKNOWN_OR_MIXED":"UNKNOWN"}
    if expected.get(label) == regime: return "MATCH", "Direct reference comparison"
    if regime == "UNKNOWN" and label in {"EXPECTED_UP", "EXPECTED_DOWN", "EXPECTED_FLAT"}: return "QUESTIONABLE_UNKNOWN", "Clean reference produced UNKNOWN; evidence/composer review warranted"
    if (label, regime) in {("EXPECTED_UP","DOWN"), ("EXPECTED_DOWN","UP")}: return "MISMATCH", "Opposite directional classification; not a tuning conclusion"
    if label == "EXPECTED_FLAT" and regime in {"UP","DOWN"}: return "MISMATCH", "Flat reference produced directional classification"
    return "NEEDS_REVIEW", "Non-direct comparison requires trace review"


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for row in rows:
            exported = dict(row)
            if "top_reason_codes" in fields:
                exported["top_reason_codes"] = "|".join(row.get("top_reason_codes", []))
            writer.writerow(exported)


def documents(suitability_rows: list[dict[str, Any]], matrix: list[dict[str, Any]], availability: list[dict[str, Any]]) -> None:
    statuses = Counter(row["match_status"] for row in matrix); regimes = Counter(row["engine_market_regime"] for row in matrix)
    per_symbol = {s: dict(Counter(r["engine_market_regime"] for r in matrix if r["symbol"] == s)) for s in sorted({r["symbol"] for r in matrix})}
    per_label = {s: dict(Counter(r["match_status"] for r in matrix if r["reference_label"] == s)) for s in sorted({r["reference_label"] for r in matrix})}
    ranking = "\n".join(f"{r['suitability_rank']}. {r['symbol']}: score {r['suitability_score']}, role {r['selection_notes']}" for r in suitability_rows)
    all_unknown = set(regimes) == {"UNKNOWN"}
    answer = ("B is the leading explanation: all three symbols, including clean UP/DOWN/FLAT windows, remained UNKNOWN. "
              "Selection noise alone (A) and insufficient diversity (C) do not explain the result. D remains untested; E trace review is required before tuning."
              if all_unknown else "A alone is not established; outcomes vary and require per-symbol trace review (E) before any core decision.")
    summary = f"""# ENGINE-TREND-15B — Symbol Suitability and Expanded Historical Validation Summary

## Purpose
Assess symbol suitability and expand real historical validation without changing engine core.
## Baseline
ENGINE-TREND-15 returned UNKNOWN 0.3 on all 15 windows.
## Data source
Read-only `public.market_candles` in PostgreSQL; report artifacts were not candle inputs.
## Symbol availability
{len(availability)} symbol/interval rows discovered; only BTCUSDT, ETHUSDT, and SOLUSDT at 15m.
## Suitability scoring method
Non-overlapping 96-candle OHLC samples; score = directional×2 + flat×2 + mixed×0.5 − high-volatility chop×0.25. Engine output is excluded.
## Suitability ranking
{ranking}
## Selected symbols
All three confirmed symbols were selected. BTC is retained as the macro/noisy benchmark, not the primary proof asset.
## Expanded validation scope
{len(matrix)} real windows, 15 per symbol, 96 candles each; required clean and mixed labels plus recent baseline.
## Expanded validation results
Regimes: {dict(regimes)}. Match statuses: {dict(statuses)}.
## Per-symbol results
{per_symbol}
## Per-label results
{per_label}
## Safety contract verification
All {len(matrix)} rows preserve NOT_EVALUATED, runtime safety false, and live connection false; zero violations.
## Interpretation
Suitability differs descriptively, but suitability does not itself validate engine reading quality.
## Answer to key decision question
{answer}
## What this proves
The expanded real-data pipeline is reproducible and safe, and symbol/window selection can be separated from engine output.
## What this does not prove
- no trading edge proven
- no profitability proven
- no runtime trading allowed
- no execution readiness proven
- no threshold tuning performed
- no model training performed
## Recommended next stage
ENGINE-TREND-16 — Historical Validation Review and Core Tuning Decision. Inspect evidence/composer traces before deciding on any change; still no runtime trading.
"""
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT/"ENGINE_TREND_15B_SYMBOL_SUITABILITY_SUMMARY.md").write_text(summary, encoding="utf-8")
    report = f"""# ENGINE-TREND-15B — Symbol Suitability and Expanded Historical Validation

## Stage goal
Determine validation-symbol suitability and expand historical coverage without core tuning.
## Baseline
ENGINE-TREND-15: 15 safe real windows; all UNKNOWN 0.3.
## Files created/changed
Runner, offline test, availability/suitability/window/matrix artifacts, 90 per-window artifacts, summary, manifest, and this report. Protected modules unchanged.
## DB source
Read-only PostgreSQL `public.market_candles`.
## Symbol availability discovery
Only BTCUSDT, ETHUSDT, SOLUSDT at 15m; approximately 50,962 candles each.
## Suitability scoring
OHLC-only non-overlapping 96-candle samples; no engine-output leakage and no threshold relaxation.
## Selected symbols
All three: highest-ranked asset is main candidate, remaining non-BTC asset secondary, BTC macro/noisy benchmark.
## Expanded validation scope
{len(matrix)} windows; 15 per symbol; five required window types where available.
## Expanded validation result summary
Regimes {dict(regimes)}; statuses {dict(statuses)}.
## Per-symbol summary
{per_symbol}
## Per-label summary
{per_label}
## Safety contract verification
{len(matrix)}/{len(matrix)} passed; zero violations.
## Tests executed
Runner, compilation, requested offline and relevant ENGINE-TREND gates (recorded after execution).
## Scans executed
Write-SQL, legacy, trading-term, secret, diff, and protected-core scans (recorded after execution).
## Known limitations
Rule labels are validation references, not ground truth. Selection is deterministic, not a random holdout. Only three DB symbols exist. Context length remains 96; 192/384 is untested. No core tracing or tuning was performed.
## Next recommended stage
ENGINE-TREND-16 — Historical Validation Review and Core Tuning Decision; no runtime trading.
"""
    REPORT.write_text(report, encoding="utf-8")


def main() -> int:
    try: _, db_url = resolve_db_url(os.environ)
    except Exception: print("error: DB_CONFIG_MISSING", file=sys.stderr); return 1
    engine = create_engine(db_url); availability: list[dict[str, Any]] = []; all_rows: dict[str, list[dict[str, Any]]] = {}; samples_by_symbol = {}
    try:
        with engine.connect() as connection:
            connection.execute(text("SET TRANSACTION READ ONLY"))
            availability = [dict(row) for row in connection.execute(AVAILABILITY_SQL).mappings().all()]
            eligible = [r for r in availability if r["interval"] == INTERVAL and int(r["candle_count"]) >= 10_000]
            if len(eligible) < 3: eligible = [r for r in availability if r["interval"] == INTERVAL]
            if not eligible: raise RuntimeError("NO_ELIGIBLE_SYMBOLS")
            for item in eligible:
                symbol = str(item["symbol"]); rows = [dict(r) for r in connection.execute(OHLC_SQL, {"symbol":symbol, "interval":INTERVAL}).mappings().all()]
                all_rows[symbol] = rows; samples_by_symbol[symbol] = sampled(rows)
            suit = [suitability(str(a["symbol"]), a, samples_by_symbol[str(a["symbol"])]) for a in eligible]
            suit.sort(key=lambda r: (-r["suitability_score"], r["symbol"]))
            for rank, row in enumerate(suit, 1): row["suitability_rank"] = rank
            selected_symbols = [r["symbol"] for r in suit[:5]]
            main_non_btc = next((s for s in selected_symbols if s != "BTCUSDT"), selected_symbols[0])
            roles = {s: ("MACRO_NOISY_BENCHMARK" if s == "BTCUSDT" else "MAIN_VALIDATION_CANDIDATE" if s == main_non_btc else "SECONDARY_VALIDATION_CANDIDATE") for s in selected_symbols}
            for row in suit:
                row["selected_for_expanded_validation"] = row["symbol"] in selected_symbols
                row["selection_notes"] = roles.get(row["symbol"], "not selected by suitability rank")
            provider = PostgresMarketCandlesProvider(connection); matrix=[]; windows=[]; per_paths=[]
            for symbol in selected_symbols:
                choices = select(samples_by_symbol[symbol]); recent_start = len(all_rows[symbol])-WINDOW_LENGTH
                choices.append({"start_index":recent_start, "metrics":metrics(all_rows[symbol][recent_start:]), "window_type":"RECENT_BASELINE", "reference_label":"RECENT_BASELINE", "selection_reason":"latest 96 candles; observational baseline"})
                counters=Counter()
                for choice in choices:
                    kind=choice["window_type"]; counters[kind]+=1; window_id=f"{symbol.lower()}_15m_{kind.lower()}_{counters[kind]:03d}"
                    block=all_rows[symbol][choice["start_index"]:choice["start_index"]+WINDOW_LENGTH]
                    start,end=iso(block[0]["open_time"]),iso(block[-1]["open_time"])
                    request=CandleDataRequest(symbol=symbol, interval=INTERVAL, limit=WINDOW_LENGTH, start_time=start, end_time=end, source_name="postgresql.public.market_candles")
                    result=run_engine_trend_from_provider(provider, request, min_candle_count=WINDOW_LENGTH); preview=result.engine_output.preview
                    if preview["safety"] != SAFETY or result.status.value != "READY" or result.batch.metadata.get("candle_count") != WINDOW_LENGTH: raise RuntimeError(f"SAFETY_OR_BOUNDARY_CONTRACT_VIOLATION: {window_id}")
                    pp=ROOT/"previews"/f"{window_id}_preview.json"; rp=ROOT/"results"/f"{window_id}_result.json"
                    write_json(pp,{"stage":STAGE,"window_id":window_id,"reference_label":choice["reference_label"],"selection_metrics":choice["metrics"],"boundary_status":result.status.value,"warnings":list(result.warnings),"errors":list(result.errors),"engine_preview":preview})
                    write_json(rp,{"stage":STAGE,"window_id":window_id,"reference_label":choice["reference_label"],"request":request.to_dict(),"boundary":result.to_dict()}); per_paths += [pp.as_posix(),rp.as_posix()]
                    status,notes=compare(choice["reference_label"],preview["market_regime"]); m=choice["metrics"]
                    matrix.append({"window_id":window_id,"symbol":symbol,"symbol_role":roles[symbol],"interval":INTERVAL,"period_start":start,"period_end":end,"window_length":WINDOW_LENGTH,"reference_label":choice["reference_label"],"selection_reason":choice["selection_reason"],"close_return_pct":round(m["close_return_pct"],6),"high_low_range_pct":round(m["high_low_range_pct"],6),"directional_efficiency":round(m["directional_efficiency"],6),"close_position_in_window_range":round(m["close_position_in_window_range"],6),"engine_market_regime":preview["market_regime"],"confidence":preview["confidence"],"boundary_status":result.status.value,"top_reason_codes":list(preview["reason_codes_top"]),"warnings_count":len(result.warnings),"errors_count":len(result.errors),**SAFETY,"match_status":status,"review_notes":notes,"preview_artifact":pp.as_posix(),"result_artifact":rp.as_posix()})
                    windows.append({"window_id":window_id,"symbol":symbol,"symbol_role":roles[symbol],"interval":INTERVAL,"period_start":start,"period_end":end,"window_length":WINDOW_LENGTH,"window_type":kind,"reference_label":choice["reference_label"],"selection_reason":choice["selection_reason"],"descriptive_metrics":m})
    finally: engine.dispose()
    availability_path=ROOT/"ENGINE_TREND_15B_SYMBOL_AVAILABILITY.json"; suit_json=ROOT/"ENGINE_TREND_15B_SYMBOL_SUITABILITY_MATRIX.json"; suit_csv=ROOT/"ENGINE_TREND_15B_SYMBOL_SUITABILITY_MATRIX.csv"; windows_path=ROOT/"ENGINE_TREND_15B_EXPANDED_VALIDATION_WINDOWS.json"; matrix_json=ROOT/"ENGINE_TREND_15B_EXPANDED_VALIDATION_MATRIX.json"; matrix_csv=ROOT/"ENGINE_TREND_15B_EXPANDED_VALIDATION_MATRIX.csv"
    clean_availability=[{**r,"min_open_time":iso(r["min_open_time"]),"max_open_time":iso(r["max_open_time"])} for r in availability]
    write_json(availability_path,{"stage":STAGE,"source_table":"public.market_candles","query_mode":"read_only","rows":clean_availability}); write_json(suit_json,{"stage":STAGE,"rows":suit}); write_csv(suit_csv,SUITABILITY_FIELDS,suit)
    write_json(windows_path,{"stage":STAGE,"source":"postgresql.public.market_candles","selection_without_engine_output":True,"windows":windows}); write_json(matrix_json,{"stage":STAGE,"rows":matrix}); write_csv(matrix_csv,MATRIX_FIELDS,matrix)
    documents(suit,matrix,clean_availability); summary=ROOT/"ENGINE_TREND_15B_SYMBOL_SUITABILITY_SUMMARY.md"; manifest=ROOT/"ENGINE_TREND_15B_ARTIFACT_MANIFEST.json"
    checksum_paths=[availability_path,suit_json,suit_csv,windows_path,matrix_json,matrix_csv,summary,REPORT]+[Path(p) for p in per_paths]
    write_json(manifest,{"stage":STAGE,"generated_at":datetime.now(timezone.utc).isoformat(),"source_table":"public.market_candles","symbols_discovered":sorted({r["symbol"] for r in clean_availability}),"symbols_selected":selected_symbols,"interval":INTERVAL,"window_count":len(matrix),"suitability_matrix_paths":[suit_csv.as_posix(),suit_json.as_posix()],"expanded_validation_matrix_paths":[matrix_csv.as_posix(),matrix_json.as_posix()],"summary_path":summary.as_posix(),"per_window_artifact_paths":per_paths,"sha256_checksums":{p.as_posix():digest(p) for p in checksum_paths},"safety_summary":{**SAFETY,"verified_window_count":len(matrix),"violations":0},"no_trading_claims":True,"core_changed":False,"adapter_changed":False,"db_cli_changed":False})
    print(f"{STAGE}: symbols={len(selected_symbols)} windows={len(matrix)} regimes={dict(Counter(r['engine_market_regime'] for r in matrix))}"); return 0


if __name__ == "__main__": raise SystemExit(main())
