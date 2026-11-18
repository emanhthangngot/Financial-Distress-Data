# the platform Acceptance Criteria Catalog

Every scored row in `rubric-matrix.csv` resolves to exactly one ID below. Each
criterion uses the mandatory `WHO -> ACTION -> RESULT` form. A row may share a
section-level criterion, but Phase 8 still requires its own executed artifact.

## ML Track — 57 rows / 100 points

- `ML-AC-01-WEB-API`: ML API consumer -> requests historical features with a valid or boundary input -> receives schema-validated, documented FastAPI output and deterministic error behavior.
- `ML-AC-02-DRIFT-API`: Drift producer -> submits a real-time event through Knative -> receives validated drift output from the independently deployed drift API and KServe-backed path.
- `ML-AC-03-AUTOSCALE`: Load tester -> drives each ML API across its accepted threshold -> observes independent scale-out/scale-in, bounded errors, and captured replica/latency evidence.
- `ML-AC-04-VALIDATION`: Test runner -> executes unit, equivalence, boundary, property, mutation, and Locust gates -> obtains >90% changed-code coverage, >80% mutation score, and an SLA report without hidden failures.
- `ML-AC-05-DATA-GENERATOR`: Data engineer -> generates configured drift and label scenarios -> obtains repeatable, schema-valid versions that cover normal, boundary, and drift cases.
- `ML-AC-06-FEAST`: Feature consumer -> requests timestamped structured features from Feast offline/online stores -> receives point-in-time-correct values with documented TTL, lineage, and idempotent materialization.
- `ML-AC-07-ML-UNDERSTANDING`: ML reviewer -> runs the documented notebook -> reproduces data retrieval, time split, baseline training, evaluation, and saved model output.
- `ML-AC-08-PIPELINES`: ML engineer -> starts the Kubeflow pipeline -> receives the same logical steps as the notebook plus a successful distributed Kubeflow Trainer run.
- `ML-AC-09-VERSIONING`: Promotion controller -> registers a candidate -> records immutable model, incremental data, code, environment, and lineage versions in MLflow.
- `ML-AC-10-CICD`: Developer -> changes any ML deployable -> CI tests/scans/signs once and opens a digest-only GitOps PR whose merge is the sole Argo deployment trigger.
- `ML-AC-11-ROUTING`: Reviewer -> opens every approved ML route through F5 NGINX OSS -> sees valid TLS/auth/rate-limit behavior while internal services remain private and mesh-authorized.
- `ML-AC-12-IAC`: Platform operator -> provisions Terraform and applies the mandatory Ansible role twice -> obtains reproducible cloud state plus a healthy, idempotent Vast.ai CPU load client targeting the llm-d endpoint.
- `ML-AC-13-OBSERVABILITY`: ML operator -> runs scheduled drift monitoring above and below threshold -> sees Pushgateway/Grafana telemetry and an actual KFP API run ID only for the trigger branch.
- `ML-AC-14-AB`: Reviewer -> sends controlled traffic to two ML revisions -> sees version-attributed quality, latency, error, distribution, and proxy-outcome comparisons plus Git rollback.
- `ML-AC-15-SECURITY`: Unauthorized ML workload -> attempts a protected call or secret access -> is denied while an authorized short-lived identity succeeds over mTLS without secret leakage.
- `ML-AC-16-REPOSITORY`: Maintainer -> inspects the source monorepo and GitOps control repo -> finds one owner per artifact, coherent module boundaries, tests, and no microservice-per-repo sprawl.
- `ML-AC-17-DOCUMENTATION`: Coursework reviewer -> opens README and ML documents -> finds business context, TOC, repo map, deployable-unit diagram, numbered/described flows, docstrings, and evidence links.
- `ML-AC-18-NOVEL`: ML reviewer -> executes the leakage guard and cost-governed reproducibility manifest -> receives measurable working proof tied to data/model digests.

## LLM Track — 60 rows / 100 points

> **Submission scope (2026-08-07, [ADR-010](./adr/adr-010-llm-only-scope-and-platform-simplification.md)):**
> the LLM track is the submitted track. The criteria below were amended to
> describe what the submission actually demonstrates — KServe/llm-d, Envoy
> gateways, Istio mesh and the Vast.ai worker are out of scope. The ML criteria
> above are unchanged and belong to the deferred phase-05 retrofit.

