from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.engine_paper.accounting import PaperAccountSummary
from app.engine_paper.controlled_quantity_validity import (
    DECISION_TIMEFRAME_MS,
    QUANTITY_POLICY_VERSION,
    VALIDITY_POLICY_VERSION,
    calculate_controlled_quantity,
    derive_approval_valid_until_ms,
    issue_controlled_paper_quantity_approval,
)
from app.engine_paper.paper_approvals import (
    finalize_paper_risk_approval,
    finalize_paper_strategy_approval,
    map_final_approvals_to_command_compatibility,
)
from app.engine_safety.paper_domain import PaperDomainError
from app.instrument_constraints.registry import (
    ACTIVE_QUANTITY_CONSTRAINT_REGISTRY as REGISTRY,
    MARKET_TYPE,
    REGISTRY_VERSION,
    SOURCE_OBSERVED_AT_UTC,
    InstrumentConstraintRegistryError,
    InstrumentQuantityConstraintRegistry,
    normalize_binance_spot_exchange_info,
)
from app.trading_universe.domain import PREPARED_NEXT_TRADING_UNIVERSE
from tests.paper_approval_remediation.conftest import make_risk, make_strategy, strategy_kwargs


CLOSED = 1_700_000_099_999  # exact Binance-style 15m close boundary
APPROVED_AT = datetime.fromtimestamp((CLOSED + 1_000) / 1000, tz=timezone.utc)


def account(equity: Decimal = Decimal("100")) -> PaperAccountSummary:
    zero = Decimal("0")
    return PaperAccountSummary(
        "account:1", "session:1", "USDT", equity, equity, zero, zero, zero,
        zero, 0, 0, 0, 0, zero, zero, zero, None, None, None, None, None, None,
    )


def chain(symbol: str = "BTCUSDT", *, entry: str = "1", stop: str = "0.99"):
    research_strategy = make_strategy(symbol=symbol, closed_until_ms=CLOSED)
    research_risk = make_risk(symbol=symbol, closed_until_ms=CLOSED)
    valid = CLOSED + DECISION_TIMEFRAME_MS
    strategy = finalize_paper_strategy_approval(
        research_strategy,
        **strategy_kwargs(
            entry_reference_price=Decimal(entry), stop_price=Decimal(stop),
            target_price=Decimal("120") if Decimal(entry) < Decimal("120") else Decimal(entry) + Decimal("20"),
            approved_at=APPROVED_AT, valid_until_ms=valid,
            evaluation_time_ms=CLOSED + 2_000,
            symbol_constraints_id=REGISTRY_VERSION,
        ),
    )
    return research_risk, strategy


def assert_paper_error(action) -> None:
    try:
        action()
    except PaperDomainError:
        return
    raise AssertionError("PaperDomainError was not raised")


def source_payload() -> dict[str, object]:
    symbols = []
    for symbol in PREPARED_NEXT_TRADING_UNIVERSE.symbols:
        item = REGISTRY.for_symbol(symbol)
        native = item.source_filters
        symbols.append({
            "symbol": symbol, "status": "TRADING", "baseAsset": item.base_asset,
            "isSpotTradingAllowed": True,
            "filters": [
                {"filterType": "LOT_SIZE", "minQty": format(native.lot_min_qty, "f"), "maxQty": format(native.lot_max_qty, "f"), "stepSize": format(native.lot_step_size, "f")},
                {"filterType": "MARKET_LOT_SIZE", "minQty": format(native.market_min_qty, "f"), "maxQty": format(native.market_max_qty, "f"), "stepSize": format(native.market_step_size, "f")},
                {"filterType": "NOTIONAL", "minNotional": format(native.min_notional, "f"), "maxNotional": format(native.max_notional, "f"), "applyMinToMarket": True, "applyMaxToMarket": False},
            ],
        })
    return {"symbols": symbols}


