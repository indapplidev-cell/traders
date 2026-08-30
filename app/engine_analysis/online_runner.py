"""Closed-window online runner connecting market data to analysis only."""

from __future__ import annotations

import inspect
import time
from collections.abc import AsyncIterable, AsyncIterator, Iterable
from enum import Enum
from threading import RLock
from typing import Any, Callable

from app.engine_analysis.analysis_snapshot import AnalysisSnapshot, AnalysisSnapshotStatus
from app.engine_analysis.analysis_contract import AnalysisWindowConfig
from app.engine_analysis.analysis_snapshot_store import AnalysisSnapshotStore
from app.engine_analysis.engine import run_engine_analysis
from app.engine_analysis.market_data_adapter import MarketDataAdapter
from app.engine_analysis.online_config import OnlineAnalysisConfig
from app.engine_analysis.online_errors import InvalidMarketDataSnapshotError
from app.engine_analysis.online_health import evaluate_market_data_health
from app.engine_analysis.online_state import OnlineAnalysisState
from app.engine_market_data.candle_stream import ClosedCandleEvent
from app.engine_market_data.market_data_snapshot import MarketDataSnapshot


AnalysisPipeline = Callable[..., object]


def _plain(value: object) -> object:
    return value.value if isinstance(value, Enum) else value


def _mapping_value(mapping: dict[str, Any], *paths: tuple[str, ...]) -> Any:
    for path in paths:
        current: Any = mapping
        for part in path:
            if not isinstance(current, dict) or part not in current:
                break
            current = current[part]
        else:
            return current
    return None


