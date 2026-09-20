from datetime import datetime, timezone

import pytest

from app.server_api.repositories.protocols import ApiRepositories
from app.server_api.repositories.records import TradingUniverseSymbolReadinessRecord
from app.server_api.services.query_service import ApiQueryService
from app.server_api.settings import ApiSettings
from app.trading_universe import (
    ACTIVE_TRADING_UNIVERSE,
    LEGACY_TRADING_UNIVERSE_V2,
    PREPARED_NEXT_TRADING_UNIVERSE,
    TARGET_TIMEFRAMES,
    bind_new_canary,
    expand_legacy_scalping_symbols,
    market_data_streams,
)
from app.trading_universe.domain import runtime_universe


class _UniverseRepository:
    def __init__(self, active_version="trading-universe-v1"):
        self.active_version = active_version

    def active_trading_universe(self):
        return runtime_universe(self.active_version)

    def trading_universe_readiness(self):
        return tuple(
            TradingUniverseSymbolReadinessRecord(
                symbol=symbol,
                ready_timeframes=TARGET_TIMEFRAMES,
                history_ready=True,
                analysis_ready=True,
                setup_ready=True,
                strategy_compatible=True,
                risk_compatible=True,
            )
            for symbol in PREPARED_NEXT_TRADING_UNIVERSE.symbols
        )


def test_versioned_active_and_prepared_universes_are_exact_and_distinct():
    assert ACTIVE_TRADING_UNIVERSE.version_id == "trading-universe-v1"
    assert ACTIVE_TRADING_UNIVERSE.symbols == ("BTCUSDT", "ETHUSDT", "SOLUSDT")
    assert PREPARED_NEXT_TRADING_UNIVERSE.version_id == "trading-universe-v3"
    assert PREPARED_NEXT_TRADING_UNIVERSE.symbols == (
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
        "LINKUSDT", "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "SUIUSDT",
        "ZECUSDT", "NEARUSDT", "UNIUSDT", "ENAUSDT", "XLMUSDT",
        "TRXUSDT", "WLDUSDT", "LTCUSDT", "FETUSDT", "FILUSDT",
    )
    assert ACTIVE_TRADING_UNIVERSE.activation_state == "ACTIVE"
    assert PREPARED_NEXT_TRADING_UNIVERSE.activation_state == "PREPARED_NOT_ACTIVE"


def test_market_data_plan_is_exactly_120_unique_deterministic_streams():
    first = market_data_streams()
    assert first == market_data_streams()
    assert len(first) == len(set(first)) == 120
    assert first[:6] == tuple(("BTCUSDT", timeframe) for timeframe in TARGET_TIMEFRAMES)
    assert first[-6:] == tuple(("FILUSDT", timeframe) for timeframe in TARGET_TIMEFRAMES)


def test_deployed_v2_argv_expands_only_for_scalping_v2_and_leaves_15m_unchanged():
    assert expand_legacy_scalping_symbols(LEGACY_TRADING_UNIVERSE_V2.symbols) == PREPARED_NEXT_TRADING_UNIVERSE.symbols
    assert expand_legacy_scalping_symbols(
        LEGACY_TRADING_UNIVERSE_V2.symbols, trade_profile_id="trade-15m-v1"
    ) == LEGACY_TRADING_UNIVERSE_V2.symbols


def test_canary_binding_is_immutable_explicit_and_prepared_version_fails_closed():
    binding = bind_new_canary(
        ACTIVE_TRADING_UNIVERSE.version_id, ACTIVE_TRADING_UNIVERSE.symbols
    )
    assert binding.universe_version_id == ACTIVE_TRADING_UNIVERSE.version_id
    assert binding.allowed_symbols == ACTIVE_TRADING_UNIVERSE.symbols
    with pytest.raises(Exception):
        binding.allowed_symbols += ("BNBUSDT",)
    with pytest.raises(ValueError, match="not active"):
        bind_new_canary(PREPARED_NEXT_TRADING_UNIVERSE.version_id, PREPARED_NEXT_TRADING_UNIVERSE.symbols)


def test_readonly_projection_labels_active_and_prepared_without_controls():
    repository = _UniverseRepository()
    service = ApiQueryService(
        ApiRepositories(
            health=None, markets=None, analysis=None, setups=None, incidents=None,
            dashboard=None, universe=repository,
        ),
        ApiSettings(),
        clock=lambda: datetime(2026, 8, 14, tzinfo=timezone.utc),
    )
    envelope = service.trading_universe()
    assert envelope.data.active_symbol_count == 3
    assert envelope.data.target_symbol_count == 20
    assert envelope.data.ready_market_data_streams == 120
    assert [item.trading_activation_state for item in envelope.data.symbols[:3]] == ["ACTIVE"] * 3
    assert [item.trading_activation_state for item in envelope.data.symbols[3:]] == ["PREPARED_NOT_ACTIVE"] * 17
    assert "activation" not in envelope.model_dump()


def test_readonly_projection_switches_atomically_to_exact_v2():
    repository = _UniverseRepository("trading-universe-v2")
    service = ApiQueryService(
        ApiRepositories(
            health=None, markets=None, analysis=None, setups=None, incidents=None,
            dashboard=None, universe=repository,
        ),
        ApiSettings(),
        clock=lambda: datetime(2026, 8, 14, tzinfo=timezone.utc),
    )
    data = service.trading_universe().data
    assert data.active_universe_version == "trading-universe-v2"
    assert data.active_symbol_count == 10
    assert tuple(data.active_symbols) == LEGACY_TRADING_UNIVERSE_V2.symbols
    assert {item.trading_activation_state for item in data.symbols} == {"ACTIVE", "PREPARED_NOT_ACTIVE"}


def test_readonly_projection_switches_atomically_to_exact_v3():
    repository = _UniverseRepository("trading-universe-v3")
    service = ApiQueryService(
        ApiRepositories(
            health=None, markets=None, analysis=None, setups=None, incidents=None,
            dashboard=None, universe=repository,
        ),
        ApiSettings(),
        clock=lambda: datetime(2026, 9, 20, tzinfo=timezone.utc),
    )
    data = service.trading_universe().data
    assert data.active_universe_version == "trading-universe-v3"
    assert data.active_symbol_count == 20
    assert tuple(data.active_symbols) == PREPARED_NEXT_TRADING_UNIVERSE.symbols
    assert {item.trading_activation_state for item in data.symbols} == {"ACTIVE"}
