# Remaining Production Gaps — Gate Ledger

**Captured:** 2026-09-14
**Phase:** Gap 01 — Reconfirm gates and inventory
**Source revision:** `5fa76e1` (local `dev` baseline at branch creation)
**Evidence baseline:** `evidence-baseline-pre-rebuild` resolves locally

## Status

| Gate | Status | Evidence | Owner / next action |
|---|---|---|---|
| Baseline tag | PASS | `git tag -l evidence-baseline-pre-rebuild` resolved | Evidence owner: retain tag and existing evidence |
| Billing enabled | PASS | `gcloud billing projects describe project-60655616-d84a-4883-867`: billing enabled; billing account present | Operator: verify residual credit and teardown controls before any paid-capacity action |
| Regional CPU capacity | BLOCKED | `asia-southeast1`: `CPUS=32`, usage `9`; `E2_CPUS=8`, usage `0`; `PREEMPTIBLE_CPUS=0`, usage `0`; `INSTANCES=8`, usage `2` | Platform owner: obtain approved quota/no-spend window before capacity-backed phases |
| Kubernetes capacity | PASS (changed from prior baseline) | `fsds-evidence` is RUNNING; one Ready node reported by `kubectl`; node version `v1.35.7-gke.1222000` | Platform owner: re-check capacity immediately before each live operation |
| External load balancers | BLOCKED | Live cluster reports NGINX and Kourier `LoadBalancer` services; required target is exactly one external entry point | Platform owner: perform reviewed atomic network cutover; no unreviewed deletion |
| Jenkins controller/runtime | BLOCKED | No root `Jenkinsfile`; no checked-in Jenkins runtime/catalog surface found | Platform owner: establish controller, JCasC, backup and ephemeral-agent proof |
| LangGraph runtime | UNVERIFIED | No checked-in LangGraph/LangChain implementation found in current source inventory | ML/agent owner: implement and measure parity before cutover |
| Domain/HTTPS | UNVERIFIED | No fresh domain certificate/edge exercise was run in this local gate refresh | Serving owner: capture trusted HTTPS and auth/rate-limit evidence |
| Kaggle/GPU capacity | UNVERIFIED | No Kaggle job or GPU capacity exercise was run in this refresh | ML owner: run only after access and spend controls are verified |

## Inventory reconciliation

- Baseline tag is retained; no evidence tree was deleted.
- Existing prior gate evidence remains historical and is not relabeled as current proof.
- Current live observations differ from the 2026-09-03 report: one Kubernetes node is Ready and regional CPU usage is 9. The prior hard-stop decision must therefore be re-evaluated for the specific requested workload, not copied forward blindly.
- The two live external `LoadBalancer` services show the network-cost invariant is still open.
- Local source inventory contains no Jenkinsfile and no production LangGraph/LangChain implementation.

## Resource safety

No Terraform apply, Kubernetes mutation, quota request, paid API call, or new billable resource was performed by this refresh. Any live change remains gated on an approved zero-spend window, explicit teardown list, backup/export path, and residual-cost check.

## Commands exercised

- `git tag -l evidence-baseline-pre-rebuild`
- `gcloud auth list --filter=status:ACTIVE`
- `gcloud billing projects describe project-60655616-d84a-4883-867`
- `gcloud compute regions describe asia-southeast1 --format=json`
- `gcloud container clusters list`
- `kubectl get nodes`
- `kubectl get svc -A --field-selector spec.type=LoadBalancer`
- repository inventory for `Jenkinsfile`, Jenkins, LangChain and LangGraph surfaces

## Phase result

Phase 01 is complete for the reachable local/live inventory work. Cloud-backed implementation remains gated by the statuses above; no production-ready claim is made.
