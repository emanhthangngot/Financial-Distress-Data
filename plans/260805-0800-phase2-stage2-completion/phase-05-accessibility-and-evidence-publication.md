---
phase: 5
title: "Accessibility proof and evidence publication"
status: done
priority: P2
effort: "1d"
dependencies: [2]
---

# Phase 5: Accessibility proof and evidence publication

## Overview

The parent phase requires axe accessibility checks and deterministic screenshot
fixtures a reviewer can open. Today the Playwright suites assert keyboard access
and no-horizontal-scroll but run no axe pass, and every captured frame lands in
gitignored `apps/web/e2e/.artifacts/`, so `docs/platform/evidence/product/` holds
only the three approved design references. This phase closes both, and then
reconciles the parent phase's checklist against what now exists.

## Requirements

Functional:

- An axe pass runs over every route in the parent phase's route inventory, at
  1440, 1024 and 390, for both analyst and platform roles.
- Zero serious or critical violations; any accepted moderate violation is listed
  with its reason in the accessibility evidence document.
- The evidence run publishes manifests for every captured frame and PNGs for the
  rubric-named states into `docs/platform/evidence/product/`.
- Each manifest records route, state, role, viewport, plane availability, data
  origin, data/model/agent version, source SHA and GitOps SHA — the fields
  `evidence-manifest.ts` already writes.
- The parent phase-02 file's requirement and success-criterion boxes are ticked
  only where a named artifact or command proves them.

Non-functional:

- Publication is an explicit command, not a CI side effect, so committed frames
  change when someone means them to.
- Reduced-motion and focus-visibility assertions accompany the axe run, since axe
  cannot see either.

## Architecture

`e2e/a11y.spec.ts` drives the same routes the existing suites visit, injecting
`@axe-core/playwright` and failing on `serious`/`critical` impact. It runs as its
own Playwright project (`playwright.a11y.config.ts`) so an accessibility
regression is legible on its own rather than buried in the evidence run, and so
`pnpm --filter @distresslens/web e2e:a11y` is a command a reviewer can run.

`scripts/phase2/publish-evidence.ts` copies from `e2e/.artifacts/evidence/` into
`docs/platform/evidence/product/`: every `.json` manifest, and only the PNGs whose
slug appears in an explicit allowlist of rubric-named states. The allowlist lives
in the script, so what is committed is a reviewed decision rather than whatever
the last run happened to produce.

`docs/platform/evidence/product/README.md` indexes the frames by route and state
and states plainly that fixture-backed frames are `REFERENCE_FIXTURE`, not proof
of a live runtime — the same honesty rule the UI itself follows.

## Related Code Files

- Create: `apps/web/e2e/a11y.spec.ts` — axe over the route inventory, plus reduced-motion and focus-visible assertions
- Create: `apps/web/playwright.a11y.config.ts` — three viewports, both roles, plane on and off
- Modify: `apps/web/package.json` — `@axe-core/playwright` dev dependency, `e2e:a11y` script
- Create: `scripts/phase2/publish-evidence.ts` — manifest + allowlisted PNG publication
- Create: `docs/platform/evidence/product/README.md` — index, provenance rules, regeneration command
- Create: `docs/platform/evidence/product/accessibility.md` — axe results, accepted moderates with reasons, keyboard and reduced-motion notes
- Modify: `.github/workflows/ci.yml` — run `e2e:a11y`
- Modify: `plans/260802-1037-unified-phase2-ml-llm-gitops/phase-02-build-product-shell-supabase-rbac-and-ux-states.md` — tick boxes, set `status`
- Modify: `plans/260802-1037-unified-phase2-ml-llm-gitops/plan.md` — phase 2 row status

## Implementation Steps

1. Add the axe spec and its config; run it and record the real violation list.
2. Fix violations in the components — never by relaxing the rule set. If a rule
   is genuinely inapplicable, disable it per-node with a comment naming why.
