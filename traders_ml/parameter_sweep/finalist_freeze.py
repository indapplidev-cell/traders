"""Immutable, holdout-blind finalist freeze for single-symbol research campaigns."""

from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from app.config.yaml_authority import RESEARCH_PATH, load_research_parameters
from .artifact_writer import DEFAULT_ARTIFACT_WRITER
from .universe import validate_parameter_sweep_symbol


FREEZE_SCHEMA_VERSION = 1
CANONICAL_SERIALIZATION_VERSION = "canonical-json-sort-keys-utf8-v1"
HANDOFF_ARTIFACT = "VALIDATION_RANKING_HANDOFF"


class FinalistFreezeError(RuntimeError):
    """Stable fail-closed finalist-freeze failure."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_fingerprint(value: object) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


def _read_json(path: Path, missing_code: str) -> dict[str, Any]:
    if not path.is_file():
        raise FinalistFreezeError(missing_code)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise FinalistFreezeError("FAIL_CLOSED_INVALID_VALIDATION_RANKING_HANDOFF") from error
    if not isinstance(value, dict):
        raise FinalistFreezeError("FAIL_CLOSED_INVALID_VALIDATION_RANKING_HANDOFF")
    return value


def _handoff_content(raw: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: deepcopy(value) for key, value in raw.items()
        if key not in {"handoff_fingerprint", "validation_ranking_handoff_fingerprint"}
    }


def validation_ranking_handoff_fingerprint(raw: Mapping[str, Any]) -> str:
    return canonical_fingerprint(_handoff_content(raw))


def _contains_holdout_key(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).lower()
            if normalized == "holdout_opened" and item is False:
                continue
            if normalized == "holdout_reads" and item == 0:
                continue
            if "holdout" in normalized or _contains_holdout_key(item):
                return True
        return False
    if isinstance(value, list):
        return any(_contains_holdout_key(item) for item in value)
    return False


def resolve_requested_finalist_count(path: Path = RESEARCH_PATH) -> tuple[int, str]:
    policy = load_research_parameters(path)
    return (
        policy.artifact.finalist_config_count,
        "config/research/research_parameters.yaml:artifact.finalist_config_count",
    )


def _fail_campaign(condition: bool) -> None:
    if not condition:
        raise FinalistFreezeError("FAIL_CLOSED_CAMPAIGN_MISMATCH")


def _required(candidate: Mapping[str, Any], key: str) -> Any:
    if key not in candidate:
        raise FinalistFreezeError("FAIL_CLOSED_INVALID_VALIDATION_RANKING_HANDOFF")
    return candidate[key]


def _candidate_projection(candidate: Mapping[str, Any], freeze_rank: int) -> dict[str, Any]:
    signature = str(_required(candidate, "behavioral_signature"))
    representative = str(_required(candidate, "representative_config_id"))
    members = [str(item) for item in _required(candidate, "member_config_ids")]
    if not signature or not representative or not members or representative not in members:
        raise FinalistFreezeError("FAIL_CLOSED_INVALID_VALIDATION_RANKING_HANDOFF")
    canonical_rank = int(_required(candidate, "canonical_validation_rank"))
    gates = _required(candidate, "canonical_gate_results")
    parameters = _required(candidate, "parameters")
    robustness = _required(candidate, "robustness_diagnostics")
    if not isinstance(gates, Mapping) or not isinstance(parameters, Mapping) or not isinstance(robustness, Mapping):
        raise FinalistFreezeError("FAIL_CLOSED_INVALID_VALIDATION_RANKING_HANDOFF")
    return {
        "freeze_rank": freeze_rank,
        "behavioral_signature": signature,
        "representative_config_id": representative,
        "member_config_ids": members,
        "parameters": dict(parameters),
        "validation_trade_count": int(_required(candidate, "validation_trade_count")),
        "wins": int(_required(candidate, "wins")),
        "losses": int(_required(candidate, "losses")),
        "neutrals": int(_required(candidate, "neutrals")),
        "net_pnl": _required(candidate, "net_pnl"),
        "expectancy_r": candidate.get("expectancy_r"),
        "stored_profit_factor": candidate.get("stored_profit_factor"),
        "profit_factor_available": bool(_required(candidate, "profit_factor_available")),
        "profit_factor_ranking_value": _required(candidate, "profit_factor_ranking_value"),
        "max_drawdown": _required(candidate, "max_drawdown"),
        "independent_periods": int(_required(candidate, "independent_periods")),
        "canonical_gate_results": dict(gates),
        "canonical_validation_rank": canonical_rank,
        "robustness_diagnostics": dict(robustness),
    }


def _validate_handoff(
    raw: Mapping[str, Any], *, symbol: str, profile: str,
    dataset_fingerprint: str, calibration_split_fingerprint: str,
    validation_split_fingerprint: str, validation_policy_fingerprint: str,
    ranking_policy_fingerprint: str, parameter_registry_fingerprint: str,
) -> tuple[list[dict[str, Any]], int, int, str]:
    if raw.get("artifact") != HANDOFF_ARTIFACT or int(raw.get("schema_version", -1)) != 1:
        raise FinalistFreezeError("FAIL_CLOSED_INVALID_VALIDATION_RANKING_HANDOFF")
    if _contains_holdout_key(raw):
        raise FinalistFreezeError("FAIL_CLOSED_HOLDOUT_DATA_IN_VALIDATION_RANKING_HANDOFF")
    fingerprint = validation_ranking_handoff_fingerprint(raw)
    declared = raw.get("validation_ranking_handoff_fingerprint", raw.get("handoff_fingerprint"))
    if declared is not None and declared != fingerprint:
        raise FinalistFreezeError("FAIL_CLOSED_CAMPAIGN_MISMATCH")
    expected = {
        "symbol": symbol, "profile": profile,
        "dataset_fingerprint": dataset_fingerprint,
        "calibration_split_fingerprint": calibration_split_fingerprint,
        "validation_split_fingerprint": validation_split_fingerprint,
        "validation_policy_fingerprint": validation_policy_fingerprint,
        "ranking_policy_fingerprint": ranking_policy_fingerprint,
        "parameter_registry_fingerprint": parameter_registry_fingerprint,
    }
    for key, value in expected.items():
        _fail_campaign(raw.get(key) == value)
    ranking = raw.get("eligible_behavioral_representatives")
    descriptive = raw.get("descriptive_non_eligible_ranking")
    if not isinstance(ranking, list) or not isinstance(descriptive, list):
        raise FinalistFreezeError("FAIL_CLOSED_INVALID_VALIDATION_RANKING_HANDOFF")
    signatures: set[str] = set()
    projected: list[dict[str, Any]] = []
    previous_rank = 0
    eligible_numeric = 0
    for index, candidate in enumerate(ranking, start=1):
        if not isinstance(candidate, Mapping) or candidate.get("validation_eligible") is not True:
            raise FinalistFreezeError("FAIL_CLOSED_INVALID_VALIDATION_RANKING_HANDOFF")
        row = _candidate_projection(candidate, index)
        if row["behavioral_signature"] in signatures:
            raise FinalistFreezeError("FAIL_CLOSED_DUPLICATE_BEHAVIORAL_REPRESENTATIVE")
        if row["canonical_validation_rank"] <= previous_rank:
            raise FinalistFreezeError("FAIL_CLOSED_INVALID_VALIDATION_RANKING_HANDOFF")
        signatures.add(row["behavioral_signature"])
        previous_rank = row["canonical_validation_rank"]
        eligible_numeric += len(row["member_config_ids"])
        projected.append(row)
    return projected, eligible_numeric, len(descriptive), fingerprint


def _freeze_payload(
    *, raw: Mapping[str, Any], finalists: Sequence[Mapping[str, Any]],
    requested: int, handoff_fingerprint: str, policy_source: str,
) -> dict[str, Any]:
    reason = (
        "ZERO_ELIGIBLE_VALIDATION_FINALISTS" if not finalists
        else "TOP_ELIGIBLE_BEHAVIORAL_REPRESENTATIVES_IN_HANDOFF_CANONICAL_ORDER"
    )
    return {
        "freeze_schema_version": FREEZE_SCHEMA_VERSION,
        "canonical_serialization_version": CANONICAL_SERIALIZATION_VERSION,
        "symbol": raw["symbol"], "profile": raw["profile"],
        "dataset_fingerprint": raw["dataset_fingerprint"],
        "calibration_split_fingerprint": raw["calibration_split_fingerprint"],
        "validation_split_fingerprint": raw["validation_split_fingerprint"],
        "validation_policy_fingerprint": raw["validation_policy_fingerprint"],
        "ranking_policy_fingerprint": raw["ranking_policy_fingerprint"],
        "parameter_registry_fingerprint": raw["parameter_registry_fingerprint"],
        "validation_ranking_handoff_fingerprint": handoff_fingerprint,
        "requested_finalist_count": requested,
        "selected_finalist_count": len(finalists),
        "finalist_count_policy_source": policy_source,
        "selection_reason": reason,
        "created_from_phase": "VALIDATION_RANKING",
        "finalists": [dict(row) for row in finalists],
    }


def _complete_freeze(payload: Mapping[str, Any]) -> dict[str, Any]:
    content_hash = canonical_fingerprint(payload)
    return {
        **dict(payload),
        "freeze_id": f"finalist-freeze:v1:{content_hash}",
        "finalist_freeze_content_hash": content_hash,
    }


def verify_freeze(freeze: Mapping[str, Any], expected: Mapping[str, Any] | None = None) -> None:
    payload = {
        key: deepcopy(value) for key, value in freeze.items()
        if key not in {"freeze_id", "finalist_freeze_content_hash"}
    }
    content_hash = canonical_fingerprint(payload)
    if (
        freeze.get("finalist_freeze_content_hash") != content_hash
        or freeze.get("freeze_id") != f"finalist-freeze:v1:{content_hash}"
    ):
        raise FinalistFreezeError("FAIL_CLOSED_FINALIST_FREEZE_MUTATED")
    if expected is not None and dict(freeze) != dict(expected):
        raise FinalistFreezeError("FAIL_CLOSED_FINALIST_FREEZE_MUTATED")


def _write_immutable(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise FinalistFreezeError("FAIL_CLOSED_FINALIST_FREEZE_MUTATED") from error
        verify_freeze(existing, value) if path.name == "FINALIST_FREEZE.json" else None
        if existing != dict(value):
            raise FinalistFreezeError("FAIL_CLOSED_FINALIST_FREEZE_MUTATED")
        return
    DEFAULT_ARTIFACT_WRITER.atomic_json(path, dict(value), operation="immutable_finalist_freeze")


def run_finalist_freeze(
    *, handoff_path: Path, output: Path, symbol: object, profile: str,
    dataset_fingerprint: str, calibration_split_fingerprint: str,
    validation_split_fingerprint: str, validation_policy_fingerprint: str,
    ranking_policy_fingerprint: str, parameter_registry_fingerprint: str,
    research_parameters_path: Path = RESEARCH_PATH,
) -> dict[str, Any]:
    selected_symbol = validate_parameter_sweep_symbol(symbol)
    raw = _read_json(
        handoff_path, "FAIL_CLOSED_MISSING_VALIDATION_RANKING_HANDOFF",
    )
    try:
        candidates, eligible_numeric, descriptive_excluded, handoff_fingerprint = _validate_handoff(
            raw, symbol=selected_symbol, profile=profile,
            dataset_fingerprint=dataset_fingerprint,
            calibration_split_fingerprint=calibration_split_fingerprint,
            validation_split_fingerprint=validation_split_fingerprint,
            validation_policy_fingerprint=validation_policy_fingerprint,
            ranking_policy_fingerprint=ranking_policy_fingerprint,
            parameter_registry_fingerprint=parameter_registry_fingerprint,
        )
    except FinalistFreezeError:
        raise
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        raise FinalistFreezeError("FAIL_CLOSED_INVALID_VALIDATION_RANKING_HANDOFF") from error
    requested, policy_source = resolve_requested_finalist_count(research_parameters_path)
    finalists = candidates[: min(requested, len(candidates))]
    payload = _freeze_payload(
        raw=raw, finalists=finalists, requested=requested,
        handoff_fingerprint=handoff_fingerprint, policy_source=policy_source,
    )
    freeze = _complete_freeze(payload)
    output.mkdir(parents=True, exist_ok=True)
    _write_immutable(output / "FINALIST_FREEZE.json", freeze)
    integrity = {
        "freeze_id": freeze["freeze_id"],
        "content_hash": freeze["finalist_freeze_content_hash"],
        "canonical_serialization_version": CANONICAL_SERIALIZATION_VERSION,
        "symbol_match": True, "profile_match": True,
        "dataset_fingerprint_match": True, "validation_split_match": True,
        "validation_policy_match": True, "ranking_policy_match": True,
        "handoff_match": True, "duplicate_behavioral_signatures": 0,
        "mutation_detected": False, "integrity_status": "PASS",
    }
    handoff = {
        "artifact": "FINALIST_FREEZE_HANDOFF", "schema_version": 1,
        "freeze_id": freeze["freeze_id"],
        "content_hash": freeze["finalist_freeze_content_hash"],
        "symbol": selected_symbol, "profile": profile,
        "dataset_fingerprint": dataset_fingerprint,
        "validation_split_fingerprint": validation_split_fingerprint,
        "validation_policy_fingerprint": validation_policy_fingerprint,
        "ranking_policy_fingerprint": ranking_policy_fingerprint,
        "validation_ranking_handoff_fingerprint": handoff_fingerprint,
        "finalists": freeze["finalists"],
        "reason": freeze["selection_reason"],
        "holdout_opened": False, "holdout_reads": 0,
        "lifecycle_optimization_executed": False, "promotion_eligible": False,
    }
    status = {
        "FINAL_STATUS": "PASS", "FINAL_VERDICT": "IMMUTABLE_FINALIST_FREEZE_CREATED",
        "SYMBOL": selected_symbol, "PROFILE": profile,
        "VALIDATION_RANKING_HANDOFF_FINGERPRINT": handoff_fingerprint,
        "ELIGIBLE_NUMERIC_CONFIGS": eligible_numeric,
        "ELIGIBLE_BEHAVIORAL_CANDIDATES": len(candidates),
        "DESCRIPTIVE_BEHAVIORAL_CANDIDATES_EXCLUDED": descriptive_excluded,
        "REQUESTED_FINALIST_COUNT": requested,
        "SELECTED_FINALIST_COUNT": len(finalists),
        "FREEZE_ID": freeze["freeze_id"],
        "FREEZE_CONTENT_HASH": freeze["finalist_freeze_content_hash"],
        "SELECTION_REASON": freeze["selection_reason"],
        "DUPLICATE_BEHAVIORAL_SIGNATURES": 0, "MUTATION_DETECTED": False,
        "FREEZE_INTEGRITY": "PASS", "HOLDOUT_READS": 0,
        "HOLDOUT_OPENED": False, "LIFECYCLE_OPTIMIZATION_EXECUTED": False,
        "PROMOTION_ELIGIBLE": False, "PRODUCTION_MUTATIONS": 0,
        "BINANCE_ORDER_CALLS": 0, "LIVE_STATE": False,
    }
    report = "\n".join([
        "# Immutable Finalist Freeze", "",
        f"- Symbol/profile: `{selected_symbol}` / `{profile}`",
        f"- Eligible behavioral candidates: `{len(candidates)}`",
        f"- Frozen finalists: `{len(finalists)}`",
        f"- Freeze ID: `{freeze['freeze_id']}`",
        "- Integrity: `PASS`", "- Holdout: `NOT OPENED`", "",
    ])
    _write_immutable(output / "FINALIST_FREEZE_INTEGRITY.json", integrity)
    _write_immutable(output / "FINALIST_FREEZE_HANDOFF.json", handoff)
    _write_immutable(output / "STATUS.json", status)
    report_path = output / "REPORT.md"
    if report_path.exists() and report_path.read_text(encoding="utf-8") != report:
        raise FinalistFreezeError("FAIL_CLOSED_FINALIST_FREEZE_MUTATED")
    if not report_path.exists():
        DEFAULT_ARTIFACT_WRITER.atomic_text(report_path, report, operation="immutable_finalist_freeze_report")
    return {"freeze": freeze, "integrity": integrity, "handoff": handoff, "status": status}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validation-ranking-handoff", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--profile", default="trade-5m-v2")
    for option in (
        "dataset-fingerprint", "calibration-split-fingerprint",
        "validation-split-fingerprint", "validation-policy-fingerprint",
        "ranking-policy-fingerprint", "parameter-registry-fingerprint",
    ):
        parser.add_argument(f"--{option}", required=True)
    args = parser.parse_args(argv)
    result = run_finalist_freeze(
        handoff_path=args.validation_ranking_handoff, output=args.output,
        symbol=args.symbol, profile=args.profile,
        dataset_fingerprint=args.dataset_fingerprint,
        calibration_split_fingerprint=args.calibration_split_fingerprint,
        validation_split_fingerprint=args.validation_split_fingerprint,
        validation_policy_fingerprint=args.validation_policy_fingerprint,
        ranking_policy_fingerprint=args.ranking_policy_fingerprint,
        parameter_registry_fingerprint=args.parameter_registry_fingerprint,
    )
    print(json.dumps(result["status"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
