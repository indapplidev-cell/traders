"""Small observable state for the online runner."""

from dataclasses import dataclass


@dataclass(slots=True)
class OnlineAnalysisState:
    received_windows: int = 0
    analyzed_windows: int = 0
    skipped_windows: int = 0
    error_windows: int = 0
