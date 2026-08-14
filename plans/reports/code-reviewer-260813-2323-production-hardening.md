# Code review — production hardening overlay

Scope: source-repo and sibling `financial-distress-gitops` worktree changes for phases 4–12. No files were modified by this review.

## Findings

### Critical — GitOps workloads use non-existent image digests

The new GitOps manifests and API chart defaults pin images to all-zero SHA-256 values (for example `platform/data-phase1/*.yaml`, `platform/data/lakehouse/*.yaml`, and `charts/{drift-api,feature-api}/values.yaml`). These are syntactically digest-shaped but cannot be pulled and cannot have a cosign signature. The resulting cluster cannot start the data plane or APIs, and this violates the repository rule against fake evidence/data. The image-pin validator only checks the shape, so it currently misses this blocker.

### High — invalid Kubernetes API kind prevents Phase 1 deployment

`platform/data-phase1/airflow.yaml:1-3` declares `kind: Deployment` under `apiVersion: batch/v1`; Deployments are `apps/v1`. A cluster apply will reject this object before Airflow starts.

### High — API charts probe endpoints the applications do not expose

Both API applications expose only `/health` (`apps/drift-api/app/main.py` and `apps/feature-api/app/main.py`). The sibling Helm charts probe `/readyz` and `/healthz`, and their ServiceMonitors scrape `/metrics`. Consequently the pods remain unready (and rollout analyses have no application metrics), so the progressive-delivery acceptance path cannot succeed.

### High — Phase 1 runtime image is missing its declared runtime dependencies

`infra/phase1-cluster/Dockerfile.pipeline:21-22` installs only `pandas` and `pyyaml`, but its entrypoint `scripts.run_stage1_evidence` imports the Phase 1 runtime stack (`duckdb`, `kafka-python`, `minio`, `pyarrow`, `psycopg`, and related packages). The image will fail at import time in the cluster; copying `pyproject.toml`/`uv.lock` without installing the runtime extra does not provide those packages.

### High — CDC reconciliation can report a false successful match with no data

`src/cdc/reconcile.py:run_reconciliation_task` reads `generator_rows` and `cdc_rows` only from optional context keys. The Airflow wrapper does not supply either key, so the normal task invocation returns a zero-row report with `matched: true`/`status: "matched"`. This is a false-green comparison rather than evidence that both Bronze paths reconcile.

### High — evidence capture does not implement the phase-12 contract

`configs/evidence-checklist.yaml` contains only three generic sections, not the rubric sections/artifact set described by phase 12. `scripts/capture_phase2_evidence.py` records `screenshot_declared` but never invokes a screenshot capture or `stamp_phase2_evidence.py`; it emits only command logs and a small manifest. `--all` therefore cannot regenerate the full screenshot/manifest set or stamp the eight evidence-contract fields.

### High — supply-chain workflow is incomplete and verification is fail-open on empty output

`.github/workflows/phase2-ci.yaml:130-139` installs cosign and signs the image, but has no Syft SBOM or SLSA/GitHub attestation step despite the phase-03 acceptance criteria. `scripts/verify_supply_chain.py:_cosign_json` returns `None` for an empty successful cosign stdout and `verify_supply_chain` still returns a successful `VerificationResult`; a broken/mocked verifier can therefore claim verification without a signature, provenance, or SBOM.

### High — newly added CDC/Phase-1 components are not deployables in the CI catalog

`configs/phase2-deployables.yaml` still contains only the original eight deployables and no CDC or Phase-1 pipeline image; `infra/cdc/` is absent. The caller workflows continue to carry duplicated hand-written JSON instead of consuming this catalog. Thus the new components have no build/sign/digest-bump path and cannot satisfy the supply-chain/admission contract.

### High — Kyverno signature subject excludes the branch used to build images

`platform/security/policies/require-signed-images.yaml:27-30` accepts only keyless certificates for `refs/heads/main`, while the reusable CI is triggered on both `main` and `dev` and the GitOps repo deploys from `master`. Images built from `dev` will be rejected once signature verification is enforced, even when correctly signed.

### Medium — real MLflow backend drops reproducibility metadata

`src/ml/mlflow_registry.py:55-63` calls `mlflow.register_model` but never logs/attaches the supplied `manifest` (or metrics) to the MLflow run/version. The local JSON fallback stores it, so tests pass while a real MLflow deployment loses the source/data/environment lineage required by the manifest contract.

### Medium — rollout-enabled HPA targets a Deployment that is not rendered

Both API charts suppress the Deployment when `rollout.enabled` is true, but the HPA template still renders whenever `autoscaling.enabled` and `autoscaling.keda.enabled` are true/false as configured and always targets `kind: Deployment`. Flipping progressive delivery on with the default CPU HPA path leaves the HPA targeting a nonexistent object.

### Medium — admission policies are not yet enforcing the stated acceptance behavior

`require-digest-pinned.yaml`, `require-signed-images.yaml`, `require-non-root.yaml`, and `require-resource-limits.yaml` all use `validationFailureAction: Audit` (only the latest-tag policy is Enforce). The phase acceptance requires unsigned and non-digest images to be rejected; the current manifests can only report violations until a separate enforcement change lands.

## Verification performed

- Focused Phase 2 tests: **50 passed**.
- Focused Ruff and Black checks: **pass**.
- `scripts/validate-gitops.sh`: exits 0, but skips kubeconform because it is not installed and accepts all-zero digest strings as valid pins.
- `audit_phase2_evidence.py --matrix-only --strict --check-artifacts --gitops-root ../financial-distress-gitops --track LLM`: exits 0; this validates matrix/path shape, not live image existence, runtime readiness, or evidence completeness.

Status: DONE_WITH_CONCERNS

Concerns/Blockers: Critical/High findings above block a production-shaped or submission-grade claim. The matrix remains syntactically 100/100, but the live/runtime and evidence acceptance criteria are not met.
