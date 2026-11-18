# ADR-008: Product-Plane Degradation

- Status: Accepted
- Date: 2026-08-02
- Deciders: the platform architecture review, product owner
- Related: `docs/platform/architecture.md`, ADR-003

## Context

The EKS evidence plane is ephemeral (ADR-003). When it is off, the product
must remain useful rather than broken.

## Decision

- The product plane (Next.js + Supabase) is always available.
- When EKS is `OFF`, the UI renders cached/persisted results with their
  timestamps and shows an honest evidence-plane state (`OFF -> REQUESTED ->
  PROVISIONING -> SYNCING -> READY -> CAPTURING -> DESTROYING -> OFF`, plus
  `FAILED` and `EXPIRED`).
- The UI never implies live inference when a saved result is displayed.
- Synchronous analyst inference via SSE is only available when EKS is `READY`;
  admin lifecycle actions are queued through a durable outbox and polled/
  subscribed.

## Consequences

- Analyst workflows keep working without EKS.
- A clear state machine prevents misleading "live" claims.

## Alternatives Considered

- Hiding all AI surfaces when EKS is off (rejected: breaks the analyst product
  and hides the honest state).
