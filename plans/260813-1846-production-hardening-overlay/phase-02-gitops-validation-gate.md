---
phase: 2
title: "GitOps repo validation gate"
status: in_progress
priority: P1
effort: "1.5d"
dependencies: [1]
---

# Phase 2: GitOps repo validation gate

## Overview

The GitOps control repo holds the artifacts for 48 rubric rows and has no CI, no
validation script and no agent rules. This phase gives it all three, modelled on
the two studied reference repos, and extends the source repo's preflight to cover
it.

No cloud quota required — everything renders and validates offline.

## Requirements

- Functional: every chart renders, every manifest validates against the Kubernetes
  schema, Terraform formats and validates, every image reference is digest-pinned,
  and no secret-shaped string can be committed.
- Non-functional: the whole gate runs in under three minutes on a cold runner and
  needs no cluster credentials.

## Architecture

Two patterns converge here and both are adopted.

From `yas-cd` (`scripts/validate-gitops.sh` + `.github/workflows/validate-gitops.yml`):
render every overlay, diff the rendered image list against a catalog, assert
policy invariants, grep for secret patterns, and `git diff --check`. Its
service-catalog diff is the transferable idea; its Spring gateway-route and
active/dormant-overlay checks are microservice-specific and are **not** copied.

From `RecSys-MLops` (`make full-cicd-preflight`): one command chaining config
validation, `helm lint` + `helm template` over every chart, `terraform fmt -check`
+ `validate`, `bash -n` over every shell script, and a targeted pytest run.

The digest-pin check is the load-bearing one — it is what makes phase 3's
signatures meaningful and phase 5's Kyverno policy enforceable. A tag-based
reference cannot be signature-verified reliably, so the gate rejects any image
reference lacking `@sha256:`.

## Related Code Files

GitOps repo (`~/Studying/FSDS/financial-distress-gitops`):

- Create: `AGENTS.md`
- Create: `scripts/validate-gitops.sh`
- Create: `.github/workflows/validate-gitops.yml`
- Modify: `Makefile` — add `validate` target wrapping the script
- Modify: `README.md` — document the gate

Source repo:

- Create: `scripts/run_phase2_quality_gates.py`
- Modify: `AGENTS.md` — add the Phase 2 gate to Verify Commands

## Implementation Steps

1. Write the GitOps `AGENTS.md`. Hard rules, stated concretely: Argo CD is the
   only path that mutates managed namespaces (no `kubectl apply`/`set image`);
   the source repo may only commit digest bumps; every image is digest-pinned and
   `:latest` is forbidden; never commit real secrets, kubeconfigs or service
   account keys. Include the repo-ownership table mapping `artifact_repo` values
   from the rubric matrix to their owning repo.
2. Write `scripts/validate-gitops.sh` with these checks, each failing loudly:
   `helm lint` and `helm template` for every chart in `charts/`; render each
   `apps/dev/*/values.yaml` against its chart; `kubeconform` every manifest under
   `platform/**` and `argocd/**`; `terraform fmt -check -recursive` and
   `terraform validate` (skip with a printed notice when `.terraform` is absent);
   assert every `image:` reference matches `@sha256:`; grep for secret-shaped
   patterns (`BEGIN PRIVATE`, `BEGIN OPENSSH`, `AKIA`, kubeconfig markers);
   `git diff --check`.
3. Run it locally and fix every finding **before** wiring CI, so the first CI run
   is green rather than a wall of pre-existing violations.
4. Add `.github/workflows/validate-gitops.yml` on `pull_request` and `push` to
   `main`, pinning `helm`, `kubeconform` and `terraform` versions by direct
   download rather than by API-querying installer scripts (the reference repo
   documents rate-limiting pain with the latter).
5. Add `scripts/run_phase2_quality_gates.py` in the source repo: `bash -n` over
   every shell script, the Phase 2 pytest selection, and — when `--gitops-root`
   is supplied — a delegated call to the GitOps validate script.
6. Record the gate in `AGENTS.md` Verify Commands.

## Verification

```bash
# in the gitops repo
scripts/validate-gitops.sh
make validate

# in the source repo
.venv/bin/python scripts/run_phase2_quality_gates.py \
  --gitops-root ~/Studying/FSDS/financial-distress-gitops
.venv/bin/python scripts/run_stage1_quality_gates.py
```

## Success Criteria

- [x] `validate-gitops.sh` -> run on the current GitOps `main` -> exits 0
- [ ] `validate-gitops.sh` -> given a manifest with a tag-based image reference -> fails naming the file and the reference
- [ ] `validate-gitops.sh` -> given a staged private key -> fails on the secret pattern
- [ ] GitOps CI workflow -> opened PR -> runs and blocks merge on failure
- [x] `run_phase2_quality_gates.py --gitops-root ...` -> single command -> covers both repos
- [x] Strict `--track LLM` gate -> unchanged PASS 100/100

## ML rubric rows closed

- CI/CD section (partial): the deploy-time validation half of the CI/CD rows
  (~4 pts). Full CI/CD credit lands with phases 3, 5 and 11.

## Risk Assessment

- **The first script run may surface many pre-existing violations**, particularly
  non-digest-pinned images. Step 3 handles this deliberately before CI exists, so
  remediation is a normal PR rather than a broken pipeline.
- **`kubeconform` needs CRD schemas** for Argo CD, KServe, Kyverno and Gateway API
  objects. Vendor the schema bundle into the repo or point `kubeconform` at the
  upstream schema location with an explicit version pin; do not silently skip
  unknown kinds, which would defeat the check.
