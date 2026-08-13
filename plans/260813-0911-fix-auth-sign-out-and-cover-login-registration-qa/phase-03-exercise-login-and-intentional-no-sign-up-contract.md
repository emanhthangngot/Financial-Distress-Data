---
title: "Phase 3: Exercise login and intentional no-sign-up contract"
status: complete
---

# Phase 3: Exercise login and intentional no-sign-up contract

## Overview

Exercise the real browser auth flow against the configured live Supabase test
account and make the intentional registration scope explicit in executable QA.

## Requirements

- [x] Valid sign-in -> submits the provisioned smoke account in the UI -> the
  app redirects to `/` and renders the authenticated shell.
- [x] Invalid sign-in -> submits a wrong password -> `/sign-in` remains visible
  with an alert and no server error page.
- [x] Sign-out -> uses the visible account menu -> `/sign-in` is reached and
  `sb-access-token` is absent.
- [x] Registration probe -> visits `/sign-up` -> the route is not exposed,
  matching the documented one-account scope.

## Implementation Steps

1. Extend the opt-in live Playwright suite with UI login, invalid-login,
   logout, and no-sign-up assertions.
2. Run the suite using the existing disposable smoke account setup; do not add
   a second account or commit credentials.
3. Capture status, browser console/network observations, and any blockers.

## Todo

- [x] Add live browser assertions.
- [x] Run the live auth suite.
- [x] Confirm the no-sign-up result is intentional rather than an untriaged
  404.

## Success Criteria

Supported login and logout pass in a real browser, invalid credentials fail
gracefully, and registration is explicitly verified as intentionally absent.
