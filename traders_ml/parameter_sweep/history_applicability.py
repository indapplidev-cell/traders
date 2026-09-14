"""Demand-driven historical input checks; scoped admission replay, not trading.

Runs the authoritative ScalpingPaperRunner with frozen RiskDecision and runtime
inputs, an offline cost source and a fresh in-memory opportunity registry per
boundary. This certifies only the prefix through economics. Probability,
portfolio, lifecycle and PnL are deliberately not certified by this adapter.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import fields
from datetime import datetime
import json
from math import isclose, isfinite
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from app.engine_paper.scalping_paper_runner import ScalpingPaperRunner
from app.engine_orchestrator.runtime_parameters import RuntimeProfileParameters
from app.engine_paper.scalping_shadow import COST_MODEL_VERSION, GEOMETRY_CALCULATION_VERSION, ShadowCostInputs
from app.engine_risk.risk_decision import RiskDecision
from .result_search import fingerprint, ResultSearchService
from .search_history import HistoryProvider, TIMEFRAMES

VERSION = "history-applicability/1"
SUPPORTED = {
    "geometry.stop_max_bps": "geometry_stop_envelope_bps",
    "geometry.minimum_planned_rr": "minimum_planned_rr",
    "economics.min_net_edge_bps": "economics_minimum_net_edge_bps",
}
TOLERANCE = 1e-8


def _same(left: Any, right: Any) -> bool:
    try:
        return isfinite(float(left)) and isfinite(float(right)) and isclose(
            float(left), float(right), rel_tol=1e-12, abs_tol=TOLERANCE)
    except (ValueError, TypeError):
        return False


class HistoricalCostSource:
    """Only reuse the same symbol/boundary/entry/reference-quantity snapshot.

    The recorded decision cutoff, not the candle boundary, bounds REST receipt
    time. This preserves runtime timing; it does not move later data to an earlier
    decision. A compatible derived snapshot does not require raw depth ladders.
    """
    def __init__(self, row: dict[str, Any], runtime: SimpleNamespace, parameters: dict[str, Any]):
        self.row, self.runtime, self.parameters = row, runtime, parameters
        self.requested = False
        self.blocker: str | None = None

    def fail(self, reason: str):
        self.blocker = reason
        raise ValueError(reason)

    def load(self, symbol: str, entry: float, *, safety_margin_bps: float) -> ShadowCostInputs:
        self.requested = True
        g = self.row.get("geometry") or {}
        if not g or g.get("economic_input_timestamp_ms") is None:
            return self.fail("MISSING_REQUIRED_COST_SNAPSHOT")
        if (symbol != self.row["symbol"] or g.get("symbol") != symbol
                or g.get("boundary") != self.row["closed_until_ms"]
                or g.get("commission_symbol") != symbol):
            return self.fail("SNAPSHOT_SYMBOL_OR_BOUNDARY_MISMATCH")
        if not _same(entry, g.get("entry")):
            return self.fail("ENTRY_CHANGED_REQUIRES_DEPTH_RECOMPUTATION")
        if not (_same(self.runtime.vwap_reference_notional, g.get("reference_notional"))
                and _same(self.runtime.vwap_reference_notional / entry, g.get("reference_quantity"))):
            return self.fail("QUANTITY_CHANGED_REQUIRES_DEPTH_RECOMPUTATION")
        if (g.get("geometry_calculation_version") != GEOMETRY_CALCULATION_VERSION
                or g.get("cost_model_version") != COST_MODEL_VERSION):
            return self.fail("SNAPSHOT_ENGINE_VERSION_MISMATCH")
        if not (g.get("commission_authoritative") is True
                and g.get("commission_snapshot_id")
                and g.get("fee_source") == "BINANCE_ACCOUNT_COMMISSION_SNAPSHOT"
                and g.get("spread_source") == "BINANCE_PUBLIC_BOOK_TICKER"
                and g.get("depth_impact_source") == "BINANCE_PUBLIC_MARKET_DATA_DEPTH"
                and all(g.get(k) == "READY" for k in
                        ("market_source_status", "book_source_status", "fee_source_status", "cost_model_status"))):
            return self.fail("UNVERIFIED_COST_PROVENANCE")
        try:
            capture = int(g["economic_input_timestamp_ms"])
            cutoff = int(g["decision_cutoff_timestamp_ms"])
            fetched = int(datetime.fromisoformat(g["commission_fetched_at"].replace("Z", "+00:00")).timestamp() * 1000)
            if not (self.row["closed_until_ms"] <= capture <= cutoff
                    and cutoff - capture <= self.runtime.microstructure_max_age_ms
                    and 0 <= cutoff - fetched <= self.parameters["costs.commission.max_snapshot_age_seconds"] * 1000
                    and (self.row.get("risk") or {}).get("created_at_ms", cutoff + 1) <= cutoff):
                return self.fail("STALE_OR_FUTURE_COST_SNAPSHOT")
            provenance = g["commission_provenance"]
            if not (provenance.get("real_account_data") is True and provenance.get("symbol") == symbol
                    and _same(provenance.get("effective_entry_fee_bps"), g["entry_fee_bps"])
                    and _same(provenance.get("effective_exit_fee_bps"), g["exit_fee_bps"])):
                return self.fail("COMMISSION_PROVENANCE_MISMATCH")
            for field, expected in {
                "entry_slippage_bps": self.runtime.economics_entry_slippage_bps,
                "exit_slippage_bps": self.runtime.economics_exit_slippage_bps,
                "safety_margin_bps": safety_margin_bps,
                "adverse_fill_reserve_bps": self.parameters["costs.adverse_fill_reserve_bps"],
            }.items():
                if not _same(g.get(field), expected):
                    return self.fail("FROZEN_COST_POLICY_MISMATCH")
            for field in ("spread_bps", "depth_impact_bps", "entry_fee_bps", "exit_fee_bps"):
                if not isfinite(float(g[field])):
                    return self.fail("INVALID_COST_COMPONENT")
            for field in ("entry_liquidity_role", "exit_liquidity_role"):
                if g.get(field) != self.parameters["costs.commission." + field]:
                    return self.fail("LIQUIDITY_ROLE_MISMATCH")
            values = {f.name: g[f.name] for f in fields(ShadowCostInputs) if f.name in g}
            values.update(spread_authoritative=True, depth_authoritative=True,
                          require_causal_timestamp=True, maximum_age_ms=self.runtime.microstructure_max_age_ms)
            return ShadowCostInputs(**values)
        except (KeyError, TypeError, ValueError, OverflowError):
            if self.blocker:
                raise
            return self.fail("INCOMPLETE_OR_INVALID_COST_EVIDENCE")


def _namespace(values: dict[str, Any]) -> SimpleNamespace:
    nested: dict[str, Any] = {}
    for path, value in values.items():
        parts = path.split(".")
        cursor = nested
        for part in parts[:-1]:
            cursor = cursor.setdefault(part, {})
        cursor[parts[-1]] = value
    def convert(value):
        return SimpleNamespace(**{k: convert(v) for k, v in value.items()}) if isinstance(value, dict) else value
    return convert(nested)


def assess_boundary(row: dict[str, Any], overrides: dict[str, float]) -> dict[str, Any]:
    """No cross-boundary state; unchanged upstream decisions are explicit inputs."""
    result = {"symbol": row["symbol"], "boundary": row["closed_until_ms"], "run_id": row["run_id"],
              "state": "BLOCKED", "cost_requirement": "UNKNOWN", "reason": None}
    unsupported = sorted(set(overrides) - set(SUPPORTED))
    if unsupported:
        return result | {"reason": "UPSTREAM_OR_UNSUPPORTED_PARAMETER_REQUIRES_RECOMPUTATION", "parameters": unsupported}
    if any(isinstance(v, bool) or not isfinite(float(v)) or float(v) < 0 for v in overrides.values()):
        return result | {"reason": "INVALID_PARAMETER_VALUE"}
    frozen = row.get("frozen") or {}
    if not frozen.get("resolved_config_hash") or not frozen.get("runtime_parameters") or not row.get("risk"):
        return result | {"reason": "FROZEN_UPSTREAM_OR_BASELINE_INPUTS_MISSING"}
    try:
        parameters = dict(frozen["parameters"])
        runtime_values = dict(frozen["runtime_parameters"])
        for canonical, runtime in SUPPORTED.items():
            if not _same(parameters[canonical], runtime_values[runtime]):
                return result | {"reason": "BASELINE_RESOLVER_IDENTITY_MISMATCH"}
        for key, value in overrides.items():
            parameters[key] = value
            runtime_values[SUPPORTED[key]] = value
        if parameters["geometry.stop_max_bps"] <= parameters["geometry.stop_min_bps"]:
            return result | {"reason": "INVALID_STOP_RANGE"}
        def immutable(value):
            return tuple(immutable(v) for v in value) if isinstance(value, list) else value
        runtime = RuntimeProfileParameters(**{k: immutable(v) for k, v in runtime_values.items()})
        source = HistoricalCostSource(row, runtime, parameters)
        risk = row["risk"]
        if any(risk.get(k) for k in ("future_bars_used", "is_executable", "is_trade_signal", "execution_approved",
                                     "order_approved", "position_size_approved")):
            return result | {"reason": "UNSAFE_OR_NONCAUSAL_RISK_EVIDENCE"}
        decision = RiskDecision(**{f.name: risk[f.name] for f in fields(RiskDecision) if f.init and f.name in risk})
        if decision.symbol != row["symbol"] or decision.closed_until_ms != row["closed_until_ms"]:
            return result | {"reason": "RISK_IDENTITY_MISMATCH"}
        runner = ScalpingPaperRunner(runtime_parameters=runtime, cost_source=source,
                                     scalping_parameters=_namespace(parameters),
                                     clock_ms=lambda: decision.created_at_ms)
        plan = runner._process(decision)
        diagnostic = plan.paper_context.get("scalping_geometry_diagnostics") or {}
        result.update(cost_requirement="REQUIRED" if source.requested else "NOT_REQUIRED",
                      stage=diagnostic.get("rejection_stage") or "UPSTREAM",
                      reason=diagnostic.get("rejection_reason") or plan.paper_status,
                      replay_input_fingerprint=fingerprint({"parameters": parameters, "runtime": runtime_values}),
                      baseline_hash=frozen["resolved_config_hash"],
                      diagnostic={k: diagnostic.get(k) for k in (
                          "final_stop", "causal_target", "effective_total_cost_bps", "net_rr",
                          "minimum_positive_edge_bps", "stop_envelope_bps", "required_rr")})
        if source.blocker:
            return result | {"reason": source.blocker}
        if source.requested:
            result["cost_requirement"] = "VERIFIED_SAME_INPUT_SNAPSHOT"
        if diagnostic.get("evaluator_inputs", {}).get("ev_evaluator_reached"):
            # None statistics is never evidence for an actual probability rejection.
            return result | {"state": "PREFIX_VERIFIED", "stage": "PROBABILITY",
                             "reason": "HISTORICAL_PROBABILITY_HIERARCHY_REQUIRED"}
        if diagnostic.get("valid_plan") or plan.paper_status == "PAPER_PLAN_READY":
            return result | {"state": "PREFIX_VERIFIED", "reason": "DOWNSTREAM_PORTFOLIO_AND_LIFECYCLE_REQUIRED"}
        if plan.paper_status == "ERROR":
            return result | {"reason": "SOURCE_OR_REPLAY_ERROR"}
        return result | {"state": "VERIFIED_REJECTION"}
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        return result | {"reason": "REPLAY_INPUT_INVALID", "error_type": type(error).__name__}


def baseline_parity(row: dict[str, Any], replay: dict[str, Any]) -> bool:
    if replay["state"] != "VERIFIED_REJECTION":
        return False
    g = row.get("geometry") or {}
    if g:
        if replay["stage"] != g.get("rejection_stage") or replay["reason"] != g.get("rejection_reason"):
            return False
        for name, value in replay.get("diagnostic", {}).items():
            expected = g.get(name)
            if value is None and expected is None:
                continue
            if not _same(value, expected):
                return False
        return True
    return replay["reason"] == row.get("paper_status")


def assess_dataset(directory: Path, combinations: list[dict[str, float]]) -> dict[str, Any]:
    if not combinations or len(combinations) > 100:
        raise ValueError("ASSESSMENT_REQUIRES_1_TO_100_COMBINATIONS")
    manifest, rows = HistoryProvider.load(directory)
    boundaries = [r for r in rows if r["kind"] == "PERSISTED_BOUNDARY"]
    if not boundaries:
        raise ValueError("NO_BOUNDARIES_FOR_FROZEN_UPSTREAM_ASSESSMENT")
    interval = manifest["intervals"]
    step = TIMEFRAMES["5m"]
    first = ((interval["search_start_ms"] + step - 1) // step) * step
    expected = {(s, t) for s in manifest["symbols"] for t in range(first, interval["search_end_ms"], step)}
    actual = [(r["symbol"], r["closed_until_ms"]) for r in boundaries]
    coverage = {"expected_boundaries": len(expected), "observed_boundaries": len(actual),
                "missing_boundaries": len(expected - set(actual)),
                "extra_boundaries": len(set(actual) - expected),
                "duplicate_boundaries": len(actual) - len(set(actual))}
    dataset_blockers = list(manifest["missing_inputs"])
    if any(coverage[k] for k in ("missing_boundaries", "extra_boundaries", "duplicate_boundaries")):
        dataset_blockers.append("BOUNDARY_COVERAGE_INCOMPLETE_OR_AMBIGUOUS")
    baseline = {r["run_id"] + ":" + r["symbol"]: assess_boundary(r, {}) for r in boundaries}
    results = []
    for overrides in combinations:
        details = []
        epochs: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in boundaries:
            check = assess_boundary(row, overrides)
            base = baseline[row["run_id"] + ":" + row["symbol"]]
            parity = baseline_parity(row, base)
            check["baseline_parity"] = "PASS" if parity else "UNPROVEN"
            # Do not turn a data mismatch into a newly verified combination.
            # A tighter geometry rejection can be verified without the cost data
            # needed by the baseline. Missing later data must not poison it.
            independent_early_rejection = (check["state"] == "VERIFIED_REJECTION"
                and check["cost_requirement"] == "NOT_REQUIRED"
                and base["state"] == "BLOCKED" and base["cost_requirement"] == "REQUIRED")
            if not parity and not independent_early_rejection:
                check.update(state="BLOCKED", reason="BASELINE_PARITY_UNPROVEN:" + str(base["reason"]))
            details.append(check)
            epochs[str((row.get("frozen") or {}).get("resolved_config_hash") or "MISSING")].append(check)
        def summary(items):
            counts = dict(Counter(x["state"] for x in items))
            return {"rows": len(items), "states": counts,
                    "cost_requirements": dict(Counter(x["cost_requirement"] for x in items)),
                    "reasons": dict(Counter(x["reason"] for x in items)),
                    "admission_prefix_complete": not dataset_blockers and counts.get("VERIFIED_REJECTION", 0) == len(items),
                    "full_trade_simulation_verified": False}
        results.append({"overrides": overrides, "combination_id": fingerprint(overrides),
                        **summary(details), "by_baseline": {k: summary(v) for k, v in epochs.items()},
                        "details": details})
    return {"schema": VERSION, "dataset_fingerprint": manifest["fingerprint"],
            "source_dataset": str(directory.resolve()), "scope": "FROZEN_UPSTREAM_ADMISSION_PREFIX_ONLY",
            "numeric_tolerance": TOLERANCE, "dataset_hard_blockers": dataset_blockers,
            "boundary_coverage": coverage,
            "engine_files": {str(p): __import__('hashlib').sha256(p.read_bytes()).hexdigest() for p in (
                Path(__file__), Path(__import__('inspect').getfile(ScalpingPaperRunner)))},
            "combinations": results, "full_trade_simulation_verified": False,
            "excluded_families": {"signal/regime/confirmation": "Requires recomputed upstream decisions",
                "geometry.target_min_bps": "DIAGNOSTIC_ONLY in authoritative evaluator; not an admission gate",
                "costs/risk": "Frozen, cannot reuse quantity-dependent costs after arbitrary changes",
                "probability/lifecycle/portfolio": "Outside this prefix adapter; no full-trade claim"}}


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--combinations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must not exist")
    result = assess_dataset(args.dataset, json.loads(args.combinations.read_text()))
    ResultSearchService._write(args.output, result)
    print(json.dumps({"output": str(args.output), "combinations": len(result["combinations"]),
                      "scope": result["scope"], "full_trade_simulation_verified": False}))


if __name__ == "__main__":
    main()
