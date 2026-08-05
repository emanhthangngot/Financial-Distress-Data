---
phase: 3
title: "Outbox worker runtime"
status: in_progress
priority: P1
effort: "1-2d"
dependencies: []
---

# Phase 3: Outbox worker runtime

## Overview

`drainOutbox` in `apps/web/src/lib/server/outbox-worker.ts` is a tested library
with no caller. Until a process runs it, an operator's provision request writes
an intent that nothing ever claims, and the session sits in `REQUESTED` forever.
This phase gives it a runnable process, a handler registry, an operational
contract, and proof that leases and fencing behave under a real database.

## Requirements

Functional:

- A long-running process claims outbox events with a lease, dispatches each to a
  handler, and reports completion or failure.
- Handlers are registered per `target_state`; an event with no registered handler
  fails loudly with a named error rather than silently succeeding.
- Until phase-03 of the parent plan brings up the GitOps dispatch, the registered
  handler performs the state-advance half only, and records explicitly that no
  infrastructure was contacted.
- A superseded event's completion is refused as stale fencing and marked FAILED
  without mutating the session.
- Two concurrent workers never claim the same event.
- The process exits cleanly on `SIGTERM`/`SIGINT`, finishing the in-flight batch
  and releasing nothing half-claimed.
- Graceful degradation: a claim error backs off and retries rather than exiting.

Non-functional:

- Uses the service-role key and never runs inside a request handler — enforced by
  the existing `server-only` import boundary plus a startup assertion.
- Structured single-line logs carrying event id, target state, attempt and
  outcome; never the fencing token, never the service-role key.
- Runnable locally with `pnpm --filter @distresslens/web outbox:worker` and as a
  container entrypoint later, with no code change.

## Architecture

```
scripts/phase2/outbox-worker.ts        # entrypoint: env, client, loop, signals
  -> src/lib/server/outbox-handlers.ts # registry: target_state -> handler
  -> src/lib/server/outbox-worker.ts   # existing drainOutbox, unchanged
```

The loop is deliberately simple: `drainOutbox`, sleep `POLL_INTERVAL_MS` when the
batch was empty, sleep nothing when it was full (a full batch means there is more
work). Backoff on claim failure is exponential with a cap, so a database blip
does not become a hot retry loop.

`drainOutbox` itself is not modified. Its guarantees already come from
`claim_outbox_events`, `complete_outbox_event` and `fail_outbox_event`; this
phase adds the caller and proves those guarantees against a real Postgres rather
than a stubbed client.

The handler signature stays `(event) => Promise<string>` — the returned string is
the audited result summary. The GitOps dispatcher of parent phase-03 replaces the
registered handler body without touching the loop, the registry shape or the
worker's operational contract.

## Related Code Files

- Create: `scripts/phase2/outbox-worker.ts` — entrypoint, signal handling, backoff loop
- Create: `apps/web/src/lib/server/outbox-handlers.ts` + test — registry, unknown-state failure, no-infrastructure placeholder handler
- Modify: `apps/web/package.json` — `outbox:worker` script
- Create: `tests/phase2/product/test_outbox_worker.py` — lease, concurrency and fencing behavior against the ephemeral Postgres the RLS suite already boots
- Modify: `docs/phase2/product.md` — how to run the worker, what it guarantees, what it does not yet do
- Modify: `docs/phase2/architecture.md` — the worker's place in the lifecycle path (only if the current diagram omits it)

## Implementation Steps

1. Write `outbox-handlers.ts` tests first: a registered state dispatches; an
   unregistered state throws a named error; the placeholder handler returns a
   result string that states no infrastructure was contacted.
2. Implement the registry and the placeholder handler.
3. Write the entrypoint: read `SUPABASE_URL`/service-role key, assert both are
   present (exit non-zero with a clear message otherwise), build the client,
   derive a stable `workerId` from hostname + pid, run the loop, install signal
   handlers that stop after the current batch.
