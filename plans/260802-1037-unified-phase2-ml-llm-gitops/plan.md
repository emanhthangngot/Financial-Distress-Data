---
title: "Unified Phase 2 ML + LLM GitOps"
description: "Rubric-complete Phase 2 plan combining ML and LLM tracks on an ephemeral AWS EKS evidence plane with a persistent low-cost product plane."
status: pending
priority: P1
effort: "55-79 focused workdays (11-16 weeks)"
branch: main
tags: [coursework, ml, llm, kubernetes, gitops, aws]
blockedBy: []
blocks: []
created: 2026-08-02
---

# Unified Phase 2 ML + LLM GitOps

## Overview

Active phase: **explicit Phase 2 final coursework**. Preserve the verified local Phase 1 lakehouse, add isolated `src/ml/`, `src/drift/`, `src/llm/`, `src/agents/`, and a Next.js product shell, then deploy rubric evidence through a separate GitOps repository. The system targets all 100 ML points and all 100 LLM points without keeping EKS running continuously.

Read before planning: `AGENTS.md`, `docs/spec.md`, `docs/mini_coursework.md`, `docs/coursework.md`, both final-coursework rubric CSVs, the supplied feedback, and the two supplied system-design books. The project-local `financial-distress-sdd` skill is absent; `ak:plan` and `ak:devops` provide the available workflow.

Validation report: [architecture-feedback-260802-1037-phase2-plan.md](../reports/architecture-feedback-260802-1037-phase2-plan.md)

## Goals

| # | Goal | Priority |
|---|------|----------|
| 1 | Score every ML and LLM rubric row with executable proof and a named evidence artifact | P0 |
| 2 | Keep Phase 1 contracts unchanged while publishing versioned features, labels, drift data, and RAG documents | P0 |
| 3 | Use GitOps as the sole EKS deployment path with immutable image digests and reversible Git commits | P0 |
| 4 | Offer a persistent low-cost analyst product while enforcing a bounded, auto-destroyed EKS evidence budget | P1 |

## Phases

| # | Phase | Estimate | Status |
|---|-------|----------|--------|
| 1 | [Lock specification and rubric contract](./phase-01-start.md) | 3-4 days | Pending |
| 2 | [Build product shell, Supabase, RBAC and UX states](./phase-02-build-product-shell-supabase-rbac-and-ux-states.md) | 6-8 days | Pending |
| 3 | [Bootstrap GitOps and AWS evidence platform](./phase-03-bootstrap-gitops-and-aws-evidence-platform.md) | 8-12 days | Pending |
| 4 | [Publish data, Feast stores and RAG corpus](./phase-04-publish-data-feast-stores-and-rag-corpus.md) | 7-10 days | Pending |
| 5 | [Deliver ML track](./phase-05-deliver-ml-track.md) | 8-12 days | Pending |
| 6 | [Deliver LLM, MCP and agent track](./phase-06-deliver-llm-mcp-and-agent-track.md) | 10-15 days | Pending |
| 7 | [Complete CI/CD, security and observability](./phase-07-complete-ci-cd-security-and-observability.md) | 7-10 days | Pending |
| 8 | [Produce evidence, mock-grade and promote](./phase-08-produce-evidence-mock-grade-and-promote.md) | 6-8 days | Pending |

## Fixed Architecture Decisions

- Product plane: Vercel Hobby + Supabase Free; coursework scale is 50 accounts, 10 concurrent web users, and 2 concurrent AI streams.
- Evidence plane: EKS in `ap-southeast-1`, 6-hour default/8-hour hard TTL, at most 3 sessions/month, target <= USD 25/session and <= USD 10/month persistent resources; provisioning blocks if projected spend exceeds USD 85 while reserving USD 15 contingency.
- Public edge is NGINX; Istio is east-west service mesh; agentgateway owns MCP/A2A/agent model routing; Envoy AI Gateway owns KServe `LLMInferenceService` traffic. They are complementary, not merged.
- KServe `LLMInferenceService` remains pinned to the verified 0.18 integration until a compatibility spike proves a later release. Helm owns apps and MLflow; Kustomize owns only selected pinned upstream bases/overlays. One resource has exactly one owner.
- Source repo owns code, tests, schemas, Dockerfiles, and evidence docs. `emanhthangngot/financial-distress-gitops` owns Terraform, Ansible, Helm, Kustomize, Argo CD applications, policies, and environment values.

## Timebox and Cut Policy

- Never cut: rubric gates, >90% test coverage, >80% changed-code mutation score, Locust HTML, autoscaling proof, TLS/domain, KFP + distributed training, MLflow model/data versioning, Feast offline/online jobs, KServe + Knative drift, agents/MCP/registry/sandbox/warm-up, observability, A/B tests, Terraform/Ansible, low-level classes, two novel ideas per track, or evidence mapping.
- Cut first: cosmetic motion, multi-region/HA beyond rubric proof, persistent EKS, Milvus, extra model families, hierarchical agents, and a second cloud copy of Airflow/Kafka/DataHub.
- Cut second: non-rubric product polish and optional Vast.ai benchmark if no bounded offer is available. AWS Spot remains primary; Vast.ai CPU has an aggregate hard cap of USD 10.

## Success Criteria

- [ ] Reviewer -> opens the rubric matrix -> finds one requirement, implementation owner, automated check, and executed artifact for every scored ML and LLM row.
- [ ] Analyst -> uses the product when EKS is off -> sees persisted reports plus an honest evidence-plane state instead of a broken workflow.
- [ ] Platform operator -> provisions or destroys evidence infrastructure -> receives idempotent state transitions, cost preview, audit log, fencing, and guaranteed scheduled teardown.
- [ ] Source CI -> publishes a signed immutable image digest -> opens a checked GitOps PR; only the merged Git change is reconciled by Argo CD.
- [ ] Phase 1 maintainer -> runs existing quality gates -> observes no change to collectors, Gold contracts, DQ semantics, or local evidence behavior.

<!-- slug: unified-phase2-ml-llm-gitops -->
