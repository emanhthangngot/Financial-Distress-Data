---
title: "Auth signup signin and profile switching"
description: "Fix the deployed sign-in dead end, extend Supabase profiles into a real user table, and ship a complete signup/signin/profile-switch/signout flow for DistressLens web."
status: done
priority: P1
effort: "2-3d"
tags: [phase2, auth, supabase, web]
created: 2026-08-14
---

# Auth signup signin and profile switching

## Overview

The deployed app at `https://distresslens.duckdns.org` strands every visitor as
`Khách` (guest). There is no reachable sign-in entry point, no sign-up path, no
session renewal, and the only two Supabase accounts have passwords that were set
out of band and are not available. This plan makes authentication real end to
end: a `profiles` table that carries identity (not just a role), open sign-up
defaulting to `analyst`, a signin/signout loop that survives token expiry, and a
demo-account switcher so profiles can be changed without hunting for URLs.

Supersedes the "no sign-up, one demo account" contract recorded in
[`plans/260813-0911-fix-auth-sign-out-and-cover-login-registration-qa/`](../260813-0911-fix-auth-sign-out-and-cover-login-registration-qa/plan.md)
and in `apps/web/src/lib/server/sign-in-action.ts:22-24`. That contract is the
direct cause of symptom 1 below and is being replaced deliberately.

## Diagnosis (evidence-backed, not hypotheses)

| # | Defect | Evidence | Symptom the user sees |
|---|--------|----------|-----------------------|
| RC1 | No sign-in entry point anywhere in the UI | `grep '"/sign-in"' apps/web/src` matches only `app/sign-out/route.ts:16`; `components/shell/user-menu.tsx:82` offers only `Đăng xuất` | Stuck as `Khách`; `/sign-in` only reachable by typing the URL |
| RC2 | Guest is rendered as if signed in | `lib/server/session.ts:88-96` returns `user.role: "analyst"` with `context.role: null` | Full analyst nav renders, then every read denies with `Tài khoản hiện tại không được phép tra cứu doanh nghiệp` instead of "sign in" (see `plans/reports/debugger-260814-1924-real-ui-chrome.md:52`) |
| RC3 | Session cannot outlive one JWT | `lib/server/sign-in-action.ts:80-86` stores only `sb-access-token` with `maxAge = expires_in` (3600s); no refresh token is kept and nothing calls `refreshSession` | After ~1 hour a signed-in user is silently a guest again |
| RC4 | No sign-up; only two accounts exist | Remote `auth.users`: `smoke.operator@example.com` (`platform_operator`), `distresslens.grader@gmail.com` (`analyst`). No signup route in `app/` | "không có mật khẩu" — no way to obtain a usable account |
| RC5 | AAL is always `aal1`, so privileged roles are permanently blocked | `lib/server/session.ts:135-140` reads `user.aal`; `@supabase/auth-js@2.112.0` `types.d.ts` has no `aal` on `User` (it exists only on `JwtPayload:1667`). `packages/contracts/src/authorization.ts:60-70` denies every privileged action at `aal1` | `platform_operator` / `platform_admin` can sign in but can do nothing |
| RC6 | `profiles` carries no identity | `supabase/migrations/20260803214500_phase2_schema.sql:26-31` — columns are `user_id`, `role`, timestamps only | No name/email to render an account list or a switcher |

Not a defect: the ingress Basic Auth challenge (`401`) and the HTTPS cert are
working as designed and are out of scope.

## Accepted decisions

| Decision | Choice | Consequence |
|---|---|---|
| Sign-up openness | Open sign-up, new users default to `analyst` | Reuses the existing `on_auth_user_created` trigger; no invite table |
| Profile switching | Real separate accounts, switched by sign-out/sign-in, with a demo-account list that prefills the email | No impersonation code path, no admin role-editor UI in this plan |
| AAL2 requirement | Relaxed for this demo environment | Privileged roles work at `aal1`; the relaxation is one named DB function plus one contract change, both reversible, and must be documented as a deliberate downgrade |

## Goals

| # | Goal | Priority |
|---|------|----------|
| 1 | `profiles` is a usable user table (role + display name + email) with self-service name updates that cannot escalate a role | P1 |
| 2 | Any visitor can register, sign in, and sign out from the UI without typing a URL | P1 |
| 3 | A signed-in session survives access-token expiry instead of silently degrading to guest | P1 |
| 4 | Guest state is honest: no fake analyst chrome, a visible sign-in call to action on every denial | P1 |
| 5 | Every role (`analyst`, `platform_viewer`, `platform_operator`, `platform_admin`) has a working account and can actually use its surfaces | P1 |
| 6 | Flow proven against the live Supabase project and the deployed domain, with docs updated | P2 |

