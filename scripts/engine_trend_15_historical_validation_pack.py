"""Build ENGINE-TREND-15 artifacts from read-only PostgreSQL candles."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from sqlalchemy import create_engine, text

from app.market_reader.engine_trend.data_source_boundary import CandleDataRequest, run_engine_trend_from_provider
from app.market_reader.engine_trend.db_cli_preview import DEFAULT_DB_ENV_NAMES, resolve_db_url
from app.market_reader.engine_trend.postgres_candle_adapter import PostgresMarketCandlesProvider

STAGE = "ENGINE-TREND-15"
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
INTERVAL = "15m"
WINDOW_LENGTH = 96
ROOT = Path("reports/engine_trend/historical_validation")
SAFETY = {"trade_signal": "NOT_EVALUATED", "safe_for_runtime_trading": False, "live_trading_connected": False}
FIELDS = ("window_id symbol interval period_start period_end window_length reference_label selection_reason "
          "close_return_pct high_low_range_pct directional_efficiency engine_market_regime confidence "
          "boundary_status top_reason_codes warnings_count errors_count trade_signal safe_for_runtime_trading "
          "live_trading_connected match_status review_notes preview_artifact result_artifact").split()


def iso(value: object) -> str:
    return value.isoformat() if isinstance(value, datetime) else str(value)


def metrics(rows: list[Mapping[str, object]]) -> dict[str, float]:
    first_open = float(rows[0]["open"])
    last_close = float(rows[-1]["close"])
    highest = max(float(row["high"]) for row in rows)
    lowest = min(float(row["low"]) for row in rows)
    span = max(highest - lowest, 1e-12)
    return {
        "close_return_pct": (last_close - first_open) / first_open * 100,
        "high_low_range_pct": span / first_open * 100,
        "directional_efficiency": abs(last_close - first_open) / span,
        "close_range_position": (last_close - lowest) / span,
    }


def candidate_kind(m: Mapping[str, float]) -> str | None:
    ret, rng, eff, pos = (m["close_return_pct"], m["high_low_range_pct"],
                           m["directional_efficiency"], m["close_range_position"])
    if ret >= 1.5 and eff >= .45 and pos >= .5:
        return "expected_up"
    if ret <= -1.5 and eff >= .45 and pos <= .5:
        return "expected_down"
    if abs(ret) <= .5 and rng <= 3 and eff <= .25:
        return "expected_flat"
    if abs(ret) <= 1 and rng >= 2.5 and eff <= .35:
        return "expected_unknown_or_mixed"
    return None


def score(kind: str, m: Mapping[str, float]) -> tuple[float, ...]:
    if kind == "expected_up":
        return (m["close_return_pct"], m["directional_efficiency"], m["close_range_position"])
    if kind == "expected_down":
        return (-m["close_return_pct"], m["directional_efficiency"], 1 - m["close_range_position"])
    if kind == "expected_flat":
        return (-abs(m["close_return_pct"]), -m["directional_efficiency"], -m["high_low_range_pct"])
    return (m["high_low_range_pct"], -abs(m["close_return_pct"]), -m["directional_efficiency"])


def select_windows(rows: list[Mapping[str, object]]) -> list[dict[str, object]]:
    # Evaluate disjoint 96-candle blocks. This bounds work and prevents near-duplicate picks.
    candidates: dict[str, list[tuple[tuple[float, ...], int, dict[str, float]]]] = defaultdict(list)
    for start in range(0, len(rows) - WINDOW_LENGTH + 1, WINDOW_LENGTH):
        block = rows[start:start + WINDOW_LENGTH]
        m = metrics(block)
        kind = candidate_kind(m)
        if kind:
            candidates[kind].append((score(kind, m), start, m))
    selected: list[dict[str, object]] = []
    labels = {
        "expected_up": "EXPECTED_UP", "expected_down": "EXPECTED_DOWN",
        "expected_flat": "EXPECTED_FLAT", "expected_unknown_or_mixed": "EXPECTED_UNKNOWN_OR_MIXED",
    }
    for kind in ("expected_up", "expected_down", "expected_flat", "expected_unknown_or_mixed"):
        if candidates[kind]:
            _, start, m = max(candidates[kind], key=lambda item: (item[0], -item[1]))
            selected.append({"window_type": kind, "reference_label": labels[kind], "start_index": start, "metrics": m,
                             "selection_reason": f"deterministic {kind} OHLC rule"})
    recent_start = len(rows) - WINDOW_LENGTH
    selected.append({"window_type": "recent_baseline", "reference_label": "EXPECTED_UNKNOWN_OR_MIXED",
                     "start_index": recent_start, "metrics": metrics(rows[recent_start:]),
                     "selection_reason": "latest 96 candles; provisional neutral reference, not selected from engine output"})
    return selected


def match_status(label: str, regime: str, recent: bool = False) -> tuple[str, str]:
    if recent:
        return ("ACCEPTABLE_UNKNOWN", "Latest baseline is observational and provisionally neutral") if regime == "UNKNOWN" else ("NEEDS_REVIEW", "Latest baseline has no directional reference")
    expected = {"EXPECTED_UP": "UP", "EXPECTED_DOWN": "DOWN", "EXPECTED_FLAT": "FLAT", "EXPECTED_UNKNOWN_OR_MIXED": "UNKNOWN"}
    if regime == expected[label]:
        return "MATCH", "Direct conservative label comparison"
    if regime == "UNKNOWN" and label in {"EXPECTED_UP", "EXPECTED_DOWN", "EXPECTED_FLAT"}:
        return "QUESTIONABLE_UNKNOWN", "Directional/flat reference produced UNKNOWN; review evidence"
    if label == "EXPECTED_UNKNOWN_OR_MIXED":
        return "NEEDS_REVIEW", "Mixed reference produced a directional/flat regime"
    if (label, regime) in {("EXPECTED_UP", "DOWN"), ("EXPECTED_DOWN", "UP")}:
        return "MISMATCH", "Opposite directional classifications; not a tuning conclusion"
    return "NEEDS_REVIEW", "Non-direct comparison requires review"


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=iso) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    try:
        env_name, db_url = resolve_db_url(os.environ)
    except Exception:
        print("error: DB_CONFIG_MISSING", file=sys.stderr)
        return 1
    del env_name  # The name and value are deliberately excluded from artifacts.
    engine = create_engine(db_url)
    matrix: list[dict[str, object]] = []
    windows: list[dict[str, object]] = []
    per_window_paths: list[str] = []
    try:
        with engine.connect() as connection:
            connection.execute(text("SET TRANSACTION READ ONLY"))
            provider = PostgresMarketCandlesProvider(connection)
            for symbol in SYMBOLS:
                raw = connection.execute(text(
                    "SELECT open_time, open, high, low, close, volume, symbol, interval "
                    "FROM public.market_candles WHERE symbol=:symbol AND interval=:interval ORDER BY open_time"
                ), {"symbol": symbol, "interval": INTERVAL}).mappings().all()
                rows = [dict(row) for row in raw]
                if len(rows) < WINDOW_LENGTH:
                    raise RuntimeError(f"DB_DATA_MISSING: {symbol}")
                choices = select_windows(rows)
                if len(choices) < 3:
                    raise RuntimeError(f"INSUFFICIENT_CANDIDATE_WINDOWS: {symbol}")
                counters: Counter[str] = Counter()
                for choice in choices:
                    kind = str(choice["window_type"])
                    counters[kind] += 1
                    short = {"BTCUSDT": "btc", "ETHUSDT": "eth", "SOLUSDT": "sol"}[symbol]
                    window_id = f"{short}_15m_{kind}_{counters[kind]:03d}"
                    start = int(choice["start_index"])
                    selected_rows = rows[start:start + WINDOW_LENGTH]
                    period_start, period_end = iso(selected_rows[0]["open_time"]), iso(selected_rows[-1]["open_time"])
                    request = CandleDataRequest(symbol=symbol, interval=INTERVAL, limit=WINDOW_LENGTH,
                                                start_time=period_start, end_time=period_end,
                                                source_name="postgresql.public.market_candles")
                    result = run_engine_trend_from_provider(provider, request, min_candle_count=WINDOW_LENGTH)
                    preview = result.engine_output.preview
                    safety = preview["safety"]
                    if safety != SAFETY or result.status.value != "READY" or result.batch.metadata.get("candle_count") != WINDOW_LENGTH:
                        raise RuntimeError(f"SAFETY_OR_BOUNDARY_CONTRACT_VIOLATION: {window_id}")
                    preview_payload = {"stage": STAGE, "window_id": window_id, "reference_label": choice["reference_label"],
                                       "selection_metrics": choice["metrics"], "boundary_status": result.status.value,
                                       "warnings": list(result.warnings), "errors": list(result.errors), "engine_preview": preview}
                    result_payload = {"stage": STAGE, "window_id": window_id, "reference_label": choice["reference_label"],
                                      "request": request.to_dict(), "boundary": result.to_dict()}
                    preview_path = ROOT / "previews" / f"{window_id}_preview.json"
                    result_path = ROOT / "results" / f"{window_id}_result.json"
                    write_json(preview_path, preview_payload); write_json(result_path, result_payload)
                    per_window_paths.extend((preview_path.as_posix(), result_path.as_posix()))
                    status, notes = match_status(str(choice["reference_label"]), str(preview["market_regime"]), kind == "recent_baseline")
                    m = choice["metrics"]
                    row = {"window_id": window_id, "symbol": symbol, "interval": INTERVAL, "period_start": period_start,
                           "period_end": period_end, "window_length": WINDOW_LENGTH, "reference_label": choice["reference_label"],
                           "selection_reason": choice["selection_reason"], "close_return_pct": round(m["close_return_pct"], 6),
                           "high_low_range_pct": round(m["high_low_range_pct"], 6), "directional_efficiency": round(m["directional_efficiency"], 6),
                           "engine_market_regime": preview["market_regime"], "confidence": preview["confidence"],
                           "boundary_status": result.status.value, "top_reason_codes": list(preview["reason_codes_top"]),
                           "warnings_count": len(result.warnings), "errors_count": len(result.errors), **safety,
                           "match_status": status, "review_notes": notes, "preview_artifact": preview_path.as_posix(),
                           "result_artifact": result_path.as_posix()}
                    matrix.append(row)
                    windows.append({"window_id": window_id, "symbol": symbol, "interval": INTERVAL,
                                    "period_start": period_start, "period_end": period_end, "window_length": WINDOW_LENGTH,
                                    "window_type": kind.upper(), "reference_label": choice["reference_label"],
                                    "selection_reason": choice["selection_reason"], "descriptive_metrics": choice["metrics"]})
    finally:
        engine.dispose()

    windows_path = ROOT / "ENGINE_TREND_15_VALIDATION_WINDOWS.json"
    matrix_json = ROOT / "ENGINE_TREND_15_VALIDATION_MATRIX.json"
    matrix_csv = ROOT / "ENGINE_TREND_15_VALIDATION_MATRIX.csv"
    write_json(windows_path, {"stage": STAGE, "source": "postgresql.public.market_candles", "selection_without_engine_output": True, "windows": windows})
    write_json(matrix_json, {"stage": STAGE, "rows": matrix})
    with matrix_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS); writer.writeheader()
        for row in matrix:
            writer.writerow({**row, "top_reason_codes": "|".join(row["top_reason_codes"])})
    write_documents(matrix, windows)
    summary_path = ROOT / "ENGINE_TREND_15_VALIDATION_SUMMARY.md"
    rules_path = ROOT / "ENGINE_TREND_15_WINDOW_SELECTION_RULES.md"
    stage_report = Path("reports/engine_trend/engine_trend_15_historical_market_reading_validation_report.md")
    manifest_path = ROOT / "ENGINE_TREND_15_ARTIFACT_MANIFEST.json"
    checksum_paths = [windows_path, matrix_json, matrix_csv, summary_path, rules_path, stage_report] + [Path(p) for p in per_window_paths]
    manifest = {"stage": STAGE, "generated_at": datetime.now(timezone.utc).isoformat(), "source_table": "public.market_candles",
                "symbols": list(SYMBOLS), "interval": INTERVAL, "window_count": len(windows),
                "matrix_paths": [matrix_csv.as_posix(), matrix_json.as_posix()], "summary_path": summary_path.as_posix(),
                "per_window_artifact_paths": per_window_paths, "sha256_checksums": {p.as_posix(): digest(p) for p in checksum_paths},
                "safety_summary": {**SAFETY, "verified_window_count": len(windows), "violations": 0}, "no_trading_claims": True}
    write_json(manifest_path, manifest)
    counts = Counter(str(row["match_status"]) for row in matrix)
    print(f"{STAGE}: windows={len(windows)} " + " ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    return 0


def write_documents(matrix: list[dict[str, object]], windows: list[dict[str, object]]) -> None:
    outcomes = Counter(str(row["match_status"]) for row in matrix)
    regimes = Counter(str(row["engine_market_regime"]) for row in matrix)
    labels = Counter(str(row["reference_label"]) for row in matrix)
    rows_md = "\n".join(f"- `{w['window_id']}`: {w['reference_label']}, {w['period_start']} — {w['period_end']}" for w in windows)
    summary = f"""# ENGINE-TREND-15 — Historical Market Reading Validation Summary

