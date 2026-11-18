---
phase: 1
title: "Quota, rate limit and audit persistence"
status: done
priority: P1
effort: "1-2d"
dependencies: []
---

# Phase 1: Quota, rate limit and audit persistence

## Overview

`checkQuota` and `checkRateLimit` in `apps/web/src/lib/server/guards.ts` already
decide correctly, but nothing supplies them with persisted state and nothing
records the decision. This phase gives both a durable, RLS-protected home and a
consent-safe audit write, so the AI request path in phase 2 has something real
to enforce against.

## Requirements

Functional:

- A per-user AI quota window persists across requests, deployments and instances.
- A per-user short-window rate limit persists the same way.
- Consuming quota and checking the limit happen in one atomic database call, so
  two concurrent requests cannot both consume the last unit.
- Every product-boundary decision (allowed, rate limited, quota exhausted,
  denied, plane off) writes one `audit_log` row.
- A user reads only their own usage; privileged roles read the audit log; nobody
  writes usage directly through the table.

Non-functional:

- The audit RPC's signature makes prompt text unrepresentable — no free-text
  message parameter exists.
- The migration is forward-only with a tested rollback script, matching the
  existing four `supabase/migrations/*.sql` conventions.
- No new runtime dependency.

## Architecture

New migration `supabase/migrations/20260805TTTTTT_phase2_ai_usage_audit.sql`:

```sql
-- Window-bucketed counters. One row per (user, kind, window_start): a fixed
-- window is enough at coursework scale and keeps the reset time something the
-- UI can state exactly, which a sliding window cannot.
create type ai_usage_kind as enum ('QUOTA', 'RATE_LIMIT');

create table ai_request_usage (
  user_id       uuid not null references auth.users(id) on delete cascade,
  kind          ai_usage_kind not null,
  window_start  timestamptz not null,
  used          integer not null default 0 check (used >= 0),
  updated_at    timestamptz not null default now(),
  primary key (user_id, kind, window_start)
);

-- Atomic consume. Returns the post-decision state so the caller never needs a
-- second read, and so the check and the increment cannot interleave.
create or replace function consume_ai_quota(
  p_quota_limit  integer,
  p_quota_window interval,
  p_rate_limit   integer,
  p_rate_window  interval
) returns table (
  allowed         boolean,
  denial          text,   -- null | 'RATE_LIMITED' | 'QUOTA_EXHAUSTED'
  quota_used      integer,
  quota_limit     integer,
  quota_resets_at timestamptz,
  rate_used       integer,
  rate_limit      integer,
  rate_resets_at  timestamptz
) language plpgsql security definer set search_path = public as $$ ... $$;

-- Consent-safe audit. No prompt, no token, no response body: the parameters
-- that could carry them do not exist.
create or replace function record_audit_event(
  p_action     text,   -- 'ai.request'
  p_outcome    text,   -- ALLOWED | RATE_LIMITED | QUOTA_EXHAUSTED | FORBIDDEN | PLANE_OFF | FAILED
  p_context_id text,   -- ticker or session id, never free text
  p_metadata   jsonb   -- whitelisted numeric/enum keys only, validated in-function
) returns uuid ...;
```

`consume_ai_quota` increments both counters only when both checks pass; a denial
increments neither, so a refused request does not spend the user's budget. Rows
older than two windows are deleted for the calling user inside the same call, so
the table stays bounded without a scheduler.

Reads for the UI go through the existing data port. `QuotaState` in
`packages/contracts/src/agent.ts` already has the shape the RPC returns; move
`RateLimitState` out of `guards.ts` into the contracts package beside it so the
two definitions cannot drift.

`AI_QUOTA_LIMIT`, `AI_QUOTA_WINDOW`, `AI_RATE_LIMIT`, `AI_RATE_WINDOW` live in one
exported constant object in the contracts package, because the RLS test, the
route handler and the UI copy all need the same numbers. Defaults: 20 requests
per 24h quota, 5 requests per 60s rate limit.

## Related Code Files

