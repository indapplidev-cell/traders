"""Replay the fixed 60-window pack and expose contextual hypotheses per window."""

from __future__ import annotations

import csv
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

from app.market_reader.engine_trend.data_source_boundary import (
    CandleDataRequest,
    run_engine_trend_from_provider,
)
from app.market_reader.engine_trend.db_cli_preview import resolve_db_url
from app.market_reader.engine_trend.postgres_candle_adapter import (
    PostgresMarketCandlesProvider,
)
from app.market_reader.engine_trend.offline_report_diagnostics import (
    attach_contextual_diagnostics,
)

STAGE = "ENGINE-TREND-18"
ROOT = Path("reports/engine_trend/hypothesis_replay")
REPORT = Path("reports/engine_trend/engine_trend_18_hypothesis_replay_report.md")
INPUTS = (
    (
        "ENGINE-TREND-15",
        Path("reports/engine_trend/historical_validation/ENGINE_TREND_15_VALIDATION_WINDOWS.json"),
        Path("reports/engine_trend/historical_validation/ENGINE_TREND_15_VALIDATION_MATRIX.json"),
    ),
    (
        "ENGINE-TREND-15B",
        Path("reports/engine_trend/symbol_suitability_validation/ENGINE_TREND_15B_EXPANDED_VALIDATION_WINDOWS.json"),
        Path("reports/engine_trend/symbol_suitability_validation/ENGINE_TREND_15B_EXPANDED_VALIDATION_MATRIX.json"),
    ),
)
SAFETY = {
    "trade_signal": "NOT_EVALUATED",
    "safe_for_runtime_trading": False,
    "live_trading_connected": False,
}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )


def load_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source_stage, window_path, matrix_path in INPUTS:
        windows = json.loads(window_path.read_text(encoding="utf-8"))["windows"]
        old_rows = json.loads(matrix_path.read_text(encoding="utf-8"))["rows"]
        old_by_id = {item["window_id"]: item for item in old_rows}
        for window in windows:
            rows.append(
                {
                    "source_stage": source_stage,
                    "old": old_by_id[window["window_id"]],
                    **window,
                }
            )
    return rows


def match_status(label: str, regime: str) -> str:
    expected = {
        "EXPECTED_UP": "UP",
        "EXPECTED_DOWN": "DOWN",
        "EXPECTED_FLAT": "FLAT",
        "EXPECTED_UNKNOWN_OR_MIXED": "UNKNOWN",
    }
    if expected.get(label) == regime:
        return "MATCH"
    if label in {"RECENT_BASELINE", "HIGH_VOLATILITY_CHOP"} and regime == "UNKNOWN":
        return "ACCEPTABLE_UNKNOWN"
    if label in {"EXPECTED_UP", "EXPECTED_DOWN", "EXPECTED_FLAT"} and regime == "UNKNOWN":
        return "QUESTIONABLE_UNKNOWN"
    if (
        (label, regime) in {("EXPECTED_UP", "DOWN"), ("EXPECTED_DOWN", "UP")}
        or label == "EXPECTED_FLAT" and regime in {"UP", "DOWN"}
    ):
        return "MISMATCH"
    return "NEEDS_REVIEW"


def _event(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "candle_event": item["pattern_code"],
        "event_indexes": [item["start_index"], item["end_index"]],
        "trend_context_before_event": item["prior_structure"],
        "causal_zone_available_at_event": item["zone_relation"] != "NO_CAUSAL_ZONE",
        "causal_zone_relation": item["zone_relation"],
        "causal_zone_mid": item["related_zone_mid"],
        "follow_through": item["follow_through"],
        "invalidation": {
            "invalidated": item["status"] == "INVALIDATED"
            or item["follow_through"] == "INVALIDATED",
            "event_status": item["status"],
            "reason_codes": [
                code
                for code in item["reason_codes"]
                if "INVALID" in code or "REJECT" in code
            ],
        },
    }


