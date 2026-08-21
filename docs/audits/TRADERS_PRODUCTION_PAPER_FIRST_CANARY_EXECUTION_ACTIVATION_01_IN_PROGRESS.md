# Production PAPER first-canary execution activation 01

## Verdict

`IN_PROGRESS_WAITING_FOR_NATURAL_ELIGIBLE_APPROVAL` as of
`2026-08-21T05:14:05Z`.

The production execution contour is now deployed and running for the already
authorized first canary.  It remains bounded to one command and one position,
uses persisted live-market closed 1m candles with simulated fills, has no
Binance order-call authority, and leaves LIVE disabled.  No natural eligible
approval has appeared yet, so no command, order, fill, position, fee, or PnL
fact exists and first-trade acceptance is not claimed.

## Source and validation

- implementation commit: `50fc66f93fa6199a934e45b7be77725eef50e2e8`;
- advisory-lock correction commit:
  `3be22bdf98d199594b9bdd544389714329c4ea22`;
- focused Operator Control regression: `58 passed`, zero failed;
- canonical PostgreSQL 16 full lifecycle at schema head 0017: `1 passed`,
  proving the existing exact graph of one command, two orders, two fills, one
  position, one cursor, one exit decision, eight order events and twelve
  journal entries;
- the task-owned isolated PostgreSQL container was removed after the proof.

The first deployment of `50fc66f` was not accepted: the newly added thread
called a nonexistent advisory-lock method and therefore could not execute a
lifecycle stage.  It produced zero business mutations.  The defect was fixed
in `3be22bd`, regression-tested, rebuilt, and redeployed before acceptance.

## Accepted production runtime

- Operator Control container: `cc0c783dc415`;
- image: `sha256:0d0699328de39de10be6a5ccc83921fddecd96b16b367ca00fcd21d9a6f61d7d`;
- source identity:
  `3be22bdf98d199594b9bdd544389714329c4ea22`;
- health: `healthy`, restart count `0`;
- authenticated probe: 3 GET / 5 POST, safe read PASS, unauthenticated and
  invalid-token mutation rejection PASS, no secret output;
- control: `ARMED`, effective `ARMED`, generation `6`, audit PASS;
- approval continuation: active, 30-second polling;
- lifecycle continuation: composed and running, 10-second polling;
- lifecycle mutation bound: at most one atomic stage per poll through the
  authoritative production mutation safety gate;
- market input: production persisted closed 1m candles only, maximum 512 per
  snapshot;
- fill policy: next eligible closed 1m open, one-candle latency, 2 bps adverse
  slippage, 10 bps fee per fill, no partial fill, no future data, stop-first
  conservative intrabar resolution;
- terminal action: after exact CLOSED graph, transition the bounded control to
  DISABLED, require the authoritative trade report and both reconciliations,
  then seal the canary correlation as COMPLETED or leave it
  RECONCILIATION_PENDING for safe retry.

## Current natural observation

- canary: `6f9858cd-f6b1-4c7f-810c-fccc1065bb9d`;
- status: `WAITING_FOR_ELIGIBLE_APPROVAL`;
- limits/counts: command `0/1`, position `0/1`, closed trade `0`;
- PAPER account: initial/current `100 USDT`, fees `0`, realized net PnL `0`;
- PAPER rows exposed by Readonly: orders `0`, fills `0`, journal `0`;
- WAL/PITR: true/true;
- LIVE allowed: false;
- latest observed complete 5m boundary: `1787289000000`, 10/10 processed,
  structural setup 0, strategy eligible 0, final approval 0, selector winner 0;
- rolling 4h final approvals: 0.

## Full-log contract

Every committed stage emits a structured `paper_canary_lifecycle_stage` record
to the Operator Control container log containing canary, command, stage,
before/after lifecycle state, child outcome/reason, mutation-commit flag and
position identity.  Finalization emits `paper_canary_finalized` with report and
reconciliation status plus total fees, net PnL and ROI.  The durable
authoritative transaction log remains the database graph: command, orders,
fills, position, cursor, exit decision, eight order events and twelve journal
entries.  After closure these facts and the Readonly report must be exported
into the final acceptance evidence.

## Stop condition and next action

Continuous PAPER trading is not enabled.  It may be implemented and enabled
only after this exact canary naturally creates a command, reaches CLOSED,
produces a complete report, passes paper/accounting reconciliation, and the
control is DISABLED.  Until then the correct state is controlled observation,
not PASS and not continuous-worker activation.
