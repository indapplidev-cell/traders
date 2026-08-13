from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from ipaddress import ip_address


CONTROL_API_VERSION = "1"
DEFAULT_BIND_HOST = "127.0.0.1"
DEFAULT_PORT = 8766
MAX_REQUEST_BODY_BYTES = 16 * 1024
READONLY_API_PORT = 8765


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

    @classmethod
    def production_paper(cls) -> "PaperOperatorControlConfig":
        """Enable only the authenticated PAPER mutation foundation."""
        return cls(
            enabled=True,
            operation_mode=PaperOperatorControlOperationMode.PRODUCTION_PAPER,
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
        if not address.is_loopback or self.bind_host != DEFAULT_BIND_HOST:
            raise ValueError("CONTROL_EXTERNAL_BIND_DENIED")
        if not 1 <= self.port <= 65535 or self.port == READONLY_API_PORT:
            raise ValueError("CONTROL_PORT_INVALID_OR_CONFLICTING")
        if self.environment != "PRODUCTION" or self.mode != "PAPER":
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
