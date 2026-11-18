# platform .tage 2 — slice delivery report

Branch: `feat/phase2-stage2-frontend-ui-uplift`
Plan: `plans/260802-1037-unified-phase2-ml-llm-gitops/phase-02-build-product-shell-supabase-rbac-and-ux-states.md`
(status moved `todo` → `in_progress`; not `complete` — see Definition of Done below)

## Decisions applied

| Decision | Where recorded |
|---|---|
| `/agents/chat` dropped; assistant is a floating surface | phase-02 "Accepted deviations" §1; route table, requirements, steps, validation and success criteria all amended |
| Enterprise-fintech palette instead of the archival token set | phase-02 "Accepted deviations" §2; the frontend-design gate line banning a conventional SaaS palette is explicitly disapplied for this phase, every other line still holds |
| Staged slices with review after each | this report |
| Supabase keys supplied by the user | slice 3 adapter still blocked, see Gaps |

## Slice 1 — analyst routes

Routes: `/companies`, `/companies/[ticker]`, `/compare`, `/reports`, `/reports/[id]`.

`/reports` was added to `PRODUCT_ROUTES` and to phase-02's inventory: the rail
already linked there, and a nav item that 404s is worse than one that admits it
has not shipped. It needed a `listSavedReports` port method and a
`SavedReportSummary` contract — deliberately not the full `SavedReport`, so a
list the analyst skims does not carry every company's indicators and sources.

New components under `components/company/`: `company-risk-table` (the overview's
attention list and the search results are the same rows, so they are the same
component), `risk-kpi-strip`, `trend-chart` (SVG, dual axis, screen-reader
table), `indicator-table`, `shap-chart` (signed contributions around a zero
axis), `source-list`, `provenance-panel`, `comparison-split`,
`export-report-button`.

Two helpers removed repetition that would otherwise have drifted across six
pages: `lib/states/loading-copy.ts` and `lib/states/view-state.ts` — the latter
because `ViewState` is a discriminated union TypeScript will not narrow through
an inline ternary, and six pages each getting that subtly wrong was the
alternative.

Export is the browser's own print-to-PDF, with `data-print-hidden` on the
navigation, header and assistant. The report is already a complete document
carrying its disclaimer, sources and provenance, so a second server-side
renderer would add a dependency and a second thing to keep in sync.

## Slice 2 — platform routes

Routes: `/ops/evidence`, `/agents/registry`, on the separate admin shell.

New components under `components/ops/`: `session-state-timeline` (all nine
lifecycle states, terminal states drawn apart from the happy path),
`cost-gauge` (spent plus projected against the cap, denial stated in words),
`git-revision-card` (drift called out above the SHAs), `pipeline-table`,
`promotion-queue`, `audit-timeline`, `ab-experiment-summary`,
`agent-registry-list`, `role-action-button`.

`RoleActionButton` runs the same `authorize` the server action calls, so a
control the UI enables is one the server will accept. Denied controls render
disabled with their reason rather than disappearing — an operator who cannot see
the promote button cannot tell whether they lack the role or the feature is
missing. Verified in the browser as `platform_operator`: provision, destroy and
export enabled; promote and rollback disabled, each naming the missing action.

The assistant is not mounted on the admin shell, and the `registry`/`ops`
assistant scopes were deleted: `analyst.run_ai_request` is not a platform-role
action, so a launcher there could only ever deny.

## Slice 3 — server boundary and outbox

- `supabase/migrations/20260804150000_phase2_outbox_worker.sql` — adds
  `result`, `last_error`, `completed_at` and `fencing_token` to `outbox_events`;
  `claim_outbox_events` (lease + `for update skip locked`, reclaims expired
  leases so a crashed worker cannot strand infrastructure work),
  `complete_outbox_event` (rejects a claim the worker no longer holds and a
  token the session has rotated past), `fail_outbox_event` (returns to PENDING
  until `max_attempts`). `request_session_transition` now records the new
  fencing token on the outbox row so the worker can prove the session has not
  moved on.
- `lib/server/guards.ts` — role/AAL, origin, rate limit, quota, in that order:
  cheapest and most decisive first, returning the first denial rather than
  enumerating everything the caller failed.
- `lib/server/supabase.ts` — request client (RLS applies) and service client
  (worker only, refuses to construct in a browser).
- `lib/server/session.ts` — Supabase path added. Role comes from `profiles`
  keyed by the verified user id, never a client-supplied claim. A signed-in user
  with no profile row gets no role, not a default of `analyst`. Unknown
  assurance level fails closed to `aal1`.
