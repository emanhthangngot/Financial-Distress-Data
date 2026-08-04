---
title: "Unified Phase 2 ML + LLM GitOps"
description: "Rubric-complete Phase 2 plan combining ML and LLM tracks on an ephemeral AWS EKS evidence plane with a persistent low-cost product plane."
status: pending
priority: P1
effort: "57-83 focused workdays (12-17 weeks)"
branch: dev
tags: [coursework, ml, llm, kubernetes, gitops, aws]
blockedBy: []
blocks: []
created: 2026-08-02
---

# Unified Phase 2 ML + LLM GitOps

## Overview

Active phase: **explicit Phase 2 final coursework**. Preserve the verified local Phase 1 lakehouse, keep application work in one source monorepo (`src/ml/`, `src/drift/`, `src/llm/`, `src/agents/`, `apps/`, and thin `dags/phase2/` wrappers), then deploy rubric evidence through a separate least-privilege GitOps control repository. The system targets all 57 ML rows/100 points and all 60 LLM rows/100 points without keeping EKS running continuously.

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
| 1 | [Lock specification and rubric contract](./phase-01-start.md) | 3-4 days | In Review |
| 2 | [Build product shell, Supabase, RBAC and UX states](./phase-02-build-product-shell-supabase-rbac-and-ux-states.md) | 8-12 days | Pending |
| 3 | [Bootstrap GitOps and AWS evidence platform](./phase-03-bootstrap-gitops-and-aws-evidence-platform.md) | 8-12 days | Pending |
| 4 | [Publish data, Feast stores and RAG corpus](./phase-04-publish-data-feast-stores-and-rag-corpus.md) | 7-10 days | Pending |
| 5 | [Deliver ML track](./phase-05-deliver-ml-track.md) | 8-12 days | Pending |
| 6 | [Deliver LLM, MCP and agent track](./phase-06-deliver-llm-mcp-and-agent-track.md) | 10-15 days | Pending |
| 7 | [Complete CI/CD, security and observability](./phase-07-complete-ci-cd-security-and-observability.md) | 7-10 days | Pending |
| 8 | [Produce evidence, mock-grade and promote](./phase-08-produce-evidence-mock-grade-and-promote.md) | 6-8 days | Pending |

## Fixed Architecture Decisions

- Product plane: Vercel Hobby + Supabase Free; coursework scale is 50 accounts, 10 concurrent web users, and 2 concurrent AI streams. The product UI is an explicit contract in `docs/phase2/product.md`, with approved references `UI-APPROVED-01..03`; it is not satisfied by a generic shell or a screenshot-only mock.
- Evidence plane: EKS in `ap-southeast-1`, 6-hour default/8-hour hard TTL, at most 3 sessions/month, target <= USD 25/session and <= USD 10/month persistent resources; provisioning blocks if projected spend exceeds USD 85 while reserving USD 15 contingency.
- Public edge is active F5 NGINX Ingress Controller OSS (`nginx/kubernetes-ingress`), never retired community ingress-nginx. Istio is east-west service mesh. The LLM chain is kagent `Agent` -> kagent `ModelConfig` -> agentgateway AI backend -> Envoy AI Gateway -> KServe `LLMInferenceService`/llm-d; MCP and A2A also use agentgateway routes.
- KServe `LLMInferenceService` remains pinned to the verified 0.18 integration until a compatibility spike proves a later release. Helm owns apps and MLflow; Kustomize owns only selected pinned upstream bases/overlays. One resource has exactly one owner.
- The single source monorepo owns code, tests, schemas, Dockerfiles, Airflow Phase 2 wrappers, and evidence docs. `emanhthangngot/financial-distress-gitops` is a separate control repo owning Terraform, Ansible, Helm, Kustomize, Argo CD applications, policies, and environment values; this is not a microservice-per-repo design.
- The scheduled drift contract is Airflow -> Feast offline store -> reference/proxy comparison -> Evidently -> Pushgateway/Grafana -> threshold -> actual Kubeflow Pipelines API run, with both skip and trigger evidence.
- Ansible evidence is mandatory: a role-based playbook deploys a healthy/idempotent Vast.ai CPU OpenAI-compatible load client against the llm-d endpoint under a USD 10 aggregate hard cap; it never joins the AWS GPU inference pool.

## Timebox and Cut Policy

- Never cut: rubric gates, >90% test coverage, >80% changed-code mutation score, Locust HTML, autoscaling proof, TLS/domain, KFP + distributed training, MLflow model/data versioning, Feast offline/online jobs, KServe + Knative drift, agents/MCP/registry/sandbox/warm-up, observability, A/B tests, Terraform/Ansible, low-level classes, two novel ideas per track, evidence mapping, the three approved UI references, deterministic route-state screenshots, accessibility checks, and truthful EKS-off/cached states.
- Cut first: cosmetic motion, multi-region/HA beyond rubric proof, persistent EKS, Milvus, extra model families, hierarchical agents, and a second cloud copy of Airflow/Kafka/DataHub.
- Cut second: non-rubric product polish and extra Vast.ai workloads beyond the one mandatory Ansible evidence worker. AWS Spot remains primary for inference; Vast.ai CPU has an aggregate hard cap of USD 10.

## Success Criteria

