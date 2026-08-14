---
title: "Cost"
date: 2026-08-14
status: active
---

# Cost: hibernation-first capacity budget on GCP free-trial credit

This doc is the cost deliverable, doubling as the row-67 (IaC) cost proof:
GCP free-trial credit only — zero out-of-pocket spend, target under USD 100
of the USD 300 available (90-day trial, expires 2026-11-06). It proves
hibernation discipline (node pools scaled to zero between sessions) and a
measured capacity budget; it does not prove a reconciled dollar-amount
billing report — GCP billing usage reporting lags several hours behind
resource creation, so a real spend figure is deferred, disclosed as pending
rather than estimated.

## Cost levers

- `make gcp-up` / `gcp-down` / `gcp-status`
  (`financial-distress-gitops/Makefile`) hibernate node pools when not
  actively working — the single largest cost lever (~USD 0.65-0.80/hr
  running vs ~USD 0.14/hr hibernated, measured estimate on a peer project).
- Cloud Logging/Monitoring disabled cluster-wide (bills per GB; Loki/Grafana
  score the same rubric rows instead).
- Real spend and credit-usage figures: pending final submission freeze —
  GCP billing lag makes this unmeasurable meaningfully mid-session.

## Capacity and quota budget

Figures below deliberately separate observed state, Terraform/manifest
configuration, and work that is still planned. They are not a
billing-balance claim.

### Measured and configured capacity

| Class | Capacity or state | Source and interpretation |
|---|---:|---|
| Measured project quota | 12 vCPU | `CPUS_ALL_REGIONS`; project-wide limit includes GKE nodes and the evidence VM |
| Measured hibernated state | 0 vCPU in use | Both node pools at zero, evidence VM stopped — required between-session state |
| Configured primary pool | 1 × `e2-standard-8`: 8 vCPU, 32 GiB nominal | `terraform/gcp/variables.tf`; ~7.6 allocatable vCPU after node overhead |
| Configured secondary pool | 0 × `e2-standard-4` by default; 4 vCPU when raised to one | Pool exists but Terraform defaults it to zero nodes |
| Configured evidence VM | 1 × `e2-medium`: 2 vCPU, 4 GiB | Started by `make gcp-up`; stopped by `make gcp-down` |

`make gcp-up` restores only the primary pool and starts the evidence VM: 8 +
2 = 10 of 12 vCPU, leaving 2 vCPU headroom — a secondary `e2-standard-4`
cannot run at the same time. It fits only after the VM is stopped: 8 + 4 =
12 of 12 vCPU, with no quota headroom.

### Explicit Kubernetes requests (lower bound, not a full measurement)

| Configured workload | CPU request | Memory request |
|---|---:|---:|
| Embedding `InferenceService` | 1.00 | 2 GiB |
| Knative Serving controllers | 0.60 | 360 MiB |
| Kourier controller and gateway | 0.40 | 400 MiB |
| KServe controllers and one node agent | 0.30 | 600 MiB |
| F5 NGINX ingress controller | 0.10 | 128 MiB |
| Sealed Secrets controller | 0.05 | 64 MiB |
| **Subtotal** | **2.45 CPU** | **3.52 GiB** |

Argo CD and cert-manager are installed but pin no resource requests.
Prometheus/Grafana, Loki/OpenTelemetry, the model server, warm pool, agents,
MCP services, and A/B resources are excluded from this subtotal because they
either lack a pinned request or are template-only (KServe
`ClusterServingRuntime` definitions are templates, not simultaneously
scheduled pods).

## Real capacity conflict, disclosed honestly

During the 2026-08-10 session, both A/B chat-model revisions could not go
`Ready` simultaneously: `fd-chat-model-weights` is a `ReadWriteOnce` PVC
already mounted read-write by the live predictor pod, and GCE PD rejects a
second node's attach (`Multi-Attach error`) regardless of CPU headroom. The
A/B resources were deleted and the secondary pool scaled back to zero rather
than run under-provisioned — the row stays `design_only` for that specific
concurrent-mount configuration (see `ab_testing.md` for the staged rollout
that does work, using distinct PVCs per revision instead of one shared PVC).

## Evidence-window sequencing

1. `make gcp-up` for the primary platform and evidence VM; capture
   Terraform/Ansible evidence while the secondary pool stays at zero.
2. Finish VM-dependent evidence, stop the evidence VM, verify its state.
3. Raise the secondary pool to one node only after the VM is stopped; run
   inference/agent/MCP/autoscaling evidence in the 8+4 vCPU window — full
   quota, so KEDA cannot add another node during this window.
4. Scale the secondary pool back to zero before restarting the VM.
5. End every session with `make gcp-down`, then `make gcp-status`.

Hibernation invariant: **primary pool = 0 nodes, secondary pool = 0 nodes,
evidence VM = stopped, project vCPU usage = 0**. PVCs and other non-vCPU
resources persist, so hibernation reduces compute spend but does not mean
the GCP bill is zero.

## Session log (chronological, most recent capture windows)

- **2026-08-12 (routing/observability):** primary-pool + evidence VM opened;
  11/13 Routing & Gateway / Observability rows captured live (5
  infrastructure bugs found and fixed — see `routing_gateway.md` /
  `observability.md`). Hibernation at close stalled `RECONCILING` for 30+
  minutes due to an unmanaged bare Pod and three `PodDisruptionBudget`s with
  `ALLOWED DISRUPTIONS: 0` blocking node drain; force-deleted and resize
  completed.
- **2026-08-11 (phase 4/5 closeout):** quota re-verified live
  (`E2_CPUS=8`, `CPUS_ALL_REGIONS=12`) — caps this window to primary-pool
  alone; evidence VM and secondary-pool both stayed down.
- **2026-08-11 (MCP notebook capture):** `make gcp-up` opened primary node +
  evidence VM; both MCP services, Redis, PostgreSQL became ready; two
  notebook calls returned real feature/RAG and drift results; `make
  gcp-down` closed the session.
- **2026-08-10 (Phase 5 live evidence):** ran Locust, warm-pool
  cold/warm measurement, and 4 real CI/CD digest releases during a
  primary-pool-only window; the A/B PVC conflict above occurred and was
  resolved by deferring the row rather than under-provisioning.

Billing balance and trial-account status remain a submission-owner
console check — the GCP CLI has no field for "still on the free trial" or a
billing-credit delta.

## Limitations

No dollar-amount spend figure is reported in this doc — GCP billing usage
reporting lags actual resource creation by several hours, making an
in-session dollar figure unreliable rather than absent by oversight. The
Kubernetes-request table is an explicit lower bound, not a live
`kubectl top` measurement across every deployed workload.

## References

- GCP free trial: https://cloud.google.com/free
</content>
