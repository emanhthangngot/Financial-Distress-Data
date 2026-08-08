---
title: "Unified Phase 2 ML + LLM GitOps"
description: "Phase 2 final coursework, LLM track only, delivered on a Terraform-provisioned GKE evidence cluster paid from GCP free-trial credit, with a persistent low-cost product plane. The ML track is deferred to a post-deadline retrofit."
status: pending
priority: P1
effort: "7 days to submission (LLM track); ML retrofit a further 4-5 days"
branch: dev
tags: [coursework, ml, llm, kubernetes, gitops, gcp]
blockedBy: []
blocks: []
created: 2026-08-02
---

# Unified Phase 2 ML + LLM GitOps

## Overview

Active phase: **explicit Phase 2 final coursework**. Preserve the verified local Phase 1 lakehouse, keep application work in one source monorepo (`src/ml/`, `src/drift/`, `src/llm/`, `src/agents/`, `apps/`, and thin `dags/phase2/` wrappers), then deploy rubric evidence through a separate least-privilege GitOps control repository.

**Scope revision — 2026-08-07.** The coursework accepts one of the two tracks. With 7 days to the deadline and zero executed evidence, this plan delivers the **LLM track only: 60 rows / 100 points**. The 57 ML rows stay in `docs/phase2/rubric-matrix.csv` unchanged and phase-05 stays in place as the retrofit backlog — the phase-08 auditor's canonical-coverage check requires all 117 rows present regardless of which track is submitted, and freezing the ML rows is what keeps the retrofit additive rather than rework. Track selection is enforced by a new `--track` filter on `scripts/audit_phase2_evidence.py`, not by deleting rows. Rationale and the retrofit contract: `phase-05-deliver-ml-track.md`.

Read before planning: `AGENTS.md`, `docs/spec.md`, `docs/mini_coursework.md`, `docs/coursework.md`, both final-coursework rubric CSVs, the supplied feedback, and the two supplied system-design books. The project-local `financial-distress-sdd` skill is absent; `ak:plan` and `ak:devops` provide the available workflow.

Validation report: [architecture-feedback-260802-1037-phase2-plan.md](../reports/architecture-feedback-260802-1037-phase2-plan.md)

## Goals

| # | Goal | Priority |
|---|------|----------|
| 1 | Score every LLM rubric row with executable proof and a named evidence artifact | P0 |
| 2 | Keep Phase 1 contracts unchanged while publishing versioned features, labels, drift data, and RAG documents | P0 |
| 3 | Use GitOps as the sole cluster deployment path with immutable image digests and reversible Git commits | P0 |
| 4 | Leave the deferred ML track a purely additive 4-5 day retrofit | P1 |
| 5 | Offer a persistent low-cost analyst product within a bounded, auto-destroyed cloud evidence budget | P1 |

## Phases

| # | Phase | Estimate | Day | Status |
|---|-------|----------|-----|--------|
| 1 | [Lock specification and rubric contract](./phase-01-start.md) | 3-4 days | — | In Review |
| 2 | [Build product shell, Supabase, RBAC and UX states](./phase-02-build-product-shell-supabase-rbac-and-ux-states.md) | 8-12 days | — | Done |
| 3 | [Bootstrap GKE, GitOps and the evidence harness](./phase-03-bootstrap-gitops-and-aws-evidence-platform.md) | 1.5 days | 0 evening, 1 | In Review |
| 4 | [Publish data, Feast stores and RAG corpus](./phase-04-publish-data-feast-stores-and-rag-corpus.md) | 1 day | 2 | Done (4A-4D; RAG/CI-CD evidence rows still design_only, need live services) |
| 5 | [Deliver ML track](./phase-05-deliver-ml-track.md) | 4-5 days as retrofit | post-deadline | **Deferred** |
| 6 | [Deliver LLM, MCP and agent track](./phase-06-deliver-llm-mcp-and-agent-track.md) | 3.5 days | 3, 4 | Pending |
| 7 | [Complete CI/CD, security and observability](./phase-07-complete-ci-cd-security-and-observability.md) | 0.5 day | 5 | Pending |
| 8 | [Produce evidence, mock-grade and promote](./phase-08-produce-evidence-mock-grade-and-promote.md) | 1.5 days | 6, 7 | Pending |

