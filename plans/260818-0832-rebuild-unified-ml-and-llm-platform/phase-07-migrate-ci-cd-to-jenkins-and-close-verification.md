---
title: "Phase 7: Migrate CI/CD To Jenkins And Close Verification"
status: todo
priority: P1
effort: "1 week"
dependencies: [5, 6]
---

# Phase 7: Migrate CI/CD To Jenkins And Close Verification

## Overview

Make Jenkins the sole CI/CD driver for every pipeline, service, job and agent, with
all credentials in Vault, and close the Validation & Verification block: coverage
above 90% with fixtures and mocks, equivalence partitioning and boundary value
analysis, mutation testing on changed code only, property-based idempotency
testing, and a Locust load test producing an HTML SLA report.

## Requirements

Functional — CI/CD (each is test + build + auto-deploy):
- [ ] Materialize pipeline
- [ ] Training pipeline
- [ ] Data pipelines DP1, DP2, DP3
- [ ] RAG data pipeline
- [ ] Feature API and drift API
- [ ] Inference engine (KServe)
- [ ] Real-time drift detection service
- [ ] Job 1 (stream → offline store) and Job 2 (stream → online store)
- [ ] Feature agent, drift agent, coordinator agent, each with its MCP server
- [ ] Every credential sourced from Vault; none in code, in a repo, or in Jenkins config

Functional — Validation & Verification:
- [ ] Unit test coverage > 90%, with demonstrated fixtures and mocks over the web APIs
- [ ] Test cases parametrized using equivalence partitioning and boundary value analysis
- [ ] Mutation testing with `mutmut`, scoped to changed code only
- [ ] Property-based idempotency tests (Hypothesis) over prediction and materialization paths
- [ ] Locust load test of the feature API producing an HTML report used as the SLA

Non-functional:
- [ ] CD pulls the model tagged `production` from the MLflow registry, packages and deploys it
- [ ] A pipeline failure blocks deployment rather than deploying a broken artifact

## Architecture

Jenkins replaces GitHub Actions entirely; no workflow retains deploy authority.
Pipelines are declarative `Jenkinsfile`s in the app repo, with a shared library for
the common stages (lint, test, build, sign, push, bump GitOps). Deployment is never
`kubectl` from Jenkins — Jenkins builds an immutable digest and commits a bump to
the GitOps repo, and Argo CD reconciles. That keeps GitOps the single deployment
path even with Jenkins driving.

Credentials come from Vault through the Jenkins Vault plugin, scoped per pipeline.

Verification techniques map to rubric rows one-to-one, so each is a deliberate,
documented artifact rather than a side effect:

| Technique | Applied to | Artifact |
|---|---|---|
| Coverage > 90% + fixtures/mocks | Both web APIs and both MCP servers | Coverage HTML report |
| Equivalence partitioning + BVA | API request validation boundaries | Parametrized test module + a partition/boundary table |
| Mutation testing | Only code changed in this plan | `mutmut` results summary |
| Property-based idempotency | Prediction determinism, materialization re-run | Hypothesis test module |
| Load test | Feature API | Locust HTML report |

## Related Code Files

- Create: `Jenkinsfile` per deployable, `ci/jenkins/shared-library/`, `tests/verification/test_equivalence_boundary.py`, `tests/verification/test_idempotency_properties.py`, `locust/feature_api_load.py`, `docs/validation-verification.md`
- Modify: `pyproject.toml` (coverage config, mutmut config), `tests/**`
- Create in GitOps: `platform/ci-jenkins/pipelines/`, image-digest bump automation
- Delete: `.github/workflows/**` deploy workflows in both repos (retain at most a lint-only PR check)

## Implementation Steps

1. Build the Jenkins shared library first: lint → test → build → scan → push-by-digest → bump-GitOps. Every pipeline composes these stages instead of restating them.
2. Write the `Jenkinsfile` for one representative service (feature API) end to end and prove the full path: commit → Jenkins → image digest → GitOps bump → Argo sync → running pod.
3. Replicate across the remaining pipelines, services, jobs and agents.
4. Wire the model-promotion path: CD pulls the MLflow model tagged `production`, packages it, and deploys through the same digest-bump mechanism.
5. Move every credential into Vault; verify no pipeline holds a secret in its own config; delete the GitHub Actions deploy workflows.
6. Raise coverage above 90% across the APIs and MCP servers, using fixtures and mocks for external dependencies (Feast, Redis, MLflow, the inference endpoint).
7. Write the equivalence-partitioning and BVA test module: document the partitions and boundaries in a table, then parametrize the tests directly from it so the table and the tests cannot drift.
8. Configure `mutmut` scoped to this plan's changed files; run it and record the surviving-mutant summary; kill survivors that indicate genuine test gaps.
9. Write Hypothesis property tests: the same input yields the same prediction across repeated calls; materialization re-run over the same window is a no-op.
10. Write the Locust scenario against the feature API, run it, and produce the HTML report; state the SLA the numbers support.

## Success Criteria

- [ ] Every deployable has a Jenkins pipeline that has run green at least once, captured from the Jenkins UI
- [ ] A commit reaches a running pod with no manual step and no `kubectl` from Jenkins
- [ ] A deliberately failing test blocks the deployment stage
- [ ] `grep` finds no credential literal in either repo; Jenkins credentials resolve from Vault
- [ ] No GitHub Actions workflow retains deploy permissions
- [ ] Coverage report shows > 90%, with fixture and mock usage visible in the test source
- [ ] The partition/boundary table matches the parametrized cases exactly
- [ ] `mutmut` results recorded with surviving mutants either killed or justified individually
- [ ] Hypothesis tests pass over ≥100 generated examples per property
- [ ] Locust HTML report exists with throughput and latency percentiles, and a stated SLA
- [ ] `python scripts/run_quality_gates.py` passes

## Risk Assessment

- **Twelve-plus Jenkins pipelines is a lot of near-duplicate YAML/Groovy.** Mitigation: the shared library is step 1 for exactly this reason. If a pipeline needs more than ~30 lines of its own, the shared library is missing a stage.
- **Chasing 90% coverage produces assertion-free tests that inflate the number.** Mitigation: mutation testing is the counterweight, and it runs on the same code. A high coverage figure with many surviving mutants fails this phase, and should be treated as failing.
- **`mutmut` over the whole repo would run for hours.** Mitigation: scope to files changed in this plan, as the rubric itself instructs.
- **Load testing from inside the cluster measures the wrong thing.** Mitigation: run Locust from the GCE VM through the public ingress, so the SLA reflects the path a real client takes.
