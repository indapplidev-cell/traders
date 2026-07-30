from __future__ import annotations

from dataclasses import FrozenInstanceError, asdict
from datetime import datetime, timezone
import json

import pytest

from app.engine_paper.controlled_runtime import (
    MAX_ALLOWED_SYMBOLS,
    MAX_CONFIGURATION_FILE_BYTES,
    PAPER_CONTROLLED_RUNTIME_CONFIGURATION_CONTRACT_VERSION,
    PaperControlledRuntimeAction,
    PaperControlledRuntimeConfiguration,
    PaperControlledRuntimeConfigurationLoader,
    PaperControlledRuntimeOutcome,
    PaperControlledRuntimeTarget,
    PaperDatabaseAccessMode,
)
from app.engine_paper.controlled_worker import PaperLifecycleCycleScope
from app.engine_safety import ExecutionMode


def _mapping(**changes):
    values = {
        "contract_version": PAPER_CONTROLLED_RUNTIME_CONFIGURATION_CONTRACT_VERSION,
        "runtime_action": "VALIDATE_CONFIGURATION",
        "target": "CONFIGURATION_ONLY",
        "execution_mode": "OFF",
        "runtime_enabled": False,
        "dry_run_enabled": True,
        "explicit_paper_authorization": False,
        "cycle_scope": "ADVANCE_ONE_LIFECYCLE_STEP",
        "max_stages_per_cycle": 1,
        "allowed_symbols": [],
        "market_data_input_mode": "SUPPLIED_ONLY",
        "database_access_mode": "NONE",
        "network_access_allowed": False,
        "polling_allowed": False,
        "scheduler_allowed": False,
        "daemon_allowed": False,
        "configuration_id": "runtime:loader:test",
    }
    values.update(changes)
    return values


def test_configuration_safe_defaults_are_exact_and_immutable():
    configuration = PaperControlledRuntimeConfiguration()
    assert configuration.runtime_action is PaperControlledRuntimeAction.VALIDATE_CONFIGURATION
    assert configuration.target is PaperControlledRuntimeTarget.CONFIGURATION_ONLY
    assert configuration.execution_mode is ExecutionMode.OFF
    assert configuration.runtime_enabled is False
    assert configuration.dry_run_enabled is True
    assert configuration.explicit_paper_authorization is False
    assert configuration.cycle_scope is PaperLifecycleCycleScope.ADVANCE_ONE_LIFECYCLE_STEP
    assert configuration.max_stages_per_cycle == 1
    assert configuration.allowed_symbols == ()
    assert configuration.network_access_allowed is False
    assert configuration.polling_allowed is False
    assert configuration.scheduler_allowed is False
    assert configuration.daemon_allowed is False
    with pytest.raises(FrozenInstanceError):
        configuration.runtime_enabled = True


VALID_SYMBOLS = tuple(
    [f"A{i:02d}USDT" for i in range(80)]
    + [f"B{i:02d}BTC" for i in range(40)]
    + ["BTCUSDT", "ETHUSDT", "BNBBTC", "1000SHIBUSDT"]
)


@pytest.mark.parametrize("symbol", VALID_SYMBOLS)
def test_each_normalized_binance_style_symbol_is_accepted(symbol):
    result = PaperControlledRuntimeConfigurationLoader().load_mapping(
        _mapping(allowed_symbols=[symbol])
    )
    assert result.outcome is PaperControlledRuntimeOutcome.CONFIGURATION_VALID
    assert result.configuration is not None
    assert result.configuration.allowed_symbols == (symbol,)


INVALID_SYMBOLS = tuple(
    ["", "*", "BTC*", "BTC/USDT", "btc-usdt", "_BTC", "A", "A" * 33]
    + [f"BTC USDT{i}" for i in range(24)]
    + [f"BTC_USDT{i}" for i in range(24)]
)


@pytest.mark.parametrize("symbol", INVALID_SYMBOLS)
def test_each_invalid_or_wildcard_symbol_is_rejected(symbol):
    result = PaperControlledRuntimeConfigurationLoader().load_mapping(
        _mapping(allowed_symbols=[symbol])
    )
    assert result.outcome is PaperControlledRuntimeOutcome.INVALID_CONFIGURATION
    assert result.configuration is None


@pytest.mark.parametrize("count", tuple(range(MAX_ALLOWED_SYMBOLS + 1)))
def test_allowlist_is_bounded_and_preserves_explicit_order(count):
    symbols = [f"X{i:02d}USDT" for i in range(count)]
    result = PaperControlledRuntimeConfigurationLoader().load_mapping(
        _mapping(allowed_symbols=symbols)
    )
    assert result.outcome is PaperControlledRuntimeOutcome.CONFIGURATION_VALID
    assert result.configuration.allowed_symbols == tuple(symbols)


def test_allowlist_over_hard_bound_is_rejected():
    symbols = [f"X{i:02d}USDT" for i in range(MAX_ALLOWED_SYMBOLS + 1)]
    result = PaperControlledRuntimeConfigurationLoader().load_mapping(
        _mapping(allowed_symbols=symbols)
    )
    assert result.outcome is PaperControlledRuntimeOutcome.INVALID_CONFIGURATION


