from __future__ import annotations

from dataclasses import replace

import pytest

from app.engine_execution.paper_idempotency import simulated_fill_id
from app.engine_paper.fill_causal_boundary import (
    PAPER_FILL_CAUSAL_BOUNDARY_VERSION,
    PaperFillBoundaryOutcome,
    PaperFillCausalBoundary,
    PaperFillSourceEntityType,
    resolve_paper_fill_causal_boundary,
)
from app.engine_paper.fill_simulator import (
    FillSimulationOutcome,
    FillSimulationRequest,
    PaperFillRole,
    simulate_paper_fill,
)
from app.engine_safety import PaperSide

from .conftest import T0, T1, T10, T11, make_candle, make_policy


def _assert_rejected(call):
    try:
        call()
    except BaseException:
        return
    raise AssertionError("invalid contract material was accepted")


def _close_resolution(graph, **changes):
    values = {
        "fill_role": PaperFillRole.CLOSE,
        "command": graph["command"],
        "order": graph["close_order"],
        "simulation_policy": graph["policy"],
        "correlation_id": "correlation:remediation:1",
        "causation_id": "causation:remediation:1",
        "exit_decision": graph["decision"],
        "position": graph["position"],
        "entry_order": graph["entry_order"],
        "entry_fill": graph["entry_fill"],
    }
    values.update(changes)
    return resolve_paper_fill_causal_boundary(**values)


def test_entry_boundary_is_exact_command_boundary(causal_graph):
    result = resolve_paper_fill_causal_boundary(
        fill_role=PaperFillRole.ENTRY,
        command=causal_graph["command"],
        order=causal_graph["entry_order"],
        simulation_policy=causal_graph["policy"],
        correlation_id="correlation:remediation:1",
        causation_id="causation:remediation:1",
    )
    assert result.outcome is PaperFillBoundaryOutcome.BOUNDARY_RESOLVED
    assert result.boundary.source_entity_type is (
        PaperFillSourceEntityType.PAPER_EXECUTION_COMMAND
    )
    assert result.boundary.source_entity_id == causal_graph["command"].command_id
    assert result.boundary.source_closed_until_ms == T0


