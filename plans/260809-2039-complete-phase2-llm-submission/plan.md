---
title: "Complete Phase2 LLM Submission"
description: "Execution roadmap for the 88 unscored LLM rubric points that remain after phase-03 implementation, with phase-04 source work statically verified but blocked on deployment-time evidence: contract reconciliation, inference platform, both Web APIs as MCP tools, three agents, gateway UIs, observability, CI/CD, verification gates, and the frozen evidence submission."
status: in-progress
priority: P1
effort: "9 focused days (re-budgeted after the 2026-08-09 red team)"
branch: dev
tags: [phase2, llm, kubernetes, gitops, evidence, coursework]
blockedBy: [260802-1037-unified-phase2-ml-llm-gitops]
blocks: [260811-1627-close-llm-rubric-to-100]
created: 2026-08-09
---

# Complete Phase2 LLM Submission

## Overview

Active phase: **explicit Phase 2**, LLM track only. This plan is the execution
roadmap for what is left after `plans/260802-1037-unified-phase2-ml-llm-gitops/`
closed phase-01 through phase-03, plus the deployment-time evidence still
blocking phase-04.

That plan stays the **rubric and architecture authority** — fixed architecture
decisions, the evidence contract, and the phase-05 ML deferral contract live
there. This plan owns **sequencing, current-state deltas, and the cut ladder**.
Where the two disagree on sequencing, this plan wins; where they disagree on
architecture, that one wins, except for the four deltas recorded in
`## Red Team Review`.

Read before starting: `AGENTS.md`,
`plans/260802-1037-unified-phase2-ml-llm-gitops/plan.md`, and that plan's
`phase-06`, `phase-07`, `phase-08` files.

## Measured Starting State (2026-08-09, post-red-team)

| Fact | Value | Source |
|---|---|---|
| LLM rows with a real evidence file | 7 rows / **12 of 100 points** | `docs/phase2/evidence/llm/` |
| Remaining | 53 rows / **88 points** | rubric matrix vs. filesystem |
| `evidence_type` of **all 117 rows** | `design_only` — including the 7 with evidence | `docs/phase2/rubric-matrix.csv`; generated from `scripts/_phase2_rubric_items.py:919` |
| Matrix consistency | `--matrix-only --strict` passes | `scripts/audit_phase2_evidence.py` |
| GitOps control repo | `~/Studying/FSDS/financial-distress-gitops`, HEAD `0b2e476`, **PRIVATE** (source repo is PUBLIC) | `gh repo view` |
| GKE cluster | `fsds-evidence`, `asia-southeast1-b`, both pools at 0 nodes, ingress LB IP `34.21.242.110` retained | `make gcp-status` |
| **Real capacity when restored** | `make gcp-up` restores **`primary-pool` only, 1× e2-standard-8** (~7.6 allocatable vCPU). `secondary_pool_node_count` = 0, **no `autoscaling{}` block on either pool**, project quota `CPUS_ALL_REGIONS` = 12, evidence VM holds 2 | `Makefile:29-34`, `terraform/gcp/variables.tf:24-53`, `gke.tf:54,87` |
| **NetworkPolicy enforcement** | **OFF** — no `network_policy` block in `gke.tf`; Cloud NAT is provisioned | `grep -c network_policy gke.tf` → 0 |
| Genuinely deployed via GitOps | Terraform GKE + network + registry + IAM, F5 NGINX ingress, cert-manager, Argo CD, Knative + KServe (v0.14.1), **TEI embedding `InferenceService`**, Ansible evidence-VM roles | gitops `platform/`, `terraform/`, `ansible/` |
| **Placeholder only** (5-line comment, zero content) | `platform/security/sealed-secrets.yaml`, `platform/inference/model-server.yaml`, `platform/agents/{agentregistry,agent-sandbox,global-model-config,warm-pool}.yaml`, `platform/llm/ab-testing.yaml`, `platform/observability/{prometheus,loki-otel}-values.yaml`, `charts/{feature,drift}-mcp/Chart.yaml`, `terraform/envs/evidence/main.tf` | head of each file |
| Argo coverage | 4 Applications: cert-manager, nginx-ingress, platform-inference, platform-security. **Nothing syncs** `platform/agents`, `platform/llm`, `platform/observability`, `charts/`. `applicationset-dev.yaml` generates from `apps/dev/*`, which does not exist | `argocd/` |
| Requirement test files | `tests/phase2/requirements/test_llm_ac_01..20.py` exist, **generator-owned** ("do not hand-edit"), and assert only: evidence parses, 9 keys non-empty, `artifact_path` `is_file()` | `scripts/generate_phase2_requirement_tests.py` |
| Phase 2 dependency manifest | **Does not exist.** `.venv-phase2` is missing `hypothesis`, `mutmut`, `locust`, `mcp`. `requirements.txt` has none of `fastapi`, `feast`, `hypothesis`, `locust`, `mutmut`. `phase2-ci.yaml` installs `requirements.txt` only | import probe; `requirements.txt` |
| CI | `phase2-ci.yaml` reusable + 3 callers. **No OIDC anywhere** (`grep id-token` → 0); two long-lived PATs (`GHCR_TOKEN`, `GITOPS_PAT`). Digest PR writes `pipelines/<name>/digest.txt`, which nothing consumes. No image signing | `.github/workflows/` |
| Feast online store | Points at docker-compose DNS (`phase2-redis:6379`, `phase2-postgres`) and a MinIO `s3://` registry. **No Redis/Postgres/MinIO in the cluster** | `feature_repo/*/feature_store.yaml` |
| `apps/web` | Agent registry route and the whole assistant/chat surface **already exist** (Supabase/fixture-backed). No Dockerfile, no `output: standalone`, nothing deploys it | `apps/web/src/app/agents/registry/`, `src/components/assistant/` |
| Absent code | `src/agents/`, `apps/feature-mcp/`, `apps/drift-mcp/`, `src/llm/{model_server,benchmark,embedding_registry,citation_guard}.py`, `notebooks/` content | repo |
| Python envs | `.venv` = Phase 1 gate (never mutate), `.venv-phase2` = Phase 2 deps | repo |

## Path Authority Rule

**`docs/phase2/rubric-matrix.csv`'s `artifact_path` column is the authority for
where code lives.** The generated requirement tests assert `artifact.is_file()`
at exactly that path, so a "better" layout costs the row. Build at the declared
path. Retarget a path in `scripts/_phase2_rubric_items.py::EXPLICIT_IMPLEMENTATION`
(then regenerate the CSV and the tests) **only** when two rows collide on one
artifact and each needs distinct proof — which today is true for exactly one
pair: both `LLM-demonstrate-basic-underst-*` rows point at
`notebooks/agent-mcp-demo.ipynb`.

Never hand-type a `rubric_id` into a plan, a filename, or an evidence file.
Copy it from the CSV — the IDs are long and silently truncatable, and evidence
filenames are contractually `docs/phase2/evidence/llm/<rubric_id>.md`.

## Goals

| # | Goal | Priority |
|---|------|----------|
| 1 | Turn all 53 remaining LLM rows into executed, reproducible evidence artifacts at their declared artifact paths | P0 |
| 2 | Make the audit gate satisfiable before writing code against it (evidence_type, SHA contract, cut allowance, deps) | P0 |
| 3 | Keep every deployment path GitOps-only (source CI → digest PR → Argo sync) | P0 |
| 4 | Honor all nine load-bearing decisions so the phase-05 ML retrofit stays additive | P1 |
| 5 | Keep GCP spend inside the free-trial credit; hibernate whenever not capturing | P1 |

## Phases

| # | Phase | Points | Days | Status |
|---|-------|-------:|------|--------|
| 1 | [Reconcile contracts, capacity and platform gaps](./phase-01-start.md) | 3 | 1.5 | In Progress |
| 2 | [Stand up inference platform and model chain](./phase-02-stand-up-inference-platform-and-model-chain.md) | 8 | 1 | Pending |
| 3 | [Ship both FastAPI services, MCP servers and agents](./phase-03-ship-both-fastapi-services-mcp-servers-and-agents.md) | 24 | 2 | Completed |
| 4 | [Complete gateway, UIs and observability](./phase-04-complete-gateway-uis-and-observability.md) | 21 | 1.5 | Blocked — pending live evidence |
| 5 | [Close CI/CD, security and verification gates](./phase-05-close-ci-cd-security-and-verification-gates.md) | 23 | 1.5 | Completed — 23/23 points executed with live evidence, including two-node Knative A/B |
| 6 | [Produce evidence, stamp SHAs and mock-grade](./phase-06-produce-evidence-stamp-shas-and-mock-grade.md) | 9 | 1.5 | In Progress — live proofs captured; evidence and SHA stamping pending commit approval |

12 points already executed + 88 planned = 100, in **9 days**, not 7.

**This is an honest re-budget, not padding.** Measured throughput to date is 12
LLM points since 2026-08-02. Phase 1 grew from 0.5d to 1.5d because five of its
inputs turned out to be placeholders rather than built work, and phases 3-4 grew
because `apps/web` must be containerized and a Feast-reachable online store must
exist in-cluster. If 9 days is not available, execute the cut ladder below
deliberately rather than discovering the overrun on day 7.

Dependencies are linear: 1 → 2 → 3 → 4, phase 5 needs 3 and 4, phase 6 needs all.

## Phase 04 synchronization — 2026-08-10

- Project manager -> records Phase 04 implementation -> source and private
  GitOps worktrees contain the web standalone/live-plane wiring, shared
  telemetry/redaction, gateway routes, auth/TLS/rate-limit manifests, and
  Prometheus/Loki/Jaeger/OTel/dashboard wiring -> static implementation is
  present, with the file-level inventory in
  [phase 04](./phase-04-complete-gateway-uis-and-observability.md).
- Project manager -> records verification -> Python source tests are 16/16
  passed, web behavior tests are 19/19 passed with coverage disabled, web
  typecheck/build passed, GitOps Helm/YAML checks passed, and both diffs are
  whitespace-clean -> the default narrow web test command still exits 1 on
  the package-wide 90% coverage gate.
- Project manager -> keeps Phase 04 blocked -> the active cluster has no nodes,
  only the prior `hello-web` route/certificates, `platform-observability` is
  `OutOfSync/Healthy`, and Phase 04 pods are `Pending` -> no live route/auth/
  TLS/observability proof exists.
- Project manager -> records deployment blockers -> auth ciphertexts remain
  placeholders, the web chart digest is empty, GitOps changes are uncommitted,
  and all 13 Phase 04 evidence filenames are missing -> no executed-evidence
  claim or evidence-row flip is made.

## Phase 06 synchronization — 2026-08-11

- Project manager -> records the five live Phase 06 artifact proofs ->
  `notebooks/agent-understanding-demo.ipynb`, `notebooks/agent-mcp-demo.ipynb`,
  `src/llm/embedding_registry.py`,
  `src/llm/citation_guard.py`, and `docs/phase2/low-level-design.md` were
  captured -> live artifact capture is complete, while the five canonical
  evidence markdown files and SHA-stamping remain pending commit approval.
- Project manager -> preserves rubric honesty -> the six
  `LLM-observability-*` rows and seven `LLM-routing-gateway-*` rows remain
  `design_only` -> no live observability or gateway evidence is claimed.
- Cost owner -> records the infrastructure state -> the evidence GCP VM is
  stopped and the pool resize is still being verified -> the final zero-node
  hibernation check remains open.
- Project manager -> keeps Phase 06 in progress -> canonical evidence,
  separate SHA commits, strict audit, mock-grade, and final hibernation
  verification remain open -> no phase is marked complete.

## Closeout successor — 2026-08-11

Phases 1-3 and 5 are done; 79 of 100 LLM points are executed and pass the strict
two-repo gate. The remaining 21 points (phase 4's 13 rows) plus the phase-6
freeze steps are sequenced in
`plans/260811-1627-close-llm-rubric-to-100/`. That plan owns sequencing from
here; this plan stays the architecture and evidence-contract authority.

## Cut Ladder

Ranked by points-per-hour, worst first. Each cut has a decision date; if the
phase named is not done by then, cut and move on. **A cut row stays
`design_only`, so the final audit must be run with the `--accept-design-only`
allowance built in phase 1, naming each cut row explicitly** — the gate stays
honest by forcing you to name what you dropped.

| Order | Cut | Points conceded | Decide by |
|---|---|---:|---|
| 1 | Warm-up mode | 2 | end of phase 5 day 1 |
| 2 | A/B testing (both rows) | 2 | end of phase 5 day 1 |
| 3 | Novel idea 2 (citation/PII guard) | 2 | start of phase 6 |
| 4 | The **drift** Web API's agent + autoscale + registry rows (keep the API and MCP tool) | 5 | end of phase 3 day 1 |
| 5 | Second notebook | 2 | start of phase 6 |

**Never cut:** the test suite, observability, the sandbox negatives, the
evidence contract, or the Phase 1 no-regression gate — each carries more points
across more rows than anything above.

## Point Ledger — the 88 remaining points

Every `rubric_id` below is copied verbatim from the CSV. Phase files carry the
full per-row tables with artifact paths.

| Section | Remaining | Phase |
|---|---:|---|
| IaC (Terraform, Ansible) | 2 | 1 |
| Security — centralize secret management | 1 | 1 |
| LLM inference platform (deploy 2, custom model 2, benchmark+optimize 2) | 6 | 2 |
| Global model config | 2 | 2 |
| Web API kéo dữ liệu (FastAPI 1, async 1, MCP+helm 2, agent multi-replica 2, sandbox 1, publish 2) | 9 | 3 |
| Web API real-time drift detection (same six rows) | 9 | 3 |
| Agent registry | 2 | 3 |
| Coordinator agent (coordinate 2, publish 2) | 4 | 3 |
| Routing & Gateway (hide services 2, domain+HTTPS 1, UI test agent 2, UI registry 2, auth 2, log viewer 2, trace viewer 2) | 13 | 4 |
| Observability (Prometheus+Grafana 1, token/TTFT/PII metrics 2, agent/tool call metrics 2, logs 1, traces 1, Web API metrics 1) | 8 | 4 |
| CI/CD (RAG pipeline 2, agent kéo dữ liệu 2, agent drift 2, coordinator 2) | 8 | 5 |
| Validation & Verification (equivalence/boundary 2, mutation 2, property 2, Locust 2, base 1) | 9 | 5 |
| Repository design | 2 | 5 |
| Warm-up mode | 2 | 5 |
| A/B testing | 2 | 5 |
| Demonstrate understanding of Agents (2 notebook rows) | 4 | 6 |
| Novel ideas | 4 | 6 |
| Documentation | 1 | 6 |
| **Total** | **88** | |

## Cost and Capacity Discipline

The cluster is hibernated and must return to zero nodes at the end of every
session. `make gcp-up` / `gcp-down` / `gcp-status` live in the GitOps Makefile
(`CLUSTER=fsds-evidence`, `ZONE=asia-southeast1-b`).

Two corrections the red team surfaced, both fixed in phase 1:

- `gcp-up` restores **one pool, one node**. Everything in phases 2-4 lands on
  ~7.6 allocatable vCPU alongside Argo CD, cert-manager, sealed-secrets, NGINX,
  Knative, KServe and the TEI embedding pod. Phase 1 produces a written
  CPU/memory budget; without it, phase 3's KEDA scale-out evidence is
  unobtainable because there is nothing to scale into.
- `gcp-down` never stops the evidence VM, so it bills continuously and holds 2
  of the 12 project vCPUs. Phase 1 adds `instances stop/start` to the targets.

Record the credit balance before and after every session; `docs/submission/cost.md`
needs the per-session deltas. Never upgrade the trial billing account.

Phases 1 (contract work), 5 (test authoring) and 6 (documents) do most of their
work with the cluster down.

## GitOps Repository Visibility — decided 2026-08-09

`financial-distress-gitops` **stays private**. It carries a committed
`terraform.tfstate` (cluster CA, control-plane endpoint, project ID) and
`ansible/inventory.ini` (SSH user, key path); publishing it would leak all of
that, and git history keeps it after any later deletion.

Consequences this plan must honor:

- Phase 6 adds a step granting the grader read access on the GitOps repo, and
  states that in `docs/submission/README.md`.
- Evidence files must stop asserting `redaction_status: none — public repo` on
  rows whose artifact lives in the private repo. Phase 1 corrects the two
  existing files that say this and fixes the template.

## Non-Goals

- Phase-05 ML track. Deferred; the 57 ML rows stay `design_only` and `--track LLM`
  excludes them from the executed gate. **The nine load-bearing decisions are
  kept in full** (user decision, 2026-08-09) — one parameterized Helm chart,
  list-driven CI matrix, directory-generator ApplicationSet, generic Web APIs,
  `service`-labelled metrics, and the rest.
- The unified plan's cut list: Istio, Envoy Gateway/AI Gateway, ECK/Kibana,
  Vault, Kustomize, GPU node pool, multi-environment Terraform, AWS. **llm-d
  joins this list** — see `## Red Team Review`.
- Non-rubric product polish in `apps/web` beyond the two scored routes, the
  auth/rate-limit row, and making it deployable.

## Success Criteria

- [ ] Maintainer -> runs `scripts/audit_phase2_evidence.py --strict --require-executed --run-validations --track LLM --gitops-root ~/Studying/FSDS/financial-distress-gitops` -> exits 0 for every LLM row not named in `--accept-design-only`, and the 57 ML rows remain visibly `design_only`.
- [ ] Auditor -> checks any row's `artifact_path` -> finds a real implementation file there, not a placeholder comment.
- [ ] Reviewer -> opens any of the 60 LLM evidence files -> finds rubric_id, execution timestamp, 40-hex source and GitOps SHAs, versions, reproduction command, expected result, actual result and an accurate redaction status.
- [ ] Coursework reviewer -> follows `docs/submission/*.md` -> reaches an executed artifact for every scored section, with read access to the private GitOps repo granted.
- [ ] Phase 1 maintainer -> runs `.venv/bin/python scripts/run_stage1_quality_gates.py` -> passes, proving `.venv` was never mutated by Phase 2 dependencies.
- [ ] Cost owner -> reads `docs/submission/cost.md` -> finds per-session credit deltas including the evidence VM, a final balance, and confirmation the trial account was never upgraded.
- [ ] ML retrofitter -> resumes phase-05 later -> finds all nine load-bearing decisions intact.

## Open Questions

- Which small instruction-tuned model fits ~7.6 allocatable vCPU at acceptable
  TTFT alongside the observability stack? Decided empirically in phase 1's
  capacity budget and phase 2 step 2, not assumed.
- Can `mutmut` 3.x reach >80% on the declared module subset within the phase-5
  budget? The threshold is scored text (see `## Red Team Review`), so this is a
  real gate, and the subset is chosen to make it reachable.
- Does raising `secondary_pool_node_count` to 1 fit the 12-vCPU quota after the
  evidence VM is stopped (8 + 4 = 12, exactly at cap)? Phase 1 answers this
  empirically before phase 3 needs the headroom.

## Red Team Review

### Session — 2026-08-09
**Findings:** 15 after dedupe from 39 raw (4 hostile reviewers: Security
Adversary, Failure Mode Analyst, Assumption Destroyer, Scope & Complexity
Critic) — **15 accepted, 0 rejected**.
**Severity breakdown:** 7 Critical, 8 High.

All Critical findings were independently re-verified in this session before
acceptance; none rests on reviewer assertion alone.

| # | Finding | Severity | Disposition | Applied To |
|---|---------|----------|-------------|------------|
| 1 | 13 rows / 22 pts target `artifact_path` values the plan never created | Critical | Accept | Path Authority Rule; phases 2, 3, 5, 6 |
| 2 | All 117 rows are `evidence_type: design_only`; no phase flips them, so `--require-executed` fails all 60 | Critical | Accept | Phase 1 |
| 3 | SHA stamping is non-convergent — `git commit --amend` invalidates the SHA it just stamped | Critical | Accept | Phase 1 (contract fix), phase 6 (execution) |
| 4 | `make gcp-up` restores one pool / one 8-vCPU node; no cluster autoscaler; 12-vCPU quota | Critical | Accept | Cost and Capacity Discipline; phase 1 |
| 5 | Eleven "already deployed / already scaffolded" GitOps files are comment placeholders; no Argo Application covers `platform/agents`, `platform/llm`, `platform/observability`, `charts/` | Critical | Accept | Measured Starting State; phases 1-5 |
| 6 | Feast online store points at docker-compose DNS and a MinIO registry — unreachable in-cluster, blocking 9 points | Critical | Accept | Phase 3 |
| 7 | Cut policy contradicts the pass criterion — `--require-executed` is all-or-nothing | Critical | Accept | Cut Ladder; phase 1 (`--accept-design-only`) |
| 8 | 12 rubric IDs in the phase files were truncated to 49 chars and do not exist | High | Accept | Path Authority Rule; all phase tables regenerated from the CSV |
| 9 | NetworkPolicy enforcement is off on the cluster, making the sandbox and hide-services proofs inert | High | Accept | Phase 1 |
| 10 | GitOps repo is private while the source repo is public; evidence links 404 for the grader | High | Accept | GitOps Repository Visibility; phases 1, 6 |
| 11 | No Phase 2 dependency manifest; `.venv-phase2` missing `hypothesis`/`mutmut`/`locust`/`mcp`; CI installs `requirements.txt` only | High | Accept | Phase 1 |
| 12 | llm-d was already rejected by decision D-E3 and pinned KServe v0.14.1 ships no `LLMInferenceService` | High | Accept | Phase 2 (dropped), phase 5 (A/B on Knative traffic split) |
| 13 | Requirement tests are generator-owned and assert only file existence — "fill the tests" violates the generator and `--run-validations` is vacuous | High | Accept | Phase 1 (extend the generator), all phases (language corrected) |
| 14 | `apps/web` agent registry route and assistant chat surface already exist; the app has no Dockerfile and is not deployable | High | Accept | Phase 4 |
| 15 | Three rubric-text errors: `Mutation score > 80%` is in the scored `requirement` text; phase 4's metric list omitted TTFT and the PII-safety frequency; phase 1 would have claimed OIDC that does not exist | High | Accept | Phases 1, 4, 5 |

#### User decisions taken during adjudication

1. **Apply all 15 findings.**
2. **GitOps repo stays private**; the grader is granted read access and the
   `redaction_status` wording is corrected. (Rejected: publishing the repo,
   which would leak committed Terraform state and the Ansible inventory.)
3. **`Mutation score > 80%` is restored as a real gate.** This reverses the
   unified plan's Session 2 decision, on new evidence: the threshold is printed
   verbatim in the canonical CSV's `requirement` **and** `deliverables` columns
   for a 2-point row. `mutmut` is scoped to a small pure-module subset chosen so
   the bar is reachable, and the real score is recorded either way.
4. **All nine ML-retrofit load-bearing decisions are kept.** The Scope Critic
   argued they cost time no rubric row pays for; the user's standing decision
   from 2026-08-07 stands, so the parameterized chart, list-driven CI matrix and
   directory-generator ApplicationSet remain in scope.

#### Additional accepted, folded into phase steps rather than listed separately

- `gcp-down` never stops the evidence VM (cost ledger + 2 vCPU) → phase 1.
- No PVC for model weights; TEI runs scale-to-zero on `emptyDir` → phase 1/2.
- CI digest PR writes a path nothing consumes; no image signing → phase 5.
- Auditor has no secret scanning despite phase 6 claiming it rejects
  "secret-bearing" proof → phase 1 adds a denylist scanner.
- `eval` on a `workflow_call` input in `phase2-ci.yaml` → phase 1.
- RAG documents have no untrusted-content boundary → phase 3 adds a delimiter
  plus one poisoned-fixture negative test.
- `terraform plan` cannot return "No changes" while node counts are managed and
  hibernation is imperative → phase 1 adds `lifecycle { ignore_changes }`.
- Only the chat UI was to get auth, leaving Grafana/Loki/Jaeger public → phase 4
  applies auth to all five routes and redacts span attributes.

### Whole-Plan Consistency Sweep
- Files reread: `plan.md`, `phase-01-start.md`, `phase-02-…`, `phase-03-…`,
  `phase-04-…`, `phase-05-…`, `phase-06-…`
- Decision deltas checked: 19 (15 findings + 4 user decisions)
- Reconciled stale references: rubric ID tables in all 6 phase files regenerated
  from the CSV; every "Related Code Files" path realigned to `artifact_path`;
  llm-d removed from phases 2 and 5; "already scaffolded" replaced with
  "placeholder today" throughout; day budget 7 → 9 in `plan.md` and the phase
  table; the unified plan's phase-06/07/08 marked superseded-for-sequencing.
- Unresolved contradictions: 0

<!-- slug: complete-phase2-llm-submission -->