## Non-goals

- MFA/TOTP enrollment (explicitly deferred by the AAL2 relaxation decision).
- Admin UI for editing other users' roles (role changes stay SQL/service-role).
- Password reset by email, OAuth providers, magic links.
- Any change to platform .ipelines, DAGs, or the `ops` schema.

## Phases

| # | Phase | Status |
|---|-------|--------|
| 1 | [Phase 1: Supabase user table and AAL relaxation](./phase-01-start.md) | Done |
| 2 | [Phase 2: Session integrity and guest state](./phase-02-session-integrity-and-guest-state.md) | Done |
| 3 | [Phase 3: Signup and signin server flows](./phase-03-signup-and-signin-server-flows.md) | Done |
| 4 | [Phase 4: Auth UI and account switcher](./phase-04-auth-ui-and-account-switcher.md) | Done |
| 5 | [Phase 5: Verification and docs](./phase-05-verification-and-docs.md) | Done |

Dependencies: 2 depends on 1 (role/identity shape); 3 depends on 1 and 2
(cookie contract); 4 depends on 3 (server actions it calls); 5 depends on all.

## Acceptance criteria (WHO -> ACTION -> RESULT)

- [~] Guest visitor -> opens `/` on the deployed domain -> sees a `Đăng nhập`
      control in the header and a sign-in call to action instead of an analyst
      nav with denial copy. Verified against the live Supabase project through
      a local production build (`pnpm build && pnpm start`), not the deployed
      DuckDNS host itself -- ingress Basic Auth credential unavailable this
      session (see `plans/reports/verification-260814-2058-auth-flow-verification.md`).
- [~] New visitor -> submits the sign-up form with email + password -> gets an
      `auth.users` row and an auto-provisioned `profiles` row with role
      `analyst`. The remote project requires email confirmation
      (`mailer_autoconfirm: false`, discovered in Phase 3 preflight), so the
      visitor does not land on `/` with a session immediately -- they see a
      "check your email" state, confirm, and sign in separately. Verified via
      direct `auth.signUp()` probe and unit tests; the live end-to-end
      `auth-lifecycle.spec.ts` case is rate-limited pending an SMTP cooldown
      (see verification report).
- [x] Signed-in analyst -> waits past `jwt_expiry` (3600s) and reloads -> stays
      signed in via refresh-token rotation, and is not shown as `Khách`.
- [x] Signed-in user -> clicks `Đăng xuất` -> both auth cookies are cleared, the
      Supabase session is revoked, and `/sign-in` renders.
- [x] Signed-in user -> opens the account menu and picks another demo profile ->
      is signed out and returned to `/sign-in` with that account's email
      prefilled and its role labelled.
- [x] `platform_operator` account -> signs in with password only (`aal1`) ->
      reaches `/ops` and can request an evidence-session transition, with the
      guard returning `allowed` instead of `AAL2_REQUIRED`.
- [x] Any signed-in user -> attempts to update its own `profiles.role` via the
      anon-key client -> is refused by column grants (only `display_name` is
      writable by the row owner).
- [x] `resolveSession` -> receives a token whose JWT claims say `aal2` -> reports
      `aal2` (the field is read from the verified JWT claim, not from a
      nonexistent `User.aal`).

## Success Criteria

- [x] `pnpm --filter web test` (Vitest) green, new auth paths covered
- [x] `pnpm --filter web typecheck && lint && build` green
- [~] Live Playwright auth suite: `live-smoke.spec.ts` 6/6 green; `auth-lifecycle.spec.ts` 5/6 green, case 1 blocked by hosted SMTP rate limit at verification time (see verification report -- behavior independently confirmed by direct probe + unit tests)
- [x] `.venv/bin/python scripts/run_stage1_quality_gates.py` still green (no platform .egression)
- [x] Migration applies forward and its rollback restores the prior AAL2 policy
- [x] `docs/platform/product.md` records the new auth contract and the AAL2 downgrade

## Risks

| Risk | Mitigation |
|---|---|
| Open sign-up on a public domain invites junk accounts | New users get only `analyst`; ingress Basic Auth still fronts the host; Supabase auth rate limits stay on |
| Remote project may require email confirmation, so new accounts cannot sign in and the hosted SMTP allows ~2 mails/hour | Phase 3 step 1 verifies the remote Auth setting before any UI work and records the finding |
| Relaxing AAL2 weakens a documented security control | Implemented as a single named predicate with a rollback migration, and documented as an explicit demo-environment downgrade, not a silent edit of `is_aal2()` |
| Middleware token refresh can break every route at once | Refresh is fail-open to the existing guest path, and Phase 5 runs a full route smoke |

<!-- slug: auth-signup-signin-and-profile-switching -->
