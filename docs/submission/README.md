# Submission reviewer index

Human-facing index into `docs/phase2/evidence/llm/` — not a relocation.
`scripts/audit_phase2_evidence.py`'s `_audit_matrix` pins every row's
`evidence_path` under `docs/phase2/evidence/`; these pages link to that
canonical location, they don't hold the evidence itself. See
`docs/phase2/evidence-contract.md` for what counts as proof.

Status (2026-08-12): **58 of 60 LLM rows executed and stamped (96/100 points)**,
passing the strict two-repo gate with `--accept-design-only` for the 2 rows
below. All seven Routing & Gateway rows and four of six observability rows
were captured live against the running `fsds-evidence` GKE cluster in the
phase 5 window (`plans/260811-1627-close-llm-rubric-to-100/`). Two
observability rows (token/TTFT/PII-catch metrics, agent/MCP-tool-call
metrics) stay `design_only` — see the named-cuts section below.

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

## Grader demo account

One Supabase auth account, analyst role, no elevated privileges — created
2026-08-11 for phase 3 of `plans/260811-1627-close-llm-rubric-to-100/`. This
is a coursework submission, not a production system with real users, so the
credential is disclosed here directly rather than through a separate
out-of-band channel (2026-08-11 decision). No sign-up, no password reset —
this is the only account.

- email: `distresslens.grader@gmail.com`
- password: `VjBG4w8QpeXW4EMYfCII`

## Gateway credentials

Basic-auth in front of all five protected routes (https://distresslens.duckdns.org),
and Grafana's own admin login behind it. Coursework demo, disclosed directly
here per the 2026-08-11 decision (same reasoning as the grader Supabase
account above).

- gateway basic-auth: user `grader`, password `qMwgNhqAOaJqcQwNNZ0Om0Nq`
- Grafana admin (after the gateway): user `grader`, password `zoyrVNjLTQYNJOOGlpVxCnou`

## Explicitly unearned live-evidence rows

The following exact rows stay `design_only`, named as cuts rather than
claimed. Both are blocked by defects in the coordinator/agent round-trip
found during the phase 5 capture window, documented in
[observability.md](./observability.md):

```text
LLM-observability-agent-tool-call-metrics
LLM-observability-m-b-o-t-nh-t-c-c-metrics
```

Every other Routing & Gateway and Observability row (11 of 13) is captured
live and linked from [routing_gateway.md](./routing_gateway.md) and
[observability.md](./observability.md).

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