def test_close_boundary_is_exact_exit_decision_boundary(causal_graph):
    result = _close_resolution(causal_graph)
    assert result.outcome is PaperFillBoundaryOutcome.BOUNDARY_RESOLVED
    assert result.boundary.source_entity_type is (
        PaperFillSourceEntityType.PAPER_EXIT_DECISION
    )
    assert result.boundary.source_entity_id == causal_graph["decision"].exit_decision_id
    assert result.boundary.source_closed_until_ms == T10
    assert result.boundary.source_closed_until_ms != causal_graph["command"].closed_until_ms


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("contract_version", "V2"),
        ("source_entity_id", ""),
        ("order_id", ""),
        ("symbol", ""),
        ("timeframe", "5m"),
        ("latency_candles", 0),
        ("latency_candles", 2),
        ("simulation_policy_id", ""),
        ("slippage_policy_id", ""),
        ("fee_policy_id", ""),
        ("latency_policy_id", ""),
        ("correlation_id", ""),
        ("causation_id", ""),
        ("source_closed_until_ms", -1),
        ("source_closed_until_ms", T10 + 1),
        ("source_closed_until_ms", True),
    ],
)
def test_boundary_contract_rejects_invalid_material(causal_graph, field, value):
    boundary = _close_resolution(causal_graph).boundary
    _assert_rejected(lambda: replace(boundary, **{field: value}))


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("command_missing", PaperFillBoundaryOutcome.COMMAND_REQUIRED),
        ("order_missing", PaperFillBoundaryOutcome.ORDER_REQUIRED),
        ("exit_missing", PaperFillBoundaryOutcome.EXIT_DECISION_REQUIRED),
        ("position_missing", PaperFillBoundaryOutcome.POSITION_REQUIRED),
        ("entry_order_missing", PaperFillBoundaryOutcome.SOURCE_GRAPH_INCONSISTENT),
        ("entry_fill_missing", PaperFillBoundaryOutcome.SOURCE_GRAPH_INCONSISTENT),
        ("order_command", PaperFillBoundaryOutcome.SOURCE_GRAPH_INCONSISTENT),
        ("role_key", PaperFillBoundaryOutcome.ROLE_SOURCE_MISMATCH),
        ("order_symbol", PaperFillBoundaryOutcome.SYMBOL_MISMATCH),
        ("order_side", PaperFillBoundaryOutcome.SIDE_MISMATCH),
        ("policy", PaperFillBoundaryOutcome.POLICY_MISMATCH),
        ("decision_position", PaperFillBoundaryOutcome.SOURCE_GRAPH_INCONSISTENT),
        ("decision_quantity", PaperFillBoundaryOutcome.SOURCE_GRAPH_INCONSISTENT),
        ("decision_before_open", PaperFillBoundaryOutcome.SOURCE_BOUNDARY_PRECEDES_POSITION_OPEN),
        ("entry_order", PaperFillBoundaryOutcome.SOURCE_GRAPH_INCONSISTENT),
        ("entry_fill", PaperFillBoundaryOutcome.SOURCE_GRAPH_INCONSISTENT),
        ("close_quantity", PaperFillBoundaryOutcome.SOURCE_GRAPH_INCONSISTENT),
        ("position_symbol", PaperFillBoundaryOutcome.SYMBOL_MISMATCH),
        ("position_side", PaperFillBoundaryOutcome.SIDE_MISMATCH),
    ],
)
def test_close_resolver_fail_closed_matrix(causal_graph, mutation, expected):
    changes = {}
    if mutation == "command_missing":
        changes["command"] = None
    elif mutation == "order_missing":
        changes["order"] = None
    elif mutation == "exit_missing":
        changes["exit_decision"] = None
    elif mutation == "position_missing":
        changes["position"] = None
    elif mutation == "entry_order_missing":
        changes["entry_order"] = None
    elif mutation == "entry_fill_missing":
        changes["entry_fill"] = None
    elif mutation == "order_command":
        changes["order"] = replace(causal_graph["close_order"], command_id="command:other")
    elif mutation == "role_key":
        changes["order"] = replace(
            causal_graph["close_order"],
            idempotency_key=causal_graph["entry_order"].idempotency_key,
        )
    elif mutation == "order_symbol":
        changes["order"] = replace(causal_graph["close_order"], symbol="ETHUSDT")
    elif mutation == "order_side":
        changes["order"] = replace(causal_graph["close_order"], side=PaperSide.SHORT)
    elif mutation == "policy":
        changes["simulation_policy"] = make_policy(
            simulation_policy_id="simulation:other:v1"
        )
    elif mutation == "decision_position":
        changes["exit_decision"] = replace(
            causal_graph["decision"], position_id="position:other"
        )
    elif mutation == "decision_quantity":
        changes["exit_decision"] = replace(
            causal_graph["decision"], requested_close_quantity=causal_graph["decision"].requested_close_quantity / 2
        )
    elif mutation == "decision_before_open":
        changes["exit_decision"] = replace(
            causal_graph["decision"], source_closed_until_ms=T0
        )
    elif mutation == "entry_order":
        changes["entry_order"] = replace(
            causal_graph["entry_order"], order_id="order:other"
        )
    elif mutation == "entry_fill":
        changes["entry_fill"] = replace(
            causal_graph["entry_fill"], fill_id="fill:other"
        )
    elif mutation == "close_quantity":
        changes["order"] = replace(
            causal_graph["close_order"],
            requested_quantity=causal_graph["close_order"].requested_quantity / 2,
        )
    elif mutation == "position_symbol":
        changes["position"] = replace(causal_graph["position"], symbol="ETHUSDT")
    elif mutation == "position_side":
        changes["position"] = replace(causal_graph["position"], side=PaperSide.SHORT)
    result = _close_resolution(causal_graph, **changes)
    assert result.outcome is expected
    assert result.boundary is None


@pytest.mark.parametrize("extra", ["exit", "position", "entry_order", "entry_fill"])
def test_entry_forbids_close_graph_material(causal_graph, extra):
    changes = {
        "exit": {"exit_decision": causal_graph["decision"]},
        "position": {"position": causal_graph["position"]},
        "entry_order": {"entry_order": causal_graph["entry_order"]},
        "entry_fill": {"entry_fill": causal_graph["entry_fill"]},
    }[extra]
    result = resolve_paper_fill_causal_boundary(
        fill_role=PaperFillRole.ENTRY,
        command=causal_graph["command"],
        order=causal_graph["entry_order"],
        simulation_policy=causal_graph["policy"],
        correlation_id="correlation:remediation:1",
        causation_id="causation:remediation:1",
        **changes,
    )
    assert result.outcome is PaperFillBoundaryOutcome.ROLE_SOURCE_MISMATCH


def _simulate_close(graph, boundary=None, candle=None):
    boundary = boundary or _close_resolution(graph).boundary
    candle = candle or make_candle(T10)
    return simulate_paper_fill(
        FillSimulationRequest(
            command=graph["command"],
            order=graph["close_order"],
            fill_role=PaperFillRole.CLOSE,
            causal_boundary=boundary,
            quote_asset="USDT",
            simulation_policy=graph["policy"],
            candidate_candles=(candle,),
            market_snapshot_closed_until_ms=candle.close_boundary_ms,
            correlation_id="correlation:remediation:1",
            causation_id="causation:remediation:1",
        )
    )


