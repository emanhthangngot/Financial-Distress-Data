# Remaining Production Gaps — Gate Ledger

**Captured:** 2026-09-15T01:32:11+07:00
**Phase:** Gap 01 — Reconfirm gates and inventory
**Source revision:** `5f35d08` (local `dev` at refresh)
**Evidence baseline:** `evidence-baseline-pre-rebuild` resolves locally

## Status

| Gate | Status | Evidence | Owner / next action |
|---|---|---|---|
| Baseline tag | PASS | `git tag -l evidence-baseline-pre-rebuild` resolved | Evidence owner: retain tag and existing evidence |
| Billing/spend controls | BLOCKED | Billing is enabled for project `project-60655616-d84a-4883-867`, account currency is VND, and the active account grants this user `roles/billing.admin`; the enabled Budget API lists no budgets. User-provided Cloud Billing screenshot for the last 90 days shows net subtotal/total `₫0` after savings, with gross usage about `₫6,089,726`; it does not establish a hard future spend ceiling, approved window, residual credit, teardown inventory or backup/export destination | Operator: configure a hard spend ceiling/alert and record the approved window before any paid-capacity action |
| Project-wide CPU capacity | BLOCKED | `CPUS_ALL_REGIONS=12`, usage `9`; `GPUS_ALL_REGIONS=0`, usage `0`; forwarding-rule usage includes external network LBs | Platform owner: obtain approved quota/no-spend window before capacity-backed phases |
| Regional CPU capacity | BLOCKED | `asia-southeast1`: `CPUS=32`, usage `8` after stopping the evidence VM; `E2_CPUS=8`, usage `0`; `PREEMPTIBLE_CPUS=0`, usage `0`; `INSTANCES=8`, usage `2` | Platform owner: obtain approved quota/no-spend window before capacity-backed phases |
| Kubernetes capacity | BLOCKED | One Ready `e2-standard-8` node remains running; `fsds-evidence-worker` is now `TERMINATED`, with its 30-GB persistent disk `READY` and still attached; node remains billable and violates the documented between-session hibernation invariant | Platform owner: record authorization/window and teardown deadline; hibernate the node pool in a controlled operator action if no approved window exists |
| External load balancers | BLOCKED | Direct deletion of `kourier-system/kourier` was immediately reconciled by Argo; it returned as `LoadBalancer` with pending IP, then GCP allocated `35.198.214.133`; NGINX remains `34.21.242.110`; two external forwarding rules remain | GitOps/platform owner: change the source manifest in `financial-distress-gitops` to the approved non-external type, reconcile Argo, then verify exactly one external entry point |
| Jenkins host/controller | UNVERIFIED | `fsds-evidence-worker` and one GKE node are RUNNING; no Jenkins health/controller inspection was performed; no root `Jenkinsfile` exists | Platform owner: identify or provision the approved controller, JCasC, backup and ephemeral-agent proof |
| Provider access/limits | UNVERIFIED | No fresh Groq/Gemini/provider capability or quota check was performed | ML/agent owner: measure allowed free providers before pinning or evaluating models |
| LangGraph runtime | UNVERIFIED | No checked-in LangGraph/LangChain implementation found in current source inventory | ML/agent owner: implement and measure parity before cutover |
| Domain/HTTPS | UNVERIFIED | No fresh domain certificate/edge exercise was run in this local gate refresh | Serving owner: capture trusted HTTPS and auth/rate-limit evidence |
| Kaggle/GPU capacity | UNVERIFIED | No Kaggle job or GPU capacity exercise was run in this refresh | ML owner: run only after access and spend controls are verified |

## Inventory reconciliation

- Baseline tag still resolves; no evidence tree was deleted.
- Existing prior gate evidence remains historical and is not relabeled as current proof.
- Cleanup result: `fsds-evidence-worker` is `TERMINATED`; its persistent disk remains `READY` and attached.
- Direct Kourier Service deletion was not durable because `platform-inference` has automated sync/self-heal from `financial-distress-gitops` `platform/inference`; the Service was recreated and the external rule remains.
- Current cluster has one Ready `e2-standard-8` node, NGINX external entrypoint `34.21.242.110`, and a recreated Kourier LoadBalancer currently using `35.198.214.133`.
- The accepted baseline inventory remains 161 rubric rows / 300 points: 60 executed, 57 design-only, and 44 pending. This refresh did not produce a row-level stale/recapture list; that criterion remains open.

## Resource safety

No new billable resource was created. The approved evidence VM was stopped without deleting its persistent disk. A direct Kourier Service deletion was attempted under explicit authorization but was reverted by Argo self-heal; no repeated destructive deletion will be attempted. One GKE node and two external forwarding rules remain active; approved spend ceiling, teardown deadline, backup/export path and desired-state GitOps cleanup remain unverified.


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

## Phase result

The dated inventory refresh is current and evidence-backed for identity, billing-enabled state, quota values, running resources and LoadBalancer state. Phase 01 remains **BLOCKED/PARTIAL** because approved spend controls, teardown/backup controls, provider access, Jenkins-host state, domain/HTTPS, Kaggle capacity and row-level stale/recapture reconciliation were not proven. No production-ready claim is made.