- [ ] Reviewer -> opens the rubric matrix -> finds canonical source digest, acceptance ID, owner, implementation repo/file, contract test, behavior-validation command, and executed artifact for each of 117 scored rows.
- [ ] Analyst -> uses the product when EKS is off -> sees persisted reports plus an honest evidence-plane state instead of a broken workflow.
- [ ] Platform operator -> provisions or destroys evidence infrastructure -> receives idempotent state transitions, cost preview, audit log, fencing, and guaranteed scheduled teardown.
- [ ] Source CI -> publishes a signed immutable image digest -> opens a checked GitOps PR; only the merged Git change is reconciled by Argo CD.
- [ ] Phase 1 maintainer -> runs existing quality gates -> observes no change to collectors, Gold contracts, DQ semantics, or local evidence behavior.
- [ ] ML operator -> executes both drift branches -> observes Pushgateway/Grafana metrics, a persisted skip below threshold, and a real KFP API run ID above threshold.
- [ ] Platform operator -> runs the Vast.ai Ansible playbook twice -> observes a healthy useful service and an idempotent second run within the USD 10 cap.
- [ ] Product reviewer -> opens `UI-APPROVED-01`, `UI-APPROVED-02` and `UI-APPROVED-03` -> matches the approved information hierarchy at desktop/tablet/mobile viewports and finds provenance, disclaimer, RBAC and degraded-state proof.

## Validation Log

### Session 1 — 2026-08-02

**Trigger:** `/ak:plan validate` on `phase-01-start.md` before implementation.

**Questions asked:** 7

#### Questions & Answers

1. **[Architecture]** Semantic ID scheme cho ~200 scored row (ML + LLM)?
   - Options: Slug từ requirement | Số theo track | Hybrid số + slug
   - **Answer:** Slug từ requirement
   - **Rationale:** Bền vững với thay đổi CSV, đọc được ngay mà không cần bảng tra cứu số dòng.

2. **[Architecture]** 10 class contracts (5 ML + 5 LLM) hiện diện như thế nào trong phase-01?
   - Options: Python stub + doc | Chỉ documentation
   - **Answer:** Python stub + doc
   - **Rationale:** Test seed cần đối tượng assert; stub chỉ chứa signature + docstring nên không vi phạm ranh giới "chưa implement".

3. **[Assumptions]** Trường `owner` trong rubric matrix dùng loại gì?
   - Options: Role-based | Person-based | Role + người phụ trách
   - **Answer:** Role-based
   - **Rationale:** Repo cá nhân, role (`ml_engineer`, `llm_engineer`, `data_engineer`, `platform_operator`) không lệ thuộc thành viên.

4. **[Scope]** Phạm vi acceptance criteria WHO -> ACTION -> RESULT trong phase-01?
   - Options: Per deliverable + class | Per scored row (200 AC) | Chỉ success criteria
   - **Answer:** Per deliverable + class
   - **Rationale:** ~20-30 AC đủ để linter và reviewer dùng, tránh boilerplate 200 dòng vô nghĩa.

5. **[Assumptions]** Chiến lược branch khi triển khai phase-01?
   - Options: Feature branch + PR | Commit trực tiếp lên dev
   - **Answer:** Feature branch + PR
   - **Rationale:** Khớp convention repo (`codex/*`, `feature/*`).

6. **[Scope]** Nội dung `docs/coursework.md` cũ xử lý thế nào khi rewrite?
   - Options: Thay thế hoàn toàn | Lưu archive riêng
   - **Answer:** Thay thế hoàn toàn
   - **Rationale:** Git history vẫn giữ bản cũ; không cần archive bản stale trong repo.

7. **[Assumptions]** `--matrix-only --strict` yêu cầu cột evidence_path thế nào để phase-01 PASS?
   - Options: Path đã hoạch định | Cho phép trống
   - **Answer:** Path đã hoạch định
   - **Rationale:** Mỗi row khai evidence_path là đường dẫn sẽ tạo (`docs/phase2/evidence/...`); linter verify parent dir thuộc `docs/phase2/evidence/` chứ không yêu cầu file tồn tại. Check `--require-executed` chỉ bật ở phase-08.

#### Confirmed Decisions
- Semantic ID: slug từ requirement text.
- Class contracts: Python stub (`src/ml/contracts.py`, `src/llm/contracts.py`) + `docs/phase2/low-level-design.md`.
- Owner: role-based.
- AC scope: per deliverable + per class (~20-30 AC).
- Branch: feature branch `codex/phase2-spec-lock` + PR.
- Old `docs/coursework.md`: replace hoàn toàn.
- Evidence path: planned path under `docs/phase2/evidence/`; strict `--require-executed` deferred to phase-08.

#### Action Items
- [x] Phase-01: semantic slug ID cho mọi scored row.
- [x] Phase-01: stub `src/ml/contracts.py`, `src/llm/contracts.py` + low-level design doc.
- [x] Phase-01: role-based owner trong rubric matrix.
- [x] Phase-01: AC per deliverable + per class.
- [ ] Phase-01: branch `codex/phase2-spec-lock`, mở PR sau khi PASS.
- [x] Phase-01: `docs/coursework.md` thay thế hoàn toàn.
- [x] Phase-01: linter `--matrix-only --strict` verify planned evidence path; `--require-executed` để dành phase-08.

#### Impact on Phases
- Phase 1 (phase-01): toàn bộ action items trên.
- Phase 8 (phase-08): `--require-executed` chỉ kích hoạt khi evidence đã chạy; không đổi contract matrix.

### Whole-Plan Consistency Sweep

The 2026-08-02 AK re-audit supersedes the earlier clean-sweep claim. It found
and closed these design-level gaps: mandatory role-based Ansible execution,
actual KFP API retraining after Airflow drift detection, correct kagent
`ModelConfig` ownership, active F5 NGINX OSS instead of retired ingress-nginx,
source-row/digest completeness, resolvable acceptance IDs, real repo/file
artifact ownership, exact 40-hex evidence SHAs, Phase 2 DAG isolation, and a
credential-free S3 evidence return path. Phase 8 still requires real runtime
evidence before any 100/100 claim is valid.

<!-- slug: unified-phase2-ml-llm-gitops -->
