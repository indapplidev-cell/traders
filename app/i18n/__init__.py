"""Server-authoritative product internationalization."""

from .service import (
    CATALOG_VERSION,
    CONTENT_HASH,
    DEFAULT_LOCALE,
    SCHEMA_VERSION,
    SUPPORTED_LOCALES,
    catalog_payload,
    locale_content_hash,
    manifest_payload,
    validate_catalogs,
)

__all__ = [
    "CATALOG_VERSION", "CONTENT_HASH", "DEFAULT_LOCALE", "SCHEMA_VERSION",
    "SUPPORTED_LOCALES", "catalog_payload", "locale_content_hash", "manifest_payload", "validate_catalogs",
]