def build_diagnostic(window: dict[str, Any], boundary: Any) -> dict[str, Any]:
    output = boundary.engine_output
    result = output.composer_output.result
    matrix = output.composer_output.matrix.to_dict()
    unified = matrix["unified_context"]
    hypotheses = matrix["hypothesis_result"]
    decision = output.composer_output.decision_trace.to_dict()
    scores = decision["candidate_scores"]
    schwager = unified["schwager_context"]
    altunina = unified["altunina_context"]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for hypothesis in hypotheses["hypotheses"]:
        grouped[hypothesis["status"]].append(hypothesis)
    dominant = hypotheses["dominant_hypothesis"]
    old = window["old"]
    new_regime = result.market_regime.value
    comparison = match_status(window["reference_label"], new_regime)
    selected_direction = {"UP": "BULLISH", "DOWN": "BEARISH", "FLAT": "FLAT"}.get(
        new_regime
    )
    regime_hypotheses = [
        item
        for item in grouped["CONFIRMED"]
        if item["direction"] == selected_direction
    ]
    selected_hypothesis = (
        max(regime_hypotheses, key=lambda item: item["score"])
        if regime_hypotheses
        else None
    )
    artifact = {
        "stage": STAGE,
        "source_stage": window["source_stage"],
        "window": {
            key: window.get(key)
            for key in (
                "window_id",
                "symbol",
                "interval",
                "period_start",
                "period_end",
                "window_length",
                "reference_label",
                "selection_reason",
            )
        },
        "unified_market_context": {
            "trend_structure": altunina["structure_direction"],
            "shared_swing_points": unified["structural_swing_points"],
            "range": schwager["trading_range"],
            "active_support_resistance_zones": schwager["zones"],
            "breakout_state": schwager["breakout_context"],
            "technical_indicators": unified.get("indicator_context", {}),
            "analysis_window": unified.get("analysis_window", {}),
        },
        "contextual_events": [_event(item) for item in hypotheses["contextual_events"]],
        "hypotheses": {
            "CONFIRMED": grouped["CONFIRMED"],
            "PENDING": grouped["PENDING"],
            "INVALIDATED": grouped["INVALIDATED"],
            # The current engine contract has CONFLICTED, but no CANCELLED.
            # Keep both explicit instead of silently changing lifecycle meaning.
            "CANCELLED": [],
            "CONFLICTED": grouped["CONFLICTED"],
            "cancelled_contract_note": "HypothesisStatus.CANCELLED is not implemented; CONFLICTED is reported separately.",
        },
        "composer": {
            "selected_hypothesis": selected_hypothesis,
            "engine_dominant_hypothesis": dominant,
            "regime": new_regime,
            "confidence": result.confidence,
            "reason": {
                "status": decision["status"],
                "decision_source": decision["decision_source"],
                "fallback_reason": scores.get("fallback_reason"),
                "reason_codes": decision["reason_codes"],
            },
        },
        "comparison": {
            "old_regime": old["engine_market_regime"],
            "old_confidence": old["confidence"],
            "new_regime": new_regime,
            "new_confidence": result.confidence,
            "regime_changed": old["engine_market_regime"] != new_regime,
            "match_status": comparison,
        },
        "safety": result.safety.to_dict(),
        "boundary": {
            "status": boundary.status.value,
            "warnings": list(boundary.warnings),
            "errors": list(boundary.errors),
        },
    }
    return attach_contextual_diagnostics(artifact, candles=boundary.batch.candles)


def markdown(item: dict[str, Any]) -> str:
    w = item["window"]
    context = item["unified_market_context"]
    hypotheses = item["hypotheses"]
    composer = item["composer"]
    diagnostics = item["contextual_diagnostics"]

    def compact(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, default=str)

    event_lines = [
        "- candle event: {candle_event}; trend context before event: {trend_context_before_event}; "
        "causal zone available at event: {causal_zone_available_at_event} ({causal_zone_relation}); "
        "follow-through: {follow_through}; invalidation: {invalidation}".format(**event)
        for event in item["contextual_events"]
    ] or ["- none"]
    sections = []
    for status in ("CONFIRMED", "PENDING", "INVALIDATED", "CANCELLED", "CONFLICTED"):
        values = hypotheses[status]
        sections.append(f"- {status}: {compact(values) if values else 'none'}")
    return f"""# Window: {w['window_id']}

Reference: {w['reference_label']}; period: {w['period_start']} — {w['period_end']}.

## UnifiedMarketContext

- trend structure: {context['trend_structure']}
- shared swing points: {compact(context['shared_swing_points'])}
- range: {compact(context['range'])}
- active support/resistance zones: {compact(context['active_support_resistance_zones'])}
- breakout state: {compact(context['breakout_state'])}

## Contextual events

{chr(10).join(event_lines)}

## Hypotheses

{chr(10).join(sections)}

Note: {hypotheses['cancelled_contract_note']}

## Composer

- selected hypothesis: {compact(composer['selected_hypothesis'])}
- regime: {composer['regime']}
- confidence: {composer['confidence']}
- reason: {compact(composer['reason'])}

## Contextual diagnostics (offline / no signal)

- diagnostic version: {diagnostics['diagnostic_version']}
- generated for stage: {diagnostics['generated_for_stage']}
- action: {diagnostics['action']}
- tags: {compact(diagnostics['diagnostic_tags'])}
- observability: {compact(diagnostics['observability'])}
- not observable fields: {compact(diagnostics['not_observable_fields'])}
- no-action reasons: {compact(diagnostics['no_trade_reasons'])}
- decision impact: {compact(diagnostics['decision_impact'])}

## Old → new

{item['comparison']['old_regime']} ({item['comparison']['old_confidence']}) → {composer['regime']} ({composer['confidence']}); {item['comparison']['match_status']}.
"""


