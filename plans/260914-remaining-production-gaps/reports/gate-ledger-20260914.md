# Remaining Production Gaps — Gate Ledger

**Captured:** 2026-09-15T01:32:11+07:00
**Phase:** Gap 01 — Reconfirm gates and inventory
**Source revision:** `5f35d08` (local `dev` at refresh)
**Evidence baseline:** `evidence-baseline-pre-rebuild` resolves locally

## Status

| Gate | Status | Evidence | Owner / next action |
|---|---|---|---|
| Baseline tag | PASS | `git tag -l evidence-baseline-pre-rebuild` resolved | Evidence owner: retain tag and existing evidence |
| Billing/spend controls | BLOCKED | Billing enabled for `project-60655616-d84a-4883-867`, currency VND, user holds `roles/billing.admin`. Cloud Billing report for the last 90 days shows net subtotal/total `₫0` after savings with gross usage about `₫6,089,726`. A monthly budget `fsds-evidence-guardrail` now exists (`last-period` amount, alert thresholds 50/90/100%), but an alert is not a hard cap and no approved window, teardown deadline, residual credit or backup/export destination is recorded | Operator: record the approved window, teardown deadline and backup/export destination; decide whether a fixed ceiling replaces the last-period amount |
| Project-wide CPU capacity | BLOCKED | `CPUS_ALL_REGIONS=12`, usage `9`; `GPUS_ALL_REGIONS=0`, usage `0`; forwarding-rule usage includes external network LBs | Platform owner: obtain approved quota/no-spend window before capacity-backed phases |
| Regional CPU capacity | BLOCKED | `asia-southeast1`: `CPUS=32`, usage `8` after stopping the evidence VM; `E2_CPUS=8`, usage `0`; `PREEMPTIBLE_CPUS=0`, usage `0`; `INSTANCES=8`, usage `2` | Platform owner: obtain approved quota/no-spend window before capacity-backed phases |
| Kubernetes capacity | BLOCKED | One Ready `e2-standard-8` node remains running; `fsds-evidence-worker` is now `TERMINATED`, with its 30-GB persistent disk `READY` and still attached; node remains billable and violates the documented between-session hibernation invariant | Platform owner: record authorization/window and teardown deadline; hibernate the node pool in a controlled operator action if no approved window exists |
| External load balancers | PASS | GitOps commit `ae79945` set `kourier-system/kourier` to `ClusterIP`; Argo synced revision `ae79945` and the live Service type is `ClusterIP`. Cluster now reports exactly one external `LoadBalancer` (`ingress-nginx` at `34.21.242.110`) and exactly one external forwarding rule | Platform owner: keep NGINX as the sole external entry point |
| Jenkins host/controller | UNVERIFIED | `fsds-evidence-worker` and one GKE node are RUNNING; no Jenkins health/controller inspection was performed; no root `Jenkinsfile` exists | Platform owner: identify or provision the approved controller, JCasC, backup and ephemeral-agent proof |
| Provider access/limits | UNVERIFIED | No fresh Groq/Gemini/provider capability or quota check was performed | ML/agent owner: measure allowed free providers before pinning or evaluating models |
| LangGraph runtime | UNVERIFIED | No checked-in LangGraph/LangChain implementation found in current source inventory | ML/agent owner: implement and measure parity before cutover |
| Domain/HTTPS | UNVERIFIED | No fresh domain certificate/edge exercise was run in this local gate refresh | Serving owner: capture trusted HTTPS and auth/rate-limit evidence |
| Kaggle/GPU capacity | UNVERIFIED | No Kaggle job or GPU capacity exercise was run in this refresh | ML owner: run only after access and spend controls are verified |

## Inventory reconciliation

- Baseline tag still resolves; no evidence tree was deleted.
- Existing prior gate evidence remains historical and is not relabeled as current proof.
- Cleanup result: `fsds-evidence-worker` is `TERMINATED`; its persistent disk remains `READY` and attached.
- Durable Kourier cutover: the earlier direct Service deletion was reverted by Argo self-heal, so the desired state in `financial-distress-gitops` was changed to `ClusterIP` instead; Argo reconciled and the external rule was released.
- Current cluster has one Ready `e2-standard-8` node and a single external entry point `34.21.242.110`; `kourier-internal` remains `ClusterIP` for in-cluster Knative routing.
- The accepted baseline inventory remains 161 rubric rows / 300 points: 60 executed, 57 design-only, and 44 pending. This refresh did not produce a row-level stale/recapture list; that criterion remains open.

## Resource safety

No new billable resource was created. The approved evidence VM was stopped without deleting its persistent disk. The redundant external load balancer was removed through desired state, releasing one forwarding rule and its ephemeral address. A monthly budget guardrail with 50/90/100% alert thresholds was created. One GKE node remains running; approved window, teardown deadline and backup/export destination remain unrecorded.


## Commands exercised

- `date --iso-8601=seconds`
- `git tag -l evidence-baseline-pre-rebuild`
- `git rev-parse --short HEAD`
- `gcloud auth list --filter=status:ACTIVE`
- `gcloud billing projects describe project-60655616-d84a-4883-867`
- `gcloud compute project-info describe`
- `gcloud compute regions describe asia-southeast1`
- `gcloud beta billing accounts describe 01DCB8-DBCF3D-13358B`
- `gcloud billing budgets list --billing-account=01DCB8-DBCF3D-13358B` (pass: no budgets configured)
- `gcloud container clusters list`
- `gcloud compute instances list`
- `kubectl get nodes -o wide`
- `kubectl get svc -A --field-selector spec.type=LoadBalancer -o wide`
- repository inventory for `Jenkinsfile`, Jenkins, LangChain and LangGraph surfaces
- `gcloud billing budgets create --billing-account=01DCB8-DBCF3D-13358B --display-name=fsds-evidence-guardrail --last-period-amount --threshold-rule=percent=0.5/0.9/1.0`
- `gcloud compute forwarding-rules list`, `gcloud compute addresses list`
- GitOps edit + push: `platform/inference/vendored/03-net-kourier.yaml` → `ClusterIP` (`ae79945`)

## Phase result

The dated inventory refresh is current and evidence-backed. Two gates are now closed: the baseline tag, and the single-external-entry-point invariant. Phase 01 remains **BLOCKED/PARTIAL** because an approved window, teardown deadline and backup/export destination are unrecorded, the GKE node is still running, and provider access, Jenkins host, domain/HTTPS, Kaggle capacity and row-level stale/recapture reconciliation are unproven. No production-ready claim is made.
