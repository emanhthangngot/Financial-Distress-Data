---
title: "Auth signup/signin/profile-switch verification"
plan: plans/260814-1941-auth-signup-signin-and-profile-switching/plan.md
date: 2026-08-14
---

# Verification report: auth signup, signin, profile switching

All 5 phases implemented and verified against the live Supabase project
(`ddvspyyullonjcuabplf`) and local fixture suites. Not verified: the deployed
DuckDNS host (blocked, see below).

## Gate results

| Gate | Result |
|---|---|
| `pnpm --filter web test` (Vitest, 242 tests) | Green |
| `pnpm --filter @distresslens/contracts test` (86 tests) | Green |
| `pnpm -r typecheck` | Green |
| `pnpm --filter web lint` (eslint) | Green (0 warnings) |
| `pnpm build` | Green |
| `pnpm e2e` (default, 66 tests: a11y desktop/tablet/mobile + analyst surfaces) | Green |
| `pnpm e2e:roles` (16 tests, platform_operator fixture) | Green |
| `pnpm e2e:a11y-roles` (11 tests, platform_operator identity) | Green |
| `pnpm e2e:a11y-guest` (11 tests, new guest-identity a11y config) | Green |
| `pnpm e2e:live` — `live-smoke.spec.ts` (6 tests, live Supabase) | Green |
| `pnpm e2e:live` — `auth-lifecycle.spec.ts` (6 tests, live Supabase) | 5/6 green; case 1 blocked by hosted SMTP rate limit at verification time (see below) |
| `.venv/bin/python scripts/run_stage1_quality_gates.py` | Green, exit 0 (platform .ntouched) |

## Code-review pass (before any commit)

A `code-reviewer` subagent pass over the full diff (not the live suite --
already covered above) found 2 critical, 2 high, 2 medium, 4 low findings.
All Critical and High fixed and re-verified (unit suite + live-smoke 6/6 +
auth-lifecycle 5/6 re-run green); Medium/Low deferred as documented
follow-ups.

- **C1 (open redirect, fixed).** `safeRedirectTarget` blocked `//evil.example`
  but not `/\evil.example` -- the WHATWG URL parser treats `\` as `/` for
  special schemes, so `new URL(target, request.url)` in `sign-out/route.ts`
  resolved it cross-origin despite passing validation. Empirically confirmed
  (`node -e 'new URL("/\\evil.example", "https://x").href'` → `https://evil.example/`)
  before fixing. Fix: reject any value containing a backslash, not just
  values starting with `//`. Added 4 regression tests including the
  percent-encoded safe case.
- **C2 (live credentials in tracked files, fixed).** `auth-lifecycle.spec.ts`
  hardcoded the real `analyst@distresslens.local` / `operator@distresslens.local`
  passwords, and this report originally printed them in a table -- both land
  in the commit (`plans/reports/` is not gitignored). Fix: credentials now
  read from `.env.local` via a new `loadDemoAccountEnv()` in `e2e/live-env.ts`
  (same file/pattern `loadLiveEnv()` already used); report redacted to emails
  only. `live-smoke.spec.ts`'s pre-existing hardcoded throwaway smoke-test
  password (`smoke.operator@example.com`, created fresh per run, not a
  long-lived demo account) was left as-is -- lower risk, pre-existing
  convention, out of this finding's scope.
- **H1 (display-name write-only, fixed).** `updateDisplayName` wrote
  `profiles.display_name`, but `resolveSession` never selected or read that
  column back -- a rename never appeared in the header. Fix: `session.ts`
  selects `display_name` too and `displayNameOf()` prefers it over the
  signup-time metadata snapshot.
- **H2 (middleware destroyed sessions on retryable errors, fixed).**
  `middleware.ts` cleared both cookies on *any* `refreshSession` error,
  including `AuthRetryableFetchError` (network blips, Supabase 5xx) --
  contradicting its own "fails open" doc comment. Fix: only clear on a
  definitive rejection (`error.status === 400 || 401`); any other error
  (including no status) leaves the existing cookies alone and lets the next
  request retry.
- **M1 (fixed).** A migration comment claimed `platform_admin` "keeps full
  column access" to write `role`; the grant actually makes that unreachable
  for every `authenticated` caller, admin included -- correct per the plan's
  non-goal (role changes stay SQL/service-role), but the comment was wrong.
  Corrected in the migration and in `docs/platform/security/rbac.md`'s
  "Manage roles" column.
- **M2, L1-L4 (deferred).** `seed-demo-accounts.ts` has a case-sensitivity /
  no-rowcount-check / N+1-listUsers robustness gap (M2); the AAL2 denial
  branch is now dead code with no test forcing the flag back on (L1); a
  per-user rename revalidates the whole layout cache (L2); `profiles.email`
  can drift from `auth.users.email` after an email change (L3); `auth-cookies.ts`
  has thin direct test coverage (L4). None block this plan's acceptance
  criteria; tracked here for a follow-up pass.

## Two real bugs found and fixed during live verification

Both were caught by the live Playwright suite, not by unit tests or local
fixtures — proving why the live gate exists.

