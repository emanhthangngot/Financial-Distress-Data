---
phase: 0
title: "Phase 0: Capacity, cost and version gates"
status: blocked
priority: P1
effort: "2-3 days + 1-3 days GCP quota lag"
dependencies: []
owns: ["terraform/gcp/", "platform/inference/vendored/", "reports/gate-decisions.md"]
---

# Phase 0: Capacity, cost and version gates

## Overview

Current-state gate and cost control. P4 and P6 are not authorized until every load-bearing branch is
recorded and dated. The only permitted cluster mutations here are the two cost controls the target
already requires: make the secondary pool Spot-capable, and reduce external `LoadBalancer` Services
to the sole NGINX entry point. No GKE workload capacity is resident; the user-directed evidence VM
start is recorded separately.

P1, P2 and P3 are source-only and may start while G0 is branch C. **P4 and P6 are blocked** until
G0 is A/B, G1 has a fresh credit figure, and both G2 controls pass.

## Requirements

- Functional: record integer values and dated branch letters for G0-G6; branch C on G0 is a hard
  stop; reduce the measured three external load balancers to exactly one.
- Non-functional: no workload provisioning; GCP/Kubernetes mutations limited to GitOps/Terraform
  cost controls; every measured value dated in `reports/gate-decisions.md`.

## Architecture

| Gate | Question | Branch A | Branch B | Branch C |
|------|----------|----------|----------|----------|
| **G0 Quota bundle** | Sufficient for the 46-vCPU topology? | `CPUS_ALL_REGIONS>=48`, regional `CPUS>=48`, `E2_CPUS>=48`, `PREEMPTIBLE_CPUS>=28`, `INSTANCES>=10` → plan as written | Lower approved limits → recompute a safe topology before apply | Any quota prevents the 13-18 vCPU always-on floor → **HARD STOP. Escalate. Do not start P4 or P6.** |
| **G1 Cost** | Remaining credit? | ≥ USD 180 → proceed | USD 120-180 → halve capture windows | < USD 120 → escalate scope reduction |
| **G2a Compute** | Secondary pool Spot-capable? | Existing pool renders with `spot = true`; quota supports the node count | Spot quota pending → keep pool at zero | Spot quota denied → reassess cost model; escalate |
| **G2b Network** | Exactly one external load balancer? | Only NGINX remains `LoadBalancer` after atomic `net-istio` cutover and agentgateway internalization | Cutover pending → P4 and P6 blocked | Cutover cannot preserve serving → escalate architecture decision |
| **G3 KServe** | 0.18 exposes `LLMInferenceService` + Gateway API + GIE + LWS? | Yes → llm-d path (P8 as planned) | No → ADR-004 branch B (llama.cpp + semantic cache) | — |
| **G4 Sidecars** | Kubernetes ≥ 1.33 and Istio-injected Jobs reach `Completed`? | Yes → mesh-wide injection safe | No → exclude Job namespaces from injection | — |
| **G5 vLLM** | vLLM CPU production-usable? | Yes → KV-cache-routing evidence path | No → llama.cpp + semantic cache evidence path | — |
| **G6 Knative net layer** | Which network layer serves Knative? | **Selected: `net-istio`; `net-kourier` is removed** | — | — |

Two artifacts are required before any G0 branch is declared:
1. GCP Billing Console snapshot dated at execution start — supersedes the stale 2026-08-18 USD 223 figure.
2. Quota-increase request ticket ID and submission date.

The secondary node pool resource already exists
(`financial-distress-gitops/terraform/gcp/gke.tf:96-131`); the P0 change is adding `spot = true` to
its existing `node_config`. Raise `secondary_pool_node_count` only after quota approval.

### Measured baseline (2026-08-31)

- Quota bundle: `CPUS_ALL_REGIONS` 12, regional `CPUS` 32, `E2_CPUS` 8, `PREEMPTIBLE_CPUS` 0,
  `INSTANCES` 8. CPU usage reads zero because both pools are at size 0 and the `e2-medium` evidence
  VM is terminated.
