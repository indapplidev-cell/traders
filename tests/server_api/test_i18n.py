from __future__ import annotations

from hashlib import sha256
import json
from string import Formatter

from fastapi.testclient import TestClient

from app.i18n import CATALOG_VERSION, CONTENT_HASH, catalog_payload, manifest_payload, validate_catalogs
from app.i18n.catalog import EN, RU
from app.i18n.public_codes import PUBLIC_ENUM_NAMESPACES, PUBLIC_LITERAL_CODES, PUBLIC_REASON_CODES, PUBLIC_REASON_ENUMS
from app.server_api import create_app
from scripts.generate_desktop_i18n_bootstrap import build_snapshot
from pathlib import Path


def _fields(value: str) -> frozenset[str]:
    return frozenset(field for _, field, _, _ in Formatter().parse(value) if field)


def test_catalog_schema_key_and_placeholder_parity():
    validate_catalogs()
    assert set(RU) == set(EN)
    assert all("." in key for key in RU)
    assert all(_fields(RU[key]) == _fields(EN[key]) for key in RU)


def test_public_enum_and_reason_coverage_is_complete():
    for namespace, enum_types in PUBLIC_ENUM_NAMESPACES:
        for enum_type in enum_types:
            for member in enum_type:
                assert f"{namespace}.{member.value}" in RU
                assert f"{namespace}.{member.value}" in EN
    for reason in PUBLIC_REASON_CODES:
        assert f"funnel.reason.{reason}" in RU
        assert f"funnel.reason.{reason}" in EN
    assert PUBLIC_REASON_CODES.issuperset(
        member.value for enum_type in PUBLIC_REASON_ENUMS for member in enum_type
    )
    for namespace, codes in PUBLIC_LITERAL_CODES.items():
        for code in codes:
            assert f"{namespace}.{code}" in RU
            assert f"{namespace}.{code}" in EN


def test_catalog_identity_is_deterministic_public_only_and_content_sensitive():
    assert manifest_payload() == manifest_payload()
    assert catalog_payload("ru") == catalog_payload("ru")
    assert CATALOG_VERSION == f"i18n-{CONTENT_HASH[:16]}"
    original = json.dumps(dict(sorted(RU.items())), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    changed = json.dumps({**dict(sorted(RU.items())), "common.refresh": "Изменено"}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert sha256(original.encode()).hexdigest() != sha256(changed.encode()).hexdigest()
    serialized = json.dumps(manifest_payload()).lower()
    assert all(name not in serialized for name in ("database_url", "bearer", "password", "binance_api_key"))


def test_readonly_i18n_routes_and_unknown_locale():
    client = TestClient(create_app())
    manifest = client.get("/api/v1/i18n/manifest")
    assert manifest.status_code == 200
    assert manifest.json() == manifest_payload()
    for locale in ("ru", "en"):
        response = client.get(f"/api/v1/i18n/catalog/{locale}")
        assert response.status_code == 200
        assert response.json() == catalog_payload(locale)
    unknown = client.get("/api/v1/i18n/catalog/de")
    assert unknown.status_code == 422
    assert unknown.json()["error"]["code"] == "INVALID_REQUEST"


def test_i18n_adds_exactly_two_get_routes_and_no_write_or_db_dependency():
    app = create_app()
    paths = app.openapi()["paths"]
    assert len(paths) == 28
    assert all(set(operations).intersection({"get", "post", "put", "patch", "delete"}) == {"get"} for operations in paths.values())
    assert {path for path in paths if "/i18n/" in path} == {
        "/api/v1/i18n/manifest", "/api/v1/i18n/catalog/{locale}",
    }
    assert len(json.dumps(catalog_payload("ru"), ensure_ascii=False).encode("utf-8")) < 1_000_000


def test_generated_desktop_bootstrap_matches_server_catalog():
    path = Path(__file__).resolve().parents[3] / "traders-client" / "src" / "traders_client" / "i18n" / "generated_bootstrap.json"
    assert json.loads(path.read_text(encoding="utf-8")) == build_snapshot()


def test_trade_profile_keys_are_server_owned_and_ru_en_complete():
    ru = catalog_payload("ru")["translations"]
    en = catalog_payload("en")["translations"]
    assert ru["trading.profile.trade_15m.title"] == "Сделка 15м"
    assert en["trading.profile.trade_15m.title"] == "15m Trade"
    assert ru["trading.profile.trade_5m.title"] == "Сделка 5м"
    assert en["trading.profile.trade_5m.title"] == "5m Trade"
    for key in (
        "trading.profile.mode.SHADOW_SEARCH",
        "trading.profile.trade_5m.empty",
        "trading.profile.trade_5m.paper_enabled",
        "trading.profile.conflict.CROSS_TIMEFRAME_CONFLICT",
    ):
        assert key in ru and key in en


def test_trading_funnel_current_freshness_is_server_owned_and_bilingual():
    ru = catalog_payload("ru")["translations"]
    en = catalog_payload("en")["translations"]
    assert ru["market.data.CURRENT"] == "Данные актуальны"
    assert en["market.data.CURRENT"] == "Data current"


def test_trading_funnel_cycle_titles_are_timeframe_parameterized_and_bilingual():
    ru = catalog_payload("ru")["translations"]
    en = catalog_payload("en")["translations"]
    assert ru["funnel.current_cycle"].format(timeframe="5m") == "ТЕКУЩИЙ 5m ЦИКЛ"
    assert ru["funnel.last_completed_cycle"].format(timeframe="5m") == "ПОСЛЕДНИЙ ЗАВЕРШЁННЫЙ 5m ЦИКЛ"
    assert en["funnel.current_cycle"].format(timeframe="5m") == "CURRENT 5m CYCLE"
    assert en["funnel.last_completed_cycle"].format(timeframe="5m") == "LAST COMPLETED 5m CYCLE"


def test_trading_funnel_stage_labels_separate_historical_passage_from_current_eligibility():
    ru = catalog_payload("ru")["translations"]
    en = catalog_payload("en")["translations"]
    assert ru["funnel.stage.VALIDITY_APPROVED"] == "Срок проверен"
    assert ru["funnel.stage.FINAL_APPROVAL"] == "Одобрение создано"
    assert ru["funnel.stage.ELIGIBLE"] == "Допущен сейчас"
    assert en["funnel.stage.VALIDITY_APPROVED"] == "Validity check passed"
    assert en["funnel.stage.FINAL_APPROVAL"] == "Approval created"
    assert en["funnel.stage.ELIGIBLE"] == "Currently eligible"
