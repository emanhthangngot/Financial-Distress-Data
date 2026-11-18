---
title: "CI/CD"
date: 2026-08-14
status: active
---

# CI/CD: six coursework deployables through a reusable build, signing and GitOps handoff

This document records the coursework CI/CD runs: a reusable workflow linted,
tested, built, signed and published immutable GHCR image digests, then opened
GitOps PRs for the coordinator, feature and drift agents, RAG data pipeline,
and the two Feast stream-feature jobs. The capture used GitHub Actions identity
for registry authentication and Sigstore signing. The recorded deployments
were rolling digest bumps, not blue/green or canary releases.

The [reusable workflow executed by the RAG run](https://github.com/emanhthangngot/Financial-Distress-Data/blob/41940f6c1ed1fa16a80ef886b95302e6c53d8239/.github/workflows/phase2-ci.yaml)
shows the historical GitOps handoff. The [current source workflow](../../../.github/workflows/phase2-ci.yaml)
publishes signed images without opening deployment PRs.

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

Full evidence, one file per deployable:
[`LLM-ci-cd-agent-l-m-coordinator.md`](../../platform/evidence/llm/LLM-ci-cd-agent-l-m-coordinator.md) (coordinator),
[`LLM-ci-cd-agent-k-o-d-li-u.md`](../../platform/evidence/llm/LLM-ci-cd-agent-k-o-d-li-u.md) (feature-agent),
[`LLM-ci-cd-agent-drift-detection.md`](../../platform/evidence/llm/LLM-ci-cd-agent-drift-detection.md) (drift-agent),
[`LLM-ci-cd-ci-cd-cho-rag-data-pipeline.md`](../../platform/evidence/llm/LLM-ci-cd-ci-cd-cho-rag-data-pipeline.md) (RAG pipeline),
[`LLM-ci-cd-job-1.md`](../../platform/evidence/llm/LLM-ci-cd-job-1.md) (stream-feature-offline),
[`LLM-ci-cd-job-2.md`](../../platform/evidence/llm/LLM-ci-cd-job-2.md) (stream-feature-online).

### RAG run attribution

The [GitHub Actions REST record for run 31405317841](https://api.github.com/repos/emanhthangngot/Financial-Distress-Data/actions/runs/31405317841)
reports `41940f6c1ed1fa16a80ef886b95302e6c53d8239` for both the
[RAG caller](https://github.com/emanhthangngot/Financial-Distress-Data/blob/41940f6c1ed1fa16a80ef886b95302e6c53d8239/.github/workflows/phase2-rag-pipeline.yaml)
(`head_sha`) and the reusable workflow (`referenced_workflows[].sha`).
The [original receipt](../../platform/evidence/llm/LLM-ci-cd-ci-cd-cho-rag-data-pipeline.md)
points to that successful run but records `source_sha`
`9ec6f065276d316bad1e308c88028c5662edc4db`. The receipt is preserved
unchanged; its stamp is not the executed workflow revision. The requirement
check uses local Git history to inspect the executed workflow and verifies the
receipt's original stamp and run URL without calling GitHub.

## Part II — Real bugs found and fixed while building the reusable template

Three infrastructure bugs surfaced on the first CI runs and were fixed once
in the reusable workflow, benefiting all six historical callers.

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
