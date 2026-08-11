# Phase 2 report — release inputs and platform preflight

Status: in progress. Steps 4-9 done; steps 1-3 blocked on `gh auth login`
(token was invalid at phase start — user is re-authenticating).

## Step 1: web CI caller (`.github/workflows/phase2-web.yaml`)

Written in full with `secrets:` mapping (`GHCR_TOKEN`, `GITOPS_PAT`), mirroring
the existing agent callers. Decision recorded inline (top-of-file comment):
`phase2-ci.yaml`'s lint/test jobs are Python-only and cannot meaningfully gate
a Next.js app — the real gate is `ci.yml`'s existing `contracts` job
(`pnpm typecheck`, `pnpm test`, Playwright a11y), which already runs on every
push/PR to `main`/`dev`. This caller's own `lint_paths`/`test_selector` point
at the one real Python artifact touching the web deployable
(`tests/phase2/verification/test_web_api_adapters.py`), verified locally:
`pytest tests/phase2/verification -k web_api_adapters` → 4 passed.

**Blocked**: opening the PR to `dev` needs `gh` (or an equivalent GitHub API
credential); `gh auth status` reported an invalid token at phase start.
Pending user re-authentication.

## Step 2-3: digest PR + pull path

Blocked on step 1 (CI must run on `dev` to open the digest PR). Pull-path
decision made ahead of the run: **`imagePullSecrets` on `charts/web`**, not a
public GHCR package — GHCR packages stay private by default even under a
public source repo (confirmed: `Financial-Distress-Data` is
`visibility: public` via the GitHub API, but that does not make its GHCR
packages public), and there is no declarative way to flip that, so a pull
secret is the only GitOps-clean option that needs no manual web-UI step.

Implemented in the GitOps repo:
- `charts/web/templates/deployment.yaml` — `imagePullSecrets` from
  `.Values.imagePullSecrets` (standard Helm pattern, empty list is a no-op).
- `charts/web/values.yaml` — `imagePullSecrets: []` default, documented.
- `apps/dev/web/values.yaml` — `imagePullSecrets: [{name: ghcr-pull-secret}]`.
- `platform/security/ghcr-pull-sealed-secret.yaml` — template-only
  `SealedSecret` (same pattern as `basic-auth-sealed-secret.yaml`): a
  `read:packages`-scoped PAT sealed out of band in phase 4, ciphertext only
  ever committed. Already synced by the existing `platform-security` Argo
  Application — no new Application needed.

## Step 4: rendered-chart capacity budget

Rendered every chart the transitive stack needs with `helm template` (not
hand-summed): `kube-prometheus-stack` 88.2.0, `loki` 7.2.0 (both against
`master`'s values files), plus the three local charts
(`charts/feature-mcp`, `charts/drift-mcp`, `charts/web`) against their
`apps/dev/*/values.yaml`. Manifest-declared pods (agents, agentgateway
model/route CRs, `platform/llm/ab-testing.yaml`'s Knative `Configuration`,
`platform/inference/*.yaml`'s two `InferenceService`s, Jaeger, OTel
collector, Postgres, Redis) summed from their plain YAML. Vendored
controller/CRD manifests (Knative, KServe, sealed-secrets controller,
agentgateway CRDs) excluded — pre-existing platform baseline, not this
window's incremental ask.

| Component | cpu (requests) | memory (requests) |
|---|--:|--:|
| kube-prometheus-stack (operator+grafana+node-exporter+kube-state-metrics+prometheus pod) | 450m | 768Mi |
| loki (caches disabled — see below) | 100m | 256Mi |
| agentgateway controller (estimate — OCI chart `cr.agentgateway.dev/charts`, not locally renderable; typical small-proxy footprint) | ~100m | ~128Mi |
| manifest-declared (model server, embeddings, ab-testing config, postgres, redis, jaeger, otel-collector, 3 agents, agentregistry, sandbox probe) | 5440m | 5024Mi |
| charts (feature-mcp + drift-mcp + web) | 175m | 544Mi |
| **Total** | **~6265m (6.27 vCPU)** | **~6720Mi (6.56 GiB)** |

`e2-standard-8` allocatable (GKE reservation formula, 32GiB node): **~7940m
CPU, ~29023Mi (28.3 GiB) memory**. **Verdict: fits**, ~1.6 vCPU / ~22GiB
headroom even before accounting for the excluded controller overhead
(cert-manager, ingress-nginx controller, ArgoCD, Knative/KServe control
plane) — recommend a `kubectl top nodes` / `describe node` check in phase 4
once the primary pool is up and before syncing the heavy Applications, as a
live sanity check against this estimate rather than trusting it blind.

**Disables applied** (both on `master`, see gitops commit):
- Loki `chunksCache` + `resultsCache` → `enabled: false`. Rendered before:
  100m cpu / **11315Mi**; after: 100m cpu / 256Mi. A single Loki replica with
  no read/write split has no cache tier to serve — this alone was the
  single largest budget item (9.8Gi chunks-cache + 1.2Gi results-cache).
- `alertmanager.enabled: false` already set (pre-existing, not this phase).

Nothing else needed scaling to zero — the reduced total already fits with
large headroom, so KServe/Knative/TEI residents stay up.

## Step 5: quota reconciliation

**New finding beyond the plan's framing** (verified live via `gcloud`, not
assumed): the predecessor plan's `CPUS_ALL_REGIONS = 12` and
`terraform.tfvars`'s regional `CPUS = 32` are **both correct** — they're
different quota dimensions — but neither is the actual binding constraint.
`gcloud compute regions describe asia-southeast1` shows a **per-machine-family**
regional quota, `E2_CPUS = 8`, separate from the general `CPUS = 32`. The
current sizing (`primary-pool` = `e2-standard-8`, 8 vCPU E2 +
`evidence-vm` = `e2-medium`, 2 vCPU E2) needs 10 E2 vCPU against an 8 E2 vCPU
ceiling — the primary pool alone already saturates `E2_CPUS`.

