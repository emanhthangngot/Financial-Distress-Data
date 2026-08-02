# Phase 2 Novel Ideas — Two per Track

Four ideas, two per track, each with a named proof path. These are recorded
before implementation begins (phase-01 requirement 5) and will be executed and
captured in phases 5–8.

## ML Idea 1: Point-in-Time Leakage Guard

- **Claim:** any training frame built from Feast must never contain a feature
  value produced *after* the label/reference timestamp.
- **Mechanism:** `PointInTimeSplitService.assert_no_leakage` plus a property
  test that asserts `future_feature_leakage_rows == 0` on generated frames.
- **Proof path:** `docs/phase2/evidence/ml/pit-leakage-guard.md`; pytest
  `tests/phase2/test_rubric_matrix.py` seed + Hypothesis property test in
  phase-05.
- **Rubric hook:** ML training data rows (point-in-time correctness).

## ML Idea 2: Cost-Governed Reproducibility Manifest

- **Claim:** every training/RAG run records a reproducibility manifest tied to
  the data delta and the model digest, with a hard cost cap enforced.
- **Mechanism:** manifest records snapshot ID, parent ID, changed
  partitions/hashes, code SHA, environment digest, image digest and projected
  cost; provisioning fails if projected spend exceeds the cap.
- **Proof path:** `docs/phase2/evidence/ml/reproducibility-manifest.md`;
  golden-manifest test in phase-05.
- **Rubric hook:** ML data versioning + CI/CD reproducibility rows.

## LLM Idea 1: Embedding-Version Hot Swap

- **Claim:** switching the active embedding model version causes no downtime
  and no mixed-vector query.
- **Mechanism:** dual-read validation (new + old versions answer in parallel),
  then alias change atomically; a compatibility check rejects mixed-dimension
  queries.
- **Proof path:** `docs/phase2/evidence/llm/embedding-hot-swap.md`; integration
  evidence in phase-06.
- **Rubric hook:** LLM RAG pipeline + custom model rows.

## LLM Idea 2: Citation / PII Guard With Trace-Linked Decisions

- **Claim:** unsupported or sensitive LLM output is blocked or rewritten, and
  every decision links back to its OpenTelemetry trace and evidence manifest.
- **Mechanism:** citation check (every claim → retrievable source) and PII
  guard (prompt/document/tool-arg redaction) that record a decision record
  referencing the trace ID.
- **Proof path:** `docs/phase2/evidence/llm/citation-pii-guard.md`;
  observability evidence in phase-06.
- **Rubric hook:** LLM telemetry (PII safety frequency) + agent safety rows.
