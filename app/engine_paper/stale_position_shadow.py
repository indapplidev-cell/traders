"""Config-driven, non-mutating stale-position lifecycle diagnostics for PAPER."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from decimal import Decimal
import json
import os
from pathlib import Path
import tempfile
from typing import Callable, Iterable, Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config.trade_parameters import (
    SCALPING_V2, TRADE_PARAMETERS, StalePositionPolicyParameters,
)
from app.db.paper_models import ScalpingStalePositionShadowRecord
from app.engine_paper.fill_simulator import PaperFillCandle
from app.engine_paper.scalping_shadow import ShadowCostInputs
from app.engine_position.paper_models import PaperPosition


POLICY_VERSION = "scalping-stale-position-shadow-v1"
STATUS_PATH_ENV = "TRADERS_STALE_POSITION_SHADOW_STATUS_PATH"
DEFAULT_STATUS_PATH = Path("/run/traders-control/stale-position-shadow.json")

TIME_STOP_SHADOW_NO_PROGRESS = "TIME_STOP_SHADOW_NO_PROGRESS"
TIME_STOP_SHADOW_EV_DECAY = "TIME_STOP_SHADOW_EV_DECAY"
TIME_STOP_SHADOW_HARD_LIMIT = "TIME_STOP_SHADOW_HARD_LIMIT"
TIME_STOP_SHADOW_BREAK_EVEN_PROTECT = "TIME_STOP_SHADOW_BREAK_EVEN_PROTECT"
TIME_STOP_SHADOW_EXTENSION_ALLOWED = "TIME_STOP_SHADOW_EXTENSION_ALLOWED"


class CurrentCostSource(Protocol):
    def load(self, symbol: str, entry: float, *, safety_margin_bps: float) -> ShadowCostInputs: ...


@dataclass(frozen=True, slots=True)
class StalePositionInputs:
    position_id: str
    symbol: str
    side: str
    opened_at: datetime
    evaluation_time: datetime
    evaluation_closed_until_ms: int
    entry_price: Decimal
    current_price: Decimal
    quantity: Decimal
    stop_price: Decimal
    target_price: Decimal
    entry_fee_incurred: Decimal
    exit_commission_bps: Decimal
    spread_bps: Decimal
    slippage_bps: Decimal
    adverse_exit_reserve_bps: Decimal
    highs: tuple[Decimal, ...]
    lows: tuple[Decimal, ...]
    setup_valid: bool | None
    momentum_valid: bool | None
    remaining_ev_r: Decimal | None = None
    extension_count: int = 0
    commission_provenance: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class StalePositionShadowDecision:
    position_id: str
    symbol: str
    side: str
    mode: str
    policy_version: str
    config_hash: str
    evaluated_at: datetime
    opened_at: datetime
    evaluation_closed_until_ms: int
    current_price: Decimal
    holding_seconds: int
    soft_timeout_reached: bool
    hard_timeout_reached: bool
    target_progress: Decimal
    mfe_bps: Decimal
    mae_bps: Decimal
    current_gross_pnl: Decimal
    estimated_net_exit_pnl: Decimal
    remaining_target_distance: Decimal
    remaining_ev_r: Decimal | None
    setup_valid: bool | None
    momentum_valid: bool | None
    entry_fee_incurred: Decimal
    expected_exit_commission: Decimal
    spread_cost: Decimal
    slippage_cost: Decimal
    adverse_exit_reserve: Decimal
    net_break_even_price: Decimal
    break_even_activation_reason: str | None
    extension_count: int
    shadow_decision: str
    decision_reason: str | None
    shadow_exit_time: datetime | None
    shadow_exit_price: Decimal | None
    shadow_exit_reason: str | None
    shadow_gross_pnl: Decimal | None
    shadow_fees: Decimal | None
    shadow_net_pnl: Decimal | None
    position_capacity_seconds_consumed: int
    later_rejected_candidates: int | None
    provenance: dict[str, object]


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def evaluate_stale_position_shadow(
    value: StalePositionInputs,
    *,
    policy: StalePositionPolicyParameters | None = None,
    config_hash: str | None = None,
) -> StalePositionShadowDecision:
    policy = policy or SCALPING_V2.exit_policy.stale_position
    selected_config_hash = config_hash or TRADE_PARAMETERS.config_hash
    evaluation = value.evaluation_time.astimezone(timezone.utc)
    opened = value.opened_at.astimezone(timezone.utc)
    holding = max(0, int((evaluation - opened).total_seconds()))
    long = value.side == "LONG"
    direction = Decimal("1") if long else Decimal("-1")
    target_distance = abs(value.target_price - value.entry_price)
    favorable_now = direction * (value.current_price - value.entry_price)
    target_progress = favorable_now / target_distance if target_distance else Decimal("0")
    favorable_extreme = (
        max(value.highs, default=value.current_price)
        if long else min(value.lows, default=value.current_price)
    )
    adverse_extreme = (
        min(value.lows, default=value.current_price)
        if long else max(value.highs, default=value.current_price)
    )
    mfe_bps = max(Decimal("0"), direction * (favorable_extreme - value.entry_price) / value.entry_price * 10000)
    mae_bps = max(Decimal("0"), -direction * (adverse_extreme - value.entry_price) / value.entry_price * 10000)
    gross = direction * (value.current_price - value.entry_price) * value.quantity
    notional = value.current_price * value.quantity
    expected_exit_commission = notional * value.exit_commission_bps / 10000
    spread_cost = notional * value.spread_bps / 10000
    slippage_cost = notional * value.slippage_bps / 10000
    adverse_reserve = notional * value.adverse_exit_reserve_bps / 10000
    total_costs = (
        value.entry_fee_incurred + expected_exit_commission + spread_cost
        + slippage_cost + adverse_reserve
    )
    net = gross - total_costs
    exit_rate = (
        value.exit_commission_bps + value.spread_bps + value.slippage_bps
        + value.adverse_exit_reserve_bps
    ) / 10000
    per_unit_entry_fee = value.entry_fee_incurred / value.quantity
    net_break_even = (
        (value.entry_price + per_unit_entry_fee) / (Decimal("1") - exit_rate)
        if long else
        (value.entry_price - per_unit_entry_fee) / (Decimal("1") + exit_rate)
    )
    remaining_target = max(Decimal("0"), direction * (value.target_price - value.current_price))
    soft = holding >= policy.soft_timeout_seconds
    hard = holding >= policy.hard_timeout_seconds
    break_even_active = (
        policy.net_break_even_protection_enabled
        and target_progress >= _d(policy.break_even_activation_target_progress)
    )
    break_even_reason = "TARGET_PROGRESS_THRESHOLD_REACHED" if break_even_active else None

    decision = "MONITORING"
    reason = None
    extension_count = value.extension_count
    if hard:
        decision, reason = "HYPOTHETICAL_EXIT", TIME_STOP_SHADOW_HARD_LIMIT
    elif break_even_active and net <= 0:
        decision, reason = "HYPOTHETICAL_EXIT", TIME_STOP_SHADOW_BREAK_EVEN_PROTECT
    elif soft:
        if value.extension_count > 0:
            decision, reason = "EXTENSION_ACTIVE", TIME_STOP_SHADOW_EXTENSION_ALLOWED
        else:
            progress_ok = target_progress >= _d(policy.min_target_progress_at_soft_timeout)
            mfe_ok = (
                policy.min_mfe_bps_at_soft_timeout is None
                or mfe_bps >= _d(policy.min_mfe_bps_at_soft_timeout)
            )
            ev_ok = (
                value.remaining_ev_r is None
                or value.remaining_ev_r >= _d(policy.min_remaining_ev_r_at_soft_timeout)
            )
            if not (progress_ok and mfe_ok and ev_ok):
                extension_ok = (
                    policy.extension_allowed
                    and value.extension_count < policy.max_extensions
                    and (
                        not policy.extension_requires_positive_net_exit_pnl or net > 0
                    )
                    and (
                        not policy.extension_requires_setup_valid or value.setup_valid is True
                    )
                    and (
                        not policy.extension_requires_momentum_valid or value.momentum_valid is True
                    )
                )
                if extension_ok:
                    decision, reason = "EXTENSION_ALLOWED", TIME_STOP_SHADOW_EXTENSION_ALLOWED
                    extension_count += 1
                else:
                    decision = "HYPOTHETICAL_EXIT"
                    reason = (
                        TIME_STOP_SHADOW_EV_DECAY
                        if value.remaining_ev_r is not None and not ev_ok
                        else TIME_STOP_SHADOW_NO_PROGRESS
                    )

    hypothetical = decision == "HYPOTHETICAL_EXIT"
    provenance = {
        "commission": dict(value.commission_provenance or {}),
        "use_current_exit_costs": policy.use_current_exit_costs,
        "entry_fee_source": "PERSISTED_INCURRED_ENTRY_FEE",
        "market_input": "CLOSED_1M_AND_CURRENT_PUBLIC_BOOK",
    }
    return StalePositionShadowDecision(
        position_id=value.position_id, symbol=value.symbol, side=value.side,
        mode=policy.mode, policy_version=POLICY_VERSION,
        config_hash=selected_config_hash, evaluated_at=evaluation,
        opened_at=opened, evaluation_closed_until_ms=value.evaluation_closed_until_ms,
        current_price=value.current_price, holding_seconds=holding,
        soft_timeout_reached=soft, hard_timeout_reached=hard,
        target_progress=target_progress, mfe_bps=mfe_bps, mae_bps=mae_bps,
        current_gross_pnl=gross, estimated_net_exit_pnl=net,
        remaining_target_distance=remaining_target, remaining_ev_r=value.remaining_ev_r,
        setup_valid=value.setup_valid, momentum_valid=value.momentum_valid,
        entry_fee_incurred=value.entry_fee_incurred,
        expected_exit_commission=expected_exit_commission,
        spread_cost=spread_cost, slippage_cost=slippage_cost,
        adverse_exit_reserve=adverse_reserve, net_break_even_price=net_break_even,
        break_even_activation_reason=break_even_reason,
        extension_count=extension_count, shadow_decision=decision,
        decision_reason=reason,
        shadow_exit_time=evaluation if hypothetical else None,
        shadow_exit_price=value.current_price if hypothetical else None,
        shadow_exit_reason=reason if hypothetical else None,
        shadow_gross_pnl=gross if hypothetical else None,
        shadow_fees=total_costs if hypothetical else None,
        shadow_net_pnl=net if hypothetical else None,
        position_capacity_seconds_consumed=holding,
        later_rejected_candidates=None, provenance=provenance,
    )


def _json_value(value: object) -> object:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    return value


class PostgresStalePositionShadowService:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        cost_source: CurrentCostSource,
        *,
        status_path: Path | None = None,
    ) -> None:
        self._sessions = session_factory
        self._cost_source = cost_source
        self._status_path = status_path or Path(os.environ.get(STATUS_PATH_ENV, DEFAULT_STATUS_PATH))

    def _extension_count(self, position_id: str) -> int:
        with self._sessions() as session:
            return int(session.scalar(select(func.max(
                ScalpingStalePositionShadowRecord.extension_count
            )).where(
                ScalpingStalePositionShadowRecord.position_id == position_id
            )) or 0)

    def evaluate_and_persist(
        self, position: PaperPosition, candles: Iterable[PaperFillCandle]
    ) -> StalePositionShadowDecision | None:
        ordered = tuple(sorted(candles, key=lambda item: item.open_time_ms))
        opened_ms = int(position.opened_at.timestamp() * 1000)
        causal = tuple(item for item in ordered if item.close_boundary_ms > opened_ms)
        if not causal:
            return None
        latest = causal[-1]
        with self._sessions() as session:
            existing = session.get(
                ScalpingStalePositionShadowRecord,
                (position.position_id, latest.close_boundary_ms),
            )
            if existing is not None:
                return StalePositionShadowDecision(**{
                    field.name: getattr(existing, field.name)
                    for field in fields(StalePositionShadowDecision)
                })
        costs = self._cost_source.load(
            position.symbol, float(latest.close_price), safety_margin_bps=0.0
        )
        if not costs.commission_authoritative or not costs.causally_usable:
            return None
        closes = tuple(item.close_price for item in causal)
        momentum = None
        if len(closes) >= 2:
            momentum = (
                closes[-1] >= closes[-2]
                if position.side.value == "LONG" else closes[-1] <= closes[-2]
            )
        setup_valid = (
            latest.close_price > position.stop_price
            if position.side.value == "LONG" else latest.close_price < position.stop_price
        )
        decision = evaluate_stale_position_shadow(StalePositionInputs(
            position_id=position.position_id, symbol=position.symbol,
            side=position.side.value, opened_at=position.opened_at,
            evaluation_time=datetime.fromtimestamp(latest.close_boundary_ms / 1000, tz=timezone.utc),
            evaluation_closed_until_ms=latest.close_boundary_ms,
            entry_price=position.average_entry_price,
            current_price=latest.close_price, quantity=position.remaining_quantity,
            stop_price=position.stop_price, target_price=position.target_price,
            entry_fee_incurred=position.entry_fees,
            exit_commission_bps=_d(costs.exit_fee_bps),
            spread_bps=_d(costs.spread_bps),
            slippage_bps=_d(costs.exit_slippage_bps),
            adverse_exit_reserve_bps=_d(costs.adverse_fill_reserve_bps),
            highs=tuple(item.high_price for item in causal),
            lows=tuple(item.low_price for item in causal),
            setup_valid=setup_valid, momentum_valid=momentum,
            extension_count=self._extension_count(position.position_id),
            commission_provenance=costs.commission_provenance,
        ))
        values = asdict(decision)
        with self._sessions() as session:
            session.merge(ScalpingStalePositionShadowRecord(**values, created_at=decision.evaluated_at))
            session.commit()
        self._write_status(decision)
        return decision

    def _write_status(self, decision: StalePositionShadowDecision) -> None:
        payload = stale_position_capability()
        payload["latest"] = _json_value(asdict(decision))
        self._status_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=self._status_path.parent,
            prefix=".stale-shadow-", suffix=".json", delete=False,
        ) as handle:
            json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            temporary = Path(handle.name)
        try:
            os.replace(temporary, self._status_path)
        finally:
            temporary.unlink(missing_ok=True)


def stale_position_capability() -> dict[str, object]:
    policy = SCALPING_V2.exit_policy.stale_position
    return {
        "capability": "STALE_POSITION_SHADOW",
        "runtime_active": bool(policy.enabled),
        "mode": policy.mode,
        "policy_version": POLICY_VERSION,
        "config_hash": TRADE_PARAMETERS.config_hash,
        "policy": policy.model_dump(mode="json"),
        "latest": None,
    }


def stale_position_runtime_projection(path: Path | None = None) -> dict[str, object]:
    capability = stale_position_capability()
    selected = path or Path(os.environ.get(STATUS_PATH_ENV, DEFAULT_STATUS_PATH))
    try:
        payload = json.loads(selected.read_text(encoding="utf-8"))
        if (
            payload.get("capability") == capability["capability"]
            and payload.get("mode") == "SHADOW"
            and payload.get("config_hash") == capability["config_hash"]
        ):
            capability["latest"] = payload.get("latest")
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass
    return capability


__all__ = (
    "POLICY_VERSION", "PostgresStalePositionShadowService", "StalePositionInputs",
    "StalePositionShadowDecision", "evaluate_stale_position_shadow",
    "stale_position_capability", "stale_position_runtime_projection",
)
