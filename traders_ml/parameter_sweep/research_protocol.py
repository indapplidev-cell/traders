"""Fail-closed research protocol for Parameter Sweep holdout isolation.

This module contains no production runtime integration.  It owns the phase
state, finalist freeze, one-shot holdout ledger, and run-local diagnostic
artifacts used by the offline research engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
import json
from pathlib import Path
import statistics
from typing import Any, Callable, Iterable, Mapping, Sequence

from .artifact_writer import DEFAULT_ARTIFACT_WRITER


class ResearchPhase(str, Enum):
    CALIBRATION_SEARCH = "CALIBRATION_SEARCH"
    SEPARABILITY_ANALYSIS = "SEPARABILITY_ANALYSIS"
    DATA_DRIVEN_RANGE_GENERATION = "DATA_DRIVEN_RANGE_GENERATION"
    VALIDATION_RANKING = "VALIDATION_RANKING"
    FINALIST_FREEZE = "FINALIST_FREEZE"
    HOLDOUT_EVALUATION = "HOLDOUT_EVALUATION"
    FINAL_REPORT = "FINAL_REPORT"


class ResearchProtocolError(RuntimeError):
    """Stable research-methodology failure with a machine-readable code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(slots=True)
class HoldoutAccessPolicy:
    """Capability guard: outcome rows are visible only after finalist freeze."""

    phase: ResearchPhase = ResearchPhase.CALIBRATION_SEARCH
    freeze_hash: str | None = None
    frozen_finalists: frozenset[str] = frozenset()
    finalist_hashes: dict[str, str] = field(default_factory=dict)
    evaluated_finalists: set[str] = field(default_factory=set)
    holdout_opened: bool = False

    def transition(self, phase: ResearchPhase) -> None:
        if self.holdout_opened and phase not in {
            ResearchPhase.HOLDOUT_EVALUATION, ResearchPhase.FINAL_REPORT,
        }:
            raise ResearchProtocolError("POST_HOLDOUT_RETUNING_FORBIDDEN")
        if phase is ResearchPhase.HOLDOUT_EVALUATION and not self.freeze_hash:
            raise ResearchProtocolError("HOLDOUT_ACCESS_BEFORE_FINALIST_FREEZE")
        self.phase = phase

    def install_freeze(self, freeze: Mapping[str, Any]) -> None:
        if self.holdout_opened:
            raise ResearchProtocolError("FINALIST_FREEZE_IMMUTABLE")
        finalists = freeze.get("finalists")
        if not isinstance(finalists, list):
            raise ResearchProtocolError("FINALIST_FREEZE_INVALID")
        expected = canonical_hash({k: v for k, v in freeze.items() if k != "freeze_hash"})
        if freeze.get("freeze_hash") != expected:
            raise ResearchProtocolError("FINALIST_FREEZE_HASH_MISMATCH")
        if self.freeze_hash is not None and self.freeze_hash != expected:
            raise ResearchProtocolError("FINALIST_FREEZE_IMMUTABLE")
        self.freeze_hash = expected
        self.frozen_finalists = frozenset(str(item["finalist_id"]) for item in finalists)
        self.finalist_hashes = {
            str(item["finalist_id"]): str(item["config_hash"]) for item in finalists
        }
        self.phase = ResearchPhase.FINALIST_FREEZE

    def holdout_rows(
        self, rows: Sequence[Mapping[str, Any]], *, finalist_id: str,
        config_hash: str,
    ) -> list[dict[str, Any]]:
        if self.phase is not ResearchPhase.HOLDOUT_EVALUATION or not self.freeze_hash:
            raise ResearchProtocolError("HOLDOUT_ACCESS_BEFORE_FINALIST_FREEZE")
        if finalist_id not in self.frozen_finalists:
            raise ResearchProtocolError("HOLDOUT_CONFIG_NOT_IN_FINALIST_FREEZE")
        if self.finalist_hashes[finalist_id] != config_hash:
            raise ResearchProtocolError("FINALIST_CONFIG_HASH_MISMATCH")
        if finalist_id in self.evaluated_finalists:
            raise ResearchProtocolError("HOLDOUT_ONE_SHOT_ALREADY_EVALUATED")
        self.holdout_opened = True
        self.evaluated_finalists.add(finalist_id)
        return [dict(row) for row in rows]


