---
title: "Phase 2: Build product shell, Supabase, RBAC and UX states"
status: done
estimate: "8-12 days"
---

# Phase 2: Build product shell, Supabase, RBAC and UX states

## Overview

Build DistressLens as a persistent Next.js 16 product on Vercel with Supabase Auth/Postgres. The EKS plane may be absent; the UI must remain useful, show previously generated reports, and represent evidence infrastructure as an explicit state machine.

The three user-approved visual references are now a normative UI contract, not
an informal design note. The original binaries are stored at
`docs/platform/evidence/product/design/UI-APPROVED-0{1,2,3}.png`. They are the
initial frontend direction; implementation may improve visual polish and
responsive behavior without removing the approved information hierarchy or
security/product boundaries.

## Approved UI Baseline

| Reference | Product surface | Required route | What the approved frame must prove |
|---|---|---|---|
| `UI-APPROVED-01` | Analyst overview | `/` and `/companies` | portfolio risk cards, attention table, alert rail, sector-risk chart, model-method summary, global search and persistent navigation |
| `UI-APPROVED-02` | Company detail + AI analysis | `/companies/[ticker]` and the analysis assistant surface | KPI strip, risk/trend chart, financial indicators, SHAP explanation, cited sources, AI panel, MCP/tool trace, model version, loading/error/blocked states and disclaimer |
| `UI-APPROVED-03` | Admin GitOps operations | `/ops/evidence` and `/agents/registry` | plane health, AWS/Vast cost, evidence session, Argo desired/live revision, pipelines, promotion/A-B summary, audit history, observability links and RBAC-disabled actions |

The three references share one design system: a calm analyst workspace, clear
primary action hierarchy, dense but readable evidence metadata, no decorative
motion required for the rubric, responsive layouts at 1440/1024/390 px, and
keyboard-visible focus. UI-APPROVED-03 may use two linked panels in one
responsive shell, but registry and operations remain separate routes and
authorization boundaries. The images are reference fixtures; pixel-perfect
copy is not required if the improved implementation is more accessible and
clearer while preserving the same content hierarchy.

### Route and state inventory

| Route | Required states |
|---|---|
| `/` | authenticated redirect, signed-out landing, loading, auth error |
| `/companies` | search idle, results, no results, stale data, API error |
| `/companies/[ticker]` | live-ready, EKS-off cached result, loading, partial data, forbidden |
| `/compare` | two-version model split, no baseline, loading, error |
| `/reports/[id]` | persisted report, provenance, export, revoked/forbidden |
| analysis assistant (floating, every route) | agent selection, streaming, tool-running, citation, timeout, policy-blocked, EKS-off |
| `/agents/registry` | registry list, version detail, sandbox policy, replica health, unauthorized mutation |
| `/ops/evidence` | OFF/REQUESTED/PROVISIONING/SYNCING/READY/CAPTURING/DESTROYING/FAILED/EXPIRED, cost cap denial, stale fencing |

Every non-success state must explain what is unavailable, what is cached, and
what action is safe. The UI must never present cached evidence as live
inference.

### Accepted deviations from the original phase-02 text

Recorded 2026-08-04, approved by the product owner. Both were deliberate product
decisions, not implementation shortcuts.

1. **The AI surface is a floating assistant, not a `/agents/chat` route.** The
   assistant is available on every analyst surface, carries that surface's
   context, keeps one conversation thread per context, and expands to a
   full-viewport working mode. It still owes every state the route was required
   to prove — permission denial, quota, streaming, tool trace, citations,
   timeout, policy-block and EKS-off — and those states live in
   `ASSISTANT_STATE_COPY` rather than the route catalog. Rationale: an assistant
   the analyst has to navigate to is a place, not a tool; navigating away from
   the numbers to ask about them defeats the purpose. The authorization boundary
   is unchanged — `analyst.run_ai_request` is still enforced server-side.
2. **Palette follows the enterprise-fintech direction** (`#2563EB` primary,
   `#6366F1` assistant accent, `#F6F8FB`/`#FFFFFF` surfaces, `#172A46` chrome)
   rather than the earlier "archival instrument panel" tokens. The
   frontend-design self-review line banning a conventional SaaS palette and a
   purple-family accent does not apply to this phase. Every other line of that
   gate still applies, including token-driven styling, contrast, focus
   visibility, touch targets and reduced motion.

