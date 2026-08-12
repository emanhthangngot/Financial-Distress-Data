# Evidence — CI/CD Job 1 (stream feature → OFFLINE)

Proves `.github/workflows/phase2-stream-feature-offline.yaml` calling the
reusable `.github/workflows/phase2-ci.yaml` template (lint → test → build →
push immutable GHCR digest → open a GitOps digest-bump PR) runs end to end on
a real push to `dev`, deploying `src/ml/feast/offline_job.py`
(`dags/phase2/phase2_stream_feature_offline.py`).

- rubric_id: LLM-ci-cd-job-1
- execution_timestamp: 2026-08-09T06:41:12+00:00
- source_sha: 52dc00c17e69cdc46403f377ae83f00a5406fac5
- gitops_sha: a9491d1a0164f098e0de02ab6cebec39752dc8c0
- versions: financial-distress-data@94774e5, docker/build-push-action@v5, docker/login-action@v3, ghcr.io/emanhthangngot/financial-distress-data/stream-feature-offline
- command: `git push origin dev` (merge of PR #54) triggering `phase2-stream-feature-offline.yaml` on the `push` event; workflow run watched via `gh run list --branch dev` and `gh run view <id> --json jobs`
- expected_result: all four jobs (`lint`, `test`, `build`, `gitops-pr`) succeed; `build` pushes an immutable digest to GHCR; `gitops-pr` opens a PR in `financial-distress-gitops` bumping `pipelines/stream-feature-offline/digest.txt` to that digest
- actual_result: run [31300863227](https://github.com/emanhthangngot/Financial-Distress-Data/actions/runs/31300863227) — `lint` success, `test` success, `build` success (pushed `ghcr.io/emanhthangngot/financial-distress-data/stream-feature-offline:94774e59ba72a815005ed2ea93874c1424a24676`, digest `sha256:a0f8f194774d07ce9df95bd0cdbe3481910c8cc3c9ec4f15588658ad6db9cb67`), `gitops-pr` success — opened [financial-distress-gitops#3](https://github.com/emanhthangngot/financial-distress-gitops/pull/3) bumping `pipelines/stream-feature-offline/digest.txt` to the same digest, base `master` (the gitops repo's real default branch — two earlier attempts on the same run chain failed with a hardcoded `--base main` and a missing `packages: write` permission; both fixed in PRs #53/#54 before this run)
- redaction_status: reviewed — source repository is public, GitOps repository is private; secret values are masked and absent from this evidence

## Command output (real run)

```
$ gh run view 31300863227 --json jobs --jq '.jobs[] | {name,conclusion}'
{"conclusion":"success","name":"ci / lint"}
{"conclusion":"success","name":"ci / test"}
{"conclusion":"success","name":"ci / build"}
{"conclusion":"success","name":"ci / gitops-pr"}

$ gh pr list --repo emanhthangngot/financial-distress-gitops
3	chore(stream-feature-offline): bump image digest	digest-bump/stream-feature-offline-94774e59ba72	OPEN

$ gh api 'repos/emanhthangngot/financial-distress-gitops/contents/pipelines/stream-feature-offline/digest.txt?ref=digest-bump/stream-feature-offline-94774e59ba72' --jq '.content' | base64 -d
sha256:a0f8f194774d07ce9df95bd0cdbe3481910c8cc3c9ec4f15588658ad6db9cb67
```

## Prerequisite fixes made to unblock this run

Three real bugs found and fixed while getting this row from `startup_failure`
to `success`, all in `.github/workflows/phase2-ci.yaml` / the three caller
workflows:

1. Callers lacked `permissions: packages: write` — the repo's default
   `GITHUB_TOKEN` permission is read-only, so the nested `build` job's
   `packages: write` request was rejected before any job ran
   (`startup_failure`). Fixed by adding `permissions: contents: read,
   packages: write` to each caller workflow.
2. `docker/build-push-action` tag used `github.repository` directly, which
   preserves the repo's mixed-case name (`Financial-Distress-Data`); GHCR
   tags must be all-lowercase. Fixed with a `tr '[:upper:]' '[:lower:]'` step
   feeding the tag.
3. `gitops-pr`'s `gh pr create` ran without `--repo`, so it defaulted to the
   calling repo (via `$GITHUB_REPOSITORY`) instead of the checked-out
   `gitops/` subdirectory, and separately hardcoded `--base main` when the
   gitops repo's actual default branch is `master`. Fixed with an explicit
   `--repo emanhthangngot/financial-distress-gitops --base master`.
