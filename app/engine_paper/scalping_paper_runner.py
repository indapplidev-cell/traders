"""Production-search adapter for causal 5m geometry and net-cost gating."""

from __future__ import annotations

from decimal import Decimal
import time
from typing import Protocol

from app.engine_market_data.binance_public_rest import BinancePublicRestClient
from app.engine_paper.paper_config import PaperConfig
from app.engine_paper.paper_reason_codes import PaperReasonCode as R
from app.engine_paper.paper_runner import PaperRunner
from app.engine_paper.scalping_shadow import (
    CausalTarget,
    ShadowCostInputs,
    ShadowGeometryCandidate,
    ShadowGeometryConfig,
    evaluate_scalping_shadow,
)
from app.engine_risk.risk_decision import RiskDecision
from app.engine_risk.strategy_type_contract import SCALPING_RISK_STRATEGY_TYPES
from app.engine_paper.scalping_opportunity_registry import ScalpingOpportunityRegistry


class ScalpingCostSource(Protocol):
    def load(self, symbol: str, entry: float, *, safety_margin_bps: float) -> ShadowCostInputs: ...


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
    ) -> None:
        self.client = client or BinancePublicRestClient()
        self.reference_notional = Decimal(str(reference_notional))
        self.depth_limit = int(depth_limit)
        self.maximum_age_ms = int(maximum_age_ms)
        self.entry_fee_bps = float(entry_fee_bps)
        self.exit_fee_bps = float(exit_fee_bps)
        self.entry_slippage_bps = float(entry_slippage_bps)
        self.exit_slippage_bps = float(exit_slippage_bps)
        if self.reference_notional <= 0 or self.maximum_age_ms <= 0:
            raise ValueError("Scalping cost-source bounds must be positive")
        if self.depth_limit not in {5, 10, 20, 50, 100, 500, 1000, 5000}:
            raise ValueError("unsupported bounded depth limit")

    def load(self, symbol: str, entry: float, *, safety_margin_bps: float) -> ShadowCostInputs:
        capture_started_at_ms = time.time_ns() // 1_000_000
        ticker = self.client.fetch_book_ticker(symbol)
        reference_quantity = self.reference_notional / Decimal(str(entry))
        depth = self.client.estimate_round_trip_depth_impact(
            symbol, reference_quantity, limit=self.depth_limit
        )
        captured_at_ms = time.time_ns() // 1_000_000
        return ShadowCostInputs(
            entry_fee_bps=self.entry_fee_bps,
            exit_fee_bps=self.exit_fee_bps,
            entry_slippage_bps=self.entry_slippage_bps,
            exit_slippage_bps=self.exit_slippage_bps,
            safety_margin_bps=safety_margin_bps,
            spread_bps=ticker.spread_bps,
            depth_impact_bps=depth.depth_impact_bps,
            fee_source="CONFIGURED_CONSERVATIVE_FEE_ASSUMPTION_NOT_AUTHORITATIVE",
            spread_source="BINANCE_PUBLIC_BOOK_TICKER",
            depth_impact_source=depth.source,
            spread_authoritative=True,
            depth_authoritative=True,
            bid=float(ticker.bid_price),
            ask=float(ticker.ask_price),
            buy_vwap=float(depth.buy_vwap),
            sell_vwap=float(depth.sell_vwap),
            economic_input_timestamp_ms=capture_started_at_ms,
            economic_capture_started_at_ms=capture_started_at_ms,
            decision_cutoff_timestamp_ms=captured_at_ms,
            economic_input_source="BINANCE_PUBLIC_REST_RECEIPT_BOUNDED_BOOK_AND_DEPTH",
            maximum_age_ms=self.maximum_age_ms,
            require_causal_timestamp=True,
            reference_quantity=float(reference_quantity),
            reference_notional=float(self.reference_notional),
        )


class ScalpingPaperRunner(PaperRunner):
    """Apply 5m-only causal geometry and economics before a plan becomes ready."""

    def __init__(
        self,
        *,
        runtime_parameters: object,
        cost_source: ScalpingCostSource | None = None,
        opportunity_registry: ScalpingOpportunityRegistry | None = None,
        store: object | None = None,
    ) -> None:
        minimum_rr = float(getattr(runtime_parameters, "minimum_planned_rr"))
        super().__init__(PaperConfig(
            minimum_planned_rr=minimum_rr,
            allowed_strategy_types=SCALPING_RISK_STRATEGY_TYPES,
        ), store=store)
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
            max_depth_impact_bps=float(runtime_parameters.economics_max_depth_impact_bps),
            minimum_net_edge_shadow_cohorts_bps=tuple(
                runtime_parameters.economics_minimum_net_edge_shadow_cohorts_bps
            ),
            rr_shadow_cohorts=tuple(runtime_parameters.rr_shadow_cohorts),
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
        candidate = ShadowGeometryCandidate(
            trade_profile_id="trade-5m-v1",
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
        }
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
    "ScalpingCostSource",
    "ScalpingPaperRunner",
)
