"""Deterministic validation, hashing, and public export for product i18n."""

from __future__ import annotations

from hashlib import sha256
import json
from string import Formatter
from typing import Final, Mapping

from .catalog import CATALOGS, Locale

SCHEMA_VERSION: Final = "traders-i18n/1"
DEFAULT_LOCALE: Final = Locale.RU.value
SUPPORTED_LOCALES: Final = tuple(locale.value for locale in Locale)
MAX_KEYS: Final = 2_000
MAX_KEY_LENGTH: Final = 160
MAX_VALUE_LENGTH: Final = 4_096


def _placeholders(value: str) -> frozenset[str]:
    try:
        return frozenset(
            field_name.split(".", 1)[0].split("[", 1)[0]
            for _, field_name, _, _ in Formatter().parse(value)
            if field_name
        )
    except ValueError as exc:
        raise ValueError("invalid translation placeholder syntax") from exc


def validate_catalogs(catalogs: Mapping[Locale, Mapping[str, str]] = CATALOGS) -> None:
    if set(catalogs) != set(Locale):
        raise ValueError("catalog locales must exactly match supported locales")
    reference_keys: set[str] | None = None
    reference: Mapping[str, str] | None = None
    for locale in Locale:
        catalog = catalogs[locale]
        if not 0 < len(catalog) <= MAX_KEYS:
            raise ValueError("catalog key count is outside the public bound")
        keys = set(catalog)
        if reference_keys is None:
            reference_keys, reference = keys, catalog
        elif keys != reference_keys:
            raise ValueError("RU/EN catalog key parity failed")
        for key, value in catalog.items():
            if not isinstance(key, str) or not key or len(key) > MAX_KEY_LENGTH or "." not in key:
                raise ValueError("translation keys must be bounded and namespaced")
            if not isinstance(value, str) or not value.strip() or len(value) > MAX_VALUE_LENGTH:
                raise ValueError("translation values must be non-empty bounded strings")
            if reference is not None and _placeholders(value) != _placeholders(reference[key]):
                raise ValueError(f"placeholder parity failed for {key}")


def _public_content() -> dict[str, object]:
    validate_catalogs()
    return {
        "schema_version": SCHEMA_VERSION,
        "default_locale": DEFAULT_LOCALE,
        "supported_locales": list(SUPPORTED_LOCALES),
        "catalogs": {
            locale.value: dict(sorted(CATALOGS[locale].items())) for locale in Locale
        },
    }


def _canonical_bytes() -> bytes:
    return json.dumps(
        _public_content(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


CONTENT_HASH: Final = sha256(_canonical_bytes()).hexdigest()
CATALOG_VERSION: Final = f"i18n-{CONTENT_HASH[:16]}"


def locale_content_hash(locale: Locale | str) -> str:
    selected = Locale(locale)
    content = json.dumps(
        dict(sorted(CATALOGS[selected].items())),
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return sha256(content).hexdigest()


def manifest_payload() -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "catalog_version": CATALOG_VERSION,
        "content_hash": CONTENT_HASH,
        "default_locale": DEFAULT_LOCALE,
        "supported_locales": list(SUPPORTED_LOCALES),
        "locale_hashes": {locale.value: locale_content_hash(locale) for locale in Locale},
    }


def catalog_payload(locale: str) -> dict[str, object]:
    selected = Locale(locale)
    return {
        "locale": selected.value,
        "schema_version": SCHEMA_VERSION,
        "catalog_version": CATALOG_VERSION,
        "content_hash": CONTENT_HASH,
        "locale_content_hash": locale_content_hash(selected),
        "translations": dict(sorted(CATALOGS[selected].items())),
    }