def test_close_simulator_selects_t10_to_t11_not_t0_to_t1(causal_graph):
    result = _simulate_close(causal_graph)
    assert result.outcome is FillSimulationOutcome.FILLED
    assert result.selected_candle.open_time_ms == T10
    assert result.selected_candle.close_boundary_ms == T11
    assert result.fill.source_closed_until_ms == T11


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("order_id", "order:other"),
        ("symbol", "ETHUSDT"),
        ("source_closed_until_ms", T10 + 60_000),
        ("simulation_policy_id", "simulation:other"),
        ("slippage_policy_id", "slippage:other"),
        ("fee_policy_id", "fee:other"),
        ("latency_policy_id", "latency:other"),
    ],
)
def test_simulator_rejects_unvalidated_boundary_material(causal_graph, field, value):
    boundary = replace(_close_resolution(causal_graph).boundary, **{field: value})
    result = _simulate_close(causal_graph, boundary=boundary)
    assert result.outcome in {
        FillSimulationOutcome.INVALID_CAUSAL_BOUNDARY,
        FillSimulationOutcome.INVALID_POLICY,
        FillSimulationOutcome.MARKET_DATA_GAP,
        FillSimulationOutcome.NOT_YET_ELIGIBLE,
    }
    assert result.fill is None


@pytest.mark.parametrize(
    "open_ms",
    [T0, T0 + 60_000, T10 - 120_000, T10 - 60_000, T10 + 60_000, T10 + 120_000],
)
def test_close_has_no_previous_or_later_candle_fallback(causal_graph, open_ms):
    result = _simulate_close(causal_graph, candle=make_candle(open_ms))
    assert result.outcome is not FillSimulationOutcome.FILLED


@pytest.mark.parametrize(
    ("material", "delta"),
    [
        ("exit_id", 1),
        ("exit_id", 2),
        ("exit_id", 3),
        ("exit_boundary", 1),
        ("exit_boundary", 2),
        ("exit_boundary", 3),
        ("order", 1),
        ("order", 2),
        ("simulation", 1),
        ("simulation", 2),
        ("slippage", 1),
        ("fee", 1),
        ("latency", 1),
    ],
)
def test_close_v2_identity_changes_with_material_cause(causal_graph, material, delta):
    baseline = _simulate_close(causal_graph).fill.fill_id
    boundary = _close_resolution(causal_graph).boundary
    order = causal_graph["close_order"]
    policy = causal_graph["policy"]
    if material == "exit_id":
        boundary = replace(boundary, source_entity_id=f"exit:changed:{delta}")
    elif material == "exit_boundary":
        shifted = T10 + delta * 60_000
        boundary = replace(boundary, source_closed_until_ms=shifted)
    elif material == "order":
        order = replace(order, order_id=f"order:changed:{delta}")
        boundary = replace(boundary, order_id=order.order_id)
    else:
        field = {
            "simulation": "simulation_policy_id",
            "slippage": "slippage_policy_id",
            "fee": "fee_policy_id",
            "latency": "latency_policy_id",
        }[material]
        changed = f"{field}:changed:{delta}"
        policy = replace(policy, **{field: changed})
        boundary = replace(boundary, **{field: changed})
    candle = make_candle(boundary.source_closed_until_ms)
    result = simulate_paper_fill(
        FillSimulationRequest(
            command=(
                replace(causal_graph["command"], **{
                    {
                        "simulation": "simulation_policy_id",
                        "slippage": "slippage_policy_id",
                        "fee": "fee_policy_id",
                        "latency": "latency_policy_id",
                    }[material]: getattr(policy, {
                        "simulation": "simulation_policy_id",
                        "slippage": "slippage_policy_id",
                        "fee": "fee_policy_id",
                        "latency": "latency_policy_id",
                    }[material])
                })
                if material in {"simulation", "slippage", "fee", "latency"}
                else causal_graph["command"]
            ),
            order=order,
            fill_role=PaperFillRole.CLOSE,
            causal_boundary=boundary,
            quote_asset="USDT",
            simulation_policy=policy,
            candidate_candles=(candle,),
            market_snapshot_closed_until_ms=candle.close_boundary_ms,
            correlation_id="correlation:remediation:1",
            causation_id="causation:remediation:1",
        )
    )
    assert result.outcome is FillSimulationOutcome.FILLED
    assert result.fill.fill_id != baseline
    assert result.fill.fill_id.startswith("paper:fill-id:v2:")


def test_entry_fill_identity_remains_exact_v1(causal_graph):
    expected = simulated_fill_id(
        contract_version=causal_graph["policy"].contract_version,
        order_id=causal_graph["entry_order"].order_id,
        fill_role="ENTRY",
        source_open_time_ms=T0,
        source_close_boundary_ms=T1,
        simulation_policy_id=causal_graph["policy"].simulation_policy_id,
        slippage_policy_id=causal_graph["policy"].slippage_policy_id,
        fee_policy_id=causal_graph["policy"].fee_policy_id,
        latency_policy_id=causal_graph["policy"].latency_policy_id,
    )
    assert causal_graph["entry_fill"].fill_id == expected
    assert expected.startswith("paper:fill-id:v1:")
