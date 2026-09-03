---
name: phase2-stage2-frontend-implementation
description: Implement the DistressLens platform .roduct shell, approved UI baseline, Supabase/RLS boundary, outbox lifecycle worker and deterministic UX evidence.
---

# platform .tage 2 implementation prompt

You are the lead frontend engineer, product designer and product-plane
integrator for the DistressLens coursework repository. Complete platform .tage
2 from implementation through verification. Work in the existing repository;
do not create a second app, a microservice-per-repo layout, or a fake demo that
only looks complete in a screenshot.

## Mission

Turn the current product foundation into a working, typed, accessible
DistressLens product shell that satisfies the platform .lan and the three
approved visual references. Finish the analyst, company/AI, agent, registry
and admin/evidence surfaces; connect them to Supabase/RLS and the typed session
contract; implement the durable outbox worker behavior; and leave reproducible
Playwright evidence for every required state.

Do not claim platform .s complete until the Definition of Done at the end is
true. The current report is a gap report, not proof of completion:
`plans/reports/review-260803-2249-phase2-status.md`.

## Read first

Read these files before changing code:

1. `AGENTS.md` and the repository development rules.
2. `plans/reports/review-260803-2249-phase2-status.md`.
3. `plans/260802-1037-unified-phase2-ml-llm-gitops/phase-02-build-product-shell-supabase-rbac-and-ux-states.md`.
4. `docs/platform/product.md` and `docs/platform/security/rbac.md`.
5. `docs/platform/requirements.md`, `docs/platform/evidence-contract.md` and
   `docs/platform/architecture.md`.
6. `packages/contracts/src/role.ts`, `session-state.ts`,
   `session-transitions.json` and `outbox-event.ts`.
7. Both Supabase migrations under `supabase/migrations/` and the existing
   product/RLS tests under `tests/platform/product/`.

The product UI contract and the three images are the visual source of truth:

![UI-APPROVED-01 analyst overview](../../docs/platform/evidence/product/design/UI-APPROVED-01.png)

![UI-APPROVED-02 company detail and AI analysis](../../docs/platform/evidence/product/design/UI-APPROVED-02.png)

![UI-APPROVED-03 admin GitOps operations](../../docs/platform/evidence/product/design/UI-APPROVED-03.png)

These images are the initial composition and interaction baseline. They are not
a pixel-perfect production mandate. Improve spacing, responsive behavior,
contrast, chart semantics, empty/error states and micro-interactions when that
makes the product clearer and more accessible. Preserve the information
hierarchy, analyst/agent/admin separation, provenance, disclaimer and truthful
live/cached states.

## Current implementation facts

- `apps/web/` is a Next.js 16 App Router scaffold; `src/app/page.tsx` is still
  the create-next-app placeholder.
- Supabase schema/RLS, role contracts, session transition contracts and RLS
  tests already exist. Extend them; do not replace them with client-only logic.
- `OutboxEvent` is currently a type contract. A lease-claiming worker/consumer
  and durable mutation path are still required.
- The GitOps repository owns infrastructure desired state. This repository
  owns product routes, typed contracts, tests and evidence descriptions only.
- platform .ode and behavior are frozen. Do not edit platform .AGs, collectors,
  Gold semantics or `docs/evidence/**` for this task.

## Design read and aesthetic direction

Before coding, write a short design-read note in the implementation PR or
working report using this exact shape:

> Reading this as: a dense financial-risk operations product for analysts and
> platform operators, with a calm evidence-control-room language, leaning
> disciplined neo-grotesque product UI.

Use these design dials for the dashboard/product surface:

- `DESIGN_VARIANCE=3`: consistent grids and predictable navigation.
- `MOTION_INTENSITY=2`: 150–250 ms state feedback only; no page-load spectacle.
- `VISUAL_DENSITY=6`: information-rich tables/charts with disciplined spacing.

Break default-style mode collapse before choosing the direction: derive a
repeatable seed from the request text (for example, the character count of
`DistressLens platform .tage 2`) and use it to select one candidate from the
frontend-design direction menu. If the seeded direction conflicts with the
financial-operations audience or the supplied screenshots, move to the
adjacent direction and record why. Do not silently fall back to a generic SaaS
dashboard.

Write one aesthetic thesis before implementation. Example:

> Calm evidence control room for financial-risk decisions: navy ink, cool
> paper, restrained red/amber/green states, compact humanist sans typography,
> a persistent two-shell navigation model, and a single memorable evidence
> ribbon that makes live/cached/GitOps state impossible to miss.

Choose the final palette and fonts deliberately from the content. Use design
tokens first. Verify Vietnamese glyph support. Do not use Inter, Roboto, Arial
or system UI as the display face; do not use purple gradients, raw black/white,
generic glassmorphism, default unstyled shadcn, decorative grid backgrounds,
or random card ornament. Use one coherent radius system and one depth strategy.

The one memorable element should be the evidence/risk status ribbon or another
domain-derived element you can justify from financial distress and GitOps
operations. Keep every other decorative choice quiet.

Before implementation, inspect all three supplied images with the available
multimodal/image-view tooling and record a compact observation of layout,
spacing, type hierarchy, color/state semantics, chart/table density and likely
responsive changes. The screenshot is the source for composition; the product
contract is the source for behavior, security and truthfulness.

## Product surfaces and route contract

Implement these routes with shared typed data adapters and separate
authorization boundaries:

| Route | Surface | Required states |
|---|---|---|
| `/` | Analyst overview and signed-out entry | authenticated redirect, signed-out landing, loading, auth error |
| `/companies` | Search and portfolio | idle, results, no results, stale data, API error |
| `/companies/[ticker]` | Company risk detail and AI panel | live-ready, EKS-off cached, loading, partial data, forbidden |
| `/compare` | Model/version comparison | two-version split, no baseline, loading, error |
| `/reports/[id]` | Saved report and export | persisted, provenance, export, revoked/forbidden |
| `/agents/chat` | Bounded agent workbench | selection, streaming, tool-running, citations, timeout, policy-blocked, EKS-off |
| `/agents/registry` | Agent governance | list, version detail, sandbox policy, replica health, unauthorized mutation |
| `/ops/evidence` | Admin GitOps/evidence control room | OFF, REQUESTED, PROVISIONING, SYNCING, READY, CAPTURING, DESTROYING, FAILED, EXPIRED, cost-cap denial, stale fencing |

### UI-APPROVED-01: analyst overview

Preserve the reference's left navigation, global ticker/company search, last
data/freshness header, user/notification controls, risk summary cards,
attention table, alert rail, sector-risk comparison and model-method summary.
Use real labels such as “Nguy cơ cao”, “Cần theo dõi”, “Ổn định”, “Xem báo cáo”
and “Phân tích với AI”. Do not copy screenshot values into production data.

### UI-APPROVED-02: company detail and AI analysis

Preserve the company breadcrumb/header, watchlist action, distress probability
and confidence strip, trend chart, financial indicators, SHAP drivers, source
list and right-side AI analysis panel. The panel must render citation IDs,
agent/model version and an expandable MCP/tool trace. `/agents/chat` may reuse
these components, but it must remain a separate route with its own permission,
quota and policy states.

### UI-APPROVED-03: admin GitOps operations

Preserve the separate `DistressLens Admin` shell, environment selector,
online/offline plane status, AWS and Vast cost gauges, evidence-session action,
Argo desired/live revision, sync health, pipeline table, promotion queue, A/B
summary, audit history and links to Grafana, Kibana, Jaeger and Agent Registry.
Viewers inspect. Operators mutate lifecycle state. Admins can promote,
rollback and manage roles only with AAL2, fencing and audit.

## Shared component and content rules

Create reusable components rather than duplicating markup:

- `AppShell`, `AnalystNav`, `AdminNav`, `HeaderSearch`, `UserMenu`,
  `PlaneStatus`, `DisclaimerBanner`.
- `RiskSummaryCard`, `RiskTable`, `AlertTimeline`, `SectorRiskChart`,
  `FreshnessBadge`, `ProvenancePanel`, `SourceList`, `ShapChart`.
- `AgentPanel`, `CitationList`, `ToolTrace`, `StreamingMessage`,
  `PolicyBlock`, `QuotaNotice`.
- `SessionStateTimeline`, `CostGauge`, `GitRevisionCard`, `PipelineTable`,
  `PromotionQueue`, `AuditTimeline`, `RoleActionButton`.

