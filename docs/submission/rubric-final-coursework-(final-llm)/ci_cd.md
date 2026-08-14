---
title: "CI/CD"
date: 2026-08-14
status: active
---

# CI/CD: six deployables through the same reusable lint→test→build→sign→GitOps-PR template

This doc proves the six rows in "CI/CD": one reusable template
(`.github/workflows/phase2-ci.yaml`) drives lint, test, build, cosign sign,
push an immutable GHCR digest, and open a GitOps digest-bump/manifest-rewrite
PR — for the coordinator agent, feature agent, drift agent, and RAG data
pipeline deployables, plus the two Feast stream-feature jobs. No secret is
embedded in code — GHCR auth and cosign signing use GitHub Actions' own
token/OIDC identity. It does not prove blue/green or canary deployment
strategy — every merge here is a rolling digest bump.

**Active deployment facts:** `.github/workflows/phase2-ci.yaml` (reusable
template) called by 6 caller workflows; `sigstore/cosign-installer@v3.7.0`;
GitOps target repo `financial-distress-gitops` (private, default branch
`master`).

## Part I — Six real CI runs

| Deployable | Workflow | Run | GitOps PR | Result |
|---|---|---|---|---|
| coordinator | `phase2-agent-coordinator.yaml` | [31410264103](https://github.com/emanhthangngot/Financial-Distress-Data/actions/runs/31410264103) | [gitops#29](https://github.com/emanhthangngot/financial-distress-gitops/pull/29) | 5/5 jobs success, merged |
| feature-agent | `phase2-agent-feature.yaml` | [31410263833](https://github.com/emanhthangngot/Financial-Distress-Data/actions/runs/31410263833) | [gitops#30](https://github.com/emanhthangngot/financial-distress-gitops/pull/30) | 5/5 jobs success, merged |
| drift-agent | `phase2-agent-drift.yaml` | [31410267509](https://github.com/emanhthangngot/Financial-Distress-Data/actions/runs/31410267509) | [gitops#27](https://github.com/emanhthangngot/financial-distress-gitops/pull/27) | 5/5 jobs success, merged |
| RAG data pipeline | `phase2-rag-pipeline.yaml` | [31405317841](https://github.com/emanhthangngot/Financial-Distress-Data/actions/runs/31405317841) | [gitops#24](https://github.com/emanhthangngot/financial-distress-gitops/pull/24) | 5/5 jobs success (2nd attempt), merged; `platform-data` Argo app `Synced` |
| stream-feature-offline (Job 1) | `phase2-stream-feature-offline.yaml` | [31300863227](https://github.com/emanhthangngot/Financial-Distress-Data/actions/runs/31300863227) | [gitops#3](https://github.com/emanhthangngot/financial-distress-gitops/pull/3) | 4/4 jobs success |
| stream-feature-online (Job 2) | `phase2-stream-feature-online.yaml` | [31300863194](https://github.com/emanhthangngot/Financial-Distress-Data/actions/runs/31300863194) | [gitops#2](https://github.com/emanhthangngot/financial-distress-gitops/pull/2) | 4/4 jobs success |

Real digests landed in real manifests, verified after merge — e.g. the
drift-agent Deployment:

```text
$ git show origin/master:platform/agents/agent-deployments.yaml | grep drift-agent -A1 | grep image
image: ghcr.io/emanhthangngot/financial-distress-data/drift-agent@sha256:b29bdbf2c7859d28c3c8eea7fcda6df8a262014f37a664f077dfbc93e4ca7b47
```

Full evidence: each row links to its own file under
[`docs/phase2/evidence/llm/LLM-ci-cd-*.md`](../../phase2/evidence/llm/).

## Part II — Real bugs found and fixed while building the reusable template

Three infrastructure bugs surfaced on the first CI runs and were fixed once
in `phase2-ci.yaml`, benefiting all six caller workflows — not patched
per-workflow:

1. **Missing `packages: write` permission.** The repo's default
   `GITHUB_TOKEN` is read-only; the `build` job's GHCR push was rejected
   before any job ran (`startup_failure`). Fixed with
   `permissions: contents: read, packages: write` on each caller.
2. **Uppercase GHCR tag.** `docker/build-push-action`'s tag used
   `github.repository` directly, preserving the mixed-case repo name
   (`Financial-Distress-Data`); GHCR tags must be lowercase. Fixed with a
   `tr '[:upper:]' '[:lower:]'` step.
3. **Wrong GitOps repo/branch target.** `gitops-pr`'s `gh pr create` ran
   without `--repo`, defaulting to the calling repo, and hardcoded
   `--base main` when the GitOps repo's real default branch is `master`.
   Fixed with an explicit `--repo emanhthangngot/financial-distress-gitops
   --base master`.

A fourth, RAG-pipeline-specific bug: the target GitOps path
(`platform/data/pipeline-deployments.yaml`) existed only on an unmerged
GitOps branch, not on `master`, which is what CI checks out — the first
`gitops-pr` attempt failed a `test -f "$GITOPS_PATH"` guard. Fixed by merging
that branch to `master` first, then re-running.

## Limitations

Every CI run here is a rolling digest-bump merged directly to the GitOps
`master` branch through a reviewed PR — there is no staged canary or
blue/green rollout strategy; Argo CD's own rolling-update behavior is the
deployment strategy in effect. Two runs (drift-agent, feature-agent) show a
benign race between a `push`-triggered run and a manual `workflow_dispatch`
run targeting the same short-SHA branch name — expected behavior of two
independent CI triggers, not a template defect, and disclosed rather than
hidden.

## References

- cosign: https://docs.sigstore.dev/cosign/overview/
- GitHub Actions reusable workflows: https://docs.github.com/en/actions/using-workflows/reusing-workflows
</content>
