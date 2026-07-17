from __future__ import annotations

from collections import Counter
from typing import Any

from .observation_models import ResultRecord, RunRecord

RUN_FIELDS = ("future_bars_used", "is_trade_signal", "is_executable", "order_approved", "execution_approved",
              "position_opened", "position_size_approved")
COUNTER_FIELDS = ("private_api_used", "api_keys_used", "synthetic_candles_used", "outcome_pnl_used")
FORBIDDEN_KEYS = {"order_id", "client_order_id", "exchange_order", "filled_quantity", "position_id",
                  "position_open", "realized_pnl", "unrealized_pnl", "account_balance", "api_key", "api_secret"}


def _runtime_hits(value: Any, path: str = "") -> list[dict]:
    hits = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if str(key).lower() in FORBIDDEN_KEYS and child not in (None, False, 0, "", [], {}):
                hits.append({"path": child_path, "value_type": type(child).__name__})
            hits.extend(_runtime_hits(child, child_path))
    elif isinstance(value, list):
        for i, child in enumerate(value[:100]): hits.extend(_runtime_hits(child, f"{path}[{i}]"))
    return hits


def audit_safety(runs: list[RunRecord], results: list[ResultRecord]) -> dict:
    counters = Counter({field: sum(int(bool(getattr(run, field))) for run in runs) for field in RUN_FIELDS})
    payload_hits = []
    for result in results:
        safety = result.safety_counters_json if isinstance(result.safety_counters_json, dict) else {}
        for key, value in safety.items(): counters[str(key)] += int(value or 0)
        for field in ("market_data_payload_json", "analysis_payload_json", "setup_payload_json",
                      "strategy_payload_json", "risk_payload_json", "paper_payload_json"):
            payload_hits.extend({"run_id": result.run_id, "field": field, **hit} for hit in _runtime_hits(getattr(result, field)))
    for field in COUNTER_FIELDS: counters.setdefault(field, 0)
    nonzero = {key: value for key, value in counters.items() if value}
    return {"counters": dict(sorted(counters.items())), "forbidden_runtime_evidence": payload_hits,
            "forbidden_runtime_evidence_count": len(payload_hits),
            "violation_count": sum(nonzero.values()) + len(payload_hits), "nonzero_counters": nonzero}
