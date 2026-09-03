# the platform Product RBAC and Security Boundary

This document is the security contract for the product-plane routes in
`docs/platform/product.md`. It complements Supabase RLS and server-side
authorization tests; hiding a button in the browser is never an authorization
control.

## Roles and actions

| Role | Read analyst data | Run bounded AI | Read platform/evidence | Lifecycle mutate | Promote/rollback | Manage roles |
|---|---:|---:|---:|---:|---:|---:|
| `analyst` | own/allowed companies | yes, quota-bound | no | no | no | no |
| `platform_viewer` | no analyst mutation | no | yes | no | no | no |
| `platform_operator` | no analyst mutation | no | yes | provision/retry/destroy/export | no | no |
| `platform_admin` | no analyst mutation | no | yes | all operator actions | yes, with lease/fencing | no client path -- the `role` column has no `authenticated` grant at all (see `supabase/migrations/20260814200000_phase2_profile_identity.sql`); role changes are SQL/service-role only |

The effective permission is the intersection of the role, the tenant/user
scope, the route policy and the current evidence-plane state. A denied action
must be rejected by both the Next.js server boundary and the database policy.

## Authentication and request rules

- Supabase Auth is the identity source. `platform_operator` and
  `platform_admin` privileged actions are gated on a step-up check
  (`meets_step_up()` in the database, `STEP_UP_REQUIRED` in
  `packages/contracts/src/authorization.ts`), which is currently relaxed to
  allow a password-only (AAL1) session in this demo environment -- see
  `docs/platform/adr/adr-015-aal2-step-up-relaxation.md` for why and the revert
  path. `is_aal2()` itself still reports the real assurance level.
- Server actions/API handlers validate the signed session, role claim, origin/
  CSRF policy, request schema and rate limit before touching data or an outbox.
- The assistant stream route (`POST /api/assistant/stream`) authorizes
  `analyst.run_ai_request`, spends budget atomically through
  `consume_ai_quota()`, audits exactly one row per outcome, and bounds the whole
  upstream interaction with `ASSISTANT_TIMEOUT_MS` below the hosting response
  limit — a silent upstream cannot hold the route open, and the response emits a
  `timeout` frame rather than a dead connection.
- Lifecycle mutations require a client idempotency key, a fresh fencing token,
  and a lease owned by the current actor. Replays return the original result;
  stale tokens return a fencing error and create no GitOps mutation.
- Client components may render disabled controls, but cannot grant or infer a
  role. Route handlers repeat the check for every mutation and export.
- Responses and audit events must omit prompts, tokens, credentials, raw model
  traces containing secrets, email addresses and unnecessary PII.

## Route policy

| Route | Read roles | Mutating actions | Required denial proof |
|---|---|---|---|
| `/companies`, `/companies/[ticker]`, `/compare`, `/reports/[id]` | `analyst`, admin support read | save/export own report | analyst can read; platform viewer cannot mutate analyst data |
| `/agents/chat` | `analyst` and explicitly granted users | bounded AI request | quota/rate-limit and policy-block response |
| `POST /api/assistant/stream` | `analyst` (authorized `analyst.run_ai_request`) | streaming AI request | 403 policy-block, 429 with reset time, or `eks_off` frame when the plane is off |
| `/agents/registry` | `platform_viewer`, `platform_operator`, `platform_admin` | admin promotion/rollback only | viewer/operator cannot promote; server rejects direct call |
| `/ops/evidence` | `platform_viewer`, `platform_operator`, `platform_admin` | operator lifecycle; admin role/policy changes | viewer read-only; stale lease is rejected |

## Database and server enforcement

Supabase tables separate product-owned reports, evidence sessions, audit
events and outbox records. RLS policies constrain rows by authenticated user,
tenant and role; service-role access is limited to server workers and never
shipped to the browser. Tests must cover every role/action pair, signed-out
requests, AAL1 privileged requests, cross-user report access, stale fencing and
idempotent replay.

The UI contract's cached/EKS-off states are security relevant: a cached report
may be read only when its row policy permits it, and an unavailable live plane
must not cause the client to fall back to an unscoped or unauthenticated API.

### AI budget counters and audit (quota / rate limit)

- `ai_request_usage` is the quota/rate-limit counter table. Rows are keyed by
  `(user_id, kind, window_start)` and scoped to the caller by a select policy on
  `auth.uid()`; `authenticated` gets `select` only, `service_role` gets full DML.
  Counters may only move through `consume_ai_quota()` — there is **no direct
  insert/update/delete grant** to `authenticated`, so a caller can never write
  their own budget or another user's row.
- `consume_ai_quota(p_quota_limit, p_quota_window, p_rate_limit, p_rate_window)`
  is the only write path for a bounded AI request. It increments both counters
  only when both limits pass, increments neither on denial, and prunes rows older
  than two windows for the calling user in the same call.
- `record_audit_event(p_action, p_outcome, p_context_id, p_metadata)` writes to
  `audit_log` and raises on metadata keys outside a fixed whitelist
  (`reason`, `quota_remaining`, `rate_remaining`, `attempt`), so an RPC payload
  cannot smuggle prompts or credentials into the audit row.
- Both RPCs follow the grant-hardening pattern of
  `20260804160000_phase2_function_grant_hardening.sql`: revoke from
  `public`/`anon`/`authenticated`, then `grant execute` to `authenticated` only.
  `anon` reaches neither table nor either RPC.

## Acceptance criteria

- RLS test -> exercises every role/action pair -> allowed rows are returned and
  denied rows/actions are rejected at the database boundary.
- Server-route test -> sends a valid-looking client-only role for a caller
  whose real role is not privileged -> mutation is rejected without an
  outbox or GitOps side effect. (A missing AAL2 claim alone no longer
  rejects: see ADR-015.)
- Replay/fencing test -> repeats an idempotency key and then uses a stale token
  -> exactly one transition is committed and the stale request is rejected.
- Browser security test -> navigates to every product route signed out and as
  each role -> protected content is blocked, disabled controls are explained,
  and no secret-bearing payload is rendered.
