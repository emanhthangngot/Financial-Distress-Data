# Auth sign-out fix and login/register verification

Date: 2026-08-13  
Repository: `Financial-Distress-Data`  
Branch: `codex/phase06-llm-submission`

## Outcome

Fixed the browser-QA defect where the two protected-shell logout affordances
requested `/sign-out` but received `404`. The new route clears the existing
`sb-access-token` cookie and redirects to `/sign-in`.

The supported authentication flow now passes in a real browser. Registration
is intentionally not implemented: the Phase 2 auth contract provisions one
demo/grader account and explicitly excludes sign-up, password reset, and
account management. The live browser test verifies that `/sign-up` is not
exposed and that the sign-in page contains no registration affordance.

## Changes

- `apps/web/src/app/sign-out/route.ts`
  - Added a same-origin GET route for the existing normal logout links.
  - Deletes `sb-access-token` and redirects to `/sign-in`.
- `apps/web/src/app/sign-out/route.test.ts`
  - Covers cookie deletion and redirect location/status.
- `apps/web/e2e/live-smoke.spec.ts`
  - Added real UI login with valid credentials.
  - Added invalid-credential error coverage.
  - Added account-menu logout and cookie absence coverage.
  - Added the intentional no-sign-up contract check.

## Verification

| Command | Result |
|---|---|
| `pnpm --filter @distresslens/web exec vitest run src/app/sign-out/route.test.ts src/lib/server/sign-in-action.test.ts --coverage.enabled=false` | 4 tests passed |
| `pnpm --filter @distresslens/web test -- --coverage.enabled=false` | 22 files, 184 tests passed; 92.91% statements, 90.10% branches, 90.99% functions |
| `pnpm --filter @distresslens/web typecheck` | Passed |
| `pnpm --filter @distresslens/web lint` | Passed |
| `pnpm --filter @distresslens/web e2e:live` | 6 tests passed, 0 skipped |
| `pnpm --filter @distresslens/web e2e` | 60 tests passed, 0 skipped across desktop/tablet/mobile |
| `.venv/bin/python scripts/run_stage1_quality_gates.py` | 311 Python tests passed; Ruff, Black, Compose config, and Stage 1 evidence audit passed |

The live runner still prints the existing `next start` warning for the
standalone output and `NO_COLOR`/`FORCE_COLOR` notices; neither is a test
failure or introduced by this change.

## Acceptance mapping

- Existing shell logout link -> GET `/sign-out` -> cookie cleared, redirect to
  `/sign-in`, no 404: **passed** by route test and live browser test.
- Valid sign-in form -> real Supabase credentials -> authenticated root shell:
  **passed**.
- Invalid sign-in form -> wrong password -> stays on `/sign-in` with an alert:
  **passed**.
- Registration probe -> `/sign-up` -> not exposed by design: **passed and
  documented**, no fake flow added.
- Shared web/repository gates -> no regression: **passed**.

## Notes

- Supabase schemas, RLS policies, environment contracts, and the existing
  `sb-access-token` reader were not changed.
- Existing unrelated dirty worktree changes were preserved.
- The route is a state-changing GET because the existing shell contract uses a
  normal link and must remain usable without a client bundle. If the product
  later changes to a POST form/action, add CSRF protection; immediate token
  revocation would also require an explicit Supabase session contract change.
