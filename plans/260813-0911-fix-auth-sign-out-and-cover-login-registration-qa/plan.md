---
title: "Fix auth sign-out and cover login registration QA"
description: "Fix the protected-shell sign-out 404 found during browser QA and prove the real Supabase login/logout flow while preserving the intentional no-sign-up product contract."
status: completed
priority: P1
effort: ""
tags: []
created: 2026-08-13
---

# Fix auth sign-out and cover login registration QA

## Overview

The completed browser QA found one user-facing defect: both protected-shell
logout links request `/sign-out`, but the route does not exist. The auth design
explicitly supports one provisioned demo/grader account and intentionally does
not expose registration, password reset, or account management. This plan adds
the missing logout boundary and tests the supported login/logout behavior plus
the intentional no-sign-up contract against the live Supabase-backed app.

## Goals

| # | Goal | Priority |
|---|------|----------|
| 1 | Fix the missing sign-out route without changing the session cookie contract | P1 |
| 2 | Exercise supported login/logout and the intentional no-sign-up behavior in a browser | P1 |
| 3 | Run repository/web gates and record reproducible evidence | P1 |

## Phases

| # | Phase | Status |
|---|-------|--------|
| 1 | [Phase 1: Scout and lock the auth contract](./phase-01-start.md) | Completed |
| 2 | [Phase 2: Implement sign-out route and regression tests](./phase-02-implement-sign-out-route-and-regression-tests.md) | Completed |
| 3 | [Phase 3: Exercise login and intentional no-sign-up contract](./phase-03-exercise-login-and-intentional-no-sign-up-contract.md) | Completed |
| 4 | [Phase 4: Run full gates and record evidence](./phase-04-run-full-gates-and-record-evidence.md) | Completed |

## Success Criteria

- [x] Protected shell -> requests `/sign-out` -> the access-token cookie is cleared and the browser lands on `/sign-in` without a 404 or console resource error.
- [x] Sign-in form -> submits valid Supabase credentials -> the app redirects to `/` and resolves the signed-in profile.
- [x] Sign-in form -> submits invalid credentials -> the form stays on `/sign-in` and shows a user-facing error without exposing a stack trace.
- [x] Product auth contract -> requests `/sign-up` -> registration is not exposed, matching the documented one-account scope; no fake registration flow is added.
- [x] Maintainer -> runs targeted auth tests, live auth Playwright tests, web quality gates, and the applicable repository gates -> all results are recorded with failures/skips explained.

## Scope and constraints

- In scope: `apps/web/src/app/sign-out/`, auth regression tests, and the live
  auth Playwright coverage/report for the defect and supported flow.
- Out of scope: Supabase migrations, RLS/policy changes, new user provisioning
  APIs, password reset, account management, GitOps, or unrelated pre-existing
  dirty worktree changes.
- Stable contracts: keep the `sb-access-token` cookie name and `signIn`
  server-action behavior unchanged; use the existing Next.js/Supabase patterns.
- Verification: targeted Vitest first, then live auth Playwright, then web and
  repository gates proportionate to the changed public route.

<!-- slug: fix-auth-sign-out-and-cover-login-registration-qa -->
