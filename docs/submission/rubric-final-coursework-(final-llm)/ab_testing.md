---
title: "A/B Testing"
date: 2026-08-14
status: active
---

# A/B Testing: two live model versions, 80/20 stable/canary split with independent storage

This doc proves the two rows in "A/B Testing": `platform/llm/ab-testing.yaml`
routes two live LLM versions (v1, v2) through one Knative Service with an
80%/20% stable/canary traffic split, each version bound to distinct
immutable storage, and deploying v2 never replaces v1 in place. It does not
prove quality, TTFT, token, safety, or cost comparison between versions —
that measurement was not part of this row's supplied execution facts, and is
disclosed as absent rather than invented.

**Active deployment facts:** Knative Service `fd-chat-model-ab`, revisions
`fd-chat-model-v1-config-ab` (stable, 80%) and `fd-chat-model-ab-v2-clone`
(canary, 20%). Argo CD Application `platform-llm` `Synced/Healthy` at GitOps
SHA `99c01252`.

## Part I — Independent storage, staged rollout

### 1. Distinct PVCs, distinct PVs — no shared mutable storage

```text
PVC fd-chat-model-weights-ab-v1  Bound  2Gi  RWO  PV pvc-c980d0e6-9124-4a3d-ab4b-7fa2a0a1f624
PVC fd-chat-model-weights-ab-v2  Bound  2Gi  RWO  PV pvc-2d1cfb4e-fb78-4608-8a69-f784f314fe29
```

v1 runs on the primary node, v2 on the secondary node, both `Ready 1/1`.
Deploying v2 clones a new PVC and revision rather than mutating v1's — the
staged rollout preserves v1 the whole time. GitOps audit trail: PRs #31
(clone PVCs), #32 (immutable revision rotation), #33 (readiness probes), #34
(Configuration-backed v1). Full evidence:
[`LLM-a-b-testing-when-you-deploy-a-new-model.md`](../../platform/evidence/llm/LLM-a-b-testing-when-you-deploy-a-new-model.md).

## Part II — Traffic split and readiness

### 2. 80/20 stable/canary, both routes healthy

```text
Knative Service fd-chat-model-ab: Ready, RoutesReady
  stable (v1): 80% traffic
  canary (v2): 20% traffic

$ curl <stable-route>/health   -> {"status":"ok"}
$ curl <canary-route>/health   -> {"status":"ok"}
$ curl <stable-route>/v1/models -> succeeds, pod MODEL_VERSION=v1
$ curl <canary-route>/v1/models -> succeeds, pod MODEL_VERSION=v2
```

`platform-ab-dashboard`, `fd-agent-model-v1`, and `fd-agent-model-v2` are all
present, giving both a dashboard resource and per-version agent model
configs to evaluate the split against. Full evidence:
[`LLM-a-b-testing-perform-a-b-test-for-different.md`](../../platform/evidence/llm/LLM-a-b-testing-perform-a-b-test-for-different.md).

## Limitations

This evidence proves routing, readiness, model identity, and the presence of
evaluation resources (dashboard, per-version configs) — it does not include
quality, TTFT, token, safety, failure-rate, or cost measurements comparing v1
against v2; those were not part of this row's supplied execution facts. No
rollback was executed during capture; the evidence records the staged
rollout state only, not a rollback drill.

## References

- Knative traffic splitting: https://knative.dev/docs/serving/traffic-management/