## Requirements

- [x] Analyst pages: company search, risk snapshot, model explanation, cited RAG answer, comparison, saved report, and data freshness. `apps/web/src/app/{page,companies,companies/[ticker],compare,reports,reports/[id]}.tsx`; `analyst-surfaces.spec.ts`.
- [x] Separate LLM rubric surfaces: the analysis assistant UI and the agent registry UI. `components/assistant/*`, `app/agents/registry/page.tsx`.
- [x] Admin surfaces: session state/timeline, estimated and actual cost, GitOps revision, health, evidence exports, promotion, rollback, and teardown. `app/ops/evidence/page.tsx`; `platform-surfaces.spec.ts`. GitOps promotion/rollback render the control and its RBAC/fencing gate — the GitOps repo they dispatch to is out of this repo's scope (unified plan phase-03).
- [x] Fixed disclaimer on company, explanation, AI assistant, comparison, and exported report: educational coursework, not investment advice. `components/shell/disclaimer-banner.tsx`, `DISCLAIMER_SURFACES`; `disclaimer-banner.test.tsx`.
- [x] Enforce RBAC in Supabase RLS and Next.js server boundaries, never only in client components. `supabase/migrations/20260803214600_phase2_rls.sql`, `apps/web/src/lib/server/guards.ts`; `tests/platform/product/test_rbac_rls.py` (653 lines) + `test_outbox_worker.py`.
- [x] Implement all three approved visual references as responsive routes with deterministic screenshot fixtures; no create-next-app placeholder remains. Routes above; `docs/platform/evidence/product/` holds captured frames per route/state/role/viewport.
- [x] Add loading, empty, stale, degraded, forbidden, timeout, and policy-blocked states for every route in the inventory. `lib/states/route-states.ts`, `components/assistant/assistant-message.tsx` state-copy map.
- [x] Keep registry, analyst, and operations navigation separate while sharing typed contracts and the same disclaimer/design tokens; the assistant is a surface on top of them, never a substitute for their authorization boundaries. Separate route trees + `packages/contracts`; `nav-rail.test.tsx` proves an analyst never sees platform items and vice versa.
- [x] Expose evidence provenance (source SHA, GitOps SHA, model/data/agent version, execution time) without exposing prompts, tokens, credentials, or PII. `evidence-manifest.ts` fields + `FORBIDDEN_PATTERNS` redaction check; `record_audit_event` RPC has no free-text prompt column.

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
- Create: `apps/web/src/app/companies/`, `apps/web/src/app/compare/`, `apps/web/src/app/reports/`, `apps/web/src/app/agents/registry/`, `apps/web/src/app/ops/evidence/`, `apps/web/src/components/assistant/`.
- Create: `apps/web/src/components/`, `apps/web/src/lib/server/`, `apps/web/e2e/`, `packages/contracts/` UI/API schemas, Supabase migrations, RLS tests, UI component tests, and Playwright tests.
- Create: `docs/platform/product.md`, `docs/platform/security/rbac.md`,
  `docs/platform/evidence/product/`, and the image-backed reference manifests
  `docs/platform/evidence/product/design/UI-APPROVED-0{1,2,3}.md`.
- Keep infrastructure implementation in the GitOps repo; the source repo stores typed API contracts only.

## Implementation Steps

1. Seed failing authorization, RLS, disclaimer-placement, degraded-mode, and evidence-session state tests.
2. Define session states `OFF -> REQUESTED -> PROVISIONING -> SYNCING -> READY -> CAPTURING -> DESTROYING -> OFF`, plus `FAILED` and `EXPIRED`; persist transition version, actor, idempotency key, lease expiry, fencing token, cost snapshot, Git SHA, and timestamps.
3. Implement an outbox so state transition and requested infrastructure action commit atomically; workers claim events with leases and reject stale fencing tokens.
4. Show preflight cost projection before provision; disable provision at the monthly cap; make destroy always available to operators/admins.
5. Keep synchronous analyst inference as direct SSE only when EKS is `READY`. Queue admin lifecycle actions and poll/subscribe to durable state.
6. Render cached/persisted results when EKS is off. Never imply live inference when a saved result is displayed.
7. Implement the three approved UI references first, then add responsive route variants and deterministic states from the route inventory; preserve the approved information hierarchy rather than adding cosmetic features.
8. Add screenshot-friendly states for the analysis assistant and independent navigation for the agent registry; registry mutations require admin/operator authorization and fencing.
9. Add rate limits and per-user AI quotas at the product boundary; record consent-safe audit events without prompts, tokens, or secrets.
10. Wire the UI to typed server actions/API contracts: SSE only for a READY inference plane, durable outbox/polling for lifecycle operations, cached reports for EKS-OFF, and explicit provenance for every displayed result.

