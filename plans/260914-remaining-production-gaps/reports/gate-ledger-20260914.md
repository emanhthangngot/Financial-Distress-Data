# Remaining Production Gaps — Gate Ledger

**Captured:** 2026-09-15T01:32:11+07:00
**Phase:** Gap 01 — Reconfirm gates and inventory
**Source revision:** `5f35d08` (local `dev` at refresh)
**Evidence baseline:** `evidence-baseline-pre-rebuild` resolves locally

## Status

| Gate | Status | Evidence | Owner / next action |
|---|---|---|---|
| Baseline tag | PASS | `git tag -l evidence-baseline-pre-rebuild` resolved | Evidence owner: retain tag and existing evidence |
| Billing/spend controls | BLOCKED | Billing is enabled for project `project-60655616-d84a-4883-867`; this refresh did not retrieve residual credit, approved window, teardown inventory, backup/export destination, or a hard spend-control result | Operator: stop unapproved capacity, refresh allocation and lifecycle controls before any paid-capacity action |
| Project-wide CPU capacity | BLOCKED | `CPUS_ALL_REGIONS=12`, usage `9`; `GPUS_ALL_REGIONS=0`, usage `0`; forwarding-rule usage includes external network LBs | Platform owner: obtain approved quota/no-spend window before capacity-backed phases |
| Regional CPU capacity | BLOCKED | `asia-southeast1`: `CPUS=32`, usage `9`; `E2_CPUS=8`, usage `0`; `PREEMPTIBLE_CPUS=0`, usage `0`; `INSTANCES=8`, usage `2` | Platform owner: obtain approved quota/no-spend window before capacity-backed phases |
| Kubernetes capacity | BLOCKED | One Ready `e2-standard-8` node and the `fsds-evidence-worker` `e2-medium` VM are RUNNING; this violates the documented between-session hibernation invariant and consumes quota/credit | Platform owner: record authorization/window and teardown deadline; hibernate in a controlled operator action if no approved window exists |
| External load balancers | BLOCKED | Live cluster still reports NGINX `34.21.242.110` and Kourier `35.240.138.190` `LoadBalancer` services; regional quota reports `EXTERNAL_NETWORK_LB_FORWARDING_RULES=2` | Platform owner: reconcile reviewed GitOps revision and GCP forwarding-rule/address state before network-cost closure |
| Jenkins host/controller | UNVERIFIED | `fsds-evidence-worker` and one GKE node are RUNNING; no Jenkins health/controller inspection was performed; no root `Jenkinsfile` exists | Platform owner: identify or provision the approved controller, JCasC, backup and ephemeral-agent proof |
| Provider access/limits | UNVERIFIED | No fresh Groq/Gemini/provider capability or quota check was performed | ML/agent owner: measure allowed free providers before pinning or evaluating models |
| LangGraph runtime | UNVERIFIED | No checked-in LangGraph/LangChain implementation found in current source inventory | ML/agent owner: implement and measure parity before cutover |
| Domain/HTTPS | UNVERIFIED | No fresh domain certificate/edge exercise was run in this local gate refresh | Serving owner: capture trusted HTTPS and auth/rate-limit evidence |
| Kaggle/GPU capacity | UNVERIFIED | No Kaggle job or GPU capacity exercise was run in this refresh | ML owner: run only after access and spend controls are verified |

## Inventory reconciliation

- Baseline tag still resolves; no evidence tree was deleted.
- Existing prior gate evidence remains historical and is not relabeled as current proof.
- Current refresh confirms billing enabled, one Ready GKE `e2-standard-8` node, one RUNNING evidence VM, two external LoadBalancer services, and regional CPU usage of 9.
- Current repository inventory still contains no root `Jenkinsfile` and no production LangGraph/LangChain implementation; the only matching tracked path is a historical plan file.
- The accepted baseline inventory remains 161 rubric rows / 300 points: 60 executed, 57 design-only, and 44 pending. This refresh did not produce a row-level stale/recapture list; that criterion remains open.

## Resource safety

No Terraform apply, Kubernetes mutation, quota request, paid API call, or new billable resource was performed by this refresh. Billing is enabled and running resources remain; approved-window, teardown, backup/export, residual-cost, provider, domain/HTTPS and Kaggle controls remain unverified.


## Commands exercised

- `date --iso-8601=seconds`
- `git tag -l evidence-baseline-pre-rebuild`
- `git rev-parse --short HEAD`
- `gcloud auth list --filter=status:ACTIVE`
- `gcloud billing projects describe project-60655616-d84a-4883-867`
- `gcloud compute project-info describe`
- `gcloud compute regions describe asia-southeast1`
- `gcloud container clusters list`
- `gcloud compute instances list`
- `kubectl get nodes -o wide`
- `kubectl get svc -A --field-selector spec.type=LoadBalancer -o wide`
- repository inventory for `Jenkinsfile`, Jenkins, LangChain and LangGraph surfaces

## Phase result

The dated inventory refresh is current and evidence-backed for identity, billing-enabled state, quota values, running resources and LoadBalancer state. Phase 01 remains **BLOCKED/PARTIAL** because approved spend controls, teardown/backup controls, provider access, Jenkins-host state, domain/HTTPS, Kaggle capacity and row-level stale/recapture reconciliation were not proven. No production-ready claim is made.
