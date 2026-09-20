"""One immutable stage model for screen and export compatibility projections."""
from dataclasses import asdict, dataclass
from typing import Mapping


STAGE_ALIASES = {
    'ANALYSIS_QUALIFIED': 'analysis', 'STRUCTURAL_SETUP': 'setup',
    'STRATEGY_ADMITTED': 'strategy', 'RISK_COMPATIBILITY_ADMITTED': 'risk_compatibility',
    'GEOMETRY_VALID': 'geometry', 'TARGET_VALID': 'target_actionability',
    'NET_COST_PASS': 'cost', 'RR_PASS': 'rr', 'RISK_ADMITTED': 'risk',
    'PORTFOLIO_ADMITTED': 'portfolio', 'FINAL_APPROVAL': 'final_approval',
    'PAPER_PLAN': 'paper_plan',
}


@dataclass(frozen=True, slots=True)
class StageResult:
    stage_id: str
    reached: bool
    status: str
    reason_code: str | None
    raw_reason: str | None
    terminal: bool
    phase: str = 'DECISION'


def canonical_stages(trace: Mapping[str, str], reasons: Mapping[str, str | None]):
    results = []
    stopped = False
    for stage in STAGE_ALIASES:
        state = trace.get(stage, 'NOT_REACHED')
        state = 'SOURCE_UNAVAILABLE' if state == 'UNAVAILABLE' else state
        if stopped:
            state = 'NOT_REACHED'
        terminal = state in {'REJECTED', 'ERROR', 'DEFERRED'}
        reason = reasons.get(stage) if terminal else None
        results.append(StageResult(stage, state not in {
            'NOT_REACHED', 'NOT_APPLICABLE', 'NOT_EVALUATED', 'SOURCE_UNAVAILABLE', 'PENDING',
        }, state, reason, reason, terminal))
        stopped = stopped or terminal or state == 'NOT_REACHED'
    return tuple(results)


def lifecycle_stages(outcome):
    # Persisted asynchronous lifecycle facts are a separate typed phase,
    # not additional synchronous decision gates or inferred approvals.
    facts = (
        ('PAPER_COMMAND', bool(outcome.get('command_id'))),
        ('POSITION', bool(outcome.get('position_id'))),
        ('EXIT', outcome.get('exit_status') == 'REACHED'),
    )
    return tuple(
        StageResult(stage, reached, 'PASS' if reached else 'NOT_REACHED',
                    None, None, False, 'LIFECYCLE')
        for stage, reached in facts
    )


def serialize_stages(stages):
    return {stage.stage_id: asdict(stage) for stage in stages}


def compatibility_trace(stages):
    """APPROVED/WAIT remain v1 aliases; canonical_status is authoritative."""
    return {STAGE_ALIASES.get(stage.stage_id, stage.stage_id.lower()): {
        **asdict(stage), 'canonical_status': stage.status,
        'status': {'PASS': 'APPROVED', 'DEFERRED': 'WAIT', 'PENDING': 'WAIT'}.get(stage.status, stage.status),
    } for stage in stages}
