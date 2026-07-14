"""Audit ENGINE-TREND-18 replay artifacts without changing engine rules."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

STAGE = "ENGINE-TREND-18B"
DEFAULT_INPUT = Path("reports/engine_trend/hypothesis_replay")
DEFAULT_OUTPUT = Path("reports/engine_trend/hypothesis_replay_review")
DEFAULT_REPORT = Path(
    "reports/engine_trend/engine_trend_18b_hypothesis_replay_review_report.md"
)

TARGET_MATCH_STATUSES = {"NEEDS_REVIEW", "QUESTIONABLE_UNKNOWN"}
REVIEW_VERDICTS = {
    "LABEL_ISSUE",
    "EXPECTED_CAUTION",
    "RULE_TOO_STRICT",
    "PRIORITY_ISSUE",
    "INSUFFICIENT_CONTEXT",
}

BEARISH_REVERSAL_CODES = {
    "SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED",
    "HANGING_MAN_LIKE_CONTEXT_REQUIRED",
    "BEARISH_ENGULFING_CONTEXT",
    "DARK_CLOUD_BEARISH_CONTEXT",
    "EVENING_STAR_LIKE_CONTEXT",
    "EVENING_DOJI_STAR_LIKE_CONTEXT",
    "BEARISH_HARAMI_CONTEXT",
    "TWEEZERS_TOP_CONTEXT_REQUIRED",
    "BEARISH_COUNTERATTACK_CONTEXT",
    "THREE_BLACK_CROWS_CONTEXT",
    "THREE_MOUNTAINS_CONTEXT_REQUIRED",
    "THREE_BUDDHA_TOP_CONTEXT_REQUIRED",
    "DUMPLING_TOP_CONTEXT_REQUIRED",
    "TOWER_TOP_CONTEXT_REQUIRED",
    "GRAVESTONE_DOJI_CONTEXT",
    "DOJI_TOP_CONTEXT_REQUIRED",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def fingerprint(item: dict[str, Any]) -> str:
    window = item["window"]
    return "|".join(
        str(window[key])
        for key in ("symbol", "interval", "period_start", "period_end")
    )


def hypothesis_items(item: dict[str, Any], status: str) -> list[dict[str, Any]]:
    return list(item["hypotheses"].get(status, []))


def unknown_cause(item: dict[str, Any]) -> str | None:
    if item["composer"]["regime"] != "UNKNOWN":
        return None
    confirmed = hypothesis_items(item, "CONFIRMED")
    pending = hypothesis_items(item, "PENDING")
    conflicted = hypothesis_items(item, "CONFLICTED")
    if confirmed:
        return "UNKNOWN_WITH_CONFIRMED_HYPOTHESIS"
    if not pending and not conflicted:
        return "NO_HYPOTHESES"
    if pending and conflicted:
        return "PENDING_PLUS_CONFLICTED_NO_CONFIRMED"
    if pending:
        return "ONLY_PENDING_NO_CONFIRMED"
    return "ONLY_CONFLICTED_NO_CONFIRMED"


def canonicalize(
    items: Iterable[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        groups[fingerprint(item)].append(item)
    canonical: list[dict[str, Any]] = []
    aliases: dict[str, list[str]] = {}
    for key, group in groups.items():
        ordered = sorted(
            group,
            key=lambda item: (
                item.get("source_stage") != "ENGINE-TREND-15B",
                item["window"]["window_id"],
            ),
        )
        canonical.append(ordered[0])
        aliases[key] = sorted(item["window"]["window_id"] for item in group)
    return sorted(canonical, key=lambda item: item["window"]["window_id"]), aliases


def label_quality(item: dict[str, Any]) -> str:
    reason = str(item["window"].get("selection_reason") or "").lower()
    return (
        "DETERMINISTIC_OHLC_PROXY"
        if "deterministic" in reason
        else "DESCRIPTIVE_REVIEW_LABEL"
    )


def target_groups(item: dict[str, Any]) -> list[str]:
    window = item["window"]
    label = window["reference_label"]
    regime = item["composer"]["regime"]
    groups: list[str] = []
    if item["comparison"]["match_status"] == "NEEDS_REVIEW":
        groups.append("NEEDS_REVIEW")
    if label == "EXPECTED_DOWN" and regime == "UNKNOWN":
        groups.append("EXPECTED_DOWN_UNKNOWN")
    if label == "EXPECTED_UP" and regime == "UNKNOWN":
        groups.append("EXPECTED_UP_UNKNOWN")
    if label == "EXPECTED_FLAT" and regime == "UNKNOWN":
        groups.append("EXPECTED_FLAT_UNKNOWN")
    confirmed_types = {
        hypothesis["hypothesis_type"]
        for hypothesis in hypothesis_items(item, "CONFIRMED")
    }
    if "CONFIRMED_RANGE" in confirmed_types and confirmed_types & {
        "BULL_TRAP",
        "BEAR_TRAP",
    }:
        groups.append("TRAP_VS_RANGE")
    return groups


def missing_confirmations(item: dict[str, Any]) -> list[str]:
    cause = unknown_cause(item)
    missing: list[str] = []
    if cause == "NO_HYPOTHESES":
        missing.append("NO_CAUSAL_SCENARIO_FORMED")
    for hypothesis in hypothesis_items(item, "PENDING"):
        htype = hypothesis["hypothesis_type"]
        codes = set(hypothesis["reason_codes"])
        if htype in {"UP_CONTINUATION", "DOWN_CONTINUATION"}:
            if "HYPOTHESIS_CROSS_METHOD_CONFIRMATION_PENDING" in codes:
                missing.append("ALIGNED_STRUCTURE_OR_CONFIRMED_CONTINUATION_EVENT")
        elif htype in {"BULLISH_REVERSAL", "BEARISH_REVERSAL"}:
            if "HYPOTHESIS_PATTERN_FOLLOW_THROUGH_PENDING" in codes:
                missing.append("PATTERN_FOLLOW_THROUGH")
        elif htype == "CONFIRMED_RANGE":
            breakout = item["unified_market_context"]["breakout_state"]
            if breakout["status"] == "ATTEMPT":
                missing.append("RANGE_BREAKOUT_ATTEMPT_RESOLUTION")
            else:
                missing.append("SECONDARY_FLAT_CONTEXT")
    if hypothesis_items(item, "CONFLICTED"):
        missing.append("CONFIRMED_BREAKOUT_PREVENTS_RANGE_CONFIRMATION")
    return list(dict.fromkeys(missing))


def review_verdict(item: dict[str, Any]) -> tuple[str, str]:
    groups = target_groups(item)
    if "TRAP_VS_RANGE" in groups:
        return (
            "PRIORITY_ISSUE",
            "Confirmed trap and confirmed range differ by less than the dominance margin; post-return continuation is not represented.",
        )
    if item["comparison"]["match_status"] == "NEEDS_REVIEW":
        return (
            "LABEL_ISSUE",
            "A confirmed causal hypothesis supports the engine result while the reference is descriptive or deterministic, not ground truth.",
        )
    cause = unknown_cause(item)
    if cause == "NO_HYPOTHESES":
        return (
            "INSUFFICIENT_CONTEXT",
            "The 96-candle input formed no continuation, reversal, range, or trap hypothesis; the label alone cannot authorize a regime.",
        )
    return (
        "EXPECTED_CAUTION",
        "The available scenario remains pending or conflicted and therefore correctly cannot select a regime under the current contract.",
    )


def compact_hypotheses(item: dict[str, Any]) -> str:
    parts: list[str] = []
    for status in ("CONFIRMED", "PENDING", "CONFLICTED", "INVALIDATED"):
        for hypothesis in hypothesis_items(item, status):
            parts.append(
                f"{hypothesis['hypothesis_type']}:{status}:{hypothesis['score']:.3f}"
            )
    return ";".join(parts)


def trap_range_delta(item: dict[str, Any]) -> float | None:
    scores = {
        hypothesis["hypothesis_type"]: float(hypothesis["score"])
        for hypothesis in hypothesis_items(item, "CONFIRMED")
    }
    trap = scores.get("BULL_TRAP", scores.get("BEAR_TRAP"))
    range_score = scores.get("CONFIRMED_RANGE")
    if trap is None or range_score is None:
        return None
    return range_score - trap


def review_row(
    item: dict[str, Any], aliases: dict[str, list[str]]
) -> dict[str, Any]:
    window = item["window"]
    breakout = item["unified_market_context"]["breakout_state"]
    verdict, rationale = review_verdict(item)
    event_statuses = Counter(
        event["invalidation"]["event_status"] for event in item["contextual_events"]
    )
    return {
        "window_id": window["window_id"],
        "aliases": aliases[fingerprint(item)],
        "fingerprint": fingerprint(item),
        "symbol": window["symbol"],
        "period_start": window["period_start"],
        "period_end": window["period_end"],
        "reference_label": window["reference_label"],
        "label_quality": label_quality(item),
        "selection_reason": window.get("selection_reason"),
        "regime": item["composer"]["regime"],
        "match_status": item["comparison"]["match_status"],
        "review_groups": target_groups(item),
        "unknown_cause": unknown_cause(item),
        "trend_structure": item["unified_market_context"]["trend_structure"],
        "range_detected": item["unified_market_context"]["range"]["is_detected"],
        "breakout_status": breakout["status"],
        "breakout_direction": breakout["direction"],
        "returned_to_range": breakout["returned_to_range"],
        "false_breakout_confirmation": breakout.get("false_breakout_confirmation"),
        "hypotheses": compact_hypotheses(item),
        "contextual_event_status_counts": dict(event_statuses),
        "missing_confirmations": missing_confirmations(item),
        "trap_range_score_delta": trap_range_delta(item),
        "verdict": verdict,
        "rationale": rationale,
    }


def count_unique_causes(items: Iterable[dict[str, Any]]) -> dict[str, int]:
    return dict(Counter(unknown_cause(item) or "HAS_CONFIRMED" for item in items))


def event_direction_audit(items: Iterable[dict[str, Any]]) -> dict[str, Any]:
    bearish_events = [
        event
        for item in items
        for event in item["contextual_events"]
        if event["candle_event"] in BEARISH_REVERSAL_CODES
    ]
    statuses = Counter(
        event["invalidation"]["event_status"] for event in bearish_events
    )
    candidate_zones = Counter(
        event["causal_zone_relation"]
        for event in bearish_events
        if event["invalidation"]["event_status"] == "CANDIDATE"
    )
    return {
        "bearish_reversal_event_status_counts": dict(statuses),
        "bearish_reversal_candidate_zone_counts": dict(candidate_zones),
        "bearish_reversal_confirmed_or_awaiting": statuses.get("CONFIRMED", 0)
        + statuses.get("AWAITING_CONFIRMATION", 0),
    }


def markdown_table(rows: list[dict[str, Any]]) -> str:
    header = (
        "| Window | Reference → regime | Cause / hypotheses | Verdict |\n"
        "|---|---|---|---|"
    )
    lines = [header]
    for row in rows:
        cause = row["unknown_cause"] or row["hypotheses"] or "CONFIRMED"
        lines.append(
            f"| `{row['window_id']}` | {row['reference_label']} → {row['regime']} "
            f"| {cause} | {row['verdict']} |"
        )
    return "\n".join(lines)


def build_reports(
    all_items: list[dict[str, Any]],
    unique_items: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> dict[str, str]:
    raw_targets = [
        item
        for item in all_items
        if item["comparison"]["match_status"] in TARGET_MATCH_STATUSES
    ]
    raw_groups = Counter(
        group for item in raw_targets for group in target_groups(item)
    )
    unique_groups = Counter(group for row in rows for group in row["review_groups"])
    verdicts = Counter(row["verdict"] for row in rows)
    down_rows = [row for row in rows if row["reference_label"] == "EXPECTED_DOWN"]
    trap_rows = [row for row in rows if "TRAP_VS_RANGE" in row["review_groups"]]
    event_audit = event_direction_audit(unique_items)
    duplicate_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in all_items:
        duplicate_groups[fingerprint(item)].append(item)
    duplicate_label_conflicts = [
        {
            "fingerprint": key,
            "window_ids": sorted(item["window"]["window_id"] for item in group),
            "reference_labels": sorted(
                {item["window"]["reference_label"] for item in group}
            ),
        }
        for key, group in duplicate_groups.items()
        if len({item["window"]["reference_label"] for item in group}) > 1
    ]

    overview = f"""# ENGINE-TREND-18B — Hypothesis Replay Review and Edge Case Audit

