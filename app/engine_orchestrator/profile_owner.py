"""Cross-process PostgreSQL singleton ownership for non-default trade profiles."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Callable
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.engine_orchestrator.trade_profile import resolve_trade_profile


class ProfileOwnerError(RuntimeError):
    pass


class OwnerAlreadyActiveError(ProfileOwnerError):
    pass


class ProfileOwnershipLostError(ProfileOwnerError):
    pass


def advisory_lock_key(profile_id: str) -> int:
    """Return one stable signed bigint key derived only from the public profile ID."""
    profile = resolve_trade_profile(profile_id)
    raw = hashlib.sha256(
        f"traders-ml:orchestrator-owner:v1:{profile.trade_profile_id}".encode("utf-8")
    ).digest()[:8]
    return int.from_bytes(raw, byteorder="big", signed=True)


@dataclass(frozen=True, slots=True)
class ProfileOwnerStatus:
    profile_id: str
    mode: str
    owner_state: str
    owner_instance_id: str
    backend_process_id: int | None
    mechanism: str = "POSTGRESQL_SESSION_ADVISORY_LOCK"
    heartbeat_model: str = "LIVE_DEDICATED_DB_SESSION"
    expiry_model: str = "SESSION_DEATH_RELEASES_LOCK"


class PostgresProfileOwner:
    """Own a profile for the lifetime of one dedicated PostgreSQL session."""

    def __init__(self, session_factory: Callable[[], Session], profile_id: str, *,
                 owner_instance_id: str | None = None) -> None:
        self.profile = resolve_trade_profile(profile_id)
        self.owner_instance_id = owner_instance_id or f"profile-owner-{uuid4()}"
        self.lock_key = advisory_lock_key(self.profile.trade_profile_id)
        self._session_factory = session_factory
        self._session: Session | None = None
        self._connection: Connection | None = None
        self._backend_process_id: int | None = None
        self._state = "NOT_ACQUIRED"

    @property
    def session(self) -> Session:
        if self._session is None:
            raise ProfileOwnershipLostError("profile owner has no live session")
        return self._session

    @property
    def acquired(self) -> bool:
        return self._state == "ACQUIRED"

    def acquire(self) -> None:
        if self._state != "NOT_ACQUIRED":
            raise ProfileOwnerError("profile owner acquisition is single-use")
        probe = self._session_factory()
        try:
            engine = probe.get_bind()
        finally:
            probe.close()
        connection = engine.connect()
        session = Session(bind=connection, expire_on_commit=False)
        try:
            if connection.dialect.name != "postgresql":
                raise ProfileOwnerError("profile singleton requires PostgreSQL")
            row = session.execute(text(
                "SELECT pg_try_advisory_lock(:lock_key), pg_backend_pid()"
            ), {"lock_key": self.lock_key}).one()
            session.commit()
            if not bool(row[0]):
                self._state = "OWNER_ALREADY_ACTIVE"
                raise OwnerAlreadyActiveError(
                    f"OWNER_ALREADY_ACTIVE:{self.profile.trade_profile_id}"
                )
            self._session = session
            self._connection = connection
            self._backend_process_id = int(row[1])
            self._state = "ACQUIRED"
        except Exception:
            if self._state != "ACQUIRED":
                session.close()
                connection.close()
            raise

    def assert_active(self, mutation_session: Session | None = None) -> None:
        if self._state != "ACQUIRED" or self._session is None:
            raise ProfileOwnershipLostError(
                f"PROFILE_OWNERSHIP_NOT_ACTIVE:{self.profile.trade_profile_id}"
            )
        if mutation_session is not None and mutation_session is not self._session:
            raise ProfileOwnershipLostError("authoritative mutation is not on owner session")
        try:
            backend_pid = int(self._session.scalar(text("SELECT pg_backend_pid()")))
            if backend_pid != self._backend_process_id:
                raise ProfileOwnershipLostError("profile owner DB session changed")
            unsigned_key = self.lock_key & ((1 << 64) - 1)
            class_id = unsigned_key >> 32
            object_id = unsigned_key & 0xFFFFFFFF
            held = bool(self._session.scalar(text(
                "SELECT EXISTS (SELECT 1 FROM pg_locks "
                "WHERE locktype = 'advisory' AND pid = pg_backend_pid() "
                "AND granted AND classid = :class_id AND objid = :object_id "
                "AND objsubid = 1)"
            ), {"class_id": class_id, "object_id": object_id}))
            if not held:
                raise ProfileOwnershipLostError("profile advisory lock is no longer held")
        except ProfileOwnershipLostError:
            self._state = "LOST"
            raise
        except Exception as exc:
            self._state = "LOST"
            raise ProfileOwnershipLostError(
                f"profile ownership verification failed: {type(exc).__name__}"
            ) from exc

    def status(self) -> ProfileOwnerStatus:
        return ProfileOwnerStatus(
            profile_id=self.profile.trade_profile_id,
            mode=self.profile.mode,
            owner_state=self._state,
            owner_instance_id=self.owner_instance_id,
            backend_process_id=self._backend_process_id,
        )

    def close(self) -> None:
        session = self._session
        connection = self._connection
        self._session = None
        self._connection = None
        if session is None:
            return
        try:
            if self._state == "ACQUIRED":
                session.execute(
                    text("SELECT pg_advisory_unlock(:lock_key)"),
                    {"lock_key": self.lock_key},
                )
                session.commit()
        finally:
            session.close()
            if connection is not None:
                connection.close()
            self._state = "RELEASED"

    def invalidate_session_for_test(self) -> None:
        """Model abrupt connection death for isolated lifecycle acceptance only."""
        if self._session is None:
            return
        connection = self._connection
        if connection is None:
            return
        connection.invalidate()
        self._session.close()
        connection.close()
        self._session = None
        self._connection = None
        self._state = "LOST"

    def __enter__(self) -> "PostgresProfileOwner":
        self.acquire()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