- Terraform warm demand is one `e2-standard-8` + the `e2-medium` VM = 10 vCPU, leaving 2 project-wide
  and 8 Kubernetes-schedulable vCPU. The 13-18 vCPU floor does not fit.
- Recommended post-approval topology: primary 2 × `e2-standard-8` = 16 on-demand; secondary maximum
  7 × Spot `e2-standard-4` = 28; evidence VM conservatively budgeted as 2 → 46/48 vCPU,
  10 instances. Its measured shared-core quota charge is 1. Secondary defaults to 0.
- GKE `fsds-evidence`, `asia-southeast1-b`, Kubernetes `1.35.7-gke.1027000`, Regular channel. G4's
  version prerequisite passes; injected-Job completion untested.
- Three external Services live: `ingress-nginx`, `kourier`, `agentgateway-proxy`. Target is one.
- KServe v0.14.1; `InferenceService` CRD present; `LLMInferenceService` and LeaderWorkerSet absent.
- Billing enabled; remaining credit not readable with current CLI permissions. G1 stays open.

Full command evidence: [`reports/gate-decisions.md`](./reports/gate-decisions.md).

## Related Code Files

- Modify: `financial-distress-gitops/terraform/gcp/gke.tf` — `spot = true` on the secondary pool;
  primary count 2 and secondary window maximum 7 only after quota approval
- Modify: `financial-distress-gitops/terraform/gcp/variables.tf` — replace label `phase=phase2`
  with `component=unified-platform`; retain zero-capacity-safe defaults while G0 is branch C
- Remove: `financial-distress-gitops/platform/inference/vendored/03-net-kourier.yaml` when the
  KServe 0.18 + `net-istio` replacement is ready to reconcile
- Modify: the agentgateway controller/Gateway GitOps configuration that renders
  `agentgateway-proxy` — generated Service becomes `ClusterIP`; never patch the live Service out of band
- Update: `reports/gate-decisions.md`

## Implementation Steps

1. **Measure and request** — query project-wide, regional, machine-family, preemptible and
   instance-count quotas on the active Terraform project. Record the verified limits. Request
   `CPUS_ALL_REGIONS>=48`, regional `CPUS>=48`, `E2_CPUS>=48`, `PREEMPTIBLE_CPUS>=28`,
   `INSTANCES>=10`; record ticket IDs, submission dates, and outcomes. Open the Billing Console and
   record remaining credit in USD and VND — CLI billing access is unavailable, so no value may be
   inferred. *(Do this on day 1; it is the longest external pole.)*
2. **G2a — encode the approved topology.** Retain E2 only if `E2_CPUS` is approved; otherwise
   re-plan the machine family first. Primary two `e2-standard-8`; secondary `spot = true`, window
   maximum seven `e2-standard-4`, default count 0. With the 2-vCPU evidence VM, verify maximum
   planned demand is 46/48 vCPU and 10 instances. Run `terraform validate` and a reviewed
   `terraform plan`; do not apply a non-zero node count while G0 is open.
3. **G2b — remove the two redundant load balancers.** Replace `net-kourier` with `net-istio`;
   do not create an NGINX-to-Kourier route. Configure agentgateway so the generated
   `agentgateway-proxy` Service is `ClusterIP`. Reconcile both changes through Argo CD — never
   delete forwarding rules directly, because GKE recreates a rule underneath a `LoadBalancer`
   Service. Verify `kubectl get svc -A --field-selector spec.type=LoadBalancer` returns exactly
   one row.
   Replace the stale `phase=phase2` label at the next reviewed apply.
4. **G3 — KServe 0.18 compatibility.** Preserve the measured baseline. After G0 allows capacity,
   install KServe 0.18 in a throwaway namespace and verify `LLMInferenceService`, Gateway API, GIE
   and LeaderWorkerSet CRDs. Record branch A or B.