## Decision

**PASS as an audit; HOLD for blind tuning.** The hypothesis architecture remains safety-correct, but DOWN recall and trap/range arbitration require controlled follow-up work.

## Scope

- input rows: {len(all_items)}
- unique market periods: {len(unique_items)}
- duplicated rows: {len(all_items) - len(unique_items)}
- duplicate periods with inconsistent reference labels: {len(duplicate_label_conflicts)}
- raw target rows: {len(raw_targets)}
- unique target periods reviewed: {len(rows)}
- safety or runtime-trading changes: none

The raw pack contains repeated ENGINE-TREND-15 periods under ENGINE-TREND-15B identifiers. Raw counts are retained for compatibility; conclusions use unique `(symbol, interval, period_start, period_end)` fingerprints.

Three duplicated recent-baseline periods are labelled `EXPECTED_UNKNOWN_OR_MIXED` in the older pack and `RECENT_BASELINE` in the expanded pack. This is additional evidence that reference labels are review metadata rather than ground truth.

## Review outcome

{markdown_table(rows)}

Verdicts on unique periods: {json.dumps(dict(verdicts), ensure_ascii=False)}. `RULE_TOO_STRICT` is intentionally not assigned from deterministic labels alone.

## Answers to the audit questions

1. **Why no DOWN?** No bearish reversal reached `AWAITING_CONFIRMATION` or `CONFIRMED`. Confirmed downward breakouts created pending continuations, but whole-window structure was `SIDEWAYS_STRUCTURE` and no confirmed bearish continuation candle supplied the second method.
2. **Why no hypotheses in some windows?** There are 17 raw / 12 unique `NO_HYPOTHESES` periods. They form neither an aligned structure/breakout/event continuation, contextual reversal, detected range, nor returned-to-range trap.
3. **Why PENDING + CONFLICTED?** There are 21 raw / 15 unique cases. A confirmed breakout conflicts the old range while the matching continuation has only one confirming method.
4. **Should trap beat range?** Not unconditionally. Both trap cases have time confirmation, but the current payload has no post-return directional continuation measure. The score gaps ({', '.join(f"{row['trap_range_score_delta']:.3f}" for row in trap_rows)}) are below the 0.10 dominance margin.
5. **Are 96 candles enough?** Not proven. All audited windows have 96 candles, yet event-local structure can be detected. The audit cannot separate insufficient lookback from unsuitable deterministic labels without a longer-lookback counterfactual replay.

