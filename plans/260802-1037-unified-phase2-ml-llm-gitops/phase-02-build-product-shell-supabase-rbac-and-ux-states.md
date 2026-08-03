---
title: "Phase 2: Build product shell, Supabase, RBAC and UX states"
status: todo
estimate: "8-12 days"
---

# Phase 2: Build product shell, Supabase, RBAC and UX states

## Overview

Build DistressLens as a persistent Next.js 16 product on Vercel with Supabase Auth/Postgres. The EKS plane may be absent; the UI must remain useful, show previously generated reports, and represent evidence infrastructure as an explicit state machine.

The three user-approved visual references are now a normative UI contract, not
an informal design note. The original image binaries are not present in this
checkout, so the plan records stable reference IDs and the exact screen/state
requirements below. Before implementation, copy the approved images to
`docs/phase2/evidence/product/design/` using these IDs; do not replace them
with an invented mock.

## Approved UI Baseline

| Reference | Product surface | Required route | What the approved frame must prove |
|---|---|---|---|
| `UI-APPROVED-01` | Analyst risk workspace | `/companies/[ticker]` | company search, financial-distress risk snapshot, model explanation, data freshness, cited RAG answer, save/export report, and comparison entry point |
| `UI-APPROVED-02` | Agent chat workbench | `/agents/chat` | agent selector, streaming response, citations, MCP/tool trace, model/agent version, loading/error/blocked states, and fixed non-investment disclaimer |
| `UI-APPROVED-03` | Agent registry + evidence operations | `/agents/registry` and `/ops/evidence` | governed agent registry, version/status/replicas/sandbox policy, evidence-plane lifecycle, cost preview, GitOps revision, promotion/rollback/teardown controls, and RBAC-disabled actions |

The three references share one design system: a calm analyst workspace, clear
primary action hierarchy, dense but readable evidence metadata, no decorative
motion required for the rubric, responsive layouts at 1440/1024/390 px, and
keyboard-visible focus. UI-APPROVED-03 may use two linked panels in one
responsive shell, but registry and operations remain separate routes and
authorization boundaries.

### Route and state inventory

| Route | Required states |
|---|---|
| `/` | authenticated redirect, signed-out landing, loading, auth error |
| `/companies` | search idle, results, no results, stale data, API error |
| `/companies/[ticker]` | live-ready, EKS-off cached result, loading, partial data, forbidden |
| `/compare` | two-version model split, no baseline, loading, error |
| `/reports/[id]` | persisted report, provenance, export, revoked/forbidden |
| `/agents/chat` | agent selection, streaming, tool-running, citation, timeout, policy-blocked, EKS-off |
| `/agents/registry` | registry list, version detail, sandbox policy, replica health, unauthorized mutation |
| `/ops/evidence` | OFF/REQUESTED/PROVISIONING/SYNCING/READY/CAPTURING/DESTROYING/FAILED/EXPIRED, cost cap denial, stale fencing |

Every non-success state must explain what is unavailable, what is cached, and
what action is safe. The UI must never present cached evidence as live
inference.

## Requirements

- [ ] Analyst pages: company search, risk snapshot, model explanation, cited RAG answer, comparison, saved report, and data freshness.
- [ ] Separate LLM rubric surfaces: agent chat UI and agent registry UI.
- [ ] Admin surfaces: session state/timeline, estimated and actual cost, GitOps revision, health, evidence exports, promotion, rollback, and teardown.
- [ ] Fixed disclaimer on company, explanation, AI chat, comparison, and exported report: educational coursework, not investment advice.
- [ ] Enforce RBAC in Supabase RLS and Next.js server boundaries, never only in client components.
- [ ] Implement all three approved visual references as responsive routes with deterministic screenshot fixtures; no create-next-app placeholder remains.
- [ ] Add loading, empty, stale, degraded, forbidden, timeout, and policy-blocked states for every route in the inventory.
- [ ] Keep registry, chat, analyst, and operations navigation separate while sharing typed contracts and the same disclaimer/design tokens.
- [ ] Expose evidence provenance (source SHA, GitOps SHA, model/data/agent version, execution time) without exposing prompts, tokens, credentials, or PII.

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
- Create: `apps/web/src/app/companies/`, `apps/web/src/app/compare/`, `apps/web/src/app/reports/`, `apps/web/src/app/agents/chat/`, `apps/web/src/app/agents/registry/`, `apps/web/src/app/ops/evidence/`.
- Create: `apps/web/src/components/`, `apps/web/src/lib/server/`, `apps/web/e2e/`, `packages/contracts/` UI/API schemas, Supabase migrations, RLS tests, UI component tests, and Playwright tests.
- Create: `docs/phase2/product.md`, `docs/phase2/security/rbac.md`, `docs/phase2/evidence/product/`, and `docs/phase2/evidence/product/design/UI-APPROVED-0{1,2,3}.md`.
- Keep infrastructure implementation in the GitOps repo; the source repo stores typed API contracts only.