def canonical_hash(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), default=str,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def not_evaluated_metrics() -> dict[str, str]:
    return {
        "status": "NOT_EVALUATED",
        "trade_count": "NOT_EVALUATED",
        "expectancy_R": "NOT_EVALUATED",
        "profit_factor": "NOT_EVALUATED",
        "net_pnl": "NOT_EVALUATED",
        "max_drawdown": "NOT_EVALUATED",
    }


def assert_validation_only_rows(rows: Iterable[Mapping[str, Any]]) -> None:
    forbidden = {
        "holdout", "holdout_expectancy", "holdout_pf", "holdout_pnl",
        "holdout_drawdown", "holdout_trade_count",
    }
    for row in rows:
        if forbidden & set(row):
            raise ResearchProtocolError("HOLDOUT_METRIC_IN_VALIDATION_RANKING")


def create_finalist_freeze(
    *, campaign_id: str, dataset_fingerprint: str, split_fingerprint: str,
    baseline_id: str, search_space_hash: str, selection_rule: Mapping[str, Any],
    ranked_rows: Sequence[Mapping[str, Any]], finalist_count: int,
    symbol: str | None = None,
    freeze_timestamp: str | None = None,
) -> dict[str, Any]:
    assert_validation_only_rows(ranked_rows)
    selected = list(ranked_rows[:finalist_count])
    payload: dict[str, Any] = {
        "campaign_id": campaign_id,
        "symbol": symbol,
        "SYMBOL": symbol,
        "dataset_fingerprint": dataset_fingerprint,
        "split_fingerprint": split_fingerprint,
        "baseline_id": baseline_id,
        "search_space_hash": search_space_hash,
        "selection_rule_hash": canonical_hash(selection_rule),
        "finalist_count_requested": finalist_count,
        "finalist_count_selected": len(selected),
        "finalists": [
            {
                "finalist_id": str(row["config_id"]),
                "config_hash": str(row["config_id"]),
                "parameters": dict(
                    row.get("candidate_parameters") or row.get("overrides") or {}
                ),
                "validation_metrics_snapshot": {
                    key: row.get(key) for key in (
                        "trade_count", "win_rate", "expectancy_R", "profit_factor",
                        "net_pnl", "max_drawdown", "symbol_coverage",
                        "independent_period_count", "performance_class",
                    )
                },
            }
            for row in selected
        ],
        "freeze_timestamp": freeze_timestamp or datetime.now(timezone.utc).isoformat(),
    }
    payload["freeze_hash"] = canonical_hash(payload)
    return payload


def write_immutable_freeze(path: Path, freeze: Mapping[str, Any]) -> None:
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ResearchProtocolError("FINALIST_FREEZE_INVALID") from error
        if existing != dict(freeze):
            raise ResearchProtocolError("FINALIST_FREEZE_IMMUTABLE")
        return
    DEFAULT_ARTIFACT_WRITER.atomic_json(path, dict(freeze), operation="finalist_freeze_create")


ENTRY_FEATURES = (
    "symbol", "direction", "setup_type", "regime", "strategy_score",
    "impulse_absolute_pct", "impulse_atr_ratio", "atr", "volume_ratio",
    "momentum", "one_min_confirmation_count", "stop_distance_bps",
    "target_distance_bps", "gross_rr", "net_rr", "required_rr", "p_win_raw",
    "expected_ev_r", "volatility_state",
)


