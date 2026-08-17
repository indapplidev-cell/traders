from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from ipaddress import ip_address
from pathlib import Path


CONTROL_API_VERSION = "1"
DEFAULT_BIND_HOST = "127.0.0.1"
DEFAULT_PORT = 8766
MAX_REQUEST_BODY_BYTES = 16 * 1024
READONLY_API_PORT = 8765
DEFAULT_MOBILE_PORT = 8767
SIGNED_REQUEST_MAX_AGE_SECONDS = 120
SIGNED_REQUEST_MAX_FUTURE_SKEW_SECONDS = 30
REPLAY_RETENTION_SECONDS = 86_400


class ControlAuthProfile(StrEnum):
    OPERATOR_LOOPBACK_BEARER = "operator_loopback_bearer"
    MOBILE_DEVICE_SIGNED_TLS = "mobile_device_signed_tls"


class PaperOperatorControlOperationMode(StrEnum):
    DISABLED_FOUNDATION = "DISABLED_FOUNDATION"
    ISOLATED_CONTROL_ROOT = "ISOLATED_CONTROL_ROOT"
    PRODUCTION_PAPER = "PRODUCTION_PAPER"


@dataclass(frozen=True, slots=True)
class PaperOperatorControlConfig:
    enabled: bool = False
    operation_mode: PaperOperatorControlOperationMode = (
        PaperOperatorControlOperationMode.DISABLED_FOUNDATION
    )
    bind_host: str = DEFAULT_BIND_HOST
    port: int = DEFAULT_PORT
    environment: str = "PRODUCTION"
    mode: str = "PAPER"
    live_allowed: bool = False
    docs_enabled: bool = False
    max_request_body_bytes: int = MAX_REQUEST_BODY_BYTES
    auth_profile: ControlAuthProfile = ControlAuthProfile.OPERATOR_LOOPBACK_BEARER
    tls_enabled: bool = False
    tls_certificate_path: Path | None = None
    tls_private_key_path: Path | None = None
    tls_chain_path: Path | None = None
    tls_server_identity: str | None = None
    mobile_persistence_configured: bool = False
    allow_test_mobile_plaintext: bool = False

    @classmethod
    def production_paper(cls) -> "PaperOperatorControlConfig":
        """Enable only the authenticated PAPER mutation foundation."""
        return cls(
            enabled=True,
            operation_mode=PaperOperatorControlOperationMode.PRODUCTION_PAPER,
        )

    @classmethod
    def mobile_device_signed_tls(
        cls,
        *,
        bind_host: str,
        port: int = DEFAULT_MOBILE_PORT,
        tls_certificate_path: Path,
        tls_private_key_path: Path,
        tls_server_identity: str,
        tls_chain_path: Path | None = None,
    ) -> "PaperOperatorControlConfig":
        return cls(
            enabled=True,
            operation_mode=PaperOperatorControlOperationMode.PRODUCTION_PAPER,
            bind_host=bind_host,
            port=port,
            auth_profile=ControlAuthProfile.MOBILE_DEVICE_SIGNED_TLS,
            tls_enabled=True,
            tls_certificate_path=tls_certificate_path,
            tls_private_key_path=tls_private_key_path,
            tls_chain_path=tls_chain_path,
            tls_server_identity=tls_server_identity,
            mobile_persistence_configured=True,
        )

    @property
    def mutation_foundation_enabled(self) -> bool:
        return (
            self.enabled
            and self.operation_mode is not PaperOperatorControlOperationMode.DISABLED_FOUNDATION
            and self.environment == "PRODUCTION"
            and self.mode == "PAPER"
            and not self.live_allowed
        )

    def __post_init__(self) -> None:
        try:
            address = ip_address(self.bind_host)
        except ValueError as error:
            raise ValueError("CONTROL_EXTERNAL_BIND_DENIED") from error
        is_test_mobile = (
            self.auth_profile is ControlAuthProfile.MOBILE_DEVICE_SIGNED_TLS
            and self.environment == "TEST"
        )
        if self.auth_profile is ControlAuthProfile.OPERATOR_LOOPBACK_BEARER:
            if not address.is_loopback or self.bind_host != DEFAULT_BIND_HOST:
                raise ValueError("CONTROL_EXTERNAL_BIND_DENIED")
            if self.tls_enabled or self.allow_test_mobile_plaintext:
                raise ValueError("CONTROL_AUTH_PROFILE_INVALID")
        elif self.auth_profile is ControlAuthProfile.MOBILE_DEVICE_SIGNED_TLS:
            if (
                (self.environment == "PRODUCTION" and (not address.is_private or address.is_loopback))
                or (is_test_mobile and not address.is_loopback)
            ):
                raise ValueError("CONTROL_EXTERNAL_BIND_DENIED")
            if not self.mobile_persistence_configured:
                raise ValueError("CONTROL_MOBILE_PERSISTENCE_REQUIRED")
            if not self.tls_enabled and not self.allow_test_mobile_plaintext:
                raise ValueError("MOBILE_TLS_REQUIRED")
            if self.tls_enabled and (
                self.tls_certificate_path is None
                or self.tls_private_key_path is None
                or not self.tls_server_identity
            ):
                raise ValueError("MOBILE_TLS_REQUIRED")
            if self.allow_test_mobile_plaintext and not is_test_mobile:
                raise ValueError("MOBILE_TLS_REQUIRED")
        else:
            raise ValueError("CONTROL_AUTH_PROFILE_INVALID")
        if not 1 <= self.port <= 65535 or self.port == READONLY_API_PORT:
            raise ValueError("CONTROL_PORT_INVALID_OR_CONFLICTING")
        if (self.environment != "PRODUCTION" and not is_test_mobile) or self.mode != "PAPER":
            raise ValueError("INVALID_CONTROL_TARGET")
        if self.live_allowed:
            raise ValueError("LIVE_NOT_ALLOWED")
        if not 1024 <= self.max_request_body_bytes <= MAX_REQUEST_BODY_BYTES:
            raise ValueError("INVALID_REQUEST_BODY_LIMIT")
        if (
            self.operation_mode is PaperOperatorControlOperationMode.DISABLED_FOUNDATION
            and self.enabled
        ):
            raise ValueError("DISABLED_FOUNDATION_CANNOT_BE_ENABLED")
