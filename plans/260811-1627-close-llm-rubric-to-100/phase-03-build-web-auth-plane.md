---
phase: 3
title: "Build the web auth plane so the UI rows are real"
status: complete
priority: P1
effort: "1d (no cluster)"
dependencies: [2]
---

# Phase 3: Build the web auth plane so the UI rows are real

# 0 points (unblocks 4 UI points + the 7 correlated-run rows)

## Overview

User decision, 2026-08-11: build Supabase auth for real rather than capturing the
UI in fixture mode. This phase is **new build work**, not capture — the red team
established that the "already built" premise is false for the two UI rows and the
assistant round-trip. It runs with the cluster down.

## Requirements

- Functional: a signed-in session is obtainable in the deployed web app; the
  agent registry page renders from the live registry (not fixtures); a real
  generation can be driven through `/api/assistant/stream` end to end; the
  `web-runtime-config` secret exists as a SealedSecret; the pod's provenance env
  vars are populated so the live registry adapter does not fail closed.
- Non-functional: the Supabase service-role key never enters a container image, a
  values file, an evidence file, or either repository. Only anon/publishable
  values reach the pod.

## Architecture

**What is missing today, verified:**

- `apps/dev/web/values.yaml:25-26` mounts `NEXT_PUBLIC_SUPABASE_URL` and
  `NEXT_PUBLIC_SUPABASE_ANON_KEY` from a Secret named `web-runtime-config` that
  **exists nowhere** in the GitOps repo, and `charts/web/templates/deployment.yaml`
  renders a non-optional `secretKeyRef` → `CreateContainerConfigError`.
- Nothing in `apps/web/src` sets the `sb-access-token` cookie;
  `src/lib/server/session.ts` only reads it. A browser hitting the gateway is
  permanently signed out (`role: null`), and `resolveSession` throws outright when
  neither fixture mode nor Supabase is configured.
- `src/lib/data/index.ts::getDataPort()` throws unless
  `DISTRESSLENS_DATA_SOURCE=fixture` **or** Supabase is configured; the values
  file sets neither.
- The live registry path (`src/lib/data/supabase-adapter.ts:186-191`) is reached
  only in Supabase mode with `DISTRESSLENS_LIVE_PLANE=1`, and is guarded by
  `guard(context, "session.read")` — a signed-out caller gets the forbidden panel,
  and fixture mode returns fixtures. So "registry UI lists agents from the live
  registry" is only true with a working session.
- `/api/assistant/stream` calls `guardRequest({action: "analyst.run_ai_request"})`
  then `consume_ai_quota` and `record_audit_event` RPCs
  (`src/lib/server/ai-budget.ts:62,126`) — a live project with those functions and
  a `profiles` row for the user is required.
- `live-registry-adapter.ts:130-137` throws unless `DISTRESSLENS_SOURCE_SHA` and
  `DISTRESSLENS_GITOPS_SHA` are set and valid; the values file sets neither and
  the CI digest rewrite touches only `repository`/`digest`.

**What already exists:** the migrations for the Phase 2 schema, RLS, function
grant hardening, AI usage/audit (`supabase/migrations/2026080*`), the guard
policy layer, and the whole assistant/registry UI. So the build is: apply the
migrations to a live project, add a sign-in path, seal the runtime config, and
wire provenance — not build the product.

**`NEXT_PUBLIC_*` are inlined at Next.js build time.** Injecting them as runtime
env into a prebuilt standalone image does not configure any browser-side client.
Decide and record which half of the auth flow is server-side (route handler that
signs in and sets the cookie, using runtime env) versus browser-side (needs
build-time values, i.e. a rebuild with build args). The server-side sign-in route
is the cheaper path and keeps the anon key out of the bundle.

**Scope discipline.** One demo/grader account with an analyst-role `profiles`
row is enough. No sign-up flow, no password reset, no account management — none
of that is a rubric row.

## Related Code Files

- Create: a server-side sign-in route/action in `apps/web/src/app/` that
  authenticates against Supabase and sets `sb-access-token` (plus its test)
- Modify: `apps/web/src/lib/server/session.ts` only if the cookie contract needs
  it — prefer leaving the reader untouched
