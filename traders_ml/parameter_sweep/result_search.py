"""Versioned result-search foundation. No database writes or order adapters.

Block 01 deliberately exposes preparation only until a historical simulator is
installed. Front ends share this contract; legacy searches are not evidence for it.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Literal, Mapping
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .artifact_writer import DEFAULT_ARTIFACT_WRITER
from .universe import validate_parameter_sweep_symbol

CONTRACT_VERSION = "result-search/1"
REGISTRY_VERSION = "result-search-registry/1-foundation"
ENGINE_VERSION = "result-search-engine/1-foundation"
ROOT = Path(__file__).resolve().parents[2]


def fingerprint(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode()).hexdigest()


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class SearchRequest(Contract):
    version: Literal["result-search/1"] = CONTRACT_VERSION
    symbols: tuple[str, ...]
    scope: Literal["SINGLE_SYMBOL", "GLOBAL"]
    profile: Literal["trade-5m-v2"] = "trade-5m-v2"
    start: datetime
    end: datetime
    data_cutoff: datetime
    initial_capital: float = Field(gt=0)
    baseline_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    parameters: dict[str, tuple[float | str | bool, ...]] = Field(default_factory=dict)
    constraints: tuple[str, ...] = ()
    seed: int = Field(ge=0)
    max_trials: int = Field(gt=0)
    max_wall_time: float = Field(gt=0)
    artifact_budget_bytes: int = Field(ge=4096)
    storage_budget_bytes: int = Field(ge=4096)
    target_config_count: int = Field(default=1, gt=0)
    success_criterion: Literal["VALID_CLOSED_TRADE_NET_PNL_GT_ZERO"] = "VALID_CLOSED_TRADE_NET_PNL_GT_ZERO"
    data_mode: Literal["HISTORICAL_VERIFIED", "ASSUMPTION_BASED"]
    execution_mode: Literal["CAUSAL_OHLC_STOP_FIRST"] = "CAUSAL_OHLC_STOP_FIRST"

    @model_validator(mode="after")
    def validate_request(self) -> SearchRequest:
        if not self.symbols or len(set(self.symbols)) != len(self.symbols):
            raise ValueError("NONEMPTY_UNIQUE_SYMBOLS_REQUIRED")
        normalized = tuple(sorted(validate_parameter_sweep_symbol(s) for s in self.symbols))
        if len(set(normalized)) != len(normalized):
            raise ValueError("DUPLICATE_NORMALIZED_SYMBOL")
        object.__setattr__(self, "symbols", normalized)
        if self.scope == "SINGLE_SYMBOL" and len(normalized) != 1:
            raise ValueError("SINGLE_SYMBOL_REQUIRES_ONE_SYMBOL")
        for field in ("start", "end", "data_cutoff"):
            value = getattr(self, field)
            if value.utcoffset() is None:
                raise ValueError("TIMEZONE_REQUIRED")
            object.__setattr__(self, field, value.astimezone(timezone.utc))
        if not self.start < self.end <= self.data_cutoff:
            raise ValueError("INVALID_INTERVAL_OR_CUTOFF")
        if self.artifact_budget_bytes > self.storage_budget_bytes:
            raise ValueError("ARTIFACT_BUDGET_EXCEEDS_STORAGE")
        if any(not values for values in self.parameters.values()):
            raise ValueError("EMPTY_PARAMETER_DOMAIN")
        return self

    @property
    def identity(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


class ExecutionState(StrEnum):
    READY = "READY"
    RUNNING = "RUNNING"
    VERIFYING = "VERIFYING"
    TERMINAL = "TERMINAL"


class SearchOutcome(StrEnum):
    FOUND = "FOUND"
    NOT_FOUND_WITHIN_BUDGET = "NOT_FOUND_WITHIN_BUDGET"
    SEARCH_SPACE_EXHAUSTED = "SEARCH_SPACE_EXHAUSTED"
    BLOCKED_DATA = "BLOCKED_DATA"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class ResumeIdentity(Contract):
    contract: str = CONTRACT_VERSION
    request: str = Field(pattern=r"^[a-f0-9]{64}$")
    dataset: str = Field(pattern=r"^[a-f0-9]{64}$")
    baseline: str = Field(pattern=r"^[a-f0-9]{64}$")
    registry: str = REGISTRY_VERSION
    engine: str = ENGINE_VERSION


class ClosedTradeProof(Contract):
    trade_id: str = Field(min_length=1)
    config_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    dataset_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    engine: str
    entry_valid: bool
    closed: bool
    exit_reason: Literal["STOP", "TARGET", "TIME_STOP", "PATH_END"]
    gross_pnl: float
    costs: float = Field(ge=0)
    net_pnl: float
    causal: bool
    replay_verified: bool

    @property
    def qualifying(self) -> bool:
        return (self.entry_valid and self.closed and self.exit_reason != "PATH_END"
                and self.causal and self.replay_verified and self.net_pnl > 0
                and abs(self.gross_pnl - self.costs - self.net_pnl) <= 1e-8)


def deployment_diagnostics() -> dict[str, Any]:
    def git(*args: str) -> str:
        return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()
    return {"source_commit": git("rev-parse", "HEAD"), "checkout": str(ROOT),
            "interpreter": sys.executable, "pid": os.getpid(),
            "module": str(Path(__file__).resolve()), "contract": CONTRACT_VERSION,
            "engine": ENGINE_VERSION, "registry": REGISTRY_VERSION,
            "module_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
            "module_dirty": bool(git("status", "--porcelain", "--", str(Path(__file__).resolve()))),
            "capabilities": ["TYPED_REQUEST", "RESUME_GUARD", "DURABLE_VERIFIED_RESULT_CONTRACT"],
            "search_execution_available": False}


class ResultSearchService:
    """Shared service with fail-closed state and durable proof publication.

    Proofs are supplied by the forthcoming simulator/verifier, never legacy PnL.
    No public CLI accepts externally supplied proofs as search results.
    """
    @staticmethod
    def request(values: Mapping[str, Any]) -> SearchRequest:
        return SearchRequest.model_validate(values)

    def prepare(self, request: SearchRequest, root: Path, dataset_hash: str,
                *, resume: Path | None = None) -> Path:
        # Revalidate to isolate the service from caller-owned mutable mappings.
        request = SearchRequest.model_validate_json(request.model_dump_json())
        identity = ResumeIdentity(request=request.identity, dataset=dataset_hash,
                                  baseline=request.baseline_hash).model_dump()
        if resume is not None:
            manifest = json.loads((resume / "SEARCH_MANIFEST.json").read_text())
            if manifest["identity"] != identity:
                raise ValueError("INCOMPATIBLE_RESUME")
            return resume
        run = root / uuid4().hex
        run.mkdir(parents=True, exist_ok=False)
        self._write(run / "SEARCH_MANIFEST.json", {"run_id": run.name, "identity": identity,
                    "request": request.model_dump(mode="json"),
                    "deployment": deployment_diagnostics()})
        self._write(run / "STATUS.json", {"execution_state": "READY", "outcome": None,
                    "evidence_quality": request.data_mode,
                    "independent_validation": "NOT_EVALUATED", "reason": "FOUNDATION_PREPARED"})
        return run

    @staticmethod
    def _write(path: Path, value: Any) -> None:
        DEFAULT_ARTIFACT_WRITER.atomic_bytes(path, json.dumps(value, sort_keys=True,
                                              allow_nan=False, indent=2).encode())

    def transition(self, run: Path, state: ExecutionState, *,
                   outcome: SearchOutcome | None = None, reason: str = "") -> None:
        previous = json.loads((run / "STATUS.json").read_text())
        allowed = {"READY": {"RUNNING", "TERMINAL"},
                   "RUNNING": {"VERIFYING", "TERMINAL"},
                   "VERIFYING": {"RUNNING", "TERMINAL"}, "TERMINAL": set()}
        if state not in allowed[previous["execution_state"]]:
            raise ValueError("INVALID_STATE_TRANSITION")
        if (state == ExecutionState.TERMINAL) != (outcome is not None):
            raise ValueError("TERMINAL_OUTCOME_REQUIRED")
        if outcome == SearchOutcome.FOUND:
            if previous["execution_state"] != "VERIFYING":
                raise ValueError("VERIFICATION_REQUIRED")
            self._verify_saved_proof(run)
        previous.update(execution_state=state, outcome=outcome, reason=reason)
        self._write(run / "STATUS.json", previous)

    def _verify_saved_proof(self, run: Path) -> ClosedTradeProof:
        proof = ClosedTradeProof.model_validate_json((run / "REPLAY_PROOF.json").read_text())
        identity = json.loads((run / "SEARCH_MANIFEST.json").read_text())["identity"]
        if not proof.qualifying or proof.dataset_hash != identity["dataset"] or proof.engine != identity["engine"]:
            raise ValueError("INVALID_FINDING_EVIDENCE")
        config = json.loads((run / "VERIFIED_CONFIG.json").read_text())
        if fingerprint(config) != proof.config_hash:
            raise ValueError("CONFIG_IDENTITY_MISMATCH")
        return proof

    def persist_verified_proof(self, run: Path, proof: ClosedTradeProof, config: Mapping[str, Any]) -> None:
        if json.loads((run / "STATUS.json").read_text())["execution_state"] != "VERIFYING":
            raise ValueError("VERIFICATION_REQUIRED")
        if not proof.qualifying or fingerprint(config) != proof.config_hash:
            raise ValueError("INVALID_FINDING_EVIDENCE")
        self._write(run / "VERIFIED_CONFIG.json", dict(config))
        self._write(run / "REPLAY_PROOF.json", proof.model_dump(mode="json"))
        self._verify_saved_proof(run)