def test_registry_exact_immutable_provenance_and_decimal_contract():
    assert tuple(REGISTRY.symbols) == PREPARED_NEXT_TRADING_UNIVERSE.symbols
    assert len(REGISTRY.symbols) == 10
    assert REGISTRY.version == REGISTRY_VERSION
    assert REGISTRY.universe_id == "trading-universe-v2"
    assert REGISTRY.market_type == MARKET_TYPE
    assert SOURCE_OBSERVED_AT_UTC.endswith("Z")
    assert all(isinstance(item.quantity_step, Decimal) for item in REGISTRY.symbols.values())
    assert all(item.source_filter_names == ("LOT_SIZE", "MARKET_LOT_SIZE", "NOTIONAL") for item in REGISTRY.symbols.values())
    with pytest.raises(TypeError):
        REGISTRY.symbols["BTCUSDT"] = REGISTRY.for_symbol("BTCUSDT")  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        REGISTRY.version = "other"  # type: ignore[misc]


def test_source_normalization_is_deterministic_and_matches_registry():
    assert normalize_binance_spot_exchange_info(source_payload()) == REGISTRY
    assert normalize_binance_spot_exchange_info(source_payload()) == normalize_binance_spot_exchange_info(source_payload())


@pytest.mark.parametrize("mutation", ["duplicate", "missing", "extra", "invalid_step", "bad_status", "bad_notional_applicability"])
def test_registry_load_fails_closed(mutation: str):
    payload = source_payload()
    symbols = payload["symbols"]
    assert isinstance(symbols, list)
    if mutation == "duplicate":
        symbols.append(symbols[0])
    elif mutation == "missing":
        symbols.pop()
    elif mutation == "extra":
        symbols.append({**symbols[0], "symbol": "EXTRAUSDT"})
    elif mutation == "invalid_step":
        symbols[0]["filters"][0]["stepSize"] = "0"
    elif mutation == "bad_status":
        symbols[0]["status"] = "BREAK"
    else:
        symbols[0]["filters"][2]["applyMinToMarket"] = False
    with pytest.raises(InstrumentConstraintRegistryError):
        normalize_binance_spot_exchange_info(payload)


def test_wrong_universe_and_version_fail_closed():
    with pytest.raises(InstrumentConstraintRegistryError):
        InstrumentQuantityConstraintRegistry(
            "wrong", REGISTRY.universe_id, REGISTRY.market_type,
            REGISTRY.source_endpoint_kind, REGISTRY.source_observed_at_utc,
            REGISTRY.source_snapshot_sha256, REGISTRY.symbols,
        )
    with pytest.raises(InstrumentConstraintRegistryError):
        InstrumentQuantityConstraintRegistry(
            REGISTRY.version, "wrong", REGISTRY.market_type,
            REGISTRY.source_endpoint_kind, REGISTRY.source_observed_at_utc,
            REGISTRY.source_snapshot_sha256, REGISTRY.symbols,
        )


@pytest.mark.parametrize("symbol", PREPARED_NEXT_TRADING_UNIVERSE.symbols)
def test_quantity_authority_all_ten_symbols(symbol: str):
    risk, strategy = chain(symbol)
    audit = calculate_controlled_quantity(strategy=strategy, account=account())
    constraint = REGISTRY.for_symbol(symbol)
    assert audit.quantity_policy_version == QUANTITY_POLICY_VERSION
    assert audit.instrument_registry_version == REGISTRY_VERSION
    assert audit.normalized_quantity <= min(audit.raw_quantity, audit.balance_cap_quantity)
    assert audit.normalized_quantity % constraint.quantity_step == 0
    assert audit.normalized_quantity >= constraint.min_quantity
    assert audit.normalized_quantity * audit.entry_price >= constraint.min_notional
    result = issue_controlled_paper_quantity_approval(
        strategy, risk, account(), approved_at=APPROVED_AT,
        evaluation_time_ms=CLOSED + 2_000,
    )
    assert result.approval.approved_quantity == audit.normalized_quantity
    assert result.validity_policy_version == VALIDITY_POLICY_VERSION
    assert result.to_persisted_payload()["quantity_sizing_audit"]["instrument_registry_version"] == REGISTRY_VERSION


