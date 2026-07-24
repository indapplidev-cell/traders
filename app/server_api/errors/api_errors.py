from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    INVALID_REQUEST = "INVALID_REQUEST"
    INVALID_CURSOR = "INVALID_CURSOR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    CONTRACT_VERSION_UNSUPPORTED = "CONTRACT_VERSION_UNSUPPORTED"
    DATA_NOT_AVAILABLE = "DATA_NOT_AVAILABLE"
    SERVICE_NOT_CONFIGURED = "SERVICE_NOT_CONFIGURED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass(slots=True)
class ApiError(Exception):
    status_code: int
    code: str
    safe_message: str
    details: dict[str, Any] = field(default_factory=dict)
