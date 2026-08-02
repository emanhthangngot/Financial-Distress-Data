# Phase 2 Low-Level Design — Class Contracts

This document locks the five ML and five LLM named classes before
implementation. Each class lists its design pattern, responsibility, key
methods (signature contract), and the rubric-matrix ID that will consume it.

Design patterns used across the contracts: **Strategy** (swappable baseline
training/evaluation), **Facade** (unified feature/tool access), **Factory**
(immutable artifact promotion), **Repository** (data versioning), **Observer**
(drift/event publication), and **Command** (deployment actions that can be
rolled back). The pattern is enforced by the `src/ml/contracts.py` and
`src/llm/contracts.py` signature stubs.

## ML Classes

### 1. TrainingDataService

- Pattern: **Repository + Facade**
- Responsibility: read Feast historical features, join labels by PIT rules,
  validate the training schema, and return snapshot lineage.
- Key methods: `read_historical_features`, `join_labels`, `validate_schema`,
  `snapshot_lineage`.
- Evidence link: rubric-matrix `ML-*` training data rows; implemented in
  phase-05.

### 2. PointInTimeSplitService

- Pattern: **Strategy**
- Responsibility: derive non-overlapping time boundaries and split into
  train/validation/test without future leakage.
- Key methods: `get_split_boundaries`, `split_by_time`, `assert_no_leakage`.
- Novel idea hook: the PIT leakage guard test asserts no feature after the
  label timestamp.

### 3. FeatureMaterializationService

- Pattern: **Repository + Idempotency**
- Responsibility: own batch/stream materialization checkpoints, TTL, and
  idempotency for offline→online and stream pushes.
- Key methods: `materialize_offline_to_online`, `push_stream_features_offline`,
  `push_stream_features_online`, `ttl_policy`.

### 4. ModelTrainingService

- Pattern: **Strategy + Template Method**
- Responsibility: train/evaluate distributed baseline models (logistic
  regression, XGBoost via Kubeflow Trainer) and log reproducible MLflow runs.
- Key methods: `train`, `evaluate`, `log_run`.

### 5. ModelPromotionService

- Pattern: **Command + Factory**
- Responsibility: apply promotion gates, resolve immutable artifact URI, open
  GitOps PR, canary, and emit Git-revert rollback metadata.
- Key methods: `check_gates`, `resolve_immutable_uri`, `open_gitops_pr`,
  `rollback_metadata`.

## LLM Classes

### 1. RagIngestionService

- Pattern: **Pipeline + Repository**
- Responsibility: fetch trusted documents, parse/chunk/deduplicate, enforce
  metadata/licensing, write Feast/PGVector versions.
- Key methods: `fetch_documents`, `parse_and_chunk`, `deduplicate_chunks`,
  `enforce_licensing_and_metadata`, `write_vectors`.

### 2. EmbeddingRegistryService

- Pattern: **Registry + Strategy**
- Responsibility: record model/vector compatibility and perform zero-downtime
  embedding-version hot swap.
- Key methods: `register_version`, `hot_swap`, `resolve_active`,
  `compatibility_check`.

### 3. McpToolService

- Pattern: **Facade + Guard**
- Responsibility: validate scoped tool requests, authorize agent/tool identity,
  enforce timeouts/budgets, emit traces.
- Key methods: `authorize`, `invoke`, `validate_request`, `emit_trace`.

### 4. AgentOrchestrationService

- Pattern: **Mediator + Circuit Breaker**
- Responsibility: coordinate specialist agents with bounded hops, citation
  checks and deterministic failure policy.
- Key methods: `coordinate`, `check_citations`, `failure_policy`.

### 5. AgentReleaseService

- Pattern: **Command + Canary**
- Responsibility: register, canary, warm, promote and roll back agent/model
  configurations through GitOps.
- Key methods: `register`, `canary`, `warm_up`, `promote_or_rollback`.

## Contract Enforcement

- Signature stubs live in `src/ml/contracts.py` and `src/llm/contracts.py`.
- `tests/phase2/test_rubric_matrix.py::TestClassContracts` asserts the files
  exist; later phases will add import-and-signature tests.
- Each class maps to rubric-matrix rows through its evidence path, so the
  reviewer can trace a design decision to a proof artifact.
