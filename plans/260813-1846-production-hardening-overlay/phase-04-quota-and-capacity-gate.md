---
phase: 4
title: "Quota raise and capacity gate"
status: cancelled
priority: P1
effort: "0.5d work + external approval latency"
dependencies: [1]
---

> **CANCELLED 2026-08-14 (user decision, ML track dropped).** Existed only to unblock phases 5-12, all cancelled below. LLM track's IaC rows (Terraform GKE, Ansible VM) are already `executed` and need no quota raise.
> Body below is kept as the historical record of what was planned/built; nothing further is executed against it. See `plan.md` Overview.

# Phase 4: Quota raise and capacity gate

# THIS PHASE GATES EVERYTHING FROM PHASE 5 ONWARD

## Overview

The evidence cluster cannot host the target system on its current quota. This
phase raises capacity, re-sizes the node pools through Terraform, and fixes the
component placement plan against the **full** final component list rather than
growing it incrementally.

Start the quota request on day one of the plan, in parallel with phases 1-3 —
approval latency is external and cannot be compressed.

## Requirements

- Functional: the cluster can run every component from phases 5-11 concurrently,
  which acceptance criterion 5 of the plan requires.
- Non-functional: cost stays bounded by preserving the hibernate levers, and a
  billing leak cannot survive a failed scale-up.

## Architecture

Current state, from the GitOps repo `Makefile` header: `primary-pool` is one
`e2-standard-8`, `secondary-pool` is `e2-standard-4` and cannot be scaled because
the region's `E2_CPUS` quota is 8 and `primary-pool` alone saturates it. The
evidence VM is skipped via `NO_VM=1` for the same reason.

Target component budget for the final concurrent soak:

| Group | Components | Approx vCPU |
|---|---|---:|
| Existing platform | Argo CD, ingress, cert-manager, observability, agents, inference | ~6 |
| Phase 5 | Kyverno | ~0.5 |
| Phase 6 | External Secrets Operator, Linkerd control plane | ~1.5 |
| Phase 7 | Lakekeeper, catalog Postgres | ~1.5 |
| Phase 8 | Flink CDC job, CDC Postgres | ~2 |
| Phase 9 | platform data plane (Kafka, MinIO, Airflow, Flink, Postgres) | ~5 |
| Phase 10 | MLflow, training job, KServe models | ~4 |
| Phase 11 | Argo Rollouts controller, extra exporters | ~1 |
| Headroom | scheduling slack, rollout surge | ~3 |

Target: **~24 vCPU**. Request 32 to leave room for the rollout surge in phase 11,
where a canary temporarily doubles a workload.

Fallback if the grant is smaller: this plan's components are hibernatable per
group. Phase 4 delivers `make platform-up GROUP=...` / `platform-down GROUP=...`
so a smaller ceiling degrades to sequential group demos rather than blocking the
plan — at the cost of the concurrent soak, which would then be documented as a
known limitation instead of claimed.

## Measured cost baseline (2026-08-13)

Read from the billing console and by enumerating live resources. These are the
numbers the capacity decision must respect.

| Period | Gross | Net after credit |
|---|---:|---:|
| Aug 1-12, 2026 | ₫892,973 (~$34) | ₫0 |
| Aug 1-31 forecast | ₫2,519,114 (~$96) | ₫0 |

Net is ₫0 only because free-trial credit absorbs it. **The remaining credit
balance is the real budget ceiling and has not yet been read** — see step 0.

Estimated burn from live resource enumeration:

| Item | $/hr |
|---|---:|
| `e2-standard-8` node (primary-pool) | ~0.33 |
| 3 network LB forwarding rules | ~0.075 |
| Cloud NAT | ~0.045 |
| 9 persistent disks (~100 GB) | ~0.011 |
| static IP | ~0.005 |
| **Running** | **~0.47** |
| **Hibernated (nodes = 0)** | **~0.14** |

Cross-check: ₫892,973 over 12 days is ~$2.83/day ≈ $0.118/hr, matching the
hibernated estimate — the cluster was mostly asleep, and the GitOps `Makefile`
comment ("~$0.65-0.80/hr running vs ~$0.14/hr hibernated") is consistent.

### Two findings that change the plan

**1. Three load balancers bill during hibernation.** `kourier` (Knative,
up 5d20h), `agentgateway-proxy` (3d13h) and `nginx-ingress` (2d22h) each hold a
regional forwarding rule at roughly $0.025/hr. That is ~$0.075/hr — **more than
half the entire hibernated cost**, about $54/month, burning while nothing runs.
`make gcp-down` scales nodes to zero but does not delete `Service type:
LoadBalancer`, so the rules survive. `kourier` is the prime suspect for being
redundant: nginx-ingress is already the gateway, so unless KServe genuinely
routes through Knative's own ingress, that LB is pure waste. Verify before
deleting — it serves live LLM evidence.

**2. Budget scale.** A free trial is $300. At 24 vCPU:

| Pattern | $/month |
|---|---:|
| Today, mostly hibernated | ~$96 |
| 24 vCPU, session-based up/down | ~$150-250 |
| 24 vCPU running continuously | **~$650-870** |

Running continuously exhausts the credit in about two weeks — shorter than this
plan. **Session-based operation is therefore not a cost optimisation, it is a
precondition**, and phase 12's concurrent soak must be scheduled as a deliberate,
bounded window rather than left running.

**3. Actual spend is not readable from the CLI.** The Cloud Billing Budget API is
disabled on the project and no BigQuery billing export exists, so `gcloud` cannot
report spend — only the console can. Phase 12 owes a cost ledger, which needs one
of these enabled.

## Related Code Files

GitOps repo:

- Modify: `terraform/gcp/*.tf` — node pool sizing
- Modify: `terraform/envs/evidence/main.tf`
- Modify: `Makefile` — `platform-up`/`platform-down` per group, updated `gcp-up`
- Create: `docs/capacity-plan.md` (or the repo's equivalent docs location)

## Implementation Steps

0. **Read the remaining credit balance** (Billing console -> Credits). It is the
   real budget ceiling and decides whether the target is 24 or 32 vCPU, and how
   long phase 12's soak can run. Enable either the Cloud Billing Budget API or a
   BigQuery billing export so spend becomes machine-readable — phase 12 owes a
   cost ledger and `gcloud` cannot produce one today. Set a budget alert at 50%
   and 80% of the remaining credit.
1. Read the live quota before assuming anything:
   `gcloud compute regions describe asia-southeast1 --format="table(quotas.metric,quotas.limit,quotas.usage)"`.
   Record the actual numbers.
2. File the quota increase for `E2_CPUS` (and `CPUS` regional if separately
   limited) to 32, with a written justification. Record the case ID.
3. While waiting, write the capacity plan document with the table above and the
   per-group hibernate mapping.
4. On approval, update Terraform node pool sizing. Keep one pool; a second pool
   adds scheduling complexity without benefit at this scale.
5. `terraform plan`, review the diff, record it as evidence, then `terraform apply`.
6. Extend the `Makefile` with per-group hibernate targets. Preserve the existing
   `gcp-up` billing-leak rollback trap — it stops the evidence VM when scale-up
   fails and must survive this edit.
6b. **Close the load-balancer leak.** Audit the three forwarding rules; confirm
   whether `kourier` is actually serving traffic (nginx-ingress is already the
   gateway) and remove it if not. Then make `gcp-down` delete or scale away the
   `Service type: LoadBalancer` objects it currently leaves billing, and make
   `gcp-up` restore them. Verify the round trip returns the same ingress IP, or
   document that the IP changes — DuckDNS records point at it.
7. Verify the cluster schedules the full component list by applying a placeholder
   resource-request set matching the table, then removing it.

## Verification

```bash
gcloud compute regions describe asia-southeast1 \
  --format="table(quotas.metric,quotas.limit,quotas.usage)"
terraform -chdir=terraform/envs/evidence plan
make gcp-status
kubectl describe nodes | grep -A5 "Allocated resources"
```

## Success Criteria

- [ ] `gcloud compute regions describe` -> run after approval -> `E2_CPUS` limit >= 24
- [ ] `terraform apply` -> completes -> node pool sized to the capacity plan, `terraform validate` clean
- [ ] Placeholder workload matching the full component budget -> scheduled -> all pods reach Running, no `Insufficient cpu`
- [ ] `make gcp-down` then `make gcp-up` -> round trip -> cluster returns healthy with PVCs intact
- [ ] `make platform-down GROUP=<g>` -> named group scales to zero -> other groups unaffected
- [ ] Credit balance -> read from the console -> recorded, with a budget alert set at 50% and 80%
- [ ] Budget API or BigQuery billing export -> enabled -> spend is machine-readable for phase 12's cost ledger
- [ ] `make gcp-down` -> run -> forwarding-rule count drops to zero (currently 3 survive, ~$54/month)
- [ ] `kourier` -> traffic checked -> removed if redundant, or its necessity documented

## ML rubric rows closed

- **IaC x2 (4 pts)** — "Dùng Terraform để setup GKE" and "Dùng Ansible để configure
  và deploy các service lên VM". The Terraform half lands here; the Ansible half
  lands in phase 9 when the platform data plane is provisioned.

## Risk Assessment

- **The quota request may be denied or partially granted.** This is the plan's
  single largest external dependency. Mitigation is the per-group hibernate
  fallback in step 6, which converts a hard block into a documented limitation.
- **A larger cluster burns credit faster.** The hibernate levers are mandatory,
  not optional; phase 12's soak window should be scheduled deliberately and the
  cluster brought down immediately afterwards.
- **Editing `gcp-up` risks dropping the billing-leak rollback trap.** Treat that
  trap as protected behaviour and assert it survives by testing a deliberately
  failing scale-up.
