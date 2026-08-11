"""Create/get-only persistence for the immutable V1 PAPER baseline.

V1 has one logical active PAPER account/session. Existing economic tables do
not carry account/session columns, so any persisted command, order, fill,
position, or journal event is prior economic activity. A transaction-scoped
advisory lock serializes initialization. Methods flush but never commit.
"""

from __future__ import annotations

from sqlalchemy import exists as sql_exists, select, text
from sqlalchemy.orm import Session

from app.db.paper_models import (
    PaperAccountBaselineRecord,
    PaperExecutionCommandRecord,
    PaperFillRecord,
    PaperJournalEntryRecord,
    PaperOrderRecord,
    PaperPositionRecord,
)
from app.engine_paper.accounting import (
    PaperAccountBaseline,
    PaperAccountIdentity,
    PaperAccountingError,
    PaperAccountingFinding,
)


_V1_INITIALIZATION_LOCK_KEY = 5_741_975_929_012


def acquire_v1_account_initialization_lock(session: Session) -> None:
    """Serialize baseline initialization and first economic command creation."""

    session.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": _V1_INITIALIZATION_LOCK_KEY},
    )


def _domain(row: PaperAccountBaselineRecord) -> PaperAccountBaseline:
    return PaperAccountBaseline(
        baseline_id=row.baseline_id,
        identity=PaperAccountIdentity(
            account_id=row.account_id,
            accounting_session_id=row.accounting_session_id,
            currency=row.currency,
        ),
        initial_balance=row.initial_balance,
        initialized_at=row.initialized_at,
        semantic_version=row.semantic_version,
    )


def baseline_semantically_equal(
    existing: PaperAccountBaseline, requested: PaperAccountBaseline
) -> bool:
    """Compare replay economics, excluding caller-generated identity/time."""

    return (
        existing.identity == requested.identity
        and existing.initial_balance == requested.initial_balance
        and existing.semantic_version == requested.semantic_version
    )


class PaperAccountBaselineRepository:
    """Baseline repository intentionally exposing no update/delete method."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(
        self, account_id: str, accounting_session_id: str
    ) -> PaperAccountBaseline | None:
        row = self.session.scalar(
            select(PaperAccountBaselineRecord).where(
                PaperAccountBaselineRecord.account_id == account_id,
                PaperAccountBaselineRecord.accounting_session_id
                == accounting_session_id,
            )
        )
        return None if row is None else _domain(row)

    def list_for_identity(
        self, identity: PaperAccountIdentity
    ) -> tuple[PaperAccountBaseline, ...]:
        found = self.get(identity.account_id, identity.accounting_session_id)
        return () if found is None else (found,)

    def exists(self, account_id: str, accounting_session_id: str) -> bool:
        return self.get(account_id, accounting_session_id) is not None

    def has_economic_activity_before_baseline(
        self, identity: PaperAccountIdentity
    ) -> bool:
        if not identity.account_id or not identity.accounting_session_id:
            raise PaperAccountingError(
                PaperAccountingFinding.BASELINE_INVALID, "invalid identity"
            )
        economic_records = (
            PaperExecutionCommandRecord,
            PaperOrderRecord,
            PaperFillRecord,
            PaperPositionRecord,
            PaperJournalEntryRecord,
        )
        return any(
            bool(self.session.scalar(select(sql_exists().select_from(record))))
            for record in economic_records
        )

    def has_economic_activity(self, identity: PaperAccountIdentity) -> bool:
        return self.has_economic_activity_before_baseline(identity)

    def create_if_absent(
        self, baseline: PaperAccountBaseline
    ) -> PaperAccountBaseline:
        acquire_v1_account_initialization_lock(self.session)
        existing = self.get(
            baseline.identity.account_id,
            baseline.identity.accounting_session_id,
        )
        if existing is not None:
            if baseline_semantically_equal(existing, baseline):
                return existing
            raise PaperAccountingError(
                PaperAccountingFinding.BASELINE_IMMUTABILITY_VIOLATION,
                "an established baseline cannot be rewritten",
            )
        if self.has_economic_activity_before_baseline(baseline.identity):
            raise PaperAccountingError(
                PaperAccountingFinding.BASELINE_AFTER_ECONOMIC_ACTIVITY_DENIED,
                "baseline initialization after economic activity is denied",
            )
        self.session.add(
            PaperAccountBaselineRecord(
                baseline_id=baseline.baseline_id,
                account_id=baseline.identity.account_id,
                accounting_session_id=baseline.identity.accounting_session_id,
                currency=baseline.identity.currency,
                initial_balance=baseline.initial_balance,
                initialized_at=baseline.initialized_at,
                semantic_version=baseline.semantic_version,
            )
        )
        self.session.flush()
        return baseline

    def insert_once(self, baseline: PaperAccountBaseline) -> PaperAccountBaseline:
        """Compatibility alias; retains create/get-only semantics."""

        return self.create_if_absent(baseline)