def test_quantity_caps_round_down_and_never_exceeds_risk_or_equity():
    _, strategy = chain()
    audit = calculate_controlled_quantity(strategy=strategy, account=account())
    assert audit.normalized_quantity == Decimal("100.00000")
    assert audit.normalized_quantity * audit.risk_per_unit <= audit.risk_budget
    assert audit.normalized_quantity * audit.entry_price <= audit.paper_equity_at_approval
    assert audit.normalized_quantity <= audit.balance_cap_quantity


@pytest.mark.parametrize("equity", ["0", "0.01"])
def test_quantity_invalid_or_minimum_constraints_fail_closed(equity: str):
    _, strategy = chain()
    assert_paper_error(lambda: calculate_controlled_quantity(strategy=strategy, account=account(Decimal(equity))))


def test_invalid_stop_fails_before_quantity_approval():
    assert_paper_error(lambda: chain(entry="1", stop="1"))


def test_wrong_registry_binding_and_cross_symbol_fail_closed():
    _, strategy = chain()
    assert_paper_error(lambda: calculate_controlled_quantity(strategy=replace(strategy, symbol_constraints_id="wrong"), account=account()))
    assert_paper_error(lambda: calculate_controlled_quantity(strategy=replace(strategy, symbol="ETHUSDT"), account=account()))


def test_validity_next_boundary_stricter_no_extension_and_replay():
    expected = CLOSED + DECISION_TIMEFRAME_MS
    assert derive_approval_valid_until_ms(CLOSED) == expected
    assert derive_approval_valid_until_ms(CLOSED) == derive_approval_valid_until_ms(CLOSED)
    assert derive_approval_valid_until_ms(CLOSED, stricter_valid_until_ms=(expected - 1,)) == expected - 1
    assert_paper_error(lambda: derive_approval_valid_until_ms(CLOSED, evaluation_time_ms=expected + 1))
    assert_paper_error(lambda: derive_approval_valid_until_ms(CLOSED + 1))


def test_replay_identity_and_final_approval_prerequisite_compatibility():
    risk, strategy = chain()
    kwargs = dict(approved_at=APPROVED_AT, evaluation_time_ms=CLOSED + 2_000)
    one = issue_controlled_paper_quantity_approval(strategy, risk, account(), **kwargs)
    two = issue_controlled_paper_quantity_approval(strategy, risk, account(), **kwargs)
    assert one == two
    assert one.approval.quantity_approval_id == two.approval.quantity_approval_id
    final_risk = finalize_paper_risk_approval(
        strategy, risk, one.approval, mode="PAPER", paper_authorized=True,
        approved_at=APPROVED_AT, evaluation_time_ms=CLOSED + 2_000,
        correlation_id=strategy.pipeline_run_id,
        causation_id=one.approval.quantity_approval_id,
    )
    compatibility = map_final_approvals_to_command_compatibility(
        strategy, one.approval, final_risk,
    )
    assert compatibility.approved_quantity == one.audit.normalized_quantity
    assert compatibility.valid_until_ms == min(
        strategy.valid_until_ms, one.approval.valid_until_ms, final_risk.valid_until_ms,
    )


def test_quantity_concurrent_replay_has_one_semantic_identity():
    risk, strategy = chain()
    def issue():
        return issue_controlled_paper_quantity_approval(
            strategy, risk, account(), approved_at=APPROVED_AT,
            evaluation_time_ms=CLOSED + 2_000,
        ).approval.quantity_approval_id
    with ThreadPoolExecutor(max_workers=8) as pool:
        identities = tuple(pool.map(lambda _: issue(), range(32)))
    assert len(set(identities)) == 1


@pytest.mark.parametrize("status", ["REJECT", "WAIT"])
def test_rejected_or_deferred_risk_cannot_receive_quantity(status: str):
    _, strategy = chain()
    rejected = make_risk(symbol="BTCUSDT", closed_until_ms=CLOSED, risk_status=status)
    assert_paper_error(lambda: issue_controlled_paper_quantity_approval(
            strategy, rejected, account(), approved_at=APPROVED_AT,
            evaluation_time_ms=CLOSED + 2_000,
        ))
