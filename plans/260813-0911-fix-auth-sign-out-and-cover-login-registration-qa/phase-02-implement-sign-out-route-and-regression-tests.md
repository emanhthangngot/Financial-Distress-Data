---
title: "Phase 2: Implement sign-out route and regression tests"
status: complete
---

# Phase 2: Implement sign-out route and regression tests

## Overview

Add a real GET boundary for the existing logout links and test its redirect and
cookie-clearing behavior without changing the shared session reader.

## Requirements

- [x] User-menu or analyst-shell logout link -> requests `/sign-out` -> the
  `sb-access-token` cookie is deleted and the response redirects to `/sign-in`.
- [x] Route regression test -> exercises the redirect and cookie deletion -> no
  404 regression is possible without a failing test.

## Implementation Steps

1. Read the code standards available in the repository and adjacent Next.js
   route/test patterns.
2. Add `apps/web/src/app/sign-out/route.ts` using the existing cookie name and
   a safe same-origin redirect target.
3. Add a focused route test and preserve the two existing shell links.
4. Run the focused Vitest/typecheck checks immediately.

## Todo

- [x] Implement the route.
- [x] Add and pass the route regression test.
- [x] Verify no unrelated files changed.

## Success Criteria

The protected shell's existing logout affordances no longer produce a 404,
the cookie is cleared, and focused tests/typecheck pass.