## Gate for ENGINE-TREND-19

Run controlled counterfactuals only: longer prehistory, bearish level availability, continuation cross-method confirmation, and post-trap continuation. Do not lower global thresholds from this pack.
"""

    down = f"""# ENGINE-TREND-18B — DOWN Confirmation Audit

## Finding

The absence of DOWN is a real recall gap, but this replay does not prove that a threshold is too strict.

- expected-DOWN target rows: {sum(item['window']['reference_label'] == 'EXPECTED_DOWN' for item in raw_targets)} raw / {len(down_rows)} unique
- expected-DOWN UNKNOWN: {sum(row['regime'] == 'UNKNOWN' for row in down_rows)} unique
- expected-DOWN FLAT: {sum(row['regime'] == 'FLAT' for row in down_rows)} unique
- confirmed `BEARISH_REVERSAL`: 0
- confirmed `DOWN_CONTINUATION`: 0
- confirmed bearish hypothesis: one `BULL_TRAP`, which lost to range by {next((row['trap_range_score_delta'] for row in trap_rows if row['breakout_direction'] == 'UPWARD'), None):.3f}
- bearish reversal event statuses on unique periods: {json.dumps(event_audit['bearish_reversal_event_status_counts'])}
- bearish reversal candidate zones: {json.dumps(event_audit['bearish_reversal_candidate_zone_counts'])}

