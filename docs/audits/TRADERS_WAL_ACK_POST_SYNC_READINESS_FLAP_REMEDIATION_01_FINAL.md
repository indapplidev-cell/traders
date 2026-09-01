# TRADERS WAL ACK post-sync readiness flap remediation 01

```text
FINAL_VERDICT = PASS
OBSERVED_AT_UTC = 2026-09-01T13:59:13Z
PROJECT_STATE_COMMITS = 51bf7297d7b5e128db9fad4298c71870b024e426_736100d
ROOT_CAUSE = ACK_DAEMON_PUBLISHED_THE_PRE_SYNC_SNAPSHOT_AFTER_SUCCESSFUL_SYNC
USER_VISIBLE_EFFECT = READONLY_WAL_READY_AND_PITR_READY_BRIEFLY_FLAPPED_FALSE_ON_A_NEW_WAL_BACKLOG
FIX = RECAPTURE_CANONICAL_SNAPSHOT_AFTER_SYNC_AND_WAIT_FOR_ARCHIVE_COMMAND_ACK_SETTLEMENT_BEFORE_PUBLISHING_BACKLOG_PENDING_COUNTS
REPLAY_OR_TRADING_MUTATION = NONE
LIVE = DISABLED
BINANCE_ORDER_API_CALLS = 0
SECRET_OUTPUT = 0
```

The ACK owner captured `export_backlog_count > 0`, synchronously completed
`sync_wal`, but then published the counts from the pre-sync snapshot. The
Readonly readiness projection correctly treated that stale non-zero state as
not ready until the next daemon cycle. This caused a short false-negative
WAL/PITR gate even though archive continuity had no physical gap and the sync
had already completed.

The daemon cycle now captures the canonical snapshot again after a successful
sync and waits for the bounded archive-command ACK settlement. This closes the
remaining race where a first immediate post-sync recapture could still observe
the short-lived `.ready`/export pair. `published_segment_count_last_cycle`
remains the result of that sync, while `export_backlog_count` and
`pending_archive_status_count` describe the settled post-sync durable state.
The production host owner was restarted from the committed source and the
established current-user autostart remains installed.

```text
FOCUSED_DAEMON_TESTS = 7_PASSED
READONLY_RUNTIME_OBSERVATION_TESTS = 12_PASSED
COMPILE = PASS
KNOWN_BASELINE_SENSITIVE_TEST = test_foundation_and_market_data_adapter_unchanged
KNOWN_BASELINE_SENSITIVE_RESULT = FAILS_ON_PREEXISTING_BRANCH_DIFF_OUTSIDE_THIS_CHANGE
SAFE_ACK_INSPECTOR = RUNNING_IDENTITY_MATCH_HEARTBEAT_HEALTHY_BACKLOG0_PENDING0
ARCHIVE_DIAGNOSIS = PASS_NO_PHYSICAL_GAP_NO_UNRESOLVED_FAILURE
READONLY_READINESS_AFTER = READY_WALTRUE_PITRTRUE_CONTROLHEALTHY_LIVEFALSE
PAPER_OUTCOMES_COMMANDS_POSITIONS = 0_0_0
NATURAL_PLAN_STATUS = NOT_YET_OBSERVED_MONITORING_CONTINUES
```