### Seven-day critical path

Ordering is variance-first: the cluster and the evidence harness are where a day
disappears to a CRD mismatch or a failing gate, so they go first; the FastAPI
code is low-variance and portable. Feast/RAG now precede the agent track because
the MCP tools read Feast. Days 3-4 absorb the restored KServe/Knative/llm-d/KEDA
chain (~13h of Tier-1 advanced work, user-confirmed 2026-08-07) without dropping
any row; if either day slips, warm-up (row 25) and A/B (row 16) are cut first —
never the test suite or observability, which carry more points across more rows.

| Day | Work |
|---|---|
| 0 evening | Read the real GCP `CPUS` quota and pick the node pool before sizing anything else; dependency-install smoke in `.venv-phase2`; GitOps repo skeleton with the 14 declared artifact paths; register a free DuckDNS subdomain |
| 1 | `--track` filter on the auditor, generate the 20 requirement test files, `terraform apply` (GKE + GCE VM), NGINX Ingress + cert-manager + DuckDNS HTTPS, `make gcp-up/down/status`, install Knative + KServe operator, bootstrap Argo CD |
| 2 | Feast (offline defined, online used), Airflow RAG pipeline + DataHub lineage, PGVector, label table, data generator drift/config; Prometheus/Grafana/Loki/Jaeger with three gateway viewer routes |
| 3 | KServe `InferenceService` + llm-d router + agentgateway + global `ModelConfig`; kagent; baseline benchmark; both FastAPI services; one parameterized Helm chart |
| 4 | Quantization optimize + before/after table; KEDA HTTP scaler; both MCP servers; three agents multi-replica; sandbox namespace; agent registry; chat and registry UIs with auth and rate limit |
| 5 | Six CI/CD workflows; sealed-secrets; NetworkPolicy; Locust HTML; `mutmut`; coverage >90% with fixture/mock proof; Hypothesis; equivalence/boundary |
| 6 | Warm-up + HA doc; A/B + Git rollback; two notebooks; two novel ideas; Ansible role on the GCE VM (`changed=0`); repository design; the SHA-stamping script; evidence capture into `docs/submission/*.md` |
| 7 | Audit, fix, freeze, submit. Buffer only |

## Fixed Architecture Decisions

- Product plane: Vercel Hobby + Supabase Free; coursework scale is 50 accounts, 10 concurrent web users, and 2 concurrent AI streams. The product UI is an explicit contract in `docs/phase2/product.md`, with approved references `UI-APPROVED-01..03`; it is not satisfied by a generic shell or a screenshot-only mock.
- Evidence plane: a Terraform-provisioned GKE Standard zonal cluster in `asia-southeast1-b`, sized from the real day-0 vCPU quota (8-16 vCPU depending on quota), plus a Terraform-provisioned GCE VM for the Ansible row. Paid entirely from an untouched GCP free-trial credit (USD 300 / 90 days) — **no out-of-pocket spend**, target under USD 100. The local machine has ~7 GB available RAM (measured) and cannot host the ~34 GB stack. `make gcp-up`/`gcp-down` hibernates node pools overnight (PVCs preserved) to keep spend near the low end of that range.
- Terraform authenticates via `gcloud auth application-default login`; **no service-account key JSON is ever created**. In-cluster workloads use Workload Identity. The trial billing account is never upgraded to paid — an exhausted trial stops rather than billing further.
- Public edge is active F5 NGINX Ingress Controller OSS (`nginx/kubernetes-ingress`), never retired community ingress-nginx. Backends are `ClusterIP` only, with a default-deny NetworkPolicy. **Istio is dropped** — the rubric section is named "Routing & Gateway (NGINX Ingress Controller)" and no LLM row mentions Istio, mesh, mTLS or TLS.
- The LLM chain is kagent `Agent` -> kagent `ModelConfig` -> agentgateway AI backend -> a KServe `InferenceService` serving a custom model server on CPU (vLLM-CPU or llama.cpp) behind an llm-d router, running on Knative Serving. **Restored 2026-08-07**: the earlier cut assumed a 16 GB k3d box; GKE has ~43 GB allocatable, and canonical row 2 (2 pts) links a KServe/llm-d deployment guide verbatim. Envoy Gateway and Envoy AI Gateway stay dropped — agentgateway is the gateway the agent rows name. MCP and A2A use agentgateway routes.
- Helm is the only render tool. **Kustomize is dropped**, so one resource has exactly one owner by construction and the duplicate-owner CI check is unnecessary.
- Observability is Prometheus + Grafana for metrics, Loki + Grafana Explore for logs, and Jaeger for traces, each exposed as its own gateway-reachable viewer route (canonical rows 40/41/42, 2 pts each). GKE Cloud Logging/Monitoring are disabled — scored via Loki/Grafana, and Cloud Logging bills per GB. **ECK/Kibana is dropped** — the rubric row says "ví dụ Kibana", an example. Secrets are GitHub Actions secrets + OIDC + sealed-secrets; **Vault is dropped**.
- The single source monorepo owns code, tests, schemas, Dockerfiles, Airflow Phase 2 wrappers, and evidence docs. `emanhthangngot/financial-distress-gitops` is a separate control repo owning Terraform, Ansible, Helm charts, Argo CD applications, policies, and environment values; this is not a microservice-per-repo design.
- Ansible evidence is mandatory and now honest work the project needs: a role-based playbook configures the Terraform-provisioned GCE VM (Docker, kubectl, kubeconfig, benchmark client) and proves `changed=0` on a second run.
- Feast defines an offline store from day one even though only the online store is read this week. This is load-bearing for the phase-05 retrofit; see that file's deferral contract.

## Timebox and Cut Policy

- Never cut: every scored LLM row, the phase-08 evidence contract, Locust HTML, autoscaling proof, Feast offline+online jobs, RAG governance metadata, the label table, agents/MCP/registry/sandbox/warm-up, observability with three reachable viewer routes, A/B tests, Terraform + Ansible, two novel ideas, evidence mapping, the three approved UI references, accessibility checks, and truthful degraded-state behaviour.
- Cut first: Istio, Envoy Gateway/Envoy AI Gateway, ECK/Kibana, Vault, Kustomize, the compatibility spike, Jenkins-in-cluster, GPU node pool, multi-environment Terraform, failure injection, and all AWS work. All cost zero scored rows.
- Cut second (only if days 3-4 overrun their absorbed Tier-1 scope): warm-up + HA doc (row 25, 1 pt) first, then A/B (row 16) — never the test suite or observability, which carry more points across more rows. Also cut: non-rubric product polish and LoRA fine-tuning.
- **Coverage >90% is a scored rubric row, not a self-imposed gate.** Canonical LLM CSV row 26 (1 pt) requires `Unit test với Test Coverage > 90%` with a screenshot showing Web API tests using fixtures and mocks. It stays a hard gate.
- **Retired self-imposed gate:** only the ">80% changed-code mutation score" bar. Canonical row 28 asks that mutation testing be used (`mutmut`), not that a score threshold be met. Record the real number.

## Success Criteria

- [ ] Reviewer -> opens the rubric matrix -> finds canonical source digest, acceptance ID, owner, implementation repo/file, contract test, behavior-validation command, and a planned evidence path for all 117 rows, and an *executed* artifact for each of the 60 LLM rows.
- [ ] Maintainer -> runs the auditor with `--require-executed --track LLM` -> passes; omitting `--track` still demands all 117 rows, keeping the ML deferral visible rather than hidden.
- [ ] Analyst -> uses the product when the evidence cluster is off -> sees persisted reports plus an honest evidence-plane state instead of a broken workflow.
- [ ] Platform operator -> runs `make gcp-down` overnight and `make gcp-up` each morning -> receives a recorded cost delta, node pools resized to zero with PVCs preserved, and never upgrades the trial billing account.
- [ ] Source CI -> publishes a signed immutable image digest -> opens a checked GitOps PR; only the merged Git change is reconciled by Argo CD.
- [ ] Phase 1 maintainer -> runs existing quality gates -> observes no change to collectors, Gold contracts, DQ semantics, or local evidence behavior, proving `.venv` was never mutated by Phase 2 dependencies.
- [ ] Platform operator -> runs the Ansible evidence-host role twice -> observes a healthy host and `changed=0` on the second run.
- [ ] ML retrofitter -> resumes phase-05 after the deadline -> finds the Feast offline store defined, the label table present, both Web APIs generic, and the 57 ML rows unchanged, so the remaining work is additive.
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

### Session 2 — 2026-08-07

**Trigger:** `/ak:plan --advice` — re-plan phases 3, 4 and 6 for a 7-day
LLM-only submission and defer phase 5. Supervised by `kongming`.

**Decisive facts established (verified in the repository, not assumed):**

1. The coursework accepts one of the two tracks. 7 days remain. Zero of 117 rows
   had an executed evidence file; only 59 phase-02 product UI artifacts existed.
   The pre-existing plan estimated 46-67 remaining workdays.
2. `scripts/audit_phase2_evidence.py::_audit_executed` has no track filter, so an
   LLM-only submission fails the phase-08 gate with 57 errors. Neither `--ml 0`
   nor deleting ML rows fixes it — `EXPECTED_ROW_COUNTS` and
   `_audit_canonical_coverage` both require all 117 rows. A `--track` filter is
   the only correct lever, and it is day-1 blocking work.
3. `tests/phase2/requirements/` does not exist, yet all 60 LLM rows pin an exact
   `validation_command` into it that the auditor executes. pytest's exit code 5
   on a zero-match reads as failure.
4. 29 LLM rows declare `artifact_repo: gitops`, resolving to 14 distinct paths
   that must exist in the GitOps checkout. That repository did not exist.
5. No LLM rubric row mentions EKS, Kubernetes, Argo CD, Istio, mesh, mTLS or
   TLS. The rows *do* require an agent sandbox, a reachable log-viewer service
   and a reachable trace-viewer service.
6. `.venv` holds only `pytest`, `ruff`, `black`, `duckdb`, `pyspark`. Every
   Phase 2 Python dependency is absent, and installing them into `.venv` risks
   the Phase 1 gate that phase-08 must re-run clean.
7. The local machine has ~5 GB free RAM — insufficient for the platform stack.

**Confirmed decisions:**

- Submit the LLM track only; keep all 117 rows in the matrix; defer phase-05 in
  place with a retrofit contract and nine load-bearing decisions the LLM track
  must honour.
- Add `--track` to the auditor rather than editing expected row counts.
- Generate the 20 requirement test files from the CSV as import-light contract
  tests before any feature work.
- Rented CPU VM running k3d as the evidence cluster; no GPU; one 3-hour cloud
  session for Terraform/TLS/cost evidence only.
- Drop Istio, KServe/llm-d/Envoy gateways, ECK/Kibana, Vault, Kustomize, the
  compatibility spike and cloud sessions two and three. Recorded rubric cost:
  ~2 points at risk, all in phase-06's inference section.
- Implement the agent sandbox as a restricted-PSS namespace with negative
  proofs, and name it accurately in the evidence rather than claiming a product
  that was not installed.
- Retire the self-imposed ">90% coverage / >80% mutation" gate; the rubric asks
  only that mutation testing be used.
- Honest expected outcome: 85-95/100, not 100.

**Action items:**

- [ ] Retarget three artifact paths in **both** `docs/phase2/rubric-matrix.csv`
      and `scripts/_phase2_rubric_items.py::EXPLICIT_IMPLEMENTATION`
      (`llminferenceservice.yaml`, `eck-otel-values.yaml`,
      `vault-external-secrets.yaml`), then re-run `--matrix-only --strict`.
- [ ] Amend `docs/phase2/acceptance-criteria.md:42` and `:46`, which assert
      Istio mTLS and mesh controls the submission will not demonstrate. Leave
      the ML acceptance lines untouched.
- [ ] Update `docs/coursework.md` to declare the LLM-only submission scope and
      the deferred ML track.
- [ ] Flip the 60 LLM rows from `design_only` to `executed` only as each
      evidence artifact is genuinely produced.
- [ ] Write `scripts/stamp_phase2_evidence.py` on day 6 — the evidence contract
      requires each file to record the SHA of the commit that contains it, in
      both repositories, with both worktrees clean. Doing this by hand on day 7
      is the single most likely late failure.

**Whole-plan consistency:** phases 3, 4, 5 and 6 and this index are reconciled.
Phase 7 and phase 8 still carry ML-track language and a `--ml 100 --llm 100`
audit invocation; both are corrected as part of this session.

### Session 3 — 2026-08-07 (afternoon)

**Trigger:** `/ak:plan --advice` — re-plan phase-03 onto GKE after two facts
invalidated the rented-VM/k3d/AWS design from Session 2.

**Decisive facts established:**

1. The user will spend only GCP free-trial credit (USD 300 / 90 days,
   untouched) — no Hetzner, no Vast.ai, no AWS out of pocket.
2. Canonical LLM CSV row 67 reads `Dùng Terraform để setup GKE hoặc các cloud
   services` — GKE named first. Terraform-provisioned GKE scores it verbatim.
3. A peer repository for the same coursework, `itsmekhoathekid/RecSys-MLops`
   (ML track, pushed 2026-08-04), independently converged on the same shape:
   GKE Standard zonal in `asia-southeast1`, Workload Identity, Terraform split
   one file per service, DataHub via Helm. Its published cost measurement —
   **USD 0.65-0.80/hr running, ~USD 0.14/hr hibernated** — is the basis for this
   plan's `make gcp-up/down` requirement and the < USD 100 budget target.
4. Moving off k3d removes the reason KServe/Knative/llm-d were cut (`"a full
   day of CRD wrangling on k3d"`). GKE has ~43 GB allocatable at the top of the
   quota table; those install cleanly, converting canonical row 2 (2 pts, links
   a KServe/llm-d guide) from at-risk to satisfied as written.
5. Local RAM was previously misrecorded as "~5 GB free"; measured this session:
   14 GB total, ~7 GB available, 16 cores, 7.5 GB zram swap. Still insufficient
   for the ~34 GB restored stack, so the cloud-cluster decision is unchanged —
   only the provider and the restored scope are.

**Confirmed decisions:**

- Replace the rented-VM/k3d evidence cluster with Terraform-provisioned GKE
  Standard zonal (`asia-southeast1-b`) plus a Terraform-provisioned GCE VM for
  Ansible. Node pool size is decided day 0 from the real quota, not assumed.
- Delete the timeboxed 3-hour AWS session entirely; Terraform against GCP moves
  to day 1 as the main IaC path.
- Restore KServe `InferenceService`, Knative Serving and the llm-d router (row
  2, row 4); add a KEDA HTTP scaler (rows 12/18/23). Absorb the added ~13h into
  days 3-4 without dropping any row (user-confirmed).
- Write `make gcp-up`/`gcp-down`/`gcp-status` on day 1, not day 5 — the single
  largest cost lever in the plan.
- No service-account key JSON, ever; ADC + Workload Identity only. Never
  upgrade the trial billing account.
- Domain/HTTPS row (46) moves to DuckDNS (free) + cert-manager ACME HTTP-01,
  since the GKE LoadBalancer exposes 80/443 directly.
- Evidence stays under `docs/phase2/evidence/` (the auditor's path-prefix
  contract is unchanged); add `docs/submission/*.md` as a reviewer-facing index
  linking into it, satisfying the canonical CSV's per-section-doc note without
  touching the machine contract.
- Expected outcome revised from 90-97/100 (Session 2) to **95-99/100**: the
  restored KServe/llm-d chain converts the highest-risk scored row (row 2) from
  at-risk to satisfied as written.

**Action items:**

- [x] Rewrite `phase-03-bootstrap-gitops-and-aws-evidence-platform.md` around
      GKE (filename kept for existing links; AWS content removed).
- [ ] Rewrite `phase-06` restoring KServe/Knative/llm-d/KEDA and re-slotting
      Tier-1 advanced work into days 3-4.
- [ ] Sweep `phase-04` (lines referencing "no AWS cluster"), `phase-07` (day
      slot only), `phase-08` (AWS resource inventory -> GCP cost/hibernate
      evidence, add `docs/submission/` capture step).
- [ ] Update `docs/phase2/adr/adr-010-*.md`: move KServe/Knative/llm-d from
      *Dropped* to a new *Restored* section; replace the ephemeral-EKS/rented-VM
      decision with GKE; add the free-credit-only budget constraint.
      `adr-004-kserve-018-pin.md` partially revives — re-mark its status.
- [ ] Re-run `--matrix-only --strict`, `run_stage1_quality_gates.py`, and a
      stale-term grep (`k3d|vast\.ai|EKS|ap-southeast-1|rented (VM|host)`) across
      the plan directory and ADR-010 after the sweep.

**Whole-plan consistency:** phase-03 reconciled this session. `plan.md`
reconciled in this same pass. phase-04/06/07/08 and ADR-010/ADR-004 are the
remaining sweep surface — see action items above.

### Session 4 — 2026-08-08

**Trigger:** `/ak:cook phase-04` — planner produced a file-level implementation
supplement (`phase-04-implementation-notes.md`); brainstorm gate surfaced a
real cross-phase dependency before any code was written.

**Decisive fact established:** `src/llm/rag_pipeline.py::write_vectors` needs
a real embedding backend for its evidence run. The user rejected both the
sentence-transformers stopgap and the deterministic-hash-embedder-now/hot-swap
option, choosing instead to call phase-06's vLLM-CPU inference endpoint
directly. That endpoint does not exist until phase-06 (days 3-4). Chunking,
dedup, governance, the Feast repo, DAG wrappers and CI/CD do not depend on the
embedding backend and were not blocked — but the user chose to stop rather
than implement that unblocked subset this session.

**Confirmed decision:**

- Critical path reorders: **phase-06 (KServe/Knative/llm-d/vLLM-CPU inference
  stack) moves before phase-04 completes**, inverting the "Seven-day critical
  path" table's stated ordering ("Feast/RAG now precede the agent track
  because the MCP tools read Feast"). That rationale no longer holds for the
  embedding step specifically — RAG's vector-write path now depends on the
  agent/inference track instead of preceding it.
- Phase-04 is **not started** this session. `phase-04-implementation-notes.md`
  (file-level plan, Feast/RAG/drift/label design, 4-slice execution order) is
  written and stays valid — it targets the pinned rubric-matrix artifact paths
  and is the plan to resume from once phase-06's endpoint exists.
- Next work: `/ak:cook phase-06` to stand up the vLLM-CPU inference endpoint,
  then resume phase-04 slices 4A-4D per the implementation-notes file. Slices
  4A (drift+labels) and 4C (Feast+jobs+DAGs) do not actually require the
  endpoint and remain safe to implement first when phase-04 resumes, if a
  future session wants to parallelize rather than strictly serialize.

**Action items:**

- [ ] Reconcile `phase-06-deliver-llm-mcp-and-agent-track.md`'s day slot (3-4)
      against this reorder — does its own scope still assume Feast/RAG already
      published, or does it now need to expose an embeddings-compatible route
      before RAG can complete?
- [ ] Update the "Seven-day critical path" table above once the new day-by-day
      shape is confirmed (currently still shows Feast/RAG on day 2, agent
      track on days 3-4, unreordered).
- [ ] Resume phase-04 (4A/4B/4C/4D per `phase-04-implementation-notes.md`)
      after phase-06's inference endpoint exists.

**Whole-plan consistency:** not reconciled this session — the critical-path
table above and `phase-06-deliver-llm-mcp-and-agent-track.md` still reflect
the pre-reorder ordering. Flagged for the next planning session on either file.

<!-- slug: unified-phase2-ml-llm-gitops -->
