from datetime import datetime, timezone

import pytest

from app.server_api.repositories.protocols import ApiRepositories
from app.server_api.repositories.records import TradingUniverseSymbolReadinessRecord
from app.server_api.services.query_service import ApiQueryService
from app.server_api.settings import ApiSettings
from app.trading_universe import (
    ACTIVE_TRADING_UNIVERSE,
    PREPARED_NEXT_TRADING_UNIVERSE,
    TARGET_TIMEFRAMES,
    bind_new_canary,
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
    assert PREPARED_NEXT_TRADING_UNIVERSE.version_id == "trading-universe-v2"
    assert PREPARED_NEXT_TRADING_UNIVERSE.symbols == (
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
        "LINKUSDT", "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "SUIUSDT",
    )
    assert ACTIVE_TRADING_UNIVERSE.activation_state == "ACTIVE"
    assert PREPARED_NEXT_TRADING_UNIVERSE.activation_state == "PREPARED_NOT_ACTIVE"


def test_market_data_plan_is_exactly_60_unique_deterministic_streams():
    first = market_data_streams()
    assert first == market_data_streams()
    assert len(first) == len(set(first)) == 60
    assert first[:6] == tuple(("BTCUSDT", timeframe) for timeframe in TARGET_TIMEFRAMES)
    assert first[-6:] == tuple(("SUIUSDT", timeframe) for timeframe in TARGET_TIMEFRAMES)


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
    assert envelope.data.target_symbol_count == 10
    assert envelope.data.ready_market_data_streams == 60
    assert [item.trading_activation_state for item in envelope.data.symbols[:3]] == ["ACTIVE"] * 3
    assert [item.trading_activation_state for item in envelope.data.symbols[3:]] == ["PREPARED_NOT_ACTIVE"] * 7
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
    assert tuple(data.active_symbols) == PREPARED_NEXT_TRADING_UNIVERSE.symbols
    assert {item.trading_activation_state for item in data.symbols} == {"ACTIVE"}
