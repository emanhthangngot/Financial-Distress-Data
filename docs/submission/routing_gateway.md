# Routing & Gateway (NGINX Ingress Controller)

Row: `LLM-AC-13-ROUTING`. F5 NGINX Ingress Controller OSS is the only
externally reachable object; every backend Service is `ClusterIP`.

## Implementation present (static)

The Phase 04 application changes are present in the current working tree:

- `apps/web/Dockerfile` and `apps/web/next.config.ts` provide the standalone
  web image shape.
- `apps/web/src/app/agents/registry/page.tsx` and
  `apps/web/src/lib/data/live-registry-adapter.ts` use the cluster registry
  path and require source/GitOps provenance; they do not silently fall back to
  fixture entries.
- `apps/web/src/app/api/assistant/stream/route.ts` covers the authenticated
  assistant stream, quota/rate-limit responses, coordinator routing, citations
  and tool-status frames.

The sibling `financial-distress-gitops` working tree contains the corresponding
static deployment shape in `charts/web/`, `apps/dev/web/`,
`platform/ingress/f5-nginx-values.yaml`, `platform/ingress/routes-ui.yaml`,
`platform/ingress/routes-viewers.yaml`,
`platform/ingress/duckdns-certificate.yaml`, and
`platform/ingress/basic-auth-sealed-secret.yaml`. Those Phase 04 changes are
uncommitted and have not been shown to Argo CD as a reconciled revision.

## Validation performed

- `npx vitest run --coverage.enabled=false src/app/api/assistant/stream/route.test.ts src/lib/data/live-registry-adapter.test.ts` — **19 passed** across 2 files.
- `npm run typecheck` in `apps/web` — **passed**.
- `.venv/bin/python -m pytest -q tests/phase2/requirements/test_llm_ac_13_routing.py tests/phase2/requirements/test_llm_ac_15_observability.py` — exit 0, **13 skipped** because the rows remain `design_only`; this is not runtime proof.
- `git diff --check` in both working trees — passed with no whitespace errors.

## Deployment and evidence status

The earlier platform record proves the ingress/TLS path with a throwaway test
Service on 2026-08-08. It does not prove the Phase 04 routes. No live check
has been recorded for the Web API HTTPS route, direct-backend refusal,
authenticated viewer routes, 429 burst behavior, or either deployed UI. No
Phase 04 evidence file has been executed, and none of the seven routing rows is
claimed as `executed`; the rubric CSV remains `design_only` for these rows.

## Release blockers before live proof

- The NGINX auth secret must be provisioned through the sealed-secret flow and
  verified with an auth challenge and authorized request. No credential is
  stored in this page.
- The web deployment must receive the Supabase runtime Secret referenced as
  `web-runtime-config`; its presence and runtime behavior are not verified.
- The web image must be built and published by immutable digest, with the
  matching immutable application-source SHA and GitOps SHA recorded in the
  deployment. The current web values still have an empty digest, and both
  checkouts contain uncommitted Phase 04 changes.
- A schedulable GKE cluster with capacity for the web, services, ingress and
  viewers must be available. This session did not verify a live node pool,
  rollout, or Argo sync.

Until those blockers are cleared, the route manifests are implementation
artifacts only and must not be presented as deployed runtime evidence.