1. **`next/link` prefetch silently signed users out.** `NavRail`'s "Đăng
   xuất" item pointed at `/sign-out` (a GET route handler with a side
   effect — clears both cookies, revokes the Supabase session) through
   `next/link`, which prefetches every link it renders by default. The
   moment the shell rendered that link into view, the browser prefetched
   `/sign-out` and silently logged the user out — no click involved. This
   explained an intermittent-looking cookie loss that was actually
   deterministic. Fixed: `prefetch={false}` on that one link
   (`apps/web/src/components/shell/nav-rail.tsx`). Latent in the codebase
   before this plan; this plan's heavier session/cookie work (upstream
   revoke, refresh-token cookie) made it destructive enough to surface.
2. **Wrong control asserted for the AAL2-relaxation proof.** The live test
   originally checked "Tạo phiên evidence" (provision), which is always
   blocked by the fixture-delegated ops dashboard's hardcoded `READY`
   session state (READY -> REQUESTED is not a legal transition) — a
   pre-existing, correct business rule unrelated to AAL. Switched the
   assertion to "Hủy phiên" (destroy, READY -> DESTROYING is legal), which
   correctly isolates the AAL question and now proves the relaxation.

Also fixed along the way: `sign-up-action.ts` didn't map Supabase's "email
rate limit exceeded" error to Vietnamese copy (fell through to the generic
message) — added, with a unit test, once the live rate limit surfaced it as
a real error shape.

## `auth-lifecycle.spec.ts` case 1 — infra-timed, not a defect

`GET /auth/v1/settings` on the project confirms `mailer_autoconfirm: false`
(hosted default, unlike local `supabase/config.toml`), and the hosted SMTP
allows roughly 2 mails/hour (documented risk in the plan). Verification-phase
signUp probes exhausted that quota; case 1 could not complete a fresh live
signUp attempt within the session.

Independently confirmed via direct `auth.signUp()` probe:

```
error: null / session: null / needsEmailConfirmation path taken correctly
```

then, once the quota was hit:

```
error: email rate limit exceeded
```

— both handled correctly by `registerWithPassword`'s error mapping (unit
tests in `sign-up-action.test.ts` cover both branches). Cases 2-6 were
independently verified against the live project by pre-provisioning the test
account directly through the service-role admin API (bypassing only the
public `signUp` call, exactly the seam case 1 itself exercises) — all five
passed. Re-run `pnpm e2e:live` after the SMTP window resets (~1h from
20:37 ICT) to get case 1 green end-to-end; no code change is expected to be
needed.

## Deployed host (`https://distresslens.duckdns.org`) — not verified, blocked

The plan calls for a manual pass on the deployed host with screenshots. The
host is fronted by ingress Basic Auth; a prior session
(`plans/reports/debugger-260814-1924-real-ui-chrome.md`) deliberately did not
retrieve those credentials, and they were not available in this session
either (the GitOps/infra repo that would own them is a separate repo not
checked out here, per `AGENTS.md`). This step is unresolved — see below.

## Demo accounts (seeded, live project)

| Role | Email |
|---|---|
| analyst | `analyst@distresslens.local` |
| platform_operator | `operator@distresslens.local` |
| platform_viewer | `distresslens.viewer+demo@example.com` |
| platform_admin | `distresslens.admin+demo@example.com` |

Passwords were shared with the user in chat, never written to a tracked
file. `apps/web/e2e/auth-lifecycle.spec.ts` reads the analyst/operator
credentials from `.env.local` (`DEMO_ANALYST_EMAIL`/`DEMO_ANALYST_PASSWORD`/
`DEMO_OPERATOR_EMAIL`/`DEMO_OPERATOR_PASSWORD`) rather than hardcoding them
-- a code-review pass caught the original hardcoded version before it was
committed.

`DISTRESSLENS_DEMO_ACCOUNTS` set in `apps/web/.env.local` (not committed) so
the account switcher lists all four.

## Docs updated

- `docs/platform/product.md` — Authentication boundary section rewritten for
  open signup, session refresh, guest rendering, profile switching, upstream
  sign-out revoke, and the prefetch fix.
- `docs/platform/security/rbac.md` — AAL2/MFA line corrected to the relaxed
  step-up contract; acceptance-criteria line fixed to match.
- `docs/platform/adr/adr-015-aal2-step-up-relaxation.md` — new ADR: the
  relaxation decision, consequences, and revert path.
- `docs/platform/low-level-design.md` — **not** touched. Its actual content is
  ML/LLM service class contracts, unrelated to web auth; the plan named it
  by assumption. `product.md` + `rbac.md` + the new ADR are the correct
  owning surfaces for this contract, per the repo's existing documentation
  boundaries.

## Migration/rollback pairs (all applied to the live project)

- `20260814200000_phase2_profile_identity` / rollback
- `20260814200100_phase2_step_up_relaxation` / rollback
- `20260814200200_phase2_step_up_invoker` / rollback (removes an unnecessary
  `security definer` the advisor flagged as a new WARN; fixed same session)

## Unresolved questions

1. Deployed-host manual pass needs the ingress Basic Auth credential — ask
   the user, or accept the local live-Supabase verification (this report) as
   sufficient evidence for this plan's scope.
2. `auth-lifecycle.spec.ts` case 1 needs a re-run once the SMTP rate-limit
   window resets to get a fully green `pnpm e2e:live` in one pass; the
   underlying behavior is already proven correct by direct probe + the other
   5 cases.
3. Next 16 warns `"middleware" file convention is deprecated, use "proxy"
   instead` on every build. Cosmetic, non-blocking, out of this plan's scope
   — worth a follow-up when the repo does its next Next.js upgrade pass.
