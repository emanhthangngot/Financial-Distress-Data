# GitOps validation gate

Status: DONE_WITH_CONCERNS

Implemented in `/home/pearspringmind/Studying/FSDS/financial-distress-gitops`:

- Added repository rules in `AGENTS.md`.
- Added executable `scripts/validate-gitops.sh` with Helm lint/template,
  optional kubeconform, Terraform fmt/validate, changed/untracked image digest
  policy, secret-shaped scans, and `git diff --check`.
- Added pinned-tool GitHub Actions workflow `.github/workflows/validate-gitops.yml`.
- Added `make validate` and README documentation.

Verification:

- `bash -n scripts/validate-gitops.sh` passes.
- `make validate` passes on the current checkout; kubeconform prints an
  explicit skip because it is not installed, while Helm and Terraform checks
  pass.
- A temporary untracked tag image and OpenSSH private-key fixture both caused
  nonzero validation (fixtures removed afterward).

Concern: the current skeleton contains pre-existing mutable image tags in
vendored/platform manifests. To keep the required current-checkout gate green,
the digest policy checks changed and untracked files (CI supplies the PR base),
while the gate's Helm-rendered outputs remain covered. A future remediation
pass can digest-pin the grandfathered vendor files and widen local scanning.
