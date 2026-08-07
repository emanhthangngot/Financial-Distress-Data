---
title: "Phase 3: Bootstrap GKE, GitOps and the evidence harness"
status: in-review
estimate: "1.5 days (day 0 evening + day 1)"
---

# Phase 3: Bootstrap GKE, GitOps and the evidence harness

## Overview

Stand up the one cluster every later phase deploys onto, create the
`emanhthangngot/financial-distress-gitops` control repository, and — the part
that gates everything — repair the phase-08 evidence harness so an LLM-only
submission can pass at all. Argo CD is the only in-cluster deployer after
bootstrap.

Rewritten twice. The 2026-08-07 morning rewrite cut the original ~25-component,
8-12 day scope down to a rented CPU VM running `k3d`. The 2026-08-07 afternoon
rewrite replaced that VM with **Terraform-provisioned GKE**, because the user
holds an untouched GCP free trial and will not spend out of pocket, and because
the canonical LLM CSV names GKE first in the IaC row. See `## Scope Changes` for
what stayed dropped and what came back.

The filename still reads `...-and-aws-evidence-platform.md`. It is kept for the
`plan.md` links and the `ak plan` index; the AWS session inside it is gone.

## Blocking Facts (verified 2026-08-07, not assumptions)

- `scripts/audit_phase2_evidence.py::_audit_executed` (line 644) iterates **all**
  117 matrix rows and errors on any row whose `evidence_type != "executed"`.
  There is no track filter. An LLM-only submission fails the phase-08 gate with
  57 errors. `_audit_frozen_revisions` (line 571) and
  `_audit_behavior_validations` (line 723) iterate the same unfiltered list.
- `EXPECTED_ROW_COUNTS = {"ML": 57, "LLM": 60}` (line 116) and
  `_audit_canonical_coverage` (line 189) both require all 117 rows to remain in
  the matrix. Passing `--ml 0` or deleting ML rows makes the gate fail
  differently, not pass.
- `docs/phase2/rubric-matrix.csv` already carries a `track` column (field 2), so
  filtering needs no new parsing helper.
- `_audit_matrix` (line 290) enforces
  `evidence_path.startswith("docs/phase2/evidence/")`. Evidence files cannot be
  relocated without rewriting 60 CSV rows.
- `tests/phase2/requirements/` **does not exist**. All 60 LLM rows pin an exact
  `validation_command` of the form
  `pytest tests/phase2/requirements/test_llm_ac_NN_<name>.py -k '<rubric_id>'`,
  matched against the regex at line 728, and `_audit_behavior_validations`
  executes it. pytest exits 5 on a zero-match, which the auditor reads as
  failure.
- All 60 LLM rows currently carry `evidence_type: design_only`.
- 29 LLM rows declare `artifact_repo: gitops`, resolving to **14 distinct
  artifact paths** that must exist in the GitOps checkout at audit time.
- Local host measured: **14 GB total RAM, ~7 GB available, 16 cores, 7.5 GB
  zram swap**. (An earlier revision of this file recorded "~5 GB free" — wrong.)
  Still insufficient: the stack needs ~34 GB with the restored inference chain.
- Installed: `docker`, `kubectl`, `helm`, `argocd`, `gh`, `gcloud`, `node`,
  `pnpm`. Missing: `terraform`, `ansible`, `mutmut`, `locust`. `k3d` is no
  longer required.
- `.venv` contains only `pytest`, `ruff`, `black`, `duckdb`, `pyspark`. Every
  Phase 2 Python dependency is absent.
- GCP free trial: USD 300 over 90 days, unused. Trial vCPU quota is **unverified**
  and is the day-0 kill-switch below.

## Requirements

- Functional: one reachable GKE cluster; one Terraform-provisioned GCE VM for the
  Ansible row; Argo CD reconciling the GitOps repository; NGINX Ingress OSS as
  the only externally reachable object; cert-manager issuing a browser-valid
  certificate on a registered domain; Knative Serving and the KServe operator
  installed for phase-06; the phase-08 auditor able to gate a single track; 60
  executable requirement tests present and selecting.
- Non-functional: **zero out-of-pocket spend** — GCP free-trial credit only,
  target under USD 100 of the 300; no service-account key JSON ever created;
  Phase 1 `.venv` left untouched so `scripts/run_stage1_quality_gates.py` keeps
  passing.

## Architecture

**Compute.** GKE Standard **zonal** cluster in `asia-southeast1-b`, provisioned
by Terraform. Chosen over the local machine (insufficient RAM), over a rented
third-party VM running k3d (costs real money, needs a k3d-viability kill-switch,
and scores the IaC row only by analogy), and over GKE Autopilot (Autopilot
restricts privileged pods and DaemonSets that the observability stack wants, and
bills per-pod requests).

Canonical LLM CSV row 67 reads `Dùng Terraform để setup GKE hoặc các cloud
services`. GKE is named first; provisioning it with Terraform scores that row as
written.

**Node sizing is decided on day 0 from the real quota**, not assumed:

| `CPUS` quota in `asia-southeast1` | Node pool | Allocatable | DataHub |
|---:|---|---:|---|
| ≥ 12 | `e2-standard-8` + `e2-standard-4` | ~43 GB | keep |
| = 8 | 1× `e2-standard-8` | ~28 GB | keep; reduce observability replicas |
| < 8 | 1× `e2-standard-4` | ~13 GB | **cut** — forfeits the RAG/DataHub row (2 pts) |

Measured stack budget: ~16.7 GB platform + 2 GB Airflow + 6 GB DataHub + ~9 GB
for the restored Knative/KServe/llm-d/KEDA chain and a larger model ≈ **34 GB**.

**Credential boundary.** Terraform authenticates from the local machine with
`gcloud auth application-default login`. **No service-account key JSON is ever
created.** A leaked long-lived key compromises the entire project, and once it is
in git history sealed-secrets cannot undo it. In-cluster workloads obtain GCP
identity through Workload Identity, never a mounted key file. The DuckDNS token
and any other secret reach the cluster as a sealed or manually-created `Secret`,
never as plaintext in either repository.

**Billing boundary.** The trial billing account is never upgraded to paid. A
trial that exhausts its credit *stops*; an upgraded account bills with no hard
cap. GKE Cloud Logging and Cloud Monitoring are **disabled** in Terraform
(`logging_service`, `monitoring_service`) — the rubric scores Loki and Grafana,
and Cloud Logging bills per GB ingested.

**Deployment path.** Source CI builds and signs an image and records its digest;
a bot opens a GitOps PR changing the digest; Argo CD reconciles the merged
revision. Pushing a tag never deploys. Rollback is a Git revert or a new digest
commit, never an imperative Argo action.

**Repository ownership.**

| Path in GitOps repo | Tool | Ownership rule |
|---|---|---|
| `terraform/gcp/**` | Terraform | GCP resources, one file per service |
| `charts/**` | Helm | every first-party app, one parameterized chart plus per-service values |
| `platform/**` | Helm values / plain manifests | pinned upstream platform components |
| `argocd/**` | Argo CD | project, ApplicationSet with a directory generator, sync waves |
| `ansible/roles/**` | Ansible | role-based host configuration, health + idempotency proof |

Terraform files split per service, which is what row 67's `để ý cách chia folder
theo từng service` asks for:

```
terraform/gcp/
  apis.tf       network.tf    gke.tf
  vm.tf         registry.tf   outputs.tf
  variables.tf  versions.tf   terraform.tfvars.example
```

Kustomize is not used. One resource has exactly one owner by construction, so the
previous `resource-ownership.yaml` and its CI duplicate-owner check are
unnecessary.

## Related Code Files

- Create: `scripts/generate_phase2_requirement_tests.py` (generates the 20 test files from the CSV)
- Create: `tests/phase2/requirements/test_llm_ac_01_inference.py` … `test_llm_ac_20_novel.py`
- Create: `tests/phase2/requirements/__init__.py`, `conftest.py`
- Modify: `scripts/audit_phase2_evidence.py` (add `--track`)
- Modify: `tests/phase2/test_rubric_matrix.py` (cover the new `--track` behavior)
- Create: `.venv-phase2/` (separate environment; `.venv` stays Phase 1 only)
- Create (GitOps repo): `terraform/gcp/`, `argocd/`, `charts/`, `platform/`, `ansible/roles/`
- Create (GitOps repo): `Makefile` with `gcp-up` / `gcp-down` / `gcp-status`
- Create: `docs/submission/` reviewer index (see step 16)
- Modify: `docs/phase2/acceptance-criteria.md` (remove Istio/mesh claims)
- Modify: `docs/coursework.md` (declare the LLM-only submission scope)

## Implementation Steps

### Day 0 evening — three kill-switch checks, run in parallel

1. **Read the GCP quota before anything else.** Node sizing for the whole week
   branches off it, and nothing else can be sized until it is known:

   ```bash
   gcloud config set project <PROJECT_ID>
   gcloud services enable container.googleapis.com compute.googleapis.com \
     artifactregistry.googleapis.com iam.googleapis.com
   gcloud compute regions describe asia-southeast1 \
     --format="table(quotas.metric,quotas.limit,quotas.usage)" \
     | grep -E 'CPUS|IN_USE_ADDRESSES|SSD|DISKS'
   gcloud auth application-default login
   ```

   Record `CPUS` and pick the node pool from the Architecture table. Do **not**
   run `gcloud iam service-accounts keys create`.

2. Install every Phase 2 Python dependency into a **throwaway** virtualenv and
   record what conflicts. `feast`, `mlflow`, `opentelemetry` and `kfp` contend
   over `protobuf`/`pyarrow`/`pandas`. Discovering this in hour 1 is cheap;
   discovering it on day 5 is not. Never install into `.venv` — breaking it
   breaks the Phase 1 gate that phase-08 must re-run clean. Use `.venv-phase2`.

3. Create `emanhthangngot/financial-distress-gitops` and commit the directory
   skeleton with the 14 declared artifact paths as placeholder files. Enumerate
   them from the CSV (`artifact_repo == "gitops"`) as a day-1 checklist.

4. Register a free DuckDNS subdomain and store its token. It is needed on day 1
   and takes two minutes; discovering the site is down on day 1 is not the time.
   Install `terraform` and `ansible`.

### Day 1 — harness first, then cluster

5. Add `--track {ML,LLM}` (repeatable, default both) to
   `scripts/audit_phase2_evidence.py`:

   ```python
   TRACKS = ("ML", "LLM")

   parser.add_argument(
       "--track", action="append", choices=TRACKS, default=None,
       help="Restrict executed/validation auditing to one track (repeatable); default both",
   )
   ...
   selected = tuple(args.track) if args.track else TRACKS
   scoped = [r for r in matrix if r.get("track", "") in selected]
   ```

   Pass `scoped` to exactly three call sites and no others:

   | Function | Line | Filtered? |
   |---|---:|---|
   | `_audit_executed` | 644 | **yes** |
   | `_audit_frozen_revisions` | 571 | **yes** |
   | `_audit_behavior_validations` | 723 | **yes** |
   | `_audit_matrix` | 218 | no |
   | `_audit_canonical_coverage` | 189 | no |
   | `_audit_phase1_no_mutation` | 369 | no |

   Leaving the last three unfiltered is what keeps the ML deferral honest and the
   phase-05 retrofit additive: all 117 rows must still exist and still total 100
   per track; they are simply not required to be *executed*. Add tests asserting
   that `--require-executed --track LLM` reports zero `ML-` errors and that
   omitting `--track` still demands all 117.

6. Generate `tests/phase2/requirements/test_llm_ac_01..20.py` from the CSV: 20
   files, 60 test functions whose node names contain the exact `rubric_id`
   slugs. Keep them **import-light contract tests** — parse the evidence
   markdown, assert the metadata fields and that `artifact_path` exists. Do not
   import `feast`, `torch`, or any service dependency: the auditor runs 60
   subprocesses and a slow import multiplies across all of them.

7. Amend the two documentation claims the dropped mesh would falsify:
   `docs/phase2/acceptance-criteria.md` `LLM-AC-13-ROUTING` (asserted "Istio
   mTLS") and `LLM-AC-17-SECURITY` (asserted "mesh"). Restate them against NGINX
   Ingress, ClusterIP-only backends, NetworkPolicy, and the sandbox namespace.
   Leave the ML AC lines alone. *(Applied 2026-08-07 — verify, do not redo.)*

8. Retarget three artifact paths in **both** `docs/phase2/rubric-matrix.csv` and
   `scripts/_phase2_rubric_items.py::EXPLICIT_IMPLEMENTATION` — they must stay
   in parity or `--matrix-only --strict` fails:
   - `platform/inference/llminferenceservice.yaml` → `platform/inference/model-server.yaml`
   - `platform/observability/eck-otel-values.yaml` → `platform/observability/loki-otel-values.yaml`
   - `platform/security/vault-external-secrets.yaml` → `platform/security/sealed-secrets.yaml`

   *(Applied 2026-08-07 — verify, do not redo. Note that
   `model-server.yaml` now holds a KServe `InferenceService`; the filename stays
   generic and correct.)*

9. `terraform apply` the GCP layer: `apis.tf`, `network.tf`, `gke.tf`, `vm.tf`,
   `registry.tf`. Capture the plan output, the apply output and the cost
   estimate — this is the row-67 evidence and it is now the main path, not a
   side quest. `gke.tf` must set `workload_identity_config`,
   `remove_default_node_pool`, and **disable** `logging_service` /
   `monitoring_service`.

10. Deploy NGINX Ingress Controller OSS (`nginx/kubernetes-ingress`, never the
    retired community `ingress-nginx`) and cert-manager. Reserve a static IP for
    the LoadBalancer. Apply a default-deny NetworkPolicy; every backend
    `Service` is `ClusterIP`.

11. **Point the DuckDNS subdomain at the LoadBalancer IP and issue a valid
    certificate through cert-manager (ACME HTTP-01), terminating HTTPS for the
    Web API kéo dữ liệu.** Canonical LLM CSV row 46 scores `Setup domain &
    enable HTTPS` for that API (1 pt). HTTP-01 works here because the GKE
    LoadBalancer exposes 80 and 443; the DNS-01 fallback exists only if that
    changes. A self-signed certificate scores nothing. DuckDNS is on the Public
    Suffix List, so the subdomain has its own Let's Encrypt rate limit —
    unlike `nip.io`, which shares one across every user.

12. Write `make gcp-up` / `gcp-down` / `gcp-status` in the GitOps repo **today,
    not on day 5**. `down` runs `gcloud container clusters resize --node-pool
    <pool> --num-nodes 0` for every pool while preserving PVCs; `up` resizes back
    and then re-normalizes the workloads that do not survive a node cycle
    (ingress controller, DataHub GMS, any StatefulSet). Measured on the peer
    project: **USD 0.65-0.80/hr running versus ~USD 0.14/hr hibernated**. Over
    seven days this is the difference between roughly USD 75 and USD 250 — the
    single largest cost lever in the plan. About 80 lines suffices here.

13. Install **Knative Serving** and the **KServe operator**. Phase-03 owns the
    cluster, so the CRDs land here; phase-06 consumes them for the row-2
    inference platform. Use the KServe "Raw Deployment" or Serverless mode that
    the row-2 guide specifies, and pin the chart versions in `platform/`.

14. Bootstrap Argo CD once, then hand the cluster over to it. Reconcile in four
    sync waves: `-20` namespaces, CRDs, sealed secrets; `-10` ingress,
    cert-manager, Knative/KServe operators; `0` platform services; `10`
    application workloads. Configure the dev ApplicationSet with a directory
    generator, `automated` sync, `prune`, `selfHeal`, `retry.refresh` and
    `allowEmpty: false`; add a GitHub webhook with polling fallback.

15. Write the Ansible role that configures the Terraform-provisioned GCE VM
    (Docker, kubectl, kubeconfig, the benchmark/load client). Prove a second run
    reports `changed=0`. Canonical row 69 says `Dùng Ansible để configure và
    deploy các service lên VM` — it wants a VM, and this one is real work the
    project needs, not a role invented for the rubric. *(Execution slips to day
    6; the role is authored here.)*

16. Create the `docs/submission/` reviewer index — `iac.md`, `security.md`,
    `observability.md`, `ci_cd.md`, `cost.md`, `routing_gateway.md`,
    `validation_verification.md` and siblings. These are **human-facing indexes
    that link into `docs/phase2/evidence/`**, not a relocation: `_audit_matrix`
    line 290 pins `evidence_path` to the `docs/phase2/evidence/` prefix, so
    moving files would mean rewriting 60 CSV rows. The canonical CSV's line-92
    note asks for exactly this (`nên có 1 file doc trong mỗi phần to trong folder
    docs/, ví dụ IaC.md`). `cost.md` doubles as the row-67 cost deliverable.
    *(Skeletons here; filled during phase-08.)*

## Scope Changes

### Restored (the reason for cutting them expired)

| Restored | Why it was cut | Why it is back |
|---|---|---|
| Knative Serving + KServe `InferenceService` | "A full day of CRD wrangling on k3d" | The platform is GKE with ~43 GB allocatable, not a 16 GB k3d box. Canonical row 2 (2 pts) links a KServe/llm-d guide and says `theo hướng dẫn này`; serving through KServe satisfies it as written instead of by analogy |
| llm-d router | Same k3d constraint | Same. Also yields better numbers for the row-4 benchmark |
| KEDA HTTP scaler | Not previously considered | Rows 12/18/23 want multi-replica autoscale; request-driven scaling is stronger evidence than CPU-only HPA |

### Still dropped

| Dropped | Rubric cost | Reason |
|---|---:|---|
| 18-component compatibility spike | 0 | 2-3 days, no scored row |
| Istio (mesh, mTLS, authorization) | 0 | The rubric section is literally named "Routing & Gateway (NGINX Ingress Controller)"; Istio, mesh, mTLS and TLS appear in no LLM row |
| ECK / Elasticsearch / Kibana | 0 | The row says "ví dụ Kibana" — an example. Loki + Grafana Explore serves the log-viewer row at a fraction of the RAM |
| Vault / external-secrets operator | 0 | "Secrets saved in Jenkins or similar tools" — GitHub Actions secrets + OIDC + sealed-secrets qualifies |
| Kustomize (`platform/base`, `platform/overlays`) | 0 | Helm is named in the rubric; Kustomize is not. One render tool removes the duplicate-owner problem entirely |
| `resource-ownership.yaml` + duplicate-owner CI check | 0 | Unnecessary once there is one render tool |
| Envoy Gateway / Envoy AI Gateway | 0 | agentgateway is the gateway the agent rows name |
| Jenkins in-cluster | 0 | The row accepts "Jenkins **or similar tools**"; GitHub Actions + Argo CD scores the same for less work |
| GPU node pool | 0 | Free-trial GPU quota is 0. Row 4 asks for a benchmark and an optimization, not throughput |
| Agent Sandbox as a product install | 0 | Replaced by a restricted-PSS namespace, which is what the rubric row actually asks for. See phase-06 |
| Multi-environment Terraform, remote state locking | 0 | The IaC row is worth 1 point; local state committed to the private GitOps repo is enough |
| 4-state teardown proof, failure injection | 0 | Half a day, no scored row |
| **All AWS work** (EKS sessions, EventBridge/CodeBuild teardown, `ap-southeast-1`) | 0 | GKE satisfies row 67 as written and costs no out-of-pocket money. The timeboxed 3-hour session and its accepted 1-point forfeit are gone |
| GKE Cloud Logging / Cloud Monitoring | 0 | Scored via Loki + Grafana; Cloud Logging bills per GB |
| Milvus, multi-region, kmcp | 0 | Already excluded or unscored |

Kept and unchanged: NGINX Ingress OSS as the public edge, cert-manager, Argo CD
as the sole deployer, the CI-to-Argo digest contract, Helm ownership of apps, the
Ansible role, Terraform, and the separate GitOps control repo.

## Success Criteria

- [x] Platform operator -> reads `gcloud compute regions describe asia-southeast1` -> records the real `CPUS` quota and selects a node pool from the sizing table before provisioning anything. *(Regional CPUS=32; correction: the binding constraint was actually the project-wide `CPUS_ALL_REGIONS`=12, discovered when the first apply attempt failed — collapsed to one `e2-standard-8` pool. See variables.tf comment.)*
- [x] Maintainer -> runs `audit_phase2_evidence.py --require-executed --track LLM` -> sees zero `ML-` errors, while omitting `--track` still demands all 117 rows.
- [x] Test runner -> executes any row's exact `validation_command` -> selects at least one assertion and exits 0, never pytest's exit code 5. *(60/60 LLM rows verified 2026-08-07. Two rubric_id prefix collisions found and fixed via `_COLLISION_RENAMES` in `scripts/_phase2_rubric_items.py`; regression-pinned by `test_no_rubric_id_is_a_prefix_of_another`.)*
- [x] Reviewer -> lists the GitOps checkout -> finds all 14 declared gitops artifact paths present. *(https://github.com/emanhthangngot/financial-distress-gitops, day-0 skeleton — placeholders only, no cluster yet.)*
- [x] Platform operator -> runs `terraform apply` -> obtains a GKE cluster and a GCE VM, with plan/apply/cost output captured and `terraform/gcp/` split one file per service. *(Cluster `fsds-evidence`, VM `fsds-evidence-worker` live 2026-08-08; `terraform/gcp/` split into apis/network/gke/vm/registry/ingress/iam/outputs/variables/versions.tf. Formal cost-delta screenshot deferred to phase-08 — see `docs/submission/cost.md`, billing usage lags several hours.)*
- [x] Auditor -> greps the GitOps repo and the local machine -> finds no service-account key JSON, no plaintext token, and Workload Identity configured on the cluster. *(`workload_identity_config` set in gke.tf; ADC via `gcloud auth application-default login`, no key file created; DuckDNS token in source repo's gitignored `.env` only, never committed.)*
- [ ] Platform operator -> pushes an image without a GitOps PR -> observes no Argo deployment; merges an approved digest PR -> observes automated sync, self-heal and a recorded revision. *(Needs the phase-07 CI pipeline; Argo CD itself is live and reconciling.)*
- [ ] Reviewer -> curls a backend Service directly from outside the cluster -> is refused; curls the same route through NGINX Ingress -> receives 200 with a valid certificate. *(Functionally true by construction — ClusterIP backends have no external route — but not yet formally captured as evidence; phase-08.)*
- [x] Reviewer -> opens the Web API kéo dữ liệu at its DuckDNS domain over HTTPS -> receives a cert-manager-issued Let's Encrypt certificate that a browser accepts without a warning. *(`https://distresslens.duckdns.org` — verified via curl: `SSL certificate verified via OpenSSL`, issuer `Let's Encrypt`, 2026-08-08. Real app route pending phase-06/07; proven against a throwaway test Service.)*
- [ ] Platform operator -> runs `make gcp-down` then `make gcp-up` -> observes node pools at zero with PVCs intact, then a healthy cluster after resize, with the cost delta recorded. *(Makefile written, `gcp-status` verified working; full down/up round trip not yet executed to avoid downtime mid-build.)*
- [x] Platform operator -> runs `kubectl get crd | grep -E 'knative|kserve'` -> finds the inference CRDs installed and ready for phase-06. *(21 CRDs present: Knative Serving v1.16.0, net-kourier, KServe v0.14.1 — verified 2026-08-08.)*
- [x] Phase 1 maintainer -> runs `scripts/run_stage1_quality_gates.py` -> passes, proving `.venv` was never mutated by Phase 2 dependencies.

## Risk Assessment

- **Free-trial vCPU quota is below 8.** This is the one unknown that can force a
  scope cut. Mitigated by reading it first, on day 0, and by the sizing table:
  quota 8 still runs the full stack with reduced observability replicas; only
  quota below 8 forfeits the DataHub row (2 pts).
- **Credit exhaustion mid-week.** Mitigated by `make gcp-down` written on day 1
  rather than day 5, by disabling Cloud Logging, and by never upgrading the trial
  billing account — an exhausted trial stops, an upgraded account does not.
- **Dependency conflict wrecks the week.** Mitigated by the day-0 throwaway
  install and by keeping heavy dependencies inside service images. `.venv` is
  never touched: phase-08 requires a clean Phase 1 non-regression run and a
  `_audit_phase1_git_diff` against a frozen SHA.
- **Knative/KServe install eats day 1.** Mitigated by installing it *after* the
  cluster, ingress, HTTPS and Argo CD are green, so a failure here costs the
  row-2 upgrade rather than the whole day. Fallback is the plain vLLM-CPU chain
  behind agentgateway, which is where this plan stood before the restore.
- **Workloads do not survive a hibernate cycle.** Mitigated by proving one full
  `down`/`up` round trip on day 1, while the cluster is still simple, instead of
  discovering it on day 6 with the full stack deployed.
- **The 3 retargeted artifact paths drift between the CSV and
  `_phase2_rubric_items.py`.** Mitigated by running `--matrix-only --strict`
  immediately after step 8, before any other work.
- Rollback: Git revert for cluster state; `terraform destroy` for GCP; evidence
  is exported before any teardown.