5. **G4 — native-sidecar completion test.** Record `1.35.7-gke.1027000` (satisfies ≥ 1.33). After a
   node pool is raised, deploy an Istio-injected Job that produces output and terminates; verify it
   reaches `Completed` within its deadline. Record branch A or B.
6. **G5 — vLLM CPU benchmark.** Run the fixed representative prompt set on the planned 7B model.
   Record TTFT, tokens/s, CPU allocation, branch A or B.
7. **G6 — Knative net layer.** Install KServe 0.18 with `net-istio`, route one
   `InferenceService` revision through the Istio `GatewayClass`, and remove `net-kourier`.
8. **Finalize** — update `reports/gate-decisions.md` with every closed branch, dated measurement,
   ticket ID and remaining blocker.

## Success Criteria

- [x] AC-P0-1: Platform operator → requests the quota bundle → records the outcome for
      `CPUS_ALL_REGIONS>=48`, regional `CPUS>=48`, `E2_CPUS>=48`, `PREEMPTIBLE_CPUS>=28`,
      `INSTANCES>=10`; rejected load-bearing quotas halt P4 and P6
- [ ] AC-P0-2: Cost owner → reads the GCP Billing Console → records remaining credit (USD + VND)
      plus a dated branch; no inferred value is accepted
- [x] AC-P0-3: Every quota-request ticket ID and submission date is recorded
- [ ] AC-P0-4: Terraform operator → plans primary 2 × `e2-standard-8`, secondary up to 7 × Spot
      `e2-standard-4` default 0, plus the `e2-medium` VM → `terraform validate` passes and maximum
      demand is 46 vCPU / 10 instances
- [ ] AC-P0-5: GitOps operator → replaces `net-kourier` with `net-istio` and makes the generated
      agentgateway proxy internal → the cluster exposes exactly one `LoadBalancer`, the NGINX ingress
- [x] AC-P0-6: Terraform operator → replaces `phase=phase2` with
      `component=unified-platform` → all planned Terraform resources carry no phase label
- [ ] AC-P0-7: Platform operator → installs KServe 0.18 in a throwaway namespace →
      `LLMInferenceService`, Gateway API, GIE and LeaderWorkerSet CRDs exist, or G3 branch B is recorded
- [ ] AC-P0-8: Platform operator → runs an Istio-injected Job on `1.35.7-gke.1027000` → the Job
      reaches `Completed` within deadline, or G4 branch B is recorded
- [ ] AC-P0-9: Platform operator → routes a KServe revision through `net-istio` →
      the request succeeds and no `net-kourier` resource remains
- [ ] AC-P0-10: All gate branches, measured values and blockers are dated in `reports/gate-decisions.md`
- [x] P4 and P6 are not authorized until G0 is A/B, G1 is measured, and both G2 controls pass

## Risk Assessment

**Risk:** G0 branch C (quota refused). Signal: quota query still returns 12 after the ticket closes.
Response: hard stop; escalate to the user; do not start P4 or P6. P1-P3 continue — they are
source-only and cost nothing.

**Risk:** Spot quota denied. Signal: GCP rejects the preemptible increase. Response: reassess the
cost model against remaining credit; escalate the budget decision.

**Risk:** Three external load balancers continue billing while pools are at zero. Signal:
`kubectl get svc -A --field-selector spec.type=LoadBalancer` returns three rows. Response: convert
through GitOps before P4; exactly one external load balancer is a hard invariant.

**Risk:** G3 branch B. Signal: `LLMInferenceService` CRD missing after install. Response: adopt
ADR-004 branch B; P8 switches to llama.cpp + semantic cache.

**Risk:** G4 branch B. Signal: an injected Job stays `Running` past its deadline. Response: exclude
`dataflow` and `kubeflow` from injection; restrict mTLS STRICT to `kserve`, `agents`, `api-serving`.
