"""Canonical, reproducible effective configuration snapshots for winners."""
from __future__ import annotations
from copy import deepcopy
from functools import lru_cache
from typing import Any, Mapping
from app.config.trade_parameters import ACTIVE_SCALPING_V2_PARAMETER_SET, parameter_snapshot

def _flatten(value: Mapping[str, Any], prefix: str = "") -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, item in value.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(item, Mapping): result.update(_flatten(item, path))
        else: result[path] = item
    return result

@lru_cache(maxsize=1)
def _canonical_resolver_material() -> tuple[dict[str, Any], dict[str, Any]]:
    resolved = parameter_snapshot(ACTIVE_SCALPING_V2_PARAMETER_SET)
    nested = ACTIVE_SCALPING_V2_PARAMETER_SET.parameters.model_dump(mode="json")
    return resolved, nested

def build_effective_config_snapshot(*, symbol: str, replay_parameters: Mapping[str, Any], search_parameters: Mapping[str, Any]) -> dict[str, Any]:
    resolved, canonical_nested = _canonical_resolver_material()
    nested = deepcopy(canonical_nested)
    leaves = _flatten(nested)
    by_leaf = {path.rsplit(".", 1)[-1]: path for path in leaves}
    sources: dict[str, dict[str, Any]] = {}
    for path, row in sorted((resolved.get("parameters") or {}).items()):
        sources[path] = {"parameter_id": path, "effective_value": row.get("value"),
                         "source_layer": row.get("source"),
                         "source_yaml_path": row.get("source_component") or row.get("source_file"),
                         "source_policy": row.get("source_path"), "search_overridden": False}
    replay = dict(replay_parameters); search = dict(search_parameters)
    for name, value in sorted(replay.items()):
        path = by_leaf.get(name, name)
        if path in leaves: leaves[path] = value
        row = sources.setdefault(path, {"parameter_id": path})
        row["effective_value"] = value
        if name in search:
            row.update(source_layer="SEARCH_OVERRIDE", search_overridden=True,
                       source_yaml_path="config/research/research_parameters.yaml#search_space",
                       source_policy=name)
    effective_nested = deepcopy(nested)
    for path, value in leaves.items():
        target = effective_nested
        parts = path.split(".")
        for part in parts[:-1]: target = target[part]
        target[parts[-1]] = value
    effective = {"replay_parameters": replay, "resolved_parameters": effective_nested,
                 "parameter_set_id": resolved.get("parameter_set_id"),
                 "parameter_set_version": resolved.get("parameter_set_version"),
                 "resolver_config_hash": resolved.get("resolved_config_hash")}
    return {"config_id": "", "symbol": symbol, "search_parameters": search,
            "effective_configuration": effective, "parameter_sources": sources,
            "config_generation": ACTIVE_SCALPING_V2_PARAMETER_SET.config_generation,
            "config_hash": resolved.get("resolved_config_hash")}

def attach_effective_config(row: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(row)
    if result.get("effective_configuration") and result.get("parameter_sources") and result.get("search_parameters"):
        return result
    effective = result.get("effective_configuration") or {}
    snapshot = build_effective_config_snapshot(
        symbol=str(row.get("symbol") or ""),
        replay_parameters=dict(row.get("resolved_config") or effective.get("replay_parameters") or row.get("parameters") or row.get("overrides") or {}),
        search_parameters=dict(row.get("candidate_parameters") or row.get("overrides") or row.get("parameters") or {}),
    )
    config_id = str(row.get("config_id") or row.get("config_hash") or "")
    snapshot["effective_configuration"]["replay_config_hash"] = config_id
    result.update(search_parameters=snapshot["search_parameters"], effective_configuration=snapshot["effective_configuration"],
                  parameter_sources=snapshot["parameter_sources"], config_generation=snapshot["config_generation"],
                  resolved_config_hash=config_id or snapshot["config_hash"])
    return result
