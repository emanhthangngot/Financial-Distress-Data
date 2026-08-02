---
title: "Phase 1: Lock specification and rubric contract"
status: todo
estimate: "3-4 days"
---

# Phase 1: Lock specification and rubric contract

## Context

Phase 2 is explicit, but `docs/coursework.md` still describes LLM/Kubernetes/AWS as optional or excluded. This phase replaces that stale boundary with one accepted architecture and a machine-checkable, 200-point evidence contract before implementation begins.

Start checklist:

- Active phase: explicit Phase 2 final coursework.
- Specs read: `AGENTS.md`, `docs/spec.md`, `docs/mini_coursework.md`, `docs/coursework.md`, ML rubric CSV, LLM rubric CSV.
- Skills: `ak:plan`, then `ak:devops`; `financial-distress-sdd` was requested by repo law but is not installed in this checkout.
- Verification target: rubric linter returns no unmapped scored row, no unowned evidence, and no Phase 1 contract mutation.

## Requirements

- [ ] Convert every ML and LLM CSV row into a stable rubric ID with points, requirement, Proof text, Deliverables text, implementation owner, test, and evidence path.
- [ ] Write acceptance criteria only as `WHO -> ACTION -> RESULT`.
- [ ] Separate executed proof, design-only claims, and optional stretch work.
- [ ] Make the two-plane architecture, two-repository boundary, four traffic layers, and cost envelope normative.
- [ ] Record the two custom ideas and five low-level classes for each track before code begins.

## Files

- Modify: `docs/coursework.md`, `docs/system-architecture.md`, `README.md`.
- Create: `docs/phase2/requirements.md`, `docs/phase2/rubric-matrix.{md,csv}`, `docs/phase2/architecture.md`, `docs/phase2/evidence-contract.md`, `docs/phase2/adr/`.
- Create tests/scripts: `tests/phase2/test_rubric_matrix.py`, `scripts/audit_phase2_evidence.py`.
- Do not modify Phase 1 data contracts, collectors, transforms, or evidence outputs.

## Implementation Steps

1. Give every non-header rubric row a semantic ID; do not rely on spreadsheet line numbers, which shift with multiline cells and headers.
2. Rewrite `docs/coursework.md` as the accepted Phase 2 source of truth while linking to, not duplicating, Phase 1 contracts.
3. Add numbered data flows for analyst, training, inference, agent, platform operator, CI/GitOps, observability, and teardown. Diagram nodes must be deployable units.
4. Add ADRs for two gateways, two repos, ephemeral EKS, KServe 0.18 pin, Feast stores, MLflow promotion, mixed Helm/Kustomize ownership, and product-plane degradation.
5. Seed failing rubric-matrix tests before implementing the linter; fail on missing Proof, Deliverables, evidence type, owner, or acceptance criterion.
6. Define the named class contracts:
   - ML: `TrainingDataService`, `PointInTimeSplitService`, `FeatureMaterializationService`, `ModelTrainingService`, `ModelPromotionService`.
   - LLM: `RagIngestionService`, `EmbeddingRegistryService`, `McpToolService`, `AgentOrchestrationService`, `AgentReleaseService`.
7. Define novel ideas and proof:
   - ML: point-in-time leakage guard; cost-governed reproducibility manifest tied to data delta and model digest.
   - LLM: embedding-version hot swap; citation/PII guard whose decisions link to traces and evidence.

## Validation

- `python scripts/audit_phase2_evidence.py --matrix-only --strict`
- `pytest tests/phase2/test_rubric_matrix.py tests/test_stage1_quality_gates.py`
- Markdown link and Mermaid syntax checks.

## Success Criteria

- [ ] Coursework reviewer -> selects any scored row in either CSV -> finds an exact implementation, validation command, and planned artifact without inference.
- [ ] Phase 1 maintainer -> compares the accepted Phase 2 spec to `docs/mini_coursework.md` -> finds additive boundaries and no silent change to Phase 1 semantics.
- [ ] Developer -> runs the rubric linter on a deliberately incomplete fixture -> receives a failing result naming the missing contract field.

## Risks and Rollback

- Risk: chasing all 200 points expands scope. Mitigation: use the cut policy in `plan.md`; never cut a scored item.
- Rollback: revert only Phase 2 documentation/linter commits; Phase 1 runtime stays untouched.
