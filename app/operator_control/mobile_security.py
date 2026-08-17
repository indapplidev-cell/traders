"""Device-bound authentication for the separate TLS-only mobile Control profile."""

from __future__ import annotations

import base64
import hashlib
import json
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol
from uuid import UUID

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import Request
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db.paper_models import ControlMobileDeviceRecord, ControlMobileReplayNonceRecord

from .auth import OperatorAuthError
from .config import (
    REPLAY_RETENTION_SECONDS,
    SIGNED_REQUEST_MAX_AGE_SECONDS,
    SIGNED_REQUEST_MAX_FUTURE_SKEW_SECONDS,
)


SCHEME = "traders-control-mobile-v1"
ALGORITHM = "ECDSA_P256_SHA256"
HEADER_SCHEME = "x-traders-control-scheme"
HEADER_DEVICE_ID = "x-traders-device-id"
HEADER_KEY_VERSION = "x-traders-key-version"
HEADER_ISSUED_AT = "x-traders-issued-at"
HEADER_NONCE = "x-traders-nonce"
HEADER_REQUEST_ID = "x-traders-request-id"
HEADER_ACTION = "x-traders-action"
HEADER_EXPECTED_GENERATION = "x-traders-expected-generation"
HEADER_SIGNATURE = "x-traders-signature"
NONCE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{22,128}$")
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$")


@dataclass(frozen=True, slots=True)
class MobileDevice:
    device_id: str
    public_key_spki: bytes
    public_key_fingerprint: str
    algorithm: str
    key_version: int
    enabled: bool
    created_at: datetime
    revoked_at: datetime | None = None
    label: str | None = None


@dataclass(frozen=True, slots=True)
class SignedRequestEnvelope:
    scheme: str
    device_id: str
    key_version: int
    method: str
    path: str
    query: str
    body_sha256: str
    issued_at: int
    nonce: str
    request_id: str
    action: str
    expected_generation: str

    def canonical_bytes(self) -> bytes:
        fields = (
            self.scheme,
            self.device_id,
            str(self.key_version),
            self.method,
            self.path,
            self.query,
            self.body_sha256,
            str(self.issued_at),
            self.nonce,
            self.request_id,
            self.action,
            self.expected_generation,
        )
        output = bytearray()
        for value in fields:
            encoded = value.encode("utf-8")
            output.extend(f"{len(encoded):08x}:".encode("ascii"))
            output.extend(encoded)
        return bytes(output)


class MobileSecurityStore(Protocol):
    def get_device(self, device_id: str) -> MobileDevice | None: ...

    def claim_nonce(
        self, *, device_id: str, nonce: str, issued_at: datetime,
        expires_at: datetime, request_id: str, action: str, accepted_at: datetime,
    ) -> bool: ...

    def cleanup_expired(self, now: datetime, *, limit: int = 500) -> int: ...