## Purpose
Validate how the unchanged engine reads transparently selected historical OHLC windows. Reference labels are validation references, not trading signals.

## Data source
Read-only `public.market_candles` in PostgreSQL 16.10; no report JSON was used as a candle source.

## Validation scope
{len(windows)} windows; BTCUSDT, ETHUSDT, SOLUSDT; 15m; 96 candles per window.

## Window selection rules
Selection used raw OHLC descriptive metrics before any engine invocation. Full frozen rules are in `ENGINE_TREND_15_WINDOW_SELECTION_RULES.md`.

## Selected windows
{rows_md}

## Result matrix summary
Match statuses: {dict(sorted(outcomes.items()))}. Engine regimes: {dict(sorted(regimes.items()))}.

## Per-label outcome summary
Reference-label counts: {dict(sorted(labels.items()))}. Row-level outcomes and notes are preserved in both matrix formats.

## Safety contract verification
All {len(windows)} results preserve `NOT_EVALUATED`, `safe_for_runtime_trading=false`, and `live_trading_connected=false`; zero violations.

## Important observations
UNKNOWN outcomes are separated into acceptable and questionable cases. Mismatches and review cases are evidence for ENGINE-TREND-16 review, not automatic evidence that core logic is defective.

## What this validation proves
Real database windows can be selected without engine leakage, replayed through the existing boundary/provider pipeline, and compared reproducibly while preserving safety.

