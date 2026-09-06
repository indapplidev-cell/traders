"""Production-search adapter for causal 5m geometry and net-cost gating."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from threading import Lock
import time
from typing import Protocol

from app.engine_market_data.binance_public_rest import BinancePublicRestClient
from app.engine_paper.paper_config import PaperConfig
from app.engine_paper.paper_reason_codes import PaperReasonCode as R
from app.engine_paper.paper_runner import PaperRunner
from app.engine_paper.scalping_policy_v2 import policy_provenance
from app.engine_paper.scalping_shadow import (
    CausalTarget,
    ShadowCostInputs,
    ShadowGeometryCandidate,
    ShadowGeometryConfig,
    evaluate_scalping_shadow,
)
from app.config.trade_parameters import SCALPING_V2
from app.engine_risk.risk_decision import RiskDecision
from app.engine_risk.strategy_type_contract import SCALPING_RISK_STRATEGY_TYPES
from app.engine_paper.scalping_opportunity_registry import ScalpingOpportunityRegistry


class ScalpingCostSource(Protocol):
    def load(self, symbol: str, entry: float, *, safety_margin_bps: float) -> ShadowCostInputs: ...


@dataclass(frozen=True, slots=True)
class BinanceCommissionSnapshot:
    symbol: str
    snapshot_id: str
    fetched_at: str
    commission_source: str
    maker_bps: float
    taker_bps: float
    entry_liquidity_role: str
    exit_liquidity_role: str
    bnb_discount_state: str
    special_commission_state: str
    tax_commission_state: str
    source_snapshot_id: str | None = None
    authorization_valid_until: str | None = None
    rehydration_generation: int = 0

    @property
    def entry_commission_bps(self) -> float:
        return self.maker_bps if self.entry_liquidity_role == "MAKER" else self.taker_bps

    @property
    def exit_commission_bps(self) -> float:
        return self.maker_bps if self.exit_liquidity_role == "MAKER" else self.taker_bps


@dataclass(frozen=True, slots=True)
class CommissionSnapshotLoad:
    snapshot: BinanceCommissionSnapshot | None
    status: str


def _utc(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("commission timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def read_binance_commission_snapshot(
    symbol: str, *, now: datetime | None = None
) -> CommissionSnapshotLoad:
    """Read a secret-free snapshot produced by an authenticated ops boundary."""
    raw_path = os.environ.get("TRADERS_BINANCE_COMMISSION_SNAPSHOT_PATH")
    if not raw_path:
        return CommissionSnapshotLoad(None, "SOURCE_NOT_CONFIGURED")
    try:
        payload = json.loads(Path(raw_path).read_text(encoding="utf-8"))
        row = payload["symbols"][symbol.upper()]
        snapshot_type = str(payload["snapshot_type"])
        if snapshot_type not in {
            "BINANCE_ACCOUNT_COMMISSION_SNAPSHOT",
            "USER_AUTHORIZED_STUB",
        }:
            return CommissionSnapshotLoad(None, "SNAPSHOT_TYPE_INVALID")
        observed_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        fetched = _utc(payload["fetched_at"])
        source_snapshot_id = str(payload["snapshot_id"])
        authorization_valid_until = None
        rehydration_generation = 0
        if snapshot_type == "USER_AUTHORIZED_STUB" and payload.get("rehydration_authorization"):
            authorization = payload["rehydration_authorization"]
            if authorization.get("schema") != "USER_AUTHORIZED_STUB_REHYDRATION_V1":
                return CommissionSnapshotLoad(None, "AUTHORIZATION_SCHEMA_INVALID")
            authorized_at = _utc(authorization["authorized_at"])
            valid_until = _utc(authorization["valid_until"])
            interval_seconds = int(authorization["interval_seconds"])
            if not 60 <= interval_seconds <= 3600 or not authorized_at <= observed_at <= valid_until:
                return CommissionSnapshotLoad(None, "AUTHORIZATION_EXPIRED")
            rehydration_generation = int(observed_at.timestamp()) // interval_seconds
            fetched = datetime.fromtimestamp(
                rehydration_generation * interval_seconds, tz=timezone.utc
            )
            authorization_valid_until = valid_until.isoformat().replace("+00:00", "Z")
            snapshot_id = (
                f"{source_snapshot_id}:rehydrated:{rehydration_generation}"
            )
        else:
            if observed_at - fetched > timedelta(hours=24):
                return CommissionSnapshotLoad(None, "SNAPSHOT_STALE")
            snapshot_id = source_snapshot_id
        entry_role = str(row.get("entry_liquidity_role", "TAKER")).upper()
        exit_role = str(row.get("exit_liquidity_role", "TAKER")).upper()
        if entry_role not in {"MAKER", "TAKER"} or exit_role not in {"MAKER", "TAKER"}:
            return CommissionSnapshotLoad(None, "LIQUIDITY_ROLE_INVALID")
        snapshot = BinanceCommissionSnapshot(
            symbol=symbol.upper(), snapshot_id=snapshot_id,
            fetched_at=fetched.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            commission_source=snapshot_type,
            maker_bps=float(row["maker_bps"]),
            taker_bps=float(row["taker_bps"]),
            entry_liquidity_role=entry_role,
            exit_liquidity_role=exit_role,
            bnb_discount_state=str(payload.get("bnb_discount_state", "NOT_APPLICABLE")),
            special_commission_state=str(row.get("special_commission_state", "NOT_APPLICABLE")),
            tax_commission_state=str(row.get("tax_commission_state", "NOT_APPLICABLE")),
            source_snapshot_id=source_snapshot_id,
            authorization_valid_until=authorization_valid_until,
            rehydration_generation=rehydration_generation,
        )
        return CommissionSnapshotLoad(snapshot, "READY")
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return CommissionSnapshotLoad(None, "SNAPSHOT_UNREADABLE")


def load_binance_commission_snapshot(symbol: str) -> BinanceCommissionSnapshot | None:
    return read_binance_commission_snapshot(symbol).snapshot


class BinancePublicScalpingCostSource:
    """Two bounded public requests; the diagnostic quantity grants no authority."""

    def __init__(
        self,
        client: BinancePublicRestClient | None = None,
        *,
        reference_notional: float = 100.0,
        depth_limit: int = 100,
        maximum_age_ms: int = 5_000,
        entry_fee_bps: float = 10.0,
        exit_fee_bps: float = 10.0,
        entry_slippage_bps: float = 2.0,
        exit_slippage_bps: float = 2.0,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.client = client or BinancePublicRestClient()
        self.reference_notional = Decimal(str(reference_notional))
        self.depth_limit = int(depth_limit)
        self.maximum_age_ms = int(maximum_age_ms)
        self.entry_fee_bps = float(entry_fee_bps)
        self.exit_fee_bps = float(exit_fee_bps)
        self.entry_slippage_bps = float(entry_slippage_bps)
        self.exit_slippage_bps = float(exit_slippage_bps)
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self._recovery_lock = Lock()
        self._connection_generation = 0
        self._last_signature: tuple[str, str, str, str] | None = None
        self._last_success_at: str | None = None
        self._last_failure_at: str | None = None
        self._recovered_at: str | None = None
        self._rehydration_started_at: datetime | None = None
        self._rehydration_duration_ms: float | None = None
        if self.reference_notional <= 0 or self.maximum_age_ms <= 0:
            raise ValueError("Scalping cost-source bounds must be positive")
        if self.depth_limit not in {5, 10, 20, 50, 100, 500, 1000, 5000}:
            raise ValueError("unsupported bounded depth limit")

    def load(self, symbol: str, entry: float, *, safety_margin_bps: float) -> ShadowCostInputs:
        capture_started_at_ms = time.time_ns() // 1_000_000
        reference_quantity = self.reference_notional / Decimal(str(entry))
        ticker = None
        depth = None
        ticker_status = "READY"
        depth_status = "READY"
        try:
            ticker = self.client.fetch_book_ticker(symbol)
        except Exception:
            ticker_status = "BOOK_TICKER_NOT_READY"
        try:
            depth = self.client.estimate_round_trip_depth_impact(
                symbol, reference_quantity, limit=self.depth_limit
            )
        except Exception:
            depth_status = "DEPTH_NOT_READY"
        captured_at_ms = time.time_ns() // 1_000_000
        observed_at = self.clock().astimezone(timezone.utc)
        commission_load = read_binance_commission_snapshot(symbol, now=observed_at)
        commission = commission_load.snapshot
        market_status = (
            "READY" if ticker_status == depth_status == "READY" else "NOT_READY"
        )
        book_status = (
            "READY" if ticker_status == depth_status == "READY"
            else ticker_status if ticker_status != "READY" else depth_status
        )
        cost_status = (
            "READY" if market_status == "READY" and commission is not None
            else "NOT_READY"
        )
        telemetry = self._observe_recovery(
            observed_at,
            market_status=market_status,
            fee_status=commission_load.status,
            book_status=book_status,
            cost_status=cost_status,
        )
        return ShadowCostInputs(
            entry_fee_bps=(commission.entry_commission_bps if commission else self.entry_fee_bps),
            exit_fee_bps=(commission.exit_commission_bps if commission else self.exit_fee_bps),
            entry_slippage_bps=self.entry_slippage_bps,
            exit_slippage_bps=self.exit_slippage_bps,
            safety_margin_bps=safety_margin_bps,
            spread_bps=(None if ticker is None else ticker.spread_bps),
            depth_impact_bps=(None if depth is None else depth.depth_impact_bps),
            fee_source=(commission.commission_source if commission else "CONFIGURED_CONSERVATIVE_FEE_ASSUMPTION_NOT_AUTHORITATIVE"),
            commission_authoritative=commission is not None,
            commission_symbol=None if commission is None else commission.symbol,
            commission_snapshot_id=None if commission is None else commission.snapshot_id,
            commission_fetched_at=None if commission is None else commission.fetched_at,
            entry_liquidity_role=("TAKER" if commission is None else commission.entry_liquidity_role),
            exit_liquidity_role=("TAKER" if commission is None else commission.exit_liquidity_role),
            bnb_discount_state=("NOT_APPLICABLE" if commission is None else commission.bnb_discount_state),
            special_commission_state=("NOT_APPLICABLE" if commission is None else commission.special_commission_state),
            tax_commission_state=("NOT_APPLICABLE" if commission is None else commission.tax_commission_state),
            spread_source="BINANCE_PUBLIC_BOOK_TICKER",
            depth_impact_source=("BINANCE_PUBLIC_MARKET_DATA_DEPTH" if depth is None else depth.source),
            spread_authoritative=ticker is not None,
            depth_authoritative=depth is not None,
            bid=(None if ticker is None else float(ticker.bid_price)),
            ask=(None if ticker is None else float(ticker.ask_price)),
            buy_vwap=(None if depth is None else float(depth.buy_vwap)),
            sell_vwap=(None if depth is None else float(depth.sell_vwap)),
            economic_input_timestamp_ms=capture_started_at_ms,
            economic_capture_started_at_ms=capture_started_at_ms,
            decision_cutoff_timestamp_ms=captured_at_ms,
            economic_input_source="BINANCE_PUBLIC_REST_RECEIPT_BOUNDED_BOOK_AND_DEPTH",
            maximum_age_ms=self.maximum_age_ms,
            require_causal_timestamp=True,
            reference_quantity=float(reference_quantity),
            reference_notional=float(self.reference_notional),
            connection_generation=telemetry["connection_generation"],
            market_source_status=market_status,
            fee_source_status=commission_load.status,
            book_source_status=book_status,
            cost_model_status=cost_status,
            last_success_at=telemetry["last_success_at"],
            last_failure_at=telemetry["last_failure_at"],
            recovered_at=telemetry["recovered_at"],
            rehydration_duration_ms=telemetry["rehydration_duration_ms"],
            fee_watermark=(None if commission is None else commission.snapshot_id),
            fee_authorization_valid_until=(
                None if commission is None else commission.authorization_valid_until
            ),
        )

    def _observe_recovery(
        self,
        observed_at: datetime,
        *,
        market_status: str,
        fee_status: str,
        book_status: str,
        cost_status: str,
    ) -> dict[str, object]:
        timestamp = observed_at.isoformat().replace("+00:00", "Z")
        signature = (market_status, fee_status, book_status, cost_status)
        with self._recovery_lock:
            if signature != self._last_signature:
                self._connection_generation += 1
                self._last_signature = signature
            if cost_status == "READY":
                self._last_success_at = timestamp
                if self._rehydration_started_at is not None:
                    self._recovered_at = timestamp
                    self._rehydration_duration_ms = max(
                        0.0,
                        (observed_at - self._rehydration_started_at).total_seconds() * 1000.0,
                    )
                    self._rehydration_started_at = None
            else:
                self._last_failure_at = timestamp
                if self._rehydration_started_at is None:
                    self._rehydration_started_at = observed_at
            return {
                "connection_generation": self._connection_generation,
                "last_success_at": self._last_success_at,
                "last_failure_at": self._last_failure_at,
                "recovered_at": self._recovered_at,
                "rehydration_duration_ms": self._rehydration_duration_ms,
            }


class ScalpingPaperRunner(PaperRunner):
    """Apply 5m-only causal geometry and economics before a plan becomes ready."""

    def __init__(
        self,
        *,
        runtime_parameters: object,
        cost_source: ScalpingCostSource | None = None,
        opportunity_registry: ScalpingOpportunityRegistry | None = None,
        store: object | None = None,
        clock_ms: Callable[[], int] | None = None,
    ) -> None:
        profile_id = str(getattr(runtime_parameters, "profile_id", ""))
        if profile_id != "trade-5m-v2":
            raise ValueError("Scalping PAPER execution requires trade-5m-v2")
        minimum_rr = float(getattr(runtime_parameters, "minimum_planned_rr"))
        super().__init__(PaperConfig(
            minimum_planned_rr=minimum_rr,
            allowed_strategy_types=SCALPING_RISK_STRATEGY_TYPES,
        ), store=store, clock_ms=clock_ms)
        self.runtime_parameters = runtime_parameters
        self.opportunity_registry = opportunity_registry or ScalpingOpportunityRegistry()
        self.cost_source = cost_source or BinancePublicScalpingCostSource(
            reference_notional=float(runtime_parameters.vwap_reference_notional),
            depth_limit=int(runtime_parameters.bounded_book_depth_limit),
            maximum_age_ms=int(runtime_parameters.microstructure_max_age_ms),
            entry_fee_bps=float(runtime_parameters.economics_entry_fee_bps),
            exit_fee_bps=float(runtime_parameters.economics_exit_fee_bps),
            entry_slippage_bps=float(runtime_parameters.economics_entry_slippage_bps),
            exit_slippage_bps=float(runtime_parameters.economics_exit_slippage_bps),
        )
        self.geometry_config = ShadowGeometryConfig(
            atr_buffer_multiplier=float(runtime_parameters.geometry_atr_buffer_multiplier),
            stop_envelope_bps=float(runtime_parameters.geometry_stop_envelope_bps),
            minimum_target_diagnostic_bps=float(
                runtime_parameters.geometry_minimum_target_bps
            ),
            minimum_positive_edge_bps=float(runtime_parameters.economics_minimum_net_edge_bps),
            production_rr_floor=minimum_rr,
            minimum_empirical_samples=SCALPING_V2.economics.bucket_min_sample,
            minimum_positive_ev_r=SCALPING_V2.economics.min_positive_ev_r,
            minimum_ev_reserve_r=SCALPING_V2.economics.min_ev_reserve_r,
            max_depth_impact_bps=float(runtime_parameters.economics_max_depth_impact_bps),
            minimum_net_edge_shadow_cohorts_bps=tuple(
                runtime_parameters.economics_minimum_net_edge_shadow_cohorts_bps
            ),
            rr_shadow_cohorts=tuple(runtime_parameters.rr_shadow_cohorts),
            profile_id=profile_id,
        )

    def _process(self, source: RiskDecision):
        gate = self.policy.evaluate(source)
        if not gate.proceed:
            return super()._process(source)

        context = self.level_builder_context(source)
        entry = context.confirmation_close or context.reference_close or context.current_closed_candle_close
        if entry is None:
            return super()._process(source)

        invalidation = (
            context.causal_support_level or context.causal_invalidation_level
            if source.direction_hint == "BULLISH"
            else context.causal_resistance_level or context.causal_invalidation_level
        )
        is_v2 = str(getattr(self.runtime_parameters, "profile_id", "")) == "trade-5m-v2"
        if is_v2 and invalidation is None and context.atr_value:
            direction_sign = 1.0 if source.direction_hint == "BULLISH" else -1.0
            invalidation = float(entry) - direction_sign * 0.5 * float(context.atr_value)
        targets: list[CausalTarget] = []
        for raw in context.causal_target_candidates:
            price = raw.get("price")
            source_type = str(raw.get("source_type") or "").upper()
            timeframe = str(raw.get("timeframe") or "").lower() or None
            if price is None or source_type not in {"LOCAL_5M", "STRUCTURAL", "15M", "1H"}:
                continue
            reachability_atr = raw.get("reachability_atr")
            achievable = bool(raw.get("achievable", True))
            if source_type == "1H":
                try:
                    achievable = achievable and float(reachability_atr) > 0 and (
                        abs(float(price) - float(entry)) <= float(reachability_atr)
                    )
                except (TypeError, ValueError):
                    achievable = False
            targets.append(CausalTarget(
                float(price), source_type, int(raw.get("known_at_ms") or source.closed_until_ms),
                validated=bool(raw.get("validated", False)),
                relevant=bool(raw.get("still_relevant", True)),
                achievable=achievable,
                timeframe=timeframe,
                source_detail=(
                    str(raw.get("source_detail"))
                    if raw.get("source_detail") is not None else None
                ),
            ))
        if not targets and context.causal_target_level is not None:
            targets.append(CausalTarget(
                context.causal_target_level, "LOCAL_5M", source.closed_until_ms,
                timeframe="5m", source_detail="legacy_nearest_opposite_level",
            ))
        if is_v2 and context.atr_value:
            direction_sign = 1.0 if source.direction_hint == "BULLISH" else -1.0
            targets.append(CausalTarget(
                float(entry) + direction_sign * 2.0 * float(context.atr_value),
                "LOCAL_RANGE_BOUNDARY", source.closed_until_ms,
                timeframe="5m", source_detail="scalping_v2_two_atr_short_target",
            ))
        candidate = ShadowGeometryCandidate(
            trade_profile_id=str(getattr(self.runtime_parameters, "profile_id", "")),
            symbol=source.symbol,
            boundary_ms=source.closed_until_ms,
            direction=source.direction_hint,
            entry=entry,
            causal_invalidation=invalidation,
            atr=context.atr_value,
            targets=tuple(targets),
            # The setup detector identity is stable across adjacent boundaries.
            # Legacy fixtures without it retain the prior family-level fallback.
            setup_identity=context.opportunity_id or context.setup_type or source.source_strategy_type,
        )
        unavailable_costs = ShadowCostInputs(
            entry_fee_bps=float(self.runtime_parameters.economics_entry_fee_bps),
            exit_fee_bps=float(self.runtime_parameters.economics_exit_fee_bps),
            entry_slippage_bps=float(self.runtime_parameters.economics_entry_slippage_bps),
            exit_slippage_bps=float(self.runtime_parameters.economics_exit_slippage_bps),
            safety_margin_bps=float(
                getattr(self.runtime_parameters, "cost_safety_margin_bps")
            ),
            fee_source="CONFIGURED_CONSERVATIVE_FEE_ASSUMPTION_NOT_AUTHORITATIVE",
        )
        diagnostic = evaluate_scalping_shadow(
            candidate, unavailable_costs, self.geometry_config
        )
        if diagnostic.rejection_stage == "NET_COST_GATE":
            diagnostic = evaluate_scalping_shadow(
                candidate, self._costs(candidate), self.geometry_config
            )
        diagnostic_payload = diagnostic.to_dict()
        paper_context = {
            "plan_policy_version": self.config.plan_policy_version,
            "causal_primitives": context.to_dict(),
            "scalping_geometry_diagnostics": diagnostic_payload,
            "cost_data_query_bound": 2,
            "economic_gate_enabled": True,
            "production_rr_floor": self.geometry_config.production_rr_floor,
            "minimum_positive_edge_bps": self.geometry_config.minimum_positive_edge_bps,
            "minimum_actionable_target_bps": diagnostic.minimum_actionable_target_bps,
            "target_policy_id": getattr(self.runtime_parameters, "target_policy_id", None),
            "rr_policy_version": diagnostic.rr_policy_version,
            "expected_value_bps": diagnostic.expected_value_bps,
            "expectancy_gate_reason": diagnostic.expectancy_gate_reason,
        }
        if is_v2:
            paper_context["scalping_policy_provenance"] = policy_provenance()
        common = dict(
            context=context,
            entry=diagnostic.entry,
            invalidation=diagnostic.causal_invalidation,
            stop=diagnostic.final_stop,
            target=diagnostic.causal_target,
            planned_rr=diagnostic.gross_rr,
            entry_source="confirmation_or_reference_closed_candle",
            invalidation_source="causal_5m_invalidation",
            stop_source="causal_invalidation_plus_profile_atr_buffer",
            target_source=diagnostic.target_source_type,
        )
        unique_opportunity = True
        if diagnostic.valid_plan:
            unique_opportunity = self.opportunity_registry.observe_and_claim(
                diagnostic.opportunity_id,
                reentry_enabled=bool(
                    getattr(self.runtime_parameters, "opportunity_reentry_enabled", False)
                ),
            )
            paper_context["opportunity_observation"] = (
                "UNIQUE_CAUSAL_OPPORTUNITY" if unique_opportunity
                else "REPEAT_CAUSAL_OPPORTUNITY"
            )
            paper_context["opportunity_observation_count"] = (
                self.opportunity_registry.observation_count(diagnostic.opportunity_id)
            )
        if diagnostic.valid_plan and unique_opportunity:
            plan = self._base_plan(
                source,
                status="PAPER_PLAN_READY",
                quality=gate.quality,
                reasons=[
                    R.PAPER_PLAN_READY_VALID_LEVELS.value,
                    R.PAPER_PLAN_READY_MIN_RR_MET.value,
                ],
                **common,
            )
        else:
            reason = str(
                R.SCALP_REJECT_DUPLICATE_OPPORTUNITY.value
                if diagnostic.valid_plan and not unique_opportunity
                else diagnostic.rejection_reason or R.PAPER_ERROR_PROCESSING_FAILED.value
            )
            missing = reason.startswith("PAPER_NO_PLAN_")
            plan = self._base_plan(
                source,
                status="NO_PLAN" if missing else "REJECT",
                quality="UNKNOWN" if missing else "REJECTED",
                reasons=[reason],
                rejection=[] if missing else [reason],
                **common,
            )
        mutable_context = dict(plan.paper_context)
        mutable_context.update(paper_context)
        object.__setattr__(plan, "paper_context", mutable_context)
        return plan

    @staticmethod
    def level_builder_context(source: RiskDecision):
        from app.engine_paper.paper_context import PaperContext

        return PaperContext.from_risk_decision(source)

    def _costs(self, candidate: ShadowGeometryCandidate) -> ShadowCostInputs:
        try:
            return self.cost_source.load(
                candidate.symbol,
                candidate.entry,
                safety_margin_bps=float(
                    getattr(self.runtime_parameters, "cost_safety_margin_bps")
                ),
            )
        except Exception:
            return ShadowCostInputs(
                entry_fee_bps=float(self.runtime_parameters.economics_entry_fee_bps),
                exit_fee_bps=float(self.runtime_parameters.economics_exit_fee_bps),
                entry_slippage_bps=float(self.runtime_parameters.economics_entry_slippage_bps),
                exit_slippage_bps=float(self.runtime_parameters.economics_exit_slippage_bps),
                safety_margin_bps=float(
                    getattr(self.runtime_parameters, "cost_safety_margin_bps")
                ),
                fee_source="CONFIGURED_CONSERVATIVE_FEE_ASSUMPTION_NOT_AUTHORITATIVE",
                spread_source=None,
                depth_impact_source=None,
                spread_authoritative=False,
                depth_authoritative=False,
            )


__all__ = (
    "BinancePublicScalpingCostSource",
    "CommissionSnapshotLoad",
    "ScalpingCostSource",
    "ScalpingPaperRunner",
    "read_binance_commission_snapshot",
)
