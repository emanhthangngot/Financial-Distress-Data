# Frontend UI uplift — pass 1 (prompt-improve.md)

Branch: `feat/phase2-stage2-frontend-ui-uplift`
Scope: `plans/reports/prompt-improve.md` only. Phase-02 implementation prompt
(`prompt-260804-0835-...`) not started — waiting on your evaluation.

## Decisions you made, and what they cost

| Decision | Effect | Phase-02 conflict |
|---|---|---|
| Adopt prompt-improve hex palette | `globals.css` retokenized to `#2563EB` primary, `#6366F1` AI accent, `#F6F8FB`/`#FFFFFF` surfaces, `#172A46` rail | Phase-02 self-review gate bans generic-SaaS palette and purple-family accent. That gate line now fails by design. |
| Vietnamese copy | All new copy Vietnamese; disclaimer unchanged | none |
| Drop `/agents/chat`, floating assistant instead | Route removed from `PRODUCT_ROUTES`; assistant states moved to `ASSISTANT_STATE_COPY` | Phase-02 route table lists `/agents/chat` as a required surface with its own permission/quota states. Phase-02 acceptance needs updating deliberately. |

## What changed

**Design tokens** (`app/globals.css`) — full retoken: colour, radius (6/10/12/16),
shadow (card/popover/overlay/assistant), motion, z-index (`--z-assistant` between
drawer and overlay). Risk colours ship `-ink` (text-safe) and `-fill` (graphic)
variants; risk is never colour-only. Fonts unchanged (Be Vietnam Pro + IBM Plex
Mono, kept for Vietnamese diacritics).

**Shell**
- Rail 248 → 232px, grouped `Phân tích` / `Quản lý` / `Hệ thống`. Active item is a
  translucent blue wash + 3px left marker, not a solid white slab. Unshipped items
  carry a `Sắp có` badge instead of a lock glyph.
- Header reduced to search + status + account. The provenance strip is gone;
  `SystemStatus` replaces it — a one-line `Đã đồng bộ · DL-Score v2.1` control whose
  popover holds fixture origin, data version, model, agent, source SHA, GitOps SHA
  and run id. Built on `<details>`, works without hydration.
- `evidence-ribbon.tsx` deleted, `system-status.tsx` added. Admin shell moved to the
  same nav-group API and status control.

**Overview page** — was a title, a disclaimer and a role line. Now: page header
(title / description / freshness / period filter / `Xuất báo cáo`), compact
disclaimer banner, 4 KPI cards (each with keyboard-reachable definition and
drill-down), sector-risk bar chart with market-average reference line, risk-band
distribution, recent-alert rail, and a full-width attention table (table ≥ `lg`,
stacked cards below). All from existing `REFERENCE_FIXTURE` data through the data
port — no new fake values.

**Floating analysis assistant** — three modes: bubble (bottom-right, icon-only
below `lg`), docked support-widget rectangle (404px, `lg`+) and expanded full-viewport.
Below `lg` docked becomes a bottom sheet with safe-area padding and a body scroll
lock. One conversation thread per context key (`scope` or `scope:ticker`), so HPG
and NVL do not share a thread; threads are session-only, never persisted.
Escape closes; focus returns to the launcher. Quick actions are scope-specific —
the panel never opens on an empty chat box.

**Assistant context** is an allowlist (`lib/assistant/assistant-context.ts`):
route, scope, surface label, ticker, selected tickers, period, filters, data and
model version. Nothing else can reach the assistant.

## Missing backend, stated honestly

There is no agent request path yet (no authorised route handler, no quota
enforcement, no evidence-plane stream). `UNAVAILABLE_TRANSPORT` answers every
question with `Dịch vụ phân tích chưa được kết nối trong bản dựng này` plus a next
action. It never invents an analysis. Implement `AssistantTransport` against the real
handler and pass it to `AssistantProvider` — no component changes needed.

Also absent from the data contract: a portfolio-level time series. The
"risk trend over time" chart prompt-improve asked for has no data behind it, so the
analytics row is sector risk + band distribution instead. Adding it needs a
contract change.

## Files

New: `components/ui/{card,button,risk-badge,trend-indicator,state-panel}.tsx`,
`components/dashboard/{page-header,metric-card,sector-risk-chart,risk-distribution,attention-table,alert-timeline}.tsx`,
`components/assistant/{analysis-assistant,assistant-provider,assistant-launcher,assistant-panel,assistant-message}.tsx`,
`components/shell/system-status.tsx`,
`lib/assistant/{assistant-context,assistant-transport}.ts`.

Changed: `app/globals.css`, `app/page.tsx`, `components/shell/{analyst-shell,admin-shell,nav-rail,disclaimer-banner,icons}.tsx`,
`lib/states/route-states.ts` + test, `lib/data/fixture-adapter.ts`.

Deleted: `components/shell/evidence-ribbon.tsx`.

No new dependencies. Charts are CSS/SVG.

## Verification

```
pnpm --filter @distresslens/web lint        pass (0 problems)
pnpm --filter @distresslens/web typecheck   pass
pnpm --filter @distresslens/web test        pass (24)
pnpm --filter @distresslens/web build       pass
pnpm --filter @distresslens/contracts typecheck  pass
pnpm --filter @distresslens/contracts test       pass (52)
```

Manual, fixture mode (`DISTRESSLENS_DATA_SOURCE=fixture`), 1456 / 406 px:
no horizontal scroll (fixed an `sr-only` table that laid out to content width and
pushed the document 96px wide on a phone), assistant opens/expands/closes, Escape
returns focus, quick action produces the unavailable state with its next action.

Not verified: Playwright suite (none added this pass), roles other than analyst,
EKS-off rendering of the new overview, contrast measured with a tool rather than
by construction.

## Known gaps

- The sector-chart column is shorter than the alert rail beside it, so the row has a
  ragged bottom on wide screens. Cards themselves are full; nothing is an empty panel.
- Period filter changes the URL and the assistant context but no data yet — the
  fixture adapter has one period.
- `/companies`, `/companies/[ticker]`, `/compare`, `/reports/[id]`,
  `/agents/registry`, `/ops/evidence` are still unbuilt; the rail links to them.
  That is Phase-02 Stage 2 work, next pass.

## Open questions

1. Phase-02's self-review gate and route table now contradict two of your decisions.
   Update `phase-02-...md` and the rubric to match, or keep them and record the
   deviation as an accepted exception?
2. Should the assistant get a deep-linkable route (`/assistant`) for the expanded
   mode, or stay purely floating?