class SqlAlchemyMobileSecurityStore:
    def __init__(self, sessions: sessionmaker[Session] | Callable[[], Session]) -> None:
        self._sessions = sessions

    def get_device(self, device_id: str) -> MobileDevice | None:
        with self._sessions() as session:
            row = session.get(ControlMobileDeviceRecord, device_id)
            if row is None:
                return None
            return MobileDevice(
                device_id=row.device_id,
                public_key_spki=bytes(row.public_key_spki),
                public_key_fingerprint=row.public_key_fingerprint,
                algorithm=row.algorithm,
                key_version=row.key_version,
                enabled=row.enabled,
                created_at=row.created_at,
                revoked_at=row.revoked_at,
                label=row.label,
            )

    def register_device(
        self, *, device_id: str, public_key_spki: bytes, key_version: int = 1,
        label: str | None = None, created_at: datetime | None = None,
    ) -> MobileDevice:
        _validate_device_material(device_id, public_key_spki, key_version)
        now = (created_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
        fingerprint = hashlib.sha256(public_key_spki).hexdigest()
        with self._sessions() as session:
            if session.get(ControlMobileDeviceRecord, device_id) is not None:
                raise ValueError("MOBILE_DEVICE_ALREADY_EXISTS")
            session.add(ControlMobileDeviceRecord(
                device_id=device_id, public_key_spki=public_key_spki,
                public_key_fingerprint=fingerprint, algorithm=ALGORITHM,
                key_version=key_version, enabled=True, label=label,
                created_at=now, revoked_at=None,
            ))
            session.commit()
        return self.get_device(device_id)  # type: ignore[return-value]

    def revoke_device(self, device_id: str, *, revoked_at: datetime | None = None) -> None:
        with self._sessions() as session:
            row = session.get(ControlMobileDeviceRecord, device_id)
            if row is None:
                raise ValueError("MOBILE_DEVICE_UNKNOWN")
            row.enabled = False
            row.revoked_at = (revoked_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
            session.commit()

    def rotate_device_key(
        self, *, device_id: str, public_key_spki: bytes, new_key_version: int,
    ) -> MobileDevice:
        _validate_device_material(device_id, public_key_spki, new_key_version)
        with self._sessions() as session:
            row = session.get(ControlMobileDeviceRecord, device_id)
            if row is None:
                raise ValueError("MOBILE_DEVICE_UNKNOWN")
            if new_key_version != row.key_version + 1:
                raise ValueError("MOBILE_KEY_VERSION_INVALID")
            row.public_key_spki = public_key_spki
            row.public_key_fingerprint = hashlib.sha256(public_key_spki).hexdigest()
            row.key_version = new_key_version
            row.enabled = True
            row.revoked_at = None
            session.commit()
        return self.get_device(device_id)  # type: ignore[return-value]

    def claim_nonce(self, **values: object) -> bool:
        try:
            with self._sessions() as session:
                session.add(ControlMobileReplayNonceRecord(**values))
                session.commit()
            return True
        except IntegrityError:
            return False

    def cleanup_expired(self, now: datetime, *, limit: int = 500) -> int:
        with self._sessions() as session:
            keys = session.execute(
                select(
                    ControlMobileReplayNonceRecord.device_id,
                    ControlMobileReplayNonceRecord.nonce,
                )
                .where(ControlMobileReplayNonceRecord.expires_at < now)
                .limit(limit)
            ).all()
            if not keys:
                return 0
            count = 0
            for device_id, nonce in keys:
                count += session.execute(
                    delete(ControlMobileReplayNonceRecord).where(
                        ControlMobileReplayNonceRecord.device_id == device_id,
                        ControlMobileReplayNonceRecord.nonce == nonce,
                    )
                ).rowcount or 0
            session.commit()
            return count


class InMemoryMobileSecurityStore:
    """Deterministic isolated-test store; never valid for the production profile."""

    def __init__(self, devices: tuple[MobileDevice, ...] = ()) -> None:
        self.devices = {device.device_id: device for device in devices}
        self.claims: set[tuple[str, str]] = set()
        self._lock = threading.Lock()

    def get_device(self, device_id: str) -> MobileDevice | None:
        return self.devices.get(device_id)

    def claim_nonce(self, **values: object) -> bool:
        key = (str(values["device_id"]), str(values["nonce"]))
        with self._lock:
            if key in self.claims:
                return False
            self.claims.add(key)
            return True

    def cleanup_expired(self, now: datetime, *, limit: int = 500) -> int:
        return 0


@dataclass(frozen=True, slots=True)
class MobileDevicePrincipal:
    device_id: str
    key_version: int
    public_key_fingerprint: str
    request_id: str
    action: str
    expected_generation: int | None
    nonce_fingerprint: str


class MobileRequestVerifier:
    def __init__(
        self,
        store: MobileSecurityStore,
        *,
        clock: Callable[[], datetime] | None = None,
        max_age_seconds: int = SIGNED_REQUEST_MAX_AGE_SECONDS,
        max_future_skew_seconds: int = SIGNED_REQUEST_MAX_FUTURE_SKEW_SECONDS,
        replay_retention_seconds: int = REPLAY_RETENTION_SECONDS,
    ) -> None:
        if max_age_seconds <= 0 or max_future_skew_seconds < 0:
            raise ValueError("MOBILE_AUTH_PROFILE_INVALID")
        if replay_retention_seconds <= max_age_seconds + max_future_skew_seconds:
            raise ValueError("MOBILE_REPLAY_RETENTION_INVALID")
        self._store = store
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._max_age = max_age_seconds
        self._future_skew = max_future_skew_seconds
        self._retention = replay_retention_seconds

    async def authenticate(
        self, request: Request, *, expected_action: str, mutation: bool
    ) -> MobileDevicePrincipal:
        envelope, signature, body = await self._parse(request, expected_action, mutation)
        device = self._store.get_device(envelope.device_id)
        if device is None:
            raise OperatorAuthError(401, "MOBILE_DEVICE_UNKNOWN")
        if not device.enabled or device.revoked_at is not None:
            raise OperatorAuthError(401, "MOBILE_DEVICE_REVOKED")
        if device.key_version != envelope.key_version:
            raise OperatorAuthError(401, "MOBILE_KEY_VERSION_INVALID")
        if device.algorithm != ALGORITHM:
            raise OperatorAuthError(401, "MOBILE_ALGORITHM_UNSUPPORTED")

        now = self._clock().astimezone(timezone.utc)
        issued = datetime.fromtimestamp(envelope.issued_at, tz=timezone.utc)
        if issued < now - timedelta(seconds=self._max_age):
            raise OperatorAuthError(401, "MOBILE_REQUEST_EXPIRED")
        if issued > now + timedelta(seconds=self._future_skew):
            raise OperatorAuthError(401, "MOBILE_REQUEST_FUTURE_SKEW")
        if hashlib.sha256(body).hexdigest() != envelope.body_sha256:
            raise OperatorAuthError(401, "MOBILE_SIGNATURE_INVALID")

        try:
            key = serialization.load_der_public_key(device.public_key_spki)
            if not isinstance(key, ec.EllipticCurvePublicKey) or not isinstance(key.curve, ec.SECP256R1):
                raise ValueError
            key.verify(signature, envelope.canonical_bytes(), ec.ECDSA(hashes.SHA256()))
        except (ValueError, TypeError, InvalidSignature):
            raise OperatorAuthError(401, "MOBILE_SIGNATURE_INVALID") from None

        if mutation:
            accepted_at = self._clock().astimezone(timezone.utc)
            if not self._store.claim_nonce(
                device_id=device.device_id,
                nonce=envelope.nonce,
                issued_at=issued,
                expires_at=issued + timedelta(seconds=self._retention),
                request_id=envelope.request_id,
                action=envelope.action,
                accepted_at=accepted_at,
            ):
                raise OperatorAuthError(409, "MOBILE_REPLAY_DETECTED")
        return MobileDevicePrincipal(
            device_id=device.device_id,
            key_version=device.key_version,
            public_key_fingerprint=device.public_key_fingerprint,
            request_id=envelope.request_id,
            action=envelope.action,
            expected_generation=(int(envelope.expected_generation) if envelope.expected_generation else None),
            nonce_fingerprint=hashlib.sha256(envelope.nonce.encode("ascii")).hexdigest()[:16],
        )

    async def _parse(
        self, request: Request, expected_action: str, mutation: bool
    ) -> tuple[SignedRequestEnvelope, bytes, bytes]:
        headers = request.headers
        required = (
            HEADER_SCHEME, HEADER_DEVICE_ID, HEADER_KEY_VERSION, HEADER_ISSUED_AT,
            HEADER_NONCE, HEADER_REQUEST_ID, HEADER_ACTION, HEADER_EXPECTED_GENERATION,
            HEADER_SIGNATURE,
        )
        if any(headers.get(name) is None for name in required):
            raise OperatorAuthError(401, "MOBILE_AUTH_MISSING")
        if headers[HEADER_SCHEME] != SCHEME:
            raise OperatorAuthError(401, "MOBILE_AUTH_PROFILE_INVALID")
        try:
            UUID(headers[HEADER_DEVICE_ID], version=4)
            key_version = int(headers[HEADER_KEY_VERSION])
            issued_at = int(headers[HEADER_ISSUED_AT])
            signature = _decode_base64url(headers[HEADER_SIGNATURE], 512)
        except (ValueError, TypeError):
            raise OperatorAuthError(401, "MOBILE_AUTH_MISSING") from None
        nonce = headers[HEADER_NONCE]
        request_id = headers[HEADER_REQUEST_ID]
        action = headers[HEADER_ACTION]
        generation = headers[HEADER_EXPECTED_GENERATION]
        if (
            key_version < 1
            or not NONCE_PATTERN.fullmatch(nonce)
            or not REQUEST_ID_PATTERN.fullmatch(request_id)
            or action != expected_action
        ):
            raise OperatorAuthError(401, "MOBILE_SIGNATURE_INVALID")
        body = await request.body()
        if mutation:
            try:
                parsed = json.loads(body)
                parsed_generation = parsed["expected_generation"]
                parsed_request_id = parsed["request_id"]
                if not generation or int(generation) != parsed_generation or request_id != parsed_request_id:
                    raise ValueError
            except (ValueError, TypeError, KeyError, json.JSONDecodeError):
                raise OperatorAuthError(401, "MOBILE_SIGNATURE_INVALID") from None
        elif generation:
            raise OperatorAuthError(401, "MOBILE_SIGNATURE_INVALID")
        raw_path = request.scope.get("raw_path", request.url.path.encode("ascii"))
        raw_query = request.scope.get("query_string", b"")
        try:
            path = bytes(raw_path).decode("ascii")
            query = bytes(raw_query).decode("ascii")
        except UnicodeDecodeError:
            raise OperatorAuthError(401, "MOBILE_SIGNATURE_INVALID") from None
        envelope = SignedRequestEnvelope(
            scheme=SCHEME,
            device_id=headers[HEADER_DEVICE_ID],
            key_version=key_version,
            method=request.method.upper(),
            path=path,
            query=query,
            body_sha256=hashlib.sha256(body).hexdigest(),
            issued_at=issued_at,
            nonce=nonce,
            request_id=request_id,
            action=action,
            expected_generation=generation,
        )
        return envelope, signature, body


def _decode_base64url(value: str, maximum: int) -> bytes:
    if len(value) > maximum or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _validate_device_material(device_id: str, public_key_spki: bytes, key_version: int) -> None:
    try:
        UUID(device_id, version=4)
        key = serialization.load_der_public_key(public_key_spki)
    except (ValueError, TypeError):
        raise ValueError("MOBILE_DEVICE_KEY_INVALID") from None
    if (
        key_version < 1
        or not isinstance(key, ec.EllipticCurvePublicKey)
        or not isinstance(key.curve, ec.SECP256R1)
    ):
        raise ValueError("MOBILE_DEVICE_KEY_INVALID")
