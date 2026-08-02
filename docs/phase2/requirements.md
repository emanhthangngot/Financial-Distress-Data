# Phase 2 Requirements — Accepted Contract

This document is the authoritative Phase 2 requirements contract. Every
requirement below is written as `WHO -> ACTION -> RESULT`. It complements
`docs/coursework.md` (the accepted Phase 2 source of truth) and the
machine-checkable `docs/phase2/rubric-matrix.{csv,md}`.

Phase 2 is additive: it must not change Phase 1 collectors, schema contracts,
DQ rules, Gold output semantics, or evidence outputs defined in
`docs/mini_coursework.md`.

## 1. Two-Plane Architecture

- **Architect** -> defines a persistent product plane (Vercel Hobby +
  Supabase Free) and a disposable evidence plane (EKS in `ap-southeast-1`,
  6-hour default / 8-hour hard TTL, ≤ 3 sessions/month, ≤ USD 25/session,
  ≤ USD 10/month persistent) -> every Phase 2 deployable unit is assigned to
  exactly one plane and this assignment is recorded in
  `docs/phase2/architecture.md`.
- **Cost owner** -> runs any provisioning request -> sees a preflight cost
  projection; provisioning is blocked when projected spend would exceed
  USD 85 minus USD 15 reserve.
- **Phase 1 maintainer** -> compares the accepted Phase 2 spec to
  `docs/mini_coursework.md` -> finds additive boundaries and no silent change
  to Phase 1 semantics.

## 2. Two-Repository Boundary

- **Source repository** -> owns code, tests, schemas, Dockerfiles, and
  evidence docs (`emanhthangngot/Financial-Distress-Data`) -> all Phase 2
  implementation artifacts live here under `src/ml/`, `src/drift/`,
  `src/llm/`, `src/agents/`, and `apps/`.
- **GitOps repository** -> owns Terraform, Ansible, Helm, Kustomize,
  Argo CD applications, policies, and environment values
  (`emanhthangngot/financial-distress-gitops`) -> the source repo stores only
  typed API contracts, never infrastructure desired state.

## 3. Four Traffic Layers

- **NGINX Ingress** -> terminates public TLS and exposes only approved
  UIs/APIs -> internal services remain private and mesh-authorized.
- **Istio** -> enforces east-west mTLS and authorization -> service-to-service
  calls are authenticated and authorized.
- **agentgateway** -> owns MCP/A2A protocol routing, agent identity, and
  global model configuration -> agents reach the inference platform only
  through this gateway chain.
- **Envoy Gateway + Envoy AI Gateway** -> own KServe `LLMInferenceService`
  traffic and llm-d integration -> they are managed by GitOps as
  prerequisites, not auto-created by an `LLMInferenceService` object.

## 4. Rubric Contract

- **Coursework reviewer** -> selects any scored row in either final rubric
  CSV -> finds the exact implementation, validation command, and planned
  artifact in `docs/phase2/rubric-matrix.{md,csv}` without inference.
- **Developer** -> runs `python scripts/audit_phase2_evidence.py
  --matrix-only --strict` on a deliberately incomplete fixture -> receives a
  failing result naming the missing contract field.
- **Test runner** -> executes `pytest tests/phase2/test_rubric_matrix.py
  tests/test_stage1_quality_gates.py` -> both suites pass and Phase 1 quality
  gates are unchanged.

## 5. Class Contracts (Low-Level Design)

- **ML engineer** -> implements `src/ml/contracts.py` -> the five classes
  `TrainingDataService`, `PointInTimeSplitService`,
  `FeatureMaterializationService`, `ModelTrainingService`,
  `ModelPromotionService` exist with the documented method signatures.
- **LLM engineer** -> implements `src/llm/contracts.py` -> the five classes
  `RagIngestionService`, `EmbeddingRegistryService`, `McpToolService`,
  `AgentOrchestrationService`, `AgentReleaseService` exist with the documented
  method signatures.
- **Reviewer** -> opens `docs/phase2/low-level-design.md` -> finds each class
  contract, its design pattern, and its evidence link.

## 6. Novel Ideas

- **ML engineer** -> documents the point-in-time leakage guard and the
  cost-governed reproducibility manifest -> each idea has a named proof path
  in `docs/phase2/novel-ideas.md`.
- **LLM engineer** -> documents the embedding-version hot swap and the
  citation/PII guard -> each idea has a named proof path in
  `docs/phase2/novel-ideas.md`.

## 7. Evidence Contract

- **Evidence auditor** -> runs `python scripts/audit_phase2_evidence.py
  --require-executed --ml 100 --llm 100` at submission time -> every scored
  row has an existing, rubric_id-referencing evidence artifact under
  `docs/phase2/evidence/`.
- **Evidence owner** -> creates any evidence artifact -> it records
  requirement ID, execution timestamp, source SHA, GitOps SHA, image/model/
  data/agent versions, command/scenario, expected and actual result, and
  redaction status, per `docs/phase2/evidence-contract.md`.