All visible copy is user-facing and domain-specific. Use sentence case and
active verbs. Controls must say exactly what they do: “Lưu báo cáo”, “Tạo
phiên evidence”, “Xem log”, “Mở PR promotion”, “Hủy phiên”. Error and empty
states explain what happened and the safe next action. Do not use lorem ipsum,
generic “AI magic” copy, fake credentials, hidden prompts or unexplained
round numbers.

Every decision-support surface and exported report includes:

> Nội dung phục vụ mục đích học tập, không phải khuyến nghị đầu tư.

## Typed server, data and security contract

1. Extend `packages/contracts` for route view models, provenance, UI state,
   cost projection, quota result, citations, tool traces and audit events.
2. Keep authorization in Next.js server actions/route handlers and Supabase
   RLS. Client-side hidden/disabled controls are presentation only.
3. Require signed session, role, origin/CSRF check, input schema validation,
   rate limit and quota before any mutation or AI request.
4. `platform_viewer`, `platform_operator` and `platform_admin` require AAL2
   for privileged paths. Use the existing role/action contract.
5. Lifecycle mutations require idempotency key, fresh fencing token and lease.
   A replay returns the original result; a stale token creates no outbox or
   GitOps side effect.
6. Implement the outbox transaction so the session transition and requested
   infrastructure action commit atomically. The worker claims pending events
   with a lease, is safe to retry, records attempts/result, and rejects stale
   fencing tokens.
7. Show cost projection before provision. Block provision at the declared cap;
   destroy remains available to authorized operators/admins.
8. Stream analyst/agent inference only when the evidence plane is `READY`.
   Lifecycle operations use durable outbox plus polling/subscription.
9. When EKS is unavailable, render only authorized persisted/cached results and
   label them `CACHED_RESULT` and `LIVE_UNAVAILABLE` with timestamp, source SHA,
   model/data/agent version and run ID.
10. Never render prompts, tokens, credentials, raw secret-bearing traces or
    unnecessary PII. Audit events contain actor/action/result/version only.

## Implementation sequence

Work in this order and keep each step reviewable:

### Step 1: reconnaissance and contracts

- Confirm the route tree and current scaffold.
- Add/extend typed contracts and deterministic `REFERENCE_FIXTURE` adapters.
- Add failing tests for route states, disclaimer placement, role/action denial,
  EKS-off labeling, cost-cap denial, idempotent replay and stale fencing.

### Step 2: tokenized visual foundation

- Replace the placeholder shell with tokens for color, typography, spacing,
  radius, shadow, focus, breakpoints and motion.
- Use a 4 px spacing base, 44 px minimum touch targets and explicit z-index
  layers. No ad-hoc hex/color/spacing values in component files.
- Implement keyboard navigation and `prefers-reduced-motion` before adding
  polish.

### Step 3: shared shells and analyst routes

- Build analyst navigation/header and `/`, `/companies`,
  `/companies/[ticker]`, `/compare`, `/reports/[id]`.
- Match the approved hierarchy first, then refine chart/table behavior and
  responsive composition. Collapse rails/tables on mobile; do not merely
  shrink desktop content until it becomes unreadable.

### Step 4: agent and admin routes

- Build `/agents/chat` with streaming, citations, tool trace, timeout,
  policy-block and EKS-off states.
- Build `/agents/registry` with version/status/replica/sandbox data and
  unauthorized mutation proof.
- Build `/ops/evidence` with session timeline, cost projection, GitOps revision,
  pipeline/promotion/A-B/audit data, role-aware controls and observability
  links.

### Step 5: server boundary and outbox

- Implement server actions/route handlers and Supabase queries with RLS.
- Implement the outbox worker/consumer with lease claim, retry, idempotency,
  fencing and audit result. Keep long AWS work outside the request lifecycle.
- Add polling/subscription state updates and honest failure/retry guidance.

### Step 6: evidence and visual verification

- Add Playwright fixtures for every approved reference at 1440, 1024 and
  390 px, plus all non-success states and every role.
- Capture screenshots and manifests with route, state, viewport, source SHA,
  GitOps SHA, data/model/agent version, expected/actual result and redaction
  status. The supplied reference PNGs remain immutable baseline assets.
- Run the frontend-design self-review gate below. Fix failures before claiming
  completion.