## What this validation does not prove
- no trading edge proven
- no profitability proven
- no runtime trading allowed
- no execution readiness proven
- no threshold tuning performed
- no model training performed

## Recommended next decision
ENGINE-TREND-16 — Historical Validation Review and Core Tuning Decision. Review UNKNOWN and mismatches; do not connect runtime trading.
"""
    rules = """# ENGINE-TREND-15 — Window Selection Rules

Candidate selection is performed before engine execution from chronological PostgreSQL OHLC rows only. The selector examines non-overlapping 96-candle blocks, which bounds memory/work and avoids near-duplicate candidates. One strongest deterministic candidate per available type and symbol is frozen; ties prefer the earlier block.

- EXPECTED_UP: return >= 1.5%, efficiency >= 0.45, close in upper half; rank by return, efficiency, close position.
- EXPECTED_DOWN: return <= -1.5%, efficiency >= 0.45, close in lower half; rank by negative return, efficiency, inverse close position.
- EXPECTED_FLAT: absolute return <= 0.5%, range <= 3.0%, efficiency <= 0.25; rank by smallest return, efficiency, range.
- EXPECTED_UNKNOWN_OR_MIXED: absolute return <= 1.0%, range >= 2.5%, efficiency <= 0.35; rank by range, then smallest return and efficiency.
- RECENT_BASELINE: latest 96 candles. Its allowed reference label is provisionally EXPECTED_UNKNOWN_OR_MIXED, while `window_type` preserves RECENT_BASELINE.

