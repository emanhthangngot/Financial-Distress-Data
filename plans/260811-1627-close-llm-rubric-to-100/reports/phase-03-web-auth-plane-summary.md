# Phase 3 report — build the web auth plane

Status: code/data complete. Steps 1-4, 6, 8 done against the live Supabase
project; step 5 (seal `web-runtime-config`) and the container half of step 7
deferred to phase 4 as planned (need the live cluster's sealed-secrets key /
`docker`, which this sandbox blocks — see below).

## Step 1: migrations applied to the live project

`mcp__supabase__list_migrations` showed only 4 of the repo's 6 migrations
applied (`phase2_schema`, `phase2_rls`, `phase2_outbox_worker`,
`phase2_function_grant_hardening`) — the two newest,
`20260805090000_phase2_ai_usage_audit.sql` (defines `consume_ai_quota`,
`record_audit_event`, `ai_request_usage`) and
`20260805100000_phase2_outbox_worker_service_role_access.sql`
(`assert_worker_access`, fixes the outbox worker's claim/complete/fail RPCs),
had never been applied. Applied both via `mcp__supabase__apply_migration`
verbatim from the repo files (no hand-edits). Verified:
`consume_ai_quota`, `record_audit_event`, `claim_outbox_events`,
`assert_worker_access` all present in `information_schema.routines`.

The Supabase project (`ddvspyyullonjcuabplf`) was unreachable at phase start
(`Connection terminated due to connection timeout` on every MCP call) —
consistent with the free-tier auto-pause; resumed after the user opened the
dashboard.

## Step 2: demo/grader account

Created via direct `auth.users` insert (`pgcrypto`'s `crypt(password,
gen_salt('bf'))`, `email_confirmed_at = now()`) rather than the public
`/auth/v1/signup` endpoint — signup requires an email-confirmation send, and
the project's free-tier email rate limit was already exhausted from earlier
testing this session (`over_email_send_rate_limit`). `handle_new_user()`
(the existing `on_auth_user_created` trigger) auto-created the `profiles`
row with the default `role = 'analyst'` — no extra write needed.

One real bug hit and fixed in the process: GoTrue's Go driver cannot scan a
`NULL` `confirmation_token` (or the sibling recovery/email-change/phone-change
token columns) into its `string` field — `sql: Scan error ... converting
NULL to string is unsupported`, a known Supabase gotcha for hand-inserted
auth rows. Fixed by setting those columns to `''` instead of leaving them
`NULL`.

**Verified end-to-end against the real project** (not mocked):
- `POST /auth/v1/token?grant_type=password` → real `access_token`,
  `token_type: bearer`, `expires_in: 3600`.
- `GET /rest/v1/profiles?select=role` with that token as `Authorization:
  Bearer` → `role: analyst` (RLS-scoped read, matches `session.ts`'s own
  query shape).
- `POST /rest/v1/rpc/consume_ai_quota` with that token → real atomic
  decision (`allowed: true, quota_used: 1, rate_used: 1`), proving the
  migration from step 1 and the guard-policy RPC call path both work live.

Credential written to `docs/submission/README.md` (2026-08-11 decision:
disclosed directly, this is a coursework demo account, not a production
credential — see phase 2's credential-delivery decision for the same
reasoning applied to the gateway basic-auth secret).

## Step 3: server-side sign-in route

`apps/web/src/lib/server/sign-in-action.ts` (`authenticateWithPassword` +
`signIn` server action) and `apps/web/src/app/sign-in/page.tsx` +
`apps/web/src/components/auth/sign-in-form.tsx`. Architecture matches the
plan: `NEXT_PUBLIC_*` are inlined at Next.js build time, so runtime env into
a prebuilt image can never configure a browser-side Supabase client — the
exchange is entirely server-side (anon key stays server-side, never a
service-role key). Sets `sb-access-token` (httpOnly, `secure` in
production, `sameSite: lax`) — the exact cookie `session.ts::resolveSession`
already reads. `authenticateWithPassword` is unit-tested against a
hand-built fake `SupabaseClient` (3 cases: success, rejected credential,
null-session-no-error fallback) — `pnpm --filter web exec vitest run`:
**179 tests / 21 files passed**, coverage gate (90% global) clears.

## Step 4: data-source mode

Decision: **leave `DISTRESSLENS_DATA_SOURCE` unset** on the deployed pod.
`getDataPort()` (`lib/data/index.ts`) only special-cases the literal string
`"fixture"`; with it unset and Supabase configured (once
`web-runtime-config` is sealed in phase 4), it resolves to
`SupabaseDataPort` automatically — no values.yaml change needed, the
absence of the key is itself the decision. Nothing to implement here beyond
recording it.

## Step 5: `web-runtime-config` SealedSecret

Deferred to phase 4 by design — sealing requires the live cluster's
`sealed-secrets` controller public key. Plaintext material ready:
`NEXT_PUBLIC_SUPABASE_URL` = `https://ddvspyyullonjcuabplf.supabase.co`,
`NEXT_PUBLIC_SUPABASE_ANON_KEY` = the legacy anon key from
`mcp__supabase__get_publishable_keys` (JWT-format, `role: anon` — the
publishable key, never the service-role key).

## Step 6: provenance SHA wiring

Done in phase 2 (same commit as the digest-rewrite mechanism, so it could
not be split across phases without duplicating the CI edit):
`DISTRESSLENS_SOURCE_SHA`/`DISTRESSLENS_GITOPS_SHA` rewritten by
`phase2-ci.yaml`'s `gitops-pr` job in the same commit as the image digest
bump. See `reports/phase-02-preflight-summary.md`.

## Step 7: local proof before the window

`docker` is blocked by this sandbox's permission classifier (`docker info`
denied), so the container-level proof from the plan's exact wording could
not run here. Adapted, and the gaps are named rather than glossed over:

- `pnpm --filter @distresslens/web build` → succeeds; route manifest shows
  `/sign-in` as `ƒ` (dynamic, matches `export const dynamic =
  "force-dynamic"`), `/agents/registry` and `/api/assistant/stream` present.
- Ran the **actual production standalone server** (`node
  .next/standalone/apps/web/server.js`, `NODE_ENV=production`, real
  `NEXT_PUBLIC_SUPABASE_URL`/`ANON_KEY`) on a local port — not `docker run`,
  but the same build artifact and the same runtime Node process the
  container would run. `/`, `/sign-in`, `/agents/registry` all → `200`
  (signed-out renders the forbidden/landing state, not a crash — confirms
  `isSupabaseConfigured()` resolves and `resolveSession()` doesn't throw for
  an anonymous request).
- **Did not** curl-drive the sign-in server action itself against that
  server: Next.js Server Actions use the React Server Components action
  protocol (an action-ID-keyed POST, not a plain form submission), which
  isn't practically curl-scriptable. Substituted with the step-2 proof
  instead — `authenticateWithPassword`'s actual logic (same Supabase
  `auth.signInWithPassword` call, same client construction) was verified
  against the real project via the REST API directly, and the function
  itself is unit-tested. This is real coverage of the same code path, not
  the same artifact (a running container serving a real HTTP request) the
  plan asked for.
- **Not proven this phase**: `/api/assistant/stream` completing a real
  generation end-to-end through the container. That route also needs the
  model/agent plane, which is cluster-dependent — genuinely phase 4/5 scope,
  not something a local, cluster-down proof can reach regardless of Docker
  availability.

## Step 8: repository gates

- `pnpm --filter @distresslens/web exec tsc --noEmit` → clean.
- `pnpm --filter @distresslens/web exec vitest run` → 179/179 passed,
  coverage gate clears.
- `pnpm --filter @distresslens/web exec eslint <changed files>` → clean.
- `pnpm --filter @distresslens/web build` → succeeds.
- `.venv/bin/python scripts/run_stage1_quality_gates.py` → exit 0, `status:
  pass` (Phase 1 stage-1 evidence audit, ruff, black, pytest all green).

## Outstanding for this phase

- [ ] Seal `web-runtime-config` (phase 4, needs the live cluster).
- [ ] Prove `/api/assistant/stream` end-to-end through the deployed
      container (phase 4/5, needs the model/agent plane).
- [ ] The RSC-action-protocol gap in step 7 stays open until the real
      gateway capture in phase 5 (a browser-driven Playwright run, not
      curl, is the natural way to exercise the actual sign-in form).
