# Phase 2 Stage 2 — frontend implementation plan and design read

Source prompt: `plans/reports/prompt-260804-0835-phase2-stage2-frontend-implementation.md`
Gap report: `plans/reports/review-260803-2249-phase2-status.md`
Phase: **Phase 2** (explicit). Specs read: `AGENTS.md`, phase-02 plan file,
`docs/phase2/product.md`, `docs/phase2/security/rbac.md`,
`docs/phase2/requirements.md`, `docs/phase2/evidence-contract.md`,
`docs/phase2/architecture.md`, `packages/contracts/src/*`, both Supabase
migrations, `tests/phase2/product/`.

## Design Read

> Reading this as: a dense financial-risk operations product for analysts and
> platform operators, with a calm evidence-control-room language, leaning
> disciplined neo-grotesque product UI.

Design dials: `DESIGN_VARIANCE=3`, `MOTION_INTENSITY=2`, `VISUAL_DENSITY=6`.

### Seeded direction

Seed = character count of `DistressLens Phase 2 Stage 2` = **28**.
Direction menu (10 entries): 1 brutalist, 2 editorial, 3 neo-grotesque product,
4 warm humanist, 5 terminal/monospace, 6 soft organic, 7 high-contrast Swiss,
8 archival instrument panel, 9 playful maximalist, 10 glass/futurist.
`28 mod 10 = 8` → **archival instrument panel**.

Kept, not moved to an adjacent direction: an instrument panel is exactly what a
GitOps/evidence control room and a distress-probability desk are — measured
gauges, engraved rules, tabular numerals, labeled provenance plates. It also
absorbs the reference screenshots' density without turning into generic SaaS.

### Aesthetic thesis

> Calm evidence instrument panel for Vietnamese financial-distress decisions:
> navy ink on cool paper, engraved 1 px rules instead of card shadows,
> restrained red/amber/green risk states that always carry a non-color label,
> Be Vietnam Pro for text and IBM Plex Mono for every number, identifier and
> SHA, a two-shell navigation model (analyst vs admin), and one memorable
> element — a persistent evidence ribbon that makes live/cached/GitOps state
> impossible to miss on every surface.

### Typography

- Display/UI: **Be Vietnam Pro** (`next/font/google`) — drawn for Vietnamese
  diacritics, so `Nguy cơ cao` / `Đồng bộ lần cuối` render without fallback
  swaps. Not Inter/Roboto/Arial/system.
- Numeric/identifier: **IBM Plex Mono** with tabular figures for probabilities,
  currency, revisions, run IDs, SHAs.

### Depth and radius

One depth strategy: engraved borders (`--border-hairline`) + a single low
ambient elevation reserved for overlays/popovers only. One radius scale
(`--radius-sm|md|lg`), no per-component ad-hoc values.

### Reference observations (from the three PNGs)

- **01 analyst overview** — 240 px left rail (icon+label, active item filled
  navy), 64 px header with centered search field, right-aligned freshness +
  bell + avatar. Body = 3 risk cards with left color bar, then a two-column
  split: attention table (7 columns, sortable headers, paginated 1-8/40) and a
  right alert rail (timeline dots + "Xem tất cả cảnh báo"), then a horizontal
  sector-bar chart with a market-average dashed reference line and a delta
  column, plus a method note. Density is high; spacing is ~16/24 px.
  Mobile: rail becomes a drawer, cards stack, table becomes per-row cards,
  sector chart keeps bars but drops to one column.
- **02 company detail** — breadcrumb, big ticker+name header, watchlist button
  right; 4-cell KPI strip (probability 78.6% in red with a "Rất cao" chip,
  delta, confidence, model version); 5 tabs; dual-axis quarterly line chart with
  hover tooltip and 8/12/24-quarter range toggle + export; below, a 2-up of
  indicator table and a diverging SHAP bar chart (signed, ±20 axis); then a
  source list with type chips and external links. Right column (~380 px) is the
  AI panel: user bubble, streamed answer with inline numbered citation chips,
  collapsible "Cơ sở & nguồn tham chiếu", collapsible tool-trace cards with
  status, composer, and a caution line.
- **03 admin** — visually distinct shell (`DistressLens Admin`, environment
  select, online/offline pill, desired commit chip). Row 1: plane health list +
  two cost gauges with hard-cap captions + next-session card with primary
  action. Row 2: Argo desired/live revision, sync health, last sync, repo
  links, and a horizontal audit strip. Row 3: 2-up pipeline table and promotion
  queue (both with row checkboxes and per-row actions). Row 4: A/B summary
  table and security/audit history. Footer: four observability deep links +
  budget precheck.

