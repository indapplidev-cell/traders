"""UTC-millisecond scheduler emitting each closed boundary once."""

from dataclasses import dataclass

from app.engine_market_data.timeframe import timeframe_to_milliseconds


BOUNDARY_TIMEFRAMES = ("15m", "1h", "4h", "1d")


@dataclass(frozen=True, slots=True)
class BoundaryEvent:
    timeframe: str
    open_time_ms: int
    close_time_ms: int
    detected_at_ms: int

    @property
    def boundary_open_time_ms(self) -> int: return self.open_time_ms
    @property
    def boundary_close_time_ms(self) -> int: return self.close_time_ms


def latest_closed_boundary_open_time(timeframe: str, now_ms: int, safety_delay_ms: int = 2_000) -> int:
    if timeframe not in BOUNDARY_TIMEFRAMES: raise ValueError("unsupported boundary timeframe")
    if now_ms < 0 or safety_delay_ms < 0: raise ValueError("timestamps and delay must be non-negative")
    duration = timeframe_to_milliseconds(timeframe)
    eligible = now_ms - safety_delay_ms
    if eligible < duration: raise ValueError("no closed boundary exists yet")
    return eligible - eligible % duration - duration


def is_closed_boundary(timeframe: str, now_ms: int, safety_delay_ms: int = 2_000) -> bool:
    duration = timeframe_to_milliseconds(timeframe)
    return timeframe in BOUNDARY_TIMEFRAMES and now_ms >= duration + safety_delay_ms and now_ms % duration >= safety_delay_ms


class BoundaryScheduler:
    def __init__(self, *, safety_delay_ms: int = 2_000,
                 timeframes: tuple[str, ...] = BOUNDARY_TIMEFRAMES) -> None:
        if not 1_000 <= safety_delay_ms <= 5_000: raise ValueError("safety delay must be 1-5 seconds")
        self.safety_delay_ms = safety_delay_ms
        self.timeframes = timeframes
        self._emitted: set[tuple[str, int]] = set()

    def due_boundaries(self, now_ms: int) -> list[BoundaryEvent]:
        events = []
        for timeframe in self.timeframes:
            try: open_ms = latest_closed_boundary_open_time(timeframe, now_ms, self.safety_delay_ms)
            except ValueError: continue
            key = (timeframe, open_ms)
            if key in self._emitted: continue
            self._emitted.add(key)
            duration = timeframe_to_milliseconds(timeframe)
            events.append(BoundaryEvent(timeframe, open_ms, open_ms + duration - 1, now_ms))
        return events


_DEFAULT_SCHEDULER = BoundaryScheduler()


def due_boundaries(now_ms: int) -> list[BoundaryEvent]:
    return _DEFAULT_SCHEDULER.due_boundaries(now_ms)
