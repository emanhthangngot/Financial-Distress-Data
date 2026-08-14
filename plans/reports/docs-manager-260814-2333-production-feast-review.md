---
title: Production Feast and GHCR documentation accuracy review
date: 2026-08-14
phase: 2
status: completed
---

# Production Feast and GHCR documentation accuracy review

## Summary

Audited the production Feast/GHCR plan against the supplied runtime evidence and incident journal. The overall plan is now `partially-verified`: successful materialization, the batch-job cold pull, GitOps reconciliation, and source gates remain recorded, while four unproved acceptance paths are explicitly open.

## Findings

- Digest `sha256:a58f381abd0e8cdb0066a12ba18566e4e8e9deb4282e88d85be3a72f04d3e0c9` cold-pulled in 1m32s for the batch job, which completed with 843 Gold rows, 16 risk rows, and non-null NVL online features.
- MinIO uses a `Bound` PVC, but its pod was created at 16:00 with `restartCount: 0`; persistence across restart is not verified.
- The cited browser response predates the new materialization. The incident journal explicitly records null online values, so a cited answer based on non-null post-materialization features is not verified.
- The SealedSecret reports `Synced=True`, and the Docker config Secret exists. The web pod previously emitted `FailedToRetrieveImagePullSecret`, and no post-secret web cold pull verifies that workload path.
- SealedSecret ciphertext does not reveal PAT scopes; least-privilege scope remains unverified.

## Documentation changes

- Reclassified the plan and affected phases from complete to partially verified or implemented-with-open-verification.
- Rewrote acceptance criteria as `WHO -> ACTION -> RESULT` statements with evidence status.
- Added a residual verification gaps section so batch-job evidence is not overgeneralized to MinIO restart, analyst, web-pod, or token-scope acceptance.

## Unresolved questions

- Will a controlled MinIO pod restart retain and re-read the expected Gold objects?
- Will a fresh authenticated analyst request after materialization cite a completed answer based on non-null NVL values?
- Will a newly scheduled web pod cold-pull the immutable digest without pull-secret warnings?
- What scopes are configured on the GHCR PAT, and do they satisfy the intended least-privilege policy?