## Decisions taken (confirmed with user)

1. **Staged execution** with a review gate after each step.
2. **Typed data port** with two adapters: `REFERENCE_FIXTURE` (deterministic,
   offline, used by dev + Playwright) and Supabase/RLS (env-selected).
   Authorization, validation, quota and outbox logic are identical on both
   paths; only the row source swaps. Docker networking is unavailable in this
   sandbox (documented in `tests/phase2/product/conftest.py`), so a live
   Supabase instance cannot back the E2E run here.
3. **Hand-rolled SVG charts** — token-driven, accessible (table fallback,
   `aria`, non-color encoding), no chart dependency.
4. **Playwright with Chromium installed and executed** here to produce real
   screenshots + manifests.

## Implementation steps and gates

| Step | Content | Gate |
|---|---|---|
| 1 | Route/view-model/provenance/quota/audit contracts, fixture adapters, failing tests for every required state | plan + contracts review |
| 2 | Token layer (color/type/space/radius/shadow/focus/motion/z), app shells, keyboard + reduced-motion | visual direction review |
| 3 | `/`, `/companies`, `/companies/[ticker]`, `/compare`, `/reports/[id]` | analyst surface review |
| 4 | `/agents/chat`, `/agents/registry`, `/ops/evidence` | agent + admin review |
| 5 | Server actions/route handlers, RLS queries, outbox worker (lease, retry, idempotency, fencing), polling | server boundary review |
| 6 | Playwright fixtures at 1440/1024/390 for every state and role, manifests, self-review gate | delivery |

## Non-goals

- No AWS/EKS/Argo/K8s code in this repository (GitOps repo owns desired state).
- No Phase 1 edits: `dags/*.py` outside `phase2/`, `src/collectors|generator|
  streaming|transforms|quality|catalog|metadata`, `warehouse.db`, `outputs/**`,
  `docs/evidence/**`.
- No live cloud calls; no fabricated "executed" evidence.

## Acceptance criteria (WHO -> ACTION -> RESULT)

1. Analyst -> opens `/` signed out -> sees landing + auth entry, no portfolio
   rows leak, and the educational disclaimer is present.
2. Analyst -> opens `/companies/NVL` while the evidence plane is OFF ->
   sees `CACHED_RESULT` + `LIVE_UNAVAILABLE` labels with `cached_at`,
   `source_sha`, model/data version, and no live-inference affordance.
3. `platform_viewer` -> POSTs `session.provision` to the server action ->
   receives 403, no `outbox_events` row is created, one audit row is written.
4. `platform_operator` (AAL2) -> retries provision with the same idempotency
   key -> exactly one transition and one outbox row exist.
5. `platform_admin` -> submits a promotion with a stale fencing token ->
   receives `STALE_FENCING_TOKEN`, no outbox row, session state unchanged.
6. Outbox worker -> claims a `PENDING` event -> row becomes `CLAIMED` with
   lease + `claimed_by`; a second worker claims nothing; lease expiry makes it
   reclaimable; attempts increments on retry.
7. Operator -> requests provision above the declared monthly cap -> provision
   is blocked with the projected cost shown; `session.destroy` stays enabled.
8. Playwright -> runs the suite at 1440/1024/390 -> emits a screenshot plus a
   manifest carrying route, state, viewport, source SHA, GitOps SHA,
   data/model/agent version, expected/actual result, redaction status.
9. Reviewer -> opens company, model-explanation, chat, compare and export
   surfaces -> sees `Nội dung phục vụ mục đích học tập, không phải khuyến nghị
   đầu tư.` on each.

## Verify commands

```bash
pnpm --filter @distresslens/web lint
pnpm --filter @distresslens/web typecheck
pnpm --filter @distresslens/web build
pnpm --filter @distresslens/contracts typecheck
pnpm --filter @distresslens/contracts test
pnpm --filter @distresslens/web test:e2e
.venv/bin/python -m pytest tests/phase2/product/test_rbac_rls.py \
  tests/phase2/test_rubric_matrix.py tests/phase2/test_rubric_row_contracts.py
.venv/bin/python scripts/audit_phase2_evidence.py --matrix-only --strict
```

## Unresolved questions

- None blocking. Runtime gaps (no live Supabase, no EKS/Argo) are handled by
  the fixture adapter and reported as runtime gaps, never as passing evidence.