def build_winner_loser_dataset(
    calibration_rows: Sequence[Mapping[str, Any]],
    validation_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Extract causal entry features from calibration/validation only."""
    result: list[dict[str, Any]] = []
    for split, rows in (("CALIBRATION", calibration_rows), ("VALIDATION", validation_rows)):
        for source in rows:
            outcome = source.get("net_pnl")
            if outcome is None:
                continue
            decision_ts = source.get("entry_decision_timestamp", source.get("opened_at_ms", source.get("boundary_ms")))
            feature_ts = source.get("feature_timestamp", source.get("market_data_watermark_ms", decision_ts))
            if decision_ts is None or feature_ts is None or int(feature_ts) > int(decision_ts):
                continue
            numeric = float(outcome)
            row: dict[str, Any] = {
                "split": split,
                "label": "WIN" if numeric > 0 else "LOSS" if numeric < 0 else "BREAKEVEN",
                "entry_decision_timestamp": int(decision_ts),
                "feature_timestamp": int(feature_ts),
                "causality": "FEATURE_TIMESTAMP_LTE_ENTRY_DECISION_TIMESTAMP",
                "features": {},
            }
            for key in ENTRY_FEATURES:
                if source.get(key) is not None:
                    row["features"][key] = source[key]
            timestamp = datetime.fromtimestamp(int(decision_ts) / 1000, timezone.utc)
            row["features"].update({"time_of_day_utc": timestamp.strftime("%H:%M"), "day_of_week_utc": timestamp.weekday()})
            result.append(row)
    return result


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]], *, operation: str) -> None:
    rendered = "".join(json.dumps(dict(row), sort_keys=True, default=str) + "\n" for row in rows)
    DEFAULT_ARTIFACT_WRITER.atomic_text(path, rendered or "\n", operation=operation)


def _quantiles(values: Sequence[float]) -> dict[str, float] | None:
    if not values:
        return None
    ordered = sorted(values)
    def at(fraction: float) -> float:
        return ordered[round((len(ordered) - 1) * fraction)]
    return {"q10": at(.1), "q25": at(.25), "q50": statistics.median(ordered), "q75": at(.75), "q90": at(.9)}


def build_data_driven_ranges(
    *, search_space: Mapping[str, Sequence[Any]], baseline: Mapping[str, Any],
    winner_loser_rows: Sequence[Mapping[str, Any]], proposals: Mapping[str, Sequence[Any]] | None = None,
) -> dict[str, Any]:
    """Build an explicit run-local override artifact; never writes YAML."""
    proposed = proposals or {}
    ranges = []
    for key, current in sorted(search_space.items()):
        winners = [float(row["features"][key]) for row in winner_loser_rows if row["label"] == "WIN" and isinstance(row.get("features", {}).get(key), (int, float))]
        losers = [float(row["features"][key]) for row in winner_loser_rows if row["label"] == "LOSS" and isinstance(row.get("features", {}).get(key), (int, float))]
        suggestion = list(proposed[key]) if key in proposed else None
        ranges.append({
            "canonical_parameter_key": key,
            "baseline": baseline.get(key),
            "current_range": list(current),
            "observed_quantiles": _quantiles(winners + losers),
            "winner_distribution": _quantiles(winners),
            "loser_distribution": _quantiles(losers),
            "proposed_range": suggestion,
            "reason": "EXPLICIT_RUN_LOCAL_PROPOSAL" if suggestion is not None else "INSUFFICIENT_EVIDENCE_NO_AUTOMATIC_PROPOSAL",
            "boundary_status": "PROPOSAL_OUTSIDE_CURRENT_RANGE" if suggestion and not set(suggestion).issubset(set(current)) else "WITHIN_CURRENT_OR_NOT_PROPOSED",
        })
    return {
        "artifact_type": "RUN_LOCAL_RESEARCH_OVERRIDE",
        "mutates_yaml": False,
        "global_authority": False,
        "ranges": ranges,
    }


def load_run_local_search_ranges(
    path: Path, base_space: Mapping[str, Sequence[Any]],
) -> dict[str, list[Any]]:
    """Apply only explicit proposals from one named run artifact."""
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ResearchProtocolError("RUN_LOCAL_RANGE_ARTIFACT_INVALID") from error
    if artifact.get("mutates_yaml") is not False or artifact.get("global_authority") is not False:
        raise ResearchProtocolError("RUN_LOCAL_RANGE_ARTIFACT_INVALID")
    result = {key: list(values) for key, values in base_space.items()}
    for row in artifact.get("ranges", []):
        key = str(row.get("canonical_parameter_key"))
        proposal = row.get("proposed_range")
        if proposal is None:
            continue
        if key not in result or not isinstance(proposal, list) or not proposal:
            raise ResearchProtocolError("RUN_LOCAL_RANGE_ARTIFACT_INVALID")
        result[key] = list(proposal)
    return result


def orchestrate_research_blocks(
    block1_result: str, *, run_block2: Callable[[], Any],
    run_block3: Callable[[], Any], block4: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    valid = {"POSITIVE_CONFIG_FOUND", "NO_POSITIVE_CONFIG_IN_CURRENT_SPACE"}
    if block1_result not in valid:
        raise ResearchProtocolError("BLOCK1_REAL_BLOCKER")
    result = {"BLOCK1": block1_result}
    result["BLOCK2"] = run_block2()
    result["BLOCK3"] = run_block3()
    result["BLOCK4_REACHABLE"] = True
    if block4 is not None:
        result["BLOCK4"] = block4()
    return result


def holdout_result_hash(rows: Sequence[Mapping[str, Any]]) -> str:
    return canonical_hash(list(rows))