def finish(items: list[dict[str, Any]]) -> None:
    artifact_prefix = STAGE.replace("-", "_")
    regimes = Counter(item["composer"]["regime"] for item in items)
    statuses = Counter(item["comparison"]["match_status"] for item in items)
    unknown_causes = Counter()
    hypothesis_statuses = Counter()
    hypothesis_types = Counter()
    event_statuses = Counter()
    traps = Counter()
    flat_sources = Counter()
    for item in items:
        hypotheses = item["hypotheses"]
        for status in ("CONFIRMED", "PENDING", "INVALIDATED", "CONFLICTED"):
            hypothesis_statuses[status] += len(hypotheses[status])
            for hypothesis in hypotheses[status]:
                hypothesis_types[(hypothesis["hypothesis_type"], status)] += 1
                if hypothesis["hypothesis_type"] in {"BULL_TRAP", "BEAR_TRAP"}:
                    traps[(hypothesis["hypothesis_type"], status)] += 1
        for event in item["contextual_events"]:
            event_statuses[event["invalidation"]["event_status"]] += 1
        if item["composer"]["regime"] == "UNKNOWN":
            if not any(hypotheses[key] for key in ("CONFIRMED", "PENDING", "INVALIDATED", "CONFLICTED")):
                unknown_causes["NO_HYPOTHESES"] += 1
            elif (
                not hypotheses["CONFIRMED"]
                and hypotheses["PENDING"]
                and hypotheses["CONFLICTED"]
            ):
                unknown_causes["PENDING_PLUS_CONFLICTED_NO_CONFIRMED"] += 1
            elif not hypotheses["CONFIRMED"] and hypotheses["PENDING"]:
                unknown_causes["ONLY_PENDING_NO_CONFIRMED"] += 1
            elif not hypotheses["CONFIRMED"]:
                unknown_causes["NO_CONFIRMED_WITH_TERMINAL_OR_CONFLICTED"] += 1
            else:
                unknown_causes["CONFIRMED_BUT_COMPOSER_FALLBACK"] += 1
        if item["composer"]["regime"] == "FLAT":
            selected = item["composer"]["selected_hypothesis"]
            flat_sources[selected["hypothesis_type"] if selected else "NONE"] += 1

    regime_windows = {
        regime: [
            item["window"]["window_id"]
            for item in items
            if item["composer"]["regime"] == regime
        ]
        for regime in ("UP", "DOWN", "FLAT", "UNKNOWN")
    }
    candle_hypothesis_counts = Counter(
        hypothesis["status"]
        for item in items
        for status in ("CONFIRMED", "PENDING", "INVALIDATED", "CONFLICTED")
        for hypothesis in item["hypotheses"][status]
        if hypothesis["hypothesis_type"]
        in {"BULLISH_REVERSAL", "BEARISH_REVERSAL"}
    )
    flat_with_confirmed_range = sum(
        item["composer"]["regime"] == "FLAT"
        and any(
            hypothesis["hypothesis_type"] == "CONFIRMED_RANGE"
            for hypothesis in item["hypotheses"]["CONFIRMED"]
        )
        for item in items
    )

    rows = []
    for item in items:
        w, c, h = item["window"], item["comparison"], item["hypotheses"]
        rows.append(
            {
                "window_id": w["window_id"],
                "symbol": w["symbol"],
                "reference_label": w["reference_label"],
                "old_regime": c["old_regime"],
                "new_regime": c["new_regime"],
                "confidence": c["new_confidence"],
                "match_status": c["match_status"],
                "confirmed": len(h["CONFIRMED"]),
                "pending": len(h["PENDING"]),
                "invalidated": len(h["INVALIDATED"]),
                "cancelled": len(h["CANCELLED"]),
                "conflicted": len(h["CONFLICTED"]),
                "selected_hypothesis": (item["composer"]["selected_hypothesis"] or {}).get("hypothesis_type"),
            }
        )
    write_json(ROOT / f"{artifact_prefix}_WINDOW_MATRIX.json", {"stage": STAGE, "rows": rows})
    with (ROOT / f"{artifact_prefix}_WINDOW_MATRIX.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "stage": STAGE,
        "windows_replayed": len(items),
        "regime_counts": dict(regimes),
        "regime_windows": regime_windows,
        "match_status_counts": dict(statuses),
        "unknown_count": regimes["UNKNOWN"],
        "unknown_causes": dict(unknown_causes),
        "hypothesis_status_counts": dict(hypothesis_statuses),
        "hypothesis_type_status_counts": {
            f"{kind}:{status}": count for (kind, status), count in hypothesis_types.items()
        },
        "contextual_event_status_counts": dict(event_statuses),
        "candle_reversal_hypothesis_status_counts": dict(candle_hypothesis_counts),
        "trap_counts": {f"{kind}:{status}": count for (kind, status), count in traps.items()},
        "flat_selected_hypothesis_counts": dict(flat_sources),
        "flat_with_confirmed_range_count": flat_with_confirmed_range,
        "flat_without_confirmed_range_count": regimes["FLAT"] - flat_with_confirmed_range,
        "mismatch_windows": [row["window_id"] for row in rows if row["match_status"] == "MISMATCH"],
        "safety_violations": sum(item["safety"] != SAFETY for item in items),
        "cancelled_status_available": False,
        "cancelled_contract_note": "HypothesisStatus exposes CONFLICTED instead of CANCELLED.",
    }
    write_json(ROOT / f"{artifact_prefix}_SUMMARY.json", summary)

    table = "\n".join(
        f"| [{row['window_id']}]({ROOT.name}/markdown/{row['window_id']}.md) | {row['reference_label']} | {row['old_regime']} | {row['new_regime']} | {row['confidence']} | {row['match_status']} | {row['confirmed']}/{row['pending']}/{row['invalidated']}/{row['cancelled']} (+{row['conflicted']} conflicted) | {row['selected_hypothesis'] or 'none'} |"
        for row in rows
    )
    REPORT.write_text(
        f"""# {STAGE} — Hypothesis replay

The same fixed 60 validation rows were replayed read-only. Reference labels remain descriptive rather than ground truth.

## Critical answers

1. UNKNOWN: **{regimes['UNKNOWN']} / {len(items)}**. Causes: `{dict(unknown_causes)}`.
2. The cause split above distinguishes no hypotheses, pending-only, terminal/conflicted-only, and confirmed hypotheses blocked by composer fallback.
3. Regimes: `{dict(regimes)}`. UP: `{regime_windows['UP']}`; DOWN: `{regime_windows['DOWN']}`; FLAT: `{regime_windows['FLAT']}`.
4. MISMATCH: **{statuses['MISMATCH']}**; windows: `{summary['mismatch_windows']}`.
5. Trap hypotheses by lifecycle: `{summary['trap_counts']}`.
6. Candle contextual-event statuses: `{dict(event_statuses)}`. Reversal hypotheses: `{dict(candle_hypothesis_counts)}`.
7. FLAT selected hypothesis sources: `{dict(flat_sources)}`; {flat_with_confirmed_range}/{regimes['FLAT']} FLAT results contain a CONFIRMED_RANGE, and {regimes['FLAT'] - flat_with_confirmed_range} do not.

## Lifecycle contract observation

The requested `CANCELLED` status does not exist in the refactored enum. The engine emits `CONFLICTED`; reports retain an empty CANCELLED bucket and show CONFLICTED separately so the distinction is not hidden.

## Safety

Safety violations: {summary['safety_violations']}; no trading action was evaluated or connected.

## Per-window comparison

Lifecycle column is confirmed/pending/invalidated/cancelled, followed by conflicted.

| Window | Reference | Old | New | Confidence | Comparison | Lifecycle | Selected hypothesis |
|---|---|---|---|---:|---|---|---|
{table}
""",
        encoding="utf-8",
    )