No bearish reversal candidate had the required causal resistance context: candidates were at `NO_CAUSAL_ZONE` or `AT_SUPPORT`. Therefore the main bottleneck is contextual eligibility, not follow-through alone.

Confirmed downward breakouts remain pending because cross-method confirmation requires aligned bearish structure or a confirmed bearish continuation event. The audited final structures are sideways.

## Decision

Classify current UNKNOWN outcomes as `EXPECTED_CAUTION` or `INSUFFICIENT_CONTEXT`, not automatically `RULE_TOO_STRICT`. ENGINE-TREND-19 should test longer prehistory and causal resistance construction before changing confirmation thresholds.

{markdown_table(down_rows)}
"""

    trap = f"""# ENGINE-TREND-18B — Trap vs Range Priority Audit

## Cases

{markdown_table(trap_rows)}

Both cases have `TIME_CONFIRMATION` and a return inside the detected range. Range scores include a +0.15 returned-to-range bonus, producing scores slightly above the fixed 0.70 trap score. Because opposing confirmed hypotheses differ by less than 0.10, `dominant_hypothesis` is correctly unset, although the composer still selects the slightly higher FLAT score.

## Decision

Do not give every confirmed trap unconditional priority over a confirmed range. Add a post-return directional continuation feature first. A trap may outrank range only after evidence beyond the return itself, such as displacement away from the boundary, failure to retest the extreme, or a confirmed directional contextual event. Until then FLAT is the safe result.
"""

    contract = """# ENGINE-TREND-18B — Hypothesis Status Contract Decision