4. Write the pytest integration cases against the ephemeral Postgres used by
   `tests/phase2/product/conftest.py`: two workers claim disjoint sets; an
   expired lease returns the event to the pool; a completion after a superseding
   transition is refused as stale fencing and the event ends FAILED; attempts
   beyond `maxAttempts` stop being retried.
5. Add the package script and document the operational contract.
6. Run the gates plus the new pytest module.

## Success Criteria

- [x] Operator -> requests a provision -> the worker claims the event within one poll interval, completes it, and the session advances to the target state. Proven at the SQL layer: `request_session_transition` sets the session's state atomically with the outbox insert; `test_two_workers_claim_disjoint_event_sets`/`test_fail_below_max_attempts_returns_to_pending` (`tests/phase2/product/test_outbox_worker.py`) exercise claim through complete against a real Postgres.
- [x] Two workers -> run against the same queue -> claim disjoint event sets; no event is handled twice. `test_two_workers_claim_disjoint_event_sets`.
- [x] A worker -> is killed mid-lease -> the event returns to the pool after the lease expires and another worker completes it. `test_expired_lease_returns_event_to_pool`.
- [x] A transition supersedes an in-flight event -> the worker's `complete_outbox_event` is refused as stale fencing -> the event is FAILED and the session is unchanged. `test_completion_after_superseding_transition_is_stale_fencing`. Fixed a real defect this test caught: the original SQL raised an exception on stale fencing, which rolled back the very FAILED mark it was supposed to leave (Postgres aborts a statement's implicit transaction on an uncaught exception) — `complete_outbox_event` now returns the FAILED row instead of raising (`supabase/migrations/20260805100000_phase2_outbox_worker_service_role_access.sql`); `drainOutbox` reads `data.status` accordingly.
- [x] An event whose `target_state` has no handler -> fails with a named error, increments attempts, and never reports success. `outbox-handlers.test.ts` (`NoOutboxHandlerError`) composes with the existing `drainOutbox` fail-path test.
- [x] Worker receives `SIGTERM` -> finishes the in-flight batch, exits 0, leaves no event claimed past its lease. `outbox-worker-loop.test.ts` proves the shutdown ordering (`ShutdownController`); the entrypoint (`scripts/phase2/outbox-worker.ts`) wires it to `SIGTERM`/`SIGINT`.
- [ ] Worker logs after a full run -> contain event ids and outcomes, and contain no fencing token and no service-role key. Not automated — no test captures and asserts on log output; code review confirms the `log()` calls in `scripts/phase2/outbox-worker.ts` never reference the fencing token or the service-role key, but that is inspection, not a runnable check.
- [x] `.venv/bin/python -m pytest tests/phase2/product -q`, `pnpm test`, `pnpm typecheck`, `pnpm lint` -> pass. 44/44 pytest, 196/196 vitest (71 contracts + 125 web), typecheck and lint clean on this branch.

## Risk Assessment

- **Risk:** the placeholder handler is mistaken for real provisioning and an operator believes infrastructure exists. **Mitigation:** the result string and the audit row state that no infrastructure was contacted, and the ops UI renders that result verbatim.
- **Risk:** the service-role key leaks into the web bundle. **Mitigation:** the worker lives under `scripts/`, imports only `server-only`-marked modules, and a test asserts the key name appears in no file under `apps/web/src/app`.
- **Risk:** a poison event retries forever. **Mitigation:** `maxAttempts` is already enforced by `fail_outbox_event`; the pytest case pins that behavior.
- **Rollback:** the worker is additive — stopping the process restores exactly the current behavior (intents recorded, nothing claimed).

## Task-Level Breakdown

> Grounded against `dev` at `e638b95`. Verified: `drainOutbox` already exists with
> signature `(client, handle: OutboxHandler, options: WorkerOptions) => Promise<DrainResult>`
> (outbox-worker.ts:48) and calls `claim_outbox_events` / `complete_outbox_event` /
> `fail_outbox_event`; the SQL guarantees (lease via `for update skip locked`,
> stale-fencing refusal, `maxAttempts`) live in
> `supabase/migrations/20260804150000_phase2_outbox_worker.sql`. The RLS pytest
> harness (`tests/phase2/product/conftest.py`) boots an ephemeral real Postgres —
> the worker integration cases reuse it.