3. Add the reduced-motion assertion (`prefers-reduced-motion: reduce` -> no
   animated transform) and a focus-visible assertion on the primary action of
   each route.
4. Write `publish-evidence.ts` with the allowlist; run the two evidence suites,
   publish, and review what landed.
5. Write the evidence README and the accessibility document.
6. Reconcile the parent phase-02 file: tick each requirement and success criterion
   that now has an artifact, and leave unticked anything that genuinely depends
   on phases 03-08, naming the dependency inline.
7. Run every gate, including the platform .ate, to prove nothing regressed.

## Success Criteria

- [x] Accessibility reviewer -> runs `pnpm --filter @distresslens/web e2e:a11y` -> zero serious or critical violations across every route, role and viewport. 9/9 pass (analyst, plane on); `e2e:a11y-roles` (platform operator, plane off) also 9/9.
- [x] Reviewer -> reads `docs/platform/evidence/product/accessibility.md` -> finds every accepted moderate violation with a stated reason. None found this run — the table is present and empty, with the note explaining what goes there.
- [x] Keyboard user -> tabs through each route -> reaches every interactive control with a visible focus ring; the assistant traps and restores focus correctly. `e2e/a11y.spec.ts` focus-visible check; `analyst-surfaces.spec.ts` keyboard-navigation test for the assistant panel.
- [x] User with `prefers-reduced-motion: reduce` -> loads any route -> sees no animated transform. `e2e/a11y.spec.ts` reduced-motion check.
- [x] Reviewer -> opens `docs/platform/evidence/product/` -> finds a manifest per captured frame and PNGs for the rubric-named states, each carrying route, state, role, viewport, plane availability and both SHAs. 30 manifests, 21 images published.
- [x] Reviewer -> reads the evidence README -> can tell a fixture-backed frame from an executed-runtime frame without opening the JSON. README states the `REFERENCE_FIXTURE` rule up front.
- [x] Maintainer -> runs `node apps/web/scripts/phase2/publish-evidence.mjs` after a fresh evidence run -> `git status` shows only intended frame changes. Script is additive-only (never deletes an unrecognized file) and prints a per-run summary; path is `.mjs` under `apps/web/scripts/phase2/`, not TypeScript at the repo root — no TS runner exists there (see phase-03's same decision for the outbox worker).
- [x] Maintainer -> opens parent `phase-02` -> every box is either ticked with an artifact or explicitly deferred to a named later phase. All 9 requirements and 9 success criteria ticked with a named artifact; the one explicit forward-reference (GitOps promotion/rollback's actual dispatch) names the unified plan's phase-03 control repo.
- [x] `.venv/bin/python scripts/run_stage1_quality_gates.py` -> still passes. 514 pytest passed, exit 0.

## Risk Assessment

- **Risk:** axe fixes chase the score and change approved UI hierarchy. **Mitigation:** fixes are limited to labels, roles, contrast and focus; any change to information hierarchy needs product-owner approval, per the parent phase's UI contract.
- **Risk:** committed PNGs drift from the code and become misleading evidence. **Mitigation:** each manifest carries the source SHA, and the README names the regeneration command; a frame whose SHA predates a UI change is visibly stale.
- **Risk:** ticking the parent checklist overstates completion. **Mitigation:** a box is ticked only with a named artifact or a runnable command in the same line of evidence; anything depending on phases 03-08 stays unticked with the dependency named.

## Task-Level Breakdown

> Grounded against `dev` at `e638b95`. Verified: `@axe-core/playwright` is **not**
> yet in `apps/web/package.json`; the evidence frames land in gitignored
> `apps/web/e2e/.artifacts/evidence/` and are captured with a manifest by
> `e2e/evidence-manifest.ts`; `docs/platform/evidence/product/` currently holds only
> the three `design/UI-APPROVED-*` references. Route inventory and roles come from
> the parent phase-02 (`analyst`, `platform_operator`, `platform_viewer`).

### T5.1 — axe suite + config

- **Files:** Create `apps/web/e2e/a11y.spec.ts`, `apps/web/playwright.a11y.config.ts`; Modify `apps/web/package.json`.
- **Spec:** add dev dep `@axe-core/playwright`. `a11y.spec.ts` walks the parent phase-02 route inventory (must cover `/`, company list/detail, compare, reports, agent registry, ops evidence) as `analyst` and platform roles, with plane on and off, at 1440/1024/390 (reuse the fixture-session env vars). Runs `AxeBuilder({ page })` and fails on any `serious`/`critical` violation. `playwright.a11y.config.ts` is a self-contained Playwright project (no `e2e` ignore that hides it) so `pnpm --filter @distresslens/web e2e:a11y` is a reviewable command.
- **Verify:** `pnpm --filter @distresslens/web e2e:a11y` records the real violation list (expected to fail first).

### T5.2 — Fix violations + motion/focus assertions

- **Files:** components the axe run names (`assistant-panel`, `nav-rail`, `role-action-button`, forms/labels).
- **Spec rule (from phase):** never relax the rule set; disable a genuinely inapplicable rule per-node with a comment naming why. Fix only labels, roles, contrast and focus — any information-hierarchy change needs product-owner approval per the parent UI contract. Add to `a11y.spec.ts`: a `prefers-reduced-motion: reduce` assertion (no animated `transform` chosen) and a focus-visible assertion that the primary action of each route has `:focus-visible` styling.
- **Verify:** `pnpm --filter @distresslens/web e2e:a11y` green.

### T5.3 — Evidence publication script

- **Files:** Create `scripts/phase2/publish-evidence.ts`.
- **Spec:** copies from `apps/web/e2e/.artifacts/evidence/` into `docs/platform/evidence/product/`: every `*.json` manifest, and only the PNGs whose slug is in an explicit in-script allowlist of rubric-named states — three approved routes x three viewports, plus `degraded`, `forbidden`, `cost-cap-denied`, `stale-fencing`, `quota-exhausted`, `streaming`. Does not delete sibling files it did not write. Prereqs: run `pnpm --filter @distresslens/web e2e` and `e2e:roles` first so `.artifacts/evidence/` is fresh.
- **Verify:** `node scripts/phase2/publish-evidence.ts`; then `git status` shows only intended frame changes.

### T5.4 — Evidence README + accessibility doc

- **Files:** Create `docs/platform/evidence/product/README.md`, `docs/platform/evidence/product/accessibility.md`.
- **Spec:** README indexes frames by route+state, states plainly which are `REFERENCE_FIXTURE` (not proof of a live runtime), and names the regeneration command. `accessibility.md` records the axe results, every accepted moderate violation with its reason, and the keyboard/reduced-motion notes.
- **Verify:** manual review of both docs.

### T5.5 — Reconcile parent phase-02 checklist

- **Files:** Modify `plans/260802-1037-unified-phase2-ml-llm-gitops/phase-02-build-product-shell-supabase-rbac-and-ux-states.md`; Modify `plans/260802-1037-unified-phase2-ml-llm-gitops/plan.md`.
- **Spec:** tick each requirement and success-criterion box that now has a named artifact or runnable command in the same line of evidence; leave unticked anything genuinely depending on phases 03-08, naming the dependency inline; set the parent phase-02 `status` and the plan's phase-02 row accordingly.
- **Verify:** review the diff of both parent files; each tick has a sibling artifact/command.

### T5.6 — Full gates including Phase 1

- **Verify:** `pnpm test && pnpm typecheck && pnpm lint && pnpm --filter @distresslens/web e2e && pnpm --filter @distresslens/web e2e:roles && pnpm --filter @distresslens/web e2e:a11y` and `.venv/bin/python scripts/run_stage1_quality_gates.py` all pass, proving no platform .egression.
