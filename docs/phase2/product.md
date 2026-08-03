# DistressLens Product and UI Contract

This is the product-plane contract for Phase 2. It turns the three approved
visual references into testable routes and states; it does not replace the
runtime evidence captured in Phase 8.

## Implementation audit snapshot

At source `0e9aac4` (2026-08-03), the product foundation (contracts, Supabase
schema/RLS tests and state-machine types) exists, but the web app still has the
default create-next-app `apps/web/src/app/page.tsx` and none of the approved
routes is implemented. This is why the approved UI is not visible in the
checkout: the plan had previously named a generic shell without a concrete
route/state contract. Phase 2 remains `todo` until the routes and evidence
fixtures below are implemented; this document is not a claim that the UI has
already shipped.

## Approved visual references

The approved images are identified as `UI-APPROVED-01` through
`UI-APPROVED-03`. Their original binaries must be copied without modification
to `docs/phase2/evidence/product/design/` before visual sign-off. They are not
currently present in this checkout, so no generated mock is accepted as a
substitute.

| ID | Route(s) | Required content | Evidence |
|---|---|---|---|
| `UI-APPROVED-01` | `/companies`, `/companies/[ticker]`, `/compare`, `/reports/[id]` | company search, risk snapshot, model explanation, cited RAG answer, comparison, saved report, freshness and cached/live label | Playwright screenshot at 1440/1024/390 px + route/state manifest |
| `UI-APPROVED-02` | `/agents/chat` | agent selection, streaming answer, citations, MCP/tool trace, model/agent version, timeout, policy block and EKS-OFF state | Playwright screenshot + redacted trace/output |
| `UI-APPROVED-03` | `/agents/registry`, `/ops/evidence` | agent governance, versions, replicas, sandbox policy, lifecycle timeline, cost, GitOps revision, evidence export, promotion, rollback and teardown | two linked route screenshots + RBAC/action matrix |

## Information architecture

- **Analyst:** search → company detail → explanation/RAG → compare → save/export.
- **Agent:** chat and registry are separate navigation targets. Chat is for
  bounded analysis; registry is for governed releases and health.
- **Operations:** evidence lifecycle and cost controls are separate from
  analyst content. A viewer can inspect but cannot mutate.
- **Persistent shell:** header carries product identity, plane status,
  authenticated role and disclaimer; navigation remains usable when EKS is
  offline.

## State and data contract

Every route implements loading, empty, stale, degraded, forbidden, timeout and
server-error states. A cached result includes `cached_at`, `source_sha`, data or
model version and a visible `LIVE_UNAVAILABLE`/`CACHED_RESULT` label. No UI may
claim that cached output came from a live KServe or agent run.

The evidence operations state machine is:

```text
OFF -> REQUESTED -> PROVISIONING -> SYNCING -> READY -> CAPTURING -> DESTROYING -> OFF
                         |-> FAILED -------------------------------> retry
READY/any active state --expiry-------------------------------> EXPIRED -> OFF
```

The UI reads typed contracts from `packages/contracts/`; it never infers
authorization or lifecycle state from client-only flags.

## Visual and accessibility rules

- Use the approved information hierarchy and labels; cosmetic motion is not a
  Phase 2 requirement.
- Responsive breakpoints: 1440 px desktop, 1024 px tablet, 390 px mobile.
- Keyboard operation and visible focus are mandatory; semantic headings,
  labels, landmarks and contrast must pass axe checks.
- Honor `prefers-reduced-motion` and provide non-color status indicators.
- Long model/tool output is scrollable, copyable and capped; errors explain a
  safe next action without revealing prompts, tokens, credentials or PII.
- Keep the educational/non-investment disclaimer visible on company,
  explanation, chat, comparison and exported-report surfaces.

## Security and product boundaries

- Supabase RLS and Next.js server boundaries enforce role/action checks;
  client hiding is only a presentation aid.
- Lifecycle mutations require a fresh fencing token and idempotency key.
- Agent chat uses bounded SSE only when the evidence plane is `READY`; lifecycle
  operations use the durable outbox and polling/subscription path.
- Rate limits and per-user AI quotas are enforced at the product boundary.
- Audit events contain actor/action/result/version, never raw prompts, tokens or
  secrets.

## Cross-track dashboard boundary

ML observability and ML/LLM A/B dashboards remain canonical Grafana/evidence-
plane artifacts because they depend on Prometheus and executed workloads. The
product shell exposes their freshness, run ID, model/agent version and a
deep-link/status card from `/ops/evidence` and `/reports/[id]`; a product
screenshot never replaces the Grafana export required by the rubric.

## Acceptance criteria

- Product reviewer -> opens `UI-APPROVED-01` -> sees analyst search, risk,
  explanation, RAG, comparison, saved-report and freshness paths with honest
  cached/degraded states.
- LLM reviewer -> opens `UI-APPROVED-02` -> sees citations, tool trace,
  model/agent version and policy/error states without secret leakage.
- Platform reviewer -> opens `UI-APPROVED-03` -> sees registry governance and
  evidence lifecycle/cost/GitOps actions with unauthorized actions rejected on
  the server.
- Accessibility reviewer -> runs the desktop/mobile Playwright suite -> sees
  deterministic screenshots, keyboard focus and reduced-motion compliance.

## Evidence manifest

Each UI evidence file under `docs/phase2/evidence/product/` records:

```yaml
reference_id: UI-APPROVED-01
route: /companies/ACME
state: EKS_OFF_CACHED
viewport: 1440x900
source_sha: "<40-hex>"
gitops_sha: "<40-hex>"
data_version: "<version>"
artifact: "<screenshot-or-playwright-report>"
expected_result: "<what the reference proves>"
actual_result: "<observed result>"
redaction_status: "<redactions>"
```

The Phase 8 evidence auditor must reject a UI artifact with a missing route,
state, viewport, provenance, or redaction field.
