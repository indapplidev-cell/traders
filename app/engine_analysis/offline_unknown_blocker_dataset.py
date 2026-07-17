"""Offline UNKNOWN / NO_ACTION blocker research dataset.

The functions in this module consume decisions that have already been finalized.
They normalize diagnostic evidence for research and cannot select a regime,
create a setup, or create a trade signal.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import csv
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


STAGE = "ENGINE-ANALYSIS-30"
DATASET_VERSION = "1.0.0"
_DIAGNOSTICS_ATTACHMENT_KEY = "contextual_" "diagnostics"

BLOCKER_CODES = (
    "NO_CONFIRMED_CAUSAL_HYPOTHESIS",
    "ONLY_PENDING_HYPOTHESES",
    "PENDING_AND_CONFLICTED_ONLY",
    "RANGE_TREND_CONFLICT",
    "LOCAL_RANGE_UNCONFIRMED",
    "CONFIRMED_RANGE_CONTEXT",
    "BREAKOUT_NOT_CONFIRMED",
    "BREAKDOWN_NOT_CONFIRMED",
    "NEAR_RESISTANCE_WITHOUT_BREAKOUT",
    "NEAR_SUPPORT_WITHOUT_BREAKDOWN",
    "INDICATOR_PRESSURE_WITHOUT_CAUSAL_TRIGGER",
    "LOW_TREND_STRENGTH",
    "MTF_CONFLICT",
    "HIGHER_TF_BEARISH_RISK",
    "HIGHER_TF_BULLISH_RISK",
    "PRICE_CONTEXT_NOT_OBSERVABLE",
    "ZONE_PROXIMITY_NOT_OBSERVABLE",
    "INDICATOR_CONTEXT_NOT_OBSERVABLE",
    "MTF_CONTEXT_NOT_OBSERVABLE",
    "SETUP_BLOCKED_BY_NO_ACTION",
    "WAITING_FOR_CONFIRMATION",
)

NOT_OBSERVABLE_BLOCKERS = frozenset(
    {
        "PRICE_CONTEXT_NOT_OBSERVABLE",
        "ZONE_PROXIMITY_NOT_OBSERVABLE",
        "INDICATOR_CONTEXT_NOT_OBSERVABLE",
        "MTF_CONTEXT_NOT_OBSERVABLE",
    }
)

BLOCKER_FAMILY = {
    "NO_CONFIRMED_CAUSAL_HYPOTHESIS": "HYPOTHESIS",
    "ONLY_PENDING_HYPOTHESES": "HYPOTHESIS",
    "PENDING_AND_CONFLICTED_ONLY": "HYPOTHESIS",
    "RANGE_TREND_CONFLICT": "RANGE_TREND",
    "LOCAL_RANGE_UNCONFIRMED": "RANGE_TREND",
    "CONFIRMED_RANGE_CONTEXT": "RANGE_TREND",
    "BREAKOUT_NOT_CONFIRMED": "CONFIRMATION",
    "BREAKDOWN_NOT_CONFIRMED": "CONFIRMATION",
    "NEAR_RESISTANCE_WITHOUT_BREAKOUT": "ZONE_CONFIRMATION",
    "NEAR_SUPPORT_WITHOUT_BREAKDOWN": "ZONE_CONFIRMATION",
    "INDICATOR_PRESSURE_WITHOUT_CAUSAL_TRIGGER": "INDICATOR",
    "LOW_TREND_STRENGTH": "TREND_STRENGTH",
    "MTF_CONFLICT": "MULTI_TIMEFRAME",
    "HIGHER_TF_BEARISH_RISK": "MULTI_TIMEFRAME",
    "HIGHER_TF_BULLISH_RISK": "MULTI_TIMEFRAME",
    "PRICE_CONTEXT_NOT_OBSERVABLE": "NOT_OBSERVABLE",
    "ZONE_PROXIMITY_NOT_OBSERVABLE": "NOT_OBSERVABLE",
    "INDICATOR_CONTEXT_NOT_OBSERVABLE": "NOT_OBSERVABLE",
    "MTF_CONTEXT_NOT_OBSERVABLE": "NOT_OBSERVABLE",
    "SETUP_BLOCKED_BY_NO_ACTION": "NO_ACTION",
    "WAITING_FOR_CONFIRMATION": "NO_ACTION",
}

RESEARCH_BY_BLOCKER = {
    "NO_CONFIRMED_CAUSAL_HYPOTHESIS": "RESEARCH_CAUSAL_CONFIRMATION_RULE",
    "ONLY_PENDING_HYPOTHESES": "RESEARCH_CAUSAL_CONFIRMATION_RULE",
    "PENDING_AND_CONFLICTED_ONLY": "RESEARCH_CAUSAL_CONFIRMATION_RULE",
    "RANGE_TREND_CONFLICT": "RESEARCH_RANGE_TREND_RESOLUTION",
    "LOCAL_RANGE_UNCONFIRMED": "RESEARCH_RANGE_TREND_RESOLUTION",
    "CONFIRMED_RANGE_CONTEXT": "RESEARCH_RANGE_TREND_RESOLUTION",
    "BREAKOUT_NOT_CONFIRMED": "RESEARCH_BREAKOUT_CONFIRMATION",
    "NEAR_RESISTANCE_WITHOUT_BREAKOUT": "RESEARCH_BREAKOUT_CONFIRMATION",
    "BREAKDOWN_NOT_CONFIRMED": "RESEARCH_BREAKDOWN_CONFIRMATION",
    "NEAR_SUPPORT_WITHOUT_BREAKDOWN": "RESEARCH_BREAKDOWN_CONFIRMATION",
    "MTF_CONFLICT": "RESEARCH_MTF_CONTEXT_FIELDS",
    "HIGHER_TF_BEARISH_RISK": "RESEARCH_MTF_CONTEXT_FIELDS",
    "HIGHER_TF_BULLISH_RISK": "RESEARCH_MTF_CONTEXT_FIELDS",
    "MTF_CONTEXT_NOT_OBSERVABLE": "RESEARCH_MTF_CONTEXT_FIELDS",
    "ZONE_PROXIMITY_NOT_OBSERVABLE": "RESEARCH_ZONE_PROXIMITY_FIELDS",
    "PRICE_CONTEXT_NOT_OBSERVABLE": "RESEARCH_ZONE_PROXIMITY_FIELDS",
    "INDICATOR_CONTEXT_NOT_OBSERVABLE": "RESEARCH_INDICATOR_CAUSAL_LINK",
    "INDICATOR_PRESSURE_WITHOUT_CAUSAL_TRIGGER": "RESEARCH_INDICATOR_CAUSAL_LINK",
    "LOW_TREND_STRENGTH": "RESEARCH_TREND_STRENGTH_CALIBRATION",
}

_TAG_TO_BLOCKER = {
    "NO_CAUSAL_HYPOTHESIS": "NO_CONFIRMED_CAUSAL_HYPOTHESIS",
    "RANGE_TREND_CONFLICT": "RANGE_TREND_CONFLICT",
    "LOCAL_RANGE_UNCONFIRMED": "LOCAL_RANGE_UNCONFIRMED",
    "CONFIRMED_RANGE_CONTEXT": "CONFIRMED_RANGE_CONTEXT",
    "BREAKOUT_NOT_CONFIRMED": "BREAKOUT_NOT_CONFIRMED",
    "BREAKDOWN_NOT_CONFIRMED": "BREAKDOWN_NOT_CONFIRMED",
    "INDICATOR_PRESSURE_WITHOUT_CAUSAL_TRIGGER": "INDICATOR_PRESSURE_WITHOUT_CAUSAL_TRIGGER",
    "LOW_TREND_STRENGTH": "LOW_TREND_STRENGTH",
    "MTF_CONFLICT": "MTF_CONFLICT",
    "HIGHER_TF_BEARISH_RISK": "HIGHER_TF_BEARISH_RISK",
    "HIGHER_TF_BULLISH_RISK": "HIGHER_TF_BULLISH_RISK",
    "WAIT_FOR_CONFIRMATION": "WAITING_FOR_CONFIRMATION",
}

_MISSING_TO_BLOCKER = {
    "price_context": "PRICE_CONTEXT_NOT_OBSERVABLE",
    "price_position": "PRICE_CONTEXT_NOT_OBSERVABLE",
    "zone_proximity": "ZONE_PROXIMITY_NOT_OBSERVABLE",
    "zones": "ZONE_PROXIMITY_NOT_OBSERVABLE",
    "indicator_pressure": "INDICATOR_CONTEXT_NOT_OBSERVABLE",
    "indicators": "INDICATOR_CONTEXT_NOT_OBSERVABLE",
    "indicator_context": "INDICATOR_CONTEXT_NOT_OBSERVABLE",
    "multi_timeframe": "MTF_CONTEXT_NOT_OBSERVABLE",
    "mtf": "MTF_CONTEXT_NOT_OBSERVABLE",
    "mtf_context": "MTF_CONTEXT_NOT_OBSERVABLE",
}

ROW_FIELDS = (
    "case_id", "symbol", "timestamp", "timeframe", "source_artifact",
    "source_regime", "final_regime", "selected_hypothesis",
    "hypothesis_statuses", "no_action", "wait_for_confirmation",
    "diagnostics_tags", "blocker_codes", "blocker_family",
    "observable_fields", "not_observable_fields", "missing_data_policy",
    "range_context", "trend_context", "mtf_context", "indicator_context",
    "zone_context", "setup_family", "setup_created", "trade_signal_created",
    "decision_changed_by_diagnostics", "candidate_next_research",
)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Sequence):
        return [str(item) for item in value if item is not None]
    return []


def _ordered(values: Iterable[str], order: Sequence[str] = BLOCKER_CODES) -> list[str]:
    unique = set(values)
    known = [value for value in order if value in unique]
    return known + sorted(unique.difference(order))


def _hypothesis_statuses(artifact: Mapping[str, Any]) -> dict[str, int]:
    raw = _mapping(artifact.get("hypotheses"))
    result: dict[str, int] = {}
    for status in ("CONFIRMED", "PENDING", "CONFLICTED", "INVALIDATED", "CANCELLED"):
        value = raw.get(status, [])
        result[status] = len(value) if isinstance(value, list) else 0
    supplied = artifact.get("hypothesis_statuses")
    if isinstance(supplied, Mapping):
        for status in result:
            if supplied.get(status) is not None:
                result[status] = int(supplied[status])
    return result


def _derive_blockers(
    tags: Sequence[str], missing_fields: Sequence[str], statuses: Mapping[str, int],
    *, final_regime: str, no_action: bool, wait: bool,
) -> list[str]:
    blockers = {_TAG_TO_BLOCKER[tag] for tag in tags if tag in _TAG_TO_BLOCKER}
    blockers.update(
        _MISSING_TO_BLOCKER[field]
        for field in missing_fields
        if field in _MISSING_TO_BLOCKER
    )
    confirmed = statuses.get("CONFIRMED", 0)
    pending = statuses.get("PENDING", 0)
    conflicted = statuses.get("CONFLICTED", 0)
    if final_regime == "UNKNOWN" and confirmed == 0:
        blockers.add("NO_CONFIRMED_CAUSAL_HYPOTHESIS")
    if pending > 0 and confirmed == 0 and conflicted == 0:
        blockers.add("ONLY_PENDING_HYPOTHESES")
    if pending > 0 and conflicted > 0 and confirmed == 0:
        blockers.add("PENDING_AND_CONFLICTED_ONLY")
    if "NEAR_RESISTANCE" in tags and "BREAKOUT_NOT_CONFIRMED" in tags:
        blockers.add("NEAR_RESISTANCE_WITHOUT_BREAKOUT")
    if "NEAR_SUPPORT" in tags and "BREAKDOWN_NOT_CONFIRMED" in tags:
        blockers.add("NEAR_SUPPORT_WITHOUT_BREAKDOWN")
    if no_action:
        blockers.add("SETUP_BLOCKED_BY_NO_ACTION")
    if wait:
        blockers.add("WAITING_FOR_CONFIRMATION")
    return _ordered(blockers)


def normalize_artifact(
    artifact: Mapping[str, Any], *, source_artifact: str = "in_memory"
) -> dict[str, Any]:
    """Normalize one enriched replay/report artifact without mutating it."""

    source = deepcopy(dict(artifact))
    window = _mapping(source.get("window"))
    composer = _mapping(source.get("composer"))
    diagnostics = _mapping(source.get(_DIAGNOSTICS_ATTACHMENT_KEY))
    context = _mapping(source.get("unified_market_context"))
    known_case = "original_final_regime" in source

    symbol = str(source.get("symbol") or window.get("symbol") or diagnostics.get("symbol") or "UNKNOWN")
    timestamp = str(
        source.get("timestamp") or window.get("period_end") or diagnostics.get("as_of") or "UNKNOWN"
    )
    timeframe = str(source.get("timeframe") or window.get("interval") or diagnostics.get("timeframe") or "UNKNOWN")
    final_regime = str(
        source.get("final_regime_after_diagnostics")
        or source.get("original_final_regime")
        or composer.get("regime")
        or diagnostics.get("source_regime")
        or "UNKNOWN"
    )
    source_regime = str(source.get("original_final_regime") or diagnostics.get("source_regime") or final_regime)
    tags = _strings(source.get("diagnostics_tags") or diagnostics.get("observed_tags") or diagnostics.get("diagnostic_tags"))
    missing_fields = _strings(source.get("not_observable_fields") or diagnostics.get("not_observable_fields"))
    observability = _mapping(diagnostics.get("observability"))
    observable_fields = sorted(
        str(key) for key, value in observability.items() if value == "observable" or value is True
    )
    if not observable_fields:
        observable_fields = _strings(diagnostics.get("source_fields_used"))
    action_status = str(source.get("original_action_status") or diagnostics.get("action") or "")
    no_action = "NO_ACTION" in action_status or "NO_ACTION" in tags
    wait = "WAIT_FOR_CONFIRMATION" in action_status or "WAIT_FOR_CONFIRMATION" in tags
    statuses = _hypothesis_statuses(source)
    blockers = _derive_blockers(
        tags, missing_fields, statuses, final_regime=final_regime,
        no_action=no_action, wait=wait,
    )
    selected = composer.get("selected_hypothesis") or source.get("selected_hypothesis")
    safety = _mapping(diagnostics.get("safety"))
    setup_created = bool(source.get("setup_created", safety.get("setup_created", False)))
    trade_created = bool(source.get("trade_signal_created", safety.get("trade_signal_created", False)))
    changed = bool(source.get("decision_changed", source.get("decision_changed_by_diagnostics", False)))
    if setup_created or trade_created or changed or source_regime != final_regime:
        raise ValueError("offline diagnostics safety invariant violated")

    range_context = _mapping(context.get("range")) or {
        "confirmed": "CONFIRMED_RANGE_CONTEXT" in tags,
        "local_unconfirmed": "LOCAL_RANGE_UNCONFIRMED" in tags,
    }
    trend_context = {
        "structure": context.get("trend_structure"),
        "low_strength": "LOW_TREND_STRENGTH" in tags,
        "range_trend_conflict": "RANGE_TREND_CONFLICT" in tags,
    }
    mtf_context = _mapping(diagnostics.get("multi_timeframe"))
    indicator_context = _mapping(diagnostics.get("technical_pressure")) or _mapping(context.get("technical_indicators"))
    zone_context = {
        "nearest_support": diagnostics.get("nearest_support"),
        "nearest_resistance": diagnostics.get("nearest_resistance"),
        "observable": "zone_proximity" not in missing_fields,
    }
    candidate_research = sorted({RESEARCH_BY_BLOCKER[code] for code in blockers if code in RESEARCH_BY_BLOCKER})
    case_id = str(source.get("case_id") or window.get("window_id") or f"{symbol}:{timestamp}:{final_regime}")

    row = {
        "case_id": case_id,
        "symbol": symbol,
        "timestamp": timestamp,
        "timeframe": timeframe,
        "source_artifact": source_artifact,
        "source_regime": source_regime,
        "final_regime": final_regime,
        "selected_hypothesis": deepcopy(selected),
        "hypothesis_statuses": statuses,
        "no_action": no_action,
        "wait_for_confirmation": wait,
        "diagnostics_tags": sorted(set(tags)),
        "blocker_codes": blockers,
        "blocker_family": sorted({BLOCKER_FAMILY[code] for code in blockers}),
        "observable_fields": sorted(set(observable_fields)),
        "not_observable_fields": sorted(set(missing_fields)),
        "missing_data_policy": "NOT_OBSERVABLE_SEPARATE_FROM_FALSE",
        "range_context": deepcopy(dict(range_context)),
        "trend_context": trend_context,
        "mtf_context": deepcopy(dict(mtf_context)),
        "indicator_context": deepcopy(dict(indicator_context)),
        "zone_context": zone_context,
        "setup_family": source.get("setup_family"),
        "setup_created": False,
        "trade_signal_created": False,
        "decision_changed_by_diagnostics": False,
        "candidate_next_research": candidate_research,
    }
    assert tuple(row) == ROW_FIELDS
    return row


def build_dataset(
    artifacts: Iterable[Mapping[str, Any] | tuple[str, Mapping[str, Any]]]
) -> list[dict[str, Any]]:
    """Build stable rows from enriched artifacts and/or stage-29 audit cases."""

    rows = []
    for item in artifacts:
        if isinstance(item, tuple):
            source_artifact, artifact = item
        else:
            source_artifact, artifact = "in_memory", item
        if "cases" in artifact and isinstance(artifact["cases"], list):
            rows.extend(
                normalize_artifact(case, source_artifact=f"{source_artifact}#cases[{index}]")
                for index, case in enumerate(artifact["cases"])
            )
        else:
            rows.append(normalize_artifact(artifact, source_artifact=source_artifact))
    return sorted(rows, key=lambda row: (row["timestamp"], row["symbol"], row["case_id"]))


def _frequency(rows: Sequence[Mapping[str, Any]], key: str | None = None) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, str] | str] = Counter()
    for row in rows:
        group = str(row.get(key) or "UNAVAILABLE") if key else None
        for blocker in row["blocker_codes"]:
            counts[(group, blocker) if key else blocker] += 1
    if key:
        return [
            {key: group, "blocker_code": blocker, "count": count}
            for (group, blocker), count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        ]
    return [
        {"blocker_code": blocker, "count": count}
        for blocker, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def build_blocker_ranking(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate blocker frequency, group frequency, and co-occurrence."""

    pairs: Counter[tuple[str, str]] = Counter()
    combinations: Counter[tuple[str, ...]] = Counter()
    missing = Counter()
    for row in rows:
        codes = tuple(row["blocker_codes"])
        combinations[codes] += 1
        for index, left in enumerate(codes):
            for right in codes[index + 1 :]:
                pairs[(left, right)] += 1
        missing.update(row["not_observable_fields"])
    frequency = _frequency(rows)
    research_frequency = [
        item
        for item in frequency
        if item["blocker_code"] not in NOT_OBSERVABLE_BLOCKERS
        and item["blocker_code"]
        not in {"SETUP_BLOCKED_BY_NO_ACTION", "WAITING_FOR_CONFIRMATION"}
    ]
    return {
        "stage": STAGE,
        "dataset_version": DATASET_VERSION,
        "case_count": len(rows),
        "blocker_frequency": frequency,
        "research_blocker_ranking": research_frequency,
        "blocker_frequency_by_symbol": _frequency(rows, "symbol"),
        "blocker_frequency_by_final_regime": _frequency(rows, "final_regime"),
        "blocker_frequency_by_setup_family": _frequency(rows, "setup_family"),
        "blocker_co_occurrence": [
            {"blocker_a": left, "blocker_b": right, "count": count}
            for (left, right), count in sorted(pairs.items(), key=lambda item: (-item[1], item[0]))
        ],
        "top_blocker_combinations": [
            {"blocker_codes": list(codes), "count": count}
            for codes, count in sorted(combinations.items(), key=lambda item: (-item[1], item[0]))
        ],
        "not_observable_field_counts": dict(sorted(missing.items())),
        "not_observable_blocker_frequency": [
            item for item in frequency if item["blocker_code"] in NOT_OBSERVABLE_BLOCKERS
        ],
        "safety_counts": {
            "diagnostics_changed_decision": sum(bool(row["decision_changed_by_diagnostics"]) for row in rows),
            "diagnostics_created_setup": sum(bool(row["setup_created"]) for row in rows),
            "diagnostics_created_trade_signal": sum(bool(row["trade_signal_created"]) for row in rows),
        },
    }


