---
title: Production Feast data and GHCR pull hardening
status: partially-verified
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

- Phase 1 pipeline -> writes Gold datasets -> MinIO retains them across a verified pod restart. **Verified:** MinIO pod was recreated; PVC remained `Bound` at 10Gi and `mc ls --recursive` returned 19 persisted objects.
- Feast materializer -> reads `obt_company_quarter_risk` -> Redis returns non-null NVL risk fields. **Verified:** the cold-pull job completed with 843 Gold rows, 16 risk rows, and non-null NVL values.
- Analyst -> asks why NVL is high risk after materialization -> receives a cited completed answer based on non-null features. **Open:** the cited browser response predates materialization, and the incident journal records null online values for that response.
- Sealed Secrets controller -> reconciles `ghcr-pull-secret` -> a new web pod cold-pulls its immutable GHCR digest without pull-secret warnings. **Verified:** web pod was recreated after reconciliation, reached Ready with zero restarts, and no new `FailedToRetrieveImagePullSecret` event appeared; the remaining event is historical.
- Credential operator -> provisions the GHCR pull credential -> evidence demonstrates the PAT is least privilege. **Provisioned:** a dedicated 30-day classic PAT with `read:packages` only was created through the browser flow and stored in Secret Manager; ciphertext intentionally cannot disclose its value.
- Source and GitOps gates -> run after changes -> all required checks pass. **Verified:** source gates and the pipeline cold-pull job passed.

## Constraints

- No fake/synthetic shortcut added solely for checks; use the existing Phase 1 generator and Gold transforms.
- No plaintext credentials in Git, logs, reports, shell history, or conversation output.
- Argo CD remains the only mutator for managed workload manifests.
- Phase 1 contracts and Phase 2 MCP/RBAC/SSE contracts remain stable.

## Phases

1. Secure credential provisioning and GitOps secret contract — complete; dedicated read-only package credential provisioned and web pull-secret reconciliation verified.
2. Persistent MinIO and Phase 1 Gold production workload — complete; persisted object listing survived a MinIO pod restart.
3. Feast batch materialization and readiness verification — complete.
4. GitOps rollout, cold-pull test, live analyst acceptance — mostly verified; batch and web cold-pull paths passed, while post-materialization cited analyst acceptance remains open.
5. Full tests, review, documentation and plan sync — complete for recorded source checks and this evidence audit.

## Verification record

- GitHub Actions workflow dispatch `31818827736`: lint, tests, phase5 verification, build and cosign all passed; immutable image digest `sha256:a58f381abd0e8cdb0066a12ba18566e4e8e9deb4282e88d85be3a72f04d3e0c9`.
- GitOps PRs `#78` and `#79` merged; Argo `platform-data` is `Synced/Healthy` at revision `22d6446d44419d4df264a5136a4ecc97cfba181f`.
- Manual cold-pull job completed after a 1m32s pull of digest `sha256:a58f381abd0e8cdb0066a12ba18566e4e8e9deb4282e88d85be3a72f04d3e0c9`; it verified 843 Gold rows, 16 risk rows, and non-null NVL `company_risk_features` in Redis.
- Source quality gate: 318 tests passed; Ruff, Black and Compose config passed. The first failed run was corrected for missing `boto3` and string event timestamps.

## Residual verification gaps

- MinIO persistence across restart: closed by pod recreation and post-restart listing of 19 Gold/lake objects.
- Analyst answer quality after materialization: the cited browser success occurred before the new materialization and used null online feature values.
- Web workload pull-secret path: closed by recreating the web pod after Secret reconciliation; it became Ready with no new pull-secret event. One historical warning remains.
- GHCR PAT privilege: provisioned through the GitHub UI with `read:packages` only; the token value is not stored in the repository or reports.

## Rollback

- Revert GitOps commits to the prior immutable manifests and digest.
- Preserve PVCs during workload rollback; do not delete stored Gold or Redis data.
- Revoke the dedicated GHCR PAT and delete only its named Secret Manager version if rollback requires credential retirement.
