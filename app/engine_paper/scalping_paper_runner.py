"""Production-search adapter for causal 5m geometry and net-cost gating."""

from __future__ import annotations

from decimal import Decimal
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


class ScalpingCostSource(Protocol):
    def load(self, symbol: str, entry: float, *, safety_margin_bps: float) -> ShadowCostInputs: ...


class BinancePublicScalpingCostSource:
    """Two bounded public requests; the diagnostic quantity grants no authority."""

    DIAGNOSTIC_QUOTE_NOTIONAL = Decimal("100")
    DEPTH_LIMIT = 100

    def __init__(self, client: BinancePublicRestClient | None = None) -> None:
        self.client = client or BinancePublicRestClient()

    def load(self, symbol: str, entry: float, *, safety_margin_bps: float) -> ShadowCostInputs:
        ticker = self.client.fetch_book_ticker(symbol)
        reference_quantity = self.DIAGNOSTIC_QUOTE_NOTIONAL / Decimal(str(entry))
        depth = self.client.estimate_round_trip_depth_impact(
            symbol, reference_quantity, limit=self.DEPTH_LIMIT
        )
        return ShadowCostInputs(
            safety_margin_bps=safety_margin_bps,
            spread_bps=ticker.spread_bps,
            depth_impact_bps=depth.depth_impact_bps,
            fee_source="CONFIGURED_CONSERVATIVE_FEE_ASSUMPTION_NOT_AUTHORITATIVE",
            spread_source="BINANCE_PUBLIC_BOOK_TICKER",
            depth_impact_source=depth.source,
            spread_authoritative=True,
            depth_authoritative=True,
        )


class ScalpingPaperRunner(PaperRunner):
    """Apply 5m-only causal geometry and economics before a plan becomes ready."""

    def __init__(
        self,
        *,
        runtime_parameters: object,
        cost_source: ScalpingCostSource | None = None,
        store: object | None = None,
    ) -> None:
        minimum_rr = float(getattr(runtime_parameters, "minimum_planned_rr"))
        super().__init__(PaperConfig(minimum_planned_rr=minimum_rr), store=store)
        self.runtime_parameters = runtime_parameters
        self.cost_source = cost_source or BinancePublicScalpingCostSource()
        self.geometry_config = ShadowGeometryConfig(
            atr_buffer_multiplier=0.25,
            stop_envelope_bps=80.0,
            minimum_target_diagnostic_bps=45.0,
            minimum_positive_edge_bps=1.0,
            production_rr_floor=minimum_rr,
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
        if context.causal_target_level is not None:
            targets.append(CausalTarget(
                context.causal_target_level, "LOCAL_5M", source.closed_until_ms
            ))
        if (
            context.nearest_opposite_level is not None
            and context.nearest_opposite_level != context.causal_target_level
        ):
            targets.append(CausalTarget(
                context.nearest_opposite_level, "STRUCTURAL", source.closed_until_ms
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
            setup_identity=context.setup_type or source.source_strategy_type,
        )
        unavailable_costs = ShadowCostInputs(
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
        if diagnostic.valid_plan:
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
            reason = str(diagnostic.rejection_reason or R.PAPER_ERROR_PROCESSING_FAILED.value)
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