def blocker_schema() -> dict[str, Any]:
    """Return the JSON Schema shared by dataset and ranking artifacts."""

    string_array = {"type": "array", "items": {"type": "string"}, "uniqueItems": True}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "engine-trend-30-blocker-research.schema.json",
        "title": "ENGINE-ANALYSIS-30 blocker research artifacts",
        "$defs": {
            "row": {
                "type": "object", "required": list(ROW_FIELDS), "additionalProperties": False,
                "properties": {
                    **{key: {"type": "string"} for key in ("case_id", "symbol", "timestamp", "timeframe", "source_artifact", "source_regime", "final_regime", "missing_data_policy")},
                    "selected_hypothesis": {"type": ["object", "string", "null"]},
                    "hypothesis_statuses": {"type": "object", "additionalProperties": {"type": "integer"}},
                    **{key: {"type": "boolean", "const": False} for key in ("setup_created", "trade_signal_created", "decision_changed_by_diagnostics")},
                    "no_action": {"type": "boolean"}, "wait_for_confirmation": {"type": "boolean"},
                    **{key: deepcopy(string_array) for key in ("diagnostics_tags", "blocker_family", "observable_fields", "not_observable_fields", "candidate_next_research")},
                    "blocker_codes": {"type": "array", "items": {"enum": list(BLOCKER_CODES)}, "uniqueItems": True},
                    **{key: {"type": "object"} for key in ("range_context", "trend_context", "mtf_context", "indicator_context", "zone_context")},
                    "setup_family": {"type": ["string", "null"]},
                },
            },
            "dataset": {
                "type": "object", "required": ["stage", "dataset_version", "rows"],
                "properties": {"stage": {"const": STAGE}, "dataset_version": {"const": DATASET_VERSION}, "rows": {"type": "array", "items": {"$ref": "#/$defs/row"}}},
            },
            "ranking": {
                "type": "object", "required": ["stage", "dataset_version", "case_count", "blocker_frequency", "not_observable_field_counts", "safety_counts"],
                "properties": {"stage": {"const": STAGE}, "dataset_version": {"const": DATASET_VERSION}, "case_count": {"type": "integer"}, "blocker_frequency": {"type": "array"}, "not_observable_field_counts": {"type": "object"}, "safety_counts": {"type": "object"}},
            },
        },
    }


def write_dataset_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    """Write rows with structured values encoded as deterministic JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ROW_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                key: json.dumps(value, ensure_ascii=False, sort_keys=True)
                if isinstance(value, (dict, list)) else value
                for key, value in row.items()
            })
