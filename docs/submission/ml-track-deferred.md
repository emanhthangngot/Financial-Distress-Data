---
title: "ML Track — Deferred Index"
date: 2026-08-14
status: active
---

# ML Track: an accepted scope decision, not a shortfall

This submission's accepted scope is the **LLM track — 60 rubric rows, 100
points, fully covered** (see the
[LLM-track submission index](<rubric-final-coursework-(final-llm)/README.md>)).
The ML track (57 rows across 18 sections, also summing to 100 points in
`docs/platform/rubric-matrix.csv`) is **deferred by decision**, not by
oversight: every ML row's `evidence_type` in the rubric matrix is
`design_only`, recorded that way deliberately rather than discovered as a
gap during this freeze. ADR-010 (`docs/platform/adr/adr-010-llm-only-scope-and-platform-simplification.md`)
is the accepted architecture decision that scopes this submission to the LLM
track.

Each row below states its status and a concrete, one-line reason — not
repeated boilerplate — plus the nearest LLM-track equivalent where one
exists, since several ML mechanisms (CI/CD, routing/gateway, observability,
validation) share a reusable template with the LLM track's real
implementation.

## Deferred areas (18 sections, 57 rows, 100 points in the matrix)

| Area | Rows | Points | Status | Reason | Nearest LLM-track equivalent |
|---|---:|---:|---|---|---|
| A/B Testing | 2 | 2 | design_only | Same `platform/llm/ab-testing.yaml` mechanism proven for LLM; an ML-model variant was not deployed this window | `ab_testing.md` |
| Autoscale | 2 | 4 | design_only | HPA proven for LLM agent/tool web APIs; no separate ML-serving autoscale target deployed | `web_api_drift_detection.md` §HPA settle |
| CI/CD | 10 | 16 | design_only | Reusable `platform-ci.yaml` template proven for 6 LLM deployables; no ML training/inference-engine deployable exists to run it against | `ci_cd.md` |
| Documentation (low-level ML design) | 1 | 1 | design_only | `docs/platform/low-level-design.md`'s "ML Classes" section documents the design; no ML training code was implemented to verify against | `low_level_design.md` |
| Feature Store | 4 | 6 | design_only | Feast structured feature views and materialization jobs are `design_only` — this sandbox has no live Redis/MinIO reachable for a materialization run | `rag.md` §governance (shares the Feast/PGVector pattern) |
| IaC | 2 | 4 | design_only | Same Terraform/Ansible entrypoints proven for the LLM evidence plane; no separate ML infra provisioned | `iac.md` |
| Improve the Data Generator | 3 | 6 | design_only | Same drift-simulation/label-table mechanism proven for LLM; not re-run against an ML-specific scenario | `improve_data_generator.md` |
| ML (basic understanding notebook) | 1 | 2 | design_only | `notebooks/ml-training.ipynb` exists as a design artifact; not run against a live training job this window | — |
| ML Pipelines | 2 | 4 | design_only | Training pipeline design exists in low-level-design.md; no live training run executed | — |
| Novel ideas | 2 | 4 | design_only | LLM track's embedding-registry hot-swap and citation guard are the delivered novel-idea proofs for this submission | `novel_ideas.md` (LLM) |
| Observability | 6 | 10 | design_only | Same Prometheus/Jaeger/Loki collection path proven for LLM agents; no ML training/retrain pipeline emits metrics into it yet | `observability.md` |
| Repository Design | 1 | 2 | design_only | Same `src/llm/contracts.py` clean-code proof covers the shared repo-design discipline | `repository_design.md` |
| Routing & Gateway | 6 | 11 | design_only | Same NGINX ingress/basic-auth gateway proven for LLM web APIs; no separate ML web API route deployed | `routing_gateway.md` |
| Security | 2 | 2 | design_only | Same sealed-secrets controller proven for LLM; service-mesh authorization (istio/linkerd) not deployed in this submission | `security.md` |
| Validation & Verification | 5 | 10 | design_only | Same coverage/equivalence/mutation/property-based/load-test methodology proven for the LLM Web APIs; not re-run against an ML web API | `validation_verification.md` |
| Versioning | 2 | 4 | design_only | Model versioning proven for the LLM inference platform (Q8_0/Q4_K_M) and A/B revisions; Feast/feature-store versioning is design-only | `llm_inference_platform.md`, `ab_testing.md` |
| Web API — Real-time Drift Detection | 3 | 6 | design_only | The LLM track's `web_api_drift_detection.md` already delivers this exact capability — deploying a second, ML-specific instance would duplicate, not add, evidence | `web_api_drift_detection.md` (delivered) |
| Web API — Feature Pull | 3 | 6 | design_only | The LLM track's `web_api_user_data.md` already delivers this exact capability | `web_api_user_data.md` (delivered) |

**Totals: 57 rows, 100 points, all `design_only` in `docs/platform/rubric-matrix.csv`.**

## Why two rows read "already delivered, not duplicated"

The Web API rows (drift detection, feature pull) are structurally identical
between the ML and LLM rubric CSVs — same FastAPI/MCP/Helm/sandbox pattern,
same acceptance criteria. Rather than deploy a second, parallel instance
purely to claim ML-track points, this submission delivers the capability
once (LLM track) and points here rather than duplicating infrastructure for
a scope this plan does not claim.

## References

- [ADR-010: LLM-only scope and platform simplification](../platform/adr/adr-010-llm-only-scope-and-platform-simplification.md)
- [LLM-track submission index](<rubric-final-coursework-(final-llm)/README.md>)
- [Rubric matrix (machine-readable source of truth)](../platform/rubric-matrix.csv)
