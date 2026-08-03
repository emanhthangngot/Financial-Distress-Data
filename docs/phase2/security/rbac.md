# Phase 2 Product RBAC and Security Boundary

This document is the security contract for the product-plane routes in
`docs/phase2/product.md`. It complements Supabase RLS and server-side
authorization tests; hiding a button in the browser is never an authorization
control.

## Roles and actions

| Role | Read analyst data | Run bounded AI | Read platform/evidence | Lifecycle mutate | Promote/rollback | Manage roles |
|---|---:|---:|---:|---:|---:|---:|
| `analyst` | own/allowed companies | yes, quota-bound | no | no | no | no |
| `platform_viewer` | no analyst mutation | no | yes | no | no | no |
| `platform_operator` | no analyst mutation | no | yes | provision/retry/destroy/export | no | no |
| `platform_admin` | no analyst mutation | no | yes | all operator actions | yes, with lease/fencing | yes, with AAL2 |

The effective permission is the intersection of the role, the tenant/user
scope, the route policy and the current evidence-plane state. A denied action
must be rejected by both the Next.js server boundary and the database policy.

## Authentication and request rules

- Supabase Auth is the identity source. `platform_operator` and
  `platform_admin` require AAL2/MFA before privileged actions.
- Server actions/API handlers validate the signed session, role claim, origin/
  CSRF policy, request schema and rate limit before touching data or an outbox.
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

## Acceptance criteria

- RLS test -> exercises every role/action pair -> allowed rows are returned and
  denied rows/actions are rejected at the database boundary.
- Server-route test -> sends a valid-looking client-only role or missing AAL2
  claim -> privileged mutation is rejected without an outbox or GitOps side
  effect.
- Replay/fencing test -> repeats an idempotency key and then uses a stale token
  -> exactly one transition is committed and the stale request is rejected.
- Browser security test -> navigates to every product route signed out and as
  each role -> protected content is blocked, disabled controls are explained,
  and no secret-bearing payload is rendered.
