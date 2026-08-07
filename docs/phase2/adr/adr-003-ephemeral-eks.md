# ADR-003: Ephemeral EKS Evidence Plane

- Status: **Superseded by [ADR-010](./adr-010-llm-only-scope-and-platform-simplification.md) (2026-08-07)**
- Date: 2026-08-02
- Deciders: Phase 2 architecture review, cost owner
- Related: `docs/phase2/architecture.md`, `plan.md` cost envelope

> **Superseded:** the evidence plane is a single rented CPU VM running `k3d`,
> under USD 15 for the week. AWS is reduced to one timeboxed three-hour session
> for Terraform, TLS and cost evidence. What survives: the teardown job is
> created before any billable resource, cost tags are mandatory, evidence is
> exported before teardown, and the product plane stays useful when the
> evidence cluster is off (ADR-008).

## Context

Full Kubernetes evidence (KServe, KFP, Feast, MLflow, agents) is expensive to
run continuously. The plan targets all 100 ML + 100 LLM points without keeping
EKS running 24/7.

## Decision

- EKS in `ap-southeast-1` with managed node groups (Spot where compatible).
- Default TTL 6 hours; hard TTL 8 hours; at most 3 sessions/month.
- Target ≤ USD 25/session and ≤ USD 10/month persistent resources.
- Provisioning is blocked when projected spend exceeds USD 85 minus USD 15
  reserve.
- An independent EventBridge Scheduler → CodeBuild destroy job is created
  immediately at provision time, so the session is destroyed even if the
  worker fails or the session is partial.
- Persistent low-cost resources (S3 evidence exports, RDS retained snapshots)
  are bounded and itemized in a monthly-cost inventory.

## Consequences

- The product plane must remain useful when EKS is off (ADR-008).
- Every evidence run must be captured and exported before teardown.

## Alternatives Considered

- Always-on EKS (rejected: exceeds the cost envelope and the rubric does not
  require persistent serving).
