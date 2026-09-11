"""YAML-owned staged targeted calibration planning."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping


STAGE_ORDER = (
    "SET2_BASELINE", "ONE_FACTOR_SENSITIVITY", "SMALL_FAMILY_SEARCH",
    "TOP_REGION_REFINEMENT", "LOCAL_FINALIST_VALIDATION",
)


@dataclass(frozen=True, slots=True)
class TargetedCandidate:
    stage: str
    overrides: dict[str, Any]


def validate_targeted_space(config: Mapping[str, Any]) -> None:
    calibration = config["calibration"]
    families = calibration["parameter_families"]
    targeted = set(calibration["targeted_families"])
    frozen = set(calibration["frozen_families"])
    if targeted & frozen or targeted | frozen != set(families):
        raise ValueError("PARAMETER_FAMILY_PARTITION_INVALID")
    allowed = {name for family in targeted for name in families[family]}
    if not set(config["search_space"]) & allowed:
        raise ValueError("TARGETED_SEARCH_SPACE_EMPTY")


def active_search_space(config: Mapping[str, Any]) -> dict[str, list[Any]]:
    validate_targeted_space(config)
    calibration = config["calibration"]
    allowed = {name for family in calibration["targeted_families"] for name in calibration["parameter_families"][family]}
    return {name: list(values) for name, values in config["search_space"].items() if name in allowed}


def sensitivity_preflight(
    config: Mapping[str, Any], baseline: Mapping[str, Any], signature,
) -> dict[str, Any]:
    """Classify one-factor dimensions before any combinatorial expansion."""
    space = active_search_space(config)
    families = config["calibration"]["parameter_families"]
    family_for = {name: family for family, names in families.items() for name in names}
    baseline_signature = signature(dict(baseline))
    active: dict[str, list[Any]] = {}
    no_op: dict[str, dict[str, Any]] = {}
    signatures: dict[str, list[str]] = {}
    for name, values in sorted(space.items()):
        observed = []
        for value in values:
            resolved = {**baseline, name: value}
            observed.append(signature(resolved))
        encoded = [sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest() for value in observed]
        signatures[name] = encoded
        if len(set(encoded + [sha256(json.dumps(baseline_signature, sort_keys=True, default=str).encode()).hexdigest()])) > 1:
            active[name] = values
        else:
            no_op[name] = {
                "reason": "GENUINELY_INERT_ON_THIS_DATASET",
                "candidate_values": values,
            }
    declared = list(config["calibration"]["targeted_families"])
    active_families = sorted({family_for[name] for name in active})
    missing = sorted(set(declared) - set(active_families))
    if missing:
        raise ValueError("DECLARED_FAMILY_WITHOUT_ACTIVE_DIMENSION:" + ",".join(missing))
    raw = 1
    for values in space.values():
        raw *= len(values)
    effective = 1
    for values in active.values():
        effective *= len(values)
    return {
        "declared_families": declared,
        "active_families": active_families,
        "active_dimensions": active,
        "no_op_dimensions": no_op,
        "excluded_dimensions": {},
        "raw_config_count": raw,
        "unique_effective_config_count": effective,
        "sensitivity_signatures": signatures,
    }


def deduplicate_behavioral_configs(configs: Iterable[TargetedCandidate], signature):
    """Yield one representative per behavior and retain deterministic aliases."""
    representatives: list[TargetedCandidate] = []
    aliases: dict[str, list[dict[str, Any]]] = {}
    seen: dict[str, int] = {}
    for candidate in configs:
        key = sha256(json.dumps(signature(candidate.overrides), sort_keys=True, default=str).encode()).hexdigest()
        if key in seen:
            aliases.setdefault(key, []).append(candidate.overrides)
            continue
        seen[key] = len(representatives)
        representatives.append(candidate)
        aliases[key] = []
    return representatives, aliases


def research_config_hash(config: Mapping[str, Any]) -> str:
    return sha256(json.dumps(config, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def staged_candidates(config: Mapping[str, Any], baseline: Mapping[str, Any]) -> Iterable[TargetedCandidate]:
    """Yield baseline, one-factor points, then deterministic bounded combinations."""
    validate_targeted_space(config)
    space = active_search_space(config)
    budgets = config["search"]["stage_budgets"]
    yielded: set[str] = set()

    def emit(stage: str, overrides: dict[str, Any]):
        identity = json.dumps(overrides, sort_keys=True, separators=(",", ":"))
        if identity not in yielded:
            yielded.add(identity)
            return TargetedCandidate(stage, overrides)
        return None

    first = emit("SET2_BASELINE", {})
    if first and budgets.get("SET2_BASELINE", 0):
        yield first
    count = 0
    for name in sorted(space):
        for value in space[name]:
            if value == baseline.get(name):
                continue
            item = emit("ONE_FACTOR_SENSITIVITY", {name: value})
            if item:
                yield item
                count += 1
                if count >= budgets.get("ONE_FACTOR_SENSITIVITY", 0):
                    break
        if count >= budgets.get("ONE_FACTOR_SENSITIVITY", 0):
            break
    # A full Cartesian product is never materialized. A seeded mixed-radix walk
    # is bounded by YAML stage budgets and stable across runs.
    names = sorted(space)
    cardinality = 1
    for name in names:
        cardinality *= len(space[name])
    seed = int(config["search"]["seed"])
    for stage in STAGE_ORDER[2:]:
        budget = int(budgets.get(stage, 0))
        accepted = 0
        for offset in range(cardinality):
            index = (seed + offset * 7919) % cardinality
            overrides = {}
            for name in reversed(names):
                index, choice = divmod(index, len(space[name]))
                value = space[name][choice]
                if value != baseline.get(name):
                    overrides[name] = value
            item = emit(stage, overrides)
            if item:
                yield item
                accepted += 1
                if accepted >= budget:
                    break