## Implementation Steps

1. Seed failing authorization, RLS, disclaimer-placement, degraded-mode, and evidence-session state tests.
2. Define session states `OFF -> REQUESTED -> PROVISIONING -> SYNCING -> READY -> CAPTURING -> DESTROYING -> OFF`, plus `FAILED` and `EXPIRED`; persist transition version, actor, idempotency key, lease expiry, fencing token, cost snapshot, Git SHA, and timestamps.
3. Implement an outbox so state transition and requested infrastructure action commit atomically; workers claim events with leases and reject stale fencing tokens.
4. Show preflight cost projection before provision; disable provision at the monthly cap; make destroy always available to operators/admins.
5. Keep synchronous analyst inference as direct SSE only when EKS is `READY`. Queue admin lifecycle actions and poll/subscribe to durable state.
6. Render cached/persisted results when EKS is off. Never imply live inference when a saved result is displayed.
7. Implement the three approved UI references first, then add responsive route variants and deterministic states from the route inventory; preserve the approved information hierarchy rather than adding cosmetic features.
8. Add independent navigation and screenshot-friendly states for agent chat and agent registry; registry mutations require admin/operator authorization and fencing.
9. Add rate limits and per-user AI quotas at the product boundary; record consent-safe audit events without prompts, tokens, or secrets.
10. Wire the UI to typed server actions/API contracts: SSE only for a READY inference plane, durable outbox/polling for lifecycle operations, cached reports for EKS-OFF, and explicit provenance for every displayed result.

## Validation

- Unit/component tests with coverage >90% on changed code.
- Supabase local RLS tests for every role/action pair and AAL1/AAL2 state.
- Playwright flows for all three approved references plus analyst, viewer, operator, admin, EKS-off degradation, cost-cap denial, stale fencing rejection, agent chat, and registry.
- Screenshot assertions at 1440/1024/390 px, visual-reference checklist, keyboard navigation, focus visibility, reduced-motion preference, semantic headings/labels, contrast, and axe accessibility checks.
- Contract tests proving every screen's state comes from typed server data and that a cached result is labeled as cached.

## Success Criteria

- [ ] Analyst -> opens the product while EKS is off -> can inspect saved, timestamped results and sees that live AI is unavailable.
- [ ] Platform viewer -> opens admin -> sees cost, lifecycle, GitOps and evidence state but cannot mutate it through UI or server APIs.
- [ ] Platform operator with AAL2 -> retries a failed provision using the same idempotency key -> receives one transition and one outbox action.
- [ ] Platform admin -> attempts a stale promotion after another session owns the lease -> receives a fencing error and no GitOps mutation.
- [ ] Reviewer -> checks every decision-support surface -> sees the non-investment disclaimer.
- [ ] Product reviewer -> opens `UI-APPROVED-01` route -> sees the approved analyst information hierarchy and every required loading/stale/error/cached state in deterministic screenshots.
- [ ] LLM reviewer -> opens `UI-APPROVED-02` route -> sees streamed answer, citations, MCP/tool trace, model version and policy/error states without secret leakage.
- [ ] Platform reviewer -> opens `UI-APPROVED-03` routes -> sees registry governance and evidence lifecycle/cost/GitOps controls with unauthorized actions disabled server-side.
- [ ] Accessibility reviewer -> runs the UI audit at desktop and mobile viewports -> finds keyboard access, visible focus, semantic labels, contrast and reduced-motion compliance.

## Risks and Rollback

- Risk: Vercel serverless requests cannot babysit long AWS operations. Mitigation: durable outbox + external worker + polling/subscription.
- Risk: approved images are not available as repository assets. Mitigation: preserve the three reference IDs and block visual sign-off until the original images are copied without alteration.
- Risk: a polished screenshot hides missing runtime states. Mitigation: every screenshot fixture carries route, state, viewport, source SHA, GitOps SHA and data provenance; Playwright covers success and failure states.
- Rollback: Supabase migrations require tested down/forward-fix scripts; web releases use Vercel deployment rollback without altering EKS state.
