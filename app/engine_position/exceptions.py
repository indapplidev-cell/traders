"""Safe domain exceptions carrying stable reason codes."""


class PositionError(Exception):
    def __init__(self, *reason_codes: str, message: str | None = None) -> None:
        self.reason_codes = tuple(dict.fromkeys(str(value) for value in reason_codes))
        super().__init__(message or (self.reason_codes[0] if self.reason_codes else "POSITION_ERROR"))


class PositionContractError(PositionError):
    pass

class PositionStoreError(PositionError):
    pass
