from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
from pathlib import Path
from urllib.parse import urlencode

import pytest

from app.config.trade_parameters import load_trade_parameters
from app.engine_paper.binance_account_commission import (
    BinanceAccountCommissionClient,
    BinanceAccountCommissionManager,
    BinanceCredentials,
    PROVIDER_VERSION,
    commission_runtime_status,
    parse_commission_response,
    read_credentials,
)
from app.engine_paper.scalping_paper_runner import (
    BinancePublicScalpingCostSource,
    read_binance_commission_snapshot,
)
from app.engine_market_data.binance_public_rest import BinancePublicRestClient
from app.engine_orchestrator.orchestrator_config import OrchestratorConfig
from app.engine_orchestrator.orchestrator_daemon import OrchestratorDaemon


def response(symbol="BTCUSDT", *, special="0", tax="0", discount="0.75"):
    return {
        "symbol": symbol,
        "standardCommission": {
            "maker": "0.0008", "taker": "0.0010",
            "buyer": "0.0001", "seller": "0.0002",
        },
        "specialCommission": {
            "maker": special, "taker": special, "buyer": special, "seller": special,
        },
        "taxCommission": {
            "maker": tax, "taker": tax, "buyer": tax, "seller": tax,
        },
        "discount": {
            "enabledForAccount": True, "enabledForSymbol": True,
            "discountAsset": "BNB", "discount": discount,
        },
    }


class Result:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class SignedTransport:
    def __init__(self):
        self.calls = []
        self.failed = False

    def get(self, url, *, params, headers):
        self.calls.append((url, dict(params), dict(headers)))
        if url.endswith("/api/v3/time"):
            return Result({"serverTime": 1_700_000_000_250})
        if self.failed:
            raise OSError("private failure without credential text")
        return Result(response(str(params["symbol"])))


class PublicTransport:
    def get(self, url, *, params=None):
        if url.endswith("bookTicker"):
            return Result({"bidPrice": "99.9", "bidQty": "2", "askPrice": "100.1", "askQty": "2"})
        return Result({"bids": [["99.9", "2"]], "asks": [["100.1", "2"]]})


def test_credentials_parse_json_key_value_and_two_line_without_echo(tmp_path):
    values = (
        '{"api_key":"A' + '1' * 31 + '","api_secret":"S' + '2' * 31 + '"}',
        "API_KEY=A" + "1" * 31 + "\nAPI_SECRET=S" + "2" * 31,
        "Binance API key A" + "1" * 63 + "\nBinance API secret S" + "2" * 63,
        "A" + "1" * 31 + "\nS" + "2" * 31,
    )
    for index, value in enumerate(values):
        path = tmp_path / f"secret-{index}"
        path.write_text(value, encoding="utf-8")
        parsed = read_credentials(path)
        assert parsed.api_key.startswith("A") and parsed.secret_key.startswith("S")
    bad = tmp_path / "bad"
    bad.write_text("secret-value-that-must-not-appear", encoding="utf-8")
    with pytest.raises(RuntimeError) as error:
        read_credentials(bad)
    assert "secret-value" not in str(error.value)


def test_signed_user_data_adapter_uses_exact_endpoint_header_and_hmac():
    transport = SignedTransport()
    credentials = BinanceCredentials("api-key-123456789", "secret-key-123456789")
    client = BinanceAccountCommissionClient(
        credentials, transport=transport, clock_ms=lambda: 1_700_000_000_000,
    )
    assert client.fetch("BTCUSDT")["symbol"] == "BTCUSDT"
    assert transport.calls[0][0].endswith("/api/v3/time")
    url, params, headers = transport.calls[1]
    assert url.endswith("/api/v3/account/commission")
    assert headers == {"X-MBX-APIKEY": credentials.api_key}
    assert params["timestamp"] == 1_700_000_000_250
    unsigned = {key: value for key, value in params.items() if key != "signature"}
    expected = hmac.new(
        credentials.secret_key.encode(), urlencode(unsigned).encode(), hashlib.sha256
    ).hexdigest()
    assert params["signature"] == expected
    assert credentials.secret_key not in json.dumps((url, params, headers))


def test_parser_preserves_standard_special_tax_discount_and_effective_rates():
    value = parse_commission_response(
        "BTCUSDT", response(special="0.00001", tax="0.00002"),
        entry_role="TAKER", exit_role="MAKER",
    )
    assert value["standard_commission"]["seller"] == "0.0002"
    assert value["special_commission"]["taker"] == "0.00001"
    assert value["tax_commission"]["buyer"] == "0.00002"
    assert value["discount"] == {
        "enabled_for_account": True, "enabled_for_symbol": True,
        "asset": "BNB", "value": "0.75",
    }
    assert float(value["effective_entry_fee_bps"]) == pytest.approx(9.6)
    assert float(value["effective_exit_fee_bps"]) == pytest.approx(8.1)
    assert float(value["round_trip_fee_bps"]) == pytest.approx(17.7)


def manager(tmp_path, current, transport, symbols=("BTCUSDT", "ETHUSDT")):
    return BinanceAccountCommissionManager(
        BinanceAccountCommissionClient(
            BinanceCredentials("api-key-123456789", "secret-key-123456789"),
            transport=transport, clock_ms=lambda: int(current[0].timestamp() * 1000),
        ),
        tmp_path / "commission.json", symbols, clock=lambda: current[0],
    )