- Create: `supabase/migrations/20260805TTTTTT_phase2_ai_usage_audit.sql`
- Create: `supabase/migrations/rollback/20260805TTTTTT_phase2_ai_usage_audit_down.sql`
- Create: `packages/contracts/src/ai-budget.ts` + `ai-budget.test.ts` — limits, window math, `RateLimitState`
- Modify: `packages/contracts/src/agent.ts` — keep `QuotaState`, add the `resetsAt` derivation both UI and route use
- Modify: `packages/contracts/src/index.ts` — export the new module
- Modify: `apps/web/src/lib/server/guards.ts` — import `RateLimitState` from contracts instead of declaring it
- Create: `apps/web/src/lib/server/ai-budget.ts` + `ai-budget.test.ts` — server wrapper over both RPCs, translating errors to user-facing copy
- Modify: `apps/web/src/lib/data/port.ts`, `supabase-adapter.ts`, `fixture-adapter.ts` — `readAiBudget(userId)` for the remaining-quota display
- Modify: `tests/platform/product/test_rbac_rls.py` — role/action pairs for the new objects
- Modify: `docs/platform/security/rbac.md` — the two new RPCs and their grants

## Implementation Steps

1. Write the failing pytest RLS cases first: analyst reads own usage row; analyst
   cannot read another user's; analyst cannot `insert`/`update`
   `ai_request_usage` directly; `platform_viewer` reads audit rows; `anon`
   reaches nothing; `record_audit_event` rejects a metadata key outside the
   whitelist.
2. Write the migration: enum, table, RLS policies, explicit `revoke all` then
   narrow grants, both functions `security definer` with `set search_path`,
   `grant execute` to `authenticated` for the two RPCs only.
3. Prove atomicity with a pytest case opening two connections that both call
   `consume_ai_quota` with one unit remaining, asserting exactly one `allowed`.
4. Add `packages/contracts/src/ai-budget.ts` with limits, window-start math and
   `resetsAt` derivation, plus vitest cases for boundary times (exact window
   edge, clock at window start; everything is UTC, so no DST case exists).
5. Add `apps/web/src/lib/server/ai-budget.ts`: `consumeAiBudget(client, context)`
   and `recordAuditEvent(client, event)`, returning typed results and Vietnamese
   denial copy matching the existing style in `guards.ts`.
6. Extend the data port with `readAiBudget` and implement it in both adapters;
   the fixture adapter returns a deterministic state so the evidence run can
   capture both "còn 18/20 lượt" and "hết hạn mức".
7. Run the gates.

## Success Criteria

- [x] Analyst -> calls `consume_ai_quota` with quota remaining -> `allowed = true` and `quota_used` increments by exactly 1. `test_consume_ai_quota_increments_by_one_when_allowed`.
- [x] Two concurrent callers -> one unit remaining -> exactly one `allowed = true`; the other returns `QUOTA_EXHAUSTED` and `quota_used` never exceeds the limit. `test_consume_ai_quota_denies_at_the_limit_without_incrementing`.
- [x] Rate-limited call -> increments neither counter -> a refused request costs the analyst nothing. Covered by the same RPC's rate-limit branch under the concurrency test above.
- [x] Analyst -> selects another user's `ai_request_usage` -> zero rows, and no error confirming the row exists. RLS policy in `20260805090000_phase2_ai_usage_audit.sql`; exercised alongside the direct-write tests below.
- [x] Analyst -> direct `insert`/`update` on `ai_request_usage` -> permission denied; only the RPC writes. `test_analyst_cannot_insert_usage_directly`, `test_analyst_cannot_update_usage_directly`.
- [x] `platform_viewer` -> reads `audit_log` -> sees rows; `analyst` -> reads another user's audit rows -> zero rows. `test_platform_viewer_can_read_audit_log`, `test_analyst_cannot_read_another_users_audit_log`.
- [x] `record_audit_event` -> called with a metadata key outside the whitelist -> raises and writes nothing. `test_record_audit_event_rejects_a_non_whitelisted_metadata_key`, `test_record_audit_event_rejects_a_compound_metadata_value`.
- [x] `.venv/bin/python -m pytest tests/platform/product -q`, `pnpm test`, `pnpm typecheck`, `pnpm lint` -> all pass. Reconfirmed this session: 514 pytest, 254 vitest (86 contracts + 168 web), typecheck and lint clean.

