# Phase 0 GCP Current-State Report

**Measured:** 2026-08-31  
**Project:** `project-60655616-d84a-4883-867`  
**Active account:** `thcspl2018@gmail.com`  
**Scope:** Read-only inspection. No GCP, Kubernetes, Terraform, or billing setting was mutated.

## Executive result

The project remains blocked for the target architecture by a **quota bundle**, not only the project-wide CPU quota. Verified limits are: `CPUS_ALL_REGIONS=12`, regional `CPUS=32`, `E2_CPUS=8`, `PREEMPTIBLE_CPUS=0`, and `INSTANCES=8`. Current CPU usage is 0 because both GKE node pools are scaled to zero and the evidence VM is terminated; this does **not** mean the target fits. Terraform's intended warm baseline would consume 10 vCPU (one `e2-standard-8` node plus the `e2-medium` evidence VM), leaving only 2 project-wide quota vCPU and 8 Kubernetes-schedulable vCPU. The target always-on floor remains 13-18 vCPU.

A second immediate cost/configuration defect is live: the cluster currently exposes three external `LoadBalancer` Services. Only NGINX should remain external. Kourier and agentgateway must be converted to `ClusterIP` through GitOps before the rebuild proceeds.

## Verified GCP configuration

| Surface | Current value | Plan implication |
|---|---|---|
| Active project | `project-60655616-d84a-4883-867` | Matches `terraform/gcp/terraform.tfvars` |
| Region / zone | `asia-southeast1` / `asia-southeast1-b` | Matches Terraform |
| Billing | Enabled; account `01DCB8-DBCF3D-13358B` | Remaining credit cannot be read with current CLI access; manual Billing Console snapshot still required |
| `CPUS_ALL_REGIONS` | limit 12, usage 0 | Raise to >=48; project-wide blocker |
| Regional `CPUS` | limit 32, usage 0 | Raise to >=48 if the full 46-vCPU recommended topology remains in `asia-southeast1` |
| `E2_CPUS` | limit 8, usage 0 | Raise to >=48 if retaining the current E2 machine family |
| `PREEMPTIBLE_CPUS` | limit 0, usage 0 | Raise to >=28 for the recommended seven-node `e2-standard-4` Spot window; current value blocks every Spot node |
| `INSTANCES` | limit 8, usage 1 | Raise to >=10 for two primary nodes, up to seven Spot nodes, and the evidence VM |
| `GPUS_ALL_REGIONS` | limit 0, usage 0 | GPU work remains out of scope |
| `IN_USE_ADDRESSES` | project-wide limit 4, usage 3 | All three slots are consumed by external Kubernetes load balancers |
| GKE cluster | `fsds-evidence`, zonal Standard, `RUNNING` | Control plane exists; workload capacity is zero |
| Kubernetes version | `1.35.7-gke.1027000`, Regular channel | G4 version prerequisite (`>=1.33`) is satisfied; real injected-Job completion is still untested |
| Node pools | primary `e2-standard-8`, secondary `e2-standard-4`; both target size 0 | Matches intended hibernated state; live CPU usage is zero |
| Spot/preemptible | false/null on both pools | G2 is not ready; secondary pool needs `spot = true` in Terraform |
| Evidence VM | `fsds-evidence-worker`, `e2-medium`, `TERMINATED` | Disk remains billable; VM consumes no CPU quota while stopped |
| Recommended post-quota topology | primary: 2 x `e2-standard-8` = 16 vCPU; secondary maximum: 7 x Spot `e2-standard-4` = 28 vCPU; evidence VM: 2 vCPU; total 46/48 | Fits the 13-18 vCPU always-on floor and leaves 2 vCPU project-wide headroom; secondary stays at zero outside workload windows |
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
| `kourier-system/kourier` | `35.240.138.190` | Convert to `ClusterIP` through GitOps |
| `agentgateway-system/agentgateway-proxy` | `136.85.22.129` | Configure controller/Gateway output as `ClusterIP` through GitOps |

The plan's former acceptance criterion “external LoadBalancer count unchanged from pre-P6” was unsafe because the measured pre-P6 baseline is three. The correct invariant is **exactly one external `LoadBalancer` Service cluster-wide before P2 and throughout P6-P9**.

## Platform baseline

| Component | Current state | Gate impact |
|---|---|---|
| KServe | controller image `kserve/kserve-controller:v0.14.1` | G3 target 0.18 is not installed |
| `InferenceService` CRD | present | Existing serving path remains represented in API state |
| `LLMInferenceService` CRD | absent | G3 0.18 install test still required |
| Gateway API `Gateway` CRD | present | Partial prerequisite only |
| LeaderWorkerSet CRD | absent | G3 prerequisite still required |
| Knative Serving | installed with net-kourier | Current Kourier Service is external and must become internal |
| Kubernetes nodes | none | No live workload/Job test can run until a node pool is raised |
| Argo CD | Applications remain `Synced`; two agent apps show `Progressing` | Health is not runtime proof while no nodes exist |

## Gate status

| Gate | Status | Evidence / next action |
|---|---|---|
| G0 quota bundle | **BLOCKED / open** | Raise `CPUS_ALL_REGIONS` 12->48, regional `CPUS` 32->48, `E2_CPUS` 8->48, `PREEMPTIBLE_CPUS` 0->28, and `INSTANCES` 8->10; record request ticket and approval/refusal. P2+ remain blocked. |
| G1 cost | **OPEN** | Billing enabled, but current credit is not CLI-readable. Current account lacks usable Cloud Billing Budget API access. Take a dated Billing Console snapshot. |
| G2 spot | **NOT READY** | Secondary pool exists but is not Spot. Add `spot = true` in Terraform; validate plan. |
| G2 network cost | **NOT READY** | Three external LBs are live. Convert Kourier and agentgateway to `ClusterIP`; verify exactly one remains. |
| G3 KServe 0.18 | **NOT READY** | KServe 0.14.1 live; `LLMInferenceService` and LeaderWorkerSet CRDs absent. Run the planned 0.18 compatibility check after capacity is available. |
| G4 native sidecars | **PARTIAL PASS** | Kubernetes 1.35.7 satisfies the version prerequisite; injected Job completion is untested because node count is zero. |
| G5 vLLM CPU | **UNTESTED** | No node capacity; benchmark has not run. |

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
- `kubectl get svc -A --field-selector spec.type=LoadBalancer`
- `kubectl get nodes`
- `kubectl get crd ...`

## Required plan reconciliation

1. Distinguish **current usage 0** from **warm Terraform demand 10** and **Kubernetes-schedulable demand 8**.
2. Treat G0 as a quota bundle. A `CPUS_ALL_REGIONS` increase alone is insufficient while `E2_CPUS=8` and `PREEMPTIBLE_CPUS=0`.
3. Use the 46-vCPU recommended topology after approval: two on-demand `e2-standard-8` primary nodes, up to seven Spot `e2-standard-4` secondary nodes, and the existing `e2-medium` evidence VM; keep secondary at zero outside workload windows.
4. Add a blocking Phase 0 network-cost control: reduce external LoadBalancer Services from 3 to exactly 1 before P2.
5. Replace the P6 “unchanged from pre-P6” load-balancer criterion with “exactly one cluster-wide and no increase.”
6. Record Kubernetes `1.35.7-gke.1027000` as the measured G4 version baseline; keep injected-Job completion open.
7. Add cleanup of stale GCP label `phase=phase2` to a phase-neutral unified-platform label at the next Terraform apply.
8. Keep G1 unresolved until a dated Billing Console snapshot supplies remaining credit.