def test_manager_refreshes_active_symbol_universe_atomically_and_cache_is_low_frequency(tmp_path):
    current = [datetime(2026, 9, 6, tzinfo=timezone.utc)]
    transport = SignedTransport()
    value = manager(tmp_path, current, transport)
    refreshed = value.ensure_fresh(force=True)
    assert refreshed.status == "READY"
    assert refreshed.active_symbols == refreshed.ready_symbols == 2
    assert refreshed.queried_symbols == 2
    assert refreshed.real_account_data and not refreshed.stub_active
    assert len(transport.calls) == 3
    cached = value.ensure_fresh()
    assert cached.status == "READY" and cached.queried_symbols == 0
    assert len(transport.calls) == 3
    payload = json.loads(value.snapshot_path.read_text(encoding="utf-8"))
    assert set(payload["symbols"]) == {"BTCUSDT", "ETHUSDT"}
    assert payload["provider_version"] == PROVIDER_VERSION


def test_orchestrator_cycle_runs_low_frequency_commission_maintenance(tmp_path):
    calls = []

    class NoWindows:
        def get_unprocessed_closed_windows(self, _symbol):
            return []

    daemon = OrchestratorDaemon(
        OrchestratorConfig(
            symbols=("BTCUSDT",), trade_profile_id="trade-5m-v2",
            primary_timeframe="5m", required_timeframes=("5m", "15m", "1h", "4h"),
            minimum_windows={"5m": 1, "15m": 1, "1h": 1, "4h": 1},
            health_report_path=tmp_path / "health.json",
        ),
        NoWindows(), object(), object(), object(),
        cycle_maintenance=lambda: calls.append("freshness-checked"),
    )
    assert daemon.run_cycle(dry_run=True) == []
    assert calls == ["freshness-checked"]


def test_refresh_failure_uses_valid_cache_then_fails_closed_after_ttl(tmp_path):
    current = [datetime(2026, 9, 6, tzinfo=timezone.utc)]
    transport = SignedTransport()
    value = manager(tmp_path, current, transport)
    assert value.ensure_fresh(force=True).status == "READY"
    transport.failed = True
    current[0] += timedelta(hours=2)
    assert value.ensure_fresh(force=True).status == "CACHED_READY"
    current[0] += timedelta(days=2)
    expired = value.ensure_fresh(force=True)
    assert expired.status == "FEE_SOURCE_NOT_READY"
    assert expired.ready_symbols == 0 and not expired.real_account_data


def test_reconnect_and_symbol_universe_change_refresh(tmp_path):
    current = [datetime(2026, 9, 6, tzinfo=timezone.utc)]
    transport = SignedTransport()
    first = manager(tmp_path, current, transport, ("BTCUSDT",))
    assert first.ensure_fresh(force=True).status == "READY"
    transport.failed = True
    current[0] += timedelta(hours=2)
    assert first.ensure_fresh(force=True).status == "CACHED_READY"
    transport.failed = False
    current[0] += timedelta(minutes=5)
    assert first.ensure_fresh(force=True).status == "READY"
    changed = manager(tmp_path, current, transport, ("BTCUSDT", "SUIUSDT"))
    assert changed.ensure_fresh().ready_symbols == 2
    assert set(json.loads(changed.snapshot_path.read_text())["symbols"]) == {"BTCUSDT", "SUIUSDT"}


def test_cost_model_consumes_real_snapshot_and_exposes_nonsecret_provenance(tmp_path, monkeypatch):
    current = [datetime.now(timezone.utc)]
    transport = SignedTransport()
    authority = manager(tmp_path, current, transport, ("BTCUSDT",))
    assert authority.ensure_fresh(force=True).status == "READY"
    monkeypatch.setenv("TRADERS_BINANCE_COMMISSION_SNAPSHOT_PATH", str(authority.snapshot_path))
    source = BinancePublicScalpingCostSource(
        client=BinancePublicRestClient(transport=PublicTransport(), max_retries=0),
        commission_manager=authority, clock=lambda: current[0],
    )
    value = source.load("BTCUSDT", 100, safety_margin_bps=0)
    assert value.commission_authoritative is True
    assert value.fee_source == "BINANCE_ACCOUNT_COMMISSION_SNAPSHOT"
    assert value.fee_source_status == "READY"
    assert value.entry_fee_bps == value.exit_fee_bps == pytest.approx(9.0)
    assert value.commission_provenance["source"] == "BINANCE_ACCOUNT_COMMISSION"
    serialized = json.dumps(value.commission_provenance)
    assert "api-key" not in serialized and "secret-key" not in serialized


def test_stub_never_becomes_active_and_runtime_status_is_real_only(tmp_path, monkeypatch):
    stub = tmp_path / "stub.json"
    stub.write_text(json.dumps({
        "snapshot_type": "USER_AUTHORIZED_STUB", "snapshot_id": "stub",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "symbols": {"BTCUSDT": {"maker_bps": 10, "taker_bps": 10}},
    }), encoding="utf-8")
    monkeypatch.setenv("TRADERS_BINANCE_COMMISSION_SNAPSHOT_PATH", str(stub))
    assert read_binance_commission_snapshot("BTCUSDT").status == "STUB_FORBIDDEN"
    status = commission_runtime_status(stub)
    assert status["status"] == "FEE_SOURCE_NOT_READY"
    assert status["real_account_data"] is False and status["stub_active"] is False


def test_central_config_rejects_stub_and_contradictory_freshness(tmp_path):
    source = Path("config/trading/trade_parameters.yaml").read_text(encoding="utf-8")
    bad_stub = tmp_path / "stub.yaml"
    bad_stub.write_text(source.replace("allow_stub_fallback: false", "allow_stub_fallback: true"), encoding="utf-8")
    with pytest.raises(RuntimeError):
        load_trade_parameters(bad_stub)
    bad_age = tmp_path / "age.yaml"
    bad_age.write_text(source.replace("max_snapshot_age_seconds: 86400", "max_snapshot_age_seconds: 60"), encoding="utf-8")
    with pytest.raises(RuntimeError):
        load_trade_parameters(bad_age)
