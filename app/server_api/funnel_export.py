"""Bounded readonly renderers for professional Trading Funnel exports."""

from __future__ import annotations

import base64
import csv
import hashlib
import hmac
import io
import json
import re
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from decimal import Decimal
from dataclasses import dataclass
from typing import Any, Final

from app.engine_observation.scalping_calibration import _stage_flags, aggregate, export_record
from app.engine_orchestrator.orchestrator_models import OnlinePipelineResultRow, OnlinePipelineRun
from app.engine_orchestrator.runtime_parameters import resolve_runtime_parameters
from app.i18n import CATALOG_VERSION
from app.server_api.errors import ApiError
from app.server_api.trading_funnel import STAGES, _first_reason, _mapping, _stage_trace


EXPORT_SCHEMA_VERSION: Final = "trading-funnel-export-v1"
MAX_EXPORT_RANGE_MS: Final = 24 * 60 * 60 * 1000
MAX_EXPORT_ROWS: Final = 2_880
EXPORT_FORMATS: Final = frozenset({"jsonl", "csv", "summary-json", "summary-md"})
PAGED_EXPORT_FORMATS: Final = frozenset({"jsonl-records", "csv-records"})
DEFAULT_EXPORT_PAGE_SIZE: Final = 200
MAX_EXPORT_PAGE_SIZE: Final = 2_000
_SAFE_REASON = re.compile(r"^[A-Za-z0-9_.:/() +,=\-]{1,240}$")
_SECRET_TOKENS = ("api" + "_key", "apikey", "authorization", "bearer", "cookie", "password", "private" + "_key", "secret", "db" + "_uri")


@dataclass(frozen=True, slots=True)
class ExportCursor:
    trade_profile_id: str
    from_ms: int
    to_ms: int
    symbol: str | None
    snapshot_closed_until: int
    available_from: int | None
    available_to: int | None
    generated_at_ms: int
    last_boundary_closed_at: int
    last_symbol: str
    last_run_id: str


def encode_export_cursor(value: ExportCursor) -> str:
    """Encode a bounded, non-secret cursor with the project's validation checksum."""
    body = {
        "v": 1,
        "profile": value.trade_profile_id,
        "from": value.from_ms,
        "to": value.to_ms,
        "symbol": value.symbol,
        "snapshot": value.snapshot_closed_until,
        "available_from": value.available_from,
        "available_to": value.available_to,
        "generated_at": value.generated_at_ms,
        "last_boundary": value.last_boundary_closed_at,
        "last_symbol": value.last_symbol,
        "last_run_id": value.last_run_id,
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    body["check"] = hashlib.sha256(b"traders-funnel-export-v1\0" + canonical).hexdigest()[:24]
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def decode_export_cursor(value: str) -> ExportCursor:
    """Decode and strictly validate all snapshot and keyset cursor fields."""
    try:
        if not value or len(value) > 4096:
            raise ValueError
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        body = json.loads(raw)
        expected = {
            "v", "profile", "from", "to", "symbol", "snapshot",
            "available_from", "available_to", "generated_at", "last_boundary", "last_symbol",
            "last_run_id", "check",
        }
        if not isinstance(body, dict) or set(body) != expected:
            raise ValueError
        check = body.pop("check")
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        expected_check = hashlib.sha256(b"traders-funnel-export-v1\0" + canonical).hexdigest()[:24]
        if not isinstance(check, str) or not hmac.compare_digest(check, expected_check):
            raise ValueError
        if body["v"] != 1 or body["profile"] not in {"trade-15m-v1", "trade-5m-v1"}:
            raise ValueError
        if body["symbol"] is not None and (
            not isinstance(body["symbol"], str) or not body["symbol"].isalnum()
        ):
            raise ValueError
        integers = ("from", "to", "snapshot", "generated_at", "last_boundary")
        if any(isinstance(body[key], bool) or not isinstance(body[key], int) for key in integers):
            raise ValueError
        for key in ("available_from", "available_to"):
            if body[key] is not None and (isinstance(body[key], bool) or not isinstance(body[key], int)):
                raise ValueError
        if not isinstance(body["last_symbol"], str) or not body["last_symbol"].isalnum():
            raise ValueError
        if not isinstance(body["last_run_id"], str) or not 1 <= len(body["last_run_id"]) <= 80:
            raise ValueError
        return ExportCursor(
            body["profile"], body["from"], body["to"], body["symbol"],
            body["snapshot"], body["available_from"], body["available_to"], body["generated_at"],
            body["last_boundary"], body["last_symbol"], body["last_run_id"],
        )
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, UnicodeDecodeError):
        raise ApiError(422, "INVALID_CURSOR", "The export cursor is invalid.") from None


