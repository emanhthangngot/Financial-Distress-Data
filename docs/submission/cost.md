# Cost

Doubles as the row-67 (IaC) cost deliverable. GCP free-trial credit only —
**zero out-of-pocket spend**, target under USD 100 of the USD 300 available
(90-day trial, expires 2026-11-06).

- `make gcp-up` / `gcp-down` / `gcp-status` (`financial-distress-gitops/Makefile`)
  hibernate node pools when not actively working — the single largest cost
  lever (~USD 0.65-0.80/hr running vs ~USD 0.14/hr hibernated, per the plan's
  measured estimate on a peer project).
- Cloud Logging/Monitoring disabled cluster-wide (bills per GB; Loki/Grafana
  score the same rubric rows instead).
- Real spend and credit-usage screenshots: **TBD phase-08** — GCP billing
  usage reporting lags several hours behind actual resource creation, so
  this can't be captured meaningfully until near submission.

Status: cost levers implemented; actual spend report pending phase-08.

## Session — 2026-08-10 (Phase 5 live evidence capture)

- `make gcp-up` restored primary-pool (1 node) + evidence VM.
- Stopped the evidence VM and raised secondary-pool to 1 node
  (e2-standard-4) to give the A/B experiment's two extra chat-model
  revisions room to schedule — exactly the sequencing this file already
  prescribed (8 + 0 + 4 = 12 vCPU, at the project quota cap).
- A/B revisions could not both go `Ready`: `fd-chat-model-weights` is a
  `ReadWriteOnce` PVC already mounted read-write by the live
  `fd-chat-model-predictor` pod; GCE PD rejects a second node's attach
  (`Multi-Attach error`) regardless of CPU headroom. Deleted the A/B
  resources and scaled secondary-pool back to 0 rather than run
  under-provisioned; the row stays `design_only`.
- Ran Locust, the warm-pool cold/warm measurement, and 4 real CI/CD digest
  releases (rag-pipeline + 3 agents) during the primary-pool-only window.
- Session ends with `make gcp-down`: primary pool 0, secondary pool 0,
  evidence VM stopped. Billing balance delta: pending phase-08 (usage
  reporting lag), consistent with the rest of this file.

## Capacity and quota budget

Figures below deliberately separate observed state, Terraform/manifest
configuration, and work that is still planned. They are not a billing-balance
claim.

### Measured and configured capacity

| Class | Capacity or state | Source and interpretation |
|---|---:|---|
| Measured project quota | 12 vCPU | `CPUS_ALL_REGIONS`; this project-wide limit includes GKE nodes and the evidence VM. |
| Measured hibernated state | 0 vCPU in use | Both node pools are at zero and the evidence VM is stopped. This is the required between-session state. |
| Configured primary pool | 1 × `e2-standard-8`: 8 vCPU, 32 GiB nominal | `terraform/gcp/variables.tf`; the execution plan records about 7.6 allocatable vCPU after node overhead. |
| Configured secondary pool | 0 × `e2-standard-4` by default; 4 vCPU, 16 GiB nominal when raised to one | The pool exists but Terraform defaults it to zero nodes. |
| Configured evidence VM | 1 × `e2-medium`: 2 vCPU, 4 GiB | Started by `make gcp-up`; stopped by `make gcp-down`. |

`make gcp-up` restores only the primary node pool and starts the evidence VM:
8 + 2 = 10 of 12 vCPU, leaving 2 vCPU. A secondary `e2-standard-4`
therefore **cannot** run at the same time. It fits only after the VM is stopped:
8 + 4 = 12 of 12 vCPU, with no quota headroom. The secondary must return to
zero before the VM is restarted.

### Explicit Kubernetes requests

This table inventories request values committed in the GitOps repository. It
assumes one replica for the listed controllers and one current GKE node for the
KServe node-agent DaemonSet.

| Configured workload | CPU request | Memory request |
|---|---:|---:|
| Embedding `InferenceService` | 1.00 | 2 GiB |
| Knative Serving controllers | 0.60 | 360 MiB |
| Kourier controller and gateway | 0.40 | 400 MiB |
| KServe controllers and one node agent | 0.30 | 600 MiB |
| F5 NGINX ingress controller | 0.10 | 128 MiB |
| Sealed Secrets controller | 0.05 | 64 MiB |
| **Explicit-request subtotal** | **2.45 CPU** | **3.52 GiB** |

The subtotal is a lower bound, not a complete live-cluster measurement. Argo
CD and cert-manager are installed but their GitOps values do not pin resource
requests. Prometheus/Grafana, Loki/OpenTelemetry, the custom model server,
warm pool, agents, MCP services, and A/B resources are still planned or
placeholder manifests and therefore have no honest request value to add yet.
They must receive requests and be added to this table before deployment.

The requests embedded in KServe `ClusterServingRuntime` definitions are
templates, not simultaneously scheduled pods, so they are excluded. Selecting
one of those runtimes would normally add its declared 1 CPU / 2 GiB model-server
request; the storage initializer can add an ephemeral 0.1 CPU / 100 MiB request.

## Evidence-window sequencing

1. Run `make gcp-up` for the primary platform and evidence VM. Capture the
   Terraform and Ansible evidence while the secondary pool remains at zero.
2. Finish VM-dependent evidence, then stop the evidence VM and verify its state.
3. Raise the secondary pool to one node only after the VM is stopped. Run the
   inference, agent, MCP, and autoscaling evidence in this 8 + 4 vCPU window.
   Because it consumes the full quota, do not expect KEDA to add another node.
4. Scale the secondary pool back to zero before restarting the VM for any
   follow-up capture.
5. End every session with `make gcp-down`, then `make gcp-status`.

The hibernation invariant is exact: **primary pool = 0 nodes, secondary pool =
0 nodes, evidence VM = stopped, project vCPU usage = 0**. PVCs and other
non-vCPU resources persist, so hibernation reduces compute spend but does not
mean the GCP bill is zero. Billing balances and credit deltas remain pending
until phase-08 capture; none are inferred here.
