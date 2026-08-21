---
phase: 9
title: "Phase 9: Migrate The Web Plane Into The Cluster"
status: todo
priority: P2
effort: "1 week"
dependencies: [4]
---

# Phase 9: Migrate The Web Plane Into The Cluster

## Overview

Move the existing Next.js product app (`apps/web`, ~162 TypeScript files, the
"DistressLens" contract in `docs/phase2/product.md`) off Vercel + Supabase and onto
the cluster, and fold the agent chat UI and agent registry UI into it rather than
shipping them as separate surfaces.

Runs in parallel with phases 5-6 once the platform exists. Phase 6 owns the agent
behaviour behind the UIs; this phase owns the application that renders them.

## Why this phase exists

The app was previously outside every mechanism the coursework grades. It deployed
through Vercel rather than Argo CD, authenticated through Supabase rather than the
cluster, never passed through Jenkins, never joined the mesh, and emitted no
telemetry into Prometheus. It also sat outside the "everything runs on Kubernetes"
story the deployment diagram has to tell.

Its scored surface is small and entirely in the LLM rubric:

| Row | Points |
|---|---:|
| UI để test agent | 2 |
| UI cho agent registry | 2 |
| Setup authentication cho UI test agent | 2 |
| **Total** | **6** |

Nothing in any rubric asks for the analyst product, profile switching, RBAC or
quota surfaces. Those are kept because they already exist and make the platform a
real system rather than a pile of services — but they are **not** allowed to
consume schedule beyond what the migration itself needs. If this phase slips, the
product surfaces are cut before the three scored UIs.

## Requirements

Functional:
- [ ] `apps/web` builds into a container image and deploys via Helm through Argo CD
- [ ] Served behind NGINX Ingress at the domain apex under the wildcard certificate, no external LB of its own
- [ ] Authentication backed by the in-cluster PostgreSQL, replacing Supabase Auth
- [ ] Existing profile, RBAC and session behaviour preserved through the auth swap
- [ ] **Agent chat UI** — send a prompt to the coordinator agent, stream the response, show which agent and which MCP tools were used
- [ ] **Agent registry UI** — list agents from the registry with version, replica count and health
- [ ] Basic authentication enforced on the agent-test UI at the gateway, plus a rate limit
- [ ] Joined to the Istio mesh, with a sidecar and an `AuthorizationPolicy` covering its calls to the agent gateway
- [ ] Instrumented with OpenTelemetry so a trace spans browser request → web → agent gateway → MCP → Feast
- [ ] Built and deployed by a Jenkins pipeline like every other deployable

Non-functional:
- [ ] Playwright suites (a11y, roles, assistant, quota) pass against the in-cluster deployment
- [ ] Web pod footprint stays within ~1-1.5 vCPU

## Architecture

```
browser ─HTTPS─▶ NGINX Ingress ─▶ web (Next.js, Helm, Argo CD)
                                    │  auth ──▶ PostgreSQL (in-cluster)
                                    └─ chat / registry ──▶ agentgateway ──▶ agents ──▶ MCP ──▶ Feast
```

Supabase leaves entirely. The two things it provided — Postgres and an auth layer —
are both already in the cluster: PostgreSQL is running for Feast offline, DataHub
and `ml_metadata`, and session handling moves into the app against a `webapp`
database of its own, consistent with the existing no-cross-write schema rule.

Vercel leaves with it. The app becomes an ordinary deployable: image built by
Jenkins, digest bumped in the GitOps repo, reconciled by Argo CD, routed by NGINX,
enrolled in the mesh, scraped by Prometheus. That is the whole point of the move —
one deployment path for everything, which is also what the deployment-diagram row
is grading.

The chat and registry UIs become routes inside this app rather than separate
deployments. One authentication story, one ingress, one image.

## Related Code Files

- Modify: `apps/web/**` (auth provider swap, chat route, registry route, OTel init), `apps/web/Dockerfile`
- Create: `apps/web/src/app/agents/chat/`, `apps/web/src/app/agents/registry/`, `apps/web/src/lib/auth/` (Postgres-backed sessions)
- Create in GitOps: `charts/web/` (or extend the existing chart), `apps/dev/web/values.yaml`
- Delete: Supabase client wiring, `supabase/` config and migrations once the auth swap is verified; any Vercel deployment configuration
- Modify: `docs/product.md` (relocated from `docs/phase2/product.md` under the phase-free docs layout)

