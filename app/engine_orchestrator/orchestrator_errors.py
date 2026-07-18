"""Errors owned by the online coordination layer."""


class OrchestratorError(RuntimeError):
    pass


class SnapshotNotEnoughDataError(OrchestratorError):
    def __init__(self, counts: dict[str, int], required: dict[str, int]) -> None:
        self.counts = counts
        self.required = required
        super().__init__(f"not enough closed candles: available={counts}, required={required}")


class SnapshotContractViolationError(OrchestratorError):
    """The freshly loaded DB snapshot violates a causal boundary invariant."""


class SafetyViolationError(OrchestratorError):
    pass
