# Evidence — A/B test for different LLM versions

Proves `platform/llm/ab-testing.yaml` (financial-distress-gitops) routes two
live LLM versions through one Knative Service and exposes the deployment state
needed to evaluate the split.

- rubric_id: LLM-a-b-testing-perform-a-b-test-for-different
- execution_timestamp: 2026-08-11T00:31+07:00
- source_sha: 52dc00c17e69cdc46403f377ae83f00a5406fac5
- gitops_sha: a9491d1a0164f098e0de02ab6cebec39752dc8c0
- versions: v1 (`fd-chat-model-v1-config-ab`) and v2 (`fd-chat-model-ab-v2-clone`); Knative Service `fd-chat-model-ab`
- command: live Kubernetes inspection of `platform-llm`, the two model revisions/PVCs, the Knative Service traffic split, both DNS routes (`/health` and `/v1/models`), and the dashboard/model-config resources
- expected_result: two ready LLM versions receive an explicit stable/canary split, both routes pass readiness and model-identity checks, and dashboard/config resources are present for A/B evaluation
- actual_result: Argo CD Application `platform-llm` was `Synced/Healthy` at GitOps SHA `99c01252`; `fd-chat-model-ab` was `Ready` and `RoutesReady` with stable traffic 80% to v1 and canary traffic 20% to v2. The stable and canary DNS routes both returned `{"status":"ok"}` from `/health` and succeeded on `/v1/models`; pod `MODEL_VERSION` values were `v1` and `v2`. `phase2-ab-dashboard`, `fd-agent-model-v1`, and `fd-agent-model-v2` were present.
- redaction_status: reviewed — no credentials, tokens, personal data, or private endpoint values included

## Live result

- Argo CD -> reconciles `platform-llm` -> `Synced/Healthy` at `99c01252`.
- A/B router -> sends 80% of stable traffic to v1 and 20% of canary traffic to v2 -> both LLM versions are live behind `fd-chat-model-ab`.
- Stable/canary probe -> calls `/health` and `/v1/models` on each DNS route -> health returns `{"status":"ok"}` and model listing succeeds for both routes.
- Pod inspection -> reads `MODEL_VERSION` -> the stable/canary pods identify themselves as `v1`/`v2`.
- Dashboard/config inspection -> finds `phase2-ab-dashboard` and `fd-agent-model-v1`/`fd-agent-model-v2` -> the A/B split has dashboard and per-version model-config resources available for review.

## Deployment audit trail

GitOps PRs #31 (clone PVCs), #32 (immutable revision rotation), #33
(readiness probes), and #34 (Configuration-backed v1) are represented by the
live state captured above. The source and GitOps SHAs pin the evidence to the
execution rather than to an unversioned screenshot or manifest.

This capture verifies routing, readiness, model identity, and evaluation
resource presence. It does not claim unprovided quality, TTFT, token, safety,
failure-rate, or cost measurements.

Status: DONE
Summary: Live v1/v2 A/B routing, readiness, model identity, and dashboard/config presence verified at 80%/20%.
Concerns: Quality and operational metric values were not included in the supplied execution facts.
