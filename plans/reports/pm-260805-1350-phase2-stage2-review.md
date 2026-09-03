# platform .tage 2 — Completion Review

Target: `plans/260802-1037-unified-phase2-ml-llm-gitops/phase-02-build-product-shell-supabase-rbac-and-ux-states.md`
Branch: `dev` @ `e638b95` + 42 uncommitted files (working tree ahead of last commit).
Method: file/code evidence check per requirement + success criterion, `pnpm test`/`typecheck`/`lint` run live.

## Verdict

**Not complete.** File frontmatter `status: in_progress` matches reality. 0/9 requirement boxes and 0/9 success-criterion boxes ticked in the source file — none tick-eligible to `[x]` today either, because 3 of 5 sub-gaps identified in the completion plan (`plans/260805-0800-phase2-stage2-completion/`) are still unbuilt in the working tree.

## Requirements — evidence table

| # | Requirement | State | Evidence |
|---|---|---|---|
| 1 | Analyst pages (search, snapshot, explanation, RAG, compare, saved report, freshness) | Built | `apps/web/src/app/{page,companies,companies/[ticker],compare,reports,reports/[id]}.tsx` all exist |
| 2 | Separate LLM surfaces: assistant UI + registry UI | Built | `components/assistant/*`, `app/agents/registry/page.tsx` |
| 3 | Admin surfaces (session/cost/GitOps/health/exports/promote/rollback/teardown) | Built (UI) | `app/ops/evidence/page.tsx` |
| 4 | Fixed disclaimer on company/explanation/assistant/compare/export | Built | `components/shell/disclaimer-banner.tsx`, `components/assistant/assistant-message.tsx` both reference `DISCLAIMER_TEXT`; contract `DISCLAIMER_SURFACES` lists all 5 |
| 5 | RBAC in Supabase RLS + Next.js server boundary, never client-only | Built | `supabase/migrations/20260803214600_phase2_rls.sql`, `apps/web/src/lib/server/guards.ts` (`guardRequest`), pytest `tests/platform/product/test_rbac_rls.py` at 653 lines |
| 6 | 3 approved UI refs as responsive routes + deterministic screenshot fixtures, no boilerplate | Built | routes above + `e2e/evidence-manifest.ts` writes manifest per capture; PR #42 replaced create-next-app shell |
| 7 | Loading/empty/stale/degraded/forbidden/timeout/policy-blocked states per route | Built | `assistant-message.tsx` maps `timeout`, `policy_blocked`, `eks_off`, etc.; `lib/states/route-states.ts` |
| 8 | Registry/analyst/ops nav separated, shared contracts, assistant is overlay not substitute | Built | separate route trees + `packages/contracts` shared types |
| 9 | Evidence provenance exposed without leaking prompts/tokens/creds/PII | Built | `evidence-manifest.ts` fields (`sourceSha`, `gitopsSha`, `dataVersion`, `modelVersion`, `agentVersion`, `FORBIDDEN_PATTERNS` redaction); `record_audit_event` RPC (new migration `20260805090000_phase2_ai_usage_audit.sql`) has no free-text prompt column |

All 9 requirements now have code-level evidence. None were checked in the file — this review does not tick them itself (project-manager sync-back rule requires full-plan reconciliation, done in the completion-plan phase 5, not ad hoc here).

## Success criteria — evidence table

| # | Criterion | State | Evidence / gap |
|---|---|---|---|
| 1 | Analyst sees saved results + honest EKS-off state | Built | `route-states.ts`, `assistant-provider.tsx` "eks_off frame" comment + test |
| 2 | Platform viewer read-only, no mutation via UI or server | Built | `guardRequest` role checks; `test_rbac_rls.py` |
| 3 | Idempotent retry -> one transition, one outbox action | Built | `session-actions.ts` idempotency key path, `outbox_events` schema |
| 4 | Stale promotion -> fencing error, no GitOps mutation | Built | fencing token check in `session-actions.ts` + migration |
| 5 | Disclaimer on every decision-support surface | Built | see requirement 4 |
| 6 | UI-APPROVED-01 states in deterministic screenshots | Partial | `analyst-surfaces.spec.ts` exists and captures via `evidence-manifest.ts`; **not yet published** to `docs/platform/evidence/product/` (only `design/` refs there) |
| 7 | UI-APPROVED-02 assistant: stream, citations, tool trace, model version, no secret leak | Built (server) / Partial (evidence) | `POST /api/assistant/stream` route + test live; e2e specs (`assistant-streaming.spec.ts`, `assistant-quota.spec.ts`, `assistant-plane-off.spec.ts`) exist; not yet published as committed evidence |
| 8 | UI-APPROVED-03 registry + evidence lifecycle, unauthorized actions disabled server-side | Built | `platform-surfaces.spec.ts`, ops route + guards |
| 9 | Accessibility audit: keyboard, focus, labels, contrast, reduced-motion | **Missing** | no `@axe-core/playwright` in `apps/web/package.json`, no `a11y.spec.ts`, no axe config — confirmed via grep, zero hits |

## Cross-check against the completion plan (`plans/260805-0800-phase2-stage2-completion/`)

| Sub-phase | Status in working tree |
|---|---|
| 1 — quota/rate-limit/audit persistence | Done, uncommitted. Migration + RPC + contracts + tests live, `pnpm test` green (`ai-budget.test.ts` both packages) |
| 2 — AI request path + SSE transport | Done, uncommitted. `app/api/assistant/stream/route.ts` + test, `inference-stream.ts`, `streaming-transport.ts`, 3 e2e specs + 3 Playwright configs |
| 3 — outbox worker runtime | **Not started.** No `scripts/phase2/` directory, no `outbox-handlers.ts`. `drainOutbox` (`apps/web/src/lib/server/outbox-worker.ts`) still has no caller — a provision request has nothing to claim its outbox event |
| 4 — coverage gate + component tests | **Not started.** No `coverage` key in either `vitest.config.ts`; 90/90 threshold unenforced, real number unknown |
| 5 — accessibility + evidence publication | **Not started.** No axe spec/dep, no `publish-evidence.ts`, `docs/platform/evidence/product/` holds only the 3 original design refs |

Sub-phases 1-2 explain most of requirement-level "Built" status above; sub-phases 3-5 are exactly why success criteria 6/7/9 stay "Partial"/"Missing" and why the file's checkboxes are correctly still unticked.

## Live gate results (run this session)

```
pnpm --filter @distresslens/web typecheck   -> pass
pnpm --filter @distresslens/web lint        -> pass
pnpm test (contracts + web)                 -> 182 tests pass (71 + 111)
```
Python RLS/quality gates not re-run this pass (no code change since last full run recorded in the completion plan).

## Recommendation

Do not tick any box in `phase-02-build-product-shell-supabase-rbac-and-ux-states.md` yet — sub-phases 3-5 of the completion plan own the remaining evidence, and the skill's sync-back rule forbids partial-phase ticking. Sequence:

1. Commit sub-phases 1-2 (currently uncommitted, tests green) — reduces risk of losing 538+ lines of working, tested code.
2. Implement completion-plan phase 3 (outbox worker) — currently the most operationally dangerous gap: a real provision request today writes an outbox row nothing will ever claim.
3. Phase 4 (coverage gate), phase 5 (a11y + evidence publish) — phase 5's own task T5.5 is the correct place to tick phase-02's boxes, since it requires a named artifact per tick.

## Unresolved questions

- None. Evidence was directly verifiable from the repo; no ambiguous fields required a stakeholder decision.
