---
phase: 2
title: "Release inputs and platform preflight"
status: pending
priority: P1
effort: "0.75d (no cluster)"
dependencies: [1]
---

# Phase 2: Release inputs and platform preflight

# 0 points

## Overview

Settle every decision and produce every artifact the paid cluster window depends
on: a real web image digest reachable from the cluster, a certificate-issuance
strategy that can actually succeed, a capacity budget derived from rendered
charts rather than hand-summed values, Makefile targets for the capacity and
hibernation moves the plan relies on, and the removal of a route that publishes a
write-capable API.

## Requirements

- Functional: the web image built, signed and digest-pinned into
  `apps/dev/web/values.yaml` on `master`; the image pullable by the cluster
  without an imperative patch; an issuance strategy committed that does not
  collide with the mergeable-Ingress master; a rendered-chart capacity budget
  covering the full transitive stack; `gcp-up`/`gcp-down` able to express
  "secondary pool at 1, VM stopped"; the `/loki` route decision applied.
- Non-functional: everything reaches the cluster through GitOps on `master`.
  No rubric row is claimed.

## Architecture

**CI cannot open a digest PR from a feature branch.** `phase2-ci.yaml`'s
`gitops-pr` job is gated
`if: (push || workflow_dispatch) && (ref_name == 'main' || ref_name == 'dev')`
(`.github/workflows/phase2-ci.yaml:161`), and every caller triggers only on
`main`/`dev`. So the web caller must be merged to `dev` and run there — pushing
`codex/phase06-llm-submission` produces nothing.

**The caller must be written out in full**, not sketched. The reusable workflow
declares `GHCR_TOKEN` and `GITOPS_PAT` as `required: true` under
`workflow_call`, so a caller without a `secrets:` mapping fails validation. Its
lint/test jobs run `ruff`/`black`/`pytest` only — measured: `ruff check apps/web`
and `black --check apps/web` exit 0 with no Python files, so a naive selector
produces a green gate that tests nothing about a Next.js app, and an *empty*
selector lints the whole repo and runs the entire pytest suite including
`postgres`-marked tests. Decide explicitly: either add a Node lint/test branch,
or state that the web deployable's real gate is a local
`pnpm build` + `vitest` + a container smoke run, and record that decision.

**Image pull.** `charts/web/templates/deployment.yaml` has no `imagePullSecrets`
and no `serviceAccountName`, and `charts/web/values.yaml` has no such key — there
is no declarative way to attach a pull secret. The only GitOps-clean options are
a public GHCR package or adding pull-secret support to the chart. Patching the
namespace ServiceAccount imperatively is excluded: the deploy phase forbids
imperative changes on the rubric-bearing path.

**Certificate issuance.** `letsencrypt-prod` uses an `http01.ingress` solver, so
cert-manager creates a standalone Ingress for `distresslens.duckdns.org`. That
host is already owned by `gateway-ui-master`
(`nginx.org/mergeable-ingress-type: master`) with `ssl-redirect: "true"` and a
host-wide `nginx.org/basic-auth-secret` (`platform/ingress/routes-ui.yaml:6-13`).
F5 NGINX IC allows one configuration owner per host, so the solver Ingress is
rejected and the ACME challenge 404s — and even if routed, it would be redirected
or 401'd before Let's Encrypt could read it. Switching to the staging issuer
changes nothing about the conflict. Pick one **before** the window: a
`/.well-known/acme-challenge/` minion with auth disabled and redirect exempted, a
DNS-01 solver, or a certificate pre-issued before the master Ingress exists.

**Capacity budget, done properly.** Hand-summing `resources.requests` from
`platform/observability/*.yaml` misses everything the charts add by default —
Loki 7.x ships `chunksCache`/`resultsCache` memcached StatefulSets with multi-GB
memory requests (the values file disables only `gateway` and `minio`), and
kube-prometheus-stack adds kube-state-metrics and node-exporter. It also misses
the transitive set the token/tool-call metrics actually need: the `phase2-data`
plane (Feast + Redis + Postgres for feature-mcp), the agentgateway, and
`platform/llm/ab-testing.yaml`'s two llama.cpp servers plus the weights loader.
Derive the budget from `helm template` of each chart+values pair, summing
rendered requests across all rendered pods, and add the manifest-declared pods.
Then decide what to disable (`chunksCache`, `resultsCache`) and what existing
resident to scale to zero (Knative/KServe/TEI) to make room.

**Quota number must be reconciled.** The predecessor plan asserts
`CPUS_ALL_REGIONS = 12`; `terraform/gcp/terraform.tfvars:5-6` records a measured
regional `CPUS = 32`. Establish which governs before sizing on it, because the
"secondary pool at 1 node = exactly at cap" reasoning depends on it.

**Makefile gaps.** `gcp-up` unconditionally *starts* the evidence VM and resizes
`primary-pool` only; `POOLS := primary-pool secondary-pool` is used solely by
`gcp-down`. So the plan's capacity remedy ("raise the secondary pool") has no
target, and any `gcp-up` used as a mid-window reset silently restarts the VM and
leaves the secondary pool at 0 — evicting the whole observability stack while
printing success. Add `SECONDARY_NODES`/`gcp-up-secondary` and a `NO_VM=1`
switch now, while the cluster is free.

