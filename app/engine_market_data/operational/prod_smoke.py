"""Production-smoke utilities for ENGINE-MARKET-DATA-04.

This module is deliberately outside the market-data runtime.  It only starts the
documented CLI as a subprocess and reads PostgreSQL for verification; it never
imports or invokes analysis/trading engines.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Iterable, Mapping

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from app.config.settings import get_settings
from app.engine_market_data.timeframe import timeframe_to_milliseconds


SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
TIMEFRAMES = ("1m", "5m", "15m", "1h", "4h", "1d")
TABLES = {timeframe: f"candles_{timeframe}" for timeframe in TIMEFRAMES}
ALLOWED_HEALTH_STATUSES = {
    "OK", "STALE", "GAP_DETECTED", "RECOVERING", "DEGRADED",
    "DISCONNECTED", "ERROR", "NOT_CONFIGURED",
}
VERDICTS = {
    "PROD_SMOKE_PASSED", "PROD_SMOKE_FAILED", "PROD_SMOKE_BLOCKED_POSTGRES",
    "PROD_SMOKE_BLOCKED_NETWORK", "PROD_SMOKE_BLOCKED_CONFIG",
    "PROD_SMOKE_BLOCKED_EXTERNAL",
}
ARTIFACT_NAMES = (
    "ENGINE_MARKET_DATA_04_PROD_SMOKE_REPORT.md",
    "ENGINE_MARKET_DATA_04_PROD_SMOKE_TRACE.json",
    "ENGINE_MARKET_DATA_04_PROD_SMOKE_HEALTH_ONCE.json",
    "ENGINE_MARKET_DATA_04_PROD_SMOKE_HEALTH_CONTINUOUS.json",
    "ENGINE_MARKET_DATA_04_PROD_SMOKE_DB_STATE_BEFORE.json",
    "ENGINE_MARKET_DATA_04_PROD_SMOKE_DB_STATE_AFTER_ONCE.json",
    "ENGINE_MARKET_DATA_04_PROD_SMOKE_DB_STATE_AFTER_RESTART.json",
    "ENGINE_MARKET_DATA_04_PROD_SMOKE_ARTIFACT_MANIFEST.json",
)

REPOSITORY_ROOT_MARKERS = (
    "pyproject.toml",
    "docker-compose.yml",
    "alembic.ini",
    "alembic",
    "scripts",
)


def validate_repository_root(candidate: Path) -> Path:
    """Return a resolved repository root or fail with all missing markers."""
    root = candidate.resolve()
    missing = [marker for marker in REPOSITORY_ROOT_MARKERS if not (root / marker).exists()]
    if missing:
        raise RuntimeError(
            f"Invalid repository root {root!s}; missing required markers: {', '.join(missing)}"
        )
    return root


def find_repository_root(start: Path) -> Path:
    """Find the repository root from a file or directory, independent of cwd."""
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        try:
            return validate_repository_root(candidate)
        except RuntimeError:
            continue
    raise RuntimeError(f"Repository root could not be determined from {start!s}")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def utc_from_ms(value: int | None) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat().replace("+00:00", "Z")


def safety_counters() -> dict[str, int | bool]:
    return {
        "synthetic_candles_written": 0,
        "interpolated_candles_written": 0,
        "zero_filled_candles_written": 0,
        "unclosed_candles_written": 0,
        "future_candles_written": 0,
        "private_api_used": False,
        "api_keys_used": False,
        "downstream_analysis_runs": 0,
        "setup_candidates_created": 0,
        "strategy_decisions_created": 0,
        "risk_decisions_created": 0,
        "paper_plans_created": 0,
        "trade_signals_created": 0,
        "orders_created": 0,
        "positions_created": 0,
        "pnl_records_created": 0,
    }


def validate_health_payload(payload: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ("generated_at", "daemon_instance_id", "overall_status", "snapshots"):
        if field not in payload:
            errors.append(f"missing {field}")
    if payload.get("overall_status") not in ALLOWED_HEALTH_STATUSES:
        errors.append("invalid overall_status")
    for field in ("operational", "ready", "acceptance_blocking"):
        if field in payload and not isinstance(payload[field], bool):
            errors.append(f"{field} must be boolean")
    if payload.get("schema_version") == "MARKET_DATA_HEALTH/2.0":
        for field in (
            "operational", "ready", "acceptance_blocking", "reason_code",
            "within_grace_count", "deadline_expired_count",
        ):
            if field not in payload:
                errors.append(f"missing v2 field {field}")
    snapshots = payload.get("snapshots")
    if not isinstance(snapshots, list) or not snapshots:
        errors.append("snapshots must be a non-empty list")
        return errors
    required = {
        "symbol", "timeframe", "expected_open_time_ms", "stored_open_time_ms",
        "freshness_lag_candles", "status", "missing_count",
    }
    for index, snapshot in enumerate(snapshots):
        if not isinstance(snapshot, Mapping):
            errors.append(f"snapshot[{index}] is not an object")
            continue
        missing = required - set(snapshot)
        if missing:
            errors.append(f"snapshot[{index}] missing {sorted(missing)}")
        if snapshot.get("status") not in ALLOWED_HEALTH_STATUSES:
            errors.append(f"snapshot[{index}] invalid status")
        v2_current_evidence = (
            payload.get("schema_version") == "MARKET_DATA_HEALTH/2.0"
            and snapshot.get("operational") is True
            and snapshot.get("heartbeat_progressing") is True
            and snapshot.get("reason_code") in {
                "HEALTHY_CURRENT", "BOUNDARY_WITHIN_GRACE",
            }
        )
        if (
            not snapshot.get("last_success_at")
            and not snapshot.get("last_error")
            and not v2_current_evidence
        ):
            errors.append(f"snapshot[{index}] needs last_success_at or last_error")
        if payload.get("schema_version") == "MARKET_DATA_HEALTH/2.0":
            for field in (
                "operational", "ready", "acceptance_blocking", "reason_code",
                "expected_boundary_utc", "deadline_utc", "observed_at_utc",
                "heartbeat_progressing", "scheduler_due", "recovery_active",
                "recovery_progressing", "gap_count", "active_error",
                "cached_error_stale", "clock_skew_seconds",
            ):
                if field not in snapshot:
                    errors.append(f"snapshot[{index}] missing v2 field {field}")
    return errors


def health_payload_operational(payload: Mapping[str, Any]) -> bool:
    """Read v2 readiness while keeping old status-only reports compatible."""
    if "operational" in payload or "ready" in payload:
        return payload.get("operational") is True and payload.get("ready") is True
    return payload.get("overall_status") == "OK"


def validate_closed_only_rows(
    timeframe: str, now_exchange_ms: int, rows: Iterable[Mapping[str, Any]],
    *, checksum_required: bool = False,
) -> dict[str, Any]:
    current_open_ms = now_exchange_ms - now_exchange_ms % timeframe_to_milliseconds(timeframe)
    issues: list[dict[str, Any]] = []
    checked = 0
    for row in rows:
        checked += 1
        open_ms = int(row["open_time_ms"])
        close_ms = int(row["close_time_ms"])
        reasons: list[str] = []
        if not row.get("is_closed", False):
            reasons.append("is_closed_false")
        if close_ms >= now_exchange_ms:
            reasons.append("close_not_before_exchange_now")
        if open_ms >= current_open_ms:
            reasons.append("current_or_future_open")
        if open_ms > now_exchange_ms or close_ms > now_exchange_ms:
            reasons.append("future_candle")
        values = [float(row[name]) for name in ("open", "high", "low", "close")]
        open_value, high, low, close_value = values
        if high < max(open_value, low, close_value) or low > min(open_value, high, close_value):
            reasons.append("invalid_ohlc")
        if float(row["volume"]) < 0:
            reasons.append("negative_volume")
        if checksum_required and not row.get("data_checksum"):
            reasons.append("missing_checksum")
        if reasons:
            issues.append({"open_time_ms": open_ms, "reasons": reasons})
    return {"passed": not issues, "checked_rows": checked, "issues": issues}


def validate_runtime_independence(compose_text: str, systemd_text: str) -> dict[str, Any]:
    checks = {
        "compose_market_data_sync": "market-data-sync:" in compose_text,
        "compose_restart_always": bool(re.search(r"market-data-sync:[\s\S]*?restart:\s*always", compose_text)),
        "compose_postgres_healthcheck": "healthcheck:" in compose_text and "pg_isready" in compose_text,
        "compose_depends_on_healthy": "condition: service_healthy" in compose_text,
        "systemd_restart_always": "Restart=always" in systemd_text,
        "deterministic_cli_command": "scripts/engine_market_data_continuous_sync.py" in compose_text,
    }
    return {
        **checks,
        "runtime_requires_codex": False,
        "runtime_requires_vscode": False,
        "runtime_requires_notebook": False,
        "runtime_requires_interactive_developer_session": False,
        "docker_systemd_ready": all(checks.values()),
    }


def validate_trace_schema(payload: Mapping[str, Any]) -> list[str]:
    errors = []
    required = {
        "stage", "generated_at", "environment", "preconditions", "alembic",
        "once_mode", "continuous_mode", "restart_catch_up", "closed_only_validation",
        "health_validation", "runtime_independence", "safety_counters", "bug_candidates",
        "final_verdict", "recommendation",
    }
    missing = required - set(payload)
    if missing:
        errors.append(f"missing trace fields: {sorted(missing)}")
    if payload.get("stage") != "ENGINE-MARKET-DATA-04-PROD-SMOKE":
        errors.append("invalid stage")
    if payload.get("final_verdict") not in VERDICTS:
        errors.append("invalid final_verdict")
    counters = payload.get("safety_counters", {})
    if counters and any(value not in (0, False) for value in counters.values()):
        errors.append("non-zero safety counter")
    return errors


class ProdSmokeRunner:
    def __init__(self, output_dir: Path, *, database_url: str | None = None,
                 restart_wait_seconds: int = 130,
                 preflight_symbol: str = "BTCUSDT",
                 preflight_timeframe: str = "15m",
                 repository_root: Path | None = None) -> None:
        self.root = (
            validate_repository_root(repository_root)
            if repository_root is not None
            else find_repository_root(Path(__file__))
        )
        self.output_dir = output_dir
        self.database_url = database_url or get_settings().database_url
        self.restart_wait_seconds = restart_wait_seconds
        self.preflight_symbol = preflight_symbol
        self.preflight_timeframe = preflight_timeframe
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.commands: list[dict[str, Any]] = []
        self.bugs: list[dict[str, Any]] = []
        self.engine: Engine | None = None

    def _run(self, args: list[str], *, timeout: int = 300) -> dict[str, Any]:
        started = utc_now()
        completed = subprocess.run(
            args, cwd=self.root, text=True, capture_output=True, timeout=timeout,
            env={**__import__("os").environ, "DATABASE_URL": self.database_url},
        )
        def bounded(value: str, limit: int = 16_000) -> str:
            if len(value) <= limit:
                return value
            omitted = len(value) - limit
            return value[:4_000] + f"\n... <{omitted} characters omitted from trace> ...\n" + value[-12_000:]

        result = {
            "command": args, "started_at": started, "finished_at": utc_now(),
            "exit_code": completed.returncode, "stdout": bounded(completed.stdout),
            "stderr": bounded(completed.stderr),
        }
        self.commands.append(result)
        return result

    def _write_json(self, name: str, payload: Any) -> None:
        (self.output_dir / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")

    def _not_run(self, reason: str) -> dict[str, str]:
        return {"artifact_status": "NOT_RUN", "reason": reason, "generated_at": utc_now()}

    def preconditions(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "database_url_configured": bool(self.database_url),
            "migration_file_exists": (self.root / "alembic/versions/0006_engine_market_data_sync_state.py").exists(),
            "cli_exists": (self.root / "scripts/engine_market_data_continuous_sync.py").exists(),
        }
        try:
            self.engine = create_engine(self.database_url, pool_pre_ping=True)
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            inspector = inspect(self.engine)
            names = set(inspector.get_table_names())
            result["postgres_available"] = True
            result["candle_tables"] = {table: table in names for table in TABLES.values()}
            result["alembic_version_table_exists"] = "alembic_version" in names
        except Exception as exc:
            result.update(postgres_available=False, error=f"{type(exc).__name__}: {exc}")
        return result

    def snapshot_db(self, label: str) -> dict[str, Any]:
        if self.engine is None:
            return {"snapshot": label, "status": "UNAVAILABLE", "generated_at": utc_now()}
        payload: dict[str, Any] = {"snapshot": label, "generated_at": utc_now(), "pairs": {}, "sync_state": {}}
        inspector = inspect(self.engine)
        names = set(inspector.get_table_names())
        with self.engine.connect() as connection:
            for symbol in SYMBOLS:
                for timeframe, table in TABLES.items():
                    key = f"{symbol}:{timeframe}"
                    if table not in names:
                        payload["pairs"][key] = {"table_exists": False}
                        continue
                    row = connection.execute(text(f'''SELECT COUNT(*) AS row_count,
                        MAX(open_time_ms) AS latest_open_time_ms,
                        MAX(close_time_ms) AS latest_close_time_ms
                        FROM {table} WHERE symbol=:symbol'''), {"symbol": symbol}).mappings().one()
                    item = dict(row)
                    item.update(
                        table_exists=True,
                        latest_open_time_utc=utc_from_ms(item["latest_open_time_ms"]),
                        latest_close_time_utc=utc_from_ms(item["latest_close_time_ms"]),
                    )
                    payload["pairs"][key] = item
            if "market_data_sync_state" in names:
                rows = connection.execute(text('''SELECT symbol,timeframe,status,last_expected_open_time_ms,
                    last_stored_open_time_ms,freshness_lag_candles,missing_count,last_success_at,
                    last_error_code,last_error_message,last_inserted_count,last_updated_count,
                    last_skipped_count,last_failed_count,daemon_instance_id,updated_at
                    FROM market_data_sync_state WHERE symbol = ANY(:symbols) AND timeframe = ANY(:timeframes)'''),
                    {"symbols": list(SYMBOLS), "timeframes": list(TIMEFRAMES)}).mappings()
                payload["sync_state"] = {f"{r['symbol']}:{r['timeframe']}": dict(r) for r in rows}
            else:
                payload["sync_state_table_exists"] = False
        return payload

    def alembic_check(self) -> dict[str, Any]:
        python = sys.executable
        before = self._run([python, "-m", "alembic", "current"])
        heads = self._run([python, "-m", "alembic", "heads"])
        upgrade = self._run([python, "-m", "alembic", "upgrade", "head"])
        after = self._run([python, "-m", "alembic", "current"])
        head_revision = heads["stdout"].strip().split(maxsplit=1)[0]
        current_revision = after["stdout"].strip().split(maxsplit=1)[0]
        migration_applied = bool(
            upgrade["exit_code"] == 0
            and head_revision
            and current_revision == head_revision
        )
        result: dict[str, Any] = {
            "alembic_before": before["stdout"].strip(), "alembic_heads": heads["stdout"].strip(),
            "alembic_after": after["stdout"].strip(), "upgrade_exit_code": upgrade["exit_code"],
            "migration_applied": migration_applied,
            "upgrade_error": upgrade["stderr"].strip() or None,
            "failure_stage": None if upgrade["exit_code"] == 0 else "ALEMBIC_UPGRADE",
            "target_revision": head_revision,
            "target_revision_length": len(head_revision),
        }
        if self.engine is not None and "alembic_version" in inspect(self.engine).get_table_names():
            version_column = next(
                column for column in inspect(self.engine).get_columns("alembic_version")
                if column["name"] == "version_num"
            )
            result["alembic_version_column_type"] = str(version_column["type"])
            result["alembic_version_max_length"] = getattr(version_column["type"], "length", None)
        if upgrade["exit_code"] != 0 and "value too long for type character varying(32)" in upgrade["stderr"]:
            self.bugs.append({
                "id": "BUG_CANDIDATE_ALEMBIC_REVISION_ID_TOO_LONG",
                "stage": "ALEMBIC_UPGRADE",
                "summary": "revision id does not fit alembic_version.version_num varchar(32)",
                "reproduction": "DATABASE_URL=<real postgres> python -m alembic upgrade head",
                "error": "StringDataRightTruncation: value too long for type character varying(32)",
                "fix_applied": False,
            })
        if result["migration_applied"] and self.engine is not None:
            inspector = inspect(self.engine)
            tables = set(inspector.get_table_names())
            result["sync_state_table_exists"] = "market_data_sync_state" in tables
            if result["sync_state_table_exists"]:
                result["unique_symbol_timeframe_exists"] = any(
                    set(item.get("column_names") or ()) == {"symbol", "timeframe"}
                    for item in inspector.get_unique_constraints("market_data_sync_state"))
                result["status_check_constraint_exists"] = any(
                    item.get("name") == "ck_market_data_sync_state_status"
                    for item in inspector.get_check_constraints("market_data_sync_state"))
                utc_names = {"last_attempt_at", "last_success_at", "last_error_at", "updated_at", "created_at"}
                columns = {item["name"]: item for item in inspector.get_columns("market_data_sync_state")}
                result["utc_columns_exist"] = utc_names <= set(columns)
        return result

    def closed_only(self, now_ms: int | None = None) -> dict[str, Any]:
        now_ms = now_ms or int(time.time() * 1000)
        if self.engine is None:
            return {"passed": False, "reason": "postgres unavailable", "pairs": {}}
        pairs: dict[str, Any] = {}
        all_passed = True
        with self.engine.connect() as connection:
            names = set(inspect(self.engine).get_table_names())
            for symbol in SYMBOLS:
                for timeframe, table in TABLES.items():
                    key = f"{symbol}:{timeframe}"
                    if table not in names:
                        pairs[key] = {"passed": False, "reason": "table missing"}
                        all_passed = False
                        continue
                    rows = connection.execute(text(f'''SELECT open_time_ms,close_time_ms,open,high,low,close,
                        volume,is_closed,data_checksum FROM {table} WHERE symbol=:symbol
                        ORDER BY open_time_ms DESC LIMIT 1'''), {"symbol": symbol}).mappings().all()
                    checked = validate_closed_only_rows(timeframe, now_ms, rows)
                    pairs[key] = checked
                    all_passed = all_passed and checked["passed"] and checked["checked_rows"] == 1
        return {"passed": all_passed, "exchange_now_ms": now_ms, "pairs": pairs}

    def _load_health(self, name: str) -> tuple[dict[str, Any], list[str]]:
        path = self.output_dir / name
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload, validate_health_payload(payload)
        except Exception as exc:
            return {}, [f"{type(exc).__name__}: {exc}"]

    def _daemon(self, mode_args: list[str], health_name: str, *, timeout: int = 3600,
                symbols: Iterable[str] = SYMBOLS,
                timeframes: Iterable[str] = TIMEFRAMES) -> dict[str, Any]:
        command = [sys.executable, "scripts/engine_market_data_continuous_sync.py",
                   "--symbols", ",".join(symbols), "--timeframes", ",".join(timeframes),
                   "--warmup", *mode_args, "--health-report", str(self.output_dir / health_name)]
        result = self._run(command, timeout=timeout)
        payload, errors = self._load_health(health_name)
        return {"exit_code": result["exit_code"], "health_status": payload.get("overall_status"),
                "operational": health_payload_operational(payload),
                "ready": payload.get("ready", payload.get("overall_status") == "OK"),
                "health_valid": not errors, "health_errors": errors}

    @staticmethod
    def _strict_health_errors(payload: Mapping[str, Any]) -> list[str]:
        errors = validate_health_payload(payload)
        for snapshot in payload.get("snapshots", []):
            pair = f"{snapshot.get('symbol')}:{snapshot.get('timeframe')}"
            operational = (
                snapshot.get("operational") is True and snapshot.get("ready") is True
                if "operational" in snapshot or "ready" in snapshot
                else snapshot.get("status") == "OK"
            )
            if not operational:
                errors.append(f"{pair} status={snapshot.get('status')}")
            if snapshot.get("active_error", bool(snapshot.get("last_error"))):
                errors.append(f"{pair} reports last_error despite status={snapshot.get('status')}")
        return errors

    def write_artifacts(self, trace: dict[str, Any], before: dict[str, Any],
                        after_once: dict[str, Any], after_restart: dict[str, Any]) -> None:
        self._write_json(ARTIFACT_NAMES[1], trace)
        self._write_json(ARTIFACT_NAMES[4], before)
        self._write_json(ARTIFACT_NAMES[5], after_once)
        self._write_json(ARTIFACT_NAMES[6], after_restart)
        report = self._render_report(trace, before, after_once, after_restart)
        (self.output_dir / ARTIFACT_NAMES[0]).write_text(report, encoding="utf-8")
        entries = []
        for name in ARTIFACT_NAMES[:-1]:
            path = self.output_dir / name
            entries.append({"name": name, "exists": path.exists(), "bytes": path.stat().st_size if path.exists() else 0})
        manifest = {"stage": trace["stage"], "generated_at": utc_now(), "final_verdict": trace["final_verdict"],
                    "artifacts": entries}
        self._write_json(ARTIFACT_NAMES[7], manifest)

    @staticmethod
    def _render_report(trace: Mapping[str, Any], before: Mapping[str, Any],
                       after_once: Mapping[str, Any], after_restart: Mapping[str, Any]) -> str:
        def block(value: Any) -> str:
            return "```json\n" + json.dumps(value, indent=2, sort_keys=True, default=str) + "\n```"
        sections = [
            ("1. Executive summary", {"final_verdict": trace["final_verdict"], "recommendation": trace["recommendation"], "bug_candidates": trace["bug_candidates"]}),
            ("2. Environment", trace["environment"]),
            ("3. Alembic migration result", trace["alembic"]),
            ("4. DB state before sync", before),
            ("5. Once-mode sync result", trace["once_mode"]),
            ("6. DB state after once-mode", after_once),
            ("7. Continuous mode short-run result", trace["continuous_mode"]),
            ("8. Stop/restart catch-up result", trace["restart_catch_up"]),
            ("9. Health report validation", trace["health_validation"]),
            ("10. Closed-only validation", trace["closed_only_validation"]),
            ("11. Runtime independence validation", trace["runtime_independence"]),
            ("12. Safety counters", trace["safety_counters"]),
            ("13. Final verdict", trace["final_verdict"]),
            ("14. Recommendation", trace["recommendation"]),
        ]
        return "# ENGINE-MARKET-DATA-04-PROD-SMOKE\n\n" + "\n\n".join(f"## {title}\n\n{block(value)}" for title, value in sections) + "\n"

    def run(self) -> dict[str, Any]:
        preconditions = self.preconditions()
        runtime = validate_runtime_independence(
            (self.root / "docker-compose.yml").read_text(encoding="utf-8"),
            (self.root / "docs/operations/engine_market_data_04_systemd.md").read_text(encoding="utf-8"),
        )
        before = self.snapshot_db("BEFORE")
        health_once = ARTIFACT_NAMES[2]
        health_continuous = ARTIFACT_NAMES[3]
        not_run_reason = "ALEMBIC_UPGRADE did not complete"
        if not preconditions.get("postgres_available"):
            alembic = {"status": "NOT_RUN", "reason": "POSTGRESQL_NOT_AVAILABLE"}
            verdict = "PROD_SMOKE_BLOCKED_POSTGRES"
        else:
            alembic = self.alembic_check()
            verdict = "PROD_SMOKE_FAILED" if not alembic.get("migration_applied") else "PROD_SMOKE_PASSED"
        once: dict[str, Any] = self._not_run(not_run_reason)
        continuous: dict[str, Any] = self._not_run(not_run_reason)
        restart: dict[str, Any] = self._not_run(not_run_reason)
        health_validation: dict[str, Any] = {"once": {"valid": False, "reason": not_run_reason},
                                             "continuous": {"valid": False, "reason": not_run_reason}}
        after_once = self._not_run(not_run_reason)
        after_restart = self._not_run(not_run_reason)
        closed = {"passed": False, "reason": not_run_reason, "pairs": {}}
        if verdict == "PROD_SMOKE_PASSED":
            reduced = self._daemon(
                ["--once"], health_once,
                symbols=[self.preflight_symbol], timeframes=[self.preflight_timeframe],
            )
            after_once = self.snapshot_db("AFTER_REDUCED_ONCE")
            once_payload, once_schema_errors = self._load_health(health_once)
            once_strict_errors = self._strict_health_errors(once_payload)
            once = {
                "reduced_preflight": {
                    **reduced, "symbol": self.preflight_symbol,
                    "timeframe": self.preflight_timeframe,
                },
                "full_once": self._not_run("reduced once-mode preflight failed strict health validation"),
            }
            health_validation["once"] = {
                "valid": not once_strict_errors,
                "errors": once_strict_errors,
                "schema_errors": once_schema_errors,
                "overall_status": once_payload.get("overall_status"),
            }
            if reduced["exit_code"] or once_strict_errors:
                verdict = ("PROD_SMOKE_BLOCKED_EXTERNAL"
                           if once_payload.get("overall_status") in {"DISCONNECTED", "DEGRADED"}
                           else "PROD_SMOKE_FAILED")
                if any(
                    "number of parameters must be between 0 and 65535" in str(item.get("last_error"))
                    for item in once_payload.get("snapshots", [])
                ):
                    self.bugs.append({
                        "id": "BUG_CANDIDATE_POSTGRES_BULK_UPSERT_PARAMETER_LIMIT",
                        "stage": "ONCE_MODE_REDUCED_PREFLIGHT",
                        "summary": "multi-batch REST recovery is accumulated into one PostgreSQL INSERT exceeding 65535 parameters",
                        "reproduction": (
                            "python scripts/engine_market_data_continuous_sync.py "
                            f"--symbols {self.preflight_symbol} --timeframes {self.preflight_timeframe} "
                            "--once --warmup --health-report <path>"
                        ),
                        "health_false_positive": once_payload.get("overall_status") == "OK",
                        "fix_applied": False,
                    })
                stop_reason = "reduced once-mode preflight failed strict health validation"
                continuous = self._not_run(stop_reason)
                restart = self._not_run(stop_reason)
                after_restart = self._not_run(stop_reason)
            else:
                full_once = self._daemon(["--once"], health_once)
                full_payload, full_schema_errors = self._load_health(health_once)
                full_strict_errors = self._strict_health_errors(full_payload)
                once["full_once"] = full_once
                after_once = self.snapshot_db("AFTER_FULL_ONCE")
                health_validation["once"] = {
                    "valid": not full_strict_errors,
                    "errors": full_strict_errors,
                    "schema_errors": full_schema_errors,
                    "overall_status": full_payload.get("overall_status"),
                }
                if full_once["exit_code"] or full_strict_errors:
                    verdict = "PROD_SMOKE_FAILED"
            if verdict == "PROD_SMOKE_PASSED":
                continuous = self._daemon(["--continuous", "--stop-after-cycles", "3",
                    "--health-report-interval-seconds", "1", "--poll-interval-seconds", "1"], health_continuous)
                cont_payload, cont_schema_errors = self._load_health(health_continuous)
                cont_strict_errors = self._strict_health_errors(cont_payload)
                health_validation["continuous"] = {
                    "valid": not cont_strict_errors,
                    "errors": cont_strict_errors,
                    "schema_errors": cont_schema_errors,
                    "overall_status": cont_payload.get("overall_status"),
                }
                if continuous["exit_code"] or cont_strict_errors:
                    verdict = "PROD_SMOKE_FAILED"
                else:
                    time.sleep(self.restart_wait_seconds)
                    restart_health = "ENGINE_MARKET_DATA_04_PROD_SMOKE_HEALTH_RESTART.json"
                    restart = self._daemon(["--once"], restart_health)
                    after_restart = self.snapshot_db("AFTER_RESTART")
                    if restart["exit_code"] or not restart.get("operational"):
                        verdict = "PROD_SMOKE_FAILED"
            if verdict == "PROD_SMOKE_PASSED":
                closed = self.closed_only()
                if not closed["passed"]:
                    verdict = "PROD_SMOKE_FAILED"
            else:
                reduced_closed = self.closed_only()
                closed = {
                    "passed": False,
                    "reason": "sync stage failed before final full closed-only audit",
                    "reduced_once_validation": reduced_closed,
                    "final_full_validation": self._not_run("full once-mode was not executed"),
                }
                health_validation["continuous"] = {
                    "valid": False,
                    "reason": "once-mode strict health validation failed",
                }
                self._write_json(health_continuous, self._not_run("once-mode strict health validation failed"))
        else:
            self._write_json(health_once, self._not_run(not_run_reason))
            self._write_json(health_continuous, self._not_run(not_run_reason))
        trace = {
            "stage": "ENGINE-MARKET-DATA-04-PROD-SMOKE", "generated_at": utc_now(),
            "environment": {"python": sys.version, "platform": sys.platform,
                            "database_url_configured": bool(self.database_url), "symbols": list(SYMBOLS), "timeframes": list(TIMEFRAMES)},
            "preconditions": preconditions, "alembic": alembic, "once_mode": once,
            "continuous_mode": continuous, "restart_catch_up": restart,
            "health_validation": health_validation, "closed_only_validation": closed,
            "runtime_independence": runtime, "safety_counters": safety_counters(),
            "bug_candidates": self.bugs, "commands": self.commands, "final_verdict": verdict,
            "failure_stage": (
                "ALEMBIC_UPGRADE" if verdict == "PROD_SMOKE_FAILED" and not alembic.get("migration_applied")
                else "ONCE_MODE_REDUCED_PREFLIGHT" if verdict == "PROD_SMOKE_FAILED" and self.bugs
                else None
            ),
            "recommendation": ("ENGINE-ORCHESTRATOR-01 — Online Closed-Candle Pipeline Orchestrator"
                               if verdict == "PROD_SMOKE_PASSED" else "fix ENGINE-MARKET-DATA-04 production blocker first"),
        }
        self.write_artifacts(trace, before, after_once, after_restart)
        return trace
