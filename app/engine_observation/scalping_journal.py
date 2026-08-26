"""Lossless normalized Scalping evaluation journal projection."""

from __future__ import annotations

from collections.abc import Mapping


def _map(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def build_scalping_evaluation_journal(
    *, profile: str, parameter_set_id: str, boundary_ms: int, symbol: str,
    analysis: Mapping[str, object], setup: Mapping[str, object],
    strategy: Mapping[str, object], risk: Mapping[str, object],
    paper: Mapping[str, object],
) -> dict[str, object]:
    shadow_plan = _map(paper.get("shadow_plan")) or paper
    context = _map(shadow_plan.get("paper_context"))
    diagnostic = _map(context.get("scalping_geometry_diagnostics"))
    strategy_context = _map(strategy.get("context"))
    return {
        "schema_version": "scalping-evaluation-journal-v1",
        "profile": profile,
        "parameter_set_id": parameter_set_id,
        "boundary_ms": boundary_ms,
        "symbol": symbol,
        "regime": _map(analysis.get("analysis_context")).get("regime"),
        "direction": setup.get("direction_hint"),
        "analysis_inputs": analysis,
        "setup": setup,
        "strategy": {
            "raw_score": strategy_context.get("raw_score") or strategy.get("strategy_score"),
            "final_score": strategy.get("strategy_score"),
            "components": strategy_context.get("scalping_score_components"),
            "penalties": strategy_context.get("score_penalties"),
            "cap": strategy_context.get("score_cap"),
            "cap_reason": strategy_context.get("score_cap_reason"),
            "boolean_gates": strategy_context.get("boolean_gates"),
            "threshold": strategy_context.get("threshold"),
            "margin": strategy_context.get("score_margin"),
            "terminal_reason": (
                list(strategy.get("rejection_reasons") or [])
                or list(strategy.get("decision_reasons") or [])
                or None
            ),
        },
        "geometry": {
            key: diagnostic.get(key) for key in (
                "entry", "causal_invalidation", "causal_target", "atr",
                "final_stop", "stop_distance_bps", "target_distance_bps",
                "target_source_type", "opportunity_id",
            )
        },
        "economics": {
            key: diagnostic.get(key) for key in (
                "spread_bps", "entry_fee_bps", "exit_fee_bps",
                "entry_slippage_bps", "exit_slippage_bps", "depth_impact_bps",
                "safety_margin_bps", "total_cost_bps", "gross_rr", "net_rr",
                "expected_net_edge_bps", "break_even_win_rate",
            )
        },
        "risk": risk,
        "execution": None,
        "mfe_bps": None,
        "mae_bps": None,
        "holding_time_ms": None,
        "exit_reason": None,
        "gross_pnl": None,
        "net_pnl": None,
    }
