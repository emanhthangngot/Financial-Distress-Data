---
title: Production Feast data and GHCR pull hardening
status: completed
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

1. Secure credential provisioning and GitOps secret contract — complete.
2. Persistent MinIO and Phase 1 Gold production workload — complete.
3. Feast batch materialization and readiness verification — complete.
4. GitOps rollout, cold-pull test, live analyst acceptance — complete.
5. Full tests, review, documentation and plan sync — complete.

## Verification record

- GitHub Actions workflow dispatch `31818827736`: lint, tests, phase5 verification, build and cosign all passed; immutable image digest `sha256:a58f381abd0e8cdb0066a12ba18566e4e8e9deb4282e88d85be3a72f04d3e0c9`.
- GitOps PRs `#78` and `#79` merged; Argo `platform-data` is `Synced/Healthy` at revision `22d6446d44419d4df264a5136a4ecc97cfba181f`.
- Manual cold-pull job completed after a 1m32s GHCR pull and verified 843 Gold rows, 16 risk rows, and non-null NVL `company_risk_features` in Redis.
- Source quality gate: 318 tests passed; Ruff, Black and Compose config passed. The first failed run was corrected for missing `boto3` and string event timestamps.

## Rollback

- Revert GitOps commits to the prior immutable manifests and digest.
- Preserve PVCs during workload rollback; do not delete stored Gold or Redis data.
- Revoke the dedicated GHCR PAT and delete only its named Secret Manager version if rollback requires credential retirement.
