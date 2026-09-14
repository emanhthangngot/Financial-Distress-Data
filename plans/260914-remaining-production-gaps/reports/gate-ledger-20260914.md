# Remaining Production Gaps — Gate Ledger

**Captured:** 2026-09-14T14:53:11+07:00
**Phase:** Gap 01 — Reconfirm gates and inventory
**Source revision:** `5fa76e1` (local `dev` baseline at branch creation)
**Evidence baseline:** `evidence-baseline-pre-rebuild` resolves locally

## Status

| Gate | Status | Evidence | Owner / next action |
|---|---|---|---|
| Baseline tag | PASS | `git tag -l evidence-baseline-pre-rebuild` resolved | Evidence owner: retain tag and existing evidence |
| Billing/spend controls | BLOCKED | Billing is enabled, but this refresh did not retrieve residual credit, approved window, teardown inventory, backup/export destination, or a hard spend-control result | Operator: stop unapproved capacity, refresh allocation and lifecycle controls before any paid-capacity action |
| Project-wide CPU capacity | BLOCKED | `CPUS_ALL_REGIONS=12`, usage `9`; `GPUS_ALL_REGIONS=0`, usage `0` | Platform owner: obtain approved quota/no-spend window before capacity-backed phases |
| Regional CPU capacity | BLOCKED | `CPUS=32`, usage `9`; `E2_CPUS=8`, usage `0`; `PREEMPTIBLE_CPUS=0`, usage `0`; `INSTANCES=8`, usage `2` | Platform owner: obtain approved quota/no-spend window before capacity-backed phases |
| Kubernetes capacity | BLOCKED | One Ready `e2-standard-8` node has remained running since 2026-09-12 and the evidence VM is RUNNING; this violates the documented between-session hibernation invariant and consumes quota/credit | Platform owner: record authorization/window and teardown deadline; hibernate in a controlled operator action if no approved window exists |
| External load balancers | BLOCKED | Live cluster reports NGINX and Kourier `LoadBalancer` services; required target is exactly one external entry point; forwarding-rule/address billing for removed agentgateway was not checked | Platform owner: reconcile reviewed GitOps revision and GCP forwarding-rule/address state before network-cost closure |
| Jenkins host/controller | UNVERIFIED | `fsds-evidence-worker` and one GKE node are RUNNING; no Jenkins health/controller inspection was performed; no root `Jenkinsfile` exists | Platform owner: identify or provision the approved controller, JCasC, backup and ephemeral-agent proof |
| Provider access/limits | UNVERIFIED | No fresh Groq/Gemini/provider capability or quota check was performed | ML/agent owner: measure allowed free providers before pinning or evaluating models |
| LangGraph runtime | UNVERIFIED | No checked-in LangGraph/LangChain implementation found in current source inventory | ML/agent owner: implement and measure parity before cutover |
| Domain/HTTPS | UNVERIFIED | No fresh domain certificate/edge exercise was run in this local gate refresh | Serving owner: capture trusted HTTPS and auth/rate-limit evidence |
| Kaggle/GPU capacity | UNVERIFIED | No Kaggle job or GPU capacity exercise was run in this refresh | ML owner: run only after access and spend controls are verified |

## Inventory reconciliation

- Baseline tag is retained; no evidence tree was deleted.
- Existing prior gate evidence remains historical and is not relabeled as current proof.
- Current live observations differ from the 2026-09-03 report: one Kubernetes node is Ready and regional CPU usage is 9. The prior hard-stop decision must therefore be re-evaluated for the specific requested workload, not copied forward blindly.
- The two live external `LoadBalancer` services show the network-cost invariant is still open.
- Local source inventory contains no Jenkinsfile and no production LangGraph/LangChain implementation.
- The accepted baseline inventory remains 161 rubric rows / 300 points: 60 executed, 57 design-only, and 44 pending. This refresh did not produce a row-level stale/recapture list; that criterion remains open.

## Resource safety

No Terraform apply, Kubernetes mutation, quota request, paid API call, or new billable resource was performed by this refresh. The ledger records the policy boundary, but approved-window, teardown, backup/export, residual-cost, and fail-closed controls remain unverified.

## Commands exercised

- `date --iso-8601=seconds`
- `git tag -l evidence-baseline-pre-rebuild`
- `gcloud auth list --filter=status:ACTIVE`
- `gcloud billing projects describe project-60655616-d84a-4883-867`
- `gcloud compute project-info describe --format=json`
- `gcloud compute regions describe asia-southeast1 --format=json`
- `gcloud container clusters list`
- `gcloud compute instances list`
- `kubectl get nodes`
- `kubectl get svc -A --field-selector spec.type=LoadBalancer`
- repository inventory for `Jenkinsfile`, Jenkins, LangChain and LangGraph surfaces

## Phase result

The dated inventory refresh is recorded, but Phase 01 remains **BLOCKED/PARTIAL** because provider state, Jenkins-host state, spend controls, and row-level evidence reconciliation were not proven. No production-ready claim is made.
