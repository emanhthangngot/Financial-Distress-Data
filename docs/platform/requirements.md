# the platform Requirements — Accepted Contract

This document is the authoritative the platform requirements contract. Every
requirement below is written as `WHO -> ACTION -> RESULT`. It complements
`docs/coursework.md` (the accepted the platform source of truth), the resolvable
catalog in `docs/platform/acceptance-criteria.md`, and the machine-checkable
`docs/platform/rubric-matrix.{csv,md}`.

the platform is additive: it must not change the platform collectors, schema contracts,
DQ rules, Gold output semantics, or evidence outputs defined in
`docs/mini_coursework.md`.

## 1. Two-Plane Architecture

- **Architect** -> defines a persistent product plane (Vercel Hobby +
  Supabase Free) and a disposable evidence plane (EKS in `ap-southeast-1`,
  6-hour default / 8-hour hard TTL, ≤ 3 sessions/month, ≤ USD 25/session,
  ≤ USD 10/month persistent) -> every the platform deployable unit is assigned to
  exactly one plane and this assignment is recorded in
  `docs/platform/architecture.md`.
- **Cost owner** -> runs any provisioning request -> sees a preflight cost
  projection; provisioning is blocked when projected spend would exceed
  USD 85 minus USD 15 reserve.
- **the platform maintainer** -> compares the accepted the platform spec to
  `docs/mini_coursework.md` -> finds additive boundaries and no silent change
  to the platform semantics.

## 2. Two-Repository Boundary

- **Source repository** -> acts as the single application monorepo and owns
  code, tests, schemas, Dockerfiles, thin `dags/platform/` wrappers, and evidence
  docs (`emanhthangngot/Financial-Distress-Data`) -> product/API/ML/LLM/agent
  artifacts live under `src/ml/`, `src/drift/`, `src/llm/`, `src/agents/`,
  `apps/`, and `dags/platform/`, without creating a repo per service.
- **GitOps repository** -> owns Terraform, Ansible, Helm, Kustomize,
  Argo CD applications, policies, and environment values
  (`emanhthangngot/financial-distress-gitops`) -> the source repo stores only
  typed API contracts, never infrastructure desired state.

## 3. Four Traffic Layers

- **F5 NGINX Ingress Controller OSS** -> terminates public TLS and exposes only
  approved UIs/APIs -> internal services remain private and mesh-authorized;
  the retired community `kubernetes/ingress-nginx` is forbidden.
- **Istio** -> enforces east-west mTLS and authorization -> service-to-service
  calls are authenticated and authorized.
- **kagent Agent** -> references a kagent `ModelConfig` whose upstream/base URL
  is an agentgateway AI backend -> agent model calls follow `Agent ->
  ModelConfig -> agentgateway -> Envoy AI Gateway -> KServe/llm-d`, while MCP
  and A2A calls use declared agentgateway routes and never bypass the chain.
- **Envoy Gateway + Envoy AI Gateway** -> own KServe `LLMInferenceService`
  traffic and llm-d integration -> they are managed by GitOps as
  prerequisites, not auto-created by an `LLMInferenceService` object.

## 4. Rubric Contract

- **Coursework reviewer** -> selects any scored row in either final rubric
  CSV -> finds its source-row digest, acceptance ID, implementation repo/file,
  behavior-validation command, contract test, and planned evidence artifact in
  `docs/platform/rubric-matrix.{md,csv}` without inference.
- **Developer** -> runs `python scripts/audit_phase2_evidence.py
  --matrix-only --strict` on a deliberately incomplete fixture -> receives a
  failing result naming the missing contract field.
- **Test runner** -> executes `pytest tests/platform/test_rubric_matrix.py
  tests/test_stage1_quality_gates.py` -> both suites pass and the platform quality
  gates are unchanged.

## 4.1 Product UI and approved visual baseline

- **Product reviewer** -> opens `docs/platform/product.md` -> finds the three
  approved reference IDs (`UI-APPROVED-01` analyst overview,
  `UI-APPROVED-02` company detail + AI analysis, `UI-APPROVED-03` admin
  GitOps/evidence operations), their routes, required content and evidence
  fields without relying on an unavailable image attachment.
- **Web developer** -> implements the approved route/state inventory -> every
  route has deterministic loading, empty, stale, degraded, forbidden, timeout
  and error fixtures, and the create-next-app placeholder is removed.
- **Analyst** -> opens the company/report surfaces while EKS is off -> sees a
  timestamped cached result with `CACHED_RESULT`/`LIVE_UNAVAILABLE`, provenance
  and the educational/non-investment disclaimer rather than a false live
  inference claim.
- **LLM reviewer** -> opens `/agents/chat` -> sees citations, MCP/tool trace,
  agent/model version, bounded streaming and policy/error states without
  prompts, tokens, credentials or PII.
- **Platform reviewer** -> opens `/agents/registry` and `/ops/evidence` -> sees
  registry governance, lifecycle/cost/GitOps state and role-appropriate
  controls; unauthorized mutations fail server-side with no outbox effect.
- **Accessibility reviewer** -> runs the UI suite at 1440/1024/390 px -> finds
  keyboard-visible focus, semantic labels/headings, contrast, non-color status
  cues and reduced-motion compliance.
- **Evidence owner** -> records each UI screenshot/trace -> includes reference
  ID, route, state, viewport, source SHA, GitOps SHA, data/model/agent version,
  expected/actual result and redaction status; missing fields fail the Phase 8
  auditor.
