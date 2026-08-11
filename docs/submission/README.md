# Submission reviewer index

Human-facing index into `docs/phase2/evidence/llm/` — not a relocation.
`scripts/audit_phase2_evidence.py`'s `_audit_matrix` pins every row's
`evidence_path` under `docs/phase2/evidence/`; these pages link to that
canonical location, they don't hold the evidence itself. See
`docs/phase2/evidence-contract.md` for what counts as proof.

Status (2026-08-11): **47 of 60 LLM rows executed and stamped (79/100 points)**,
passing the strict two-repo gate with `--accept-design-only` for the 13 rows
below. Six observability rows and seven Routing & Gateway rows remain
`design_only` because their live routes/viewers have not been captured against
a running cluster — see
`plans/260811-1627-close-llm-rubric-to-100/` for the closeout sequencing.
Those 13 rows are not claimed until captured.

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
| `LLM-demonstrate-basic-underst-jupyter-notebook-demonstrate-a` | [`notebooks/agent-understanding-demo.ipynb`](../../notebooks/agent-understanding-demo.ipynb) | [evidence](../phase2/evidence/llm/LLM-demonstrate-basic-underst-jupyter-notebook-demonstrate-a.md) |
| `LLM-demonstrate-basic-underst-jupyter-notebooks-to-demonstra` | [`notebooks/agent-mcp-demo.ipynb`](../../notebooks/agent-mcp-demo.ipynb) | [evidence](../phase2/evidence/llm/LLM-demonstrate-basic-underst-jupyter-notebooks-to-demonstra.md) |
| `LLM-novel-ideas-idea-1` | [`src/llm/embedding_registry.py`](../../src/llm/embedding_registry.py) | [evidence](../phase2/evidence/llm/LLM-novel-ideas-idea-1.md) |
| `LLM-novel-ideas-idea-2` | [`src/llm/citation_guard.py`](../../src/llm/citation_guard.py) | [evidence](../phase2/evidence/llm/LLM-novel-ideas-idea-2.md) |
| `LLM-documentation-low-level-ml-design` | [`docs/phase2/low-level-design.md`](../phase2/low-level-design.md) | [evidence](../phase2/evidence/llm/LLM-documentation-low-level-ml-design.md) |

## Explicitly unearned live-evidence rows

The following exact rows remain `design_only` and must be passed to the final
audit as named cuts if the gateway/viewer capture is not completed. Static
manifests and local telemetry tests do not substitute for the required routed
runtime evidence.

```text
LLM-observability-agent-tool-call-metrics
LLM-observability-collect-v-visualize-metrics-v-
LLM-observability-m-b-o-t-nh-t-c-c-metrics
LLM-observability-t-ng-t-cho-logs
LLM-observability-t-ng-t-cho-traces
LLM-observability-web-api-metrics
LLM-routing-gateway-authentication-cho-ui-test-age
LLM-routing-gateway-c-c-service-c-n-c-hide-ng-sau-
LLM-routing-gateway-l-m-c-i-n-y-cho-web-api-k-o-d-
LLM-routing-gateway-service-coi-log
LLM-routing-gateway-service-coi-trace
LLM-routing-gateway-ui-cho-agent-registry
LLM-routing-gateway-ui-test-agent
```

The GitOps repository (`financial-distress-gitops`) stays private — it carries
a committed `terraform.tfstate` and `ansible/inventory.ini`, which the
auditor's own denylist treats as leaks. The grader instead gets a scrubbed
public read-only mirror containing only `platform/`, `apps/`, `charts/`,
`argocd/` at the frozen `gitops_sha`; its URL is recorded in
`plans/260811-1627-close-llm-rubric-to-100/phase-06-freeze-submission.md`
once published. No token or private credential is stored in this repository.

Sections without a dedicated page here (inference, model config, registry,
RAG, feature/RAG API, drift/MCP, agent understanding, coordinator, warm-up,
data generator, A/B, documentation, novel ideas) are covered directly by
their `docs/phase2/evidence/llm/*.md` files and `docs/phase2/rubric-matrix.csv`
— no separate reviewer index needed at this scale (60 LLM rows, 20 acceptance
IDs).
