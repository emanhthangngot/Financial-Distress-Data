# Submission reviewer index

Human-facing index into `docs/platform/evidence/llm/` — not a relocation.
`scripts/audit_phase2_evidence.py`'s `_audit_matrix` pins every row's
`evidence_path` under `docs/platform/evidence/`; these pages link to that
canonical location, they don't hold the evidence itself. See
`docs/platform/evidence-contract.md` for what counts as proof.

Status (2026-08-13): **60 of 60 LLM rows are logically covered (100/100
points)** and the live runtime has been verified. The final submission freeze
is pending: source and GitOps SHA stamps must be regenerated after the latest
commits, then the strict two-repository gate must pass without
`--accept-design-only`. This page must not be treated as a frozen submission
until that gate is green.

The live snapshot recorded 13/13 Argo applications as `Synced` and `Healthy`,
10 kagent agents as `Ready`, a successful coordinator round-trip with feature
and drift citations, healthy Prometheus targets, and discoverable Jaeger
services. These are runtime checks; canonical evidence files remain the rubric
source of truth.

| Page | Rubric sections | Rows |
|---|---|---|
| [iac.md](./iac.md) | IaC, Repository | LLM-AC-14, LLM-AC-18 |
| [routing_gateway.md](./routing_gateway.md) | Routing & Gateway | LLM-AC-13 |
| [observability.md](./observability.md) | Observability | LLM-AC-15 |
| [security.md](./security.md) | Security | LLM-AC-17 |
| [ci_cd.md](./ci_cd.md) | CI/CD | LLM-AC-12 |
| [validation_verification.md](./validation_verification.md) | Validation & Verification | LLM-AC-10 |
| [cost.md](./cost.md) | Cost (doubles as the row-67 IaC cost deliverable) | LLM-AC-14 |

## Phase 06 owned artifacts

| Rubric row | Executed artifact | Canonical evidence |
|---|---|---|
| `LLM-demonstrate-basic-underst-jupyter-notebook-demonstrate-a` | [`notebooks/agent-understanding-demo.ipynb`](../../notebooks/agent-understanding-demo.ipynb) | [evidence](../platform/evidence/llm/LLM-demonstrate-basic-underst-jupyter-notebook-demonstrate-a.md) |
| `LLM-demonstrate-basic-underst-jupyter-notebooks-to-demonstra` | [`notebooks/agent-mcp-demo.ipynb`](../../notebooks/agent-mcp-demo.ipynb) | [evidence](../platform/evidence/llm/LLM-demonstrate-basic-underst-jupyter-notebooks-to-demonstra.md) |
| `LLM-novel-ideas-idea-1` | [`src/llm/embedding_registry.py`](../../src/llm/embedding_registry.py) | [evidence](../platform/evidence/llm/LLM-novel-ideas-idea-1.md) |
| `LLM-novel-ideas-idea-2` | [`src/llm/citation_guard.py`](../../src/llm/citation_guard.py) | [evidence](../platform/evidence/llm/LLM-novel-ideas-idea-2.md) |
| `LLM-documentation-low-level-ml-design` | [`docs/platform/low-level-design.md`](../platform/low-level-design.md) | [evidence](../platform/evidence/llm/LLM-documentation-low-level-ml-design.md) |

## Grader and operator access

Demo accounts, gateway basic-auth, Grafana credentials, package-registry
tokens, and temporary cloud access are delivered through the private
submission/operator channel. They are intentionally not stored in this
repository. The reviewer should request the current out-of-band handoff if a
credentialed browser or Grafana session is required; the evidence links here
remain usable without exposing those secrets.

## Live-evidence completion

Every Routing & Gateway and Observability row is captured live and linked from
[routing_gateway.md](./routing_gateway.md) and [observability.md](./observability.md).
The two final Observability artifacts are:

- [per-request token, latency, and PII metrics](../platform/evidence/llm/LLM-observability-m-b-o-t-nh-t-c-c-metrics.md)
- [per-agent and per-MCP-tool call/failure metrics](../platform/evidence/llm/LLM-observability-agent-tool-call-metrics.md)

The GitOps repository (`financial-distress-gitops`) stays private because its
working tree carries operational state that must not be published. A scrubbed
public read-only mirror containing only the approved deployment paths is a
pending final packaging step and must be created at the frozen `gitops_sha`.
Its URL belongs in the freeze report once published. No token or private
credential is stored in this repository.

## Remaining freeze checklist

- Restamp every canonical LLM evidence row with the final source SHA and
  matching GitOps SHA.
- Run the strict two-repository audit with `--require-executed
  --run-validations --track LLM` and confirm zero findings.
- Publish the scrubbed GitOps mirror at the same frozen GitOps SHA.
- Re-run the product/live checks from the final commit pair and attach only
  redacted, reproducible evidence.
- Deliver demo credentials out of band and hibernate or tear down the GKE
  evidence plane after capture.

Sections without a dedicated page here (inference, model config, registry,
RAG, feature/RAG API, drift/MCP, agent understanding, coordinator, warm-up,
data generator, A/B, documentation, novel ideas) are covered directly by
their `docs/platform/evidence/llm/*.md` files and `docs/platform/rubric-matrix.csv`
— no separate reviewer index needed at this scale (60 LLM rows, 20 acceptance
IDs).
