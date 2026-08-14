# ADR-015: AAL2 Step-Up Relaxation for This Demo Environment

- Status: Accepted
- Date: 2026-08-14
- Deciders: Phase 2 architecture review
- Related: `docs/phase2/security/rbac.md`, ADR-008

## Context

`platform_operator` and `platform_admin` actions were gated on Supabase AAL2
(`is_aal2()` in the database, the AAL2 branch of `authorize()` in
`packages/contracts/src/authorization.ts`). This deployment has no MFA
enrollment flow, so a privileged account could sign in but could never clear
AAL2 -- every lifecycle mutation was permanently unreachable
(`plans/260814-1941-auth-signup-signin-and-profile-switching/plan.md`, RC5).

## Decision

Relax the step-up requirement for this demo environment, as two named,
reversible seams rather than an edit to the truth-telling primitive:

- Database: `meets_step_up()` (`supabase/migrations/20260814200100_phase2_step_up_relaxation.sql`)
  is a new function that every previously-`is_aal2()`-gated policy and
  `assert_platform_write_access()` now call. `is_aal2()` itself is untouched
  and still reports the caller's real assurance level.
- Application: `STEP_UP_REQUIRED` in `packages/contracts/src/authorization.ts`
  gates the AAL2 branch of `authorize()`; set to `false` here.

Both flip together -- a drift between them would mean the app and the
database disagree about who is privileged.

## Consequences

- `platform_operator` and `platform_admin` can mutate the evidence lifecycle
  with a password-only (AAL1) session.
- `AAL2_REQUIRED` stays in the denial union and `is_aal2()` stays truthful, so
  restoring real step-up is: revert `meets_step_up()` to
  `select is_aal2()` (`supabase/migrations/rollback/20260814200100_phase2_step_up_relaxation_down.sql`)
  and set `STEP_UP_REQUIRED = true`. No policy, route, or UI code changes.
- Until reverted, a compromised or shared privileged password is sufficient
  for a destructive lifecycle action. Ingress Basic Auth and Supabase's own
  auth rate limits are the remaining outer defenses.

## Alternatives Considered

- Rewriting `is_aal2()` itself to always return true: rejected -- a helper
  that lies about a security fact is a worse failure mode than the policy it
  relaxes, and it would make a future MFA rollout indistinguishable from this
  demo relaxation in the database.
- Building an MFA enrollment flow: out of scope for this plan (non-goal); the
  right fix when this environment needs real step-up again.