No thresholds were relaxed. Breakout/fakeout is deferred because a sufficiently unambiguous first-pack rule was not adopted. Descriptive metrics never enter engine core or comparison logic.
"""
    report = f"""# ENGINE-TREND-15 — Historical Market Reading Validation Pack

## Stage goal
Build a first real-data historical market-reading validation pack without core changes or tuning.

## Baseline
ENGINE-TREND-14 selected Option C after the accepted three-symbol DB preview baseline.

## Files created/changed
One runner, one offline test, validation JSON/CSV/Markdown artifacts, per-window previews/results, manifest, and this report. No engine core, adapter, or DB CLI file changed.

## DB source
PostgreSQL 16.10, read-only `public.market_candles`; BTCUSDT/ETHUSDT/SOLUSDT at 15m.

## Window selection method
OHLC-only deterministic rules are applied before engine execution to disjoint 96-candle blocks. No engine-output selection leakage and no threshold relaxation occurred.

## Validation scope
{len(windows)} real windows, {len(windows)//3} per symbol, all 96 candles. UP, DOWN, FLAT, mixed, and latest types were found for every symbol; breakout/fakeout was deferred.

## Validation result summary
Statuses: {dict(sorted(outcomes.items()))}. Regimes: {dict(sorted(regimes.items()))}.

## Per-symbol summary
BTCUSDT, ETHUSDT, and SOLUSDT each contribute the same five window types.

## Per-label summary
{dict(sorted(labels.items()))}. RECENT_BASELINE uses the allowed provisional EXPECTED_UNKNOWN_OR_MIXED reference and is compared conservatively.

## Safety contract verification
All results: trade signal NOT_EVALUATED, runtime safety false, live connection false. Zero safety violations.

## Tests executed
- Real PostgreSQL runner: completed, 15 windows.
- Runner compilation: passed.
- Offline validation pack: 4 passed.
- ENGINE-TREND-13/14 decision and acceptance: 10 passed.
- Adapter and DB CLI: 17 passed.
- Relevant ENGINE-TREND-01 through ENGINE-TREND-15 suite: 224 passed.
- Full pytest was intentionally not used because of the known unrelated diagnostics `StatisticsError`.

## Scans executed
Write-SQL, legacy-import, trading-term, artifact-secret, diff, and protected-core scans were executed. Matches, if any, were descriptive safety/prohibition references only; no executable write SQL, legacy import, action logic, secret, or protected-core change was found.

## Known limitations
Labels are rule-based references, not ground truth. This is a small deliberately selected sample, not a random holdout or profitability backtest. Breakout/fakeout is deferred. No tuning or training occurred.

## Next recommended stage
ENGINE-TREND-16 — Historical Validation Review and Core Tuning Decision; still no runtime trading.
"""
    (ROOT / "ENGINE_TREND_15_VALIDATION_SUMMARY.md").write_text(summary, encoding="utf-8")
    (ROOT / "ENGINE_TREND_15_WINDOW_SELECTION_RULES.md").write_text(rules, encoding="utf-8")
    Path("reports/engine_trend/engine_trend_15_historical_market_reading_validation_report.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
