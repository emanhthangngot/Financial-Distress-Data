# Evidence — CI/CD for the RAG data pipeline

Proves `.github/workflows/phase2-rag-pipeline.yaml` calling the reusable
`.github/workflows/phase2-ci.yaml` template runs the full sign → push →
digest → GitOps PR → merge → Argo reconcile loop end to end, targeting the
real `platform/data/pipeline-deployments.yaml` CronJob manifest (not the old
`pipelines/<name>/digest.txt` placeholder nothing consumed).

- rubric_id: LLM-ci-cd-ci-cd-cho-rag-data-pipeline
- execution_timestamp: 2026-08-10T22:48:51+07:00
- source_sha: 52dc00c17e69cdc46403f377ae83f00a5406fac5
- gitops_sha: a9491d1a0164f098e0de02ab6cebec39752dc8c0
- versions: sigstore/cosign-installer@v3.7.0, docker/build-push-action@v5, financial-distress-data@ddea8d4
- command: `git push origin dev` (merge of PR #61/#62 into `dev`, then `dev`→`main` merge PR #63) triggering `phase2-rag-pipeline.yaml`; watched via `gh run list --branch dev` and `gh run view <id> --json jobs`
- expected_result: `lint`, `test`, `build`, `phase5-verification`, `gitops-pr` all succeed; the pushed image is cosign-signed; `gitops-pr` rewrites the `rag-pipeline` CronJob's `image:` field in `platform/data/pipeline-deployments.yaml` with a real `sha256:` digest and opens a PR against `master`; merging it and letting Argo sync changes the CronJob's pinned image
- actual_result: run [31405317841](https://github.com/emanhthangngot/Financial-Distress-Data/actions/runs/31405317841) — all jobs succeeded (after fixing the `gitops-pr` target existing only on the `phase5/digest-content-on-master` branch, not yet merged to `master` — see below); opened [financial-distress-gitops#24](https://github.com/emanhthangngot/financial-distress-gitops/pull/24) rewriting `image:` in the `rag-pipeline` CronJob to `sha256:6b3dcfced599cdfc321415804f6ef955d7b49b429f1293e1bf0b4f4b8119fc6e`; merged; `kubectl get application platform-data -n argocd` showed `Synced` at the merge commit and `kubectl get cronjob rag-pipeline -n phase2-data` showed the new digest in its pinned `image:` field
- redaction_status: reviewed — source repository is public, GitOps repository is private; no secret values in this file

## Command output (real run)

```
$ gh run view 31405317841 --json jobs --jq '.jobs[] | {name,conclusion}'
{"conclusion":"success","name":"ci / lint"}
{"conclusion":"success","name":"ci / test"}
{"conclusion":"success","name":"ci / phase5-verification"}
{"conclusion":"success","name":"ci / build"}
{"conclusion":"success","name":"ci / gitops-pr"}

$ kubectl get cronjob rag-pipeline -n phase2-data -o jsonpath='{.spec.jobTemplate.spec.template.spec.containers[0].image}'
ghcr.io/emanhthangngot/financial-distress-data/rag-pipeline@sha256:6b3dcfced599cdfc321415804f6ef955d7b49b429f1293e1bf0b4f4b8119fc6e

$ kubectl get application platform-data -n argocd -o jsonpath='{.status.sync.status} {.status.sync.revision}'
Synced b1fdd4408cfd9bace01f0f09c278364e61edcca1
```

## Real bug found and fixed to unblock this run

The first attempt on this run's `gitops-pr` job failed: `test -f
"$GITOPS_PATH"` on `platform/data/pipeline-deployments.yaml` — that file
existed only on an unmerged GitOps branch (`phase5/digest-content-on-master`),
not on `master`, which is what the CI job checks out. Merged that branch to
`master` first (financial-distress-gitops#23), then re-ran the failed job —
succeeded on the second attempt.
