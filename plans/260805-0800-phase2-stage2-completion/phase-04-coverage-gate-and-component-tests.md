---
phase: 4
title: "Coverage gate and component tests"
status: pending
priority: P2
effort: "1-2d"
dependencies: [2, 3]
---

# Phase 4: Coverage gate and component tests

## Overview

The parent plan lists ">90% test coverage" under "never cut", but neither
`apps/web/vitest.config.ts` nor `packages/contracts/vitest.config.ts` configures
coverage at all, so the number is currently unknown and unenforced. This phase
measures it, adds the component tests needed to reach the bar honestly, and makes
CI fail below it.

## Requirements

Functional:

- `pnpm test` reports coverage and exits non-zero below threshold.
- Thresholds: 90% lines and 90% branches over `apps/web/src/lib`,
  `apps/web/src/components` and `packages/contracts/src`.
- Component tests cover the interactive surfaces whose behavior is currently only
  asserted end-to-end: assistant panel states, ops role-gated action buttons,
  disclaimer placement, nav rail and user menu.
- CI runs the same command and publishes the coverage summary.

Non-functional:

- Server page components (`src/app/**/page.tsx`) are excluded with a written
  reason: they compose already-tested lib functions and are asserted by
  Playwright, so a render test for them would assert markup, not behavior.
- No test asserts a private implementation detail to lift a number. A test that
  exists only to raise coverage is a defect, not a deliverable.

## Architecture

Coverage runs on v8 through Vitest's built-in provider — no new toolchain.

`apps/web` gains a jsdom environment project for component tests while lib tests
keep the default node environment, so a component test cannot accidentally rely
on a browser global that the server code will not have. Testing Library plus
`@testing-library/user-event` drive interaction; queries go through roles and
accessible names, which makes each test double as an accessibility assertion and
keeps it stable across the visual refinements the parent phase explicitly allows.

Exclusions, each with a comment stating why:

```
src/app/**/page.tsx        # composition of tested lib code; Playwright asserts it
src/app/**/layout.tsx      # ditto
src/lib/data/fixtures/**   # data, not logic
**/*.d.ts
```

## Related Code Files

- Modify: `apps/web/vitest.config.ts` — coverage provider, thresholds, exclusions with reasons, jsdom project for component tests
- Modify: `packages/contracts/vitest.config.ts` — same thresholds
- Modify: `apps/web/package.json` — Testing Library dev dependencies, `test:coverage` script
- Create: `apps/web/src/components/assistant/assistant-panel.test.tsx` — each state renders its copy; cancel calls the transport's abort; quota line reflects the port
- Create: `apps/web/src/components/ops/role-action-button.test.tsx` — disabled for viewer, enabled for operator, cost-cap denial copy, disabled state carries an accessible reason
- Create: `apps/web/src/components/shell/disclaimer-banner.test.tsx` — renders `DISCLAIMER_TEXT` on every surface in `DISCLAIMER_SURFACES`
- Create: `apps/web/src/components/shell/nav-rail.test.tsx` — role-scoped items; an analyst never sees platform navigation
- Modify: `.github/workflows/ci.yml` — run coverage, upload the summary
- Modify: `docs/phase2/product.md` — the testing contract: what unit, component and Playwright each own

## Implementation Steps

1. Turn on coverage with no threshold; record the real baseline per directory.
2. Set thresholds to 90/90 and let it fail — the failure list is the work plan.
3. Add the jsdom project and Testing Library, then write the component tests for
   the four surfaces above, driving them through roles and accessible names.
4. Close any remaining lib gaps with behavior tests, not detail tests; if a
   branch is genuinely unreachable, delete the branch rather than test it.
5. Wire CI and confirm it fails when a threshold is dropped by one point.
6. Run the gates.

## Success Criteria

- [ ] Maintainer -> runs `pnpm test` -> sees a coverage summary and a non-zero exit if any threshold is unmet.
- [ ] Maintainer -> deletes an assertion so a branch goes uncovered -> CI fails on that package.
- [ ] `apps/web/src/lib`, `apps/web/src/components`, `packages/contracts/src` -> each at or above 90% lines and 90% branches.
- [ ] Assistant panel component test -> renders every `AgentMessageState` plus `eks_off` -> each shows its own copy and the disclaimer.
- [ ] Ops action button test -> `platform_viewer` -> control is disabled and its disabled reason is exposed to assistive technology.
- [ ] Excluded paths -> each carries a comment naming what asserts it instead.
- [ ] `pnpm test`, `pnpm typecheck`, `pnpm lint`, both Playwright suites -> pass.

## Risk Assessment

- **Risk:** the threshold drives tests that lock in implementation detail and make refactors expensive. **Mitigation:** component tests query by role and accessible name only; a reviewer rejects any test asserting internal state or class names.
- **Risk:** jsdom component tests diverge from real browser behavior and give false confidence. **Mitigation:** they cover copy and role-gating; layout, focus order and contrast stay with Playwright and axe in phase 5.
- **Risk:** adding Testing Library slows install and CI. **Mitigation:** dev-dependency only, and the jsdom project runs in the same Vitest invocation.