## Frontend-design self-review gate

Before delivery, record pass/fail for every item:

- Design Read and aesthetic thesis are explicit and grounded in DistressLens.
- Tokens drive all colors, type, spacing, radii, shadows and motion.
- No Inter/Roboto/Arial/system display font, purple gradient, raw black/white,
  default shadcn surface, glassmorphism or decorative UI ornament.
- One memorable domain-derived element; all other decoration passes the delete
  test.
- Every interactive element has hover, visible `:focus-visible` and active
  states; controls are at least 44 px.
- No `transition: all`; motion is 150–250 ms and has a reduced-motion path.
- Body/muted/placeholder contrast is at least 4.5:1 on actual backgrounds.
- 375/390 px has no horizontal scroll; charts/tables compose rather than
  shrink into illegible content.
- Loading, empty, stale, degraded, forbidden, timeout and policy-blocked states
  explain the next safe action.
- Cached output can never be mistaken for live inference.
- Analyst, agent and admin shells remain visibly and authorization-wise
  separate.

## Required files and boundaries

Implement or extend only the relevant boundaries:

- `apps/web/src/app/` route directories and layouts.
- `apps/web/src/components/` shared UI.
- `apps/web/src/lib/server/` auth, RLS queries, actions, outbox and adapters.
- `apps/web/e2e/` Playwright tests and screenshot fixtures.
- `packages/contracts/src/` typed view/state/event contracts.
- `supabase/migrations/` additive schema/RLS changes with tests.
- `docs/platform/product.md`, `docs/platform/security/rbac.md` and
  `docs/platform/evidence/product/` when implementation changes the contract.

Do not edit platform .ipeline code, generated `warehouse.db`, `outputs/**`,
`docs/evidence/**`, or GitOps desired state from this repository.

## Verification commands

Run the narrowest relevant command after each step, then the full set before
delivery:

```bash
pnpm --filter @distresslens/web lint
pnpm --filter @distresslens/web typecheck
pnpm --filter @distresslens/web build
pnpm --filter @distresslens/contracts typecheck
pnpm --filter @distresslens/contracts test
.venv/bin/python -m pytest tests/platform/product/test_rbac_rls.py \
  tests/platform/test_rubric_matrix.py tests/platform/test_rubric_row_contracts.py
python scripts/audit_phase2_evidence.py --matrix-only --strict
ak plan validate plans/260802-1037-unified-phase2-ml-llm-gitops --json
```

Add a Playwright command to `apps/web/package.json` and run the complete
desktop/tablet/mobile and role/state suite. Do not replace a failing test with
a weaker assertion.

## Definition of Done

- [ ] No create-next-app placeholder remains.
- [ ] All eight product route groups exist with typed loading/success/failure
      states.
- [ ] UI-APPROVED-01, 02 and 03 are recognizable at desktop/tablet/mobile
      sizes while visibly improved where accessibility or clarity requires it.
- [ ] Analyst, agent, registry and admin navigation are separate.
- [ ] Disclaimer appears on company, explanation, chat, comparison and export.
- [ ] RLS and server tests cover signed-out, AAL1/AAL2 and every role/action
      pair.
- [ ] Outbox worker proves atomic transition, lease claim, retry, idempotency
      and stale-fencing rejection.
- [ ] Cost projection/cap, destroy safety, rate limits and AI quotas work at
      the product boundary.
- [ ] EKS-off UI is useful and visibly labels cached/live-unavailable data.
- [ ] Playwright screenshots/manifests contain route, state, viewport,
      provenance and redaction fields.
- [ ] Accessibility and frontend-design self-review gates pass.
- [ ] Verification commands pass; platform .iles and semantics are unchanged.
- [ ] Only after all boxes pass may `phase-02...md` move from `todo` to
      `in_review` or `complete`, with reviewer evidence linked.

## Agent handoff format

At the end, report:

```text
Status: DONE | DONE_WITH_CONCERNS | BLOCKED
Implemented: <routes, contracts, worker, tests>
Evidence: <commands, screenshots, manifests, SHAs>
Remaining: <explicit gaps; never hide failures>
```

If a required image, secret-safe integration credential, GitOps checkout or
runtime service is unavailable, keep the deterministic contract/fixture work,
mark the exact runtime gap and do not fabricate a passing result.
