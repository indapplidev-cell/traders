"""Read-only HTTP API v1.

Importing a low-level observation module must not build the HTTP factory or
validate unrelated trading-profile configuration.  Production repositories are
still injected explicitly when :func:`create_app` is requested.
"""

from typing import Any

__all__ = ["create_app"]


def __getattr__(name: str) -> Any:
    if name == "create_app":
        from .app_factory import create_app
        return create_app
    raise AttributeError(name)
