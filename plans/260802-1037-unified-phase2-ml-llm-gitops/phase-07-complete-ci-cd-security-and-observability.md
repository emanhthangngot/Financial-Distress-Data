---
title: "Phase 7: Complete CI/CD, security and observability"
status: todo
estimate: "7-10 days"
---

# Phase 7: Complete CI/CD, security and observability

## Overview

Turn all rubric deployables into reproducible, signed releases; close TLS, secret, mesh, telemetry, autoscaling and cross-repository GitOps gaps; provide one evidence-ready operational story.

## Required Pipelines

- Existing Phase 1 DP1, DP2 and DP3.
- Structured materialization pipeline, Kubeflow training pipeline and RAG data pipeline.
- Offline and online stream-feature jobs.
- Feature API, drift API + Knative/KServe, ML inference service.
- Custom LLM inference service, both MCP servers, two specialist agents and coordinator.
- Product web app and evidence-session worker.

## CI/CD Contract

1. Pull request: lint, types, unit/integration tests, >90% coverage, changed-code mutation >80%, equivalence/boundary/property checks, secrets/SAST/dependency scan, SBOM and IaC/render/policy validation.
2. Merge to source `dev` or `main`: build once, sign with keyless provenance where possible, push immutable tag and capture digest.
3. Bot opens a GitOps digest PR with source SHA, image digest, model/agent/data version and evidence manifest link.
4. GitOps `dev` PR auto-merges after all required checks; `main/evidence` requires review and protected environment approval.
5. Argo automated sync (`enabled`, `prune`, `selfHeal`, `retry.refresh`, `allowEmpty: false`) reconciles only merged Git; webhook accelerates normal polling.
6. Verification job records rollout, health, routing and evidence. Failure creates a Git revert/new-digest PR; no mutable tags, direct cluster deploy or imperative rollback.

## Security Work

- Centralize runtime secrets with Vault or an equivalent operator; CI uses OIDC and short-lived credentials; no secret is committed or copied into evidence.
- NGINX basic authentication/rate limit where the rubric requires it, plus product auth for user-facing UIs; valid HTTPS domain and cert-manager evidence.
- Istio strict mTLS and least-privilege authorization between edge, APIs, model servers, MCP tools, agents and stores.
- Supabase RLS/AAL2 roles from Phase 2; Kubernetes service accounts and namespaces enforce the same responsibility split.
- NetworkPolicy, pod security standards, non-root/read-only containers, image signature admission, egress allow-list and audit retention.
- Threat model prompts, retrieved documents, tool arguments, model artifacts, GitOps PRs and session-worker actions.

## Observability Work

- OpenTelemetry correlation IDs across NGINX, Istio, APIs, KServe, gateways, MCP tools, agents, Airflow/KFP and session worker.
- Prometheus/Grafana: request rate, failures, latency, replicas, CPU/RAM/disk/network, feature/drift metrics, retraining calls, A/B comparisons and budget/session state.
- ECK/Kibana: structured logs with prompt/document/PII redaction and release/session fields.
- Jaeger: end-to-end traces for feature, drift, RAG, agent and promotion flows.
- LLM: input/output/total tokens, round-trip, TTFT and PII safety frequency.
- Agents: calls per agent, calls per MCP tool and failures per tool invocation.

## Validation

- Rebuild each artifact from a clean runner and compare digest/provenance.
- Exercise dev auto-merge, main approval, webhook-disabled polling fallback, failed sync, self-heal, prune guard and Git rollback.
- TLS scan, rate-limit/auth proof, Vault lease rotation, mTLS positive/negative calls, signed/unsigned image admission.
- Query dashboards/logs/traces using a shared correlation ID for every required flow.
- Run Terraform, Ansible, Helm, Kustomize and Argo validation in CI.

## Success Criteria

- [ ] Developer -> merges source code -> obtains one signed immutable artifact and one checked GitOps PR; no CI principal writes directly to EKS.
- [ ] Dev GitOps PR -> passes required checks -> auto-merges and reconciles; main GitOps PR -> waits for a human approval.
- [ ] Unauthorized workload -> calls a protected service -> is denied by mesh policy; an authorized workload succeeds over mTLS.
- [ ] Reviewer -> follows one correlation ID -> finds metric, redacted log and trace across the full request path.
- [ ] Operator -> reverts a release commit -> observes Argo reconcile the prior digest and retain an auditable history.
- [ ] Security scanner -> inspects repo and evidence -> finds no secret, token, private prompt or personal data.

## Risks and Rollback

- Risk: over-instrumentation consumes the small cluster. Mitigation: bounded retention, sampling, resource quotas and evidence-window profiles.
- Rollback: observability and policy changes are versioned GitOps commits; emergency rollback still uses a reviewed Git revert.
