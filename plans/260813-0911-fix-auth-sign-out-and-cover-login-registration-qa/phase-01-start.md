---
title: "Phase 1: Scout and lock the auth contract"
status: complete
---

# Phase 1: Scout and lock the auth contract

## Overview

Record the existing auth behavior and the browser-QA defect before editing
implementation code.

## Requirements

- [x] The web app has one server-side Supabase sign-in action and reads the
  `sb-access-token` cookie through `resolveSession`.
- [x] The product spec explicitly excludes sign-up, password reset, and account
  management; the supported registration result is therefore “not exposed”.
- [x] Both protected-shell logout affordances link to `/sign-out`, while no
  route exists and production QA observed a 404.

## Implementation Steps

1. Read `docs/phase2/product.md`, the auth phase plan, adjacent auth code, and
   the existing live smoke suite.
2. Define acceptance as WHO -> ACTION -> RESULT and preserve existing auth
   contracts.

## Todo

- [x] Scout routes, server action, session reader, shell links, and tests.
- [x] Capture the exact implementation and verification touchpoints in this
  plan.

## Success Criteria

The implementation can add only the missing route plus tests; no registration
surface or auth-provider contract change is required.