## Task-Level Breakdown

> Grounded against `dev` at `e638b95`. Verified: `apps/web/vitest.config.ts` runs
> only `src/**/*.test.ts` in a `node` environment with no coverage provider;
> `packages/contracts/vitest.config.ts` likewise has no coverage; CI
> (`.github/workflows/ci.yml`) runs `pnpm typecheck` + `pnpm test` (stage 1 job
> separately runs the Python gate). The four component surfaces below exist:
> `assistant-panel.tsx`, `ops/role-action-button.tsx`, `shell/disclaimer-banner.tsx`,
> `shell/nav-rail.tsx`.

### T4.1 — Turn coverage on, record baseline

- **Files:** Modify `apps/web/vitest.config.ts`, `packages/contracts/vitest.config.ts`.
- **Spec:** set `test.coverage.provider = "v8"`, `reporter: ["text","html","json-summary"]`, `include` for `apps/web` = `src/lib/**/*.ts`, `src/components/**/*.tsx`, `src/components/**/*.ts` (non-test), `exclude` with the written reasons from the Architecture section (`src/app/**/page.tsx`, `src/app/**/layout.tsx`, `src/lib/data/fixtures/**`, `**/*.d.ts`). Run `pnpm test` with NO thresholds first and record the real per-directory line/branch numbers into the config comment as the baseline.
- **Verify:** `pnpm test` produces a coverage summary.

### T4.2 — Set 90/90 thresholds + jsdom project + Testing Library

- **Files:** Modify `apps/web/vitest.config.ts`; Modify `apps/web/package.json`.
- **Spec:** set `thresholds: { lines: 90, branches: 90 }` and let it fail — the failure list is the work plan. Add a second Vitest project `environment: "jsdom"` with `include: ["src/components/**/*.test.tsx"]`, leaving lib tests on `node` so a component test cannot accidentally rely on a browser global server code lacks. Add dev deps `@testing-library/react`, `@testing-library/user-event`, `jsdom`, `@testing-library/jest-dom`.
- **Verify:** `pnpm test` fails with a concrete list of uncovered files; `pnpm typecheck` still passes.

### T4.3 — Component tests x4

- **Files:** Create `apps/web/src/components/assistant/assistant-panel.test.tsx`, `ops/role-action-button.test.tsx`, `shell/disclaimer-banner.test.tsx`, `shell/nav-rail.test.tsx`.
- **Spec (query by role + accessible name only, never class/internal state):**
  - **assistant-panel:** renders the copy for every `AgentMessageState` plus `eks_off` (feed an `AssistantTurn` per state into the provider); the disclaimer renders on the surface; cancel calls the transport's `abort`; the quota line reflects the port's `readAiBudget` value.
  - **role-action-button:** disabled for `platform_viewer`, enabled for `platform_operator`; cost-cap denial (`blockedReason`) renders its copy; a disabled control carries an accessible reason (`aria-describedby`/`title`/`aria-disabled` + text) so assistive tech can read why.
  - **disclaimer-banner:** renders `DISCLAIMER_TEXT` on every surface in `DISCLAIMER_SURFACES`.
  - **nav-rail:** role-scoped items — an analyst never sees platform navigation; an operator never sees analyst pages; active-route aria-current works.
- **Verify:** `pnpm --filter @distresslens/web test`.

### T4.4 — Contracts thresholds

- **Files:** Modify `packages/contracts/vitest.config.ts`.
- **Spec:** same 90/90 thresholds over `src/**` excluding `*.test.ts`, `session-transitions.json` and `*.d.ts`. Close any gap with behavior tests (e.g. `role.ts`, `authorization.ts`, `ops.ts` already have suites — extend only where a branch is genuinely new).
- **Verify:** `pnpm test`.

### T4.5 — Close lib gaps honestly

- **Files:** any under `apps/web/src/lib`/`apps/web/src/components` the threshold names.
- **Spec rule (from the phase):** a test that exists only to lift a number is a defect. Prefer deleting genuinely unreachable branches; if a branch is reachable but untested, write a behavior test. No test asserts private implementation detail, class names, or internal state.
- **Verify:** `pnpm test` green at 90/90.

### T4.6 — CI + docs + full gates

- **Files:** Modify `.github/workflows/ci.yml` (the `contracts` job already runs `pnpm test`; add the coverage summary upload or a `coverage` step that fails on the same thresholds — confirm the coverage JSON artifact is published); Modify `docs/phase2/product.md` (the testing contract: what unit, component and Playwright each own).
- **Verify:** `pnpm test && pnpm typecheck && pnpm lint && pnpm --filter @distresslens/web e2e && pnpm --filter @distresslens/web e2e:roles`.
