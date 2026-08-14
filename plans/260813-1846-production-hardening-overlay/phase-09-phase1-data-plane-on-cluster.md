---
phase: 9
title: "Phase 1 data plane onto the cluster"
status: cancelled
priority: P2
effort: "2d"
dependencies: [6, 7]
---

> **CANCELLED 2026-08-14 (user decision, ML track dropped).** No LLM rubric row requires Phase 1 containerised onto the shared cluster (measured 2026-08-14). Closed only ML rows (~6 pts). `infra/phase1-cluster/` (was untracked, never wired into any active workflow) is now committed as-is in the ML-scaffolding archive commit.
> Body below is kept as the historical record of what was planned/built; nothing further is executed against it. See `plan.md` Overview.

# Phase 9: Phase 1 data plane onto the cluster

## Overview

Close the plan's central architectural gap: two operating models, two secret
mechanisms, two deploy paths. Phase 1's data plane moves onto the same cluster
plane as Phase 2 — **by packaging its existing code, not by changing it**.

This is the phase that makes "production-shaped" true rather than aspirational.

## Requirements

- Functional: Kafka, MinIO, Airflow, Flink and Postgres run on the cluster under
  Argo CD, with the identical Phase 1 pipeline code producing identical results;
  the local `docker-compose.yml` path continues to work unchanged.
- Non-functional: zero source changes under `PHASE1_PROTECTED`; the Phase 1
  evidence set stays valid and is not regenerated.

## Architecture

**Package, do not port.** Phase 1's Python is already containerised locally via
`docker-compose.yml` and `infra/`. Running it on Kubernetes means building images
from the same source and writing manifests — no code edit. `docker-compose.yml`
and `infra/` are not protected paths; `src/` is, and stays untouched.

**Two runtimes, one codebase.** The local compose path is not deleted. It remains
the fast development loop and the reproduction path for the already-captured
Phase 1 evidence. The cluster deployment is an additional runtime target. Keeping
both is what preserves goal 1 while achieving goal 4.

**Ansible's role.** The rubric's IaC row asks specifically for Ansible configuring
and deploying services onto a VM, split into clean roles. The GitOps repo already
has `ansible/roles/` scaffolding. This phase gives it real work: configuring the
evidence VM as the Phase 1 host for components that are genuinely better off the
cluster, and providing the role split the rubric asks for.

Component placement:

| Component | Placement | Why |
|---|---|---|
| Kafka | cluster StatefulSet | needs PVC, already cluster-shaped |
| MinIO | cluster StatefulSet | object storage backend for Iceberg too |
| Postgres (Phase 1 metadata) | cluster StatefulSet | consumed by cluster workloads |
| Airflow | cluster (existing chart pattern) | orchestrates cluster jobs |
| Flink | cluster session cluster | shared with the phase 8 CDC job |

## Related Code Files

Source repo:

- Create: `infra/phase1-cluster/Dockerfile.pipeline`
- Create: `infra/phase1-cluster/README.md`
- Modify: `configs/phase2-deployables.yaml` — add the Phase 1 pipeline image
- Create: `tests/phase2/test_phase1_cluster_parity.py`

GitOps repo:

- Create: `platform/data-phase1/kafka.yaml`, `minio.yaml`, `postgres.yaml`, `airflow.yaml`, `flink.yaml`
- Create: `argocd/applications/platform-data-phase1.yaml`
- Create: `ansible/roles/evidence-host/tasks/main.yml` and companion roles
- Create: `ansible/playbooks/evidence-host.yml`

**Not modified:** anything under `src/`, `sql/`, `dags/*.py` outside `dags/phase2/`.

## Implementation Steps

1. Build a pipeline image from the existing Phase 1 source with no source edits.
   Verify by diffing the image's `src/` against the repo checkout.
2. Write the platform manifests for Kafka, MinIO, Postgres, Airflow and Flink with
   explicit resource requests matching the phase 4 capacity plan, PVCs sized for
   the evidence dataset, and digest-pinned images so phase 5's Kyverno admits them.
3. Deploy via Argo CD in a dedicated namespace with its own sync wave. Do not
   co-mingle with Phase 2 namespaces — separate namespaces keep the network
   policy and mesh authorization stories clean.
4. Run the Phase 1 pipeline on the cluster and write a parity test comparing its
   outputs against the recorded local-run outputs. **Parity is the acceptance
   signal** — same code, same inputs, same results, different runtime.
5. Write the Ansible roles for evidence-host configuration with a clean role split
   (`common`, `docker`, `evidence-host`, `benchmark-client`), satisfying the
   rubric's explicit "chia thành các role để code clean" requirement.
6. Confirm the local `docker compose config` and the Phase 1 quality gate still
   pass unchanged.
7. Verify the protected-path diff is clean.

## Verification

```bash
docker compose config
.venv/bin/python scripts/run_stage1_quality_gates.py
.venv/bin/python -m pytest tests/phase2 -k phase1_cluster_parity
kubectl get pods -n phase1-data
ansible-playbook --syntax-check ansible/playbooks/evidence-host.yml
```

## Success Criteria

- [ ] Phase 1 pipeline -> runs on the cluster -> produces outputs matching the recorded local run (parity test green)
- [ ] `docker compose config` and the Phase 1 quality gate -> run locally -> still pass unchanged
- [ ] Phase 1 images -> admitted by Kyverno -> signed and digest-pinned like everything else
- [ ] Ansible playbook -> syntax-checked and run -> configures the evidence host through discrete roles
- [ ] Protected-path diff -> clean
- [ ] Strict `--track LLM` gate -> unchanged PASS 100/100

## ML rubric rows closed

- IaC — Ansible role-based configuration and deployment (2 pts), completing the
  IaC section started in phase 4
- CI/CD — DP1, DP2, DP3 pipeline deployment rows (~6 pts), which require the data
  pipelines to be genuinely deployed rather than local-only

## Risk Assessment

- **Storage cost.** Cluster PVCs for Kafka and MinIO are a standing charge.
  Size against the evidence dataset, not a production-scale guess, and confirm
  `make gcp-down` preserves them.
- **Parity failure would indicate an environment dependency in Phase 1 code**,
  which is exactly what the test exists to surface. If it fails, do **not** fix by
  editing Phase 1 source — fix the container environment.
- **Namespace and network policy interactions** with the phase 6 default-deny
  policy will block traffic until policies are written for the new namespace.
  Expect this and write them alongside the manifests, not afterwards.
