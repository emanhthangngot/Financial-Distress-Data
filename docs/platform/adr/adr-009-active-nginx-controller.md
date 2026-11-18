# ADR-009: Active F5 NGINX Ingress Controller OSS

- Status: Accepted
- Date: 2026-08-02
- Deciders: the platform architecture review, platform operator
- Related: `docs/platform/architecture.md`, `phase-03-bootstrap-gitops-and-aws-evidence-platform.md`

## Context

The rubric requires NGINX ingress behavior, TLS, authentication, rate limits,
and hidden internal services. The community `kubernetes/ingress-nginx` project
was retired and archived in March 2026, so it is not a responsible dependency
for a new evidence platform.

## Decision

- Use the active F5 NGINX Ingress Controller Open Source project
  (`nginx/kubernetes-ingress`), never `kubernetes/ingress-nginx`.
- The compatibility spike starts from controller 5.5.4 / Helm chart 2.6.4,
  then records exact chart version, image digest, Kubernetes compatibility,
  rendered resources, and upgrade/rollback result before the pin becomes
  submission-normative.
- NGINX terminates public TLS and exposes only the feature API, agent chat UI,
  agent registry UI, Grafana, Kibana, and Jaeger routes required by the rubric.
  Basic authentication and rate limits apply where the rubric requests them;
  all other services remain private behind Istio authorization.

## Consequences

- The plan avoids a retired controller while still satisfying the explicit
  NGINX rubric rows.
- Version and digest evidence must be refreshed if the compatibility spike
  selects a different supported release.

## Alternatives Considered

- Community `kubernetes/ingress-nginx` (rejected: retired/archived in March
  2026).
- Replacing NGINX with only an Envoy gateway (rejected: does not satisfy the
  NGINX-specific rubric requirements).