- **ML/LLM operator** -> opens `/ops/evidence` or `/reports/[id]` -> sees a
  freshness/run/version link to the canonical Grafana observability and A/B
  artifacts, while the product screenshot remains supplemental rather than a
  substitute for executed dashboard evidence.

## 5. 100/100 Operational Closures

- **ML operator** -> runs the scheduled the platform drift DAG -> Airflow pulls
  Feast offline features, joins a ground-truth/proxy reference, computes drift,
  publishes metrics through Prometheus Pushgateway for Grafana, and—only when
  the threshold is exceeded—calls the Kubeflow Pipelines API and persists the
  created run ID/status; both skip and trigger branches are testable.
- **Platform operator** -> applies the Ansible role-based Vast.ai CPU worker
  playbook twice -> an OpenAI-compatible Locust/benchmark client targeting the
  llm-d endpoint is healthy and the second run reports no changes, with
  command/log/cost evidence under the aggregate USD 10 cap. The worker is not
  part of the AWS GPU inference pool.
- **Platform operator** -> runs the version compatibility spike -> records an
  exact chart/image digest matrix for F5 NGINX OSS, Kubernetes/EKS, KServe
  0.18, Knative, Envoy Gateway/AI Gateway, llm-d/GIE, kagent, kmcp,
  agentgateway, agentregistry, Agent Sandbox, KFP/Trainer, Istio, and Argo CD
  before any evidence deployment.

## 6. Class Contracts (Low-Level Design)

- **ML engineer** -> implements `src/ml/contracts.py` -> the five classes
  `TrainingDataService`, `PointInTimeSplitService`,
  `FeatureMaterializationService`, `ModelTrainingService`,
  `ModelPromotionService` exist with the documented method signatures.
- **LLM engineer** -> implements `src/llm/contracts.py` -> the five classes
  `RagIngestionService`, `EmbeddingRegistryService`, `McpToolService`,
  `AgentOrchestrationService`, `AgentReleaseService` exist with the documented
  method signatures.
- **Reviewer** -> opens `docs/platform/low-level-design.md` -> finds each class
  contract, its design pattern, and its evidence link.

## 7. Novel Ideas

- **ML engineer** -> documents the point-in-time leakage guard and the
  cost-governed reproducibility manifest -> each idea has a named proof path
  in `docs/platform/novel-ideas.md`.
- **LLM engineer** -> documents the embedding-version hot swap and the
  citation/PII guard -> each idea has a named proof path in
  `docs/platform/novel-ideas.md`.

## 8. Evidence Contract

- **Evidence auditor** -> runs `python scripts/audit_phase2_evidence.py
  --require-executed --run-validations --lakehouse-base "$PHASE1_BASE_SHA"
  --gitops-root "$GITOPS_CHECKOUT" --ml 100 --llm 100` at submission time ->
  every scored row has an existing, rubric_id-referencing evidence artifact,
  the the platform diff is clean against the frozen baseline, and evidence SHAs
  match the checked-out source and GitOps HEADs.
- **Evidence owner** -> creates any evidence artifact -> it records
  requirement ID, execution timestamp, source SHA, GitOps SHA, image/model/
  data/agent versions, a mandatory reproduction command, expected and actual result, and
  redaction status, per `docs/platform/evidence-contract.md`.

## 9. Source Provenance

The CSV export retains only one literal URL:
`https://mutmut.readthedocs.io/`. Phrases such as “tutorial này” and “ở đây”
lost their hyperlinks during export. Until the original Sheet/XLSX hyperlink
metadata is supplied, implementation pins MUST use official upstream sources
(KServe, kagent, agentgateway, F5 NGINX, Kubeflow, Feast, MLflow, Argo CD,
Istio) and record the chosen URL/version in the compatibility report. The
missing tutorial provenance is disclosed; it is not silently reconstructed.

| Capability | Normative upstream source |
|---|---|
| Mutation testing | <https://mutmut.readthedocs.io/> |
| KServe LLMInferenceService + Envoy integration | <https://kserve.github.io/website/docs/model-serving/generative-inference/llmisvc/llmisvc-envoy-ai-gateway> |
| Envoy AI Gateway | <https://aigateway.envoyproxy.io/docs/> |
| llm-d | <https://llm-d.ai/docs/> |
| kagent resources/API | <https://kagent.dev/docs/kagent/resources/api-ref> |
| agentgateway Kubernetes | <https://agentgateway.dev/docs/kubernetes/main/about/overview/> |
| kmcp | <https://kagent.dev/docs/kmcp/> |
| agentregistry | <https://github.com/kagent-dev/agentregistry> |
| Agent Sandbox | <https://agent-sandbox.sigs.k8s.io/> |
| F5 NGINX Ingress Controller OSS | <https://docs.nginx.com/nginx-ingress-controller/install/helm/open-source/> |
| Kubeflow Pipelines | <https://www.kubeflow.org/docs/components/pipelines/> |
| Kubeflow Trainer | <https://www.kubeflow.org/docs/components/trainer/> |
| Feast | <https://docs.feast.dev/> |
| MLflow | <https://mlflow.org/docs/latest/ml/> |
| Knative | <https://knative.dev/docs/> |
| Argo CD | <https://argo-cd.readthedocs.io/en/stable/> |
| Istio | <https://istio.io/latest/docs/> |
| Evidently | <https://docs.evidentlyai.com/> |
| Prometheus Pushgateway | <https://github.com/prometheus/pushgateway> |
| Ansible | <https://docs.ansible.com/ansible/latest/> |
| Vast.ai | <https://docs.vast.ai/> |
