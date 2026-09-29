"""Durable PAPER-only empirical recovery and authority generation switching."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import os
from typing import Callable, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.paper_models import (
    EmpiricalAuthorityGenerationRecord,
    EmpiricalRecoveryCampaignRecord,
    EmpiricalRecoveryEvaluationRecord,
)
from app.engine_paper.scalping_policy_v2 import EmpiricalSetupBucket, evaluate_expectancy


EXPLORATION_V2_POLICY_VERSION = "limited-paper-exploration-v2"
REQUALIFICATION_POLICY_VERSION = "empirical-requalification-v1"
AUTHORITY_POLICY_VERSION = "empirical-authority-generation-v1"
EXPLORATION_V2_ADMISSION_MODE = "PAPER_EXPLORATION_V2"
REQUALIFICATION_FLAG = "EMPIRICAL_REQUALIFICATION_ENABLED"
REQUALIFICATION_POLICY_FLAG = "EMPIRICAL_REQUALIFICATION_POLICY_VERSION"
EXPLORATION_POLICY_FLAG = "PAPER_EXPLORATION_POLICY_VERSION"

RECOVERY_AUTHORITY_WINDOW_SIZE = 20
REQUALIFICATION_MIN_NEW_V2_EXPLORATION_OBSERVATIONS = 8
REQUALIFICATION_MIN_DISTINCT_SYMBOLS = 3
REQUALIFICATION_REQUIRED_CONSECUTIVE_POSITIVE_WINDOWS = 2


def requalification_enabled(environment: dict[str, str] | None = None) -> bool:
    values = os.environ if environment is None else environment
    return (
        str(values.get(REQUALIFICATION_FLAG, "false")).strip().lower() == "true"
        and str(values.get(REQUALIFICATION_POLICY_FLAG, "")).strip()
        == REQUALIFICATION_POLICY_VERSION
        and str(values.get(EXPLORATION_POLICY_FLAG, "")).strip()
        == EXPLORATION_V2_POLICY_VERSION
    )


@dataclass(frozen=True, slots=True)
class RecoveryObservation:
    position_id: str
    symbol: str
    closed_at: datetime
    net_return_bps: float
    admission_mode: str
    exploration_policy_version: str | None = None

    @property
    def is_v2_probe(self) -> bool:
        return (
            self.admission_mode == EXPLORATION_V2_ADMISSION_MODE
            and self.exploration_policy_version == EXPLORATION_V2_POLICY_VERSION
        )


@dataclass(frozen=True, slots=True)
class AuthorityMetrics:
    observation_set_fingerprint: str
    sample_count: int
    wins: int
    losses: int
    win_rate: float
    average_win_net_bps: float
    average_loss_net_bps: float
    empirical_ev_net_bps: float
    expected_ev_r: float
    break_even_win_rate: float
    required_dynamic_rr: float


@dataclass(frozen=True, slots=True)
class RequalificationSnapshot:
    authority_generation_id: str | None = None
    authority_state: str | None = None
    recovery_campaign_id: str | None = None
    recovery_new_observation_count: int = 0
    recovery_distinct_symbol_count: int = 0
    recovery_positive_confirmation_count: int = 0
    recovery_window_sample_count: int = 0
    recovery_window_ev_net_bps: float | None = None
    recovery_window_expected_ev_r: float | None = None
    recovery_window_fingerprint: str | None = None
    requalification_status: str = "NOT_EVALUATED"
    requalification_reason: str = "REQUALIFICATION_DISABLED"

    def to_dict(self) -> dict[str, object]:
        return {
            "authority_generation_id": self.authority_generation_id,
            "authority_state": self.authority_state,
            "recovery_campaign_id": self.recovery_campaign_id,
            "recovery_new_observation_count": self.recovery_new_observation_count,
            "recovery_distinct_symbol_count": self.recovery_distinct_symbol_count,
            "recovery_positive_confirmation_count": self.recovery_positive_confirmation_count,
            "recovery_window_sample_count": self.recovery_window_sample_count,
            "recovery_window_ev_net_bps": self.recovery_window_ev_net_bps,
            "recovery_window_expected_ev_r": self.recovery_window_expected_ev_r,
            "recovery_window_fingerprint": self.recovery_window_fingerprint,
            "requalification_status": self.requalification_status,
            "requalification_reason": self.requalification_reason,
        }


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _identifier(prefix: str, *parts: object) -> str:
    material = "|".join(str(part) for part in parts)
    return f"{prefix}:{sha256(material.encode('utf-8')).hexdigest()}"


def recovery_window(
    observations: Iterable[RecoveryObservation], *, as_of: datetime | None = None,
) -> tuple[RecoveryObservation, ...]:
    boundary = None if as_of is None else _utc(as_of)
    compatible = sorted(
        (
            item for item in observations
            if boundary is None or _utc(item.closed_at) <= boundary
        ),
        key=lambda item: (_utc(item.closed_at), item.position_id),
    )
    return tuple(compatible[-RECOVERY_AUTHORITY_WINDOW_SIZE:])


def authority_metrics(
    observations: Iterable[RecoveryObservation], *, bucket_level: str,
    bucket_key: str, authority_population_id: str,
) -> AuthorityMetrics | None:
    window = tuple(observations)
    if len(window) != RECOVERY_AUTHORITY_WINDOW_SIZE:
        return None
    wins = tuple(item.net_return_bps for item in window if item.net_return_bps > 0)
    losses = tuple(abs(item.net_return_bps) for item in window if item.net_return_bps < 0)
    if not wins or not losses:
        return None
    average_win = sum(wins) / len(wins)
    average_loss = sum(losses) / len(losses)
    fingerprint = sha256(
        "\n".join(sorted(item.position_id for item in window)).encode("utf-8")
    ).hexdigest()
    bucket = EmpiricalSetupBucket(
        setup_type="RECOVERY_AUTHORITY",
        direction="MIXED",
        samples=len(window),
        wins=len(wins),
        level=bucket_level,
        bucket_key=bucket_key,
        evidence_source="REALIZED_RECOVERY_WINDOW",
        average_win_net_bps=average_win,
        average_loss_net_bps=average_loss,
        authority_population_id=authority_population_id,
        observation_set_fingerprint=fingerprint,
    )
    decision = evaluate_expectancy(
        net_win_bps=average_win,
        net_loss_bps=average_loss,
        bucket=bucket,
        minimum_samples=RECOVERY_AUTHORITY_WINDOW_SIZE,
    )
    if any(value is None for value in (
        decision.empirical_ev_net_bps,
        decision.expected_ev_r,
        decision.dynamic_required_net_rr,
        decision.p_win_conservative,
    )):
        return None
    return AuthorityMetrics(
        fingerprint, len(window), len(wins), len(window) - len(wins),
        len(wins) / len(window), average_win, average_loss,
        float(decision.empirical_ev_net_bps), float(decision.expected_ev_r),
        average_loss / (average_win + average_loss),
        float(decision.dynamic_required_net_rr),
    )


def requalification_predicate(
    metrics: AuthorityMetrics | None, *, new_v2_probes: int, distinct_symbols: int,
) -> tuple[bool, str]:
    if metrics is None or metrics.sample_count != RECOVERY_AUTHORITY_WINDOW_SIZE:
        return False, "RECOVERY_WINDOW_NOT_FULL"
    if new_v2_probes < REQUALIFICATION_MIN_NEW_V2_EXPLORATION_OBSERVATIONS:
        return False, "REQUALIFICATION_MIN_NEW_V2_PROBES_NOT_MET"
    if distinct_symbols < REQUALIFICATION_MIN_DISTINCT_SYMBOLS:
        return False, "REQUALIFICATION_SYMBOL_DIVERSITY_NOT_MET"
    if metrics.empirical_ev_net_bps <= 0:
        return False, "REQUALIFICATION_EMPIRICAL_EV_NOT_POSITIVE"
    if metrics.expected_ev_r <= 0:
        return False, "REQUALIFICATION_EXPECTED_EV_R_NOT_POSITIVE"
    return True, "REQUALIFICATION_POSITIVE_WINDOW"


class EmpiricalRequalificationStore:
    """Transactional authority resolver and exactly-once promotion state machine."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _bucket_from_generation(
        generation: EmpiricalAuthorityGenerationRecord,
    ) -> EmpiricalSetupBucket:
        return EmpiricalSetupBucket(
            setup_type="ACTIVE_AUTHORITY",
            direction="MIXED",
            samples=generation.sample_count,
            wins=generation.wins,
            level=generation.bucket_level,
            bucket_key=generation.bucket_key,
            evidence_source=generation.source,
            average_win_net_bps=float(generation.average_win_net_bps),
            average_loss_net_bps=float(generation.average_loss_net_bps),
            authority_population_id=generation.authority_population_id,
            observation_set_fingerprint=generation.observation_set_fingerprint,
        )

    @staticmethod
    def _generation_values(
        *, population_id: str, metrics: AuthorityMetrics, bucket: EmpiricalSetupBucket,
        source: str, campaign_id: str | None, activated_at: datetime,
    ) -> EmpiricalAuthorityGenerationRecord:
        generation_id = _identifier(
            "authority-generation-v1", population_id,
            metrics.observation_set_fingerprint,
        )
        return EmpiricalAuthorityGenerationRecord(
            authority_generation_id=generation_id,
            authority_population_id=population_id,
            authority_policy_version=AUTHORITY_POLICY_VERSION,
            observation_set_fingerprint=metrics.observation_set_fingerprint,
            sample_count=metrics.sample_count,
            wins=metrics.wins,
            losses=metrics.losses,
            win_rate=Decimal(str(metrics.win_rate)),
            average_win_net_bps=Decimal(str(metrics.average_win_net_bps)),
            average_loss_net_bps=Decimal(str(metrics.average_loss_net_bps)),
            empirical_ev_net_bps=Decimal(str(metrics.empirical_ev_net_bps)),
            expected_ev_r=Decimal(str(metrics.expected_ev_r)),
            break_even_win_rate=Decimal(str(metrics.break_even_win_rate)),
            required_dynamic_rr=Decimal(str(metrics.required_dynamic_rr)),
            bucket_level=bucket.level,
            bucket_key=str(bucket.bucket_key or population_id),
            source=source,
            recovery_campaign_id=campaign_id,
            activated_at=_utc(activated_at),
            superseded_at=None,
            is_active=True,
        )

    @staticmethod
    def _baseline_metrics(bucket: EmpiricalSetupBucket) -> AuthorityMetrics | None:
        if (
            bucket.samples != RECOVERY_AUTHORITY_WINDOW_SIZE
            or not bucket.observation_set_fingerprint
            or bucket.average_win_net_bps is None
            or bucket.average_loss_net_bps is None
        ):
            return None
        decision = evaluate_expectancy(
            net_win_bps=bucket.average_win_net_bps,
            net_loss_bps=bucket.average_loss_net_bps,
            bucket=bucket,
        )
        if any(value is None for value in (
            decision.empirical_ev_net_bps, decision.expected_ev_r,
            decision.dynamic_required_net_rr, decision.p_win_conservative,
        )):
            return None
        return AuthorityMetrics(
            bucket.observation_set_fingerprint, bucket.samples, bucket.wins,
            bucket.samples - bucket.wins, bucket.wins / bucket.samples,
            bucket.average_win_net_bps, bucket.average_loss_net_bps,
            float(decision.empirical_ev_net_bps), float(decision.expected_ev_r),
            bucket.average_loss_net_bps / (
                bucket.average_win_net_bps + bucket.average_loss_net_bps
            ),
            float(decision.dynamic_required_net_rr),
        )

    def reconcile(
        self, *, base_bucket: EmpiricalSetupBucket,
        observations: Iterable[RecoveryObservation], now: datetime | None = None,
    ) -> tuple[EmpiricalSetupBucket, RequalificationSnapshot]:
        observed = _utc(now or datetime.now(timezone.utc))
        population_id = str(base_bucket.authority_population_id or "")
        if not population_id or not requalification_enabled():
            return base_bucket, RequalificationSnapshot(
                authority_state="ESTABLISHED_NEGATIVE",
                requalification_reason="REQUALIFICATION_DISABLED",
            )
        rows = tuple(observations)
        with self._session_factory() as session, session.begin():
            active = session.scalar(
                select(EmpiricalAuthorityGenerationRecord)
                .where(
                    EmpiricalAuthorityGenerationRecord.authority_population_id == population_id,
                    EmpiricalAuthorityGenerationRecord.is_active.is_(True),
                )
                .with_for_update()
            )
            if active is None:
                baseline_metrics = self._baseline_metrics(base_bucket)
                if baseline_metrics is None:
                    return base_bucket, RequalificationSnapshot(
                        authority_state="ESTABLISHED_NEGATIVE",
                        requalification_reason="BASELINE_AUTHORITY_NOT_PERSISTABLE",
                    )
                active = self._generation_values(
                    population_id=population_id, metrics=baseline_metrics,
                    bucket=base_bucket, source="ESTABLISHED_BASELINE",
                    campaign_id=None, activated_at=observed,
                )
                session.add(active)
                session.flush()

            if active.source in {"REQUALIFICATION_V1", "CONTINUOUS_RECENT_V1"}:
                latest_window = recovery_window(rows)
                latest_metrics = authority_metrics(
                    latest_window, bucket_level=active.bucket_level,
                    bucket_key=active.bucket_key,
                    authority_population_id=population_id,
                )
                if (
                    latest_metrics is not None
                    and latest_metrics.observation_set_fingerprint
                    != active.observation_set_fingerprint
                ):
                    active.is_active = False
                    active.superseded_at = observed
                    session.flush()
                    existing = session.scalar(
                        select(EmpiricalAuthorityGenerationRecord).where(
                            EmpiricalAuthorityGenerationRecord.authority_population_id
                            == population_id,
                            EmpiricalAuthorityGenerationRecord.observation_set_fingerprint
                            == latest_metrics.observation_set_fingerprint,
                        )
                    )
                    if existing is None:
                        existing = self._generation_values(
                            population_id=population_id, metrics=latest_metrics,
                            bucket=base_bucket, source="CONTINUOUS_RECENT_V1",
                            campaign_id=None, activated_at=observed,
                        )
                        session.add(existing)
                    else:
                        existing.is_active = True
                        existing.superseded_at = None
                    session.flush()
                    active = existing

            campaign = session.scalar(
                select(EmpiricalRecoveryCampaignRecord)
                .where(
                    EmpiricalRecoveryCampaignRecord.authority_population_id == population_id,
                    EmpiricalRecoveryCampaignRecord.state.in_((
                        "ESTABLISHED_NEGATIVE", "EXPLORATION_RECOVERY_ACTIVE",
                        "REQUALIFICATION_PENDING",
                    )),
                )
                .order_by(EmpiricalRecoveryCampaignRecord.started_at.desc())
                .limit(1)
                .with_for_update()
            )
            if float(active.empirical_ev_net_bps) < 0 and campaign is None:
                campaign_id = _identifier(
                    "recovery-campaign-v1", population_id,
                    active.authority_generation_id, observed.isoformat(),
                )
                campaign = EmpiricalRecoveryCampaignRecord(
                    recovery_campaign_id=campaign_id,
                    authority_population_id=population_id,
                    state="EXPLORATION_RECOVERY_ACTIVE",
                    started_at=observed,
                    v2_closed_probe_count=0,
                    distinct_symbol_count=0,
                    positive_confirmation_count=0,
                    latest_window_fingerprint=None,
                    latest_window_ev_net_bps=None,
                    latest_window_expected_ev_r=None,
                    latest_evaluated_closed_at=None,
                    requalified_at=None,
                    active_authority_generation_id=active.authority_generation_id,
                    initial_authority_generation_id=active.authority_generation_id,
                    updated_at=observed,
                )
                session.add(campaign)
                session.flush()

            if campaign is not None:
                probes = tuple(sorted(
                    (
                        item for item in rows
                        if item.is_v2_probe and _utc(item.closed_at) >= _utc(campaign.started_at)
                    ),
                    key=lambda item: (_utc(item.closed_at), item.position_id),
                ))
                evaluated_ids = set(session.scalars(
                    select(EmpiricalRecoveryEvaluationRecord.trigger_position_id)
                    .where(
                        EmpiricalRecoveryEvaluationRecord.recovery_campaign_id
                        == campaign.recovery_campaign_id
                    )
                ))
                for probe in probes:
                    if probe.position_id in evaluated_ids:
                        continue
                    current_probes = tuple(
                        item for item in probes
                        if (_utc(item.closed_at), item.position_id)
                        <= (_utc(probe.closed_at), probe.position_id)
                    )
                    window = recovery_window(rows, as_of=probe.closed_at)
                    metrics = authority_metrics(
                        window, bucket_level=active.bucket_level,
                        bucket_key=active.bucket_key,
                        authority_population_id=population_id,
                    )
                    distinct = len({item.symbol for item in current_probes})
                    passed, reason = requalification_predicate(
                        metrics, new_v2_probes=len(current_probes),
                        distinct_symbols=distinct,
                    )
                    confirmations = campaign.positive_confirmation_count + 1 if passed else 0
                    confirmations = min(
                        confirmations,
                        REQUALIFICATION_REQUIRED_CONSECUTIVE_POSITIVE_WINDOWS,
                    )
                    evaluation = EmpiricalRecoveryEvaluationRecord(
                        evaluation_id=_identifier(
                            "recovery-evaluation-v1", campaign.recovery_campaign_id,
                            probe.position_id,
                        ),
                        recovery_campaign_id=campaign.recovery_campaign_id,
                        trigger_position_id=probe.position_id,
                        trigger_closed_at=_utc(probe.closed_at),
                        window_fingerprint=(
                            metrics.observation_set_fingerprint if metrics else
                            sha256("\n".join(item.position_id for item in window).encode()).hexdigest()
                        ),
                        window_sample_count=len(window),
                        window_ev_net_bps=(
                            None if metrics is None else Decimal(str(metrics.empirical_ev_net_bps))
                        ),
                        window_expected_ev_r=(
                            None if metrics is None else Decimal(str(metrics.expected_ev_r))
                        ),
                        new_v2_probe_count=len(current_probes),
                        distinct_symbol_count=distinct,
                        predicate_passed=passed,
                        positive_confirmation_count=confirmations,
                        promoted_authority_generation_id=None,
                        evaluated_at=observed,
                    )
                    session.add(evaluation)
                    campaign.v2_closed_probe_count = len(current_probes)
                    campaign.distinct_symbol_count = distinct
                    campaign.positive_confirmation_count = confirmations
                    campaign.latest_window_fingerprint = evaluation.window_fingerprint
                    campaign.latest_window_ev_net_bps = evaluation.window_ev_net_bps
                    campaign.latest_window_expected_ev_r = evaluation.window_expected_ev_r
                    campaign.latest_evaluated_closed_at = _utc(probe.closed_at)
                    campaign.state = "REQUALIFICATION_PENDING" if passed else "EXPLORATION_RECOVERY_ACTIVE"
                    campaign.updated_at = observed
                    if (
                        passed and metrics is not None
                        and confirmations >= REQUALIFICATION_REQUIRED_CONSECUTIVE_POSITIVE_WINDOWS
                    ):
                        active.is_active = False
                        active.superseded_at = observed
                        session.flush()
                        promoted = self._generation_values(
                            population_id=population_id, metrics=metrics,
                            bucket=base_bucket, source="REQUALIFICATION_V1",
                            campaign_id=campaign.recovery_campaign_id,
                            activated_at=observed,
                        )
                        session.add(promoted)
                        session.flush()
                        evaluation.promoted_authority_generation_id = promoted.authority_generation_id
                        campaign.state = "REQUALIFIED_ACTIVE"
                        campaign.requalified_at = observed
                        campaign.active_authority_generation_id = promoted.authority_generation_id
                        active = promoted
                        break
                session.flush()

            snapshot_campaign = campaign
            if snapshot_campaign is None:
                snapshot_campaign = session.scalar(
                    select(EmpiricalRecoveryCampaignRecord)
                    .where(
                        EmpiricalRecoveryCampaignRecord.authority_population_id
                        == population_id
                    )
                    .order_by(EmpiricalRecoveryCampaignRecord.started_at.desc())
                    .limit(1)
                )
            snapshot = RequalificationSnapshot(
                authority_generation_id=active.authority_generation_id,
                authority_state=(
                    "REQUALIFIED_ACTIVE"
                    if snapshot_campaign is not None
                    and snapshot_campaign.state == "REQUALIFIED_ACTIVE"
                    else "EXPLORATION_RECOVERY_ACTIVE"
                    if snapshot_campaign is not None
                    and snapshot_campaign.state != "REQUALIFIED_ACTIVE"
                    else "REQUALIFIED_ACTIVE"
                    if active.source in {"REQUALIFICATION_V1", "CONTINUOUS_RECENT_V1"}
                    and float(active.empirical_ev_net_bps) >= 0
                    else "ESTABLISHED_NEGATIVE"
                ),
                recovery_campaign_id=(
                    None if snapshot_campaign is None
                    else snapshot_campaign.recovery_campaign_id
                ),
                recovery_new_observation_count=(
                    0 if snapshot_campaign is None
                    else snapshot_campaign.v2_closed_probe_count
                ),
                recovery_distinct_symbol_count=(
                    0 if snapshot_campaign is None
                    else snapshot_campaign.distinct_symbol_count
                ),
                recovery_positive_confirmation_count=(
                    0 if snapshot_campaign is None
                    else snapshot_campaign.positive_confirmation_count
                ),
                recovery_window_sample_count=(
                    0 if snapshot_campaign is None
                    or not snapshot_campaign.latest_window_fingerprint
                    else RECOVERY_AUTHORITY_WINDOW_SIZE
                ),
                recovery_window_ev_net_bps=(
                    None if snapshot_campaign is None
                    or snapshot_campaign.latest_window_ev_net_bps is None
                    else float(snapshot_campaign.latest_window_ev_net_bps)
                ),
                recovery_window_expected_ev_r=(
                    None if snapshot_campaign is None
                    or snapshot_campaign.latest_window_expected_ev_r is None
                    else float(snapshot_campaign.latest_window_expected_ev_r)
                ),
                recovery_window_fingerprint=(
                    None if snapshot_campaign is None
                    else snapshot_campaign.latest_window_fingerprint
                ),
                requalification_status=(
                    "PROMOTED" if snapshot_campaign is not None
                    and snapshot_campaign.state == "REQUALIFIED_ACTIVE"
                    else "PENDING"
                ),
                requalification_reason=(
                    "TWO_CONSECUTIVE_POSITIVE_WINDOWS"
                    if snapshot_campaign is not None
                    and snapshot_campaign.state == "REQUALIFIED_ACTIVE"
                    else "RECOVERY_EVIDENCE_ACCUMULATING"
                ),
            )
            return self._bucket_from_generation(active), snapshot


__all__ = (
    "AUTHORITY_POLICY_VERSION", "AuthorityMetrics", "EXPLORATION_POLICY_FLAG",
    "EXPLORATION_V2_ADMISSION_MODE", "EXPLORATION_V2_POLICY_VERSION",
    "EmpiricalRequalificationStore", "RECOVERY_AUTHORITY_WINDOW_SIZE",
    "REQUALIFICATION_FLAG", "REQUALIFICATION_MIN_DISTINCT_SYMBOLS",
    "REQUALIFICATION_MIN_NEW_V2_EXPLORATION_OBSERVATIONS",
    "REQUALIFICATION_POLICY_FLAG", "REQUALIFICATION_POLICY_VERSION",
    "REQUALIFICATION_REQUIRED_CONSECUTIVE_POSITIVE_WINDOWS",
    "RecoveryObservation", "RequalificationSnapshot", "authority_metrics",
    "recovery_window", "requalification_enabled", "requalification_predicate",
)
