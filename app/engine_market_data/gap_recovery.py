"""REST-backed gap recovery without synthetic data."""

from dataclasses import dataclass
from typing import Protocol

from app.engine_market_data.candle import Candle
from app.engine_market_data.candle_store import CandleStore
from app.engine_market_data.market_data_health import MarketDataHealth
from app.engine_market_data.market_symbol import normalize_market_symbol
from app.engine_market_data.timeframe import timeframe_to_milliseconds


class KlineFetcher(Protocol):
    def fetch_klines(
        self, symbol: str, timeframe: str, start_time_ms: int | None = None,
        end_time_ms: int | None = None, limit: int = 1000,
    ) -> list[Candle]: ...


@dataclass(frozen=True, slots=True)
class GapRecoveryReport:
    symbol: str
    timeframe: str
    requested_missing_count: int
    recovered_count: int
    unrecovered_open_times: list[int]
    success: bool


class GapRecovery:
    def __init__(self, rest_client: KlineFetcher, store: CandleStore, health: MarketDataHealth | None = None) -> None:
        self.rest_client = rest_client
        self.store = store
        self.health = health or store.health

    def recover(
        self, symbol: str, timeframe: str, missing_open_times: list[int] | tuple[int, ...]
    ) -> GapRecoveryReport:
        symbol = normalize_market_symbol(symbol)
        step = timeframe_to_milliseconds(timeframe)
        missing = sorted(set(missing_open_times))
        if not missing:
            return GapRecoveryReport(symbol, timeframe, 0, 0, [], True)
        self.health.recovering()
        recovered: set[int] = set()
        try:
            for group in self._contiguous_groups(missing, step):
                candles = self.rest_client.fetch_klines(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_time_ms=group[0],
                    end_time_ms=group[-1] + step - 1,
                    limit=min(1000, len(group)),
                )
                wanted = set(group)
                for candle in candles:
                    if (
                        candle.is_closed and candle.symbol == symbol and candle.timeframe == timeframe
                        and candle.open_time_ms in wanted
                    ):
                        self.store.upsert_candle(candle)
                        recovered.add(candle.open_time_ms)
        except Exception:
            self.health.degraded("REST recovery failed")
        unrecovered = [open_time for open_time in missing if open_time not in recovered]
        success = not unrecovered
        if success:
            self.health.ok()
        else:
            self.health.degraded("unrecovered gap")
        return GapRecoveryReport(symbol, timeframe, len(missing), len(recovered), unrecovered, success)

    recover_missing = recover

    @staticmethod
    def _contiguous_groups(values: list[int], step: int) -> list[list[int]]:
        groups: list[list[int]] = []
        for value in values:
            if not groups or value != groups[-1][-1] + step:
                groups.append([value])
            else:
                groups[-1].append(value)
        return groups
