---
phase: 5
title: "Gap 05: Finish serving and Jenkins release"
status: pending
priority: P1
effort: "Remaining implementation after platform and runtime"
dependencies: ["phase-03-platform-and-jenkins.md", "phase-04-ml-and-langgraph.md"]
---

# Gap 05: Finish serving and Jenkins release

## Objective

Close the production path from protected serving through Jenkins promotion, GitOps convergence and
rollback. Keep existing public contracts.

## Tasks

1. Finish API readiness, NGINX trusted HTTPS, auth/rate-limit, autoscaling and UI failure states.
2. Create the thin Jenkinsfile and artifact catalog from actual remaining deployable surfaces.
3. Migrate one reference lane, prove success/failure/cancel/rollback, then migrate every required lane.
4. Switch required statuses to Jenkins and remove only superseded GitHub Actions delivery authority.
5. Open digest-only GitOps PRs, observe Argo convergence and exercise prior-release restoration.


## Progress snapshot

Repository-side delivery contracts are present: the protected feature/drift API tests pass 19
focused cases, `Jenkinsfile` performs catalog validation and redacted digest handoff, and
`scripts/ci/delivery.py` has 7 focused contract tests. Live HTTPS/edge, provider-backed serving,
Jenkins controller execution, Argo convergence and rollback remain unverified. This phase remains
pending until the approved runtime window and external controller/provider prerequisites exist.
## Acceptance criteria

- [ ] Analyst -> submits a real request through protected edge -> feature/model/LangGraph/API/UI response contains provenance and explicit unavailable states.
- [ ] Jenkins -> runs each mapped remaining lane -> immutable signed artifact, behavior result, GitOps PR and runtime smoke are attributable.
- [ ] Release operator -> induces bad candidate/provider failure -> current healthy revision remains served or prior compatible revision is restored.
- [ ] Repository -> completes cutover -> no duplicate Jenkins/GitHub delivery authority or direct Jenkins production mutation remains.
