---
title: "Phase 2: Session integrity and guest state"
status: done
priority: P1
effort: "6h"
dependencies: [1]
---

# Phase 2: Session integrity and guest state

## Overview

Fix the three server-side defects that make a signed-in user decay into a guest
and a guest look like an analyst: no refresh token (RC3), a fabricated `aal`
read (RC5), and a guest session that reports `role: "analyst"` for display
(RC2).

## Requirements

Functional:

- [x] A session survives access-token expiry through refresh-token rotation
- [x] `aal` comes from the verified JWT claim, never from `User.aal`
- [x] A guest is represented as a guest everywhere, with no analyst role fallback
- [x] Sign-out clears both cookies and revokes the upstream Supabase session

Non-functional:

- [x] Refresh failure fails closed to the guest path, never to a 500 on every route
- [x] The cookie contract is defined in exactly one module

## Architecture

**Cookie contract in one place.** `sb-access-token` is currently a string
literal in `sign-in-action.ts:32`, `session.ts:83`, and `sign-out/route.ts:4`.
Extract `apps/web/src/lib/server/auth-cookies.ts` exporting the two cookie names,
the shared cookie options, and `setSessionCookies` / `clearSessionCookies`. Add
`sb-refresh-token` (httpOnly, `sameSite: "lax"`, `secure` in production, `path:
"/"`, `maxAge` ~30 days).

**Refresh in middleware, not in a page.** A Server Component cannot write
cookies, so `resolveSession` cannot rotate tokens where it runs. Add
`apps/web/src/middleware.ts`: when `sb-access-token` is absent or rejected and
`sb-refresh-token` is present, call `auth.refreshSession({ refresh_token })` with
an anon-key client, and write the new pair onto the `NextResponse`. On failure,
clear both cookies and continue — the request then renders the honest guest
state. Do not add `@supabase/ssr`; the existing `supabase-js` client plus
`NextResponse.cookies` covers this, and a new dependency here would duplicate
`lib/server/supabase.ts`.

Matcher excludes `/_next/*`, static assets, and `/api/assistant/stream` (an SSE
route must not be buffered behind a refresh round trip).

**Truthful AAL.** Replace `readAssuranceLevel(user)` in `session.ts:135-140`
with a claim read from the access token — the token is already verified by
`auth.getUser()` before this runs, so decoding the payload for the `aal` claim is
a read of verified data, not an independent trust decision:

```ts
function readAssuranceLevel(accessToken: string | null): "aal1" | "aal2" {
  const claims = decodeJwtPayload(accessToken); // base64url payload, no verification
  return claims?.aal === "aal2" ? "aal2" : "aal1";
}
```

Keep the fail-closed default. Pair this with the contract change agreed in
Phase 1: `packages/contracts/src/authorization.ts:60-70` stops denying
privileged roles at `aal1`. Do it as a named exported constant
(`STEP_UP_REQUIRED = false`) with a comment tying it to `meets_step_up()` in the
database, so both halves of the downgrade are greppable and reversible together.
`AAL2_REQUIRED` stays in the denial union — the code path is dormant, not deleted.

**Honest guest.** `session.ts:88-96` returns `user: { displayName: "Khách", role:
"analyst" }`. Widen `SessionUser.role` to `Role | null` and return `null`, then
fix the consumers the type checker flags (`user-menu.tsx` `ROLE_LABELS[role]`,
`analyst-shell.tsx` nav). Phase 4 owns what they render instead.

**Sign-out.** `app/sign-out/route.ts` clears the access cookie only. Clear both
via `clearSessionCookies`, and call `auth.signOut()` with the caller's token so
the refresh token is revoked server-side rather than merely forgotten by the
browser — the follow-up recorded in
`plans/reports/pm-260813-0932-auth-sign-out-fix.md:36-37`.

## Related Code Files

- Create: `apps/web/src/lib/server/auth-cookies.ts`
- Create: `apps/web/src/middleware.ts`
- Create: `apps/web/src/lib/server/jwt-claims.ts` (+ test)
- Modify: `apps/web/src/lib/server/session.ts`
- Modify: `apps/web/src/lib/server/sign-in-action.ts`
- Modify: `apps/web/src/app/sign-out/route.ts` (+ `route.test.ts`)
- Modify: `packages/contracts/src/authorization.ts` (+ `authorization.test.ts`)
- Modify: `apps/web/src/components/shell/user-menu.tsx`, `analyst-shell.tsx` (type fallout only)

## Implementation Steps

1. Extract `auth-cookies.ts`; point the three existing call sites at it (no behavior change yet).
2. Store the refresh token on sign-in.
3. Add `jwt-claims.ts` with a payload decoder + unit tests for malformed, missing, and `aal2` tokens.
4. Swap `readAssuranceLevel` to the claim read; update `session.ts` tests.
5. Flip the step-up requirement in `authorization.ts` behind `STEP_UP_REQUIRED`; update the AAL2 tests to assert the new contract rather than deleting them.
6. Make the guest session return `role: null`; fix type fallout minimally.
7. Add `middleware.ts` with rotation + fail-open-to-guest; unit-test the decision function separately from the Next.js runtime.
8. Rework sign-out to clear both cookies and revoke upstream.

## Success Criteria

- [x] Vitest: expired access token + valid refresh token -> rotated pair, session preserved
- [x] Vitest: invalid refresh token -> both cookies cleared, guest state, no throw
- [x] Vitest: token with `aal: "aal2"` claim -> `resolveSession` reports `aal2`
- [x] Vitest: `authorize({role: "platform_operator", aal: "aal1"}, "session.provision").allowed === true`
- [x] Vitest: guest session -> `user.role === null`
- [x] Sign-out test asserts both cookies cleared and `signOut` called
- [x] `pnpm --filter web typecheck` and the existing 184-test suite stay green

## Risk Assessment

- Middleware runs on every request; a bug there is a site-wide outage. Mitigation: the refresh decision is a pure function with its own tests, and any thrown error is caught into pass-through.
- Lowering the step-up requirement is a real security downgrade. Mitigation: one named constant, one named DB predicate, both documented in Phase 5; `AAL2_REQUIRED` machinery is retained so restoring it is a one-line change.
- Widening `SessionUser.role` to nullable ripples into UI. Mitigation: let the type checker enumerate the sites; do not add `?? "analyst"` fallbacks, which would reintroduce RC2.
