# Evidence — CI/CD for the feature ("kéo dữ liệu") agent

Proves `.github/workflows/phase2-agent-feature.yaml` runs the reusable CI
template end to end for the `feature-agent` deployable: build → cosign sign
→ push immutable GHCR digest → open a GitOps PR rewriting the real
`feature-agent` `Deployment` in `platform/agents/agent-deployments.yaml`.

- rubric_id: LLM-ci-cd-agent-k-o-d-li-u
- execution_timestamp: 2026-08-10T23:41:37+07:00
- source_sha: 09640b7ede4848f47be9dd9a1cd11b4d041a7170
- gitops_sha: 1d0ebb619ed04651f7e639cb25d3eb968766b685
- versions: sigstore/cosign-installer@v3.7.0, ghcr.io/emanhthangngot/financial-distress-data/feature-agent
- command: `git push origin main` (merge of PR #63, `dev`→`main`) triggering `phase2-agent-feature.yaml` on the `push` event (the merge diff touched `apps/feature-mcp/**`/`src/agents/**`, matching the workflow's path filter)
- expected_result: `lint`, `test`, `build`, `phase5-verification`, `gitops-pr` all succeed; the pushed image is cosign-signed; `gitops-pr` rewrites the `feature-agent` `Deployment`'s `image:` field with a real digest and opens a PR against `master`
- actual_result: run [31410263833](https://github.com/emanhthangngot/Financial-Distress-Data/actions/runs/31410263833) — all 5 jobs succeeded; opened [financial-distress-gitops#30](https://github.com/emanhthangngot/financial-distress-gitops/pull/30) rewriting the `feature-agent` Deployment's `image:` to `sha256:131f5c4a13b0a2c9744cc37872eed79e3016b4922c4c172bc805295294f8ab32`; merged into `master`
- redaction_status: reviewed — source repository is public, GitOps repository is private; no secret values in this file

## Command output (real run)

```
$ gh run view 31410263833 --json jobs --jq '.jobs[] | {name,conclusion}'
{"conclusion":"success","name":"ci / lint"}
{"conclusion":"success","name":"ci / test"}
{"conclusion":"success","name":"ci / phase5-verification"}
{"conclusion":"success","name":"ci / build"}
{"conclusion":"success","name":"ci / gitops-pr"}

$ git show origin/master:platform/agents/agent-deployments.yaml | grep feature-agent -A1 | grep image
image: ghcr.io/emanhthangngot/financial-distress-data/feature-agent@sha256:131f5c4a13b0a2c9744cc37872eed79e3016b4922c4c172bc805295294f8ab32
```

## Notes

A concurrent `workflow_dispatch` run of the same workflow (triggered
manually before the `push` trigger was known to also fire) raced the same
`digest-bump/feature-agent-<sha>` branch name and lost the `git push` with a
"fetch first" rejection — an expected outcome of two independent CI runs
targeting an identical short-SHA branch name, not a defect in the reusable
template. The `push`-triggered run above is the one whose PR was merged.