@pytest.mark.parametrize("symbol", ("BTCUSDT", "ETHUSDT", "BNBBTC", "A00USDT"))
def test_duplicate_normalized_symbol_is_rejected(symbol):
    result = PaperControlledRuntimeConfigurationLoader().load_mapping(
        _mapping(allowed_symbols=[symbol.lower(), symbol])
    )
    assert result.outcome is PaperControlledRuntimeOutcome.INVALID_CONFIGURATION


SECRET_FIELDS = (
    "password",
    "PASSWORD",
    "pass-word",
    "secret",
    "Secret",
    "token",
    "TOKEN",
    "api_key",
    "API-KEY",
    "api.secret",
    "api_secret",
    "database_url",
    "DATABASE-URL",
    "database_uri",
    "authorization_header",
    "Authorization Header",
    "private_key",
    "PRIVATE-KEY",
)


@pytest.mark.parametrize("field_name", SECRET_FIELDS)
@pytest.mark.parametrize("nesting", ("top", "nested"))
def test_secret_looking_field_names_are_rejected_without_value_derivation(
    field_name, nesting
):
    source = _mapping()
    if nesting == "top":
        source[field_name] = object()
    else:
        source["allowed_symbols"] = [{"safe": {field_name: object()}}]
    result = PaperControlledRuntimeConfigurationLoader().load_mapping(source)
    assert result.outcome is PaperControlledRuntimeOutcome.SENSITIVE_FIELD_FORBIDDEN
    assert result.configuration is None
    assert all("object at" not in reason for reason in result.reason_codes)


@pytest.mark.parametrize("field_name", tuple(f"unknown_field_{i}" for i in range(36)))
def test_unknown_top_level_field_is_rejected(field_name):
    result = PaperControlledRuntimeConfigurationLoader().load_mapping(
        _mapping(**{field_name: i if (i := len(field_name)) else 0})
    )
    assert result.outcome is PaperControlledRuntimeOutcome.UNKNOWN_CONFIGURATION_FIELD


def test_missing_and_unsupported_contract_versions_are_distinct():
    missing = _mapping()
    del missing["contract_version"]
    loader = PaperControlledRuntimeConfigurationLoader()
    assert loader.load_mapping(missing).outcome is PaperControlledRuntimeOutcome.CONTRACT_VERSION_MISSING
    assert (
        loader.load_mapping(_mapping(contract_version="UNSUPPORTED")).outcome
        is PaperControlledRuntimeOutcome.UNSUPPORTED_CONTRACT_VERSION
    )


def test_json_loader_requires_explicit_existing_path(tmp_path):
    loader = PaperControlledRuntimeConfigurationLoader()
    assert (
        loader.load_json_file(tmp_path / "missing.json").outcome
        is PaperControlledRuntimeOutcome.CONFIGURATION_FILE_NOT_FOUND
    )


def test_json_loader_accepts_one_utf8_object_and_rejects_trailing_ambiguity(tmp_path):
    path = tmp_path / "safe.json"
    path.write_text(json.dumps(_mapping()), encoding="utf-8")
    assert (
        PaperControlledRuntimeConfigurationLoader().load_json_file(path).outcome
        is PaperControlledRuntimeOutcome.CONFIGURATION_VALID
    )
    path.write_text(json.dumps(_mapping()) + "\n{}", encoding="utf-8")
    assert (
        PaperControlledRuntimeConfigurationLoader().load_json_file(path).outcome
        is PaperControlledRuntimeOutcome.INVALID_CONFIGURATION
    )


def test_json_loader_rejects_duplicate_keys(tmp_path):
    path = tmp_path / "duplicate.json"
    path.write_text(
        '{"contract_version":"PAPER_CONTROLLED_RUNTIME_CONFIGURATION_V1",'
        '"contract_version":"PAPER_CONTROLLED_RUNTIME_CONFIGURATION_V1"}',
        encoding="utf-8",
    )
    assert (
        PaperControlledRuntimeConfigurationLoader().load_json_file(path).outcome
        is PaperControlledRuntimeOutcome.DUPLICATE_CONFIGURATION_KEY
    )


def test_json_loader_rejects_non_utf8(tmp_path):
    path = tmp_path / "non-utf8.json"
    path.write_bytes(b"\xff\xfe{}")
    assert (
        PaperControlledRuntimeConfigurationLoader().load_json_file(path).outcome
        is PaperControlledRuntimeOutcome.CONFIGURATION_NOT_UTF8
    )


def test_json_loader_rejects_oversized_file_before_parsing(tmp_path):
    path = tmp_path / "oversized.json"
    path.write_bytes(b"{" + b" " * MAX_CONFIGURATION_FILE_BYTES + b"}")
    assert (
        PaperControlledRuntimeConfigurationLoader().load_json_file(path).outcome
        is PaperControlledRuntimeOutcome.CONFIGURATION_TOO_LARGE
    )


def test_loader_does_not_require_created_at_and_accepts_explicit_utc_timestamp():
    default = PaperControlledRuntimeConfigurationLoader().load_mapping(_mapping())
    assert default.configuration.created_at is None
    timestamp = datetime(2026, 7, 30, tzinfo=timezone.utc)
    explicit = PaperControlledRuntimeConfigurationLoader().load_mapping(
        _mapping(created_at=timestamp)
    )
    assert explicit.configuration.created_at == timestamp