- `LLM-AC-01-INFERENCE`: LLM reviewer -> deploys and benchmarks the custom model server behind agentgateway -> receives versioned baseline/optimized TTFT, inter-token latency, throughput, memory, and cost evidence.
- `LLM-AC-02-MODEL-CONFIG`: Registered agent -> resolves its kagent `ModelConfig` -> reaches the model only through the agentgateway AI backend, with traceable configuration and a negative test proving direct access is refused.
- `LLM-AC-03-REGISTRY`: Release operator -> publishes an agent version -> finds its model config, replicas, sandbox policy, health, promotion history, and rollback target in agentregistry and the registry UI.
- `LLM-AC-04-RAG`: RAG pipeline -> ingests licensed documents -> writes chunked, deduplicated, versioned Feast/PGVector data with retrievable citations and lineage.
- `LLM-AC-05-FEATURE-RAG-API`: MCP consumer -> requests stored user features or RAG chunks -> receives validated async FastAPI output with health, errors, Helm rollout, load, and fallback evidence.
- `LLM-AC-06-DRIFT-MCP`: Agent -> invokes the drift MCP tool through agentgateway -> receives authorized, schema-valid real-time drift output with timeout, telemetry, and failure behavior.
- `LLM-AC-07-AGENT-UNDERSTANDING`: LLM reviewer -> runs the agent notebook -> observes both specialist agents using governed MCP tools and returning cited results.
- `LLM-AC-08-COORDINATOR`: User -> asks the coordinator a bounded multi-part question -> receives a cited synthesis after controlled A2A delegation, bounded hops, and deterministic partial-failure handling.
- `LLM-AC-09-WARMUP`: Load tester -> compares cold and warm agent/model pools -> observes improved startup/TTFT with recorded cost, minimum capacity, multi-replica spread, and scale-down behavior.
- `LLM-AC-10-VALIDATION`: Test runner -> executes LLM unit, equivalence, boundary, property, mutation, safety, and Locust gates -> obtains >90% unit test coverage with fixture/mock proof on the Web API tests, a recorded `mutmut` score on its declared module subset, and reproducible SLA output with no hidden failures.
- `LLM-AC-11-DATA-GENERATOR`: Data engineer -> generates prompt/document/drift/PII/citation scenarios -> obtains versioned, schema-valid cases that exercise safe and unsafe boundaries.
- `LLM-AC-12-CICD`: Developer -> changes an LLM, MCP, or agent deployable -> CI tests/scans/signs once and opens a digest-only GitOps PR whose merge is the sole Argo trigger.
- `LLM-AC-13-ROUTING`: Reviewer -> exercises agent chat, registry, MCP, A2A, metric-viewer, log-viewer, trace-viewer, and model routes -> observes a browser-valid certificate on the registered domain, basic authentication and a rate limit on the chat UI, and every backend reachable only through the ingress, proven by a refused direct call and a successful routed call.
- `LLM-AC-14-IAC`: Platform operator -> applies Terraform once and the evidence-host Ansible role twice -> obtains reproducible cloud state with a cost record, and a healthy host reporting `changed=0` on the second run.
- `LLM-AC-15-OBSERVABILITY`: Platform observer -> follows one agent request -> finds correlated token/TTFT/round-trip, per-agent/per-tool calls, failures, PII catches, redacted logs, and traces.
- `LLM-AC-16-AB`: Reviewer -> compares two LLM versions and two agent model configs -> sees version-attributed quality, TTFT, tokens, safety, failure, and cost metrics plus Git rollback.
- `LLM-AC-17-SECURITY`: Unauthorized agent/tool -> attempts a protected route or unsafe action -> is denied by identity, the restricted-PSS sandbox namespace, default-deny NetworkPolicy, and budget controls while redacted audit evidence remains.
- `LLM-AC-18-REPOSITORY`: Maintainer -> inspects the source monorepo and GitOps control repo -> finds coherent LLM/agent/MCP modules, one desired-state owner, tests, and no per-service repositories.
- `LLM-AC-19-DOCUMENTATION`: Coursework reviewer -> opens README and LLM documents -> finds business context, TOC, repo map, deployable-unit diagram, numbered/described flows, docstrings, and evidence links.
- `LLM-AC-20-NOVEL`: LLM reviewer -> executes embedding hot-swap and citation/PII guard scenarios -> receives zero-downtime vector compatibility proof and trace-linked safety decisions.

## Resolution Rule

Rubric generation assigns these IDs from the exact source section. The strict
auditor fails if an ID is missing, duplicated, not present in this catalog, or
if source row count/digest/points differ from the two canonical CSV files.

## Mandatory Non-Scored README Contract

- `MANDATORY-README`: Coursework reviewer -> opens README and repository docs -> finds the business goal, TOC, repo map, repository-wide file/module/class/function descriptions, deployable-unit-only diagram nodes, solid numbered/described primary edges, and a flow legend without needing to infer architecture from screenshots.