### T3.1 — Handler registry

- **Files:** Create `apps/web/src/lib/server/outbox-handlers.ts`, `outbox-handlers.test.ts`.
- **Spec:** `export type OutboxHandlerRegistry = Record<string, OutboxHandler>`; `export function createOutboxHandlerRegistry(): { register(targetState: SessionState, handler: OutboxHandler): void; handle(event: OutboxEventRow): Promise<string> }`. `handle` throws `NoOutboxHandlerError` (named, exported) when no handler is registered for `event.target_state`. Register the placeholder: `"REQUESTED"` handler resolves `"state-advance-only: no infrastructure contacted (GitOps dispatch lands in parent phase-03); session already in REQUESTED"`. `import "server-only"` and import `OutboxEventRow`/`OutboxHandler` from `./outbox-worker`.
- **Tests (write first):** registered state dispatches and returns the handler's string; unregistered state throws `NoOutboxHandlerError`; placeholder result string contains `no infrastructure contacted` and the target state.
- **Verify:** `pnpm --filter @distresslens/web test`.

### T3.2 — Worker entrypoint

- **Files:** Create `scripts/phase2/outbox-worker.ts`; Modify `apps/web/package.json`.
- **Spec:** reads `NEXT_PUBLIC_SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`, exits non-zero with a clear message if either is missing; imports `createServiceClient` (server-only boundary, never a request handler); derives `workerId = \`${os.hostname()}-${process.pid}\``; runs `drainOutbox` in a loop — sleep `POLL_INTERVAL_MS` (default 3000) after an empty batch, no sleep after a full one; exponential backoff (1s, 2s, 4s… capped 30s) on claim failure instead of exiting; installs `SIGTERM`/`SIGINT` handlers that stop after the current batch and exit 0. Emit single-line structured JSON logs with event id, target state, attempt, outcome — never the fencing token, never the service key. Note: a full-batch flush happens in the same iteration, so the in-flight batch always finishes before exit.
- **Tests:** unit-test the backoff schedule and the signal-shutdown ordering by extracting a `buildLoop(cfg)` pure function; the real lease/fencing behavior is covered by T3.3 pytest. Manual smoke: `SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... pnpm --filter @distresslens/web outbox:worker`.
- **Verify:** `pnpm --filter @distresslens/web typecheck`.

### T3.3 — Lease/fencing integration pytest

- **Files:** Create `tests/phase2/product/test_outbox_worker.py`.
- **Spec:** against the ephemeral Postgres from `conftest.py`, call the SQL functions directly with a fake `workerId`; cases: two workers (`w1`, `w2`) claim disjoint event sets (insert several `outbox_events` rows via `request_session_transition`); a claimed event whose lease has passed (`lease_expiry < now()`) is reclaimable by another worker; `complete_outbox_event` with a rotated fencing token (perform a second `request_session_transition`) -> raises `stale fencing token` and the event row ends `FAILED` with session unchanged; `fail_outbox_event` beyond `maxAttempts` -> event stays `FAILED`, before the cap -> returns to `PENDING`.
- **Verify:** `.venv/bin/python -m pytest tests/phase2/product -q`.

### T3.4 — Package script + docs + full gates

- **Files:** Modify `apps/web/package.json` (`"outbox:worker": "tsx scripts/phase2/outbox-worker.ts"` or the ts-node runner this repo uses — check `pnpm` workspace conventions first); Modify `docs/phase2/product.md` (how to run the worker, guarantees, what it does not yet do); Modify `docs/phase2/architecture.md` only if the lifecycle diagram omits the worker.
- **Verify:** `.venv/bin/python -m pytest tests/phase2/product -q && pnpm test && pnpm typecheck && pnpm lint`.