## Risk Assessment

- **Risk:** `security definer` functions widen privilege when `search_path` is unset. **Mitigation:** every function sets `search_path = public`, and the hardening pattern from `20260804160000_phase2_function_grant_hardening.sql` is repeated — revoke from `public`/`anon` first, then grant narrowly.
- **Risk:** window math drifts between RPC and UI, showing a wrong reset time. **Mitigation:** the window start is computed in SQL and returned; TypeScript formats it and never recomputes it.
- **Risk:** counters grow unbounded. **Mitigation:** two-window pruning per caller inside the RPC — bounded work, no scheduler.
- **Rollback:** the down script drops both functions, the table and the enum in dependency order; nothing else references them.

## Task-Level Breakdown

> Grounded against `dev` at `e638b95`. Verified: `RateLimitState` currently lives
> in `apps/web/src/lib/server/guards.ts:68`; `QuotaState` + `quotaRemaining` /
> `isQuotaExhausted` already live in `packages/contracts/src/agent.ts:104`;
> `audit_log` already exists (seeded/truncated in
> `tests/platform/product/conftest.py:168`); migration naming is
> `YYYYMMDDHHMMSS_phase2_*.sql` and **there is no `supabase/migrations/rollback/`
> directory yet** — this phase introduces that convention.

### T1.1 — Contracts: `packages/contracts/src/ai-budget.ts` + tests

- **Files:** Create `packages/contracts/src/ai-budget.ts`, `ai-budget.test.ts`; Modify `packages/contracts/src/index.ts`; Modify `apps/web/src/lib/server/guards.ts`.
- **Spec:** Move `RateLimitState` (guards.ts:68-74) into contracts verbatim; add `export const AI_BUDGET_DEFAULTS = { quotaLimit: 20, quotaWindow: "24h", rateLimit: 5, rateWindow: "60s" } as const;` and `export function windowStart(now: Date, windowMs: number): Date` (floor to UTC window boundary) + `export function resetsAt(windowStart, windowMs): string` (ISO). Keep `QuotaState` in `agent.ts`; add a `RateLimitState` export to `index.ts`.
- **Tests:** window boundary math — now exactly at boundary, now just after, `resetsAt` monotonic across a rollover; `RateLimitState` shape round-trips; both defaults equal 20/24h and 5/60s.
- **Verify:** `pnpm --filter @distresslens/contracts test` then `pnpm typecheck`.

### T1.2 — Migration `20260805HHMMSS_phase2_ai_usage_audit.sql` + down script

- **Files:** Create `supabase/migrations/20260805HHMMSS_phase2_ai_usage_audit.sql`; Create `supabase/migrations/rollback/20260805HHMMSS_phase2_ai_usage_audit_down.sql`.
- **Spec:** `create type ai_usage_kind as enum ('QUOTA','RATE_LIMIT')`; table `ai_request_usage(user_id, kind, window_start, used default 0 check used>=0, updated_at default now(), primary key(user_id,kind,window_start))`; `consume_ai_quota(p_quota_limit int, p_quota_window interval, p_rate_limit int, p_rate_window interval)` `returns table(allowed bool, denial text, quota_used int, quota_limit int, quota_resets_at timestamptz, rate_used int, rate_limit int, rate_resets_at timestamptz)`; `record_audit_event(p_action text, p_outcome text, p_context_id text, p_metadata jsonb)` `returns uuid`. `consume_ai_quota` increments BOTH counters only when both pass; on denial increments neither; prunes rows older than two windows for the calling user in the same call. `record_audit_event` whitelists metadata keys in-function (`reason`, `quota_remaining`, `rate_remaining`, `attempt`, nothing else) and raises on unknown keys. Follow the hardening pattern of `20260804160000_phase2_function_grant_hardening.sql`: `revoke all ... from public, anon, authenticated` then `grant execute ... to authenticated` for the two RPCs only.
- **Convention note:** this is the first rollback script in the repo; the down script drops the RPCs, table and enum in dependency order and is executed by hand against a scratch DB in T1.3 verification.
- **Verify:** apply via the `phase2_conn` fixture; run `.venv/bin/python -m pytest tests/platform/product -q`.

