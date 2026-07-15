"""Missing-only REST recovery and warmup for closed PostgreSQL candles."""

from collections.abc import Sequence
import time

from app.engine_market_data.boundary_scheduler import BoundaryEvent
from app.engine_market_data.db_sync_config import DBSyncConfig
from app.engine_market_data.db_sync_report import SyncReport
from app.engine_market_data.market_data_health import MarketDataHealth
from app.engine_market_data.timeframe import timeframe_to_milliseconds
from app.engine_market_data.timeframe_sync_plan import build_sync_tasks_for_boundary


def _contiguous_groups(values: Sequence[int], step: int, max_size: int) -> list[list[int]]:
    groups: list[list[int]] = []
    for value in sorted(set(values)):
        if not groups or value != groups[-1][-1] + step or len(groups[-1]) >= max_size:
            groups.append([value])
        else:
            groups[-1].append(value)
    return groups


class MultiTimeframeSync:
    def __init__(self, repository: object, rest_client: object, sync_plan: dict | None,
                 config: DBSyncConfig, *, health: MarketDataHealth | None = None) -> None:
        self.repository = repository
        self.rest_client = rest_client
        self.sync_plan = sync_plan or config.sync_plan
        self.config = config
        self.health = health or MarketDataHealth()

    def warmup_symbol(self, symbol: str) -> SyncReport:
        report = SyncReport(symbol=symbol, target_timeframes=list(self.config.enabled_timeframes))
        now_ms = self._server_time_ms()
        for timeframe in self.config.enabled_timeframes:
            limit = self.config.warmup_limits.get(timeframe, 0)
            if limit <= 0: continue
            duration = timeframe_to_milliseconds(timeframe)
            latest_open = (now_ms // duration) * duration - duration
            expected = [latest_open - duration * offset for offset in range(limit - 1, -1, -1)]
            expected = [value for value in expected if value >= 0]
            self._reconcile_into(report, symbol, timeframe, expected, closed_through_ms=now_ms)
        return self._finish(report)

    def sync_boundary(self, symbol: str, boundary_event: BoundaryEvent) -> SyncReport:
        tasks = build_sync_tasks_for_boundary(symbol, boundary_event.timeframe,
                                               boundary_event.open_time_ms, self.sync_plan)
        report = SyncReport(symbol=symbol, boundary_timeframe=boundary_event.timeframe,
            target_timeframes=[task.target_timeframe for task in tasks],
            boundary_open_time_ms=boundary_event.open_time_ms,
            boundary_close_time_ms=boundary_event.close_time_ms)
        for task in tasks:
            self._reconcile_into(report, symbol, task.target_timeframe, task.expected_open_times,
                                 closed_through_ms=boundary_event.close_time_ms + 1)
        return self._finish(report)

    def reconcile_timeframe(self, symbol: str, timeframe: str,
                            expected_open_times: list[int]) -> SyncReport:
        report = SyncReport(symbol=symbol, target_timeframes=[timeframe])
        self._reconcile_into(report, symbol, timeframe, expected_open_times,
                             closed_through_ms=int(time.time() * 1000))
        return self._finish(report)

    def _reconcile_into(self, report: SyncReport, symbol: str, timeframe: str,
                        expected: Sequence[int], *, closed_through_ms: int) -> None:
        expected = sorted(set(expected))
        report.tasks_total += 1
        report.expected_candles += len(expected)
        try:
            missing = self.repository.find_missing_open_times(symbol, timeframe, expected)
            report.existing_candles += len(expected) - len(missing)
            report.missing_before += len(missing)
            report.used_websocket_existing_data |= len(expected) > len(missing)
            if missing and self.config.allow_rest_recovery:
                report.used_rest_recovery = True
                duration = timeframe_to_milliseconds(timeframe)
                expected_set = set(missing)
                recovered = []
                for group in _contiguous_groups(missing, duration, self.config.max_rest_limit):
                    candles = self.rest_client.fetch_klines(symbol=symbol, timeframe=timeframe,
                        start_time_ms=group[0], end_time_ms=group[-1] + duration - 1,
                        limit=min(len(group), self.config.max_rest_limit))
                    report.rest_calls += 1
                    valid = [c for c in candles if c.is_closed and c.open_time_ms in expected_set
                             and c.close_time_ms < closed_through_ms]
                    report.downloaded_candles += len(valid)
                    recovered.extend(valid)
                if recovered:
                    report.upserted_candles += self.repository.upsert_candles(recovered)
            missing_after = self.repository.find_missing_open_times(symbol, timeframe, expected)
            report.missing_after += len(missing_after)
            if missing_after: report.tasks_failed += 1
            else: report.tasks_success += 1
        except Exception as exc:
            report.tasks_failed += 1
            report.missing_after += len(expected)
            report.errors.append(f"{timeframe}: {exc}")

    def _finish(self, report: SyncReport) -> SyncReport:
        report.finish()
        if report.missing_after or report.errors: self.health.degraded("database candle gaps remain")
        elif report.tasks_total: self.health.ok()
        report.health_status = self.health.status.value
        return report

    def _server_time_ms(self) -> int:
        method = getattr(self.rest_client, "fetch_server_time_ms", None)
        return int(method()) if method else int(time.time() * 1000)
