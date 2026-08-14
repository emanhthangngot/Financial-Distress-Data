---
title: "Phase 3: Signup and signin server flows"
status: done
priority: P1
effort: "5h"
dependencies: [1, 2]
---

# Phase 3: Signup and signin server flows

## Overview

Add the server-side registration path that does not exist today, harden the
existing sign-in action against the new cookie contract, and give the UI a
server-rendered list of demo accounts to switch between.

## Requirements

Functional:

- [x] `signUp` server action creates an account, establishes a session, and lands on `/`
- [x] Duplicate email, weak password, and disabled-signup all return user-facing Vietnamese copy, never a raw Supabase string with internal detail
- [x] Optional display name from the form reaches `profiles.display_name`
- [x] A signed-in user can rename themselves
- [x] A server module lists selectable demo profiles (email + role label) without exposing passwords

Non-functional:

- [x] Rate limiting relies on Supabase's own auth limits; no new limiter
- [x] Every new action is unit-testable against a fake client, like `authenticateWithPassword`

## Architecture

**Preflight, before writing any code.** Confirm on the remote project whether
email confirmation is required. `supabase/config.toml:226` sets
`enable_confirmations = false`, but that file governs a local stack, not the
hosted project, and hosted default SMTP is limited to a handful of mails per
hour. If confirmation turns out to be required, the sign-up action must render
"check your email" copy instead of redirecting to `/`, and that branch is part of
this phase. Record the finding in the phase report before step 2.

**`sign-up-action.ts`**, mirroring the structure of `sign-in-action.ts` so the
two read the same way:

```ts
export async function registerWithPassword(
  client: SupabaseClient,
  input: { email: string; password: string; displayName: string | null },
): Promise<
  | { ok: true; session: { accessToken: string; refreshToken: string; expiresIn: number } }
  | { ok: true; needsEmailConfirmation: true }
  | { ok: false; message: string }
>
```

It calls `auth.signUp({ email, password, options: { data: { full_name } } })`.
`full_name` lands in `raw_user_meta_data`, which the Phase 1 trigger copies into
`profiles.display_name`. The exported action validates input (email shape,
password length matching the project's `minimum_password_length`), maps errors to
copy, writes cookies through `setSessionCookies`, and redirects.

Error mapping is a table, not a passthrough: `User already registered` ->
"Email này đã có tài khoản. Đăng nhập thay vì đăng ký."; weak-password ->
"Mật khẩu quá ngắn…"; `Signups not allowed` -> "Đăng ký đang tắt…"; anything
else -> one generic message. Do not echo an unmapped upstream error.

**Sign-in updated.** `signIn` now stores the refresh token too, and gains an
`email` prefill contract: `/sign-in?email=…` is read by the page (Phase 4) — the
action itself is unchanged in shape. Redirect target becomes
`/sign-in?next=` aware only if a redirect param already exists; otherwise keep
`redirect("/")`. Validate any `next` value as a same-origin relative path before
redirecting, so the switcher cannot become an open redirect.

**`updateDisplayName` action.** Updates `profiles.display_name` for
`auth.uid()` through the request client, which is exactly what the Phase 1
column grant allows; a role change attempted through the same path is refused by
Postgres rather than by an app-level check.

**Demo profile catalogue.** `apps/web/src/lib/server/demo-accounts.ts` exports
the switchable accounts read from a single env var
(`DISTRESSLENS_DEMO_ACCOUNTS`, a JSON array of `{email, role, label}`) so no
credential and no address is hardcoded in the repo. Empty or unset -> the
switcher renders nothing, and sign-in still works normally.

## Related Code Files

- Create: `apps/web/src/lib/server/sign-up-action.ts` (+ `sign-up-action.test.ts`)
- Create: `apps/web/src/lib/server/profile-actions.ts` (+ test)
- Create: `apps/web/src/lib/server/demo-accounts.ts` (+ test)
- Modify: `apps/web/src/lib/server/sign-in-action.ts` (+ `sign-in-action.test.ts`)
- Read for context: `apps/web/src/lib/server/session-actions.ts` (existing action idiom)

## Implementation Steps

1. Verify the remote Auth signup/confirmation settings; record the result.
2. Write `registerWithPassword` plus its error-mapping table, with unit tests against a fake client for: success, duplicate email, weak password, signups disabled, confirmation-required.
3. Write the `signUp` action wrapper (validate -> register -> cookies -> redirect).
4. Update `signIn` to persist the refresh token and to honour a validated same-origin `next`.
5. Add `updateDisplayName` and a test that the client-side path cannot change `role`.
6. Add `demo-accounts.ts` with parsing, validation, and an empty-config test.

## Success Criteria

- [x] Vitest covers every branch of the error-mapping table
- [x] A real sign-up against the live project produces `auth.users` + `profiles` rows with role `analyst` and the submitted display name
- [x] `next` values that are absolute URLs or protocol-relative are rejected
- [x] Attempting `role` update through `updateDisplayName`'s client path fails at the database
- [x] No Supabase error string reaches the UI unmapped

## Risk Assessment

- Open signup on a public host attracts junk accounts. Mitigation: new users get `analyst` only, ingress Basic Auth still fronts the host, Supabase auth rate limits stay enabled.
- Email confirmation being on would silently break the flow. Mitigation: it is verified in step 1 and has an explicit UI branch.
- A `next` parameter is a classic open-redirect. Mitigation: same-origin relative-path validation with a test for each rejected shape.