def main() -> int:
    try:
        _, url = resolve_db_url(os.environ)
    except Exception:
        print("error: DB_CONFIG_MISSING", file=sys.stderr)
        return 2
    windows = load_rows()
    if len(windows) != 60:
        raise RuntimeError(f"EXPECTED_60_WINDOWS:GOT_{len(windows)}")
    ROOT.mkdir(parents=True, exist_ok=True)
    items: list[dict[str, Any]] = []
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            connection.execute(text("SET TRANSACTION READ ONLY"))
            provider = PostgresMarketCandlesProvider(connection)
            for window in windows:
                request = CandleDataRequest(
                    window["symbol"],
                    window["interval"],
                    int(window["window_length"]),
                    window["period_start"],
                    window["period_end"],
                    "postgresql.public.market_candles",
                )
                boundary = run_engine_trend_from_provider(
                    provider, request, min_candle_count=int(window["window_length"])
                )
                if boundary.status.value != "READY":
                    raise RuntimeError(f"WINDOW_REPLAY_FAILED:{window['window_id']}")
                item = build_diagnostic(window, boundary)
                items.append(item)
                write_json(ROOT / "json" / f"{window['window_id']}.json", item)
                md = ROOT / "markdown" / f"{window['window_id']}.md"
                md.parent.mkdir(parents=True, exist_ok=True)
                md.write_text(markdown(item), encoding="utf-8")
    finally:
        engine.dispose()
    finish(items)
    print(f"{STAGE}: replayed={len(items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