## Validation

- Unit/component tests with coverage >90% on changed code.
- Supabase local RLS tests for every role/action pair and AAL1/AAL2 state.
- Playwright flows for all three approved references plus analyst, viewer, operator, admin, EKS-off degradation, cost-cap denial, stale fencing rejection, the analysis assistant, and registry.
- Screenshot assertions at 1440/1024/390 px, visual-reference checklist, keyboard navigation, focus visibility, reduced-motion preference, semantic headings/labels, contrast, and axe accessibility checks.
- Contract tests proving every screen's state comes from typed server data and that a cached result is labeled as cached.

## Success Criteria

- [x] Analyst -> opens the product while EKS is off -> can inspect saved, timestamped results and sees that live AI is unavailable. `lib/states/route-states.ts`; `assistant-plane-off.spec.ts`.
- [x] Platform viewer -> opens admin -> sees cost, lifecycle, GitOps and evidence state but cannot mutate it through UI or server APIs. `test_rbac_rls.py::test_platform_viewer_*`; `role-action-button.tsx` disables mutation server-authorized controls.
- [x] Platform operator with AAL2 -> retries a failed provision using the same idempotency key -> receives one transition and one outbox action. `request_session_transition`'s idempotency-key replay path; `session-actions.ts`.
- [x] Platform admin -> attempts a stale promotion after another session owns the lease -> receives a fencing error and no GitOps mutation. `test_completion_after_superseding_transition_is_stale_fencing` (`tests/platform/product/test_outbox_worker.py`) — the superseded event ends `FAILED`, the session state reflects only the newer transition.
- [x] Reviewer -> checks every decision-support surface -> sees the non-investment disclaimer. `disclaimer-banner.test.tsx` covers every `DISCLAIMER_SURFACES` entry.
- [x] Product reviewer -> opens `UI-APPROVED-01` route -> sees the approved analyst information hierarchy and every required loading/stale/error/cached state in deterministic screenshots. `docs/platform/evidence/product/root--*`, `companies--*`.
- [x] LLM reviewer -> opens the `UI-APPROVED-02` route and its analysis assistant -> sees streamed answer, citations, MCP/tool trace, model version and policy/error states without secret leakage. `POST /api/assistant/stream` + `assistant-streaming.spec.ts`/`assistant-quota.spec.ts`; `assistant-panel.test.tsx` renders every `AgentMessageState` plus `unavailable` with citations/tool-trace/version; `FORBIDDEN_PATTERNS` asserts no secret in any captured frame.
- [x] Platform reviewer -> opens `UI-APPROVED-03` routes -> sees registry governance and evidence lifecycle/cost/GitOps controls with unauthorized actions disabled server-side. `platform-surfaces.spec.ts`; `docs/platform/evidence/product/agents-registry--*`, `ops-evidence--*`.
- [x] Accessibility reviewer -> runs the UI audit at desktop and mobile viewports -> finds keyboard access, visible focus, semantic labels, contrast and reduced-motion compliance. `pnpm --filter @distresslens/web e2e:a11y` + `e2e:a11y-roles`, 18/18 pass; `docs/platform/evidence/product/accessibility.md`.

## Risks and Rollback

- Risk: Vercel serverless requests cannot babysit long AWS operations. Mitigation: durable outbox + external worker + polling/subscription.
- Risk: the approved images are treated as a pixel-perfect production spec. Mitigation: keep the originals and hashes immutable as baseline evidence, while allowing an accessible, responsive visual refinement during implementation.
- Risk: a polished screenshot hides missing runtime states. Mitigation: every screenshot fixture carries route, state, viewport, source SHA, GitOps SHA and data provenance; Playwright covers success and failure states.
- Rollback: Supabase migrations require tested down/forward-fix scripts; web releases use Vercel deployment rollback without altering EKS state.
