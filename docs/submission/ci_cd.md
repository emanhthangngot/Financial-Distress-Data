# CI/CD

Row: `LLM-AC-12-CICD`. Source CI builds/tests/scans/signs and pushes an
immutable image + digest; a bot opens a GitOps PR changing the digest;
Argo CD reconciles the merged revision. Pushing a tag alone never deploys.

## Implementation present (static)

- The reusable workflow `.github/workflows/phase2-ci.yaml` accepts a caller
  supplied JSON `deployables` matrix. Each entry declares its build, test,
  lint, and kind-and-name-qualified GitOps target; adding a service changes
  that caller input rather than the reusable workflow body.
- Six callers grant `id-token: write`. For a push, the workflow pushes the
  GHCR image, signs its immutable digest through GitHub OIDC and cosign, then
  opens a GitOps pull request that rewrites the declared target only. Pull
  request runs do not push or sign images.
- The Phase 05 coverage and mutation gates run after the per-deployable test
  job and before any image build. Their local reproduction commands are in
  [Validation & Verification](./validation_verification.md).

## Live evidence outstanding

No cluster is running for this work. There is no executed signed release, GitOps
pull request or merge, Argo CD rollout, or runtime A/B result. The static
workflow and manifest-target checks are implementation evidence only; no
`design_only` rubric row may be marked `executed` until those live artifacts
are captured.
