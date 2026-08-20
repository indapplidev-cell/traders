"""Causal DB snapshot construction and safe module coordination."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any

from app.engine_analysis.analysis_snapshot import AnalysisSnapshotStatus
from app.engine_analysis.analysis_snapshot_store import AnalysisSnapshotStore
from app.engine_analysis.market_data_adapter import MarketDataAdapter
from app.engine_analysis.online_config import OnlineAnalysisConfig
from app.engine_analysis.online_runner import OnlineAnalysisRunner
from app.engine_market_data.gap_detector import find_missing_open_times
from app.engine_market_data.market_data_snapshot import MarketDataSnapshot
from app.engine_market_data.timeframe import timeframe_to_milliseconds
from app.engine_orchestrator.orchestrator_config import OrchestratorConfig
from app.engine_orchestrator.orchestrator_errors import SnapshotContractViolationError, SnapshotNotEnoughDataError
from app.engine_orchestrator.orchestrator_status import FinalResult, PipelineStatus
from app.engine_orchestrator.pipeline_result import PipelineResult, SafetyCounters, json_safe
from app.engine_orchestrator.trade_profile import TradeProfileMode
from app.engine_paper.paper_runner import PaperRunner
from app.engine_risk.risk_runner import RiskRunner
from app.engine_risk.risk_config import RiskConfig
from app.engine_risk.risk_policy import RiskPolicy
from app.engine_setup.setup_detector import SetupDetector
from app.engine_setup.setup_runner import SetupRunner
from app.engine_setup.setup_store import SetupStore
from app.engine_strategy.strategy_runner import StrategyRunner
from app.engine_strategy.strategy_config import StrategyConfig
from app.engine_strategy.strategy_filter import StrategyFilter


SAFETY_FIELDS = {
    "future_bars_used": "future_bars_used_count",
    "is_trade_signal": "trade_signal_count",
    "is_executable": "is_executable_count",
    "order_approved": "order_approved_count",
    "execution_approved": "execution_approved_count",
    "position_opened": "position_opened_count",
    "position_size_approved": "position_size_approved_count",
}


def _attribute(value: object, *names: str) -> Any:
    for name in names:
        if hasattr(value, name):
            return getattr(value, name)
    return None


def _mapping_value(value: object, *names: str) -> Any:
    if not isinstance(value, dict):
        return None
    for name in names:
        if name in value:
            return value[name]
    return None


def _reasons(value: object) -> list[str]:
    for name in ("plan_reasons", "risk_reasons", "decision_reasons", "reason_codes"):
        data = _mapping_value(value, name) if isinstance(value, dict) else getattr(value, name, None)
        if data is not None:
            return [str(item) for item in data]
    return []


def _warnings(value: object) -> list[str]:
    for name in ("plan_warnings", "risk_warnings", "decision_warnings", "quality_warnings"):
        data = _mapping_value(value, name) if isinstance(value, dict) else getattr(value, name, None)
        if data is not None:
            return [str(item) for item in data]
    return []


class PipelineRunner:
    """Runs only analysis/setup/strategy/risk/paper over one reserved window."""

    def __init__(self, config: OrchestratorConfig, candle_repository: object, *,
                 analysis_runner: object | None = None, setup_runner: object | None = None,
                 strategy_runner: object | None = None, risk_runner: object | None = None,
                 paper_runner: object | None = None) -> None:
        self.config = config
        self.runtime_parameters = config.runtime_parameters
        self.candle_repository = candle_repository
        self.analysis_runner = analysis_runner or OnlineAnalysisRunner(
            OnlineAnalysisConfig(
                symbols=list(config.symbols), timeframes=[config.primary_timeframe],
                required_history_candles=self.runtime_parameters.analysis_history_candles,
                runtime_parameter_set_id=self.runtime_parameters.parameter_set_id,
                atr_lookback_candles=self.runtime_parameters.atr_lookback_candles,
                impulse_lookback_candles=self.runtime_parameters.impulse_lookback_candles,
                structure_lookback_candles=self.runtime_parameters.structure_lookback_candles,
                analysis_decision_candles=
                self.runtime_parameters.analysis_decision_candles,
                confirmation_window_candles=self.runtime_parameters.confirmation_window_candles,
                volume_baseline_candles=self.runtime_parameters.volume_baseline_candles,
                breakout_volume_baseline_candles=
                self.runtime_parameters.breakout_volume_baseline_candles,
                regime_lookback_candles=self.runtime_parameters.regime_lookback_candles,
            ),
            MarketDataAdapter(), AnalysisSnapshotStore(),
        )
        self.setup_runner = setup_runner or SetupRunner(
            SetupDetector(self.runtime_parameters), SetupStore(), self.runtime_parameters,
        )
        self.strategy_runner = strategy_runner or StrategyRunner(
            StrategyFilter(
                StrategyConfig(
                    minimum_allowed_quality=
                    self.runtime_parameters.strategy_minimum_allowed_quality,
                ),
                self.runtime_parameters,
            ),
            runtime_parameters=self.runtime_parameters,
        )
        self.risk_runner = risk_runner or RiskRunner(
            RiskPolicy(
                RiskConfig(
                    policy_version=self.runtime_parameters.risk_shadow_policy_id,
                    minimum_strategy_quality=
                    self.runtime_parameters.risk_minimum_strategy_quality,
                    minimum_strategy_score=
                    self.runtime_parameters.risk_minimum_strategy_score,
                ),
                runtime_parameters=self.runtime_parameters,
            ),
            runtime_parameters=self.runtime_parameters,
        )
        self.paper_runner = paper_runner or PaperRunner()

    @staticmethod
    def _context_boundary(timeframe: str, closed_until_ms: int) -> int:
        duration = timeframe_to_milliseconds(timeframe)
        return (int(closed_until_ms) // duration) * duration

    def build_snapshots(self, symbol: str, closed_until_ms: int) -> dict[str, MarketDataSnapshot]:
        snapshots: dict[str, MarketDataSnapshot] = {}
        counts: dict[str, int] = {}
        for timeframe in self.config.required_timeframes:
            required = self.config.minimum_windows[timeframe]
            duration = timeframe_to_milliseconds(timeframe)
            context_boundary = self._context_boundary(timeframe, closed_until_ms)
            last_open_time = context_boundary - duration
            candles = self.candle_repository.get_candles(
                symbol, timeframe, end_time_ms=last_open_time, limit=required
            )
            counts[timeframe] = len(candles)
            has_gaps = bool(find_missing_open_times(candles, timeframe))
            if candles and any(
                not bool(getattr(candle, "is_closed", False))
                or int(candle.open_time_ms) > last_open_time
                or int(candle.close_time_ms) >= context_boundary
                for candle in candles
            ):
                raise SnapshotContractViolationError(
                    f"{timeframe}:FUTURE_OR_UNCLOSED_DATA")
            if len(candles) >= required and (
                int(candles[-1].open_time_ms) != last_open_time or has_gaps
            ):
                raise SnapshotContractViolationError(
                    f"{timeframe}:SNAPSHOT_CONTRACT_VIOLATION")
            sources = sorted({candle.source for candle in candles})
            snapshots[timeframe] = MarketDataSnapshot(
                symbol=symbol.upper(), timeframe=timeframe,
                closed_until_ms=int(closed_until_ms), candles=candles,
                source=sources[0] if len(sources) == 1 else ("mixed" if sources else "none"),
                has_gaps=has_gaps, future_bars_used=False,
                health_status="OK" if not has_gaps and len(candles) >= required else "DEGRADED",
                enough_data=len(candles) >= required,
            )
        if any(counts[timeframe] < self.config.minimum_windows[timeframe]
               for timeframe in self.config.required_timeframes):
            raise SnapshotNotEnoughDataError(counts, self.config.minimum_windows)
        return snapshots

    @staticmethod
    def _invoke(target: object, method: str, value: object) -> object:
        function = getattr(target, method, target)
        if not callable(function):
            raise TypeError(f"pipeline component does not expose {method}()")
        return function(value)

    @staticmethod
    def _safety(outputs: list[object], snapshots: dict[str, MarketDataSnapshot]) -> SafetyCounters:
        counts = {field.name: 0 for field in fields(SafetyCounters)}
        for snapshot in snapshots.values():
            counts["future_bars_used_count"] += int(bool(snapshot.future_bars_used))
        for output in outputs:
            for source_name, counter_name in SAFETY_FIELDS.items():
                counts[counter_name] += int(bool(getattr(output, source_name, False)))
            counts["private_api_used"] += int(bool(getattr(output, "private_api_used", False)))
            counts["api_keys_used"] += int(bool(getattr(output, "api_keys_used", False)))
            counts["synthetic_candles_used"] += int(bool(getattr(output, "synthetic_candles_used", False)))
            counts["outcome_pnl_used"] += int(bool(getattr(output, "outcome_pnl_used", False)))
        return SafetyCounters(**counts)

    @staticmethod
    def _market_summary(snapshots: dict[str, MarketDataSnapshot]) -> dict[str, Any]:
        return {
            timeframe: {
                "candle_count": len(snapshot.candles), "source": snapshot.source,
                "has_gaps": snapshot.has_gaps, "enough_data": snapshot.enough_data,
                "first_open_time_ms": snapshot.candles[0].open_time_ms if snapshot.candles else None,
                "last_open_time_ms": snapshot.candles[-1].open_time_ms if snapshot.candles else None,
                "last_close_time_ms": snapshot.candles[-1].close_time_ms if snapshot.candles else None,
                "closed_until_ms": snapshot.closed_until_ms,
            }
            for timeframe, snapshot in snapshots.items()
        }

    @staticmethod
    def _final_from(outputs: dict[str, object]) -> str:
        paper = outputs.get("paper")
        if paper is not None:
            value = str(_attribute(paper, "paper_status"))
            return value if value in {item.value for item in FinalResult} else FinalResult.NO_PLAN.value
        risk = outputs.get("risk")
        if risk is not None and _attribute(risk, "risk_status") == "REJECT":
            return FinalResult.REJECT.value
        strategy = outputs.get("strategy")
        if strategy is not None and _attribute(strategy, "decision_status") == "REJECT":
            return FinalResult.REJECT.value
        setup = outputs.get("setup")
        if setup is not None and _attribute(setup, "status") == "NO_SETUP":
            return FinalResult.NO_SETUP.value
        analysis = outputs.get("analysis")
        if analysis is not None and _attribute(analysis, "action") == "NO_ACTION":
            return FinalResult.NO_ACTION.value
        return FinalResult.NO_DECISION.value

    def run(self, symbol: str, closed_until_ms: int) -> PipelineResult:
        identity = {
            "trade_profile_id": self.config.trade_profile_id,
            "trigger_timeframe": self.config.primary_timeframe,
            "profile_mode": self.config.trade_profile.mode,
            "runtime_parameter_set_id": self.runtime_parameters.parameter_set_id,
        }
        try:
            snapshots = self.build_snapshots(symbol, closed_until_ms)
        except SnapshotContractViolationError as exc:
            return PipelineResult(
                symbol=symbol.upper(), primary_timeframe=self.config.primary_timeframe,
                closed_until_ms=closed_until_ms,
                **identity,
                status=PipelineStatus.SKIPPED_FRESHNESS_NOT_OK.value,
                final_result=FinalResult.NO_ACTION.value,
                final_reason=str(exc), error_code="SNAPSHOT_CONTRACT_VIOLATION",
            )
        except SnapshotNotEnoughDataError as exc:
            return PipelineResult(
                symbol=symbol.upper(), primary_timeframe=self.config.primary_timeframe,
                closed_until_ms=closed_until_ms,
                **identity,
                status=PipelineStatus.SKIPPED_NOT_ENOUGH_DATA.value,
                final_result=FinalResult.NO_ACTION.value,
                final_reason=str(exc), error_code="NOT_ENOUGH_DATA",
                market_data_payload={"available": exc.counts, "required": exc.required},
            )

        outputs: dict[str, object] = {}
        try:
            analysis = self._invoke(self.analysis_runner, "analyze_market_data_snapshot",
                                    snapshots[self.config.primary_timeframe])
            outputs["analysis"] = analysis
            if _attribute(analysis, "status") != AnalysisSnapshotStatus.ANALYZED.value:
                result = PipelineResult(
                    symbol=symbol.upper(), primary_timeframe=self.config.primary_timeframe,
                    closed_until_ms=closed_until_ms, status=PipelineStatus.MODULE_ERROR.value
                    if _attribute(analysis, "status") == "ERROR" else PipelineStatus.COMPLETED.value,
                    final_result=FinalResult.ERROR.value if _attribute(analysis, "status") == "ERROR"
                    else FinalResult.NO_ACTION.value,
                    final_reason=str(_attribute(analysis, "skip_reason") or "analysis did not produce an analyzed snapshot"),
                    market_data_payload=self._market_summary(snapshots),
                    analysis_payload=json_safe(analysis), analysis_status=str(_attribute(analysis, "status")),
                    module_reasons={"analysis": _reasons(analysis)},
                    module_warnings={"analysis": _warnings(analysis)},
                    **identity,
                )
                result.safety_counters = self._safety([analysis], snapshots)
                return self._enforce_safety(result)

            setup = self._invoke(self.setup_runner, "process_analysis_snapshot", analysis)
            outputs["setup"] = setup
            strategy = self._invoke(self.strategy_runner, "process_setup_candidate", setup)
            outputs["strategy"] = strategy
            risk = self._invoke(self.risk_runner, "process_strategy_decision", strategy)
            outputs["risk"] = risk
            if self.config.trade_profile.mode == TradeProfileMode.SHADOW_SEARCH.value:
                risk_status = str(_attribute(risk, "risk_status") or "")
                shadow_plan = self._invoke(
                    self.paper_runner, "process_risk_decision", risk
                )
                shadow_plan_payload = json_safe(shadow_plan)
                shadow_plan_status = str(
                    _attribute(shadow_plan, "paper_status")
                    or _mapping_value(shadow_plan_payload, "paper_status")
                    or ""
                )
                outputs["paper"] = {
                    "paper_status": "SHADOW_SEARCH",
                    "shadow_plan_status": shadow_plan_status,
                    "shadow_plan": shadow_plan_payload,
                    "plan_reasons": _mapping_value(shadow_plan_payload, "plan_reasons") or [],
                    "plan_warnings": _mapping_value(shadow_plan_payload, "plan_warnings") or [],
                    "rejection_reasons": _mapping_value(
                        shadow_plan_payload, "rejection_reasons"
                    ) or [],
                    "wait_reasons": _mapping_value(shadow_plan_payload, "wait_reasons") or [],
                    "trade_profile_id": self.config.trade_profile_id,
                    "trigger_timeframe": self.config.primary_timeframe,
                    "runtime_parameter_set_id": self.runtime_parameters.parameter_set_id,
                    "paper_command_creation_enabled":
                    self.runtime_parameters.paper_command_creation_enabled,
                    "position_opening_enabled":
                    self.runtime_parameters.position_opening_enabled,
                    "causal_levels": {
                        "entry": _attribute(setup, "hypothetical_entry_level", "entry_level"),
                        "stop": _attribute(setup, "hypothetical_stop_level", "stop_level"),
                        "target": _attribute(setup, "hypothetical_target_level", "target_level"),
                        "stop_authority": self.runtime_parameters.stop_policy_id,
                        "target_authority": self.runtime_parameters.target_policy_id,
                        "minimum_planned_rr": self.runtime_parameters.minimum_planned_rr,
                    },
                    "cost_efficiency_diagnostic": self._cost_efficiency_diagnostic(
                        setup, risk, shadow_plan
                    ),
                    "validity_policy": {
                        "source_close_ms": int(closed_until_ms),
                        "valid_until_ms": int(closed_until_ms) + (
                            timeframe_to_milliseconds(self.config.primary_timeframe)
                            * self.runtime_parameters.validity_boundaries
                        ),
                        "validity_boundaries": self.runtime_parameters.validity_boundaries,
                        "runtime_parameter_set_id": self.runtime_parameters.parameter_set_id,
                    },
                    "shadow_final_approval_candidate": {
                        "candidate_id": (
                            f"shadow:{self.config.trade_profile_id}:{symbol.upper()}:{int(closed_until_ms)}"
                        ),
                        "status": "PLAN_READY" if (
                            risk_status in {"RISK_PRE_APPROVED_RESEARCH", "RISK_APPROVED"}
                            and shadow_plan_status == "PAPER_PLAN_READY"
                        ) else "NOT_ELIGIBLE",
                        "execution_eligible": False,
                        "persisted_final_approval_created": False,
                    },
                }
            else:
                outputs["paper"] = self._invoke(self.paper_runner, "process_risk_decision", risk)
        except Exception as exc:
            safety = self._safety(list(outputs.values()), snapshots)
            return self._enforce_safety(PipelineResult(
                symbol=symbol.upper(), primary_timeframe=self.config.primary_timeframe,
                closed_until_ms=closed_until_ms, status=PipelineStatus.MODULE_ERROR.value,
                final_result=FinalResult.ERROR.value, final_reason="safe pipeline module failed",
                error_code="MODULE_ERROR", error_message=f"{type(exc).__name__}: {exc}",
                **identity,
                market_data_payload=self._market_summary(snapshots),
                analysis_payload=json_safe(outputs.get("analysis", {})),
                setup_payload=json_safe(outputs.get("setup", {})),
                strategy_payload=json_safe(outputs.get("strategy", {})),
                risk_payload=json_safe(outputs.get("risk", {})),
                paper_payload=json_safe(outputs.get("paper", {})), safety_counters=safety,
            ))

        statuses = {
            "analysis": str(_attribute(outputs["analysis"], "status")),
            "setup": str(_attribute(outputs["setup"], "status")),
            "strategy": str(_attribute(outputs["strategy"], "decision_status")),
            "risk": str(_attribute(outputs["risk"], "risk_status")),
            "paper": str(_attribute(outputs["paper"], "paper_status") or _mapping_value(outputs["paper"], "paper_status")),
        }
        module_error = any(value == "ERROR" for value in statuses.values())
        result = PipelineResult(
            symbol=symbol.upper(), primary_timeframe=self.config.primary_timeframe,
            closed_until_ms=closed_until_ms,
            status=PipelineStatus.MODULE_ERROR.value if module_error else PipelineStatus.COMPLETED.value,
            final_result=FinalResult.ERROR.value if module_error else self._final_from(outputs),
            final_reason="module returned ERROR" if module_error else None,
            market_data_payload=self._market_summary(snapshots),
            analysis_payload=self._profiled_payload(outputs["analysis"]),
            setup_payload=self._profiled_payload(outputs["setup"]),
            strategy_payload=self._profiled_payload(outputs["strategy"]),
            risk_payload=self._profiled_payload(outputs["risk"]),
            paper_payload=json_safe(outputs["paper"]),
            analysis_status=statuses["analysis"], setup_status=statuses["setup"],
            strategy_status=statuses["strategy"], risk_status=statuses["risk"],
            paper_status=statuses["paper"],
            module_reasons={name: _reasons(value) for name, value in outputs.items()},
            module_warnings={name: _warnings(value) for name, value in outputs.items()},
            safety_counters=self._safety(list(outputs.values()), snapshots),
            **identity,
        )
        return self._enforce_safety(result)

    def _profiled_payload(self, value: object) -> dict[str, Any]:
        payload = json_safe(value)
        if not isinstance(payload, dict):
            payload = {"value": payload}
        return {
            **payload,
            "trade_profile_id": self.config.trade_profile_id,
            "trigger_timeframe": self.config.primary_timeframe,
            "runtime_parameter_set_id": self.runtime_parameters.parameter_set_id,
        }

    def _cost_efficiency_diagnostic(self, *values: object) -> dict[str, object]:
        payloads = [json_safe(value) for value in values]
        entry = next((_mapping_value(
            payload, "hypothetical_entry_reference", "hypothetical_entry_level",
            "entry_price", "entry"
        ) for payload in payloads if _mapping_value(
            payload, "hypothetical_entry_reference", "hypothetical_entry_level",
            "entry_price", "entry"
        ) is not None), None)
        target = next((_mapping_value(
            payload, "hypothetical_target_level", "target_price", "target"
        ) for payload in payloads if _mapping_value(
            payload, "hypothetical_target_level", "target_price", "target"
        ) is not None), None)
        gross_move_bps = None
        try:
            if entry is not None and target is not None and float(entry) > 0:
                gross_move_bps = abs(float(target) - float(entry)) / float(entry) * 10_000
        except (TypeError, ValueError):
            gross_move_bps = None
        known_cost_floor_bps = 2 * (10.0 + 2.0) + self.runtime_parameters.cost_safety_margin_bps
        return {
            "expected_gross_move_bps": gross_move_bps,
            "authoritative_spread_bps": None,
            "spread_authority_available": False,
            "fee_slippage_authority": "CURRENT_PAPER_FOUNDATION_POLICY",
            "fee_bps_per_fill": 10.0,
            "adverse_slippage_bps_per_fill": 2.0,
            "safety_margin_bps": self.runtime_parameters.cost_safety_margin_bps,
            "runtime_parameter_set_id": self.runtime_parameters.parameter_set_id,
            "known_round_trip_cost_floor_bps": known_cost_floor_bps,
            "gross_exceeds_known_cost_floor": (
                None if gross_move_bps is None else gross_move_bps > known_cost_floor_bps
            ),
            "gate_enabled": False,
        }

    @staticmethod
    def _enforce_safety(result: PipelineResult) -> PipelineResult:
        if result.safety_counters.has_violation:
            result.status = PipelineStatus.ERROR.value
            result.final_result = FinalResult.ERROR.value
            result.final_reason = "forbidden safety counter is non-zero"
            result.error_code = "SAFETY_VIOLATION"
        return result
