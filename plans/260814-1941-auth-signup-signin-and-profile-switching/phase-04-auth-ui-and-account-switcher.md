---
title: "Phase 4: Auth UI and account switcher"
status: done
priority: P1
effort: "7h"
dependencies: [3]
---

# Phase 4: Auth UI and account switcher

## Overview

Build the surfaces that end the dead end: a real entry point for guests, a
sign-up page, a sign-in page that can be prefilled, and an account menu that
switches profiles and signs out. Run this phase under `ak:frontend-design`
(escalating to `ak:ui-ux-pro-max` for the auth card layout), reusing the
existing design tokens rather than inventing a second visual language.

## Requirements

Functional:

- [x] Header shows `Đăng nhập` / `Đăng ký` for a guest and the account menu for a signed-in user
- [x] Guest denial states offer a sign-in link instead of a bare "not permitted" message
- [x] `/sign-up` renders a working registration form with inline validation and server error copy
- [x] `/sign-in` accepts `?email=` and prefills it
- [x] Account menu lists demo profiles with role labels; picking one signs out and returns to a prefilled `/sign-in`
- [x] Account menu shows the real role label, with a distinct guest state
- [x] A signed-in user can edit their display name from the account area

Non-functional:

- [x] Existing tokens only: `paper-*`, `ink-*`, `text-*`, `line-*`, `tap-target`, `shadow-(--shadow-popover)`
- [x] Keyboard reachable, labelled inputs, `role="alert"` on errors, 44px targets — the a11y suite already enforces this
- [x] Mobile 390px: no horizontal scroll (the existing `user-menu.tsx:75` viewport cap is the precedent)
- [x] All copy Vietnamese, matching the tone already in the shell

## Architecture

**Guest chrome.** platform .akes `SessionUser.role` nullable. `analyst-shell.tsx`
and `user-menu.tsx` branch on it: a null role renders an auth pair
(`Đăng nhập` primary, `Đăng ký` secondary) in place of the avatar menu, and the
nav hides the destinations a guest cannot use rather than rendering them into a
denial. This is the direct fix for RC1 and RC2.

**Shared auth layout.** `components/auth/auth-card.tsx` holds the centred card
currently inlined in `app/sign-in/page.tsx:14-19`, so sign-in and sign-up cannot
drift apart. `SignInForm` stays as-is structurally (`useActionState`, `role="alert"`)
and gains a `defaultEmail` prop; `SignUpForm` is its sibling with name, email,
password, and a confirm-password field validated client-side before submit.
Cross-links between the two pages both ways.

**Denial copy.** The strings in the data port / state panels that today read
`Tài khoản hiện tại không được phép…` need a guest variant: when
`context.userId === null`, the panel renders "Đăng nhập để tra cứu doanh nghiệp"
with a link, because the user is not forbidden, they are anonymous. Locate every
such site via `StatePanel` usages and the `UNAUTHENTICATED` denial rather than by
string search alone.

**Account switcher.** Inside the existing `<details>` menu, below the identity
block: a `Chuyển hồ sơ` section listing `demo-accounts.ts` entries, each a link
to `/sign-out?next=/sign-in%3Femail%3D…`. Reuse the existing GET sign-out route
(it already clears cookies) extended with a validated same-origin `next`. No
impersonation, no client-held credentials — the switch is a real sign-out
followed by a real sign-in, per the accepted decision.

**Display name editing.** A small form in the account menu (or a `/profile`
route if the menu gets crowded) calling `updateDisplayName`. Keep it one field.

## Related Code Files

- Create: `apps/web/src/app/sign-up/page.tsx`
- Create: `apps/web/src/components/auth/sign-up-form.tsx`
- Create: `apps/web/src/components/auth/auth-card.tsx`
- Create: `apps/web/src/components/shell/account-switcher.tsx`
- Modify: `apps/web/src/app/sign-in/page.tsx` (searchParams + shared card)
- Modify: `apps/web/src/components/auth/sign-in-form.tsx` (`defaultEmail`)
- Modify: `apps/web/src/components/shell/user-menu.tsx` (guest branch, switcher, role label)
- Modify: `apps/web/src/components/shell/analyst-shell.tsx` (guest nav)
- Modify: `apps/web/src/app/sign-out/route.ts` (validated `next`)
- Modify: guest-variant denial copy at its `StatePanel` call sites

## Implementation Steps

1. Load `ak:frontend-design`; inventory the tokens and existing form/menu patterns before writing markup.
2. Extract `auth-card.tsx`; refit `/sign-in` onto it with `defaultEmail` from `searchParams`.
3. Build `SignUpForm` + `/sign-up`, wired to the Phase 3 action, including the confirmation-required branch.
4. Add the guest branch to `user-menu.tsx` and `analyst-shell.tsx`.
5. Replace guest denial copy with sign-in calls to action.
6. Build `account-switcher.tsx` and extend the sign-out route with a validated `next`.
7. Add the display-name form.
8. Component tests for each new surface; extend the a11y spec to `/sign-up`.

## Success Criteria

- [x] Guest on `/` sees `Đăng nhập` in the header and a sign-in call to action in every empty state — no analyst avatar, no bare denial
- [x] `/sign-up` registers a new account and the header immediately shows that user
- [x] `/sign-in?email=a@b.c` renders with the field prefilled
- [x] Picking a demo profile ends at `/sign-in` with that email prefilled and its role labelled
- [x] Renaming updates the header without a manual reload
- [x] a11y spec green on `/sign-in`, `/sign-up`, and the guest `/`
- [x] 390px viewport: no horizontal overflow on any new surface

## Risk Assessment

- Nav/menu edits touch the shell every route renders. Mitigation: guest branch is additive and covered by both role fixtures (`DISTRESSLENS_FIXTURE_ROLE=signed_out` already exists in `session.ts:48`).
- A `next` on sign-out is an open-redirect surface. Mitigation: same validator as Phase 3, tested with absolute and protocol-relative inputs.
- Design drift between two auth pages. Mitigation: single `auth-card.tsx`, no page-local card styles.