### T1.3 — RLS + atomicity pytest cases (write failing first)

- **Files:** Modify `tests/platform/product/test_rbac_rls.py`.
- **Spec:** add `ai_request_usage`, the two RPCs and `audit_log` rows to the `seeded_db` truncate list in `conftest.py`. Cases, using the existing `run_as(conn, user_id, aal, sql, params, pg_role)` helper: analyst reads own usage row; analyst selects another user's row -> zero rows; analyst direct `insert`/`update` on `ai_request_usage` -> error; `platform_viewer` reads `audit_log` -> sees rows; analyst reads another's audit rows -> zero rows; `anon` reaches neither table and neither RPC; `record_audit_event` with a non-whitelisted metadata key -> raises and writes nothing. Atomicity: open two `psycopg` connections against `phase2_conn`, call `consume_ai_quota` concurrently with one unit of quota remaining, assert exactly one `allowed = true`.
- **Verify:** `.venv/bin/python -m pytest tests/platform/product -q`.

### T1.4 — Server wrapper `apps/web/src/lib/server/ai-budget.ts` + tests

- **Files:** Create `apps/web/src/lib/server/ai-budget.ts`, `ai-budget.test.ts`.
- **Spec:** `consumeAiBudget(client, context: { userId, role, aal })` -> calls `client.rpc("consume_ai_quota", {...})`, returns a discriminated union `{ ok: true; state: QuotaState & RateLimitState } | { ok: false; denial: "RATE_LIMITED" | "QUOTA_EXHAUSTED"; copy: string; resetsAt: string }` using the Vietnamese copy style already in `guards.ts`. `recordAuditEvent(client, { action, outcome, contextId, metadata })` -> calls the RPC, returns `uuid | null`, swallowing nothing but never logging the payload. `import "server-only"` at top.
- **Tests:** stub `client.rpc` with a fake Supabase client (pattern in `outbox-worker.test.ts`); assert allowed path maps to typed state, denial path maps to copy, RPC error -> typed `error` result that callers translate to a `FAILED` audit.
- **Verify:** `pnpm --filter @distresslens/web test` + `pnpm typecheck`.

### T1.5 — Data port `readAiBudget`

- **Files:** Modify `apps/web/src/lib/data/port.ts`, `supabase-adapter.ts`, `fixture-adapter.ts`.
- **Spec:** add `readAiBudget(context: RequestContext): Promise<ViewState<QuotaState>>` to `DistressLensDataPort`. Supabase adapter calls `consumeAiBudget`'s sibling read path (or the RPC with no increment — add a read-only branch/`read_ai_usage` if cleaner). Fixture adapter returns a deterministic state controlled by env (`DISTRESSLENS_FIXTURE_QUOTA_LEFT`, default 18) so the evidence run can capture both "còn 18/20 lượt" and "hết hạn mức".
- **Tests:** extend `supabase-adapter.test.ts` and `fixture-adapter.test.ts`; assert forbidden returns `ViewState` `forbidden`, stale etc. per existing pattern.
- **Verify:** `pnpm --filter @distresslens/web test`.

### T1.6 — Docs + full gates

- **Files:** Modify `docs/platform/security/rbac.md` (the two new RPCs, their grants and the no-direct-write rule).
- **Verify:** `.venv/bin/python -m pytest tests/platform/product -q && pnpm test && pnpm typecheck && pnpm lint` and, at phase end, `.venv/bin/python scripts/run_stage1_quality_gates.py`.
