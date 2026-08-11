# Evidence — Safe A/B rollout when deploying a new model

Proves `platform/llm/ab-testing.yaml` (financial-distress-gitops) deploys a new
LLM revision alongside the existing model, preserves independent model weights,
waits for readiness, and shifts only a canary share of traffic.

- rubric_id: LLM-a-b-testing-when-you-deploy-a-new-model
- execution_timestamp: 2026-08-11T00:31+07:00
- source_sha: 668273d7e28c9f4221f09942c95730bea0cb432a
- gitops_sha: 99c01252d5aec53737d697fcb02b0e7061d8824e
- versions: v1 (`fd-chat-model-v1-config-ab`) and v2 (`fd-chat-model-ab-v2-clone`); pod `MODEL_VERSION` values `v1`/`v2`
- command: live Kubernetes inspection of the GitOps Application, PR-backed revisions, model-weight PVC/PV bindings, revision readiness/node placement, Knative route conditions/traffic, probes, and agent `ModelConfig` resources
- expected_result: deploying v2 does not replace v1 directly; immutable revisions retain distinct bound storage, both revisions become ready, and the service exposes v1 as stable with v2 as a monitored canary
- actual_result: PRs #31 (clone PVCs), #32 (immutable revision rotation), #33 (readiness probes), and #34 (Configuration-backed v1) produced live state reconciled by Argo CD Application `platform-llm`, `Synced/Healthy` at `99c01252`. PVC `fd-chat-model-weights-ab-v1` and PVC `fd-chat-model-weights-ab-v2` were both `Bound`, `2Gi`, `RWO`, with distinct PVs `pvc-c980d0e6-9124-4a3d-ab4b-7fa2a0a1f624` and `pvc-2d1cfb4e-fb78-4608-8a69-f784f314fe29`. Revision `fd-chat-model-v1-config-ab` was `Ready 1/1` on the primary node; `fd-chat-model-ab-v2-clone` was `Ready 1/1` on the secondary node. Knative Service `fd-chat-model-ab` was `Ready` and `RoutesReady`, with stable 80% traffic to v1 and canary 20% traffic to v2. Both stable/canary DNS routes passed `/health` with `{"status":"ok"}` and `/v1/models`; pod `MODEL_VERSION` values were `v1` and `v2`. `phase2-ab-dashboard`, `fd-agent-model-v1`, and `fd-agent-model-v2` were present.
- redaction_status: reviewed — no credentials, tokens, personal data, or private endpoint values included

## WHO → ACTION → RESULT

- GitOps operator -> merges the four rollout changes through PRs #31–#34 -> v1 remains available while v2 receives its own immutable revision and cloned model-weight volume.
- Storage controller -> binds `fd-chat-model-weights-ab-v1` and `fd-chat-model-weights-ab-v2` -> each 2Gi `RWO` PVC uses a distinct PV, so the two revisions do not share mutable model storage.
- Scheduler/readiness controller -> places v1 on the primary node and v2 on the secondary node, then evaluates readiness -> both revisions report `Ready 1/1`.
- Knative Service -> exposes `fd-chat-model-ab` with `RoutesReady` -> stable traffic remains 80% on v1 and canary traffic is limited to 20% on v2.
- Probe client -> calls `/health` and `/v1/models` through both DNS routes -> both endpoints succeed and identify reachable model services.
- Agent configuration -> exposes `fd-agent-model-v1` and `fd-agent-model-v2` -> agents can be evaluated against separate model configurations while `phase2-ab-dashboard` provides the dashboard resource.

## Rollback boundary

The source SHA, GitOps SHA, and PR sequence provide the immutable audit points
for reverting the desired state. No rollback was executed during this capture;
the evidence records the safe staged rollout state only.

Status: DONE
Summary: New-model rollout preserved v1, created a distinct ready v2 revision/PVC, and exposed v2 only as a 20% canary.
Concerns: No rollback execution or supplied quality/TTFT/token/safety/failure-rate/cost measurements in this capture.
