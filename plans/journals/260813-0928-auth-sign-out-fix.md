---
title: "Auth sign-out fix"
date: 2026-08-13
timezone: Asia/Ho_Chi_Minh
branch: codex/phase06-llm-submission
platform: Linux
status: complete
tags: [phase2, auth, qa]
---

# Auth sign-out fix

## Context

The protected shell's logout links requested `/sign-out`, but the route was
missing and browser QA found a 404. Registration remains intentionally outside
the product contract: one provisioned demo/grader account is supported.

## What happened

- Added the minimal same-origin GET route: clear `sb-access-token` and redirect
  to `/sign-in`; existing logout links and the session-reader contract stayed
  unchanged.
- Verified valid login, invalid-credential handling, logout, cookie absence,
  and the intentional no-sign-up result in the live browser flow.
- Code review scored the change 9/10.

## Verification

- Web tests: **184 passed**; live auth tests: **6 passed**.
- Cross-device browser suite: **60 passed**.
- Repository quality gate: **311 Python tests passed**, with Ruff, Black,
  Compose config, and evidence audit passing.

## Decisions and caveats

No sign-up flow was added. The logout boundary is deliberately a state-changing
GET to preserve the existing normal-link contract; if changed to POST later,
add CSRF protection. Cookie deletion is client-session cleanup, not immediate
provider-side token revocation; that requires an explicit Supabase session
contract change.

## Next

No further implementation work is required for this fix. AgentWiki publishing
was unavailable in this session, so this journal is recorded locally only.

Status: DONE
Summary: The `/sign-out` 404 was fixed with a minimal same-origin cookie-clearing
redirect, and supported auth/no-sign-up behavior passed the recorded web,
browser, repository, and review checks.
