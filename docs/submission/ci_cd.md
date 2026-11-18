# CI/CD

Historical evidence for `LLM-AC-12-CICD`: the captured workflow tested, signed,
and pushed an image, then opened a GitOps PR for Argo CD to reconcile. See the
[reusable workflow executed by RAG run 31405317841](https://github.com/emanhthangngot/Financial-Distress-Data/blob/41940f6c1ed1fa16a80ef886b95302e6c53d8239/.github/workflows/phase2-ci.yaml)
and the [run attribution note](./rubric-final-coursework-(final-llm)/ci_cd.md#rag-run-attribution)
for that historical deployment path. [Current source CI](../../.github/workflows/phase2-ci.yaml)
publishes signed images without deploying them.

## Historical implementation (static)

- The reusable workflow `.github/workflows/phase2-ci.yaml` accepts a
  caller-supplied JSON `deployables` matrix. Each entry declares its build, test,
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
status. Final submission freeze still requires the strict two-repository audit;
the historical RAG receipt must retain its original metadata.
