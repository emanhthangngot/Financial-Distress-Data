# ADR-002: Two Repositories — Source and GitOps

- Status: Accepted
- Date: 2026-08-02
- Deciders: the platform architecture review
- Related: `docs/platform/architecture.md`

## Context

The requested "one repo" means one source monorepo for product, ML, LLM,
agents, APIs, tests, and evidence—not one repository per deployable. Cluster
desired state and policies still need a separate, least-privilege GitOps
control repository.

## Decision

- **Source repo** (`emanhthangngot/Financial-Distress-Data`): code, tests,
  schemas, Dockerfiles, evidence docs. the platform code lives under `src/ml/`,
  `src/drift/`, `src/llm/`, `src/agents/`, `apps/`, with thin orchestration
  wrappers under `dags/platform/`.
- **GitOps repo** (`emanhthangngot/financial-distress-gitops`): Terraform,
  Ansible, Helm, Kustomize, Argo CD applications, policies, environment values.
- Source CI never writes to the cluster. It pushes an immutable image digest,
  and a bot opens a GitOps PR changing the desired digest. Only the merged Git
  change is reconciled by Argo CD.

## Consequences

- Tag pushes alone never deploy; Git is the auditable source of truth.
- Rollback is a Git revert/new-digest commit, never an imperative Argo
  rollback (Argo official guidance under automated sync).

## Alternatives Considered

- A microservice-per-repository estate (rejected: unnecessary operational and
  review overhead for coursework).
- One repository for source and cluster desired state (rejected: conflates CI
  principals with cluster write authority).
