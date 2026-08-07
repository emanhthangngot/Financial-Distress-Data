# Submission reviewer index

Human-facing index into `docs/phase2/evidence/llm/` — not a relocation.
`scripts/audit_phase2_evidence.py`'s `_audit_matrix` pins every row's
`evidence_path` under `docs/phase2/evidence/`; these pages link to that
canonical location, they don't hold the evidence itself. See
`docs/phase2/evidence-contract.md` for what counts as proof.

Status: **skeletons** (phase-03 day 0). Filled in during phase-08 once each
row moves from `design_only` to `executed`.

| Page | Rubric sections | Rows |
|---|---|---|
| [iac.md](./iac.md) | IaC, Repository | LLM-AC-14, LLM-AC-18 |
| [routing_gateway.md](./routing_gateway.md) | Routing & Gateway | LLM-AC-13 |
| [observability.md](./observability.md) | Observability | LLM-AC-15 |
| [security.md](./security.md) | Security | LLM-AC-17 |
| [ci_cd.md](./ci_cd.md) | CI/CD | LLM-AC-12 |
| [validation_verification.md](./validation_verification.md) | Validation & Verification | LLM-AC-10 |
| [cost.md](./cost.md) | Cost (doubles as the row-67 IaC cost deliverable) | LLM-AC-14 |

Sections without a dedicated page here (inference, model config, registry,
RAG, feature/RAG API, drift/MCP, agent understanding, coordinator, warm-up,
data generator, A/B, documentation, novel ideas) are covered directly by
their `docs/phase2/evidence/llm/*.md` files and `docs/phase2/rubric-matrix.csv`
— no separate reviewer index needed at this scale (60 LLM rows, 20 acceptance
IDs).