def _safe_reason(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    lowered = text.casefold()
    if not _SAFE_REASON.fullmatch(text) or any(token in lowered for token in _SECRET_TOKENS):
        return None
    return text


def _json_scalar(value: object) -> object:
    if isinstance(value, datetime):
        aware = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        return aware.astimezone(timezone.utc).isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _reason_codes(run: OnlinePipelineRun, result: OnlinePipelineResultRow | None) -> list[str]:
    values: list[object] = [run.error_code, run.final_reason]
    if result is not None:
        for items in _mapping(result.module_reasons_json).values():
            values.extend(items if isinstance(items, (list, tuple)) else (items,))
    return list(dict.fromkeys(reason for value in values if (reason := _safe_reason(value))))


def _closed_context(result: OnlinePipelineResultRow | None) -> dict[str, int | None]:
    market = _mapping(result.market_data_payload_json) if result is not None else {}
    return {
        timeframe: (
            int(_mapping(market.get(timeframe))["closed_until_ms"])
            if _mapping(market.get(timeframe)).get("closed_until_ms") is not None else None
        )
        for timeframe in ("1m", "5m", "15m", "1h", "4h")
    }


def _source_row(run: OnlinePipelineRun, result: OnlinePipelineResultRow | None) -> dict[str, Any]:
    analysis = dict(_mapping(result.analysis_payload_json)) if result is not None else {}
    setup = dict(_mapping(result.setup_payload_json)) if result is not None else {}
    strategy = dict(_mapping(result.strategy_payload_json)) if result is not None else {}
    risk = dict(_mapping(result.risk_payload_json)) if result is not None else {}
    paper = dict(_mapping(result.paper_payload_json)) if result is not None else {}
    parameter_set_id = (
        paper.get("runtime_parameter_set_id") or analysis.get("runtime_parameter_set_id")
        or resolve_runtime_parameters(run.trade_profile_id).parameter_set_id
    )
    return {
        "run_id": run.run_id, "boundary": run.closed_until_ms, "symbol": run.symbol,
        "profile": run.trade_profile_id, "parameter_set_id": parameter_set_id,
        "duration_ms": run.duration_ms, "final_reason": _safe_reason(run.final_reason),
        "analysis": analysis, "setup": setup, "strategy": strategy, "risk": risk, "paper": paper,
        "module_reasons": {key: [reason for item in (value if isinstance(value, list) else [value])
                                 if (reason := _safe_reason(item))]
                           for key, value in (_mapping(result.module_reasons_json).items() if result is not None else ())},
        "risk_budget_reserved": bool(risk.get("execution_budget_reserved", False)),
    }


def _first_rejection(trace: Mapping[str, str], reasons: list[str]) -> tuple[str | None, str | None]:
    stage = next((name for name in STAGES if trace.get(name) in {"REJECTED", "ERROR", "DEFERRED"}), None)
    return stage, reasons[0] if reasons else None


def _trace_status(stage: str, value: str, paper: Mapping[str, object]) -> str:
    if value == "PASS":
        return "APPROVED"
    if value in {"DEFERRED", "PENDING"}:
        return "WAIT"
    if value == "REJECTED" and stage == "PAPER_TRADE_PLAN" and paper.get("paper_status") in {"NO_PLAN", "NO_DECISION"}:
        return "NO_PLAN"
    return value


def _canonical_trace(
    source: Mapping[str, Any],
    legacy_trace: Mapping[str, str],
    stage_reasons: Mapping[str, str | None],
    diagnostic: Mapping[str, Any],
    outcome: Mapping[str, object],
) -> dict[str, dict[str, object]]:
    """Project the persisted pipeline onto the stable analytics stage contract."""
    flags = _stage_flags(source)
    legacy_by_stage = {
        "analysis": "ANALYSIS",
        "setup": "STRUCTURAL_SETUP",
        "strategy": "STRATEGY_ELIGIBLE",
        "risk": "RISK_APPROVED",
        "paper_plan": "PAPER_TRADE_PLAN",
        "final_approval": "FINAL_APPROVAL",
    }
    flag_by_stage = {
        "analysis": "analysis", "setup": "structural_setup",
        "strategy": "strategy_admitted", "geometry": "geometry_valid",
        "cost": "net_cost_viable", "risk": "risk_admitted",
        "paper_plan": "paper_plan", "final_approval": "final_approval",
        "paper_command": "paper_command", "position": "position", "exit": "exit",
    }
    reason_by_stage: dict[str, str | None] = {
        name: stage_reasons.get(legacy) for name, legacy in legacy_by_stage.items()
    }
    diagnostic_reason = _safe_reason(
        diagnostic.get("rejection_reason") or diagnostic.get("raw_reason")
    )
    rejection_stage = str(diagnostic.get("rejection_stage") or "").upper()
    if rejection_stage in {"CAUSAL_INVALIDATION", "ATR_BUFFER", "STOP_ENVELOPE", "CAUSAL_TARGET", "GEOMETRY"}:
        reason_by_stage["geometry"] = diagnostic_reason
    if rejection_stage == "TARGET_ACTIONABILITY":
        reason_by_stage["target_actionability"] = diagnostic_reason
    if rejection_stage in {"COST", "ECONOMICS", "NET_COST", "NET_COST_GATE"}:
        reason_by_stage["cost"] = diagnostic_reason

    output: dict[str, dict[str, object]] = {}
    prior_reached = True
    stage_order = ["analysis", "setup", "strategy", "geometry"]
    if source.get("profile") == "trade-5m-v1":
        stage_order.append("target_actionability")
    stage_order.extend([
        "cost", "risk", "paper_plan", "final_approval", "paper_command", "position", "exit",
    ])
    for name in stage_order:
        passed = (
            bool(diagnostic.get("economically_actionable_target_exists"))
            if name == "target_actionability" else bool(flags[flag_by_stage[name]])
        )
        legacy_name = legacy_by_stage.get(name)
        legacy_status = legacy_trace.get(legacy_name, "NOT_REACHED") if legacy_name else None
        if name == "analysis" and legacy_status == "ERROR":
            status = "ERROR"
        elif passed:
            status = "APPROVED"
        elif legacy_status in {"DEFERRED", "PENDING"}:
            status = "WAIT"
        elif name == "paper_plan" and legacy_status == "REJECTED":
            status = "NO_PLAN"
        elif legacy_status in {"REJECTED", "ERROR"}:
            status = legacy_status
        elif name == "geometry" and prior_reached and diagnostic:
            status = "REJECTED"
        elif name == "target_actionability" and prior_reached and diagnostic:
            status = "REJECTED"
        elif name == "cost" and prior_reached and diagnostic.get("economic_gate_pass") is False:
            status = "REJECTED"
        else:
            status = "NOT_REACHED"
        reached = status != "NOT_REACHED"
        reason = reason_by_stage.get(name)
        output[name] = {
            "reached": reached, "status": status,
            "reason_code": reason, "raw_reason": reason,
        }
        prior_reached = prior_reached and status == "APPROVED"
    return output


def build_export_record(
    run: OnlinePipelineRun,
    result: OnlinePipelineResultRow | None,
    *,
    generated_at_ms: int,
    from_ms: int,
    to_ms: int,
    outcome: Mapping[str, object] | None = None,
) -> dict[str, Any]:
    """Build one allowlisted record; missing authoritative facts remain null."""
    source = _source_row(run, result)
    outcome = outcome or {}
    legacy = export_record(source)
    analysis, setup, strategy, risk, paper = (source[name] for name in ("analysis", "setup", "strategy", "risk", "paper"))
    diagnostic = _mapping(_mapping(paper.get("paper_context")).get("scalping_geometry_diagnostics"))
    trace, meta = _stage_trace(run, result, generated_at_ms)
    reasons = _reason_codes(run, result)
    first_stage, first_reason = _first_rejection(trace, reasons)
    module_reason_stage = {
        "analysis": "ANALYSIS", "setup": "STRUCTURAL_SETUP", "strategy": "STRATEGY_ELIGIBLE",
        "risk": "RISK_APPROVED", "paper": "PAPER_TRADE_PLAN",
    }
    stage_reasons: dict[str, str] = {}
    if result is not None:
        for module, values in _mapping(result.module_reasons_json).items():
            stage = module_reason_stage.get(str(module))
            items = values if isinstance(values, (list, tuple)) else (values,)
            if stage is not None:
                stage_reasons[stage] = next((reason for item in items if (reason := _safe_reason(item))), None)
    if first_stage is not None and first_reason is not None:
        stage_reasons.setdefault(first_stage, first_reason)
    runtime = resolve_runtime_parameters(run.trade_profile_id)
    planned = _mapping(paper.get("shadow_plan")) or paper
    return {
        "provenance": {
            "export_generated_at_utc": datetime.fromtimestamp(generated_at_ms / 1000, timezone.utc).isoformat(),
            "export_schema_version": EXPORT_SCHEMA_VERSION,
            "catalog_version": CATALOG_VERSION,
            "trade_profile_id": run.trade_profile_id,
            "parameter_set_id": source.get("parameter_set_id") or runtime.parameter_set_id,
            "parameter_set_version": runtime.contract_version,
            "parameter_set_hash": runtime.parameter_set_id.rsplit("-", 1)[-1],
            "from_ms": from_ms, "to_ms": to_ms, "query_closed_until_ms": run.closed_until_ms,
            "source_run_id": run.run_id, "trigger_source": run.trigger_source,
        },
        "market_analysis": {
            "symbol": run.symbol, "boundary_closed_at_ms": run.closed_until_ms,
            "primary_timeframe": run.primary_timeframe,
            "entry_reference_price": legacy.get("entry"), "regime": legacy.get("regime"),
            "regime_confidence": analysis.get("regime_confidence") or analysis.get("confidence"),
            "direction": legacy.get("direction"),
            "direction_confidence": analysis.get("direction_confidence"),
            "impulse_phase": analysis.get("impulse_phase"), "entry_quality": analysis.get("entry_quality"),
            "atr": legacy.get("atr"), "atr_pct": analysis.get("atr_pct"),
            "structure_state": analysis.get("structure_state"), "liquidity_state": analysis.get("liquidity_state"),
            "volume_state": analysis.get("volume_state"),
        },
        "multi_tf_closed_until_ms": _closed_context(result),
        "funnel_trace": _canonical_trace(source, trace, stage_reasons, diagnostic, outcome),
        "setup": {
            "setup_type": setup.get("setup_type"), "status": setup.get("setup_status") or setup.get("status"),
            "direction": setup.get("direction_hint"), "quality": setup.get("setup_quality"),
            "quality_score": setup.get("quality_score"),
            "confidence": setup.get("source_confidence"), "entry_zone": setup.get("entry_zone"),
            "setup_created_at": setup.get("created_at_ms"),
            "causal_invalidation": legacy.get("causal_invalidation"),
            "breakout_level": setup.get("breakout_level"), "support_level": setup.get("support_level"),
            "resistance_level": setup.get("resistance_level"), "liquidity_level": setup.get("liquidity_level"),
            "swing_level": setup.get("swing_level"),
        },
        "strategy": {
            "status": strategy.get("decision_status"), "reason": reasons[0] if reasons else None,
            "eligibility": meta.get("validity_current"), "selector_status": strategy.get("selector_status"),
            "selector_rank": strategy.get("selector_rank"), "selector_winner": strategy.get("selector_winner"),
            "strategy_quality_score": strategy.get("strategy_score"),
            "strategy_quality_threshold": strategy.get("strategy_quality_threshold"),
            "component_scores": strategy.get("component_scores"),
            "strategy_raw_score": strategy.get("strategy_raw_score"),
            "strategy_penalty_total": strategy.get("strategy_penalty_total"),
            "strategy_final_score": strategy.get("strategy_final_score"),
            "strategy_margin_to_threshold": strategy.get("strategy_margin_to_threshold"),
            "shadow_quality_cohorts": strategy.get("shadow_quality_cohorts") or {},
        },
        "risk": {
            "status": risk.get("risk_status"), "reason": reasons[0] if reasons else None,
            "research_attempt_count": risk.get("research_attempt_count"),
            "profile_research_limit": risk.get("profile_research_limit"),
            "execution_budget_reserved": risk.get("execution_budget_reserved"),
            "execution_budget_consumed": risk.get("execution_budget_consumed"),
            "global_open_position_budget": risk.get("global_open_position_budget"),
            "global_daily_risk_budget": risk.get("global_daily_risk_budget"),
            "directional_limit": risk.get("directional_limit"), "symbol_limit": risk.get("symbol_limit"),
        },
        "geometry": {
            "entry": legacy.get("entry"), "causal_invalidation": legacy.get("causal_invalidation"),
            "causal_invalidation_distance_bps": diagnostic.get("causal_invalidation_distance_bps"),
            "atr": legacy.get("atr"), "atr_buffer_multiplier": diagnostic.get("atr_buffer_multiplier"),
            "atr_buffer_bps": diagnostic.get("atr_buffer_bps"), "raw_stop": legacy.get("raw_stop"),
            "final_stop": legacy.get("stop"), "stop_distance_bps": legacy.get("stop_distance_bps"),
            "stop_envelope_bps": legacy.get("stop_envelope_bps"), "stop_envelope_pass": diagnostic.get("stop_envelope_pass"),
            "target_source_type": legacy.get("target_source"), "causal_target": legacy.get("target"),
            "target_distance_bps": legacy.get("target_distance_bps"), "target_available": legacy.get("target_valid"),
            "causal_target_exists": diagnostic.get("causal_target_exists"),
            "economically_actionable_target_exists": diagnostic.get("economically_actionable_target_exists"),
            "minimum_actionable_target_bps": diagnostic.get("minimum_actionable_target_bps"),
            "minimum_positive_edge_bps": diagnostic.get("minimum_positive_edge_bps"),
            "target_considerations": diagnostic.get("target_considerations") or [],
            "next_target_considered": diagnostic.get("next_target_considered"),
            "opportunity_id": diagnostic.get("opportunity_id"),
            "gross_reward_bps": diagnostic.get("gross_reward_bps"), "gross_risk_bps": diagnostic.get("gross_risk_bps"),
            "gross_rr": legacy.get("gross_rr"),
        },
        "cost_economics": {
            "fee_source": diagnostic.get("fee_source"), "entry_fee_bps": legacy.get("entry_fee_bps"),
            "exit_fee_bps": legacy.get("exit_fee_bps"), "spread_source": diagnostic.get("spread_source"),
            "spread_bps": legacy.get("spread_bps"), "entry_slippage_bps": legacy.get("entry_slippage_bps"),
            "exit_slippage_bps": legacy.get("exit_slippage_bps"), "depth_impact_source": diagnostic.get("depth_impact_source"),
            "depth_impact_bps": legacy.get("depth_impact_bps"), "safety_margin_bps": legacy.get("safety_margin_bps"),
            "total_known_cost_bps": legacy.get("total_cost_bps"), "gross_target_bps": diagnostic.get("gross_target_bps"),
            "net_reward_bps": diagnostic.get("net_reward_bps"), "effective_risk_bps": diagnostic.get("effective_risk_bps"),
            "expected_net_edge_bps": legacy.get("expected_net_edge_bps"), "gross_rr": legacy.get("gross_rr"),
            "net_rr": legacy.get("net_rr"), "break_even_win_rate": legacy.get("break_even_win_rate"),
            "economic_gate_enabled": diagnostic.get("economic_gate_enabled"),
            "economic_gate_pass": diagnostic.get("economic_gate_pass"),
        },
        "rr_cohorts": {
            "rr_1_0_pass": _mapping(diagnostic.get("rr_cohorts_net")).get("1.00"),
            "rr_1_2_pass": _mapping(diagnostic.get("rr_cohorts_net")).get("1.20"),
            "rr_1_5_pass": _mapping(diagnostic.get("rr_cohorts_net")).get("1.50"),
        },
        "paper_outcome": {
            "planned_entry": planned.get("planned_entry") or legacy.get("entry"),
            "planned_stop": planned.get("planned_stop") or legacy.get("stop"),
            "planned_target": planned.get("planned_target") or legacy.get("target"),
            "planned_rr": planned.get("planned_rr") or legacy.get("gross_rr"), "net_rr": legacy.get("net_rr"),
            "valid_until_ms": planned.get("valid_until_ms") or meta.get("valid_until_ms"),
            "paper_no_plan_reason": None if legacy.get("plan_status") == "PAPER_PLAN_READY" else first_reason,
            "command_id": outcome.get("command_id"), "position_id": outcome.get("position_id"),
            "entry_time_utc": _json_scalar(outcome.get("entry_time_utc")), "exit_time_utc": _json_scalar(outcome.get("exit_time_utc")),
            "holding_time_seconds": outcome.get("holding_time_seconds"), "exit_reason": outcome.get("exit_reason"),
            "gross_pnl": None, "net_pnl": _json_scalar(outcome.get("net_pnl")), "fees": _json_scalar(outcome.get("fees")),
            "slippage": None, "mfe_bps": None, "mae_bps": None,
        },
        "first_rejection_stage": first_stage, "first_rejection_reason_code": first_reason,
        "raw_reason_codes": reasons,
    }


def _flatten(value: object, prefix: str = "") -> dict[str, object]:
    if isinstance(value, Mapping):
        output: dict[str, object] = {}
        for key, item in value.items():
            output.update(_flatten(item, f"{prefix}.{key}" if prefix else str(key)))
        return output
    if isinstance(value, (list, tuple)):
        return {prefix: json.dumps(value, ensure_ascii=False, separators=(",", ":"))}
    return {prefix: value}


def _summary_source(records: Iterable[tuple[OnlinePipelineRun, OnlinePipelineResultRow | None]]) -> list[dict[str, Any]]:
    return [_source_row(run, result) for run, result in records]


def build_summary(
    pairs: tuple[tuple[OnlinePipelineRun, OnlinePipelineResultRow | None], ...],
    records: list[dict[str, Any]],
    *,
    profile_id: str,
    from_ms: int,
    to_ms: int,
    expected_symbols: int,
) -> dict[str, Any]:
    if not pairs:
        return {
            "export_schema_version": EXPORT_SCHEMA_VERSION, "sample_status": "INSUFFICIENT_SAMPLE",
            "profile": profile_id, "from_ms": from_ms, "to_ms": to_ms, "symbols": [],
            "boundaries": 0, "evaluations": 0, "funnel": {}, "top_rejection_reasons": [],
        }
    value = aggregate(
        _summary_source(pairs), expected_symbols=expected_symbols,
        boundary_interval_ms=300_000 if profile_id == "trade-5m-v1" else 900_000,
        include_calibration_cohorts=False,
    )
    value.pop("export_rows", None)
    value.update({
        "export_schema_version": EXPORT_SCHEMA_VERSION,
        "sample_status": "OK" if len(records) >= expected_symbols else "INSUFFICIENT_SAMPLE",
        "profile": profile_id, "from_ms": from_ms, "to_ms": to_ms,
        "symbols": sorted({record["market_analysis"]["symbol"] for record in records}),
        "boundaries": len({record["market_analysis"]["boundary_closed_at_ms"] for record in records}),
        "evaluations": len(records),
        "top_rejection_reasons": sorted(
            ({"reason": key, "count": item["count"]} for key, item in value["rejection_histogram"].items()),
            key=lambda item: (-item["count"], item["reason"]),
        )[:20],
    })
    return value


def render_export(records: list[dict[str, Any]], summary: Mapping[str, Any], format_name: str) -> tuple[bytes, str, str]:
    if format_name == "jsonl":
        body = "".join(json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for item in records)
        return body.encode("utf-8"), "application/x-ndjson", "jsonl"
    if format_name == "csv":
        flat = [_flatten(item) for item in records]
        fields = sorted({key for item in flat for key in item})
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(flat)
        return stream.getvalue().encode("utf-8-sig"), "text/csv; charset=utf-8", "csv"
    if format_name == "summary-json":
        return (json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"), "application/json", "json"
    lines = ["# Trading Funnel report", "", f"- Profile: `{summary.get('profile')}`",
             f"- Sample: `{summary.get('sample_status')}`", f"- Evaluations: {summary.get('evaluations', 0)}",
             f"- Boundaries: {summary.get('boundaries', 0)}", "", "## Funnel", ""]
    lines.extend(f"- {stage}: {item.get('count', 0)}" for stage, item in _mapping(summary.get("funnel")).items())
    lines.extend(["", "## Top rejection reasons", ""])
    lines.extend(f"- {item['reason']}: {item['count']}" for item in summary.get("top_rejection_reasons", []))
    return ("\n".join(lines) + "\n").encode("utf-8"), "text/markdown; charset=utf-8", "md"
