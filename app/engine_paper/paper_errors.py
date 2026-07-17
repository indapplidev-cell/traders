"""ENGINE-PAPER-01 contract errors."""


class PaperContractError(ValueError):
    pass


class PaperLevelError(ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason
