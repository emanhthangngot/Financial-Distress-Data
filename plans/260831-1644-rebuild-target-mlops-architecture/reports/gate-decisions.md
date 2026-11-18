# Phase 0 GCP Current-State Report

**Initial baseline:** 2026-08-31  
**Updated:** 2026-09-03  
**Project:** `project-60655616-d84a-4883-867`  
**Active account:** `thcspl2018@gmail.com`  
**Scope:** Live inspection, quota-request submission, the user-directed start of the existing
evidence VM, and the user-approved GitOps default-branch switch from `master` to `main`. No
Terraform or Kubernetes apply was performed.

## Executive result

The project is at **G0 branch C / hard stop** for P4 and P6 because none of the requested quota
increases was granted; every request reports insufficient usage history. Current limits are
`CPUS_ALL_REGIONS=12`, regional
`CPUS=32`, legacy `E2_CPUS=8`, `PREEMPTIBLE_CPUS=0`, and `INSTANCES=8`. The quota API reports
project/regional CPU usage 1 after the existing `e2-medium` evidence VM was started; both GKE node
pools remain at zero. Terraform's intended warm baseline would consume 10 vCPU (one
`e2-standard-8` node plus the evidence VM), leaving only 2 project-wide quota vCPU and 8
Kubernetes-schedulable vCPU. The target always-on floor remains 13-18 vCPU.

The cluster still exposes three external `LoadBalancer` Services. The accepted target keeps only
NGINX external: the atomic `net-istio` cutover removes `net-kourier`, and agentgateway's generated
Service becomes `ClusterIP`. Both changes remain unapplied.

## Verified GCP configuration

| Surface | Current value | Plan implication |
|---|---|---|
| Active project | `project-60655616-d84a-4883-867` | Matches `terraform/gcp/terraform.tfvars` |
| Region / zone | `asia-southeast1` / `asia-southeast1-b` | Matches Terraform |
| Billing | Enabled; account `01DCB8-DBCF3D-13358B` | User screenshot records VND 5,548,358 remaining; USD is not displayed, so G1 is only partially closed |
| `CPUS_ALL_REGIONS` | limit 12, usage 1 | Requested 48; not granted |
| Regional `CPUS` | limit 32, usage 1 | Requested 48; not granted |
| `E2_CPUS` | legacy limit 8, usage 0 | Requested the separate VM-family quota at 48 through the Cloud Quotas API; not granted |
| `PREEMPTIBLE_CPUS` | limit 0, usage 0 | Requested 28; not granted |
| `INSTANCES` | limit 8, usage 1 | Requested 10; not granted |
| `GPUS_ALL_REGIONS` | limit 0, usage 0 | GPU work remains out of scope |
| `IN_USE_ADDRESSES` | project-wide limit 4, usage 3 | All three slots are consumed by external Kubernetes load balancers |
| GKE cluster | `fsds-evidence`, zonal Standard, `RUNNING` | Control plane exists; workload capacity is zero |
| Kubernetes version | `1.35.7-gke.1027000`, Regular channel | G4 version prerequisite (`>=1.33`) is satisfied; real injected-Job completion is still untested |
| Node pools | primary `e2-standard-8`, secondary `e2-standard-4`; both target size 0 | Matches intended hibernated state; node-pool CPU usage is zero |
| Spot/preemptible | false/null on both live pools | GitOps Terraform now plans `spot = true` on the secondary pool; no apply while G0 is branch C |
| Evidence VM | `fsds-evidence-worker`, `e2-medium`, `RUNNING` | Started at the user's request; IAP SSH and healthy system state verified |
| Recommended post-quota topology | primary: 2 x `e2-standard-8` = 16 vCPU; secondary maximum: 7 x Spot `e2-standard-4` = 28 vCPU; evidence VM: conservatively budgeted as 2 vCPU; total 46/48 | The 2-vCPU VM allocation is a deliberate worst-case budget; live shared-core quota charge is 1. The topology leaves at least 2 vCPU project-wide headroom; secondary stays at zero outside workload windows |
| Network | `fsds-evidence-vpc`, subnet `10.10.0.0/20`, pods `10.20.0.0/14`, services `10.30.0.0/20` | Matches Terraform |
| Network policy | Calico enabled | Required sandbox isolation control is present |
| Workload Identity | `project-60655616-d84a-4883-867.svc.id.goog` | Matches Terraform |
| Cloud Logging / Monitoring | both disabled | Matches cost-control design; in-cluster Loki/Prometheus remain the evidence owners |
| Cloud NAT | `fsds-evidence-nat`, automatic IP allocation, all subnet ranges | Present |
| Persistent disks | 58 GB total: 30 GB evidence VM + 28 GB PVC disks | Billable while nodes are zero; no deletion authorized by this audit |
| Resource labels | `phase=phase2`, `environment=evidence`, `project=financial-distress-data` | `phase=phase2` is stale for the unified target; plan must replace it with a phase-neutral label at the next Terraform apply |

## External load balancer baseline

| Service | External IP | Decision |
|---|---|---|
| `ingress-nginx/nginx-ingress-nginx-ingress-controller` | `34.21.242.110` | Keep: sole external entry point |
| `kourier-system/kourier` | `35.240.138.190` | Remove only as part of the atomic `net-istio` cutover |
| `agentgateway-system/agentgateway-proxy` | `136.85.22.129` | GitOps parameters are schema-valid for `ClusterIP`; controller behavior remains unverified until reconciliation |

The plan's former acceptance criterion “external LoadBalancer count unchanged from pre-P6” was unsafe because the measured pre-P6 baseline is three. The correct invariant is **exactly one external `LoadBalancer` Service cluster-wide before P4 or P6 and throughout P6-P9**.

## Platform baseline

| Component | Current state | Gate impact |
|---|---|---|
| KServe | controller image `kserve/kserve-controller:v0.14.1` | G3 target 0.18 is not installed |
| `InferenceService` CRD | present | Existing serving path remains represented in API state |
| `LLMInferenceService` CRD | absent | G3 0.18 install test still required |
| Gateway API `Gateway` CRD | present | Partial prerequisite only |
| LeaderWorkerSet CRD | absent | G3 prerequisite still required |
| Knative Serving | installed with net-kourier | Accepted target replaces it with `net-istio`; the atomic cutover is blocked on capacity |
| Kubernetes nodes | none | No live workload/Job test can run until a node pool is raised |
| Argo CD | Applications remain `Synced`; two agent apps show `Progressing` | Health is not runtime proof while no nodes exist |

## Gate status

| Gate | Status | Evidence / next action |
|---|---|---|
| G0 quota bundle | **BRANCH C / HARD STOP** | None of the five quota preferences was granted; each reports `NOT_ENOUGH_USAGE_HISTORY`. P4 and P6 are blocked; source-only P1-P3 may proceed. |
| G1 cost | **PARTIAL** | Dated screenshot records VND 5,548,358 remaining and expiry 2026-11-06. USD is not displayed, so no USD branch is inferred. |
| G2a Spot | **PLANNED / NOT APPLIED** | Terraform sets the existing secondary pool to `spot = true`; validation and reviewed plan pass. The plan replaces that pool and makes four in-place label updates. `gcp-up` cannot raise the secondary pool until preemptible CPU quota is granted. G0 branch C prohibits apply. |
| G2b network cost | **PLANNED / NOT APPLIED** | Agentgateway parameters are schema-valid in server dry-run; controller behavior is unverified and AC-P0-5 stays open. First sync must adopt the live Gateway, which lacks the last-applied annotation. The required atomic Kourier-to-`net-istio` cutover is blocked on capacity; three external LBs remain live. |
| G3 KServe 0.18 | **NOT READY** | KServe 0.14.1 live; `LLMInferenceService` and LeaderWorkerSet CRDs absent. Run the planned 0.18 compatibility check after capacity is available. |
| G4 native sidecars | **PARTIAL PASS** | Kubernetes 1.35.7 satisfies the version prerequisite; injected Job completion is untested because node count is zero. |
| G5 vLLM CPU | **UNTESTED** | No node capacity; benchmark has not run. |
| G6 Knative net layer | **DECIDED / NOT APPLIED** | Target is `net-istio`; `net-kourier` removal waits for the atomic, capacity-backed cutover. |

## Commands used as evidence

- `gcloud auth list --filter=status:ACTIVE`
- `gcloud config list --format=json`
- `gcloud compute project-info describe --format=json`
- `gcloud compute regions describe asia-southeast1 --format=json`
- `gcloud container clusters describe fsds-evidence --zone asia-southeast1-b --format=json`
- `gcloud container node-pools list --cluster fsds-evidence --zone asia-southeast1-b --format=json`
- `gcloud compute instances list`
- `gcloud compute instance-groups managed list`
- `gcloud compute forwarding-rules list`
- `gcloud compute disks list`
- `gcloud billing projects describe project-60655616-d84a-4883-867`
- `gcloud beta quotas preferences create ...`
- `gcloud beta quotas preferences list ...`
- `gcloud compute instances start fsds-evidence-worker --zone asia-southeast1-b`
- `gcloud compute ssh fsds-evidence-worker --zone asia-southeast1-b --tunnel-through-iap ...`
- `kubectl get svc -A --field-selector spec.type=LoadBalancer`
- `kubectl get nodes`
- `kubectl get crd ...`
- `gh repo view emanhthangngot/financial-distress-gitops --json defaultBranchRef`
- `gh repo edit emanhthangngot/financial-distress-gitops --default-branch main`

## Required plan reconciliation

1. Distinguish the live quota API usage after the evidence VM start from **warm Terraform demand
   10** and **Kubernetes-schedulable demand 8**.
2. Treat G0 as a quota bundle. A `CPUS_ALL_REGIONS` increase alone is insufficient while `E2_CPUS=8` and `PREEMPTIBLE_CPUS=0`.
3. Use the 46-vCPU recommended topology after approval: two on-demand `e2-standard-8` primary nodes, up to seven Spot `e2-standard-4` secondary nodes, and the existing `e2-medium` evidence VM; keep secondary at zero outside workload windows.
4. Add a blocking Phase 0 network-cost control: reduce external LoadBalancer Services from 3 to exactly 1 before P4 or P6.
5. Replace the P6 “unchanged from pre-P6” load-balancer criterion with “exactly one cluster-wide and no increase.”
6. Record Kubernetes `1.35.7-gke.1027000` as the measured G4 version baseline; keep injected-Job completion open.
7. Add cleanup of stale GCP label `phase=phase2` to a phase-neutral unified-platform label at the next Terraform apply.
8. Keep G1 partial unless a dated source supplies USD credit or the project accepts VND-only
   evidence; never infer a currency conversion.

## Billing Console evidence

**Captured:** 2026-09-03 from the user-provided Google Cloud Console screenshot.

| Surface | Value |
|---|---:|
| Project | `project-60655616-d84a-4883-867` |
| Credit allowance | VND 7,897,351 |
| Credit used | VND 2,348,993 |
| Remaining credit | **VND 5,548,358** |
| Expiry | 2026-11-06 |

The screenshot exposes credit in VND only; no USD conversion is displayed. G1 therefore has a
dated VND measurement but remains partially open until the plan's USD value is recorded or the
project explicitly accepts VND-only evidence.

## VM state update

**Measured:** 2026-09-03 via `gcloud compute instances describe`.

`fsds-evidence-worker` is now **RUNNING**, machine type `e2-medium`, internal IP `10.10.0.2`.
Measured project-wide and regional CPU quota usage rose from 0 to 1: `e2-medium` exposes two guest
CPUs but is a shared-core machine whose quota charge is 1. The GKE node pools remain scaled to zero;
no Terraform or Kubernetes apply was performed.

## Live routing verification

**Measured:** 2026-09-03 via `kubectl`.

- `kourier-system/kourier` is `LoadBalancer` at `35.240.138.190`.
- `agentgateway-system/agentgateway-proxy` is `LoadBalancer` at `136.85.22.129`.
- `ingress-nginx/nginx-ingress-nginx-ingress-controller` is `LoadBalancer` at `34.21.242.110`.
- The cluster therefore still has **three** external LoadBalancer Services.
- The live `Gateway/agentgateway-proxy` is programmed with address `136.85.22.129`.
- The live `knative-serving/config-network` selects
  `kourier.ingress.networking.knative.dev`.
- Existing NGINX Ingress objects route UI, feature API and observability paths; no live
  NGINX route to `kourier.kourier-system` was found.

The accepted target replaces `net-kourier` with `net-istio`; it does not preserve Kourier behind
NGINX. Live state still carries the obsolete Kourier layer because the `net-istio` cutover has not
executed. Agentgateway's generated proxy Service also remains external until the reviewed GitOps
change is merged and reconciled; its `AgentgatewayParameters` configuration has passed server
dry-run without mutating the live resource.

## Terraform plan evidence

**Measured:** 2026-09-03 from `terraform/envs/evidence`.

- `terraform init -reconfigure -input=false` completed successfully.
- `terraform validate` passed for both the evidence root module and `terraform/gcp`.
- `terraform plan -input=false -lock=false -var-file=../../gcp/terraform.tfvars` reported
  `1 to add, 4 to change, 1 to destroy`.
- The add/destroy pair is the expected replacement of the secondary node pool when
  `node_config.spot` changes from `false` to `true`; it was reviewed but not applied.
- The shared label map reaches five resources: cluster, primary pool, replacement secondary pool,
  Artifact Registry, and evidence VM. The four existing non-replaced resources update in place.


## GitOps branch transition

**Measured:** 2026-09-03 via GitHub and repository search.

- The user selected `main` as the GitOps PR target.
- GitHub's default branch was switched from `master` to `main` after both remote branches were
  confirmed at the same commit.
- Every active Argo CD `targetRevision` under `argocd/` now points to `main`.
- One `targetRevision: master` remains only in
  `archive/ml-track/argocd/applications/platform-data-phase1.yaml`; the archive is not reconciled.
- The validation workflow already listens to both `main` and `master`.

## Current quota query

**Measured:** 2026-09-03 via `gcloud compute project-info describe` and
`gcloud compute regions describe asia-southeast1`.

| Metric | Limit | Usage |
|---|---:|---:|
| `CPUS_ALL_REGIONS` | 12 | 1 |
| regional `CPUS` | 32 | 1 |
| `E2_CPUS` | 8 | 0 |
| `PREEMPTIBLE_CPUS` | 0 | 0 |
| `INSTANCES` | 8 | 1 |

The quota bundle remains below the P0 target (`48`, `48`, `48`, `28`, `10`). Starting the
evidence VM did not change the hard quota limits and did not start either GKE node pool.

## SSH verification

**Measured:** 2026-09-03 via IAP SSH.

The operator connected to `fsds-evidence-worker`; the host reported
`Linux 6.1.0-52-cloud-amd64` and `systemctl is-system-running` returned `running`.

## Quota request outcomes

**Submitted:** 2026-09-03 through the Cloud Quotas API using the active project account.

| Preference ID | Requested | Granted API value | Outcome |
|---|---:|---:|---|
| `fdd-cpus-all-regions-48` | 48 | 12 | not granted; current limit retained |
| `fdd-cpus-asia-southeast1-48` | 48 | 32 | not granted; current limit retained |
| `fdd-e2-cpus-asia-southeast1-48` | 48 | 0 | not granted; this is the separate VM-family quota, not legacy `E2_CPUS=8` |
| `fdd-preemptible-cpus-asia-southeast1-28` | 28 | 0 | not granted; current limit retained |
| `fdd-instances-asia-southeast1-10` | 10 | 8 | not granted; current limit retained |

Every quota resource reports `quotaIncreaseEligibility.ineligibilityReason =
NOT_ENOUGH_USAGE_HISTORY`. G0 is therefore **branch C / hard stop** for P4 and P6. P1-P3 remain
source-only and may proceed.
