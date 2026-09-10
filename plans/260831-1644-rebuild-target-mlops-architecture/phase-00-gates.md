---
phase: 0
title: "Phase 0: Zero-spend resource and compatibility gates"
status: blocked
priority: P1
effort: "2-3 days + 1-3 days GCP quota lag"
dependencies: []
owns: ["reports/ (dated gate ledger only)"]
---

# Phase 0: Zero-spend resource and compatibility gates

## Overview

Inventory and decide before provisioning. Local source work is independent of unavailable cloud
capacity. Phase status stays blocked until live-resource prerequisites are resolved; this does not
block P1-P5 local work after the local inventory gate. No service is started by this planning update.

Historical quota tickets, naming-label changes and measurements remain in `reports/gate-decisions.md`.
The previously checked AC-P0-1/3/6 describe that old scope, not passes of the revised gates below.
The old 48-vCPU topology, USD120/180 credit thresholds and fixed KServe0.18 stack are retired.

## Requirements and decision gates

| Gate | Required evidence | Pass / blocked behavior |
|---|---|---|
| G0-local | CPU/RAM/disk, available runtimes, current source and source-unit contracts | Begin local work; do not assume all existing source is v1 |
| G0-cloud | Account/project, real free allocation/credit expiry, quota and selected workload requests | No verified allocation: block cloud apply, keep local path open |
| G1-spend | Provider allowlist, billing state, full compute/network/storage/egress estimate, teardown plan | No additional monetary spend; alerts alone do not cap spend; never enable paid tiers |
| G2-window | Explicit start/stop, required simultaneous components, backup/export and destroy inventory | No always-on floor; include LB/IP/disks/snapshots/control-plane costs after nodes stop |
| G3-serving | Current supported runtime/model/license/hardware compatibility, custom-model and benchmark capability | Small local model + existing KServe path preferred if viable; llm-d/GIE/LWS not required |
| G4-mesh | Authorized/unauthorized service calls plus real Job completion | Selective injection permitted; never call exclusions protected by mTLS |
| G5-providers | Groq Free and one free fallback capability probe, tool schemas, streaming, account limits | Gemini candidate only until verified; no per-provider quota promise or paid fallback |
| G6-Kaggle | MCP access, GPU quota/availability, private dataset and output/export policy | Bounded batch only; no hosting or cloud rubric substitution |
| G7-domain | Controlled DNS and trusted HTTPS for the Web API during demo window | Missing delegation/trust keeps P9 domain AC open |

## Related files and ownership

P0 owns a new dated gate report under this plan's `reports/`; preserve the historical gate report.
P6 owns Terraform/mesh mutations, P8 inference/provider changes, P7 Kaggle packaging, P9 DNS/ingress.
P0 supplies their measured configuration contract, not a competing implementation.

## Implementation steps

1. Inventory current source/runtime and record local feasibility without paid calls.
2. Read account/credit/quota state using authorized tools; record unavailable permissions as blockers.
3. Enumerate each resource's worst-case cost including residual resources and teardown failure. A
   free credit balance is not permission to exceed it. Do not apply when zero-spend cannot be bounded.
4. Define separate data, ML, LLM and final-integrated windows; do not claim integrated behavior from
   disjoint component-only captures. Keep persistent datasets/evidence exported before shutdown.
5. Probe Groq and the single fallback with non-sensitive input; record model ID, capability, terms,
   rate policy and date. Free-provider data-use policy must permit the supplied data.
6. Smoke selected custom-model serving locally. Quantization/thread/batch comparisons can satisfy
   optimization evidence without requiring 7B CPU inference or speculative decoding.
7. Test mesh/Jobs in the permitted runtime and record exclusions; cloud-specific proof waits for cloud.
8. Verify Kaggle access without pushing an unreviewed notebook; P7 performs compilation and artifact checks.
9. Publish the dated pass/blocked ledger with consumer phase and next action for every gate.

## Success criteria

- [ ] AC-P0-LOCAL: Operator -> inventories source and local resources -> P1-P5 source work has a feasible runtime and remains independent of cloud approval.
- [ ] AC-P0-CLOUD: Operator -> reads account/quota/credit state -> selected topology has documented no-additional-spend capacity or cloud provisioning stays blocked.
- [ ] AC-P0-COST: Cost owner -> checks API allowlist and resource lifecycle -> paid routes disabled; expiry/remaining allocation measured; residual-cost teardown covered.
- [ ] AC-P0-WINDOW: Operator -> dry-runs deployment/export/teardown sequence -> explicit owners, deadlines and recovery for every resource, no 24/7 requirement.
- [ ] AC-P0-SERVE: Inference engineer -> exercises selected custom-model server -> real response and benchmark-compatible telemetry on available hardware, or P8 live serving blocked.
- [ ] AC-P0-MESH: Platform engineer -> tests an injected Job and authorization edges -> job completes and unauthorized traffic is denied, with exclusions named.
- [ ] AC-P0-PROVIDER: LLM engineer -> probes Groq Free and one verified free fallback -> capability/terms/limits recorded, no billing-tier activation.
- [ ] AC-P0-KAGGLE: ML engineer -> inspects MCP/kernel prerequisites -> bounded private job and artifact route feasible, or experiment lane blocked without changing graded KFP work.
- [ ] AC-P0-DNS: Operator -> verifies DNS control and HTTPS prerequisites -> trusted demo domain feasible or P9 domain gate explicitly blocked.

## Risks and verification

Stale free-tier terms, hidden residual charges and cloud teardown failure are fail-closed risks.
Recheck immediately before each window. No arbitrary auto-destroy may remove shared data or unrelated
user resources. Record exact resources authorized for creation/deletion and verify their end state.
Planning is read-only; live gates require actual command output at execution, never historical counts.

