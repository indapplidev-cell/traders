# TRADERS 5m SHADOW full-funnel enablement 01

```text
TASK = TRADERS_5M_SHADOW_FULL_FUNNEL_ENABLEMENT_01
RESULT = PASS_SOURCE_IMPLEMENTATION
FINAL_VERDICT = PASS_NON_EXECUTABLE_5M_SHADOW_ANALYSIS_TO_WINNER_ROUTE
PROJECT_STATE_COMMIT = SELF
PROJECT_STATE_COMMIT_RESOLUTION = git log -1 --format=%H -- docs/audits/TRADERS_5M_SHADOW_FULL_FUNNEL_ENABLEMENT_01_FINAL.md
RECONCILED_AT_UTC = 2026-08-20T18:59:40Z
BRANCH = feature/engine-platform
PRODUCTION_DEPLOYMENT = NOT_PERFORMED_NOT_AUTHORIZED
SCHEMA_CHANGE = NONE
LIVE = DISABLED
```

## Scope and root cause

The 5m profile already evaluated analysis, setup, strategy and risk, but its
`SHADOW_SEARCH` branch stopped before the PAPER planner. The persistence and
funnel projection then exposed only a diagnostic candidate. As a result,
`PAPER_TRADE_PLAN`, quantity, validity, final approval, eligibility and winner
could never pass by construction, regardless of market direction.

This change gives the 5m profile a complete non-executable SHADOW analogue of
the 15m decision route. It does not weaken strategy, risk, RR, cost, spread or
liquidity admission criteria and does not manufacture a winner for a rejected
candidate.

## Implemented route

```text
ANALYSIS
-> STRUCTURAL_SETUP
-> STRATEGY_ELIGIBLE
-> RISK_APPROVED
-> SHADOW PAPER_TRADE_PLAN
-> SHADOW QUANTITY_APPROVED
-> SHADOW VALIDITY_APPROVED
-> SHADOW FINAL_APPROVAL
-> SHADOW ELIGIBLE
-> SELECTOR_WINNER
```

- `PaperRunner` is reused as a pure planner for `SHADOW_SEARCH`; the persisted
  top-level status remains `SHADOW_SEARCH`.
- The shadow materializer applies the authoritative PAPER account projection,
  the same instrument constraints and the same quantity math, but emits only
  `shadow_*` approvals.
- The funnel projection accepts a fully proven shadow candidate into the same
  deterministic selector and reports all ten stages.
- Shadow eligibility and winner status are explicitly separated from execution
  eligibility.

## Safety proof

For a successful 5m shadow winner, all of the following remain false:

```text
final_approval_created = false
execution_eligible = false
is_trade_signal = false
is_executable = false
order_approved = false
execution_approved = false
position_size_approved = false
position_opened = false
```

No `persisted_final_approvals`, PAPER command, order, fill or position is
created by the shadow path. The existing SHADOW/PAPER firewall therefore
remains intact.

## Validation

```text
NEW_5M_FULL_FUNNEL_TESTS = 4_PASSED
EXPANDED_FOCUSED_REGRESSION = 85_PASSED_5_SKIPPED
AFFECTED_ENGINE_API_REGRESSION = 258_PASSED_11_SKIPPED
ADDITIONAL_SELECTED_REGRESSION = 548_PASSED_11_SKIPPED_1_ENVIRONMENT_ERROR
COMPILEALL = PASS
GIT_DIFF_CHECK = PASS_LINE_ENDING_WARNINGS_ONLY
```

The repository-wide diagnostic run completed with `30635 passed`, `29
skipped`, `436 failed`, and `342 errors`. It is not recorded as PASS. The
last-failed inventory is outside the modified engine/API scope: it includes
PostgreSQL suites requiring absent `BASELINE_TEST_DATABASE_URL` or
`PAPER_TEST_DATABASE_URL`, and frozen historical migration contracts expecting
older schema heads (including `0014` while the current repository uses newer
revisions). The complete affected engine/API scope passed independently.

## Runtime corroboration and limits

The production containers remained healthy and were not rebuilt or restarted.
The production database and trading state were not mutated. Source acceptance
does not equal deployment acceptance; the running 5m service continues to use
the prior artifact until a separately authorized controlled deployment.

Recent production 5m risk-pre-approved observations inspected during diagnosis
had planned reward/risk values below the existing `1.5` minimum. Therefore the
new route removes the structural impossibility, but those particular market
candidates must still be rejected honestly. A bullish market alone is not a
reason to bypass net-edge and RR gates.

```text
NEXT_ACTION = SEPARATELY_AUTHORIZE_CONTROLLED_5M_SHADOW_DEPLOYMENT_AND_OBSERVE_NATURAL_FULL_FUNNEL_SAMPLE
```
