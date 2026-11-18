# Accessibility Evidence

## Runs

| Run | Command | Identity | Plane | Result |
|---|---|---|---|---|
| Analyst | `pnpm e2e:a11y` | analyst, AAL2 | on | 9/9 pass |
| Platform | `pnpm e2e:a11y-roles` | platform_operator, AAL2 | off | 9/9 pass |

Both runs check the full route inventory (`/`, `/companies`, `/companies/NVL`,
`/compare?ticker=NVL`, `/reports`, `/agents/registry`, `/ops/evidence`) via
`@axe-core/playwright`, plus a `prefers-reduced-motion` check and a
focus-visible check on the first focusable control of the overview route.
Running the platform identity through the same analyst-only routes is
deliberate: a route this role cannot reach still renders a forbidden state,
and that state's accessibility is checked too.

**Zero serious or critical violations on either run.** No moderate violation
was found either — there is currently nothing to record in the "accepted
moderate violations" table below.

## Violations found and fixed

Two real violations surfaced on the first run of each spec, both
`color-contrast` (serious, WCAG 2 AA 1.4.3), fixed at the design-token level
in `apps/web/src/app/globals.css` rather than per-component, since the tokens
are shared:

| Token | Before | After | Where it showed | Ratio before → after |
|---|---|---|---|---|
| `--color-text-muted` | `#64748b` | `#5f6f88` | Body copy on `paper-1` background, every route | 4.47:1 → 4.79:1 |
| `--color-ai-500` | `#6366f1` | `#5b5ede` | White label on the assistant launcher pill | 4.46:1 → 5.12:1 |
| `--color-primary-500` | `#3b82f6` | `#4088f7` | Dark percentage label over a progress-bar fill (risk KPI strip) | 4.42:1 → 4.71:1 |

All three were near-misses (4.4x:1 against the 4.5:1 threshold), consistent
with the tokens having been contrast-checked by eye rather than measured at
authoring time. Each fix is a token adjustment of a few hex points — visually
indistinguishable at a glance, verified by rerunning the full analyst and
role Playwright suites (93 tests) after the change with no assertion changes
needed.

A third class of violation, `scrollable-region-focusable` (serious, WCAG 2A
2.1.1/2.1.3), was found on `/ops/evidence` under the platform run: a
horizontally-scrollable table wrapper (`overflow-x-auto`) had no way for a
keyboard-only user to reach its scrolled content. Fixed by adding
`tabIndex={0}`, `role="region"` and an `aria-label` (reusing the table's
existing `sr-only` caption text) to every such wrapper in the codebase, not
only the one axe happened to visit:

- `apps/web/src/components/ops/pipeline-table.tsx`
- `apps/web/src/components/ops/ab-experiment-summary.tsx`
- `apps/web/src/components/company/indicator-table.tsx`
- `apps/web/src/components/company/company-risk-table.tsx`
- `apps/web/src/components/company/trend-chart.tsx` (the wrapper now carries
  the region label; the inner `<svg>` became `aria-hidden` to avoid announcing
  the same description twice)

## Accepted moderate violations

None recorded. If a future run finds one that is genuinely not worth fixing
(a third-party embed, a case where fixing it would itself reduce clarity),
list it here with the rule id, the element, and the reason it stands.

## Keyboard and reduced-motion notes

- Every interactive control reachable via `Tab` carries a visible
  `:focus-visible` outline or box-shadow ring (Tailwind's focus-visible
  utilities); verified programmatically in `e2e/a11y.spec.ts` and manually via
  the existing `analyst-surfaces.spec.ts` keyboard-navigation test for the
  assistant panel (open by keyboard, `Escape` closes, focus returns to the
  launcher).
- `prefers-reduced-motion: reduce` is honored — no element carries an animated
  `transform` transition on the overview route. The only motion in the
  product is a 150ms hover lift on the assistant launcher and standard
  color/opacity transitions, neither of which axe or WCAG 2.3.3 requires
  suppressing under reduced motion (they are not vestibular-triggering
  parallax/motion effects).
