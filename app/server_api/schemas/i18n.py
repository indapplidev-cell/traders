"""Platform-neutral Readonly i18n response contracts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class I18nManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["traders-i18n/1"]
    catalog_version: str = Field(pattern=r"^i18n-[0-9a-f]{16}$")
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    default_locale: Literal["ru"]
    supported_locales: list[Literal["ru", "en"]]
    locale_hashes: dict[Literal["ru", "en"], str]


class I18nCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")
    locale: Literal["ru", "en"]
    schema_version: Literal["traders-i18n/1"]
    catalog_version: str = Field(pattern=r"^i18n-[0-9a-f]{16}$")
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    locale_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    translations: dict[str, str]