**`/loki` is not a viewer.** `loki-otel-values.yaml:4` sets `auth_enabled: false`
and `:43-44` disables the Loki gateway, and `routes-viewers.yaml:29-36` exposes
the whole `/loki` prefix — including `POST /loki/api/v1/push` and
`.../delete` — behind one shared basic-auth credential. That is a write path into
the store backing the logs evidence. Grafana already proxies Loki as a datasource
(`prometheus-values.yaml:29-32`), so drop the route and capture the logs row
through Grafana Explore, or restrict it to exact read paths.

**Credential delivery.** One htpasswd guards all five routes, so whatever reaches
a grader is full access to Grafana, Loki, Jaeger and the feature API. Decide the
out-of-band delivery channel now (course submission field / password manager
link) and record only the *fact* of delivery in the repo. Phase 1's denylist
additions are the backstop, not the plan.

## Related Code Files

- Create: `.github/workflows/phase2-web.yaml` (full caller, `secrets:` included)
- Modify (via CI digest PR on `master`): gitops `apps/dev/web/values.yaml`
- Modify (gitops): `Makefile` (secondary-pool target, `NO_VM` switch)
- Modify (gitops): `platform/security/letsencrypt-clusterissuer.yaml` and/or
  `platform/ingress/routes-ui.yaml` / `duckdns-certificate.yaml` (issuance strategy)
- Modify (gitops): `platform/ingress/routes-viewers.yaml` (`/loki` route decision)
- Modify (gitops): `platform/observability/loki-otel-values.yaml` (cache disables, if the budget requires)
- Modify (gitops): `charts/web/*` only if the pull-secret option is chosen
- Create: this plan's `reports/` — rendered-chart capacity budget, quota reconciliation, issuance decision, credential-delivery decision

## Implementation Steps

1. Write `.github/workflows/phase2-web.yaml` in full, with `secrets:` and
   explicit lint/test selectors, and record the decision about what actually
   gates the web image. Open a PR to `dev` and merge it — the digest PR cannot
   be produced from a feature branch.
2. Verify the `gitops-pr` job **ran** (not skipped), merge the digest PR into
   GitOps `master`, and confirm `apps/dev/web/values.yaml` carries a GHCR
   repository and a real `sha256:` digest.
3. Settle the pull path: make the GHCR package public and verify with an
   unauthenticated `docker pull` of the exact digest, or add `imagePullSecrets`
   to `charts/web` in the same GitOps PR. Record which.
4. Render the capacity budget with `helm template` for kube-prometheus-stack,
   Loki, and each app chart with its `apps/dev/*` values, sum the rendered
   requests, add the manifest-declared pods (Jaeger, OTel, agents, agentgateway,
   model servers, data plane), and compare against the node's allocatable.
   Produce an explicit verdict plus the list of things to disable or scale to
   zero.
5. Reconcile the vCPU quota number against the project's actual quota, and state
   which figure the window plan uses.
6. Add the GitOps Makefile targets for secondary-pool scaling and VM-less
   bring-up; dry-run them with `--help`/`-n` so their behavior is known before
   the window.
7. Commit the issuance strategy to `master` (acme-challenge minion, DNS-01, or
   pre-issued certificate) and state how it will be verified in the deploy phase.
8. Apply the `/loki` route decision and the Loki cache disables on `master`.
9. Record the credential-delivery channel decision.

## Success Criteria

- [ ] Release owner -> checks the CI run on `dev` -> the `gitops-pr` job ran and opened a digest PR against GitOps `master`.
- [ ] Release owner -> opens gitops `apps/dev/web/values.yaml` on `master` -> GHCR repository and a non-empty `sha256:` digest.
- [ ] Release owner -> runs an unauthenticated `docker pull` of that digest (or renders the chart showing `imagePullSecrets`) -> the cluster's pull path is proven, not assumed.
- [ ] Release owner -> reads the capacity budget -> it is derived from `helm template` output, covers the data plane, agentgateway and model servers, and ends in a fits/does-not-fit verdict with named disables.
- [ ] Operator -> reads the quota reconciliation -> one governing number, cited from the project's actual quota.
- [ ] Operator -> inspects the GitOps Makefile -> a target exists that raises the secondary pool and one that brings the cluster up without starting the evidence VM.
- [ ] Operator -> reads the issuance decision on `master` -> a strategy that does not require a second Ingress owner for the master's host.
- [ ] Reviewer -> checks `routes-viewers.yaml` on `master` -> no unauthenticated-write Loki API is published as a "viewer".
- [ ] Cost owner -> runs `make gcp-status` -> cluster still at zero nodes.

## Risk Assessment

- **The web CI gate is decorative** (Python matrix over a Next.js app) → config
  errors surface first inside the paid window. Mitigation: step 1's explicit
  decision plus a local container smoke run in the next phase.
- **Public GHCR package** exposes the image publicly. Acceptable for a
  coursework image with no secrets baked in; verify the image contains no
  `.env`, no Supabase service-role key, before publishing.
- **Issuance strategy still fails in-window** → all 7 gateway rows die.
  Mitigation: prefer DNS-01 (no Ingress ownership conflict at all) if the DuckDNS
  token can be sealed; otherwise the acme minion must be reconciled and reviewed
  on `master` before the window.
- **Budget still wrong** → pods `Pending` at hour four. Mitigation: rendered
  requests, not hand sums; and a named list of what to scale to zero.
- Rollback: every change is a GitOps commit on `master` or a source workflow
  file; revert and re-sync.
