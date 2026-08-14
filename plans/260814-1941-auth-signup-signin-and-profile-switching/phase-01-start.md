---
title: "Phase 1: Supabase user table and AAL relaxation"
status: done
priority: P1
effort: "5h"
dependencies: []
---

# Phase 1: Supabase user table and AAL relaxation

## Overview

Turn `profiles` into a real user table (identity, not just a role), let a user
rename themselves without being able to change their own role, drop the AAL2
step-up requirement for this demo environment in a reversible way, and provision
one working account per role.

## Requirements

Functional:

- [x] `profiles` carries `display_name` and `email`, backfilled for both existing users
- [x] `handle_new_user()` copies email and `full_name` metadata on signup
- [x] Row owner can update `display_name` only; `role` is not writable by the owner
- [x] Privileged roles pass authorization at `aal1` in this environment
- [x] One account exists per role with a password held by the operator, never committed

Non-functional:

- [x] Every DDL change ships with a rollback file under `supabase/migrations/rollback/`
- [x] `is_aal2()` keeps telling the truth; the relaxation is a separate predicate

## Architecture

Two migrations, one seeding script.

**Identity columns.** `profiles` gains `display_name text` and `email text`.
Backfill runs from `auth.users` in the same migration. `handle_new_user()` is
replaced (it is already `security definer`) to insert those values on signup:

```sql
insert into profiles (user_id, role, email, display_name)
values (
  new.id,
  'analyst',
  new.email,
  nullif(trim(coalesce(new.raw_user_meta_data ->> 'full_name', '')), '')
)
on conflict (user_id) do nothing;
```

The `on conflict do nothing` clause stays: an exception in this trigger aborts
the `auth.users` insert and turns signup into a 500.

**Self-rename without escalation.** RLS policies cannot restrict columns, so the
column grant does it. `20260803214600_phase2_rls.sql:107` currently grants
`select, update` on the whole table to `authenticated`. Replace with:

```sql
revoke update on profiles from authenticated;
grant update (display_name) on profiles to authenticated;

create policy profiles_update_own on profiles
  for update using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));
```

`platform_admin` role administration keeps working because
`profiles_update_admin` runs for the admin's own grants — verify during
implementation whether the admin path needs `grant update (role)` restored for
that role, and if so route admin role changes through a `security definer`
function instead of a broad column grant.

**AAL2 relaxation.** Do not rewrite `is_aal2()` — a helper that lies about a
security fact is worse than the policy it relaxes. Add a named predicate whose
only job is to encode the environment decision:

```sql
-- Demo environment: no MFA enrollment path exists, so step-up is not required.
-- Reverting = restore this function to `select is_aal2()`.
create or replace function meets_step_up() returns boolean
language sql stable security definer set search_path = public
as $$ select true $$;
```

Then rewrite only the policies that called `is_aal2()` to call
`meets_step_up()`. `packages/contracts/src/authorization.ts:60-70` gets the
matching change in Phase 2's code sweep — track it here so the two never drift.

**Accounts.** Passwords cannot be set from SQL. Add
`apps/web/scripts/seed-demo-accounts.ts`, run manually with the service-role key
from the environment, which calls `auth.admin.createUser` (with
`email_confirm: true`) for one account per role and upserts the `profiles.role`.
It reads every password from env vars and prints none.

## Related Code Files

- Create: `supabase/migrations/<ts>_phase2_profile_identity.sql`
- Create: `supabase/migrations/<ts>_phase2_step_up_relaxation.sql`
- Create: `supabase/migrations/rollback/<ts>_phase2_profile_identity_down.sql`
- Create: `supabase/migrations/rollback/<ts>_phase2_step_up_relaxation_down.sql`
- Create: `apps/web/scripts/seed-demo-accounts.ts`
- Read for context: `supabase/migrations/20260803214500_phase2_schema.sql:26-31,145-185`
- Read for context: `supabase/migrations/20260803214600_phase2_rls.sql:13-52,103-120`

## Implementation Steps

1. Read the two existing migrations end to end; list every policy that calls `is_aal2()`.
2. Write the identity migration: columns, backfill from `auth.users`, replaced `handle_new_user()`.
3. Write the grant/policy change for owner-writable `display_name` only.
4. Write the step-up relaxation migration rewriting each `is_aal2()` policy to `meets_step_up()`.
5. Write both rollback files; confirm the down file restores the exact prior predicate.
6. Apply forward against the live project (`mcp__supabase__apply_migration`), then re-run `list_migrations`.
7. Prove the negative: as an `authenticated` user, `update profiles set role='platform_admin'` must fail.
8. Write and run `seed-demo-accounts.ts` for the four roles; record only the emails in the phase report.
9. Run `mcp__supabase__get_advisors` for security warnings introduced by the change.

## Success Criteria

- [x] `select user_id, role, email, display_name from profiles` returns populated rows for all accounts
- [x] Owner `update profiles set display_name = 'X'` succeeds; `set role = ...` is refused
- [x] A policy that previously required `is_aal2()` now passes for a password-only session
- [x] Four accounts exist, one per role, each with `email_confirmed_at` set
- [x] Advisors report no new `ERROR`-level finding

## Risk Assessment

- Broad `revoke update` could break an existing admin write path. Mitigation: enumerate every write to `profiles` in `apps/web/src` before revoking, and re-grant narrowly or move the admin path into a `security definer` function.
- Seeding with the service-role key bypasses RLS by design. Mitigation: the script is manual, never imported by app code, and reads credentials only from env.
- Backfilling `email` duplicates PII into a second table. Mitigation: it is already readable by the row owner and admins only; no new policy widens that.
