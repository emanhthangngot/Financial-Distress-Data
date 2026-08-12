# Evidence — CI/CD for the drift-detection agent

Proves `.github/workflows/phase2-agent-drift.yaml` runs the reusable CI
template end to end for the `drift-agent` deployable: build → cosign sign →
push immutable GHCR digest → open a GitOps PR rewriting the real
`drift-agent` `Deployment` in `platform/agents/agent-deployments.yaml`.

- rubric_id: LLM-ci-cd-agent-drift-detection
- execution_timestamp: 2026-08-10T23:41:40+07:00
- source_sha: 6c13197663dd6e2a11981167a19bd3ca21ce44ea
- gitops_sha: a9491d1a0164f098e0de02ab6cebec39752dc8c0
- versions: sigstore/cosign-installer@v3.7.0, ghcr.io/emanhthangngot/financial-distress-data/drift-agent
- command: `git push origin main` (merge of PR #63, `dev`→`main`) triggering `phase2-agent-drift.yaml` on the `push` event
- expected_result: `lint`, `test`, `build`, `phase5-verification`, `gitops-pr` all succeed; `gitops-pr` rewrites the `drift-agent` `Deployment`'s `image:` field with a real digest and opens a PR against `master`
- actual_result: run [31410267509](https://github.com/emanhthangngot/Financial-Distress-Data/actions/runs/31410267509) — all 5 jobs succeeded; opened [financial-distress-gitops#27](https://github.com/emanhthangngot/financial-distress-gitops/pull/27) rewriting the `drift-agent` Deployment's `image:` to `sha256:b29bdbf2c7859d28c3c8eea7fcda6df8a262014f37a664f077dfbc93e4ca7b47`; merged into `master`
- redaction_status: reviewed — source repository is public, GitOps repository is private; no secret values in this file

## Command output (real run)

```
$ gh run view 31410267509 --json jobs --jq '.jobs[] | {name,conclusion}'
{"conclusion":"success","name":"ci / lint"}
{"conclusion":"success","name":"ci / test"}
{"conclusion":"success","name":"ci / phase5-verification"}
{"conclusion":"success","name":"ci / build"}
{"conclusion":"success","name":"ci / gitops-pr"}

$ git show origin/master:platform/agents/agent-deployments.yaml | grep drift-agent -A1 | grep image
image: ghcr.io/emanhthangngot/financial-distress-data/drift-agent@sha256:b29bdbf2c7859d28c3c8eea7fcda6df8a262014f37a664f077dfbc93e4ca7b47
```

## Notes

A concurrent `workflow_dispatch` run of the same workflow raced the same
`digest-bump/drift-agent-<sha>` branch name and lost the `git push` with a
"fetch first" rejection — an expected outcome of two independent CI runs
targeting an identical short-SHA branch name, not a defect in the reusable
template. The `push`-triggered run above is the one whose PR was merged.
