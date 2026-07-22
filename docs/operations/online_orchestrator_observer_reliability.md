# Online orchestrator observer reliability contract

The observer is a read-only, filesystem-state process. It does not supervise or
restart PostgreSQL, market-data-sync, online-orchestrator, or any other service.

## Ownership

One Python worker owns one soak directory. It holds `observer.lock` for its
entire lifetime and writes its actual PID to `observer.pid` plus typed metadata
to `observer_process.json`. A second writer is rejected. The lock uses a
non-blocking operating-system lock; an active live-process record is never
removed. A released record can be reused. A crash record is recovered only
after process absence or identity mismatch is established, and recovery is
written to `incident_log.jsonl`.

`observer_run_id` is persisted in `observer_run.json` for the soak directory.
Every process start receives a fresh `observer_instance_id`; sample identity is
the pair `(observer_instance_id, sample_sequence)`, with instance sequence
starting at one. Existing JSONL files are only appended to.

## Heartbeat and scheduling

`observer_heartbeat.json` uses `OBSERVER_HEARTBEAT/1.0` and is updated by an
in-process heartbeat thread using flush, fsync, and atomic replace. Heartbeats
continue while bounded collectors execute or fail. Heartbeat states are
`STARTING`, `RUNNING`, `DEGRADED`, `STOPPING`, `STOPPED`, and `FAILED`.
Heartbeat history is durably appended to `heartbeat_history.jsonl`.

Sampling is scheduled against a monotonic clock at fixed boundaries. The policy
is `SKIP_MISSED_INTERVALS_AND_RECORD_GAP`: an overrun never causes burst
catch-up or invented historical samples. Wall-clock UTC is used only for
persisted timestamps. The default interval is 60 seconds, allowed jitter is 15
seconds, and the default threshold is 75 seconds. A gap is measured between
scheduled boundaries, not collector completion timestamps.

## Collector isolation and persistence

Docker commands use a subprocess timeout. PostgreSQL collection, when enabled
through `OBSERVER_READ_ONLY_DSN`, uses connection timeout, statement timeout,
and transaction read-only guards. File reads are size bounded. Each collector
returns `SUCCESS`, `PARTIAL`, `TIMEOUT`, `UNAVAILABLE`, or `FAILED`; one failure
does not cancel other collectors or terminate the process. Consecutive failures
move self-health to `DEGRADED`.

Each JSONL record is exactly one UTF-8 JSON object terminated by a newline and
is flushed and fsynced. The single-instance lock excludes other observer
writers. Existing artifact names remain readable and receive additive metadata:
schema version, instance ID, sequence, recorded time, scheduled time, and record
type. Persistence and error strings pass through recursive credential
redaction. A primary artifact write failure causes a nonzero exit and a
redacted best-effort report outside the soak directory.

## Stop and restart

Ctrl+C or atomically creating `observer.stop.request` is the controlled-stop
mechanism. The process writes `STOPPING`, completes any atomic write, flushes
artifacts, creates `observer_final_state.json` and `observer_shutdown.json`,
writes `STOPPED`, and releases the lock. Each final state is also preserved in
`observer_final_states.jsonl`. A later start creates
`observer_restart_report.md`; a clean prior stop is `CONTROLLED_RESTART`, while
stale active metadata is `ABRUPTLY_TERMINATED` / `PROCESS_NOT_RUNNING`.

Example isolated canary:

```powershell
python scripts/engine_observer_reliability.py `
  --soak-directory D:\path\to\isolated_canary `
  --repository D:\path\to\traders-ml `
  --sampling-interval-seconds 30 `
  --heartbeat-interval-seconds 5 `
  --maximum-runtime-seconds 1800
```

Stop from another terminal:

```powershell
python scripts/engine_observer_reliability.py --soak-directory D:\path\to\isolated_canary --request-stop
```
