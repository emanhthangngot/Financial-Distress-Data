# Plan Complete: Fix auth sign-out and cover login registration QA

Date: 2026-08-13  
Plan: `plans/260813-0911-fix-auth-sign-out-and-cover-login-registration-qa/`  
Status: **completed** — 4/4 phases, 23/23 tasks

## Achievements

- Fixed the protected-shell `/sign-out` 404 with a same-origin cookie-clearing
  redirect to `/sign-in`.
- Added focused route regression coverage.
- Proved valid login, invalid credentials, logout cookie clearing, and the
  intentional no-sign-up contract with live Supabase Playwright.
- Preserved the existing cookie, session, Supabase schema, RLS, and env
  contracts.
- Updated `docs/platform/product.md` with the auth boundary and logout caveat.
- Wrote the technical journal at
  `plans/journals/260813-0928-auth-sign-out-fix.md`.

## Testing status

| Gate | Result |
|---|---|
| Web Vitest | 184/184 passed; 92.91% statements, 90.10% branches, 90.99% functions |
| Live auth browser | 6/6 passed |
| Cross-device analyst browser suite | 60/60 passed |
| Web typecheck/lint/build | Passed |
| platform .epository gate | 311 pytest passed; Ruff, Black, Compose config, evidence audit passed |
| Code review | 9/10; zero critical issues |

## Risks and follow-up

- `GET /sign-out` is state-changing by design because the existing shell uses a
  normal link and must work without a client bundle. If the contract moves to a
  POST action, add CSRF protection.
- The route deletes the app cookie but does not revoke an already-issued
  upstream Supabase token; changing that requires an explicit auth contract.
- Git commit was intentionally not performed: the branch has mixed with
  unrelated pre-existing dirty files and the user did not authorize staging or
  committing.

## Unresolved mappings

None. All phase tasks and acceptance criteria are checked and the plan
validator reports a valid complete plan.