- Modify (gitops): `apps/dev/web/values.yaml` — `DISTRESSLENS_DATA_SOURCE`
  decision, `DISTRESSLENS_SOURCE_SHA` / `DISTRESSLENS_GITOPS_SHA` injection
- Create (gitops): a `web-runtime-config` SealedSecret manifest under
  `platform/` (anon/publishable values only)
- Modify: `.github/workflows/phase2-web.yaml` if provenance SHAs are injected at
  build/digest time rather than in the values file
- Read-only: `supabase/migrations/*`, `src/lib/data/*`, `src/lib/server/*`

## Implementation Steps

1. Apply the existing migrations to the live Supabase project and verify the
   RPCs `consume_ai_quota` and `record_audit_event` and the `profiles` table are
   present with the expected grants.
2. Create one demo/grader account and its `profiles` row with the role the guard
   policy expects for `analyst.run_ai_request` and `session.read`.
3. Implement the server-side sign-in route that exchanges credentials for a
   session and sets `sb-access-token`, with a unit test. Keep it minimal and
   server-side so the anon key stays out of the browser bundle.
4. Decide and record the data-source mode for the deployed pod. If Supabase mode
   is required for the live registry row (it is), set the env accordingly and
   ensure `getDataPort()` resolves without fixture fallback.
5. Seal `web-runtime-config` for the web namespace against the cluster's
   sealed-secrets key — this requires the live cluster, so produce the plaintext
   material here and seal it in the deploy phase alongside the other ciphertexts.
   Do not commit plaintext.
6. Wire `DISTRESSLENS_SOURCE_SHA` / `DISTRESSLENS_GITOPS_SHA` into the pod, in
   the same mechanism that pins the digest, so they cannot drift from the image.
7. Prove it locally before the window: `docker run` the exact built image with
   the runtime env, then verify `/` renders, sign-in sets the cookie,
   `/agents/registry` renders from the live registry path, and
   `POST /api/assistant/stream` completes a generation. Record the outputs.
8. Re-run the repository gates (`pnpm --filter @distresslens/web typecheck`,
   `vitest`, `build`, plus the Phase 1 stage gate) so nothing regresses.

## Success Criteria

- [x] Developer -> runs the built image locally with runtime env -> `/` renders, the sign-in route sets `sb-access-token`, and a signed-in session reports a non-null role.
- [x] Developer -> loads `/agents/registry` in that container -> entries come from the live registry adapter, and removing the registry URL makes it fail closed rather than silently showing fixtures.
- [x] Developer -> posts to `/api/assistant/stream` in that container -> a generation completes, `consume_ai_quota` and `record_audit_event` succeed, and no service-role key is present in the container environment.
- [x] Reviewer -> greps the image and both repos -> the Supabase service-role key appears nowhere; only anon/publishable values are used.
- [x] Maintainer -> inspects the pod spec rendered from `master` -> `web-runtime-config` is produced by a SealedSecret manifest in the repo, and both provenance SHA env vars are set.
- [x] Maintainer -> runs the web typecheck, vitest and build, plus `.venv/bin/python scripts/run_stage1_quality_gates.py` -> all pass.

## Risk Assessment

- **Build-time vs runtime env confusion** → the app looks configured but the
  browser client is not. Mitigation: server-side sign-in route; step 7 proves it
  against the real image, not `pnpm dev`.
- **RLS/guard policy rejects the demo account** → 403 `policy_blocked` in the
  window. Mitigation: step 7's local generation is the gate; the window never
  sees an unproven auth path.
- **Scope creep into product auth** (sign-up, reset, roles UI) → days lost for
  zero rubric points. Mitigation: one account, one sign-in route, nothing else.
- **Service-role key leaking into the image or a values file** → a real secret in
  a public repo. Mitigation: anon-only in the pod; the phase-1 denylist scans
  evidence, and step 7 greps the image environment.
- **This phase overruns and delays the window** → cost pressure. Mitigation: it
  runs with the cluster down, so overrun costs time, not credit; if it cannot be
  finished, fall back to the cut ladder's UI-row entries rather than capturing
  fixture mode as live.
