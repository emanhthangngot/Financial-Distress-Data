# Evidence — CI/CD Job 2 (stream feature → ONLINE)

Proves `.github/workflows/phase2-stream-feature-online.yaml` calling the
reusable `.github/workflows/phase2-ci.yaml` template (lint → test → build →
push immutable GHCR digest → open a GitOps digest-bump PR) runs end to end on
a real push to `dev`, deploying `src/ml/feast/online_job.py`
(`dags/phase2/phase2_stream_feature_online.py`).

- rubric_id: LLM-ci-cd-job-2
- execution_timestamp: 2026-08-09T06:41:12+00:00
- source_sha: 758722c52ef3035a7e3f9464dc03c5a39e50a74e
- gitops_sha: 921bdc1075ef8335e0f509747bd64db2d525f73e
- versions: financial-distress-data@94774e5, docker/build-push-action@v5, docker/login-action@v3, ghcr.io/emanhthangngot/financial-distress-data/stream-feature-online
- command: `git push origin dev` (merge of PR #54) triggering `phase2-stream-feature-online.yaml` on the `push` event; workflow run watched via `gh run list --branch dev` and `gh run view <id> --json jobs`
- expected_result: all four jobs (`lint`, `test`, `build`, `gitops-pr`) succeed; `build` pushes an immutable digest to GHCR; `gitops-pr` opens a PR in `financial-distress-gitops` bumping `pipelines/stream-feature-online/digest.txt` to that digest
- actual_result: run [31300863194](https://github.com/emanhthangngot/Financial-Distress-Data/actions/runs/31300863194) — `lint` success, `test` success, `build` success (pushed `ghcr.io/emanhthangngot/financial-distress-data/stream-feature-online:94774e59ba72a815005ed2ea93874c1424a24676`, digest `sha256:1fdb71c97b4952211ca759409bb93f314e7a69c834681950f9e1fb36811e9b7e`), `gitops-pr` success — opened [financial-distress-gitops#2](https://github.com/emanhthangngot/financial-distress-gitops/pull/2) bumping `pipelines/stream-feature-online/digest.txt` to the same digest, base `master` (the gitops repo's real default branch — two earlier attempts on the same run chain failed with a hardcoded `--base main` and a missing `packages: write` permission; both fixed in PRs #53/#54 before this run)
- redaction_status: reviewed — source repository is public, GitOps repository is private; secret values are masked and absent from this evidence

## Command output (real run)

```
$ gh run view 31300863194 --json jobs --jq '.jobs[] | {name,conclusion}'
{"conclusion":"success","name":"ci / lint"}
{"conclusion":"success","name":"ci / test"}
{"conclusion":"success","name":"ci / build"}
{"conclusion":"success","name":"ci / gitops-pr"}

$ gh pr list --repo emanhthangngot/financial-distress-gitops
2	chore(stream-feature-online): bump image digest	digest-bump/stream-feature-online-94774e59ba72	OPEN

$ gh api 'repos/emanhthangngot/financial-distress-gitops/contents/pipelines/stream-feature-online/digest.txt?ref=digest-bump/stream-feature-online-94774e59ba72' --jq '.content' | base64 -d
sha256:1fdb71c97b4952211ca759409bb93f314e7a69c834681950f9e1fb36811e9b7e
```

## Prerequisite fixes made to unblock this run

Same three bugs as `LLM-ci-cd-job-1` (`docs/phase2/evidence/llm/LLM-ci-cd-job-1.md`)
in the shared `phase2-ci.yaml` template — missing `packages: write`
permission on the callers, an uppercase GHCR image tag, and `gitops-pr`
targeting the wrong repo/branch (`--base main` when the gitops repo's default
is `master`). Fixed once in `phase2-ci.yaml` / the three caller workflows,
benefiting all three phase-2 pipelines.
