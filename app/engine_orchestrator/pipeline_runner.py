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
from app.engine_orchestrator.orchestrator_errors import SnapshotNotEnoughDataError
from app.engine_orchestrator.orchestrator_status import FinalResult, PipelineStatus
from app.engine_orchestrator.pipeline_result import PipelineResult, SafetyCounters, json_safe
from app.engine_paper.paper_runner import PaperRunner
from app.engine_risk.risk_runner import RiskRunner
from app.engine_setup.setup_detector import SetupDetector
from app.engine_setup.setup_runner import SetupRunner
from app.engine_setup.setup_store import SetupStore
from app.engine_strategy.strategy_runner import StrategyRunner


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


def _reasons(value: object) -> list[str]:
    for name in ("plan_reasons", "risk_reasons", "decision_reasons", "reason_codes"):
        data = getattr(value, name, None)
        if data is not None:
            return [str(item) for item in data]
    return []


def _warnings(value: object) -> list[str]:
    for name in ("plan_warnings", "risk_warnings", "decision_warnings", "quality_warnings"):
        data = getattr(value, name, None)
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
        self.candle_repository = candle_repository
        self.analysis_runner = analysis_runner or OnlineAnalysisRunner(
            OnlineAnalysisConfig(
                symbols=list(config.symbols), timeframes=[config.primary_timeframe],
                required_history_candles=config.minimum_windows[config.primary_timeframe],
            ),
            MarketDataAdapter(), AnalysisSnapshotStore(),
        )
        self.setup_runner = setup_runner or SetupRunner(SetupDetector(), SetupStore())
        self.strategy_runner = strategy_runner or StrategyRunner()
        self.risk_runner = risk_runner or RiskRunner()
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
        try:
            snapshots = self.build_snapshots(symbol, closed_until_ms)
        except SnapshotNotEnoughDataError as exc:
            return PipelineResult(
                symbol=symbol.upper(), primary_timeframe=self.config.primary_timeframe,
                closed_until_ms=closed_until_ms,
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
                )
                result.safety_counters = self._safety([analysis], snapshots)
                return self._enforce_safety(result)

            setup = self._invoke(self.setup_runner, "process_analysis_snapshot", analysis)
            outputs["setup"] = setup
            strategy = self._invoke(self.strategy_runner, "process_setup_candidate", setup)
            outputs["strategy"] = strategy
            risk = self._invoke(self.risk_runner, "process_strategy_decision", strategy)
            outputs["risk"] = risk
            paper = self._invoke(self.paper_runner, "process_risk_decision", risk)
            outputs["paper"] = paper
        except Exception as exc:
            safety = self._safety(list(outputs.values()), snapshots)
            return self._enforce_safety(PipelineResult(
                symbol=symbol.upper(), primary_timeframe=self.config.primary_timeframe,
                closed_until_ms=closed_until_ms, status=PipelineStatus.MODULE_ERROR.value,
                final_result=FinalResult.ERROR.value, final_reason="safe pipeline module failed",
                error_code="MODULE_ERROR", error_message=f"{type(exc).__name__}: {exc}",
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
            "paper": str(_attribute(outputs["paper"], "paper_status")),
        }
        module_error = any(value == "ERROR" for value in statuses.values())
        result = PipelineResult(
            symbol=symbol.upper(), primary_timeframe=self.config.primary_timeframe,
            closed_until_ms=closed_until_ms,
            status=PipelineStatus.MODULE_ERROR.value if module_error else PipelineStatus.COMPLETED.value,
            final_result=FinalResult.ERROR.value if module_error else self._final_from(outputs),
            final_reason="module returned ERROR" if module_error else None,
            market_data_payload=self._market_summary(snapshots),
            analysis_payload=json_safe(outputs["analysis"]), setup_payload=json_safe(outputs["setup"]),
            strategy_payload=json_safe(outputs["strategy"]), risk_payload=json_safe(outputs["risk"]),
            paper_payload=json_safe(outputs["paper"]),
            analysis_status=statuses["analysis"], setup_status=statuses["setup"],
            strategy_status=statuses["strategy"], risk_status=statuses["risk"],
            paper_status=statuses["paper"],
            module_reasons={name: _reasons(value) for name, value in outputs.items()},
            module_warnings={name: _warnings(value) for name, value in outputs.items()},
            safety_counters=self._safety(list(outputs.values()), snapshots),
        )
        return self._enforce_safety(result)

    @staticmethod
    def _enforce_safety(result: PipelineResult) -> PipelineResult:
        if result.safety_counters.has_violation:
            result.status = PipelineStatus.ERROR.value
            result.final_result = FinalResult.ERROR.value
            result.final_reason = "forbidden safety counter is non-zero"
            result.error_code = "SAFETY_VIOLATION"
        return result
