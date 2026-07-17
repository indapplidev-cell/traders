from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .observation_models import ResultRecord, RunRecord

REASON_KEYS = {"reason", "reasons", "reason_code", "reason_codes", "final_reason", "skip_reason",
               "decision_reasons", "risk_reasons", "plan_reasons"}


def _strings(value: Any, key: str | None = None) -> list[str]:
    if isinstance(value, dict):
        found = []
        for child_key, child in value.items():
            if str(child_key).lower() in REASON_KEYS:
                found.extend(_strings(child, str(child_key)))
            elif isinstance(child, (dict, list, tuple)):
                found.extend(_strings(child))
        return found
    if isinstance(value, (list, tuple)):
        return [item for child in value for item in _strings(child, key)]
    if key is not None and value not in (None, ""):
        return [str(value)]
    return []


def analyze_reasons(runs: list[RunRecord], results: list[ResultRecord], limit: int = 10) -> dict:
    run_by_id = {run.run_id: run for run in runs}
    layer_values: dict[str, list[tuple[str, RunRecord | None]]] = defaultdict(list)
    for run in runs:
        if run.final_reason: layer_values["final"].append((run.final_reason, run))
    for result in results:
        run = run_by_id.get(result.run_id)
        module = result.module_reasons_json if isinstance(result.module_reasons_json, dict) else {}
        for layer in ("analysis", "setup", "strategy", "risk", "paper"):
            values = _strings(module.get(layer), "reasons") + _strings(getattr(result, f"{layer}_payload_json"))
            for value in dict.fromkeys(values):
                layer_values[layer].append((value, run))
    output = {}
    for layer in ("final", "analysis", "setup", "strategy", "risk", "paper"):
        pairs = layer_values[layer]
        counts = Counter(value for value, _ in pairs)
        rows = []
        for reason, count in counts.most_common(limit):
            examples = [{"symbol": run.symbol, "closed_until_utc": run.closed_until_utc.isoformat()}
                        for value, run in pairs if value == reason and run is not None][:3]
            rows.append({"reason": reason, "count": count, "share": count / len(pairs) if pairs else 0.0,
                         "examples": examples})
        output[layer] = {"relevant_reason_count": len(pairs), "top": rows}
    return output
