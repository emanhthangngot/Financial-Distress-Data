---
title: Production Feast data and GHCR pull hardening
status: in-progress
priority: P0
effort: large
branch: codex/production-feast-ghcr
tags: [phase2, feast, minio, ghcr, gitops]
created: 2026-08-14
---

# Production Feast data and GHCR pull hardening

## Scope

- Deploy persistent MinIO for the existing `s3://financial-distress-lake` Feast contract.
- Produce real Phase 1 Gold Parquet and materialize `company_risk_features` into Redis.
- Provision a least-privilege GHCR pull credential without committing plaintext.
- Verify cold pulls and the live analyst assistant end to end.

## Acceptance criteria

- Phase 1 pipeline -> writes Gold datasets -> MinIO persists them across pod restart.
- Feast materializer -> reads `obt_company_quarter_risk` -> Redis returns non-null NVL risk fields.
- Analyst -> asks why NVL is high risk -> receives a cited completed answer based on non-null features.
- Sealed Secrets controller -> reconciles `ghcr-pull-secret` -> new web pod pulls its immutable GHCR digest without pull-secret warnings.
- Source and GitOps gates -> run after changes -> all required checks pass.

## Constraints

- No fake/synthetic shortcut added solely for checks; use the existing Phase 1 generator and Gold transforms.
- No plaintext credentials in Git, logs, reports, shell history, or conversation output.
- Argo CD remains the only mutator for managed workload manifests.
- Phase 1 contracts and Phase 2 MCP/RBAC/SSE contracts remain stable.

## Phases

1. Secure credential provisioning and GitOps secret contract.
2. Persistent MinIO and Phase 1 Gold production workload.
3. Feast batch materialization and readiness verification.
4. GitOps rollout, cold-pull test, live analyst acceptance.
5. Full tests, review, documentation and plan sync.

## Rollback

- Revert GitOps commits to the prior immutable manifests and digest.
- Preserve PVCs during workload rollback; do not delete stored Gold or Redis data.
- Revoke the dedicated GHCR PAT and delete only its named Secret Manager version if rollback requires credential retirement.
