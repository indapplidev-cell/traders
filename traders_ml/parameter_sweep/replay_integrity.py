"""Frozen-dataset, cost-provenance and deterministic replay gates."""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Iterable, Mapping


def frozen_dataset_hash(rows: Iterable[Mapping[str, Any]]) -> str:
    return sha256(json.dumps(list(rows), sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def verify_frozen_manifest(manifest: Mapping[str, Any], rows: list[Mapping[str, Any]]) -> str:
    if int(manifest.get("dataset_row_count", -1)) != len(rows):
        raise ValueError("FROZEN_DATASET_ROW_COUNT_MISMATCH")
    required = {"dataset_cutoff_at", "source_watermarks", "profile", "trade_config_hash"}
    if not required <= set(manifest):
        raise ValueError("FROZEN_DATASET_MANIFEST_INCOMPLETE")
    return "PASS"


def cost_provenance(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    values = []
    missing = 0
    for row in rows:
        value = row.get("cost_provenance", row.get("commission_provenance"))
        if value is None:
            missing += 1
        else:
            values.append(json.dumps(value, sort_keys=True, default=str))
    return {
        "COST_PROVENANCE_COMPLETE": missing == 0,
        "MISSING": missing,
        "SOURCE_CLASSES": sorted(set(values)),
        "CONSISTENT_SNAPSHOT": len(set(values)) <= 1,
    }


def deterministic_signature(*, dataset_hash: str, research_hash: str, baseline_hash: str, seed: int, config_ids: Iterable[str], ranking: Iterable[str]) -> str:
    return sha256(json.dumps({
        "dataset_hash": dataset_hash, "research_hash": research_hash,
        "baseline_hash": baseline_hash, "seed": seed,
        "config_ids": list(config_ids), "ranking": list(ranking),
    }, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