## Implementation Steps

1. Inventory every Supabase touchpoint in `apps/web` before changing anything — auth calls, RLS-dependent queries, session helpers, and the migrations under `supabase/`. The RLS policies encode authorization rules that must survive the move; losing them silently is the main risk in this phase.
2. Implement Postgres-backed authentication and sessions against a dedicated `webapp` database. Port the RLS-derived rules into explicit application-layer authorization plus database constraints, and cover each with a test before deleting the Supabase path.
3. Verify profile switching, sign-up, sign-in and sign-out against the new backend — these were fixed in earlier work and must not regress. Run the existing Playwright `roles` suite as the check.
4. Build the agent chat route: prompt input, streamed response, and a panel showing which agent handled the turn and which MCP tools it called. The rubric wants a screen a grader can chat with, so streaming and tool visibility matter more than styling.
5. Build the agent registry route: list agents from the registry API with version, replica count and health.
6. Containerize with a multi-stage build; record the before/after image size for the Docker-optimization row.
7. Package as a Helm chart, deploy through Argo CD, route behind NGINX Ingress at the domain apex under the wildcard certificate from phase 4, reusing the single static IP — no second load balancer.
8. Apply gateway basic auth and a rate limit to the agent-test routes, sourcing the credential from Vault.
9. Enrol in the mesh; add an `AuthorizationPolicy` for its calls to the agent gateway; add OpenTelemetry instrumentation so the browser-to-Feast path is one trace.
10. Add its Jenkins pipeline using the shared library from phase 7.
11. Re-run the Playwright suites against the in-cluster deployment and capture the results.
12. Delete `supabase/` and the Vercel configuration once everything above passes.

## Success Criteria

- [ ] The app is reachable over HTTPS at the domain apex, behind the single existing NGINX load balancer, with `/agents/chat` and `/agents/registry` under the same host and session
- [ ] Sign-up, sign-in, sign-out and profile switching all work against in-cluster PostgreSQL, with no Supabase call remaining in the codebase
- [ ] Every authorization rule previously enforced by RLS has an equivalent test that passes
- [ ] A grader can open the chat UI, send a prompt, and see a streamed answer plus the agent and tools involved
- [ ] The registry UI lists all three agents with version, replicas and health
- [ ] Unauthenticated access to the agent-test UI is rejected; a request burst returns 429
- [ ] Kiali shows the web pod in the mesh; an `AuthorizationPolicy` governs its gateway calls
- [ ] One Jaeger trace spans browser → web → agent gateway → MCP → Feast
- [ ] A Jenkins pipeline builds and deploys it with no manual step
- [ ] Playwright a11y, roles, assistant and quota suites pass against the deployed app
- [ ] `python scripts/run_quality_gates.py` passes

## Risk Assessment

- **Replacing Supabase Auth is the riskiest edit in this phase, and it is not a swap of one library for another.** Supabase enforces authorization in the database through RLS policies; moving to a plain Postgres means those rules have to be re-expressed in application code and constraints. A missed policy does not fail loudly — it silently grants access. Mitigation: step 1 inventories every policy and step 2 requires a passing test per rule before the Supabase path is deleted. Do not delete `supabase/` until step 11 passes.
- **Auth was recently fixed and can easily regress.** Earlier plans closed real defects in sign-out and profile switching. Mitigation: the existing Playwright `roles` suite is the regression gate, run before and after the swap.
- **This phase earns 6 points and could absorb far more than 6 points of schedule.** The product surfaces are pre-existing, not new work, but polishing them is a bottomless task on a budget of ~230-260 cluster-hours. Mitigation: the three scored UIs and the migration are the deliverable; if the phase slips past a week, the product surfaces ship as-is and the phase closes.
- **Losing Vercel's build and CDN means the app now costs cluster resources.** Mitigation: ~1-1.5 vCPU budgeted, on the on-demand pool since it is user-facing and should not be preempted mid-demo.
