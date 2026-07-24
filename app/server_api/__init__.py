"""Read-only HTTP API v1.

Importing this package never creates a database session, opens a socket, or
starts background work. Production repositories must be injected explicitly.
"""

from .app_factory import create_app

__all__ = ["create_app"]
