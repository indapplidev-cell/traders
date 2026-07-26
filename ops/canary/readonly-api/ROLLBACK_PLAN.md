# Readonly API canary rollback plan

Any stop criterion rejects the canary and triggers this plan:

1. Stop the canary service with the exact project name, env file, Compose file,
   profile, and service from the runbook.
2. Remove the canary container; never remove unrelated containers.
3. Preserve only redacted logs and evidence outside Git.
4. Verify existing market-data, orchestrator, database, and other services are
   unchanged and were not restarted.
5. Re-run and compare database row counts, content hashes, Alembic version, and
   schema object inventory; all must be unchanged.
6. Remove only the task-owned canary network after the container is gone.
7. Retain or remove the immutable canary image only by explicit operator
   decision.
8. Do not run Alembic downgrade: the canary has no migration authority.
9. Do not restart unaffected services.
10. Mark the canary rejected, record the triggering stop criterion, and require
    a new evidence-backed authorization before another attempt.

Rollback removes only canary runtime resources; it never mutates production
data or compensates with database writes.
