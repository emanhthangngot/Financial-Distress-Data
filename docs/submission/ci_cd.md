# CI/CD

Historical evidence for `LLM-AC-12-CICD`: the captured workflow tested, signed,
and pushed an image, then opened a GitOps PR for Argo CD to reconcile. See the
[pinned workflow](https://github.com/emanhthangngot/Financial-Distress-Data/blob/9ec6f065276d316bad1e308c88028c5662edc4db/.github/workflows/phase2-ci.yaml)
for that deployment path and [current source CI](../../.github/workflows/phase2-ci.yaml)
for today's signed-image handoff without deployment.

## Historical implementation (static)

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

## Evidence status

The CI/CD rows are executed. The Phase 05 evidence package records signed
digest releases, GitOps digest updates, and the validation gates for the RAG
pipeline and three agents. Routing and observability are separate rubric
sections with their own linked runtime captures; they do not change the CI/CD
status. Final submission freeze still requires SHA restamping and the strict
two-repository audit.