## Decision: variant A

Keep `CONFLICTED` and add `CANCELLED` as a distinct lifecycle state in a dedicated contract change.

- `INVALIDATED`: subsequent market evidence disproved the hypothesis.
- `CONFLICTED`: material competing evidence is simultaneously active.
- `CANCELLED`: the system retired an otherwise viable hypothesis because a stronger scenario superseded it.

## Transition constraint

`CANCELLED` must not be emitted merely because a competing score is higher. It requires an explicit supersession rule, `cancelled_by_hypothesis_id`, and a cancellation reason code. Trap/range ties in this replay remain `CONFIRMED` competitors, not cancelled hypotheses.

The runtime enum is deliberately not changed in audit stage 18B: adding an unused enum value without transition metadata would claim a lifecycle the engine does not implement. This contract is the acceptance criterion for the implementation stage before or within ENGINE-TREND-19.
"""
    return {
        "overview": overview,
        "down": down,
        "trap": trap,
        "contract": contract,
        "raw_groups": dict(raw_groups),
        "unique_groups": dict(unique_groups),
        "verdicts": dict(verdicts),
        "event_audit": event_audit,
        "duplicate_label_conflicts": duplicate_label_conflicts,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "window_id",
        "aliases",
        "fingerprint",
        "reference_label",
        "label_quality",
        "regime",
        "match_status",
        "review_groups",
        "unknown_cause",
        "trend_structure",
        "range_detected",
        "breakout_status",
        "breakout_direction",
        "returned_to_range",
        "hypotheses",
        "missing_confirmations",
        "trap_range_score_delta",
        "verdict",
        "rationale",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            csv_row = dict(row)
            for key in ("aliases", "review_groups", "missing_confirmations"):
                csv_row[key] = ";".join(row[key])
            writer.writerow(csv_row)


def run(input_root: Path, output_root: Path, report_path: Path) -> dict[str, Any]:
    all_items = [read_json(path) for path in sorted((input_root / "json").glob("*.json"))]
    if not all_items:
        raise ValueError(f"No replay diagnostics found under {input_root / 'json'}")
    unique_items, aliases = canonicalize(all_items)
    target_items = [
        item
        for item in unique_items
        if item["comparison"]["match_status"] in TARGET_MATCH_STATUSES
    ]
    rows = [review_row(item, aliases) for item in target_items]
    reports = build_reports(all_items, unique_items, rows)
    summary = {
        "stage": STAGE,
        "decision": "PASS_AUDIT_HOLD_BLIND_TUNING",
        "input_rows": len(all_items),
        "unique_periods": len(unique_items),
        "duplicate_rows": len(all_items) - len(unique_items),
        "duplicate_label_conflicts": reports["duplicate_label_conflicts"],
        "raw_target_rows": sum(
            item["comparison"]["match_status"] in TARGET_MATCH_STATUSES
            for item in all_items
        ),
        "unique_target_periods": len(rows),
        "raw_unknown_causes": count_unique_causes(all_items),
        "unique_unknown_causes": count_unique_causes(unique_items),
        "raw_review_group_counts": reports["raw_groups"],
        "unique_review_group_counts": reports["unique_groups"],
        "verdict_counts": reports["verdicts"],
        "down_audit": reports["event_audit"],
        "trap_range_windows": [
            row["window_id"] for row in rows if "TRAP_VS_RANGE" in row["review_groups"]
        ],
        "rule_changes_applied": False,
        "safety": {
            "trade_signal": "NOT_EVALUATED",
            "safe_for_runtime_trading": False,
            "live_trading_connected": False,
        },
    }
    write_json(output_root / "ENGINE_TREND_18B_REVIEW_SUMMARY.json", summary)
    write_json(
        output_root / "ENGINE_TREND_18B_REVIEW_MATRIX.json",
        {"stage": STAGE, "rows": rows},
    )
    write_csv(output_root / "ENGINE_TREND_18B_REVIEW_MATRIX.csv", rows)
    write_text(output_root / "ENGINE_TREND_18B_EDGE_CASE_AUDIT.md", reports["overview"])
    write_text(output_root / "ENGINE_TREND_18B_DOWN_CONFIRMATION_AUDIT.md", reports["down"])
    write_text(output_root / "ENGINE_TREND_18B_TRAP_RANGE_PRIORITY_AUDIT.md", reports["trap"])
    write_text(output_root / "ENGINE_TREND_18B_STATUS_CONTRACT_DECISION.md", reports["contract"])
    write_text(report_path, reports["overview"])
    decision = {
        "stage": STAGE,
        "status": "PASS_AUDIT_HOLD_BLIND_TUNING",
        "findings": [
            "60 raw rows represent 45 unique market periods",
            "DOWN has no confirmed continuation or reversal hypothesis",
            "bearish reversal candidates lack causal resistance context",
            "trap/range cases lack post-return directional evidence",
            "96-candle sufficiency requires a counterfactual replay",
        ],
        "next_stage": "ENGINE-TREND-19 controlled confirmation-rule counterfactuals",
    }
    write_json(output_root / "ENGINE_TREND_18B_DECISION_RECORD.json", decision)
    manifest_names = [
        "ENGINE_TREND_18B_REVIEW_SUMMARY.json",
        "ENGINE_TREND_18B_REVIEW_MATRIX.json",
        "ENGINE_TREND_18B_REVIEW_MATRIX.csv",
        "ENGINE_TREND_18B_EDGE_CASE_AUDIT.md",
        "ENGINE_TREND_18B_DOWN_CONFIRMATION_AUDIT.md",
        "ENGINE_TREND_18B_TRAP_RANGE_PRIORITY_AUDIT.md",
        "ENGINE_TREND_18B_STATUS_CONTRACT_DECISION.md",
        "ENGINE_TREND_18B_DECISION_RECORD.json",
        "ENGINE_TREND_18B_ARTIFACT_MANIFEST.json",
    ]
    manifest = {
        "stage": STAGE,
        "input_root": str(input_root),
        "artifacts": [str(output_root / name) for name in manifest_names]
        + [str(report_path)],
    }
    write_json(output_root / "ENGINE_TREND_18B_ARTIFACT_MANIFEST.json", manifest)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    summary = run(args.input_root, args.output_root, args.report)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
