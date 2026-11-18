---
title: "Phase 7: Complete CI/CD, security and observability"
status: todo
estimate: "0.5 day (day 5)"
---

# Phase 7: Complete CI/CD, security and observability

## Overview

Turn every LLM-track deployable into a reproducible, signed release; close TLS,
secret, telemetry, autoscaling and cross-repository GitOps gaps; provide one
evidence-ready operational story.

Most of the work lands inside phases 4 and 6, where each pipeline is built with
its workflow. This phase is the close-out pass: the cross-cutting security and
observability rows, and the repository-design row.

## Required Pipelines

- Existing platform .P1, DP2 and DP3 (unchanged).
- RAG data pipeline; stream-feature job to the offline store; stream-feature job
  to the online store.
- Web API kéo dữ liệu and the real-time drift API, each deployed as an MCP tool.
- The model server, both MCP servers, the two specialist agents and the
  coordinator.
- Product web app.

Kubeflow training pipelines, the structured materialization pipeline for
training, and the ML inference service belong to the deferred phase-05 retrofit.

## CI/CD Contract

1. Pull request: lint, types, unit/integration tests, coverage, mutation testing
   on its declared module subset, equivalence/boundary/property checks,
   secrets/SAST/dependency scan, SBOM and IaC/render/policy validation. The
   former ">90% coverage, >80% mutation" thresholds are retired — see the plan
   index's cut policy.
2. Merge to source `dev` or `main`: build once, sign with keyless provenance where possible, push immutable tag and capture digest.
3. Bot opens a GitOps digest PR with source SHA, image digest, model/agent/data version and evidence manifest link.
4. GitOps `dev` PR auto-merges after all required checks; `main/evidence` requires review and protected environment approval.
5. Argo automated sync (`enabled`, `prune`, `selfHeal`, `retry.refresh`, `allowEmpty: false`) reconciles only merged Git; webhook accelerates normal polling.
6. Verification job records rollout, health, routing and evidence into an immutable bundle on in-cluster MinIO (no cloud object-storage credential needed). A source-side CI/bot verifies the bundle and opens the evidence PR; the cluster has no source-repository write credential. Failure creates a Git revert/new-digest PR; no mutable tags, direct cluster deploy or imperative rollback.

## Security Work

- Centralize runtime secrets with GitHub Actions secrets plus OIDC short-lived
  credentials for CI, and sealed-secrets in-cluster. No secret is committed or
  copied into evidence. Vault is out of scope — see the plan index.
- F5 NGINX OSS basic authentication and rate limit where the rubric requires it,
  plus product authentication on the agent chat UI (its own scored row); valid
  HTTPS and cert-manager evidence.
- Backends are `ClusterIP` only behind a default-deny NetworkPolicy, with the
  ingress as the sole externally reachable object. Prove it with a negative curl
  direct to a backend and a successful curl through the route. Istio is out of
  scope — no LLM rubric row mentions mesh, mTLS or TLS.
- Agents run in the `agents-sandbox` restricted-PSS namespace with a tokenless
  ServiceAccount and an egress allow-list (phase-06).
- Supabase RLS/AAL2 roles from Phase 2; Kubernetes service accounts and namespaces enforce the same responsibility split.
- NetworkPolicy, pod security standards, non-root/read-only containers, image signature admission, egress allow-list and audit retention.
- Threat model prompts, retrieved documents, tool arguments, model artifacts, GitOps PRs and session-worker actions.

## Observability Work

- OpenTelemetry correlation IDs across F5 NGINX OSS, the APIs, the model server, agentgateway, MCP tools, agents and Airflow.
- Prometheus/Grafana: request rate, failures, latency, replicas, CPU/RAM/disk/network, drift metrics, A/B comparisons and session state.
- Loki with Grafana Explore: structured logs with prompt/document/PII redaction and release/session fields. Reachable through the gateway — that is a scored row, so installation alone does not satisfy it.
- Jaeger: end-to-end traces for feature, drift, RAG, agent and promotion flows.
- LLM: input/output/total tokens, round-trip, TTFT and PII safety frequency.
- Agents: calls per agent, calls per MCP tool and failures per tool invocation.

## Validation

- Rebuild each artifact from a clean runner and compare digest/provenance.
- Exercise dev auto-merge, main approval, webhook-disabled polling fallback, failed sync, self-heal, prune guard and Git rollback.
- TLS scan, rate-limit and auth proof, sealed-secret rotation, direct-to-backend negative call, signed/unsigned image admission.
- Query dashboards, logs and traces using a shared correlation ID for every required flow.
- Run `terraform validate`, `ansible-lint` plus a second-run idempotency check, `helm lint/template`, `kubeconform`, Argo render and retired-controller rejection validation in CI. Kustomize and Molecule are out of scope.

## Success Criteria

- [ ] Developer -> merges source code -> obtains one signed immutable artifact and one checked GitOps PR; no CI principal writes directly to the cluster.
- [ ] Dev GitOps PR -> passes required checks -> auto-merges and reconciles; main GitOps PR -> waits for a human approval.
- [ ] Reviewer -> calls a backend Service directly from outside the cluster -> is refused; calls the same route through the ingress -> receives 200 over HTTPS.
- [ ] Reviewer -> follows one correlation ID -> finds metric, redacted log and trace across the full request path.
- [ ] Operator -> reverts a release commit -> observes Argo reconcile the prior digest and retain an auditable history.
- [ ] Security scanner -> inspects repo and evidence -> finds no secret, token, private prompt or personal data.

## Risks and Rollback

- Risk: over-instrumentation consumes the small cluster. Mitigation: bounded retention, sampling, resource quotas and evidence-window profiles.
- Rollback: observability and policy changes are versioned GitOps commits; emergency rollback still uses a reviewed Git revert.
