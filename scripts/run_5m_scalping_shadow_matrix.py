"""Deterministic geometry/cost cohort report; never calls an exchange or executor."""

from __future__ import annotations

import json
from itertools import product

from app.engine_paper.scalping_shadow import (
    CausalTarget,
    ShadowCostInputs,
    ShadowGeometryCandidate,
    ShadowGeometryConfig,
    evaluate_scalping_shadow,
    summarize_shadow_configuration,
)


BOUNDARY = 1_700_000_000_000


def fixture_dataset() -> tuple[ShadowGeometryCandidate, ...]:
    def row(symbol: str, entry: float, invalidation: float | None, atr: float | None,
            target: float | None, source: str = "LOCAL_5M", known_offset: int = 0):
        targets = () if target is None else (
            CausalTarget(target, source, BOUNDARY + known_offset),
        )
        return ShadowGeometryCandidate(
            trade_profile_id="trade-5m-v2", symbol=symbol, boundary_ms=BOUNDARY,
            direction="BULLISH", entry=entry, causal_invalidation=invalidation,
            atr=atr, targets=targets,
        )
    return (
        row("BTCUSDT", 100.0, 99.70, 0.10, 101.20),
        row("ETHUSDT", 100.0, 99.55, 0.12, 101.00, "STRUCTURAL"),
        row("SOLUSDT", 100.0, 99.35, 0.10, 101.10),
        row("BNBUSDT", 100.0, 99.20, 0.15, 101.40),
        row("XRPUSDT", 100.0, 99.65, 0.08, 100.25),
        row("ADAUSDT", 100.0, 99.72, 0.10, None),
        row("SUIUSDT", 100.0, 99.68, 0.11, 101.30, known_offset=1),
        row("AVAXUSDT", 100.0, 99.50, 0.20, 101.80, "HIGHER_TF"),
    )


def cost_fixture() -> ShadowCostInputs:
    return ShadowCostInputs(
        spread_bps=1.5, depth_impact_bps=2.5,
        spread_source="DETERMINISTIC_PUBLIC_BOOK_TICKER_FIXTURE",
        depth_impact_source="DETERMINISTIC_PUBLIC_DEPTH_VWAP_FIXTURE",
        spread_authoritative=True, depth_authoritative=True,
    )


def old_geometry_rr(candidate: ShadowGeometryCandidate) -> float | None:
    if candidate.causal_invalidation is None or candidate.atr is None:
        return None
    known = [target for target in candidate.targets if target.known_at_ms <= candidate.boundary_ms]
    if not known:
        return None
    stop = candidate.causal_invalidation - candidate.atr
    risk = candidate.entry - stop
    reward = min(target.price - candidate.entry for target in known if target.price > candidate.entry)
    return reward / risk if risk > 0 and reward > 0 else None


def build_report() -> dict[str, object]:
    dataset = fixture_dataset()
    costs = cost_fixture()
    configurations: list[dict[str, object]] = []
    for multiplier, envelope, target_floor in product(
        (0.25, 0.50, 0.75, 1.00), (50.0, 65.0, 80.0), (45.0, 60.0, 80.0)
    ):
        config = ShadowGeometryConfig(multiplier, envelope, target_floor)
        diagnostics = [evaluate_scalping_shadow(candidate, costs, config) for candidate in dataset]
        base = summarize_shadow_configuration(diagnostics)
        for rr in (1.0, 1.2, 1.5):
            configurations.append({
                "atr_buffer_multiplier": multiplier,
                "stop_envelope_bps": envelope,
                "minimum_target_diagnostic_bps": target_floor,
                "rr_shadow_threshold": rr,
                **base,
                "gross_rr_ge_threshold": sum(
                    row.gross_rr is not None and row.gross_rr >= rr for row in diagnostics
                ),
                "net_rr_ge_threshold": sum(
                    row.net_rr is not None and row.net_rr >= rr for row in diagnostics
                ),
            })
    primary = ShadowGeometryConfig(0.25, 80.0, 45.0)
    primary_rows = [evaluate_scalping_shadow(candidate, costs, primary) for candidate in dataset]
    old_rr = [value for candidate in dataset if (value := old_geometry_rr(candidate)) is not None]
    return {
        "dataset": "DETERMINISTIC_CAUSAL_5M_FIXTURES_V1",
        "dataset_size": len(dataset),
        "execution_authority": "NONE",
        "configuration_count": len(configurations),
        "old_geometry_rr_1_2_pass_count": sum(value >= 1.2 for value in old_rr),
        "new_geometry_rr_1_2_pass_count": sum(
            row.gross_rr is not None and row.gross_rr >= 1.2 for row in primary_rows
        ),
        "new_geometry_net_cost_pass_count": sum(row.economic_gate_pass for row in primary_rows),
        "primary_rejected_diagnostics": [row.to_dict() for row in primary_rows if not row.valid_plan],
        "configurations": configurations,
    }


def compact_markdown(report: dict[str, object]) -> str:
    """Render 36 geometry rows; each row contains all three RR classifications."""
    rows = report["configurations"]
    grouped: dict[tuple[float, float, float], list[dict[str, object]]] = {}
    for row in rows:  # type: ignore[assignment]
        key = (
            float(row["atr_buffer_multiplier"]), float(row["stop_envelope_bps"]),
            float(row["minimum_target_diagnostic_bps"]),
        )
        grouped.setdefault(key, []).append(row)
    lines = [
        "| ATR | Env bps | Target bps | Geometry | Wide | Missing | Cost | Gross RR 1/1.2/1.5 | Net RR 1/1.2/1.5 | Valid/final | Med stop/P90/target/gross/net/edge/BE |",
        "|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|",
    ]
    def fmt(value: object) -> str:
        return "NA" if value is None else f"{float(value):.4f}"
    for key, values in grouped.items():
        values.sort(key=lambda item: float(item["rr_shadow_threshold"]))
        base = values[0]
        gross = "/".join(str(item["gross_rr_ge_threshold"]) for item in values)
        net = "/".join(str(item["net_rr_ge_threshold"]) for item in values)
        stats = "/".join(fmt(base[name]) for name in (
            "median_stop_distance_bps", "p90_stop_distance_bps",
            "median_target_distance_bps", "median_gross_rr", "median_net_rr",
            "median_expected_net_edge_bps", "median_break_even_win_rate",
        ))
        lines.append(
            f"| {key[0]:.2f} | {key[1]:.0f} | {key[2]:.0f} | "
            f"{base['geometry_valid']} | {base['stop_too_wide']} | "
            f"{base['missing_target']} | {base['cost_gate_passed']} | {gross} | {net} | "
            f"{base['valid_plans']}/{base['final_shadow_approvals']} | {stats} |"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    print(json.dumps(build_report(), indent=2, sort_keys=True))
