"""Безопасный paper-only runner."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime

from app.config.settings import get_settings
from app.db.session import session_scope
from app.execution.paper_step_service import PaperStepService, PaperStepResult
from app.execution.position_manager import PositionManager
from app.market.analysis_service import MarketAnalysisService
from app.market.candle_service import CandleService


INTERVAL_SECONDS = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "2h": 7200,
    "4h": 14400,
    "6h": 21600,
    "8h": 28800,
    "12h": 43200,
    "1d": 86400,
    "3d": 259200,
    "1w": 604800,
    "1M": 2592000,
}


@dataclass(slots=True)
class RunnerIterationResult:
    """Результат одной итерации paper-runner."""

    processed: bool
    message: str
    result: PaperStepResult | None = None


class PaperRunnerService:
    """Следит за новой закрытой свечой и запускает ровно один paper-step."""

    def __init__(
        self,
        candle_service: CandleService | None = None,
        analysis_service: MarketAnalysisService | None = None,
    ) -> None:
        self.settings = get_settings()
        self.candle_service = candle_service or CandleService()
        self.analysis_service = analysis_service or MarketAnalysisService()

    async def run_once(self, *, symbol: str, interval: str) -> RunnerIterationResult:
        """Обновляет свечи и, если появилась новая закрытая свеча, выполняет paper-step."""

        await self.candle_service.fetch_and_store_candles(
            symbol=symbol,
            interval=interval,
            limit=self.settings.default_candle_limit,
        )

        with session_scope() as session:
            analysis = self.analysis_service.load_and_analyze(
                session=session,
                symbol=symbol,
                interval=interval,
                limit=self.settings.default_candle_limit,
            )
            manager = PositionManager(session)
            runner_state = manager.get_or_create_runner_state(symbol=symbol, interval=interval)

            if self._normalize_datetime(runner_state.last_processed_open_time) == self._normalize_datetime(
                analysis.latest_candle.open_time
            ):
                return RunnerIterationResult(
                    processed=False,
                    message="Новая закрытая свеча ещё не появилась, шаг пропущен.",
                    result=None,
                )

            result = PaperStepService(session).process(
                analysis.strategy_decision,
                indicator_snapshot=analysis.indicator_snapshot,
                latest_candle=analysis.latest_candle,
            )
            runner_state.last_processed_open_time = analysis.latest_candle.open_time
            runner_state.updated_at = datetime.now(UTC)

            return RunnerIterationResult(
                processed=True,
                message="Новая закрытая свеча обработана paper-runner.",
                result=result,
            )

    async def run_forever(self, *, symbol: str, interval: str, on_iteration) -> None:
        """Крутит безопасный paper-only цикл до Ctrl+C."""

        sleep_seconds = self._get_poll_seconds(interval)
        while True:
            try:
                result = await self.run_once(symbol=symbol, interval=interval)
                on_iteration(result)
            except Exception as exc:
                on_iteration(RunnerIterationResult(processed=False, message=f"Ошибка paper-runner: {exc}", result=None))
            await asyncio.sleep(sleep_seconds)

    @staticmethod
    def _get_poll_seconds(interval: str) -> int:
        """Подбирает частоту опроса рынка для MVP runner."""

        interval_seconds = INTERVAL_SECONDS[interval]
        return min(max(interval_seconds // 4, 30), 60)

    @staticmethod
    def _normalize_datetime(value: datetime | None) -> datetime | None:
        """Приводит datetime к UTC-виду для корректного сравнения после roundtrip через БД."""

        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
