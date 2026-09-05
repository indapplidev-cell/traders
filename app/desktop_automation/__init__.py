"""Read-only Windows desktop automation support for the Traders Tk client."""

from .win32_fallback import (
    BlockingReason,
    CaptureResult,
    PreflightResult,
    ProcessInfo,
    WindowInfo,
    Win32DesktopAutomation,
    capture_mode_for,
    choose_canonical_window,
    evaluate_preflight_blockers,
)

__all__ = [
    "BlockingReason",
    "CaptureResult",
    "PreflightResult",
    "ProcessInfo",
    "WindowInfo",
    "Win32DesktopAutomation",
    "capture_mode_for",
    "choose_canonical_window",
    "evaluate_preflight_blockers",
]
