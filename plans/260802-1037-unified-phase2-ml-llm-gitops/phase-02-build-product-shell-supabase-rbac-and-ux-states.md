---
title: "Phase 2: Build product shell, Supabase, RBAC and UX states"
status: todo
estimate: "6-8 days"
---

# Phase 2: Build product shell, Supabase, RBAC and UX states

## Overview

Build DistressLens as a persistent Next.js 16 product on Vercel with Supabase Auth/Postgres. The EKS plane may be absent; the UI must remain useful, show previously generated reports, and represent evidence infrastructure as an explicit state machine.

## Requirements

- [ ] Analyst pages: company search, risk snapshot, model explanation, cited RAG answer, comparison, saved report, and data freshness.
- [ ] Separate LLM rubric surfaces: agent chat UI and agent registry UI.
- [ ] Admin surfaces: session state/timeline, estimated and actual cost, GitOps revision, health, evidence exports, promotion, rollback, and teardown.
- [ ] Fixed disclaimer on company, explanation, AI chat, comparison, and exported report: educational coursework, not investment advice.
- [ ] Enforce RBAC in Supabase RLS and Next.js server boundaries, never only in client components.

## Authorization Model

| Role | Allowed | Explicitly denied |
|---|---|---|
| `analyst` | query companies, run bounded AI requests, save own reports | platform and role operations |
| `platform_viewer` | read session, cost, health, evidence and audit state | provision, destroy, promote, rollback |
| `platform_operator` | provision, destroy, retry and export evidence | change roles/security, promote production |
| `platform_admin` | operator actions, model/agent promotion, Git rollback request, role administration | bypass audit, budget, AAL2 or fencing |

All privileged roles require Supabase AAL2. Server actions verify signed claims, current role, CSRF/origin, idempotency key, and a fresh fencing token.

## Files

- Create: `apps/web/`, `packages/contracts/`, Supabase migrations, RLS tests, UI component tests, Playwright tests.
- Create: `docs/phase2/product.md`, `docs/phase2/security/rbac.md`, `docs/phase2/evidence/product/`.
- Keep infrastructure implementation in the GitOps repo; the source repo stores typed API contracts only.

## Implementation Steps

1. Seed failing authorization, RLS, disclaimer-placement, degraded-mode, and evidence-session state tests.
2. Define session states `OFF -> REQUESTED -> PROVISIONING -> SYNCING -> READY -> CAPTURING -> DESTROYING -> OFF`, plus `FAILED` and `EXPIRED`; persist transition version, actor, idempotency key, lease expiry, fencing token, cost snapshot, Git SHA, and timestamps.
3. Implement an outbox so state transition and requested infrastructure action commit atomically; workers claim events with leases and reject stale fencing tokens.
4. Show preflight cost projection before provision; disable provision at the monthly cap; make destroy always available to operators/admins.
5. Keep synchronous analyst inference as direct SSE only when EKS is `READY`. Queue admin lifecycle actions and poll/subscribe to durable state.
6. Render cached/persisted results when EKS is off. Never imply live inference when a saved result is displayed.
7. Add independent navigation and screenshot-friendly states for agent chat and agent registry.
8. Add rate limits and per-user AI quotas at the product boundary; record consent-safe audit events without prompts, tokens, or secrets.

## Validation

- Unit/component tests with coverage >90% on changed code.
- Supabase local RLS tests for every role/action pair and AAL1/AAL2 state.
- Playwright flows for analyst, viewer, operator, admin, EKS-off degradation, cost-cap denial, stale fencing rejection, agent chat, and registry.
- Accessibility checks and deterministic screenshot fixtures.

## Success Criteria

- [ ] Analyst -> opens the product while EKS is off -> can inspect saved, timestamped results and sees that live AI is unavailable.
- [ ] Platform viewer -> opens admin -> sees cost, lifecycle, GitOps and evidence state but cannot mutate it through UI or server APIs.
- [ ] Platform operator with AAL2 -> retries a failed provision using the same idempotency key -> receives one transition and one outbox action.
- [ ] Platform admin -> attempts a stale promotion after another session owns the lease -> receives a fencing error and no GitOps mutation.
- [ ] Reviewer -> checks every decision-support surface -> sees the non-investment disclaimer.

## Risks and Rollback

- Risk: Vercel serverless requests cannot babysit long AWS operations. Mitigation: durable outbox + external worker + polling/subscription.
- Rollback: Supabase migrations require tested down/forward-fix scripts; web releases use Vercel deployment rollback without altering EKS state.
