"""Execution-intent errors. They never represent exchange failures."""


class ExecutionError(Exception):
    """Base error for the local execution-intent boundary."""


class ExecutionContractError(ExecutionError):
    """Raised when a model cannot satisfy its immutable contract."""


class LiveExecutionDisabledError(ExecutionError):
    """Raised by the permanently disabled live boundary."""

    reason_code = "LIVE_EXECUTION_DISABLED"
