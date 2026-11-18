---
name: project-edai-rebuild-plan
description: EDAI MLOps coursework rebuild plan (260818-0832), locked stack, credit deadline, and known rubric gaps as of 2026-08-18
metadata:
  type: project
---

Repo `Financial-Distress-Data` (app monorepo) + sibling `financial-distress-gitops` (control repo)
implement a university MLOps coursework ("EDAI") graded against three rubric CSVs in `docs/`
(mini-coursework 100pt, final-ml 100pt/57 rows, final-llm 100pt/60 rows = 117 rows / 200pt total).
Plan: `plans/260818-0832-rebuild-unified-ml-and-llm-platform/` (plan.md + phase-01..08).

**Why:** prior submission scored 100/100 LLM track but ML track was 100% design-only and the data
generator only produced 16 rows / 780KB, too small to substantiate Spark-skew/lakehouse-compaction
rubric rows. User decided (2026-08-18) to purge all existing evidence and regenerate all 117 rows
under one unified evidence tree, delivering both tracks concurrently on GKE.

**Hard constraints:** GCP free-trial credit USD 300 expires 2026-11-06 (hard stop). CPU-only —
`GPUS_ALL_REGIONS` = 0, unraisable on free trial. Requested vCPU quota 32-48. Timeline ~10 weeks.

**Locked stack (do not relitigate without new evidence):** GKE/Terraform+Ansible, Argo CD (2 repos
kept separate), Jenkins (replaces GH Actions), Vault+ESO (replaces sealed-secrets), Istio ambient,
MinIO+Iceberg(REST catalog on Postgres)+Spark+Trino+Superset, Debezium→Kafka→Flink, Feast (Redis
online/Postgres offline), Kubeflow Pipelines+Ray Train+MLflow+KServe/Triton (ML), KServe 0.18+
`LLMInferenceService` on llm-d + vLLM CPU backend + agentgateway + kagent x3 + 2 MCP servers +
sandbox + KEDA (LLM), Prometheus/Grafana/Loki/Jaeger/PushGateway, DataHub (governance/lineage,
already in target architecture diagram in plan.md even though absent from the locked-decisions
table), Airflow (orchestration, already implied throughout phases).

**Verified via kongming review (2026-08-18):**
- KServe v0.18.0 is real, released ~April 2026 — the plan's version pin is not fictional (checked
  github.com/kserve/kserve/releases).
- Istio ambient reached GA in 1.24 (2024); by 2026 it is production-proven — not a risky choice.
- Feast SparkSource now supports Iceberg as an offline table format — integration is real, not
  a gap, though Feast+Iceberg is thinner than Feast+Parquet in practice (plan already flags this).
- vLLM CPU backend genuinely has "single core only" / limited production-readiness issues reported
  in community sources as of 2026 — a real risk beyond what phase 6 states; worth pinning
  `OMP_NUM_THREADS`/verifying multi-core utilization early, with llama.cpp-server-behind-KServe as
  documented fallback if vLLM CPU throughput proves unusable for benchmarking.
- Ray's own docs state there is "no inherent benefit" to >1 worker per node for CPU-only XGBoost
  training since XGBoost already threads across cores — the plan's "Ray dashboard shows distributed
  execution" framing (evidence of mechanism, not of speedup) is the right claim to make; do not let
  the write-up imply a CPU speedup from Ray Train that Ray's own docs contradict.
- **Concrete gap found**: ML rubric CI/CD row explicitly names "KNative Eventing kết hợp với KServe"
  for the real-time drift-detection API CI/CD row (1 pt). Plan phase 4 installs "Knative Serving"
  only — Knative **Eventing** is not mentioned anywhere in the plan. Grep confirmed zero hits for
  "eventing" across all phase files as of 2026-08-18.
- **Capacity gap found**: DataHub (GMS + frontend + Elasticsearch + MySQL/Kafka backing stores) is
  in the target architecture and required for the DataHub-lineage rubric rows (DP1/DP2/DP3 lineage,
  RAG pipeline lineage — 8+ pts), but its resource cost (~4-8 vCPU / 8-16GB in typical deployments)
  is never budgeted or risk-assessed in any phase, unlike every other heavy component (Kubeflow,
  Ray, Spark all have explicit capacity mitigations). A rough static-footprint accounting across all
  always-on platform services (Kubeflow ~4-8, DataHub ~4-8, Kafka+Connect+Flink ~5-7, Trino ~2-4,
  Airflow ~2-3, Jenkins ~2, observability stack ~2-3, KServe/Triton/vLLM ~4-8, agents/MCP/gateway
  ~2-4, Istio/Vault/ingress ~2-3) lands around 30-45 vCPU baseline alone, before any Spark/Ray/Locust
  burst workload — i.e. near or over the entire approved quota with the platform merely idling.

**How to apply:** future kongming/advisor consults on this repo should treat the locked-decisions
table in plan.md as settled (per orchestration-protocol review rules) unless armed with evidence
like the above. Do not re-propose swapping Iceberg/Spark/Jenkins/Vault/Istio ambient/KServe 0.18+ —
those were deliberately chosen and are technically sound per this review. Do flag Knative Eventing
and DataHub capacity budgeting as open items if asked again, and check whether phase 4/phase 8 were
updated to address them.
