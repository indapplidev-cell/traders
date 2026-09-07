"""Artifact paths and atomic JSON operations."""

from .engine import _atomic_json

atomic_json = _atomic_json

__all__ = ["atomic_json"]
