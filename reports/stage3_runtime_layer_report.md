# Stage 3 Runtime Layer Report

## 1. Status
- Stage 3 local runtime layer implemented and validated against local PostgreSQL.
- Status is local-only. Production-ready status was not assigned.

## 2. Branch
- `stage3-runtime-layer`

## 3. Commit hash
- Stage 3 commit hash was not assigned at report creation time.
- Branch HEAD before Stage 3 commit: `daa37767be5d531aeb7d4e502d327b3e890e5ca4`

## 4. Created files
- `alembic/versions/0004_strategy_audit.py`
- `app/runtime/__init__.py`
- `app/runtime/strategy_runtime.py`
- `app/strategy/strategy_context.py`
- `app/strategy/strategy_registry.py`
- `tests/test_risk_gate.py`
- `tests/test_strategy_cli.py`
- `tests/test_strategy_registry.py`
- `tests/test_strategy_runtime.py`
- `reports/stage3_runtime_layer_report.md`

## 5. Modified files
- `.env.example`
- `app/cli/commands.py`
- `app/config/settings.py`
- `app/db/models.py`
- `app/execution/paper_step_service.py`
- `app/journal/trade_journal.py`
- `app/risk/risk_manager.py`
- `app/strategy/base_strategy.py`
- `app/strategy/simple_trend_strategy.py`
- `tests/conftest.py`
- `tests/test_cli.py`
- `tests/test_settings.py`

## 6. New CLI commands
- `strategy-list`
- `strategy-run`
- `strategy-loop`

## 7. Strategy contract
- Added `StrategyDecision` with `strategy_name`, `strategy_version`, `symbol`, `interval`, `action`, `reason`, `confidence`, `metadata`.
- Added `BaseStrategy.decide(context) -> StrategyDecision`.
- Added `StrategyContext` as a ready-to-use runtime input object.
- `SimpleTrendStrategy` now implements the new strategy contract and keeps backward-compatible `evaluate(...)` for Stage 1/2 flows.

## 8. Strategy runtime flow
- `StrategyRuntime.run_tick(...)` loads candles from DB.
- If candles are missing, runtime can fetch them through the existing public `CandleService`.
- Runtime calculates indicators, detects market regime, builds `StrategyContext`, executes strategy decision, applies risk gate, runs paper-only execution, writes journal row, and returns a bounded result object.
- `StrategyRuntime.run_loop(...)` stops after exact `ticks` and rejects invalid loop bounds.

## 9. Risk gate changes
- Added runtime-aware `validate_strategy_decision(...)`.
- `HOLD` is always approved.
- Low-confidence action below `STRATEGY_MIN_CONFIDENCE` is converted to `HOLD` with `low_confidence` reason.
- Duplicate `BUY`, `SELL` without open position, max open positions, and insufficient balance are rejected.
- Existing Stage 1/2 paper-step contract was kept through `validate_decision(...)`.

## 10. Paper execution behavior
- Runtime uses only the existing paper execution engine.
- No live orders were added.
- No Binance private API client was added.
- No futures, margin, leverage, or short execution were added.

## 11. Journal behavior
- `trade_decisions` now stores `strategy_name`, `strategy_version`, and `confidence`.
- Runtime writes strategy metadata into the existing trade journal.
- Existing legacy journal writes remain supported through default values.

## 12. Migrations
- Added Alembic migration `0004_strategy_audit`.
- Local PostgreSQL check:
  - `.venv\Scripts\alembic upgrade head`: success, `0003_runner_state -> 0004_strategy_audit`
  - `.venv\Scripts\alembic current`: `0004_strategy_audit (head)`
- Direct PostgreSQL checks:
  - `alembic_version.version_num = 0004_strategy_audit`
  - `trade_decisions` contains columns `strategy_name`, `strategy_version`, `confidence`

## 13. Tests
- `.venv\Scripts\python -m pytest`: `67 passed in 5.87s`
- `.venv\Scripts\python -m ruff check .`: `All checks passed!`
- Added Stage 3 tests for:
  - strategy registry
  - strategy runtime
  - strategy CLI
  - risk gate

## 14. Checks
- `docker ps`: `traders_postgres` was `Up` and `healthy`
- `docker exec traders_postgres pg_isready -U traders -d traders`: `accepting connections`
- `.venv\Scripts\python -m app.cli.commands health`: `OK: app loaded`, `OK: database connected`
- `.venv\Scripts\python -m app.cli.commands async-health`: `OK: async database connected`
- `.venv\Scripts\python -m app.cli.commands strategy-list`: listed `simple_trend`
- `.venv\Scripts\python -m app.cli.commands strategy-run --strategy simple_trend --symbol BTCUSDT --interval 15m`:
  - strategy action: `SELL`
  - final action: `HOLD`
  - risk approved: `False`
  - risk reason: `Нельзя выполнить SELL: открытая позиция отсутствует.`
  - execution action: `SKIPPED`
  - candles used: `300`
  - market regime: `BEAR`
  - journal id: `2`
- `.venv\Scripts\python -m app.cli.commands strategy-loop --strategy simple_trend --symbol BTCUSDT --interval 15m --ticks 3 --sleep-seconds 0`:
  - loop stopped after exactly `3` ticks
  - all 3 ticks returned `SELL -> HOLD`
  - all 3 ticks returned `risk approved = False`
  - journal ids: `3`, `4`, `5`
- `.venv\Scripts\python -m app.cli.commands portfolio`:
  - `USDT balance = 1000.0000000000`
  - `open positions = 0`
  - `realized pnl = 0`

## 15. What was not done
- Live trading was not implemented.
- Binance private API was not implemented.
- Real orders were not implemented.
- Futures, margin, leverage were not implemented.
- Telegram, FastAPI, and GUI were not implemented.
- Infinite runner without tick limit was not implemented.

## 16. Pending
- VPS deploy is still pending because the server is unavailable for SSH runtime work.
- Server-side runtime validation is still pending for the same reason.
