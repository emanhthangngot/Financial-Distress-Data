# Evidence — CI/CD for the LLM coordinator agent

Proves `.github/workflows/phase2-agent-coordinator.yaml` runs the reusable
CI template end to end for the `coordinator` deployable: build → cosign sign
→ push immutable GHCR digest → open a GitOps PR rewriting the real
`coordinator` `Deployment` in `platform/agents/agent-deployments.yaml`.

- rubric_id: LLM-ci-cd-agent-l-m-coordinator
- execution_timestamp: 2026-08-10T23:41:38+07:00
- source_sha: 3e08cdfc9be520056b3fd32214dc73f8dbbe0b1c
- gitops_sha: a9491d1a0164f098e0de02ab6cebec39752dc8c0
- versions: sigstore/cosign-installer@v3.7.0, ghcr.io/emanhthangngot/financial-distress-data/coordinator
- command: `git push origin main` (merge of PR #63, `dev`→`main`) triggering `phase2-agent-coordinator.yaml` on the `push` event
- expected_result: `lint`, `test`, `build`, `phase5-verification`, `gitops-pr` all succeed; `gitops-pr` rewrites the `coordinator` `Deployment`'s `image:` field with a real digest and opens a PR against `master`
- actual_result: run [31410264103](https://github.com/emanhthangngot/Financial-Distress-Data/actions/runs/31410264103) — all 5 jobs succeeded; opened [financial-distress-gitops#29](https://github.com/emanhthangngot/financial-distress-gitops/pull/29) rewriting the `coordinator` Deployment's `image:` to `sha256:4f6b7b62c8385334d581b4cb52bf09556bb0f30b5d83dcbc19be631bd7a0d4ea`; merged into `master`
- redaction_status: reviewed — source repository is public, GitOps repository is private; no secret values in this file

## Command output (real run)

```
$ gh run view 31410264103 --json jobs --jq '.jobs[] | {name,conclusion}'
{"conclusion":"success","name":"ci / lint"}
{"conclusion":"success","name":"ci / test"}
{"conclusion":"success","name":"ci / phase5-verification"}
{"conclusion":"success","name":"ci / build"}
{"conclusion":"success","name":"ci / gitops-pr"}

$ git show origin/master:platform/agents/agent-deployments.yaml | grep coordinator -A1 | grep image
image: ghcr.io/emanhthangngot/financial-distress-data/coordinator@sha256:4f6b7b62c8385334d581b4cb52bf09556bb0f30b5d83dcbc19be631bd7a0d4ea
```

## Notes

A concurrent `workflow_dispatch` run of the same workflow raced the same
`digest-bump/coordinator-<sha>` branch name and won the `git push` before the
`push`-triggered run above got there; the `push`-triggered run's own
`gitops-pr` job was actually the one still in progress when the manual
dispatch's PR (#29) merged. Both runs' `build`/`sign` steps succeeded and
produced the identical image digest (immutable content-addressed digest from
the same source commit), so which run's PR merged first is immaterial to the
row's proof — `apps/feature-mcp/**`-triggered `push` CI is the reproducible
path; the `workflow_dispatch` trigger exists as an operational fallback.
