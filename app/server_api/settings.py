from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ApiSettings:
    api_version: str = "v1"
    default_page_limit: int = 50
    dashboard_run_limit: int = 20
    primary_timeframe: str = "15m"

    def __post_init__(self) -> None:
        if self.api_version != "v1":
            raise ValueError("only API v1 is supported")
        if not 1 <= self.default_page_limit <= 100:
            raise ValueError("default_page_limit must be within 1..100")
        if not 1 <= self.dashboard_run_limit <= 100:
            raise ValueError("dashboard_run_limit must be within 1..100")
