# ADR-002: Two Repositories — Source and GitOps

- Status: Accepted
- Date: 2026-08-02
- Deciders: Phase 2 architecture review
- Related: `docs/phase2/architecture.md`

## Context

The source repo owns the data/AI codebase; infrastructure desired state and
cluster policies must be auditable and Git-versioned separately.

## Decision

- **Source repo** (`emanhthangngot/Financial-Distress-Data`): code, tests,
  schemas, Dockerfiles, evidence docs. Phase 2 code lives under `src/ml/`,
  `src/drift/`, `src/llm/`, `src/agents/`, `apps/`.
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

- Single monorepo for code + infra (rejected: conflates CI principals with
  cluster write authority).
