# Hardening Completion Slice — 2026-08-14

## Executive Summary

- Local API images build successfully, but GHCR push is blocked by the current token: `permission_denied: token ... missing expected scopes`.
- Five infrastructure image placeholders were replaced with immutable upstream digests; Kafka manifest and kubeconform filtering defects were fixed.
- Evidence capture now covers 14 sections, records declared screenshot commands, and remains fail-closed.
- Live cluster acceptance remains blocked because the new namespaces/rollouts are not deployed and quota is not raised.

## Evidence

| Check | Result |
|---|---|
| Feature API Docker build | PASS; local digest `sha256:2d15ced4d4d67c998c26f141c1f5ea6c071eda3414004bf0a35ad3520fcfe9b8` |
| Drift API Docker build | PASS; local digest `sha256:9dca748ba8b22bfc73a649659966829ba482e6a88862d93e4bb573815cd4fe7d` |
| GHCR push | BLOCKED; `write:packages` scope unavailable |
| Upstream immutable digests | PostgreSQL, Kafka, MinIO, Flink, Airflow, Lakekeeper pinned |
| Kubeconform | PASS; 302 resources, 190 valid, 0 invalid, 112 CRD schemas skipped |
| GitOps default validation | PASS |
| GitOps strict real-digest validation | FAIL only for feature-api/drift-api Helm values until images are pushed |
| Evidence capture dry-run | PASS; 14 sections, 2 screenshot plans |
| API container smoke | PASS; `/readyz`, `/metrics`, `/drift` verified locally |
| Focused tests | 49 passed |

## Root Causes / Blockers

1. The GitHub keyring token is valid for repository operations but lacks GHCR `write:packages`; local image digests cannot be used as registry digests.
2. Cluster has no `phase1-data` or `phase2-ml` namespace and no Argo Rollout CRD/resource for `feature-api`; direct apply would create a partial, non-pullable deployment.
3. Quota remains insufficient for the planned concurrent soak (`E2_CPUS=8`); a quota/billing change requires operator approval.

## Required Handoff

- Refresh GitHub auth with `write:packages` and `read:packages`, then rerun the two API workflows or `docker push` commands.
- Let the workflow sign, attest SPDX SBOM and SLSA provenance, then let the GitOps digest-bump PR update both Helm values.
- Approve a bounded cluster rollout window and quota increase before applying Phase 1/Phase 2 data-plane manifests.
- Run Kyverno, ESO/Linkerd, Lakekeeper, Flink CDC, MLflow/Kubeflow, KEDA and Argo rollback scenarios; capture only real outputs.
