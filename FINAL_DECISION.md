# Final decision — 5m scalping analysis report export 01

`TRADERS_5M_SCALPING_ANALYSIS_REPORT_EXPORT_01` completed with PASS for the
reporting criterion. This verdict does not assert profitable trading.

The stable Readonly API snapshot covers 2026-08-24T18:05:00Z through
2026-08-25T07:45:00Z: 165 homogeneous 5m boundaries, 1,650 symbol evaluations,
100% completeness, exact batches of ten, and zero missing/duplicate/cursor
collisions. Nine bounded keyset pages were aggregated locally.

The Funnel contains 170 structural setups, four strategy admits and four valid
causal geometries. All four are consecutive observations of one SOLUSDT LONG
opportunity. Gross RR median is 0.0433, expected net edge median is -24.9448
bps, and RR 1.0/1.2/1.5 each pass 0. There are no plans, approvals, commands,
positions or closed PAPER trades. Expert status is `NOT_READY`; profitability
confidence is insufficient.

Fresh post-commit safety evidence remains WAL/PITR true/true, lineage valid,
physical gap false, backlog/pending/unresolved 0/0/0, Control ARMED generation
6, LIVE disabled, schema 0018, and one 5m singleton owner. The Readonly runtime
is healthy on the same container/image but its restart counter is now one;
Docker reports exit code 0 and `OOMKilled=false`. This task issued no restart,
recreate, Control, schema, trading, parameter, LIVE, or Binance order command.

```text
TASK_STATUS = PASS
FINAL_VERDICT = PASS_COMPLETE_REPRODUCIBLE_HOMOGENEOUS_READONLY_REPORT
EXPERT_STATUS = NOT_READY
STATUS_AS_OF_COMMIT = 6a2df4ca70a0404978b1cb41cab0c4ffaa830a46
DOCUMENTATION_COMMIT_RESOLUTION = git log -1 --format=%H -- online_trader.md
REPORT_FILE = D:\disk_E\game_projects\traders\evidence_inbox\TRADERS_5M_SCALPING_ANALYSIS_REPORT_20260824T1805_20260825T0745.md
REPORT_FULL_SHA256 = aeb99e5fa77cd85137b3ea249ce9a80aac62c27abab5e929d4a2f2465f0fb4c4
REPORT_BODY_SHA256 = 57854de94be5255882bd7e60e2bd508d2166afd89295af8851de1249efccaba5
FOCUSED_TESTS = 16_PASSED
PRODUCTION_5M_PARAMETER_CHANGES_BY_TASK = 0
PRODUCTION_15M_PARAMETER_CHANGES_BY_TASK = 0
PRODUCTION_TRADING_MUTATIONS_BY_TASK = 0
BINANCE_ORDER_API_CALLS_BY_TASK = 0
PUSHED = NO
```
