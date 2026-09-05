# ADR-016: Full platform restore

## Status

Accepted — 2026-09-01 (`plans/260831-1644-rebuild-target-mlops-architecture/plan.md`).
Supersedes [ADR-010](./adr-010-llm-only-scope-and-platform-simplification.md).

## Context

ADR-010 (2026-08-07) cut the platform to an LLM-only, 7-day-deadline shape:
Istio, Vault, Jenkins, Argo Rollouts, and the entire ML track were dropped or
deferred. That deadline passed. The unified rebuild plan
(`plans/260831-1644-rebuild-target-mlops-architecture/plan.md`) restarts from
two binding objectives (O-1, O-2 in `plan.md`): every component and annotated
edge in `images/architecture/fdd-architecture-full-4k.png` must be live, and
all 161 rubric rows (300 points, both tracks) must be `executed`. Neither
objective is a proxy for the other — they are verified independently by
`scripts/verify_target_architecture.py` and `scripts/verify_rubric_coverage.py`
respectively (both created in this phase, see `phase-03`).

## Decision

The platform is restored to the full target architecture, named component by
component in `scripts/verify_target_architecture.py` (83 entries):

- **Istio** service mesh (`istiod`, Kiali, mTLS STRICT + AuthorizationPolicy,
  mesh-wide) — dropped by ADR-010 in favor of NGINX-only edge policy.
- **HashiCorp Vault + External Secrets Operator** — dropped by ADR-010 in
  favor of GitHub Actions secrets + sealed-secrets.
- **Jenkins** (controller + agents, two lane types: `app-ci` per-artifact,
  `model-promote` triggered by the holdout gate) — dropped by ADR-010 in
  favor of GitHub Actions.
- **Argo Rollouts** (canary + `AnalysisTemplate` gating on p99 latency, error
  rate, drift) — dropped by ADR-010; Deployment-backed workloads only,
  `InferenceService`/`LLMInferenceService` stay outside Rollouts control
  (phase-10).
- **The ML track** (57 rubric rows, 100 points): Kubeflow Pipeline, Ray
  distributed training (ADR-014), MLflow (ADR-006, un-deferred), Triton
  InferenceService, `feature-api`/`drift-api`, Superset/Trino/dbt analytics.
- **Terraform + Ansible**, restoring the Ansible role tree the rubric names
  but ADR-010's plan never built (phase-06).

Every restoration is assigned exactly one owning phase (P4-P12); the mapping
is `scripts/verify_target_architecture.py`'s `TARGET_COMPONENTS` table, built
by re-checking each component against the current phase files' `owns:`
frontmatter rather than trusting the source inventory's own (stale,
predecessor-numbering) Phase column — see `phase-03` §Architecture and Step 6.

## Consequences

- ADR-005 (Feast stores), ADR-006 (MLflow promotion), ADR-013 (CDC path),
  ADR-014 (distributed training) are amended or un-deferred by this ADR; see
  each file's own status header.
- The resident-cost model returns to a real cluster footprint across P4-P12,
  in contrast to ADR-010's "Resident cost: 0" LLM-only design. Phase-00's
  capacity/cost gates (`terraform/gcp/`, `reports/gate-decisions.md`) must be
  re-verified against the restored scope before P4 opens — phase-00's own
  `status: blocked` frontmatter records this is not yet done.
- `docs/platform/rubric-matrix.csv`'s 57 ML rows, previously carried as
  `design_only`/deferred backlog, become `executed` targets tracked in
  `docs/rubric-matrix-unified.csv` (phase-03).

## Alternatives Considered

- **Stay LLM-only, retrofit ML later as originally planned in
  `phase-05-deliver-ml-track.md`** (rejected — see `plan.md`: 100/300 points
  under a plan whose own audits found the architecture and rubric objectives
  are intersecting, not nested, sets; a full restore scores strictly more of
  both).
- **Restore the architecture image but not the ML rubric rows** (rejected:
  O-1 and O-2 are independently binding by explicit user decision, `plan.md`
  §Revision 2026-08-31 — when they conflict, points win, but here they do
  not conflict; both are achievable together).