class OnlineAnalysisRunner:
    """Analyze each healthy closed market window at most once."""

    def __init__(
        self,
        config: OnlineAnalysisConfig,
        adapter: MarketDataAdapter,
        snapshot_store: AnalysisSnapshotStore,
        analysis_pipeline: AnalysisPipeline | object | None = None,
    ) -> None:
        self.config = config
        self.adapter = adapter
        self.snapshot_store = snapshot_store
        self.analysis_pipeline = analysis_pipeline or run_engine_analysis
        self.state = OnlineAnalysisState()
        self._reserved_windows: set[tuple[str, str, int]] = set()
        self._dedupe_lock = RLock()

    @staticmethod
    def _now_ms() -> int:
        return time.time_ns() // 1_000_000

    @staticmethod
    def _source_id(snapshot: MarketDataSnapshot) -> str:
        value = snapshot.snapshot_id
        if not value:
            raise ValueError("MarketDataSnapshot.snapshot_id must not be empty")
        return value

    def _build(
        self,
        snapshot: object,
        *,
        status: AnalysisSnapshotStatus,
        health: str,
        degraded: bool,
        enough_data: bool,
        skip_reason: str | None = None,
        analysis_error: str | None = None,
        **analysis: Any,
    ) -> AnalysisSnapshot:
        symbol = str(getattr(snapshot, "symbol", "UNKNOWN")).upper()
        timeframe = str(getattr(snapshot, "timeframe", "UNKNOWN"))
        closed_until_ms = int(getattr(snapshot, "closed_until_ms", 0) or 0)
        result = AnalysisSnapshot.for_window(
            symbol=symbol,
            timeframe=timeframe,
            closed_until_ms=closed_until_ms,
            created_at_ms=self._now_ms(),
            market_data_health=health,
            degraded=degraded,
            enough_data=enough_data,
            future_bars_used=False,
            status=status.value,
            skip_reason=skip_reason,
            source_market_data_snapshot_id=(
                self._source_id(snapshot)
                if isinstance(snapshot, MarketDataSnapshot)
                else None
            ),
            analysis_error=analysis_error,
            **analysis,
        )
        if self.config.store_snapshots and status is not AnalysisSnapshotStatus.SKIPPED_DUPLICATE_WINDOW:
            self.snapshot_store.save(result)
        if status is AnalysisSnapshotStatus.ANALYZED:
            self.state.analyzed_windows += 1
        elif status is AnalysisSnapshotStatus.ERROR:
            self.state.error_windows += 1
        else:
            self.state.skipped_windows += 1
        return result

    def _invalid(self, source: object, reason: str) -> AnalysisSnapshot:
        health = str(getattr(source, "health_status", "ERROR"))
        return self._build(
            source,
            status=AnalysisSnapshotStatus.SKIPPED_INVALID_SNAPSHOT,
            health=health,
            degraded=False,
            enough_data=False,
            skip_reason="INVALID_SNAPSHOT",
            reason_codes=["INVALID_SNAPSHOT"],
            analysis_context={"validation_error": reason},
        )

    def _reserve_window(self, snapshot: MarketDataSnapshot) -> bool:
        if not self.config.dedupe_by_closed_until:
            return True
        key = (snapshot.symbol.upper(), snapshot.timeframe, snapshot.closed_until_ms)
        with self._dedupe_lock:
            if key in self._reserved_windows:
                return False
            if self.snapshot_store.get_by_window(*key) is not None:
                return False
            self._reserved_windows.add(key)
            return True

    def _invoke_pipeline(self, snapshot: MarketDataSnapshot, candles: tuple[object, ...], degraded: bool) -> object:
        pipeline = self.analysis_pipeline
        if pipeline is run_engine_analysis:
            return run_engine_analysis(
                snapshot.symbol,
                snapshot.timeframe,
                candles,
                config=AnalysisWindowConfig(
                    minimum_candles=min(64, self.config.regime_lookback_candles),
                    context_candles=self.config.regime_lookback_candles,
                    decision_candles=self.config.analysis_decision_candles,
                    confirmation_candles=self.config.confirmation_window_candles,
                    atr_lookback_candles=self.config.atr_lookback_candles,
                    impulse_lookback_candles=self.config.impulse_lookback_candles,
                    structure_lookback_candles=self.config.structure_lookback_candles,
                    volume_baseline_candles=self.config.volume_baseline_candles,
                    breakout_volume_baseline_candles=
                    self.config.breakout_volume_baseline_candles,
                ),
                strict_market_series=not degraded,
            )
        target = getattr(pipeline, "analyze", pipeline)
        if not callable(target):
            raise TypeError("analysis_pipeline must be callable or expose analyze()")
        candidates = (
            (snapshot.symbol, snapshot.timeframe, candles),
            (candles,),
            (snapshot,),
        )
        try:
            signature = inspect.signature(target)
        except (TypeError, ValueError):
            return target(snapshot.symbol, snapshot.timeframe, candles)
        for args in candidates:
            try:
                signature.bind(*args)
            except TypeError:
                continue
            return target(*args)
        raise TypeError("analysis_pipeline has no supported call signature")

    @staticmethod
    def _extract_analysis(output: object) -> dict[str, Any]:
        payload: dict[str, Any]
        if isinstance(output, dict):
            payload = dict(output)
        else:
            raw_payload = getattr(output, "json_payload", None)
            payload = dict(raw_payload) if isinstance(raw_payload, dict) else {}

        composer = getattr(output, "composer_output", None)
        result = getattr(composer, "result", None)
        regime = getattr(result, "market_regime", None)
        confidence = getattr(result, "confidence", None)
        reasons = getattr(result, "reason_codes", None)
        if regime is None:
            regime = _mapping_value(
                payload,
                ("regime",), ("market_regime",), ("model_regime",), ("result", "market_regime"),
            )
        if confidence is None:
            confidence = _mapping_value(
                payload,
                ("confidence",), ("model_confidence",), ("result", "confidence"),
            )
        if reasons is None:
            reasons = _mapping_value(
                payload,
                ("reason_codes",), ("model_reason_codes",), ("result", "reason_codes"),
            )
        action = _mapping_value(
            payload,
            ("action",), ("model_final_action",), ("final_action",),
            ("safety", "final_action"),
        )
        impulse_phase = _mapping_value(
            payload,
            ("impulse_phase",), ("model_impulse_phase",),
            ("analysis_context", "impulse_phase"),
        )
        entry_quality = _mapping_value(
            payload,
            ("entry_quality",), ("model_entry_quality",),
            ("analysis_context", "entry_quality"),
        )
        explanation = _mapping_value(
            payload,
            ("human_readable_explanation",), ("human_explanation",), ("explanation",),
        )
        context = _mapping_value(payload, ("analysis_context",))
        if not isinstance(context, dict):
            context = payload
        return {
            "regime": str(_plain(regime)) if regime is not None else None,
            "confidence": float(confidence) if confidence is not None else None,
            "action": str(_plain(action)) if action is not None else "NO_ACTION",
            "impulse_phase": str(_plain(impulse_phase)) if impulse_phase is not None else None,
            "entry_quality": str(_plain(entry_quality)) if entry_quality is not None else None,
            "reason_codes": [str(_plain(item)) for item in (reasons or ())],
            "analysis_context": dict(context),
            "human_readable_explanation": str(explanation) if explanation is not None else None,
        }

    def analyze_market_data_snapshot(self, snapshot: MarketDataSnapshot) -> AnalysisSnapshot:
        self.state.received_windows += 1
        if not isinstance(snapshot, MarketDataSnapshot):
            return self._invalid(snapshot, "input is not a MarketDataSnapshot")
        if self.config.symbols and snapshot.symbol.upper() not in self.config.symbols:
            return self._invalid(snapshot, "symbol is outside online configuration")
        if self.config.timeframes and snapshot.timeframe not in self.config.timeframes:
            return self._invalid(snapshot, "timeframe is outside online configuration")

        health = evaluate_market_data_health(
            snapshot.health_status,
            has_gaps=snapshot.has_gaps,
            allow_degraded_market_data=self.config.allow_degraded_market_data,
        )
        if not health.allowed:
            invalid_health = health.reason == "INVALID_SNAPSHOT"
            return self._build(
                snapshot,
                status=(
                    AnalysisSnapshotStatus.SKIPPED_INVALID_SNAPSHOT
                    if invalid_health
                    else AnalysisSnapshotStatus.SKIPPED_DEGRADED_MARKET_DATA
                ),
                health=snapshot.health_status,
                degraded=health.degraded,
                enough_data=len(snapshot.candles) >= self.config.required_history_candles,
                skip_reason=health.reason,
                reason_codes=[health.reason] if health.reason else [],
                analysis_context={},
            )

        enough_data = (
            bool(snapshot.enough_data)
            and len(snapshot.candles) >= self.config.required_history_candles
        )
        if not enough_data:
            return self._build(
                snapshot,
                status=AnalysisSnapshotStatus.SKIPPED_NOT_ENOUGH_DATA,
                health=snapshot.health_status,
                degraded=health.degraded,
                enough_data=False,
                skip_reason="NOT_ENOUGH_DATA",
                reason_codes=["NOT_ENOUGH_DATA"],
                analysis_context={
                    "available_candles": len(snapshot.candles),
                    "required_candles": self.config.required_history_candles,
                },
            )

        try:
            candles = self.adapter.adapt(snapshot)
        except (InvalidMarketDataSnapshotError, AttributeError, TypeError, ValueError) as exc:
            return self._invalid(snapshot, str(exc))

        if self.config.run_on_closed_candle_only and len(candles) != len(snapshot.candles):
            return self._invalid(snapshot, "adapter did not preserve the closed candle window")
        if not self._reserve_window(snapshot):
            return self._build(
                snapshot,
                status=AnalysisSnapshotStatus.SKIPPED_DUPLICATE_WINDOW,
                health=snapshot.health_status,
                degraded=health.degraded,
                enough_data=True,
                skip_reason="DUPLICATE_WINDOW",
                reason_codes=["DUPLICATE_WINDOW"],
                analysis_context={},
            )
        try:
            output = self._invoke_pipeline(snapshot, candles, health.degraded)
            analysis = self._extract_analysis(output)
            analysis_context = dict(analysis.get("analysis_context") or {})
            analysis_context.update({
                "runtime_parameter_set_id": self.config.runtime_parameter_set_id,
                "analysis_runtime_parameters": {
                    "atr_lookback_candles": self.config.atr_lookback_candles,
                    "impulse_lookback_candles": self.config.impulse_lookback_candles,
                    "structure_lookback_candles": self.config.structure_lookback_candles,
                    "analysis_decision_candles": self.config.analysis_decision_candles,
                    "confirmation_window_candles": self.config.confirmation_window_candles,
                    "volume_baseline_candles": self.config.volume_baseline_candles,
                    "breakout_volume_baseline_candles":
                    self.config.breakout_volume_baseline_candles,
                    "regime_lookback_candles": self.config.regime_lookback_candles,
                },
            })
            analysis["analysis_context"] = analysis_context
            return self._build(
                snapshot,
                status=AnalysisSnapshotStatus.ANALYZED,
                health=snapshot.health_status,
                degraded=health.degraded,
                enough_data=True,
                **analysis,
            )
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            return self._build(
                snapshot,
                status=AnalysisSnapshotStatus.ERROR,
                health=snapshot.health_status,
                degraded=health.degraded,
                enough_data=True,
                skip_reason="ANALYSIS_PIPELINE_ERROR",
                analysis_error=error,
                reason_codes=["ANALYSIS_PIPELINE_ERROR"],
                analysis_context={"analysis_error": error},
            )

    def _snapshot_from_event(self, event: object) -> MarketDataSnapshot:
        if isinstance(event, MarketDataSnapshot):
            return event
        if isinstance(event, ClosedCandleEvent):
            return self.adapter.snapshot_from_closed_candle_event(
                event,
                minimum_candles=self.config.required_history_candles,
            )
        embedded = getattr(event, "snapshot", None)
        if isinstance(embedded, MarketDataSnapshot):
            return embedded
        raise InvalidMarketDataSnapshotError("event does not provide a MarketDataSnapshot")

    async def run_on_closed_candle_events(
        self,
        events: AsyncIterable[object] | Iterable[object],
    ) -> AsyncIterator[AnalysisSnapshot]:
        async def handle(event: object) -> AnalysisSnapshot:
            try:
                snapshot = self._snapshot_from_event(event)
            except (InvalidMarketDataSnapshotError, AttributeError, TypeError, ValueError) as exc:
                return self._invalid(event, str(exc))
            return self.analyze_market_data_snapshot(snapshot)

        if isinstance(events, AsyncIterable):
            async for event in events:
                yield await handle(event)
        else:
            for event in events:
                yield await handle(event)