- `lib/server/session-actions.ts` — validates the target state against the enum,
  re-derives role and AAL from the session, checks origin, then issues the one
  atomic RPC. Database errors are translated, never forwarded.
- `lib/server/outbox-worker.ts` — `drainOutbox` with handler, retry and
  stale-fence handling.

## Slice 4 — evidence and accessibility

`playwright.config.ts` (analyst, 1440/1024/390) and
`playwright.roles.config.ts` (platform operator, plane off). Both use
Chromium-based mobile emulation rather than the iPhone presets, so the evidence
run does not depend on a second browser engine being installed.

`e2e/evidence-manifest.ts` writes a JSON record beside every screenshot carrying
route, state, role, viewport, plane availability, data origin, data/model/agent
version, source SHA, GitOps SHA, expected/actual and redaction status. A
screenshot alone proves nothing; the manifest is what lets a reviewer tell a
fixture render from an executed run.

Specs assert behavior before capturing: disclaimer presence on every
decision-support surface, denial copy that does not name the protected resource,
cached data labelled as cached, replica counts marked unknown rather than zero
when the plane is off, and — the important one — that the assistant reports the
missing integration instead of inventing an analysis.

## Bugs this pass found and fixed

1. **Focus was lost when the assistant closed.** The launcher unmounted while
   the panel was open, so `focus()` on close targeted a detached node and the
   keyboard user landed at the top of the document. The launcher now stays
   mounted and hidden. Caught by the keyboard test, not by review.
2. **Horizontal overflow at 1024 and 390.** Two separate causes. At 1024 the
   eight-column table widened the document; `min-w-0` on cards and an
   `overflow-x-auto` wrapper both failed to contain it, so the fix was to remove
   the overflow at source — sector and data-through now appear only at `xl`, and
   the table composes down to six columns below that. At 390 the account popover
   and the wordmark together exceeded the header; the popover is capped to the
   viewport and the wordmark truncates before the controls do. The overflow test
   now names the offending elements on failure, which is what made both
   diagnosable.
3. **An `sr-only` table laid out to its content width** and pushed the document
   96px wide on a phone (fixed in the earlier UI pass; the wrapper carries
   `sr-only` now, not the table).

## Verification

```
pnpm --filter @distresslens/web lint        pass
pnpm --filter @distresslens/web typecheck   pass
pnpm --filter @distresslens/web test        pass (49 unit tests)
pnpm --filter @distresslens/web build       pass (8 routes)
pnpm --filter @distresslens/contracts typecheck / test   pass (52)
pnpm --filter @distresslens/web e2e         pass (33 — analyst, 1440/1024/390)
pnpm --filter @distresslens/web e2e:roles   pass (16 — operator, plane off)
```

Evidence artifacts written to `apps/web/e2e/.artifacts/evidence/`: 24 captures
plus their manifests.

## Gaps — explicitly not done

1. **Supabase-backed data adapter.** `DistressLensDataPort` still has one
   implementation, the fixture one. The server boundary, session resolution,
   guards and worker are written against the real schema but nothing has been
   executed against the live project, because `apps/web/.env.local` has no keys.
   Needed: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`,
   `SUPABASE_SERVICE_ROLE_KEY` (worker process only).
2. **RLS tests for every role/action pair × AAL1/AAL2.** `tests/platform/product/
   test_rbac_rls.py` was not extended; it needs a live database.
3. **The new migration has never been applied.** It is written against the
   existing schema but unexecuted.
4. **axe accessibility checks.** Keyboard, focus return and contrast-by-
   construction are covered; no automated axe pass has run.
5. **Coverage >90% on changed code** is unmeasured — no coverage reporter is
   configured.
6. **Server actions are not yet wired to the ops buttons.** `RoleActionButton`
   renders and authorizes correctly but does not submit; connecting it needs the
   Supabase path working first.

## Definition of Done status

Met: no placeholder remains; all eight route groups exist with typed
loading/success/failure states; analyst, registry and admin navigation are
separate; the disclaimer appears on company, explanation, assistant, comparison
and export; EKS-off UI is useful and labels cached data; Playwright manifests
carry route/state/viewport/provenance/redaction; verification commands pass;
platform .iles untouched.

Not met: RLS role/action coverage, outbox proof against a real database, cost
cap and quota enforcement at a live product boundary, and the accessibility
gate. Phase-02 stays `in_progress`.

## Open questions

1. Should the ops lifecycle buttons submit through `requestSessionTransition`
   before the Supabase adapter exists, or stay presentation-only until then?
2. Is browser print acceptable as the report export, or is a server-rendered PDF
   required for the coursework evidence?
3. `/reports` was added to the route inventory — confirm that is wanted rather
   than linking the rail straight to a report id.
