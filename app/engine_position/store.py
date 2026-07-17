"""Thread-safe, process-local position store."""
from __future__ import annotations
from abc import ABC, abstractmethod
from threading import RLock
from app.engine_position.enums import PositionReasonCode as R
from app.engine_position.events import PositionEvent
from app.engine_position.exceptions import PositionStoreError
from app.engine_position.models import Position, PositionTransitionResult, TERMINAL_STATUSES


class PositionStore(ABC):
    @abstractmethod
    def create(self, position: Position) -> Position: ...
    @abstractmethod
    def get(self, position_id: str) -> Position | None: ...
    @abstractmethod
    def get_by_position_key(self, position_key: str) -> Position | None: ...
    @abstractmethod
    def apply_event(self, position_id: str, event: PositionEvent) -> PositionTransitionResult: ...
    @abstractmethod
    def list_open(self) -> tuple[Position, ...]: ...
    @abstractmethod
    def list_terminal(self) -> tuple[Position, ...]: ...


def _copy(position: Position | None) -> Position | None:
    return None if position is None else Position.from_dict(position.to_dict())


class InMemoryPositionStore(PositionStore):
    def __init__(self) -> None:
        self._positions: dict[str, Position] = {}
        self._keys: dict[str, str] = {}
        self._lock = RLock()

    def create(self, position: Position) -> Position:
        with self._lock:
            if position.position_id in self._positions or position.position_key in self._keys:
                raise PositionStoreError(R.DUPLICATE_POSITION.value)
            self._positions[position.position_id] = _copy(position)  # type: ignore[assignment]
            self._keys[position.position_key] = position.position_id
            return _copy(position)  # type: ignore[return-value]

    def get(self, position_id: str) -> Position | None:
        with self._lock:
            return _copy(self._positions.get(position_id))

    def get_by_position_key(self, position_key: str) -> Position | None:
        with self._lock:
            position_id = self._keys.get(position_key)
            return _copy(self._positions.get(position_id)) if position_id else None

    def apply_event(self, position_id: str, event: PositionEvent) -> PositionTransitionResult:
        from app.engine_position.lifecycle import reduce_event
        with self._lock:
            position = self._positions.get(position_id)
            if position is None:
                raise PositionStoreError(R.POSITION_STORE_CONFLICT.value)
            result = reduce_event(position, event)
            if result.applied:
                self._positions[position_id] = result.position
            return PositionTransitionResult.from_dict(result.to_dict())

    def list_open(self) -> tuple[Position, ...]:
        with self._lock:
            return tuple(_copy(v) for v in self._positions.values()
                         if v.status not in TERMINAL_STATUSES)  # type: ignore[misc]

    def list_terminal(self) -> tuple[Position, ...]:
        with self._lock:
            return tuple(_copy(v) for v in self._positions.values()
                         if v.status in TERMINAL_STATUSES)  # type: ignore[misc]
