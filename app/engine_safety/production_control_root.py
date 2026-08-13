"""Shared production PAPER control-root resolution.

Production services run in the same container namespace and must observe the
same bind-mounted control state.  Host-side tools intentionally keep their
separate explicit CLI default in ``paper_production_control``.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Final


PRODUCTION_CONTROL_ROOT_KEY: Final = "TRADERS_PRODUCTION_CONTROL_ROOT"
PRODUCTION_CONTROL_ROOT_DEFAULT: Final = PurePosixPath("/run/traders-control")


def resolve_production_control_root(
    environment: Mapping[str, str] | None = None,
) -> Path:
    """Resolve one absolute container control root, failing closed on drift."""

    values = os.environ if environment is None else environment
    raw = values.get(PRODUCTION_CONTROL_ROOT_KEY, str(PRODUCTION_CONTROL_ROOT_DEFAULT))
    candidate = PurePosixPath(raw)
    if not candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("PRODUCTION_CONTROL_ROOT_INVALID")
    return Path(str(candidate))


__all__ = [
    "PRODUCTION_CONTROL_ROOT_DEFAULT",
    "PRODUCTION_CONTROL_ROOT_KEY",
    "resolve_production_control_root",
]
