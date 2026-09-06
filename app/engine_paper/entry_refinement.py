"""Lightweight 1m entry refinement for an already-selected Scalping v2 plan.

The module cannot create a candidate, approval, selector result, stop, target,
or position.  It evaluates one immutable 5m winner and returns an execution
advice which is authoritative only when the caller explicitly selects that
mode.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
import time
from typing import Callable, Mapping, Protocol

from app.engine_market_data.candle import Candle
from app.engine_paper.production_market_data import (
    PaperProductionMarketDataInputAdapter,
    PaperProductionMarketDataReadiness,
    PaperProductionMarketDataRequest,
    PaperProductionMarketDataScope,
)
from app.engine_paper.scalping_shadow import ShadowCostInputs, compute_net_economics
from app.config.trade_parameters import SCALPING_V2


PROFILE_ID = "trade-5m-v2"
MODULE_NAME = "scalping-v2-1m-entry-refinement-v1"
WINDOW_POLICY = "SELECTED_AT_TO_MIN_APPROVAL_VALID_UNTIL_OR_NEXT_5M_BOUNDARY"
WINDOW_SOURCE = "paper-approval-validity-policy-v1_AND_5M_CAUSAL_BOUNDARY"
MODE_ENV = "TRADERS_SCALPING_1M_REFINEMENT_MODE"
FIVE_MIN_MS = 300_000


class EntryRefinementMode(StrEnum):
    OFF = "OFF"
    SHADOW = "SHADOW"
    AUTHORITATIVE = "AUTHORITATIVE"


class EntryRefinementState(StrEnum):
    NOT_REACHED = "NOT_REACHED"
    WAITING_FOR_1M = "WAITING_FOR_1M"
    READY_TO_ENTER = "CONFIRMED"
    REJECTED_1M = "REJECTED"
    EXPIRED_1M = "EXPIRED"
    BYPASSED = "BYPASSED"
    FAILED = "FAILED"


WAITING = "ENTRY_REFINEMENT_WAITING_1M_CLOSE"
CONFIRMED = "ENTRY_REFINEMENT_CONFIRMED"
PRICE_DRIFT = "ENTRY_REFINEMENT_PRICE_DRIFT_TOO_LARGE"
MOMENTUM = "ENTRY_REFINEMENT_MOMENTUM_INVALIDATED"
SPREAD = "ENTRY_REFINEMENT_SPREAD_TOO_WIDE"
EXPIRED = "ENTRY_REFINEMENT_WINDOW_EXPIRED"
STALE = "ENTRY_REFINEMENT_MARKET_DATA_STALE"
NOT_APPLICABLE = "ENTRY_REFINEMENT_NOT_APPLICABLE"
COSTS_UNAVAILABLE = "ENTRY_REFINEMENT_COST_DATA_UNAVAILABLE"
ECONOMICS = "ENTRY_REFINEMENT_ECONOMICS_INVALIDATED"
UPSTREAM_ADMISSION = "ENTRY_REFINEMENT_UPSTREAM_ECONOMICS_OR_CAUSAL_REJECTED"


class CostSource(Protocol):
    def load(self, symbol: str, entry: float, *, safety_margin_bps: float) -> ShadowCostInputs: ...


@dataclass(frozen=True, slots=True)
class EntryRefinementPolicy:
    maximum_price_drift_bps: float
    maximum_spread_bps: float
    minimum_net_edge_bps: float
    required_net_rr: float
    cost_safety_margin_bps: float


@dataclass(frozen=True, slots=True)
class EntryRefinementResult:
    refinement_identity: str
    module_name: str
    mode: str
    state: str
    reason: str
    profile_id: str
    symbol: str
    side: str
    boundary_closed_at_ms: int
    candidate_id: str
    approval_id: str
    plan_id: str
    refinement_started_at: datetime
    refinement_finished_at: datetime | None
    refinement_valid_from_ms: int
    refinement_valid_until_ms: int
    one_min_candle_open_ms: int | None = None
    one_min_candle_close_ms: int | None = None
    one_min_snapshot_id: str | None = None
    one_min_watermark: str | None = None
    one_min_candle_direction: str | None = None
    one_min_body_bps: float | None = None
    one_min_range_bps: float | None = None
    price_at_refinement: Decimal | None = None
    planned_entry: Decimal | None = None
    refined_entry_reference: Decimal | None = None
    price_drift_bps: float | None = None
    spread_bps: float | None = None
    dynamic_fee_bps: float | None = None
    executed_gross_rr: float | None = None
    executed_net_rr: float | None = None
    executed_net_edge_bps: float | None = None
    data_fetch_latency_ms: float | None = None
    refinement_decision_latency_ms: float | None = None
    time_since_previous_close_seconds: float | None = None
    previous_exit_reason: str | None = None
    previous_side: str | None = None
    same_symbol_reentry: bool = False
    direction_flip: bool = False

    @property
    def permits_command(self) -> bool:
        if self.reason == UPSTREAM_ADMISSION:
            return False
        if self.mode in {EntryRefinementMode.OFF.value, EntryRefinementMode.SHADOW.value}:
            return True
        return self.state == EntryRefinementState.READY_TO_ENTER.value

    @property
    def terminal(self) -> bool:
        return self.state in {
            EntryRefinementState.READY_TO_ENTER.value,
            EntryRefinementState.REJECTED_1M.value,
            EntryRefinementState.EXPIRED_1M.value,
            EntryRefinementState.BYPASSED.value,
            EntryRefinementState.FAILED.value,
        }

    def details(self) -> dict[str, object]:
        value = asdict(self)
        for key, item in tuple(value.items()):
            if isinstance(item, datetime):
                value[key] = item.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            elif isinstance(item, Decimal):
                value[key] = format(item, "f")
        value["refinement_decision"] = self.state
        value["refinement_reason"] = self.reason
        return value


def configured_mode() -> EntryRefinementMode:
    # Authoritative promotion is deliberately impossible in this task. The
    # validated server config is the only mode authority.
    return EntryRefinementMode(SCALPING_V2.entry_refinement_1m.mode)


def refinement_identity(candidate: object, *, plan_id: str | None = None) -> str:
    material = "|".join((
        str(candidate.trade_profile_id), str(candidate.symbol),
        str(candidate.watermark.closed_until_ms), str(candidate.candidate_id),
        str(candidate.lineage.final_approval_id), str(plan_id or candidate.lineage.source_run_id),
    ))
    return "entry-refinement:" + sha256(material.encode("utf-8")).hexdigest()


def refinement_window(candidate: object, selected_at: datetime) -> tuple[int, int]:
    started_ms = int(selected_at.astimezone(timezone.utc).timestamp() * 1000)
    next_boundary = int(candidate.watermark.closed_until_ms) + FIVE_MIN_MS
    return started_ms, min(int(candidate.valid_until_ms), next_boundary)


def _direction(candle: Candle) -> str:
    if candle.close > candle.open:
        return "BULLISH"
    if candle.close < candle.open:
        return "BEARISH"
    return "FLAT"


def _bps(delta: Decimal, reference: Decimal) -> float:
    return float(abs(delta) / reference * Decimal("10000"))


class ScalpingEntryRefinementService:
    def __init__(
        self,
        *,
        market_data: PaperProductionMarketDataInputAdapter,
        cost_source: CostSource,
        policy: EntryRefinementPolicy,
        mode: EntryRefinementMode | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.market_data = market_data
        self.cost_source = cost_source
        self.policy = policy
        self.mode = mode or configured_mode()
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def evaluate(
        self,
        candidate: object,
        *,
        selected_at: datetime,
        plan_id: str | None = None,
        previous_close: Mapping[str, object] | None = None,
        economics_admitted: bool = True,
        causal_admitted: bool = True,
    ) -> EntryRefinementResult:
        started = time.perf_counter()
        now = self.clock().astimezone(timezone.utc)
        valid_from, valid_until = refinement_window(candidate, selected_at)
        common = dict(
            refinement_identity=refinement_identity(candidate, plan_id=plan_id), module_name=MODULE_NAME,
            mode=self.mode.value, profile_id=str(candidate.trade_profile_id),
            symbol=str(candidate.symbol), side=str(candidate.side.value),
            boundary_closed_at_ms=int(candidate.watermark.closed_until_ms),
            candidate_id=str(candidate.candidate_id),
            approval_id=str(candidate.lineage.final_approval_id),
            plan_id=str(plan_id or candidate.lineage.source_run_id),
            refinement_started_at=selected_at.astimezone(timezone.utc),
            refinement_valid_from_ms=valid_from, refinement_valid_until_ms=valid_until,
            planned_entry=Decimal(candidate.entry_reference_price),
            time_since_previous_close_seconds=(
                float(previous_close["time_since_previous_close_seconds"])
                if previous_close and previous_close.get("time_since_previous_close_seconds") is not None
                else None
            ),
            previous_exit_reason=(
                str(previous_close["previous_exit_reason"])
                if previous_close and previous_close.get("previous_exit_reason") is not None
                else None
            ),
            previous_side=(
                str(previous_close["previous_side"])
                if previous_close and previous_close.get("previous_side") is not None
                else None
            ),
            same_symbol_reentry=bool(previous_close),
            direction_flip=bool(
                previous_close and previous_close.get("previous_side") != candidate.side.value
            ),
        )
        if candidate.trade_profile_id != PROFILE_ID or self.mode is EntryRefinementMode.OFF:
            return EntryRefinementResult(
                **common, state=EntryRefinementState.BYPASSED.value,
                reason=NOT_APPLICABLE, refinement_finished_at=now,
                refinement_decision_latency_ms=(time.perf_counter() - started) * 1000,
            )
        if not economics_admitted or not causal_admitted:
            return EntryRefinementResult(
                **common, state=EntryRefinementState.REJECTED_1M.value,
                reason=UPSTREAM_ADMISSION, refinement_finished_at=now,
                refinement_decision_latency_ms=(time.perf_counter() - started) * 1000,
            )
        now_ms = int(now.timestamp() * 1000)
        if now_ms > valid_until:
            return EntryRefinementResult(
                **common, state=EntryRefinementState.EXPIRED_1M.value, reason=EXPIRED,
                refinement_finished_at=now,
                refinement_decision_latency_ms=(time.perf_counter() - started) * 1000,
            )
        fetch_started = time.perf_counter()
        market = self.market_data.read(PaperProductionMarketDataRequest(
            PaperProductionMarketDataScope((candidate.symbol,), ("1m",), 2),
            f"{refinement_identity(candidate, plan_id=plan_id)}:{now_ms}", as_of_ms=now_ms,
        ))
        fetch_ms = (time.perf_counter() - fetch_started) * 1000
        if market.readiness is not PaperProductionMarketDataReadiness.READY or market.data is None:
            return EntryRefinementResult(
                **common, state=EntryRefinementState.FAILED.value, reason=STALE,
                refinement_finished_at=now, data_fetch_latency_ms=fetch_ms,
                refinement_decision_latency_ms=(time.perf_counter() - started) * 1000,
            )
        snapshot = market.data.snapshots[0]
        candles = dict(snapshot.candles)["1m"]
        eligible = tuple(
            value for value in candles
            if value.is_closed and value.open_time_ms >= int(candidate.watermark.closed_until_ms)
            and value.close_time_ms + 1 >= valid_from
            and value.close_time_ms + 1 <= now_ms
        )
        if not eligible:
            return EntryRefinementResult(
                **common, state=EntryRefinementState.WAITING_FOR_1M.value, reason=WAITING,
                refinement_finished_at=None, one_min_snapshot_id=snapshot.snapshot_id,
                one_min_watermark=snapshot.watermark.watermark_id,
                data_fetch_latency_ms=fetch_ms,
                refinement_decision_latency_ms=(time.perf_counter() - started) * 1000,
            )
        expected = "BULLISH" if candidate.side.value == "LONG" else "BEARISH"
        # Use the first confirming close. If none exists yet, project the
        # latest contradictory close while retaining WAITING authority.
        candle = next(
            (value for value in eligible if _direction(value) in {expected, "FLAT"}),
            eligible[-1],
        )
        candle_direction = _direction(candle)
        body_bps = _bps(Decimal(candle.close) - Decimal(candle.open), Decimal(candle.open))
        range_bps = _bps(Decimal(candle.high) - Decimal(candle.low), Decimal(candle.open))
        candle_fields = dict(
            one_min_candle_open_ms=candle.open_time_ms,
            one_min_candle_close_ms=candle.close_time_ms + 1,
            one_min_snapshot_id=snapshot.snapshot_id,
            one_min_watermark=snapshot.watermark.watermark_id,
            one_min_candle_direction=candle_direction,
            one_min_body_bps=body_bps, one_min_range_bps=range_bps,
            data_fetch_latency_ms=fetch_ms,
        )
        if candle_direction not in {expected, "FLAT"}:
            return EntryRefinementResult(
                **common, **candle_fields,
                state=EntryRefinementState.WAITING_FOR_1M.value, reason=MOMENTUM,
                refinement_finished_at=None,
                refinement_decision_latency_ms=(time.perf_counter() - started) * 1000,
            )
        try:
            costs = self.cost_source.load(
                candidate.symbol, float(candidate.entry_reference_price),
                safety_margin_bps=self.policy.cost_safety_margin_bps,
            )
        except Exception:
            costs = None
        if costs is None or not (
            costs.commission_authoritative and costs.spread_authoritative
            and costs.depth_authoritative
            and (not costs.require_causal_timestamp or costs.causally_usable)
            and costs.bid is not None and costs.ask is not None
        ):
            return EntryRefinementResult(
                **common, **candle_fields, state=EntryRefinementState.FAILED.value,
                reason=COSTS_UNAVAILABLE, refinement_finished_at=now,
                refinement_decision_latency_ms=(time.perf_counter() - started) * 1000,
            )
        spread_bps = float(costs.spread_bps or 0.0)
        reference = Decimal(str(costs.ask if candidate.side.value == "LONG" else costs.bid))
        planned = Decimal(candidate.entry_reference_price)
        drift_bps = _bps(reference - planned, planned)
        total_cost = (
            costs.entry_fee_bps + costs.exit_fee_bps + costs.entry_slippage_bps
            + costs.exit_slippage_bps + spread_bps + float(costs.depth_impact_bps or 0.0)
            + costs.safety_margin_bps
        )
        economic_fields = dict(
            price_at_refinement=reference, refined_entry_reference=reference,
            price_drift_bps=drift_bps, spread_bps=spread_bps,
            dynamic_fee_bps=costs.entry_fee_bps + costs.exit_fee_bps,
        )
        if spread_bps > self.policy.maximum_spread_bps:
            return EntryRefinementResult(
                **common, **candle_fields, **economic_fields,
                state=EntryRefinementState.REJECTED_1M.value, reason=SPREAD,
                refinement_finished_at=now,
                refinement_decision_latency_ms=(time.perf_counter() - started) * 1000,
            )
        if drift_bps > self.policy.maximum_price_drift_bps:
            return EntryRefinementResult(
                **common, **candle_fields, **economic_fields,
                state=EntryRefinementState.REJECTED_1M.value, reason=PRICE_DRIFT,
                refinement_finished_at=now,
                refinement_decision_latency_ms=(time.perf_counter() - started) * 1000,
            )
        stop = Decimal(candidate.stop_price)
        target = Decimal(candidate.target_price)
        if candidate.side.value == "LONG":
            risk_bps = float((reference - stop) / reference * Decimal("10000"))
            reward_bps = float((target - reference) / reference * Decimal("10000"))
        else:
            risk_bps = float((stop - reference) / reference * Decimal("10000"))
            reward_bps = float((reference - target) / reference * Decimal("10000"))
        gross_rr = None if risk_bps <= 0 else reward_bps / risk_bps
        try:
            net_edge, _effective_risk, net_rr = compute_net_economics(
                gross_reward_bps=reward_bps, gross_risk_bps=risk_bps,
                total_cost_bps=total_cost,
            )
        except ValueError:
            net_edge, net_rr = -1.0, None
        economics = dict(
            executed_gross_rr=gross_rr, executed_net_rr=net_rr,
            executed_net_edge_bps=net_edge,
        )
        if (
            gross_rr is None or net_rr is None
            or net_edge < self.policy.minimum_net_edge_bps
            or net_rr < self.policy.required_net_rr
        ):
            return EntryRefinementResult(
                **common, **candle_fields, **economic_fields, **economics,
                state=EntryRefinementState.REJECTED_1M.value, reason=ECONOMICS,
                refinement_finished_at=now,
                refinement_decision_latency_ms=(time.perf_counter() - started) * 1000,
            )
        return EntryRefinementResult(
            **common, **candle_fields, **economic_fields, **economics,
            state=EntryRefinementState.READY_TO_ENTER.value, reason=CONFIRMED,
            refinement_finished_at=now,
            refinement_decision_latency_ms=(time.perf_counter() - started) * 1000,
        )


__all__ = (
    "CONFIRMED", "EntryRefinementMode", "EntryRefinementPolicy",
    "EntryRefinementResult", "EntryRefinementState", "MODULE_NAME",
    "ScalpingEntryRefinementService", "WINDOW_POLICY", "WINDOW_SOURCE",
    "configured_mode", "refinement_identity", "refinement_window",
)
