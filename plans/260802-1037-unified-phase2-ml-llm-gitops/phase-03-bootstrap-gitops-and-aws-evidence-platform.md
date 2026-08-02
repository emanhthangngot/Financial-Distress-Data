---
title: "Phase 3: Bootstrap GitOps and AWS evidence platform"
status: todo
estimate: "8-12 days"
---

# Phase 3: Bootstrap GitOps and AWS evidence platform

## Overview

Create the separate `emanhthangngot/financial-distress-gitops` control repository and a disposable EKS evidence plane. Terraform owns AWS, Helm/Kustomize own Kubernetes desired state, and Argo CD is the only in-cluster deployer after bootstrap.

## Platform Scope

- AWS: EKS in `ap-southeast-1`, managed node groups/Spot where compatible, S3, ECR, RDS PostgreSQL with PGVector, ElastiCache Valkey, Route 53, ACM or cert-manager-compatible DNS, budget alarms, EventBridge Scheduler and CodeBuild teardown.
- Kubernetes: Argo CD, active F5 NGINX Ingress Controller OSS, cert-manager, Istio, KServe 0.18, Knative Serving/Eventing, standalone Kubeflow Pipelines, Kubeflow Trainer, MLflow, Feast services/jobs, Prometheus/Grafana/Pushgateway, ECK/Kibana, OpenTelemetry/Jaeger, Vault-compatible secret management, agentgateway, Envoy Gateway + Envoy AI Gateway, kagent/kmcp/agentregistry/Agent Sandbox.
- Excluded: duplicate cloud Airflow/Kafka/DataHub, multi-region, always-on EKS, and Milvus unless PGVector exceeds the documented scale/latency trigger.

## Repository Ownership

| Path in GitOps repo | Tool | Ownership rule |
|---|---|---|
| `terraform/modules/**`, `terraform/envs/evidence/**` | Terraform | AWS resources only |
| `charts/**` | Helm | first-party apps, MLflow, and charts we own |
| `platform/base/**`, `platform/overlays/**` | Kustomize | selected pinned upstream resources and environment patches |
| `argocd/**` | Argo CD | projects, ApplicationSets, sync waves/policies |
| `ansible/roles/vast-evidence-worker/**` | Ansible | mandatory Vast.ai CPU Locust/benchmark/evidence service; health + idempotency proof |

Maintain `resource-ownership.yaml`; CI rejects any Kubernetes identity rendered by two owners. Do not render KServe/Envoy dependencies from both OCI Helm charts and Kustomize.

## Implementation Steps

1. Seed policy tests for budget, expiry tags, public endpoints, encrypted storage, least privilege, unique resource ownership, automated teardown, retired ingress-nginx rejection, and version/digest pins.
2. Build Terraform modules with remote state locking, environment boundaries, `evidence_session_id`, `expires_at`, owner and cost tags. Plan must fail if projected monthly use exceeds USD 85 minus USD 15 reserve.
3. Provision through a session worker; immediately create an independent EventBridge Scheduler -> CodeBuild destroy job. Default TTL is 6 hours; hard TTL is 8 hours; at most 3 sessions/month.
4. Run a compatibility spike and freeze an exact matrix for EKS/Kubernetes, F5 NGINX OSS (starting candidate controller 5.5.4/chart 2.6.4), cert-manager, Istio, Knative, KServe 0.18, Envoy Gateway/AI Gateway, llm-d/GIE, KFP/Trainer, Argo CD, kagent, kmcp, agentgateway, agentregistry, Agent Sandbox, Feast, and MLflow; require render/install/smoke/upgrade/rollback proof.
5. Bootstrap Argo CD once, then reconcile platform layers through sync waves:
   - `-30`: namespaces, CRDs, external secrets/Vault integration.
   - `-20`: NGINX, cert-manager, Istio, Knative, gateways.
   - `-10`: KServe, KFP/Trainer, observability operators.
   - `0`: MLflow/Feast/platform services.
   - `10`: model, MCP, agent and application workloads.
   - `20`: smoke/evidence jobs.
6. Deploy MLflow by owned Helm chart in `ml-platform`; use RDS backend and S3 artifacts. Promotion resolves the MLflow production alias to an immutable S3 artifact URI and updates KServe GitOps desired state. KServe never reads the registry directly.
7. Use F5 NGINX OSS as TLS-terminating public edge, cert-manager for certificates, Istio authorization/mTLS east-west, agentgateway for MCP/A2A/AI-backend routes, and Envoy AI Gateway for `LLMInferenceService` routing.
8. Provision one vetted Vast.ai CPU host under the aggregate USD 10 cap; apply `vast-evidence-worker` roles to deploy an OpenAI-compatible Locust/benchmark client targeting the llm-d endpoint, verify health, then prove the second Ansible run reports zero changes. Destroy immediately after export; never join it to the GPU model pool.
9. Configure each dev/evidence ApplicationSet with automated sync enabled, prune, self-heal, retry refresh, and `allowEmpty: false`; add GitHub webhook with normal polling fallback.
10. Add `terraform validate/plan`, `helm lint/template`, `kustomize build`, `kubeconform`, `conftest`, `ansible-lint`, Ansible Molecule/idempotency, and duplicate-owner checks.
11. Prove teardown from ready, partially created, failed and expired states; retain only bounded S3/RDS evidence resources.

## CI-to-Argo Contract

1. Source CI tests, builds, scans, signs and pushes an immutable image; it records the registry digest.
2. A bot opens a GitOps PR changing the environment digest. Pushing a tag alone never deploys.
3. Dev PRs auto-merge only after all required checks; main/evidence promotion requires human review.
4. Argo detects the merged Git revision by webhook or polling and reconciles it.
5. Rollback with auto-sync is a Git revert or a new digest commit, never an imperative Argo rollback.

## Validation

- Local/static: Terraform, Helm, Kustomize, schema, policy and IAM tests.
- Ephemeral integration: one full create -> sync -> TLS/mTLS -> smoke -> export -> destroy exercise.
- Failure injection: cancel mid-apply, corrupt chart values, expire lease, lose worker, and verify scheduled teardown.

## Success Criteria

- [ ] Source CI -> pushes a new image without a GitOps PR -> causes no Argo deployment.
- [ ] Approved GitOps PR -> merges an immutable digest -> Argo auto-syncs, self-heals drift and records the revision.
- [ ] Reviewer -> opens approved routes -> reaches only F5 NGINX OSS TLS endpoints with a valid certificate; internal services remain private and mesh-authorized.
- [ ] Platform operator -> applies the Vast.ai role twice -> receives a healthy service, zero changes on the second run, redacted logs and a cost receipt under USD 10.
- [ ] Session worker -> stops after partial provisioning -> independent scheduled teardown destroys the tagged session by hard TTL.
- [ ] Platform admin -> reverts a bad release in Git -> Argo returns to the previous immutable digest without mutable tags.

## Risks and Rollback

- Risk: KServe/LLM stack compatibility changes. Mitigation: pin all chart/manifests and run a compatibility spike before upgrades.
- Rollback: Git revert for Kubernetes state; Terraform state-backed destroy for AWS; retain evidence exports before teardown.