**Governing number for this window: `E2_CPUS = 8`**, not `CPUS_ALL_REGIONS`
or the regional `CPUS`. **User decision (2026-08-11): drop the evidence VM
from this window** — it serves a different, already-executed rubric row
(row 69, IaC/Ansible), not one of the 13 rows this plan closes. `primary-pool`
alone (8 vCPU E2) fits `E2_CPUS = 8` exactly, `CPUS_ALL_REGIONS = 12`
(4 vCPU headroom), and the capacity budget above. `Makefile`'s `gcp-up`
`NO_VM=1` switch (step 6) implements this operationally.

If `secondary-pool` (`e2-standard-4`, also E2 family) is ever needed
alongside `primary-pool`, that's 12 E2 vCPU — over `E2_CPUS = 8` — and would
need a quota increase first; `gcp-up-secondary` exists for when one is
granted, it does not grant one itself. Not needed this window (budget fits
on `primary-pool` alone).

## Step 6: GitOps Makefile targets

- `gcp-up-secondary` (`SECONDARY_NODES` var, default 1) — resizes
  `secondary-pool`. Dry-run: `make -n gcp-up-secondary` → correct
  `gcloud container clusters resize --node-pool secondary-pool --num-nodes 1`.
- `gcp-up`'s `NO_VM=1` switch — skips starting the evidence VM entirely.
  Dry-run: `make -n gcp-up NO_VM=1` → VM-start block skipped, primary-pool
  resize proceeds; `make -n gcp-up NO_VM=0` → VM-start path unchanged
  (verified both branches).
- All existing targets (`gcp-up`, `gcp-down`, `gcp-status`) still parse and
  dry-run cleanly after the edit.

## Step 7: certificate issuance strategy

Committed on `master` (`platform/security/letsencrypt-clusterissuer.yaml`):
both `ClusterIssuer`s now set
`solvers[0].http01.ingress.ingressTemplate.metadata.annotations` to
`nginx.org/mergeable-ingress-type: minion`. This makes cert-manager's
ephemeral HTTP-01 solver Ingress a **minion** under the existing
`gateway-ui-master`, instead of a second master colliding on the same host
(finding 8 — F5 NGINX IC allows one config owner per host).

Verified the auth-inheritance question before committing (cert-manager's
`ingressTemplate` field and the mergeable-minion pattern confirmed via
[cert-manager's HTTP01 docs](https://cert-manager.io/v1.0-docs/configuration/acme/http01/)
and the
[nginx/kubernetes-ingress basic-auth example](https://github.com/nginx/kubernetes-ingress/tree/main/examples/ingress-resources/basic-auth)):
every existing minion in this repo (`routes-ui.yaml`, `routes-viewers.yaml`)
**self-declares** `nginx.org/basic-auth-secret` rather than relying on
inheritance from the master — direct evidence that minion auth is scoped per
Ingress object. A minion that omits the annotation (the solver Ingress) gets
no auth on its own path, so the ACME challenge stays reachable without a
credential while every other route stays protected. Will be confirmed live
in phase 4 (`Certificate` reaches `Ready=True`) before any capture, per the
plan's own gate.

## Step 8: `/loki` route restricted

`platform/ingress/routes-viewers.yaml` no longer routes the bare `/loki`
prefix (which included `POST /loki/api/v1/push` and `.../delete` — a write
path into the evidence log store behind one shared basic-auth credential,
finding 15). Replaced with five explicit read-only Loki HTTP query-API
paths (`/loki/api/v1/query`, `/loki/api/v1/label`, `/loki/api/v1/series`,
`/loki/api/v1/tail`, `/loki/api/v1/index/stats`) — everything else,
including push and delete, 404s at the ingress instead of reaching Loki.
Kept the dedicated route (rather than routing logs only through Grafana)
so the `LLM-routing-gateway-service-coi-log` row's `text_contains:nameloki`
assertion (phase 1) still holds against a real, scoped Loki viewer endpoint.

## Step 9: credential-delivery decision

**User decision (2026-08-11): write the gateway basic-auth credential
directly into `docs/submission/README.md`** — this is a coursework
submission/demo, not a production system with a real user base, so a
password-manager link or a separate out-of-band channel is unneeded
overhead. Phase 1's denylist additions (curl `-u`/`--user`, userinfo-in-URL,
bcrypt htpasswd hash) remain the backstop against the credential leaking
into *evidence* files; the README entry itself is the intended, deliberate
disclosure — added at phase 6 stamp time, not before (so it isn't
invalidated by a later commit).

## Outstanding for this phase

- [ ] Steps 1-3: open+merge the web CI caller PR to `dev`, verify `gitops-pr`
      ran, confirm `apps/dev/web/values.yaml` carries a GHCR repository +
      digest on GitOps `master`. **Blocked on `gh auth login`.**
- [ ] Seal `ghcr-pull-secret` and `gateway-basic-auth` (×2) and
      `grafana-admin-credentials` out of band — deferred to phase 4 (needs
      the cluster's `sealed-secrets` controller public key, which is
      controller-instance-specific).
