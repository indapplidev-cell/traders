"""Restart-safe, missing-only historical candle backfill orchestration."""

import time
from collections.abc import Callable

from app.engine_market_data.historical_backfill_config import HistoricalBackfillConfig
from app.engine_market_data.historical_backfill_planner import (
    BackfillTask,
    HistoricalBackfillPlanner,
    group_missing_open_times_into_ranges,
    split_backfill_range,
)
from app.engine_market_data.historical_backfill_report import (
    BackfillStatus,
    BackfillTaskReport,
    HistoricalBackfillReport,
)
from app.engine_market_data.historical_backfill_verifier import HistoricalBackfillVerifier
from app.engine_market_data.timeframe import timeframe_to_milliseconds


class HistoricalBackfillRunner:
    def __init__(
        self,
        repository: object,
        rest_client: object,
        planner: HistoricalBackfillPlanner,
        verifier: HistoricalBackfillVerifier,
        config: HistoricalBackfillConfig,
        *,
        now_ms: int | Callable[[], int] | None = None,
    ) -> None:
        self.repository = repository
        self.rest_client = rest_client
        self.planner = planner
        self.verifier = verifier
        self.config = config
        self._now_ms = now_ms

    def backfill_symbol_timeframe(
        self, symbol: str, timeframe: str, *, now_ms: int | None = None,
    ) -> BackfillTaskReport:
        current = self._current_time_ms() if now_ms is None else now_ms
        task = self.planner.build_task(symbol, timeframe, current,
                                       self.config.backfill_limits[timeframe])
        return self._run_task(task, current)

    def backfill_all(self) -> HistoricalBackfillReport:
        current = self._current_time_ms()
        plan = self.planner.build_plan(self.config.symbols, self.config.timeframes, current,
                                       self.config.backfill_limits)
        report = HistoricalBackfillReport(symbols=list(self.config.symbols),
                                          timeframes=list(self.config.timeframes))
        for task in plan.tasks:
            report.task_reports.append(self._run_task(task, current))
        report.finish()
        if self.config.fail_on_unrecovered_gaps and report.missing_after_total:
            raise RuntimeError(f"historical backfill left {report.missing_after_total} gaps")
        return report

    def verify_all(self) -> HistoricalBackfillReport:
        current = self._current_time_ms()
        plan = self.planner.build_plan(self.config.symbols, self.config.timeframes, current,
                                       self.config.backfill_limits)
        report = HistoricalBackfillReport(symbols=list(self.config.symbols),
                                          timeframes=list(self.config.timeframes))
        for task in plan.tasks:
            verification = self.verifier.verify_task(task)
            status = BackfillStatus.NOOP_ALREADY_FILLED if not verification.has_gaps else BackfillStatus.DEGRADED
            report.task_reports.append(BackfillTaskReport(
                symbol=task.symbol, timeframe=task.timeframe, limit=task.limit,
                start_open_time_ms=task.start_open_time_ms, end_open_time_ms=task.end_open_time_ms,
                expected_count=task.limit, existing_before=verification.actual_count,
                missing_before=verification.missing_count, existing_after=verification.actual_count,
                missing_after=verification.missing_count, status=status,
            ))
        return report.finish()

    def _run_task(self, task: BackfillTask, now_ms: int) -> BackfillTaskReport:
        result = BackfillTaskReport(task.symbol, task.timeframe, task.limit,
                                    task.start_open_time_ms, task.end_open_time_ms, task.limit)
        try:
            missing = self.repository.find_missing_open_times(task.symbol, task.timeframe,
                                                              task.expected_open_times)
            missing = sorted(set(missing))
            result.missing_before = len(missing)
            result.existing_before = task.limit - len(missing)
            if not missing:
                result.existing_after = task.limit
                result.status = BackfillStatus.NOOP_ALREADY_FILLED
                return result

            ranges = group_missing_open_times_into_ranges(missing, task.timeframe, task.symbol)
            result.rest_ranges = len(ranges)
            missing_set = set(missing)
            accepted_by_open: dict[int, object] = {}
            duration = timeframe_to_milliseconds(task.timeframe)
            batch_size = min(self.config.batch_limit, self.config.max_rest_limit)
            for item in ranges:
                for batch in split_backfill_range(item, batch_size):
                    try:
                        candles = self.rest_client.fetch_klines(
                            symbol=task.symbol,
                            timeframe=task.timeframe,
                            start_time_ms=batch.start_time_ms,
                            end_time_ms=batch.end_time_ms + duration - 1,
                            limit=batch.expected_count,
                        )
                        result.rest_calls += 1
                        result.downloaded_candles += len(candles)
                    except Exception as exc:
                        result.rest_calls += 1
                        result.errors.append(f"REST {batch.start_time_ms}-{batch.end_time_ms}: {exc}")
                        continue
                    for candle in candles:
                        if (candle.symbol != task.symbol or candle.timeframe != task.timeframe
                                or candle.open_time_ms not in missing_set
                                or candle.open_time_ms > task.latest_closed_open_time_ms):
                            result.rejected_unexpected_candles += 1
                            continue
                        if (not candle.is_closed or candle.close_time_ms >= now_ms
                                or candle.close_time_ms > task.latest_closed_open_time_ms + duration - 1):
                            result.rejected_unclosed_candles += 1
                            continue
                        accepted_by_open[candle.open_time_ms] = candle
            accepted = [accepted_by_open[value] for value in sorted(accepted_by_open)]
            result.accepted_candles = len(accepted)
            if accepted:
                result.upserted_candles = self.repository.upsert_candles(accepted)

            verification = self.verifier.verify_task(task)
            result.missing_after = verification.missing_count
            result.existing_after = verification.actual_count
            if not result.missing_after:
                result.status = BackfillStatus.SUCCESS
            elif result.accepted_candles:
                result.status = BackfillStatus.PARTIAL
            elif result.errors:
                result.status = BackfillStatus.ERROR
            else:
                result.status = BackfillStatus.DEGRADED
        except Exception as exc:
            result.errors.append(str(exc))
            result.status = BackfillStatus.ERROR
            try:
                verification = self.verifier.verify_task(task)
                result.missing_after = verification.missing_count
                result.existing_after = verification.actual_count
            except Exception as verify_exc:
                result.errors.append(f"verification: {verify_exc}")
                result.missing_after = task.limit
        return result

    def _current_time_ms(self) -> int:
        if callable(self._now_ms):
            return int(self._now_ms())
        if self._now_ms is not None:
            return int(self._now_ms)
        server_time = getattr(self.rest_client, "fetch_server_time_ms", None)
        return int(server_time()) if server_time is not None else int(time.time() * 1000)

